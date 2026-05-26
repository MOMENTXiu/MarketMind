"""Build Retail V2 marketer-side insight tables from pure ability inputs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.abilities.retail.estimate_customer_uplift import estimate_customer_uplift
from backend.abilities.retail.estimate_promotion_effect import estimate_promotion_effect
from backend.abilities.retail.rank_by_critic_topsis import critic_weights, topsis
from backend.core.errors import ValidationError

SEGMENT_VALUE_METRICS = [
    "群体总销售额",
    "人均消费金额",
    "购买频次",
    "复购率",
    "促销响应率",
    "流失风险",
]
SEGMENT_VALUE_COLUMNS = [
    "segment",
    "人数",
    "群体总销售额",
    "人均消费金额",
    "购买频次",
    "促销响应率",
    "最近购买间隔",
    "复购率",
    "流失风险",
    "营销价值得分",
    "价值排名",
    "销售贡献占比",
]
BUNDLE_STRATEGY_COLUMNS = [
    "组合",
    "项数",
    "支持度",
    "置信度",
    "提升度",
    "总效用",
    "篮均效用",
    "促销提升度",
    "跨类目数",
    "可触达篮数",
    "组合价值得分",
    "策略建议",
]
BUNDLE_METRICS = ["支持度", "置信度", "提升度", "总效用", "促销提升度", "可触达篮数"]
CATEGORY_STRATEGY_COLUMNS = [
    "大类",
    "销售贡献",
    "购买人数",
    "复购率",
    "促销依赖度",
    "增长率",
    "人均金额",
    "类目类型",
    "经营策略",
]
REQUIRED_SALES_COLUMNS = [
    "user_id",
    "cat_l1_name",
    "cat_l3_name",
    "cat_l3_code",
    "item_id",
    "amount",
    "unit_price",
    "is_promo",
    "is_return",
    "sale_month",
    "weekday",
    "is_weekend",
]
REQUIRED_PROFILE_COLUMNS = [
    "user_id",
    "M_消费金额",
    "F_购买频次",
    "R_最近购买间隔",
    "促销金额占比",
    "促销敏感度",
]
EPS = 1e-9


@dataclass(frozen=True)
class RetailMarketerInsights:
    """Structured marketer-side insight tables and ranking weights."""

    segment_value: pd.DataFrame
    bundle_strategy: pd.DataFrame
    promotion_response: pd.DataFrame
    promotion_effect_detail: pd.DataFrame
    customer_uplift: pd.DataFrame
    segment_uplift: pd.DataFrame
    category_strategy: pd.DataFrame
    weights: dict[str, dict[str, float]]


def build_marketer_insights(
    clean_sales: pd.DataFrame,
    customer_profile: pd.DataFrame,
    customer_segments: pd.DataFrame,
    high_utility_itemsets: pd.DataFrame | None = None,
    association_rules: pd.DataFrame | None = None,
    top_bundles: int = 20,
) -> RetailMarketerInsights:
    """Build marketer insight tables without file IO, plotting, or provider calls."""

    if top_bundles < 1:
        raise ValidationError("top_bundles must be positive")
    _validate_columns(clean_sales, REQUIRED_SALES_COLUMNS, "clean_sales")
    _validate_columns(customer_profile, REQUIRED_PROFILE_COLUMNS, "customer_profile")
    _validate_columns(customer_segments, ["user_id", "segment"], "customer_segments")

    positive_sales = _positive_sales(clean_sales)
    segment_value, segment_weights = _build_segment_value(customer_profile, customer_segments)
    bundle_strategy, bundle_weights = _build_bundle_strategy(
        positive_sales,
        high_utility_itemsets,
        association_rules,
        top_bundles,
    )
    promotion_effect = estimate_promotion_effect(clean_sales, customer_profile, customer_segments)
    customer_uplift = estimate_customer_uplift(
        customer_profile, customer_segments, promotion_effect
    )
    category_strategy = _build_category_strategy(positive_sales)

    return RetailMarketerInsights(
        segment_value=segment_value,
        bundle_strategy=bundle_strategy,
        promotion_response=promotion_effect.promotion_response,
        promotion_effect_detail=promotion_effect.effect_detail,
        customer_uplift=customer_uplift.customer_uplift,
        segment_uplift=customer_uplift.segment_uplift,
        category_strategy=category_strategy,
        weights={"segment_value": segment_weights, "bundle_strategy": bundle_weights},
    )


def _validate_columns(frame: pd.DataFrame, required: list[str], name: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValidationError(f"{name} missing required columns: {', '.join(missing)}")


def _positive_sales(clean_sales: pd.DataFrame) -> pd.DataFrame:
    positive_sales = clean_sales[clean_sales["is_return"] == 0].copy()
    if positive_sales.empty:
        raise ValidationError("Retail V2 marketer insights require positive sales rows")
    for column in ["amount", "unit_price", "is_promo", "sale_month"]:
        positive_sales[column] = pd.to_numeric(positive_sales[column], errors="coerce").fillna(0.0)
    return positive_sales


def _build_segment_value(
    customer_profile: pd.DataFrame,
    customer_segments: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float]]:
    profile = customer_profile[REQUIRED_PROFILE_COLUMNS].merge(
        customer_segments[["user_id", "segment"]].drop_duplicates("user_id"),
        on="user_id",
        how="left",
    )
    profile["segment"] = profile["segment"].fillna("未知群体")
    for column in REQUIRED_PROFILE_COLUMNS[1:]:
        profile[column] = pd.to_numeric(profile[column], errors="coerce").fillna(0.0)

    segment_value = profile.groupby("segment", as_index=False).agg(
        人数=("user_id", "size"),
        群体总销售额=("M_消费金额", "sum"),
        人均消费金额=("M_消费金额", "mean"),
        购买频次=("F_购买频次", "mean"),
        促销响应率=("促销金额占比", "mean"),
        最近购买间隔=("R_最近购买间隔", "mean"),
    )
    repeat_rate = profile.groupby("segment")["F_购买频次"].apply(
        lambda values: (values >= 2).mean()
    )
    segment_value["复购率"] = segment_value["segment"].map(repeat_rate).fillna(0.0)
    segment_value["流失风险"] = segment_value["最近购买间隔"]

    metric_matrix = segment_value[SEGMENT_VALUE_METRICS].to_numpy(dtype=float)
    weights, scores = _rank_matrix(metric_matrix, [True, True, True, True, True, False])
    segment_value["营销价值得分"] = scores.round(6)
    segment_value = segment_value.sort_values("营销价值得分", ascending=False).reset_index(
        drop=True
    )
    segment_value["价值排名"] = np.arange(1, len(segment_value) + 1)
    total_sales = float(segment_value["群体总销售额"].sum())
    segment_value["销售贡献占比"] = (
        segment_value["群体总销售额"] / total_sales if total_sales > EPS else 0.0
    ).round(6)
    weights_dict = dict(zip(SEGMENT_VALUE_METRICS, weights.round(6).astype(float)))
    return segment_value[SEGMENT_VALUE_COLUMNS], weights_dict


def _build_bundle_strategy(
    positive_sales: pd.DataFrame,
    high_utility_itemsets: pd.DataFrame | None,
    association_rules: pd.DataFrame | None,
    top_bundles: int,
) -> tuple[pd.DataFrame, dict[str, float]]:
    if high_utility_itemsets is None or high_utility_itemsets.empty:
        return pd.DataFrame(columns=BUNDLE_STRATEGY_COLUMNS), _equal_weights(BUNDLE_METRICS)
    _validate_columns(
        high_utility_itemsets,
        ["组合", "项数", "出现篮数", "支持度", "总效用", "篮均效用"],
        "high_utility_itemsets",
    )
    rule_map = _category_rule_map(association_rules)
    rows: list[dict[str, float | int | str]] = []
    for _, itemset in high_utility_itemsets.iterrows():
        items = [part.strip() for part in str(itemset["组合"]).split("+") if part.strip()]
        if not items:
            continue
        confidence, lift = _best_rule_strength(set(items), rule_map)
        related_sales = positive_sales[positive_sales["cat_l3_name"].isin(items)]
        promo_lift = _promotion_lift(related_sales)
        rows.append(
            {
                "组合": str(itemset["组合"]),
                "项数": int(itemset["项数"]),
                "支持度": float(itemset["支持度"]),
                "置信度": confidence,
                "提升度": lift,
                "总效用": float(itemset["总效用"]),
                "篮均效用": float(itemset["篮均效用"]),
                "促销提升度": promo_lift,
                "跨类目数": int(related_sales["cat_l1_name"].nunique()),
                "可触达篮数": int(itemset["出现篮数"]),
            }
        )
    if not rows:
        return pd.DataFrame(columns=BUNDLE_STRATEGY_COLUMNS), _equal_weights(BUNDLE_METRICS)

    bundle_strategy = pd.DataFrame(rows)
    metric_matrix = bundle_strategy[BUNDLE_METRICS].to_numpy(dtype=float)
    weights, scores = _rank_matrix(metric_matrix, [True] * len(BUNDLE_METRICS))
    bundle_strategy["组合价值得分"] = scores.round(6)
    bundle_strategy["策略建议"] = bundle_strategy.apply(_bundle_strategy_label, axis=1)
    bundle_strategy = bundle_strategy.sort_values("组合价值得分", ascending=False).head(top_bundles)
    weights_dict = dict(zip(BUNDLE_METRICS, weights.round(6).astype(float)))
    return bundle_strategy[BUNDLE_STRATEGY_COLUMNS].reset_index(drop=True), weights_dict


def _category_rule_map(
    association_rules: pd.DataFrame | None,
) -> dict[frozenset[str], list[tuple[float, float]]]:
    if association_rules is None or association_rules.empty:
        return {}
    _validate_columns(
        association_rules, ["层级", "前项", "后项", "置信度", "提升度"], "association_rules"
    )
    rule_map: dict[frozenset[str], list[tuple[float, float]]] = {}
    l3_rules = association_rules[association_rules["层级"] == "小类级"]
    for _, rule in l3_rules.iterrows():
        antecedents = [part.strip() for part in str(rule["前项"]).split("+") if part.strip()]
        key = frozenset([*antecedents, str(rule["后项"]).strip()])
        rule_map.setdefault(key, []).append((float(rule["置信度"]), float(rule["提升度"])))
    return rule_map


def _best_rule_strength(
    itemset: set[str],
    rule_map: dict[frozenset[str], list[tuple[float, float]]],
) -> tuple[float, float]:
    best_confidence = 0.3
    best_lift = 1.2
    for rule_items, strengths in rule_map.items():
        if not itemset.issubset(rule_items) and not rule_items.issubset(itemset):
            continue
        for confidence, lift in strengths:
            if lift > best_lift:
                best_confidence = confidence
                best_lift = lift
    return round(best_confidence, 6), round(best_lift, 6)


def _promotion_lift(related_sales: pd.DataFrame) -> float:
    if related_sales.empty:
        return 1.0
    promo_mean = related_sales[related_sales["is_promo"] == 1]["amount"].mean()
    nonpromo_mean = related_sales[related_sales["is_promo"] == 0]["amount"].mean()
    if pd.isna(promo_mean) or pd.isna(nonpromo_mean) or abs(float(nonpromo_mean)) <= EPS:
        return 1.0
    return round(float(promo_mean / nonpromo_mean), 6)


def _bundle_strategy_label(row: pd.Series) -> str:
    if int(row["跨类目数"]) >= 2:
        return "跨品类联动·第二件折扣"
    if float(row["促销提升度"]) > 1.1:
        return "满减组合·捆绑促销"
    return "联动陈列·常购组合"


def _build_category_strategy(positive_sales: pd.DataFrame) -> pd.DataFrame:
    total_sales = float(positive_sales["amount"].sum())
    rows: list[dict[str, float | int | str]] = []
    for category_name, category_sales in positive_sales.groupby("cat_l1_name"):
        sales_amount = float(category_sales["amount"].sum())
        buyers = int(category_sales["user_id"].nunique())
        repeat_rate = float((category_sales.groupby("user_id").size() >= 2).mean())
        promo_dependency = (
            float(category_sales[category_sales["is_promo"] == 1]["amount"].sum()) / sales_amount
            if sales_amount > EPS
            else 0.0
        )
        month_sales = category_sales.groupby("sale_month")["amount"].sum().sort_index()
        growth = _month_growth(month_sales)
        rows.append(
            {
                "大类": str(category_name),
                "销售贡献": sales_amount / total_sales if total_sales > EPS else 0.0,
                "购买人数": buyers,
                "复购率": repeat_rate,
                "促销依赖度": promo_dependency,
                "增长率": growth,
                "人均金额": sales_amount / buyers if buyers > 0 else 0.0,
            }
        )
    category_strategy = pd.DataFrame(rows)
    if category_strategy.empty:
        return pd.DataFrame(columns=CATEGORY_STRATEGY_COLUMNS)
    category_strategy = category_strategy.sort_values("销售贡献", ascending=False).reset_index(
        drop=True
    )
    category_strategy["类目类型"] = category_strategy.apply(
        _category_type, axis=1, frame=category_strategy
    )
    strategy_map = {
        "核心稳定类目": "保供应·会员权益",
        "增长潜力类目": "增曝光·交叉推荐",
        "促销依赖类目": "控促销成本·提毛利",
        "高价值低频类目": "精准推荐·场景营销",
        "长尾弱势类目": "打包清理·降库存",
    }
    category_strategy["经营策略"] = category_strategy["类目类型"].map(strategy_map)
    for column in ["销售贡献", "复购率", "促销依赖度", "增长率", "人均金额"]:
        category_strategy[column] = category_strategy[column].round(6)
    return category_strategy[CATEGORY_STRATEGY_COLUMNS]


def _month_growth(month_sales: pd.Series) -> float:
    if len(month_sales) < 2:
        return 0.0
    first_value = float(month_sales.iloc[0])
    last_value = float(month_sales.iloc[-1])
    if first_value <= EPS:
        return 0.0
    return float((last_value - first_value) / first_value)


def _category_type(row: pd.Series, frame: pd.DataFrame) -> str:
    median_contribution = float(frame["销售贡献"].median())
    median_repeat = float(frame["复购率"].median())
    median_amount = float(frame["人均金额"].median())
    if float(row["促销依赖度"]) >= 0.30:
        return "促销依赖类目"
    if float(row["增长率"]) >= 0.10 and float(row["销售贡献"]) < median_contribution:
        return "增长潜力类目"
    if float(row["销售贡献"]) >= median_contribution and float(row["复购率"]) >= median_repeat:
        return "核心稳定类目"
    if float(row["人均金额"]) >= median_amount and float(row["复购率"]) < median_repeat:
        return "高价值低频类目"
    return "长尾弱势类目"


def _rank_matrix(matrix: np.ndarray, benefit: list[bool]) -> tuple[np.ndarray, np.ndarray]:
    if matrix.shape[0] < 2:
        return np.ones(matrix.shape[1], dtype=float) / matrix.shape[1], np.ones(matrix.shape[0])
    variable_mask = np.nanstd(matrix, axis=0) > 1e-12
    if not variable_mask.any():
        return np.ones(matrix.shape[1], dtype=float) / matrix.shape[1], np.ones(matrix.shape[0])

    variable_matrix = matrix[:, variable_mask]
    variable_benefit = [flag for flag, keep in zip(benefit, variable_mask) if keep]
    variable_weights, _ = critic_weights(variable_matrix, variable_benefit)
    scores, _ = topsis(variable_matrix, variable_weights, variable_benefit)
    weights = np.zeros(matrix.shape[1], dtype=float)
    weights[variable_mask] = variable_weights
    return weights, scores


def _equal_weights(metrics: list[str]) -> dict[str, float]:
    return {metric: round(1.0 / len(metrics), 6) for metric in metrics}
