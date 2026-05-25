"""Recommendation model build ability."""

from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

CLUSTER_FEATURES = ["R_最近购买天数", "F_购买频次", "M_消费金额", "平均折扣", "客单价"]


def build_recommendation_model(
    dataset: pd.DataFrame,
    association_rules: list[Any] | None = None,
    n_clusters: int = 4,
) -> dict[str, Any]:
    """Build recommendation model data without filesystem side effects."""

    try:
        frame = _preprocess_dataset(dataset.copy())
        customer_data = _calculate_customer_features(frame)
        if len(customer_data) < 2:
            raise ValueError("数据量过少，无法构建推荐模型")

        best_k = min(max(2, n_clusters), len(customer_data))
        kmeans_model, cluster_scaler = _perform_clustering(customer_data, best_k)
        cluster_profiles = _generate_cluster_profiles(customer_data)
        cluster_contribution = _calculate_cluster_contribution(customer_data)
        rules_single = _process_association_rules(association_rules)
        model_data = {
            "kmeans_model": kmeans_model,
            "cluster_scaler": cluster_scaler,
            "best_k": best_k,
            "cluster_features": CLUSTER_FEATURES,
            "cluster_profiles": cluster_profiles,
            "cluster_contribution": cluster_contribution,
            "customer_data": customer_data,
            "rules_single": rules_single,
            "feature_stats": _extract_feature_stats(customer_data),
            "reference_date": customer_data["参考日期"].iloc[0],
            "categories": _unique_values(frame, "类别"),
            "subcategories": _unique_values(frame, "子类别"),
            "regions": _unique_values(frame, "地区"),
            "segments": _unique_values(frame, "细分"),
        }
        return {
            "success": True,
            "model_data": model_data,
            "total_customers": len(customer_data),
            "n_clusters": best_k,
            "n_rules": len(rules_single),
            "n_subcategories": len(model_data["subcategories"]),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "model_data": {}}


def _preprocess_dataset(dataset: pd.DataFrame) -> pd.DataFrame:
    dataset["订单日期"] = pd.to_datetime(dataset["订单日期"])
    for column in ["销售额", "数量", "折扣", "利润"]:
        if column in dataset.columns:
            dataset[column] = pd.to_numeric(dataset[column], errors="coerce")
    return dataset


def _calculate_customer_features(dataset: pd.DataFrame) -> pd.DataFrame:
    reference_date = dataset["订单日期"].max() + timedelta(days=1)
    customer_data = (
        dataset.groupby("客户 ID")
        .agg(
            {
                "订单日期": lambda value: (reference_date - value.max()).days,
                "订单 ID": "nunique",
                "销售额": "sum",
                "利润": "sum",
                "数量": "sum",
                "折扣": "mean",
                "细分": "first" if "细分" in dataset.columns else lambda value: "未知",
                "地区": "first" if "地区" in dataset.columns else lambda value: "未知",
            }
        )
        .reset_index()
    )
    customer_data.columns = [
        "客户ID",
        "R_最近购买天数",
        "F_购买频次",
        "M_消费金额",
        "总利润",
        "购买数量",
        "平均折扣",
        "客户细分",
        "地区",
    ]
    customer_data["客单价"] = customer_data["M_消费金额"] / customer_data["F_购买频次"].replace(
        0, np.nan
    )
    customer_data["件单价"] = customer_data["M_消费金额"] / customer_data["购买数量"].replace(
        0, np.nan
    )
    customer_data["利润率"] = (
        customer_data["总利润"] / customer_data["M_消费金额"].replace(0, np.nan) * 100
    )
    customer_data = customer_data.replace([np.inf, -np.inf], np.nan).fillna(0)
    customer_data["参考日期"] = reference_date
    return customer_data


def _perform_clustering(
    customer_data: pd.DataFrame, n_clusters: int
) -> tuple[KMeans, StandardScaler]:
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(customer_data[CLUSTER_FEATURES].values)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    customer_data["客户分群"] = kmeans.fit_predict(scaled_features)
    return kmeans, scaler


def _generate_cluster_profiles(customer_data: pd.DataFrame) -> pd.DataFrame:
    cluster_profiles = (
        customer_data.groupby("客户分群")
        .agg(
            {
                "客户ID": "count",
                "R_最近购买天数": "mean",
                "F_购买频次": "mean",
                "M_消费金额": "mean",
                "总利润": "mean",
                "平均折扣": "mean",
                "客单价": "mean",
            }
        )
        .round(2)
    )
    cluster_profiles.columns = [
        "客户数",
        "平均R",
        "平均F",
        "平均M",
        "平均利润",
        "平均折扣",
        "平均客单价",
    ]
    profile_rows = cluster_profiles.reset_index()
    names = [_cluster_name(row, profile_rows) for _, row in profile_rows.iterrows()]
    cluster_profiles["群体名称"] = names
    cluster_profiles["营销策略"] = [_marketing_strategy(name) for name in names]
    return cluster_profiles


def _cluster_name(row: pd.Series, profiles: pd.DataFrame) -> str:
    recency_median = profiles["平均R"].median()
    monetary_median = profiles["平均M"].median()
    if row["平均R"] < recency_median and row["平均M"] > monetary_median:
        return "高价值活跃客户"
    if row["平均R"] < recency_median and row["平均M"] <= monetary_median:
        return "普通活跃客户"
    if row["平均R"] >= recency_median and row["平均M"] > monetary_median:
        return "高价值流失预警"
    return "低价值流失客户"


def _marketing_strategy(name: str) -> str:
    return {
        "高价值活跃客户": "VIP专属优惠、会员积分加倍、新品优先体验、专属客服",
        "普通活跃客户": "满减优惠券、推荐升级产品、交叉销售、积分兑换活动",
        "高价值流失预警": "召回优惠券、专属折扣、限时特惠、电话回访关怀",
        "低价值流失客户": "大额满减券、限时秒杀、清仓特价、短信推送唤醒",
    }.get(name, "常规营销活动")


def _calculate_cluster_contribution(customer_data: pd.DataFrame) -> list[dict[str, Any]]:
    total_sales = customer_data["M_消费金额"].sum()
    total_profit = customer_data["总利润"].sum()
    contribution = customer_data.groupby("客户分群").agg({"M_消费金额": "sum", "总利润": "sum"})
    contribution["销售额占比"] = (contribution["M_消费金额"] / total_sales * 100).round(2)
    contribution["利润占比"] = (contribution["总利润"] / total_profit * 100).round(2)
    return [
        {
            "cluster_id": int(index),
            "total_sales": float(row["M_消费金额"]),
            "total_profit": float(row["总利润"]),
            "sales_percentage": float(row["销售额占比"]),
            "profit_percentage": float(row["利润占比"]),
        }
        for index, row in contribution.iterrows()
    ]


def _extract_feature_stats(customer_data: pd.DataFrame) -> dict[str, dict[str, float]]:
    stats = {}
    for column in CLUSTER_FEATURES:
        stats[column] = {
            "mean": float(customer_data[column].mean()),
            "std": float(customer_data[column].std()),
            "min": float(customer_data[column].min()),
            "max": float(customer_data[column].max()),
        }
    return stats


def _process_association_rules(association_rules: list[Any] | None) -> pd.DataFrame:
    if not association_rules:
        return pd.DataFrame()

    rows = []
    for rule in association_rules:
        if not hasattr(rule, "consequent") or not rule.consequent:
            continue
        rows.append(
            {
                "antecedents": frozenset(rule.antecedents),
                "consequents": frozenset([rule.consequent]),
                "support": rule.support,
                "confidence": rule.confidence,
                "lift": rule.lift,
                "后项商品": rule.consequent,
            }
        )
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _unique_values(dataset: pd.DataFrame, column: str) -> list[Any]:
    return dataset[column].unique().tolist() if column in dataset.columns else []
