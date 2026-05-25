"""Retail V2 customer segmentation abilities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from backend.core.errors import ValidationError

RANDOM_STATE = 42

SEGMENT_FEATURES = [
    "R_最近购买间隔",
    "F_购买频次",
    "M_消费金额",
    "客单价",
    "类目熵",
    "占比_蔬果",
    "占比_粮油",
    "占比_日配",
    "占比_休闲",
    "小类购买数",
    "促销金额占比",
    "促销频次占比",
    "低价带占比",
    "高价带占比",
    "生鲜占比",
    "复购紧迫度均值",
]

LOG_FEATURES = ["F_购买频次", "M_消费金额", "客单价", "小类购买数", "复购紧迫度均值"]


@dataclass(frozen=True)
class RetailCustomerSegmentationResult:
    """Customer segmentation outputs for pipeline composition."""

    customer_segments: pd.DataFrame
    segment_profile: pd.DataFrame
    model_comparison: pd.DataFrame
    feature_columns: list[str]
    best_segment_count: int


def cluster_retail_customers(
    customer_profile: pd.DataFrame,
    segment_count: int | None = None,
    min_segments: int = 2,
    max_segments: int = 7,
    random_state: int = RANDOM_STATE,
) -> RetailCustomerSegmentationResult:
    """Cluster Retail V2 customers with a deterministic GMM soft segmentation."""

    _validate_customer_profile(customer_profile)
    prepared_features = _prepare_feature_frame(customer_profile)
    scaled_features = StandardScaler().fit_transform(prepared_features.values)
    sample_count = len(prepared_features)
    if sample_count < 2:
        raise ValidationError("Retail V2 customer segmentation requires at least 2 customers")

    best_segment_count = segment_count or _select_gmm_segment_count(
        scaled_features=scaled_features,
        min_segments=min_segments,
        max_segments=max_segments,
        random_state=random_state,
    )
    if best_segment_count < 2 or best_segment_count > sample_count:
        raise ValidationError("Retail V2 customer segmentation segment_count is out of range")

    model = GaussianMixture(
        n_components=best_segment_count,
        covariance_type="full",
        random_state=random_state,
        n_init=5,
        reg_covar=1e-4,
    ).fit(scaled_features)
    labels = model.predict(scaled_features)
    probabilities = model.predict_proba(scaled_features)

    segment_profile, segment_names = name_retail_segments(customer_profile, labels)
    customer_segments = _build_customer_segments(
        customer_profile=customer_profile,
        labels=labels,
        probabilities=probabilities,
        segment_names=segment_names,
    )
    model_comparison = pd.DataFrame(
        [
            {
                "model": "GMM",
                "segment_count": best_segment_count,
                **_cluster_metrics(scaled_features, labels),
            }
        ]
    )

    return RetailCustomerSegmentationResult(
        customer_segments=customer_segments,
        segment_profile=segment_profile,
        model_comparison=model_comparison,
        feature_columns=SEGMENT_FEATURES.copy(),
        best_segment_count=best_segment_count,
    )


def name_retail_segments(
    customer_profile: pd.DataFrame,
    labels: np.ndarray,
    label_column: str = "cluster",
) -> tuple[pd.DataFrame, dict[int, str]]:
    """Name customer segments using Retail V2 marketing prototypes."""

    segmented = customer_profile.copy()
    segmented[label_column] = labels
    segment_profile = segmented.groupby(label_column).agg(
        人数=("user_id", "size"),
        R=("R_最近购买间隔", "mean"),
        F=("F_购买频次", "mean"),
        M=("M_消费金额", "mean"),
        促销=("促销敏感度", "mean"),
        生鲜=("生鲜占比", "mean"),
        类目熵=("类目熵", "mean"),
        低价带=("低价带占比", "mean"),
    )
    medians = segmented[
        [
            "R_最近购买间隔",
            "F_购买频次",
            "M_消费金额",
            "促销敏感度",
            "生鲜占比",
            "类目熵",
            "低价带占比",
        ]
    ].median()

    raw_names: dict[int, str] = {}
    for segment_id, row in segment_profile.iterrows():
        if (
            row["M"] >= medians["M_消费金额"]
            and row["F"] >= medians["F_购买频次"]
            and row["R"] <= medians["R_最近购买间隔"]
        ):
            name = "高价值稳定型"
        elif (
            row["R"] >= segmented["R_最近购买间隔"].quantile(0.7)
            and row["M"] >= medians["M_消费金额"]
        ):
            name = "流失预警型"
        elif row["生鲜"] >= segmented["生鲜占比"].quantile(0.65):
            name = "生鲜高频型"
        elif row["促销"] >= segmented["促销敏感度"].quantile(0.65) or row["低价带"] >= segmented[
            "低价带占比"
        ].quantile(0.7):
            name = "促销敏感型"
        elif row["类目熵"] >= segmented["类目熵"].quantile(0.65):
            name = "跨类探索型"
        elif row["类目熵"] <= segmented["类目熵"].quantile(0.35):
            name = "类目集中型"
        else:
            name = "低频偶发型"
        raw_names[int(segment_id)] = name

    segment_names = _dedupe_segment_names(raw_names)
    profile = segment_profile.reset_index()
    profile = profile.rename(columns={label_column: "segment_id"})
    profile["segment"] = profile["segment_id"].map(segment_names)
    total_amount = customer_profile["M_消费金额"].sum()
    profile["segment_sales"] = profile["人数"] * profile["M"]
    profile["sales_share"] = profile["segment_sales"] / total_amount if total_amount else 0
    profile["customer_share"] = profile["人数"] / len(customer_profile)
    return profile, segment_names


def _validate_customer_profile(customer_profile: pd.DataFrame) -> None:
    required_columns = ["user_id", *SEGMENT_FEATURES, "促销敏感度", "生鲜占比"]
    missing = [column for column in required_columns if column not in customer_profile.columns]
    if missing:
        raise ValidationError(
            "Retail V2 customer profile missing segmentation columns: " + ", ".join(missing)
        )


def _prepare_feature_frame(customer_profile: pd.DataFrame) -> pd.DataFrame:
    features = customer_profile[SEGMENT_FEATURES].copy()
    for column in SEGMENT_FEATURES:
        features[column] = pd.to_numeric(features[column], errors="coerce").fillna(0)
    for column in LOG_FEATURES:
        features[column] = np.log1p(features[column].clip(lower=0))
    return features


def _select_gmm_segment_count(
    scaled_features: np.ndarray,
    min_segments: int,
    max_segments: int,
    random_state: int,
) -> int:
    sample_count = scaled_features.shape[0]
    upper_bound = min(max_segments, sample_count)
    lower_bound = min(min_segments, upper_bound)
    candidates = range(lower_bound, upper_bound + 1)
    scores = []
    for segment_count in candidates:
        model = GaussianMixture(
            n_components=segment_count,
            covariance_type="full",
            random_state=random_state,
            n_init=3,
            reg_covar=1e-4,
        ).fit(scaled_features)
        scores.append((segment_count, model.bic(scaled_features)))
    return min(scores, key=lambda score: score[1])[0]


def _cluster_metrics(scaled_features: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    unique_labels = set(labels.tolist())
    if len(unique_labels) < 2 or len(unique_labels) >= len(labels):
        return {"silhouette": np.nan, "dbi": np.nan, "ch": np.nan, "noise_rate": 0.0}
    return {
        "silhouette": float(silhouette_score(scaled_features, labels)),
        "dbi": float(davies_bouldin_score(scaled_features, labels)),
        "ch": float(calinski_harabasz_score(scaled_features, labels)),
        "noise_rate": 0.0,
    }


def _build_customer_segments(
    customer_profile: pd.DataFrame,
    labels: np.ndarray,
    probabilities: np.ndarray,
    segment_names: dict[int, str],
) -> pd.DataFrame:
    output = customer_profile[["user_id"]].copy()
    output["segment_id"] = labels
    output["segment"] = output["segment_id"].map(segment_names)
    output["segment_confidence"] = probabilities.max(axis=1)
    for segment_id in range(probabilities.shape[1]):
        output[f"P_{segment_id}"] = probabilities[:, segment_id]
    return output


def _dedupe_segment_names(raw_names: dict[int, str]) -> dict[int, str]:
    seen: dict[str, int] = {}
    names: dict[int, str] = {}
    for segment_id, name in sorted(raw_names.items()):
        seen[name] = seen.get(name, 0) + 1
        names[segment_id] = name if seen[name] == 1 else f"{name}{seen[name]}"
    return names
