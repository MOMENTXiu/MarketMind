"""Estimate Retail V2 promotion response and causal effects."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.model_selection import StratifiedKFold

from backend.core.errors import ValidationError

BASE_CONFOUNDER_COLUMNS = ["unit_price", "price_rank", "weekday", "is_weekend", "sale_month"]
CUSTOMER_CONFOUNDER_COLUMNS = ["M_消费金额", "F_购买频次", "促销敏感度"]
EFFECT_DETAIL_COLUMNS = [
    "群体",
    "DML因果效应",
    "标准误",
    "95%CI下",
    "95%CI上",
    "样本数",
    "朴素均值差",
    "估计方法",
]
PROMOTION_RESPONSE_COLUMNS = [
    "群体",
    "样本数",
    "促销笔数",
    "非促销笔数",
    "促销笔均金额",
    "非促销笔均金额",
    "朴素PromoLift",
    "促销销售占比",
    "DML因果效应",
    "95%CI下",
    "95%CI上",
    "估计方法",
]
REQUIRED_SALES_COLUMNS = [
    "user_id",
    "cat_l1_name",
    "cat_l3_code",
    "item_id",
    "amount",
    "unit_price",
    "is_promo",
    "is_return",
    "weekday",
    "is_weekend",
    "sale_month",
]
EPS = 1e-9


@dataclass(frozen=True)
class PromotionEffectResult:
    """Promotion response tables and DML-style treatment effect details."""

    promotion_response: pd.DataFrame
    effect_detail: pd.DataFrame
    overall_effect: dict[str, float | int | str]
    naive_ate: float


def estimate_promotion_effect(
    clean_sales: pd.DataFrame,
    customer_profile: pd.DataFrame,
    customer_segments: pd.DataFrame,
    min_group_size: int = 8,
    n_folds: int = 5,
    random_state: int = 42,
) -> PromotionEffectResult:
    """Estimate naive and cross-fitted promotion effects without artifact IO."""

    if min_group_size < 1:
        raise ValidationError("min_group_size must be at least 1")
    if n_folds < 2:
        raise ValidationError("n_folds must be at least 2")

    _validate_columns(clean_sales, REQUIRED_SALES_COLUMNS, "clean_sales")
    _validate_columns(customer_profile, ["user_id"], "customer_profile")
    _validate_columns(customer_segments, ["user_id", "segment"], "customer_segments")

    analysis_frame = _build_analysis_frame(clean_sales, customer_profile, customer_segments)
    if analysis_frame.empty:
        raise ValidationError("Retail V2 promotion effect requires positive sales rows")

    treatment = analysis_frame["is_promo"].to_numpy(dtype=float)
    outcome = analysis_frame["amount"].to_numpy(dtype=float)
    naive_ate = _naive_difference(treatment, outcome)
    residuals = _cross_fit_residuals(
        analysis_frame,
        treatment,
        outcome,
        n_folds=n_folds,
        random_state=random_state,
    )

    effect_detail = _build_effect_detail(
        analysis_frame=analysis_frame,
        treatment=treatment,
        outcome=outcome,
        residuals=residuals,
        min_group_size=min_group_size,
    )
    promotion_response = _build_promotion_response(analysis_frame, effect_detail)
    overall_row = effect_detail.iloc[0]
    overall_effect: dict[str, float | int | str] = {
        "theta": float(overall_row["DML因果效应"]),
        "se": float(overall_row["标准误"]),
        "ci95_lower": float(overall_row["95%CI下"]),
        "ci95_upper": float(overall_row["95%CI上"]),
        "n": int(overall_row["样本数"]),
        "method": str(overall_row["估计方法"]),
        "naive_ate": float(naive_ate),
    }

    return PromotionEffectResult(
        promotion_response=promotion_response,
        effect_detail=effect_detail,
        overall_effect=overall_effect,
        naive_ate=float(naive_ate),
    )


def _validate_columns(frame: pd.DataFrame, required: list[str], name: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValidationError(f"{name} missing required columns: {', '.join(missing)}")


def _build_analysis_frame(
    clean_sales: pd.DataFrame,
    customer_profile: pd.DataFrame,
    customer_segments: pd.DataFrame,
) -> pd.DataFrame:
    sales = clean_sales[clean_sales["is_return"] == 0].copy()
    sales["amount"] = pd.to_numeric(sales["amount"], errors="coerce")
    sales["unit_price"] = pd.to_numeric(sales["unit_price"], errors="coerce")
    promo_values = pd.to_numeric(sales["is_promo"], errors="coerce")
    if sales["amount"].isna().any() or sales["unit_price"].isna().any():
        raise ValidationError("clean_sales contains invalid amount or unit_price values")
    if promo_values.isna().any() or not set(promo_values.unique()).issubset({0, 1}):
        raise ValidationError("clean_sales is_promo must contain binary 0/1 values")
    sales["is_promo"] = promo_values.astype(int)

    price_rank = sales.groupby(["cat_l3_code", "item_id"], as_index=False)["unit_price"].mean()
    price_rank["price_rank"] = price_rank.groupby("cat_l3_code")["unit_price"].rank(pct=True)
    sales = sales.merge(
        price_rank[["cat_l3_code", "item_id", "price_rank"]],
        on=["cat_l3_code", "item_id"],
        how="left",
    )
    sales["price_rank"] = sales["price_rank"].fillna(0.5)

    segment_columns = customer_segments[["user_id", "segment"]].drop_duplicates("user_id")
    profile_columns = [
        "user_id",
        *[c for c in CUSTOMER_CONFOUNDER_COLUMNS if c in customer_profile],
    ]
    analysis_frame = sales.merge(segment_columns, on="user_id", how="left")
    analysis_frame = analysis_frame.merge(
        customer_profile[profile_columns].drop_duplicates("user_id"),
        on="user_id",
        how="left",
    )
    analysis_frame["segment"] = analysis_frame["segment"].fillna("未知群体")
    for column in BASE_CONFOUNDER_COLUMNS + CUSTOMER_CONFOUNDER_COLUMNS:
        if column not in analysis_frame.columns:
            analysis_frame[column] = 0.0
        analysis_frame[column] = pd.to_numeric(analysis_frame[column], errors="coerce").fillna(0.0)
    return analysis_frame.reset_index(drop=True)


def _cross_fit_residuals(
    analysis_frame: pd.DataFrame,
    treatment: np.ndarray,
    outcome: np.ndarray,
    n_folds: int,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray] | None:
    value_counts = pd.Series(treatment).value_counts()
    if len(value_counts) < 2:
        return None
    fold_count = min(n_folds, int(value_counts.min()), len(treatment))
    if fold_count < 2:
        return None

    feature_matrix = _build_feature_matrix(analysis_frame)
    residual_outcome = np.zeros(len(outcome), dtype=float)
    residual_treatment = np.zeros(len(treatment), dtype=float)
    splitter = StratifiedKFold(n_splits=fold_count, shuffle=True, random_state=random_state)

    for train_index, test_index in splitter.split(feature_matrix, treatment.astype(int)):
        outcome_model = GradientBoostingRegressor(
            n_estimators=80,
            learning_rate=0.05,
            max_depth=2,
            random_state=random_state,
        )
        treatment_model = GradientBoostingClassifier(
            n_estimators=80,
            learning_rate=0.05,
            max_depth=2,
            random_state=random_state,
        )
        outcome_model.fit(feature_matrix[train_index], outcome[train_index])
        treatment_model.fit(feature_matrix[train_index], treatment[train_index].astype(int))
        residual_outcome[test_index] = outcome[test_index] - outcome_model.predict(
            feature_matrix[test_index]
        )
        class_positions = np.where(treatment_model.classes_ == 1)[0]
        if len(class_positions) == 0:
            return None
        propensity = treatment_model.predict_proba(feature_matrix[test_index])[
            :, class_positions[0]
        ]
        residual_treatment[test_index] = treatment[test_index] - propensity

    if float(np.sum(residual_treatment**2)) <= EPS:
        return None
    return residual_treatment, residual_outcome


def _build_feature_matrix(analysis_frame: pd.DataFrame) -> np.ndarray:
    numeric_features = analysis_frame[
        BASE_CONFOUNDER_COLUMNS + CUSTOMER_CONFOUNDER_COLUMNS
    ].to_numpy(dtype=float)
    category_features = pd.get_dummies(
        analysis_frame["cat_l1_name"].fillna("未知"),
        prefix="cat_l1",
        dtype=float,
    ).to_numpy(dtype=float)
    return np.hstack([numeric_features, category_features])


def _build_effect_detail(
    analysis_frame: pd.DataFrame,
    treatment: np.ndarray,
    outcome: np.ndarray,
    residuals: tuple[np.ndarray, np.ndarray] | None,
    min_group_size: int,
) -> pd.DataFrame:
    rows = [
        _estimate_row(
            group_name="全体(ATE)",
            treatment=treatment,
            outcome=outcome,
            residuals=residuals,
            mask=np.ones(len(analysis_frame), dtype=bool),
        )
    ]
    for segment in sorted(analysis_frame["segment"].dropna().unique().tolist()):
        mask = analysis_frame["segment"].to_numpy() == segment
        if int(mask.sum()) < min_group_size:
            continue
        rows.append(
            _estimate_row(
                group_name=str(segment),
                treatment=treatment,
                outcome=outcome,
                residuals=residuals,
                mask=mask,
            )
        )
    return pd.DataFrame(rows, columns=EFFECT_DETAIL_COLUMNS)


def _estimate_row(
    group_name: str,
    treatment: np.ndarray,
    outcome: np.ndarray,
    residuals: tuple[np.ndarray, np.ndarray] | None,
    mask: np.ndarray,
) -> dict[str, float | int | str]:
    group_treatment = treatment[mask]
    group_outcome = outcome[mask]
    naive_effect = _naive_difference(group_treatment, group_outcome)
    method = "naive_fallback"
    theta = naive_effect
    standard_error = 0.0

    if residuals is not None and len(np.unique(group_treatment)) == 2:
        residual_treatment, residual_outcome = residuals
        theta_candidate, standard_error_candidate = _robinson_effect(
            residual_treatment[mask],
            residual_outcome[mask],
        )
        if theta_candidate is not None:
            theta = theta_candidate
            standard_error = standard_error_candidate
            method = "dml_cross_fit"

    ci_low = theta - 1.96 * standard_error
    ci_high = theta + 1.96 * standard_error
    return {
        "群体": group_name,
        "DML因果效应": round(float(theta), 6),
        "标准误": round(float(standard_error), 6),
        "95%CI下": round(float(ci_low), 6),
        "95%CI上": round(float(ci_high), 6),
        "样本数": int(mask.sum()),
        "朴素均值差": round(float(naive_effect), 6),
        "估计方法": method,
    }


def _robinson_effect(
    residual_treatment: np.ndarray,
    residual_outcome: np.ndarray,
) -> tuple[float, float] | tuple[None, None]:
    denominator = float(np.sum(residual_treatment**2))
    if denominator <= EPS:
        return None, None
    theta = float(np.sum(residual_treatment * residual_outcome) / denominator)
    influence = residual_treatment * (residual_outcome - theta * residual_treatment)
    sample_count = len(residual_treatment)
    denominator_mean = denominator / max(sample_count, 1)
    variance = np.mean(influence**2) / (denominator_mean**2 + EPS) / max(sample_count, 1)
    standard_error = math.sqrt(max(float(variance), 0.0))
    if not np.isfinite(theta) or not np.isfinite(standard_error):
        return None, None
    return theta, standard_error


def _build_promotion_response(
    analysis_frame: pd.DataFrame,
    effect_detail: pd.DataFrame,
) -> pd.DataFrame:
    effect_map = effect_detail[effect_detail["群体"] != "全体(ATE)"][
        ["群体", "DML因果效应", "95%CI下", "95%CI上", "估计方法"]
    ]
    rows: list[dict[str, float | int | str]] = []
    for segment, group_frame in analysis_frame.groupby("segment", dropna=False):
        promo_frame = group_frame[group_frame["is_promo"] == 1]
        nonpromo_frame = group_frame[group_frame["is_promo"] == 0]
        promo_mean = _safe_mean(promo_frame["amount"])
        nonpromo_mean = _safe_mean(nonpromo_frame["amount"])
        total_amount = float(group_frame["amount"].sum())
        promo_sales_share = (
            float(promo_frame["amount"].sum()) / total_amount if total_amount > EPS else 0.0
        )
        promo_lift = promo_mean / nonpromo_mean if abs(nonpromo_mean) > EPS else np.nan
        rows.append(
            {
                "群体": str(segment),
                "样本数": int(len(group_frame)),
                "促销笔数": int(len(promo_frame)),
                "非促销笔数": int(len(nonpromo_frame)),
                "促销笔均金额": round(promo_mean, 6),
                "非促销笔均金额": round(nonpromo_mean, 6),
                "朴素PromoLift": round(float(promo_lift), 6) if np.isfinite(promo_lift) else np.nan,
                "促销销售占比": round(promo_sales_share, 6),
            }
        )
    response = pd.DataFrame(rows)
    response = response.merge(effect_map, on="群体", how="left")
    return response[PROMOTION_RESPONSE_COLUMNS].sort_values("群体").reset_index(drop=True)


def _naive_difference(treatment: np.ndarray | pd.Series, outcome: np.ndarray | pd.Series) -> float:
    treatment_values = np.asarray(treatment, dtype=float)
    outcome_values = np.asarray(outcome, dtype=float)
    promo = outcome_values[treatment_values == 1]
    nonpromo = outcome_values[treatment_values == 0]
    if len(promo) == 0 or len(nonpromo) == 0:
        return 0.0
    return float(np.mean(promo) - np.mean(nonpromo))


def _safe_mean(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    return float(pd.to_numeric(series, errors="coerce").mean())
