"""
推荐系统服务 - 复用预训练的 model_data.pkl
"""
import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from backend.services.tts_service import TTSService


def _find_dataset_path() -> Path:
    candidates = [
        Path("data/dataset.csv"),
        Path("analysis/dataset.csv"),
        Path("dataset.csv"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


MODEL_PATH = Path("backend/data/model_data.pkl")
DATA_PATH = _find_dataset_path()


class RecommendationSystem:
    """
    智能推荐系统
    直接加载 marketing_modeling.py 训练并保存的模型：
    - KMeans聚类模型
    - StandardScaler标准化器
    - 关联规则
    - 客户分群结果
    """

    def __init__(self, model_path: str = str(MODEL_PATH), data_path: str = str(DATA_PATH)):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件 '{model_path}' 不存在！请先生成 model_data.pkl。")

        self._load_model(model_path)
        self.df = pd.read_csv(data_path, encoding="utf-8")
        self._preprocess_data()
        self._build_product_stats()

    def _load_model(self, model_path):
        with open(model_path, "rb") as f:
            model_data = pickle.load(f)

        self.kmeans_model = model_data["kmeans_model"]
        self.cluster_scaler = model_data["cluster_scaler"]
        self.best_k = model_data["best_k"]
        self.cluster_features = model_data["cluster_features"]
        self.cluster_profiles = model_data["cluster_profiles"]
        self.cluster_contribution = model_data["cluster_contribution"]
        self.customer_data = model_data["customer_data"]
        self.rules_single = model_data["rules_single"]
        self.feature_stats = model_data["feature_stats"]
        self.reference_date = model_data["reference_date"]
        self.categories = model_data["categories"]
        self.subcategories = model_data["subcategories"]
        self.regions = model_data["regions"]
        self.segments = model_data["segments"]

    def _preprocess_data(self):
        self.df["订单日期"] = pd.to_datetime(self.df["订单日期"])
        num_cols = ["销售额", "数量", "折扣", "利润"]
        for c in num_cols:
            self.df[c] = pd.to_numeric(self.df[c], errors="coerce")

    def _build_product_stats(self):
        customer_cluster_map = self.customer_data.set_index("客户ID")["客户分群"].to_dict()
        self.df["客户分群"] = self.df["客户 ID"].map(customer_cluster_map)
        cluster_name_map = self.cluster_profiles["群体名称"].to_dict()
        self.df["分群名称"] = self.df["客户分群"].map(cluster_name_map)

        self.product_cluster_stats = self.df.groupby(["子类别", "分群名称"]).agg(
            {"客户 ID": "nunique", "销售额": "sum", "数量": "sum"}
        ).reset_index()
        self.product_cluster_stats.columns = ["子类别", "分群名称", "购买客户数", "销售额", "销量"]

        self.product_stats = self.df.groupby("子类别").agg(
            {"销售额": ["sum", "mean"], "利润": "sum", "客户 ID": "nunique", "类别": "first"}
        ).reset_index()
        self.product_stats.columns = ["子类别", "总销售额", "平均销售额", "总利润", "购买客户数", "所属类别"]
        self.product_stats["利润率"] = self.product_stats["总利润"] / self.product_stats["总销售额"] * 100

    # ---------- 对外推荐方法 ----------
    def recommend_user(self, user_id: str, top_n: int = 10) -> Dict:
        """根据用户ID推荐商品"""
        row = self.customer_data[self.customer_data["客户ID"] == user_id]
        if row.empty:
            return {"recommends": [], "cluster": None}

        row = row.iloc[0]
        R = row.get("R_最近购买天数")
        F = row.get("F_购买频次")
        M = row.get("M_消费金额")
        discount = row.get("平均折扣", self.feature_stats.get("平均折扣", {}).get("mean", 0.0))

        # 计算客单价
        avg_order_value = M / F if F else 0
        user_features = np.array([[R, F, M, discount, avg_order_value]])
        user_features_scaled = self.cluster_scaler.transform(user_features)
        predicted_cluster = int(self.kmeans_model.predict(user_features_scaled)[0])
        cluster_name = self.cluster_profiles.loc[predicted_cluster, "群体名称"]

        cluster_pref = self.product_cluster_stats[self.product_cluster_stats["分群名称"] == cluster_name].copy()
        if len(cluster_pref) == 0:
            cluster_pref = self.product_cluster_stats.groupby("子类别").agg(
                {"购买客户数": "sum", "销售额": "sum"}
            ).reset_index()
            cluster_pref["分群名称"] = "全局"

        total_sales = cluster_pref["销售额"].sum() or 1
        cluster_pref["群体偏好度"] = cluster_pref["销售额"] / total_sales

        recommendations = self.product_stats.merge(
            cluster_pref[["子类别", "群体偏好度", "购买客户数"]].rename(
                columns={"购买客户数": "群体购买数"}
            ),
            on="子类别",
            how="left",
        ).fillna(0)

        max_pref = recommendations["群体偏好度"].max() or 1
        recommendations["推荐分数"] = recommendations["群体偏好度"] / max_pref
        recommendations = recommendations.sort_values("推荐分数", ascending=False).head(top_n)
        recommends = []
        for _, r in recommendations.iterrows():
            recommends.append(
                {
                    "item": r["子类别"],
                    "category": r["所属类别"],
                    "score": float(r["推荐分数"]),
                    "avg_price": float(r["平均销售额"]),
                    "reason": f"{cluster_name}偏好度 {r['群体偏好度']:.1%}",
                }
            )

        cluster_info = {
            "cluster_id": predicted_cluster,
            "cluster_name": cluster_name,
            "strategy": self.cluster_profiles.loc[predicted_cluster, "营销策略"],
        }

        return {"recommends": recommends, "cluster": cluster_info}

    def recommend_item(self, item_name: str, top_n: int = 5) -> Dict:
        """根据商品名称推荐目标客户群"""
        if item_name not in self.subcategories:
            return {"targets": []}

        # 群体购买统计
        cluster_stats = self.product_cluster_stats[self.product_cluster_stats["子类别"] == item_name].copy()
        if cluster_stats.empty:
            return {"targets": []}

        total_buyers = cluster_stats["购买客户数"].sum() or 1
        cluster_stats["购买占比"] = cluster_stats["购买客户数"] / total_buyers * 100

        total_customers = len(self.customer_data)
        cluster_sizes = self.cluster_profiles["客户数"].to_dict()
        cluster_stats["群体规模"] = cluster_stats["分群名称"].map(
            {self.cluster_profiles.loc[k, "群体名称"]: v for k, v in cluster_sizes.items()}
        )
        cluster_stats["群体占比"] = cluster_stats["群体规模"] / total_customers * 100
        cluster_stats["购买倾向指数"] = cluster_stats["购买占比"] / cluster_stats["群体占比"]

        strategy_map = self.cluster_profiles.set_index("群体名称")["营销策略"].to_dict()
        cluster_stats["营销策略"] = cluster_stats["分群名称"].map(strategy_map)

        cluster_stats = cluster_stats.sort_values("购买倾向指数", ascending=False).head(top_n)
        targets = []
        for _, r in cluster_stats.iterrows():
            targets.append(
                {
                    "cluster_name": r["分群名称"],
                    "buyer_count": int(r["购买客户数"]),
                    "buy_ratio": float(r["购买占比"]),
                    "lift_index": float(r["购买倾向指数"]),
                    "strategy": r["营销策略"],
                    "to_items": [item_name],
                    "from_items": [],
                }
            )
        return {"targets": targets}


@lru_cache(maxsize=1)
def get_recommender() -> RecommendationSystem:
    return RecommendationSystem()


def speech_conclusion_merger(result: Dict) -> str:
    parts: List[str] = []
    if result.get("recommends"):
        first = result["recommends"][0]
        parts.append(
            f"优先推荐 {first.get('item')}，原因：{first.get('reason', '综合偏好')}"
        )
    if result.get("target_customers"):
        tgt = result["target_customers"][0]
        parts.append(
            f"目标客户群：{tgt.get('cluster_name', '未知')}，策略：{tgt.get('strategy', '常规营销')}"
        )
    if not parts:
        return "暂无有效推荐，请更换用户或商品。"
    return "；".join(parts)


async def generate_tts(project_id: str, speech: str) -> Dict:
    audio_dir = Path("outputs/audio")
    audio_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"recommend_{project_id}.mp3"
    audio_path = audio_dir / file_name
    tts = TTSService()
    await tts.synthesize(speech, str(audio_path))
    return {
        "audio_url": f"/outputs/audio/{file_name}",
        "path": str(audio_path),
    }
