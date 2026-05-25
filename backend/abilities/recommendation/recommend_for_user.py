"""User recommendation ability."""

from typing import Any

import numpy as np
import pandas as pd


def recommend_for_user(
    dataset: pd.DataFrame,
    model_data: dict[str, Any] | None,
    user_id: str,
    top_n: int = 10,
) -> dict[str, Any]:
    """Recommend products for a user from explicit data and optional model data."""

    frame = _preprocess_dataset(dataset.copy())
    product_stats = _build_product_stats(frame, model_data)
    if not model_data:
        return _fallback_recommendation(product_stats, top_n)

    customer_data = model_data["customer_data"]
    row = customer_data[customer_data["客户ID"] == user_id]
    if row.empty:
        return {"recommends": [], "cluster": None}

    row = row.iloc[0]
    frequency = row.get("F_购买频次")
    monetary = row.get("M_消费金额")
    discount = row.get(
        "平均折扣", model_data.get("feature_stats", {}).get("平均折扣", {}).get("mean", 0.0)
    )
    avg_order_value = monetary / frequency if frequency else 0
    user_features = np.array(
        [[row.get("R_最近购买天数"), frequency, monetary, discount, avg_order_value]]
    )
    user_features_scaled = model_data["cluster_scaler"].transform(user_features)
    predicted_cluster = int(model_data["kmeans_model"].predict(user_features_scaled)[0])
    cluster_profiles = model_data["cluster_profiles"]
    cluster_name = cluster_profiles.loc[predicted_cluster, "群体名称"]

    product_cluster_stats = _build_product_cluster_stats(frame, model_data)
    cluster_pref = product_cluster_stats[product_cluster_stats["分群名称"] == cluster_name].copy()
    if cluster_pref.empty:
        cluster_pref = (
            product_cluster_stats.groupby("子类别")
            .agg({"购买客户数": "sum", "销售额": "sum"})
            .reset_index()
        )
        cluster_pref["分群名称"] = "全局"

    total_sales = cluster_pref["销售额"].sum() or 1
    cluster_pref["群体偏好度"] = cluster_pref["销售额"] / total_sales
    recommendations = product_stats.merge(
        cluster_pref[["子类别", "群体偏好度", "购买客户数"]].rename(
            columns={"购买客户数": "群体购买数"}
        ),
        on="子类别",
        how="left",
    ).fillna(0)
    max_pref = recommendations["群体偏好度"].max() or 1
    recommendations["推荐分数"] = recommendations["群体偏好度"] / max_pref
    recommendations = recommendations.sort_values("推荐分数", ascending=False).head(top_n)
    recommends = [
        {
            "item": row["子类别"],
            "category": row["所属类别"],
            "score": float(row["推荐分数"]),
            "avg_price": float(row["平均销售额"]),
            "reason": f"{cluster_name}偏好度 {row['群体偏好度']:.1%}",
        }
        for _, row in recommendations.iterrows()
    ]
    cluster = {
        "cluster_id": predicted_cluster,
        "cluster_name": cluster_name,
        "strategy": cluster_profiles.loc[predicted_cluster, "营销策略"],
    }
    return {"recommends": recommends, "cluster": cluster}


def _preprocess_dataset(dataset: pd.DataFrame) -> pd.DataFrame:
    dataset["订单日期"] = pd.to_datetime(dataset["订单日期"])
    for column in ["销售额", "数量", "折扣", "利润"]:
        if column in dataset.columns:
            dataset[column] = pd.to_numeric(dataset[column], errors="coerce")
    return dataset


def _build_product_stats(dataset: pd.DataFrame, model_data: dict[str, Any] | None) -> pd.DataFrame:
    frame = dataset.copy()
    if model_data:
        customer_cluster_map = model_data["customer_data"].set_index("客户ID")["客户分群"].to_dict()
        frame["客户分群"] = frame["客户 ID"].map(customer_cluster_map)
        cluster_name_map = model_data["cluster_profiles"]["群体名称"].to_dict()
        frame["分群名称"] = frame["客户分群"].map(cluster_name_map)
    stats = (
        frame.groupby("子类别")
        .agg({"销售额": ["sum", "mean"], "利润": "sum", "客户 ID": "nunique", "类别": "first"})
        .reset_index()
    )
    stats.columns = ["子类别", "总销售额", "平均销售额", "总利润", "购买客户数", "所属类别"]
    stats["利润率"] = stats["总利润"] / stats["总销售额"] * 100
    return stats


def _build_product_cluster_stats(dataset: pd.DataFrame, model_data: dict[str, Any]) -> pd.DataFrame:
    frame = dataset.copy()
    customer_cluster_map = model_data["customer_data"].set_index("客户ID")["客户分群"].to_dict()
    frame["客户分群"] = frame["客户 ID"].map(customer_cluster_map)
    cluster_name_map = model_data["cluster_profiles"]["群体名称"].to_dict()
    frame["分群名称"] = frame["客户分群"].map(cluster_name_map)
    stats = (
        frame.groupby(["子类别", "分群名称"])
        .agg({"客户 ID": "nunique", "销售额": "sum", "数量": "sum"})
        .reset_index()
    )
    stats.columns = ["子类别", "分群名称", "购买客户数", "销售额", "销量"]
    return stats


def _fallback_recommendation(product_stats: pd.DataFrame, top_n: int) -> dict[str, Any]:
    top_products = product_stats.sort_values("总销售额", ascending=False).head(top_n)
    recommends = [
        {
            "item": row["子类别"],
            "category": row["所属类别"],
            "score": 0.5,
            "avg_price": float(row["平均销售额"]),
            "reason": f"热门商品（销售额 {row['总销售额']:.0f}）",
        }
        for _, row in top_products.iterrows()
    ]
    return {
        "recommends": recommends,
        "cluster": {
            "cluster_id": -1,
            "cluster_name": "未分类",
            "strategy": "基于热门商品推荐（模型未加载）",
        },
    }
