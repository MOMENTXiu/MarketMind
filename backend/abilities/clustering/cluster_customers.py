"""Customer clustering ability."""

from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

CLUSTER_FEATURES = ["R_最近购买天数", "F_购买频次", "M_消费金额", "平均折扣", "客单价"]


def cluster_customers(dataset: pd.DataFrame, n_clusters: int = 4) -> dict[str, Any]:
    """Cluster customers from an explicit transaction dataset."""

    try:
        frame = dataset.copy()
        frame["订单日期"] = pd.to_datetime(frame["订单日期"])
        customer_data = calculate_rfm(frame)
        if len(customer_data) < 2:
            raise ValueError("数据量过少，无法进行聚类分析")

        features = customer_data[CLUSTER_FEATURES].values
        scaled_features = StandardScaler().fit_transform(features)
        best_k = (
            min(max(2, n_clusters), len(customer_data))
            if n_clusters
            else _find_optimal_k(scaled_features)
        )
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        customer_data["客户分群"] = kmeans.fit_predict(scaled_features)
        try:
            silhouette = round(
                float(silhouette_score(scaled_features, customer_data["客户分群"])), 4
            )
        except Exception:
            silhouette = 0.0

        return {
            "success": True,
            "message": "客户聚类完成",
            "data": {
                "total_customers": len(customer_data),
                "n_clusters": best_k,
                "silhouette_score": silhouette,
                "cluster_profiles": analyze_clusters(customer_data),
                "contribution": calculate_contribution(customer_data),
                "cluster_customers": get_cluster_customers(customer_data),
                "customer_rows": customer_data.to_dict(orient="records"),
            },
        }
    except Exception as exc:
        return {"success": False, "message": f"聚类分析失败: {exc}", "data": {}}


def calculate_rfm(dataset: pd.DataFrame) -> pd.DataFrame:
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
    return customer_data.replace([np.inf, -np.inf], np.nan).fillna(0)


def _find_optimal_k(scaled_features: np.ndarray) -> int:
    candidates = [k for k in range(2, 8) if k <= len(scaled_features)]
    if not candidates:
        return 2
    scores = []
    for candidate in candidates:
        model = KMeans(n_clusters=candidate, random_state=42, n_init=10)
        labels = model.fit_predict(scaled_features)
        scores.append(silhouette_score(scaled_features, labels))
    return candidates[int(np.argmax(scores))]


def analyze_clusters(customer_data: pd.DataFrame) -> list[dict[str, Any]]:
    profiles = (
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
    profiles.columns = ["客户数", "平均R", "平均F", "平均M", "平均利润", "平均折扣", "平均客单价"]
    return [
        {
            "cluster_id": int(index),
            "cluster_name": _cluster_name(row, profiles),
            "customer_count": int(row["客户数"]),
            "avg_recency": round(float(row["平均R"]), 2),
            "avg_frequency": round(float(row["平均F"]), 2),
            "avg_monetary": round(float(row["平均M"]), 2),
            "avg_profit": round(float(row["平均利润"]), 2),
            "avg_discount": round(float(row["平均折扣"]), 4),
            "avg_order_value": round(float(row["平均客单价"]), 2),
            "marketing_strategy": _marketing_strategy(_cluster_name(row, profiles)),
        }
        for index, row in profiles.iterrows()
    ]


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


def calculate_contribution(customer_data: pd.DataFrame) -> list[dict[str, Any]]:
    total_sales = customer_data["M_消费金额"].sum()
    total_profit = customer_data["总利润"].sum()
    contribution = customer_data.groupby("客户分群").agg({"M_消费金额": "sum", "总利润": "sum"})
    contribution["销售额占比"] = (contribution["M_消费金额"] / total_sales * 100).round(2)
    contribution["利润占比"] = (contribution["总利润"] / total_profit * 100).round(2)
    return [
        {
            "cluster_id": int(index),
            "total_sales": round(float(row["M_消费金额"]), 2),
            "total_profit": round(float(row["总利润"]), 2),
            "sales_percentage": round(float(row["销售额占比"]), 2),
            "profit_percentage": round(float(row["利润占比"]), 2),
        }
        for index, row in contribution.iterrows()
    ]


def get_cluster_customers(customer_data: pd.DataFrame) -> dict[int, list[dict[str, Any]]]:
    cluster_customers = {}
    for cluster_id in customer_data["客户分群"].unique():
        cluster_frame = customer_data[customer_data["客户分群"] == cluster_id].copy()
        cluster_frame = cluster_frame.sort_values("M_消费金额", ascending=False).head(20)
        cluster_customers[int(cluster_id)] = [
            {
                "customer_id": str(row["客户ID"]),
                "customer_name": str(row["客户ID"]),
                "avg_order_value": round(float(row["客单价"]), 2),
                "frequency": int(row["F_购买频次"]),
                "total_monetary": round(float(row["M_消费金额"]), 2),
                "recency_days": int(row["R_最近购买天数"]),
                "profit_margin": round(float(row["利润率"]), 2),
            }
            for _, row in cluster_frame.iterrows()
        ]
    return cluster_customers
