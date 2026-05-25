"""
推荐系统服务 - 复用预训练的 model_data.pkl
"""

import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

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
        # 模型文件变为可选
        self.has_model = os.path.exists(model_path)

        if self.has_model:
            self._load_model(model_path)
        else:
            # 初始化空模型属性
            self.kmeans_model = None
            self.cluster_scaler = None
            self.best_k = 0
            self.cluster_features = []
            self.cluster_profiles = pd.DataFrame()
            self.cluster_contribution = []
            self.customer_data = pd.DataFrame()
            self.rules_single = pd.DataFrame()
            self.feature_stats = {}
            self.reference_date = None
            self.categories = []
            self.subcategories = []
            self.regions = []
            self.segments = []

        # 加载数据集（总是需要）
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"数据集文件 '{data_path}' 不存在！请先上传数据集。")

        self.df = pd.read_csv(data_path, encoding="utf-8")
        self._preprocess_data()

        # 只有在有模型时才构建产品统计
        if self.has_model:
            self._build_product_stats()
        else:
            # 基本的产品统计（不依赖聚类）
            self._build_basic_product_stats()

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
        # Use .get() to avoid KeyError if rules_single is missing in old pkl files
        self.rules_single = model_data.get("rules_single", pd.DataFrame())
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

    def _build_basic_product_stats(self):
        """不依赖聚类的基本产品统计"""
        # 提取可用的子类别列表
        if "子类别" in self.df.columns:
            self.subcategories = self.df["子类别"].unique().tolist()
        if "类别" in self.df.columns:
            self.categories = self.df["类别"].unique().tolist()
        if "地区" in self.df.columns:
            self.regions = self.df["地区"].unique().tolist()
        if "细分" in self.df.columns:
            self.segments = self.df["细分"].unique().tolist()

        # 基本产品统计
        self.product_stats = (
            self.df.groupby("子类别")
            .agg({"销售额": ["sum", "mean"], "利润": "sum", "客户 ID": "nunique", "类别": "first"})
            .reset_index()
        )
        self.product_stats.columns = [
            "子类别",
            "总销售额",
            "平均销售额",
            "总利润",
            "购买客户数",
            "所属类别",
        ]
        self.product_stats["利润率"] = (
            self.product_stats["总利润"] / self.product_stats["总销售额"] * 100
        )

    def _build_product_stats(self):
        customer_cluster_map = self.customer_data.set_index("客户ID")["客户分群"].to_dict()
        self.df["客户分群"] = self.df["客户 ID"].map(customer_cluster_map)
        cluster_name_map = self.cluster_profiles["群体名称"].to_dict()
        self.df["分群名称"] = self.df["客户分群"].map(cluster_name_map)

        self.product_cluster_stats = (
            self.df.groupby(["子类别", "分群名称"])
            .agg({"客户 ID": "nunique", "销售额": "sum", "数量": "sum"})
            .reset_index()
        )
        self.product_cluster_stats.columns = ["子类别", "分群名称", "购买客户数", "销售额", "销量"]

        self.product_stats = (
            self.df.groupby("子类别")
            .agg({"销售额": ["sum", "mean"], "利润": "sum", "客户 ID": "nunique", "类别": "first"})
            .reset_index()
        )
        self.product_stats.columns = [
            "子类别",
            "总销售额",
            "平均销售额",
            "总利润",
            "购买客户数",
            "所属类别",
        ]
        self.product_stats["利润率"] = (
            self.product_stats["总利润"] / self.product_stats["总销售额"] * 100
        )

    # ---------- 对外推荐方法 ----------
    def recommend_user(self, user_id: str, top_n: int = 10) -> Dict:
        """根据用户ID推荐商品"""
        # 如果没有模型，返回基于销售额的热门推荐
        if not self.has_model:
            return self._recommend_user_fallback(user_id, top_n)

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

        cluster_pref = self.product_cluster_stats[
            self.product_cluster_stats["分群名称"] == cluster_name
        ].copy()
        if len(cluster_pref) == 0:
            cluster_pref = (
                self.product_cluster_stats.groupby("子类别")
                .agg({"购买客户数": "sum", "销售额": "sum"})
                .reset_index()
            )
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

    def _recommend_user_fallback(self, user_id: str, top_n: int = 10) -> Dict:
        """当没有模型时的降级推荐：基于热门商品"""
        # 按销售额排序推荐热门商品
        top_products = self.product_stats.sort_values("总销售额", ascending=False).head(top_n)

        recommends = []
        for _, r in top_products.iterrows():
            recommends.append(
                {
                    "item": r["子类别"],
                    "category": r["所属类别"],
                    "score": 0.5,  # 固定分数
                    "avg_price": float(r["平均销售额"]),
                    "reason": f"热门商品（销售额 {r['总销售额']:.0f}）",
                }
            )

        return {
            "recommends": recommends,
            "cluster": {
                "cluster_id": -1,
                "cluster_name": "未分类",
                "strategy": "基于热门商品推荐（模型未加载）",
            },
        }

    def recommend_item(self, item_name: str, top_n: int = 8) -> Dict:
        """根据商品名称推荐上下游关联关系（双向拓扑图数据）"""

        upstream_rules = []
        downstream_rules = []

        try:
            if (
                hasattr(self, "rules_single")
                and not self.rules_single.empty
                and "antecedents" in self.rules_single.columns
            ):
                # 1. 下游规则 (Downstream): Item -> What else?
                # 筛选 item_name 在前项中的规则
                down_df = self.rules_single[
                    self.rules_single["antecedents"].apply(lambda x: item_name in x)
                ].copy()

                if not down_df.empty:
                    down_df = down_df.sort_values("confidence", ascending=False).head(top_n)
                    for _, r in down_df.iterrows():
                        downstream_rules.append(
                            {
                                "item": list(r["consequents"])[0],
                                "confidence": float(r["confidence"]),
                                "lift": float(r["lift"]),
                                "support": float(r["support"]),
                            }
                        )

                # 2. 上游规则 (Upstream): What else -> Item?
                # 筛选 item_name 在后项中的规则
                up_df = self.rules_single[
                    self.rules_single["consequents"].apply(lambda x: item_name in x)
                ].copy()

                if not up_df.empty:
                    up_df = up_df.sort_values("confidence", ascending=False).head(top_n)
                    for _, r in up_df.iterrows():
                        upstream_rules.append(
                            {
                                "item": list(r["antecedents"])[0],
                                "confidence": float(r["confidence"]),
                                "lift": float(r["lift"]),
                                "support": float(r["support"]),
                            }
                        )
        except Exception as e:
            print(f"Error finding bidirectional rules: {e}")

        # 获取目标客户群 (Existing Logic)
        targets = []
        if self.has_model and item_name in self.subcategories:
            try:
                cluster_stats = self.product_cluster_stats[
                    self.product_cluster_stats["子类别"] == item_name
                ].copy()
                if not cluster_stats.empty:
                    total_buyers = cluster_stats["购买客户数"].sum() or 1
                    total_customers = len(self.customer_data)
                    cluster_sizes = self.cluster_profiles["客户数"].to_dict()

                    cluster_stats["购买占比"] = cluster_stats["购买客户数"] / total_buyers * 100
                    cluster_stats["群体占比"] = (
                        cluster_stats["分群名称"].map(
                            {
                                self.cluster_profiles.loc[k, "群体名称"]: v
                                for k, v in cluster_sizes.items()
                            }
                        )
                        / total_customers
                        * 100
                    )
                    cluster_stats["购买倾向指数"] = (
                        cluster_stats["购买占比"] / cluster_stats["群体占比"]
                    )

                    strategy_map = self.cluster_profiles.set_index("群体名称")["营销策略"].to_dict()
                    cluster_stats = cluster_stats.sort_values("购买倾向指数", ascending=False).head(
                        5
                    )

                    for _, r in cluster_stats.iterrows():
                        targets.append(
                            {
                                "cluster_name": r["分群名称"],
                                "buyer_count": int(r["购买客户数"]),
                                "lift_index": float(r["购买倾向指数"]),
                                "strategy": strategy_map.get(r["分群名称"], "常规营销"),
                            }
                        )
            except Exception:
                pass

        return {
            "item": item_name,
            "upstream": upstream_rules,
            "downstream": downstream_rules,
            "target_customers": targets,
        }

    def calculate_realtime_rules(self, item_name: str, min_confidence: float = 0.1) -> List[Dict]:
        """
        实时计算指定商品的关联规则 (On-demand Apriori)
        """
        try:
            from mlxtend.frequent_patterns import apriori, association_rules
            from mlxtend.preprocessing import TransactionEncoder
        except ImportError:
            raise ImportError("Please install mlxtend: pip install mlxtend")

        # 1. 过滤包含该商品的订单 (Transaction subset)
        # 获取包含 item_name 的所有订单ID
        target_orders = self.df[self.df["子类别"] == item_name]["订单 ID"].unique()

        # 获取这些订单的所有商品明细
        subset_df = self.df[self.df["订单 ID"].isin(target_orders)]

        if len(subset_df) < 5:  # Not enough data
            return []

        # 构建购物篮
        basket = subset_df.groupby("订单 ID")["子类别"].apply(list).tolist()

        # Transaction Encoder
        te = TransactionEncoder()
        te_ary = te.fit_transform(basket)
        df_trans = pd.DataFrame(te_ary, columns=te.columns_)

        # Apriori (Lower support since we are already in a focused subset)
        # In a focused subset, support means "conditional probability" given the item exists (almost)
        # Actually, if we filter by item, support of item is 1.0 in this subset.
        frequent_itemsets = apriori(df_trans, min_support=0.01, use_colnames=True)

        if frequent_itemsets.empty:
            return []

        # Generate Rules
        rules = association_rules(
            frequent_itemsets, metric="confidence", min_threshold=min_confidence
        )

        # Filter: Antecedents must include item_name
        # And convert frozenset to list for checking
        filtered_rules = rules[rules["antecedents"].apply(lambda x: item_name in x)]

        # Format results
        results = []
        new_rules_rows = []

        for _, r in filtered_rules.sort_values("lift", ascending=False).head(10).iterrows():
            consequent = list(r["consequents"])[0]
            if len(r["consequents"]) > 1:
                continue  # Only simple rules

            rule_obj = {
                "item": consequent,  # 统一使用 "item" 字段，与 recommend_item 的 downstream 格式一致
                "confidence": float(r["confidence"]),
                "lift": float(r["lift"]),
                "support": float(r["support"])
                * (
                    len(target_orders) / len(self.df["订单 ID"].unique())
                ),  # Adjust support to global estimate roughly
            }
            results.append(rule_obj)

            # Prepare for persistence
            new_rules_rows.append(
                {
                    "antecedents": r["antecedents"],
                    "consequents": r["consequents"],
                    "support": rule_obj["support"],
                    "confidence": rule_obj["confidence"],
                    "lift": rule_obj["lift"],
                }
            )

        # 2. Persistence (Simple CSV Append)
        if new_rules_rows:
            new_df = pd.DataFrame(new_rules_rows)
            # Append to in-memory rules
            self.rules_single = pd.concat([self.rules_single, new_df], ignore_index=True)

            # Append to file
            dynamic_rules_path = Path("backend/data/dynamic_rules.csv")
            header = not dynamic_rules_path.exists()
            new_df.to_csv(dynamic_rules_path, mode="a", header=header, index=False)

        return results


@lru_cache(maxsize=1)
def get_recommender() -> RecommendationSystem:
    return RecommendationSystem()


def clear_recommender_cache():
    """清除推荐系统缓存，用于模型更新后重新加载"""
    get_recommender.cache_clear()
    print("✓ 推荐系统缓存已清除")


def speech_conclusion_merger(result: Dict) -> str:
    parts: List[str] = []
    if result.get("recommends"):
        first = result["recommends"][0]
        parts.append(f"优先推荐 {first.get('item')}，原因：{first.get('reason', '综合偏好')}")
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
