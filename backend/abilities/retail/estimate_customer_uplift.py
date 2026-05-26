"""Rank Retail V2 customers for promotion uplift targeting."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.abilities.retail.estimate_promotion_effect import PromotionEffectResult
from backend.core.errors import ValidationError

REQUIRED_PROFILE_COLUMNS = [
    "user_id",
    "M_消费金额",
    "F_购买频次",
    "促销敏感度",
    "R_最近购买间隔",
]
CUSTOMER_UPLIFT_COLUMNS = [
    "user_id",
    "segment",
    "segment_effect",
    "促销敏感度",
    "M_消费金额",
    "F_购买频次",
    "R_最近购买间隔",
    "expected_incremental_amount",
    "uplift_score",
    "uplift_rank",
    "target_priority",
]
SEGMENT_UPLIFT_COLUMNS = [
    "segment",
    "客户数",
    "平均uplift_score",
    "平均预期增量",
    "segment_effect",
    "高优先级客户数",
]


@dataclass(frozen=True)
class CustomerUpliftResult:
    """Customer-level and segment-level uplift targeting tables."""

    customer_uplift: pd.DataFrame
    segment_uplift: pd.DataFrame


def estimate_customer_uplift(
    customer_profile: pd.DataFrame,
    customer_segments: pd.DataFrame,
    promotion_effect: PromotionEffectResult,
    top_k: int | None = None,
) -> CustomerUpliftResult:
    """Rank customers by expected incremental promotion response."""

    if top_k is not None and top_k < 1:
        raise ValidationError("top_k must be positive when provided")
    _validate_columns(customer_profile, REQUIRED_PROFILE_COLUMNS, "customer_profile")
    _validate_columns(customer_segments, ["user_id", "segment"], "customer_segments")
    if promotion_effect is None:
        raise ValidationError("promotion_effect is required")

    uplift_frame = _build_uplift_frame(customer_profile, customer_segments, promotion_effect)
    customer_uplift = _score_customer_uplift(uplift_frame)
    segment_uplift = _aggregate_segment_uplift(customer_uplift)
    if top_k is not None:
        customer_uplift = customer_uplift.head(top_k).reset_index(drop=True)
    return CustomerUpliftResult(
        customer_uplift=customer_uplift[CUSTOMER_UPLIFT_COLUMNS],
        segment_uplift=segment_uplift[SEGMENT_UPLIFT_COLUMNS],
    )


def _validate_columns(frame: pd.DataFrame, required: list[str], name: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValidationError(f"{name} missing required columns: {', '.join(missing)}")


def _build_uplift_frame(
    customer_profile: pd.DataFrame,
    customer_segments: pd.DataFrame,
    promotion_effect: PromotionEffectResult,
) -> pd.DataFrame:
    segment_effects = _segment_effect_map(promotion_effect)
    overall_effect = float(promotion_effect.overall_effect.get("theta", promotion_effect.naive_ate))
    segment_columns = customer_segments[["user_id", "segment"]].drop_duplicates("user_id")
    uplift_frame = customer_profile[REQUIRED_PROFILE_COLUMNS].merge(
        segment_columns,
        on="user_id",
        how="left",
    )
    uplift_frame["segment"] = uplift_frame["segment"].fillna("未知群体")
    for column in REQUIRED_PROFILE_COLUMNS[1:]:
        uplift_frame[column] = pd.to_numeric(uplift_frame[column], errors="coerce").fillna(0.0)
    uplift_frame["segment_effect"] = (
        uplift_frame["segment"].map(segment_effects).fillna(overall_effect)
    )
    uplift_frame["expected_incremental_amount"] = (
        uplift_frame["segment_effect"] * uplift_frame["促销敏感度"]
    )
    return uplift_frame


def _segment_effect_map(promotion_effect: PromotionEffectResult) -> dict[str, float]:
    if promotion_effect.effect_detail.empty:
        return {}
    detail = promotion_effect.effect_detail[promotion_effect.effect_detail["群体"] != "全体(ATE)"]
    return {
        str(row["群体"]): float(row["DML因果效应"])
        for _, row in detail.iterrows()
        if pd.notna(row["DML因果效应"])
    }


def _score_customer_uplift(uplift_frame: pd.DataFrame) -> pd.DataFrame:
    scored = uplift_frame.copy()
    value_signal = 0.65 * _normalize(np.log1p(scored["M_消费金额"].clip(lower=0)))
    value_signal += 0.35 * _normalize(scored["F_购买频次"].clip(lower=0))
    scored["uplift_score"] = (
        0.35 * _normalize(scored["segment_effect"].clip(lower=0))
        + 0.25 * _normalize(scored["促销敏感度"].clip(lower=0))
        + 0.25 * value_signal
        + 0.15 * _normalize(scored["R_最近购买间隔"].clip(lower=0))
    )
    scored = scored.sort_values(
        ["uplift_score", "expected_incremental_amount", "user_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    scored["uplift_rank"] = np.arange(1, len(scored) + 1)
    high_cutoff = max(1, math.ceil(len(scored) * 0.20))
    medium_cutoff = max(high_cutoff, math.ceil(len(scored) * 0.50))
    scored["target_priority"] = scored["uplift_rank"].apply(
        lambda rank: "高优先级"
        if rank <= high_cutoff
        else "中优先级"
        if rank <= medium_cutoff
        else "低优先级"
    )
    scored["segment_effect"] = scored["segment_effect"].round(6)
    scored["expected_incremental_amount"] = scored["expected_incremental_amount"].round(6)
    scored["uplift_score"] = scored["uplift_score"].round(6)
    return scored


def _aggregate_segment_uplift(customer_uplift: pd.DataFrame) -> pd.DataFrame:
    if customer_uplift.empty:
        return pd.DataFrame(columns=SEGMENT_UPLIFT_COLUMNS)
    grouped = customer_uplift.groupby("segment", as_index=False).agg(
        客户数=("user_id", "size"),
        平均uplift_score=("uplift_score", "mean"),
        平均预期增量=("expected_incremental_amount", "mean"),
        segment_effect=("segment_effect", "mean"),
        高优先级客户数=("target_priority", lambda values: int((values == "高优先级").sum())),
    )
    grouped["平均uplift_score"] = grouped["平均uplift_score"].round(6)
    grouped["平均预期增量"] = grouped["平均预期增量"].round(6)
    grouped["segment_effect"] = grouped["segment_effect"].round(6)
    return grouped.sort_values("平均uplift_score", ascending=False).reset_index(drop=True)


def _normalize(values: pd.Series | np.ndarray) -> pd.Series:
    series = pd.Series(values, dtype=float)
    value_range = float(series.max() - series.min())
    if not np.isfinite(value_range) or value_range <= 1e-12:
        return pd.Series(np.zeros(len(series)), index=series.index, dtype=float)
    return (series - float(series.min())) / value_range
