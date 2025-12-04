"""
商品关联推荐 - 基于关联规则 DataFrame
优先从项目数据集计算关联规则，无需额外规则文件；如存在持久化文件则直接加载。
"""
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import numpy as np
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

RULES_PATHS = [
    Path("data/association_rules.pkl"),
    Path("data/association_rules.csv"),
]


def _normalize_item(name: str) -> str:
    return name.strip()


def _extract_strategy(row: pd.Series, antecedents: List[str], consequents: List[str]) -> str:
    if "strategy" in row and isinstance(row["strategy"], str):
        return row["strategy"]
    if "strategy_text" in row and isinstance(row["strategy_text"], str):
        return row["strategy_text"]
    # 回退生成简单策略描述
    try:
        conf = float(row.get("confidence", 0))
        return f"购买{', '.join(antecedents)}的顾客有{conf:.1%}概率购买{', '.join(consequents)}，建议组合促销。"
    except Exception:
        return ""


def _build_rules_from_dataset(dataset_path: str) -> pd.DataFrame:
    """从指定数据集现算关联规则（Apriori）。"""
    df = pd.read_csv(dataset_path, encoding="utf-8")
    basket_data = df.groupby("订单 ID")["子类别"].apply(list).reset_index()
    basket_data.columns = ["订单 ID", "商品列表"]
    basket_data = basket_data[basket_data["商品列表"].apply(len) > 1]

    transactions = basket_data["商品列表"].tolist()
    te = TransactionEncoder()
    te_ary = te.fit_transform(transactions)
    basket_df = pd.DataFrame(te_ary, columns=te.columns_)

    frequent_itemsets = apriori(basket_df, min_support=0.02, use_colnames=True)
    rules = association_rules(
        frequent_itemsets, metric="lift", min_threshold=1.0, num_itemsets=len(frequent_itemsets)
    ).sort_values(["confidence", "lift"], ascending=[False, False])

    # 补充策略文本
    rules["strategy"] = rules.apply(
        lambda r: _extract_strategy(
            r,
            list(r["antecedents"]) if not isinstance(r["antecedents"], list) else r["antecedents"],
            list(r["consequents"]) if not isinstance(r["consequents"], list) else r["consequents"],
        ),
        axis=1,
    )
    return rules[
        [
            "antecedents",
            "consequents",
            "support",
            "confidence",
            "lift",
            "strategy",
        ]
    ]


@lru_cache(maxsize=16)
def _load_rules_from_dataset_cached(dataset_path: str) -> pd.DataFrame:
    return _build_rules_from_dataset(dataset_path)


@lru_cache(maxsize=1)
def _load_rules_from_files() -> pd.DataFrame:
    for path in RULES_PATHS:
        if path.exists():
            if path.suffix == ".pkl":
                return pd.read_pickle(path)
            return pd.read_csv(path)
    return pd.DataFrame(
        columns=["antecedents", "consequents", "support", "confidence", "lift", "strategy"]
    )


def load_rules(dataset_path: Optional[str] = None) -> pd.DataFrame:
    """
    加载关联规则：
    - 优先使用传入的 dataset_path 直接现算（并缓存）
    - 否则尝试读取 data/association_rules.pkl 或 csv
    """
    if dataset_path:
        path = Path(dataset_path)
        if path.exists():
            return _load_rules_from_dataset_cached(str(path.resolve()))
    return _load_rules_from_files()


def query_user_basket(dataset_path: str, user_id: str) -> List[str]:
    """读取用户的历史购物篮（去重后的商品列表）"""
    df = pd.read_csv(dataset_path, encoding="utf-8")
    if "客户 ID" not in df.columns or "子类别" not in df.columns:
        return []
    user_df = df[df["客户 ID"] == user_id]
    if user_df.empty:
        return []
    orders = user_df.groupby("订单 ID")["子类别"].apply(list)
    basket: List[str] = []
    for items in orders:
        basket.extend(items)
    return list(dict.fromkeys(basket))  # 去重并保持顺序


def customer_cluster_match(dataset_path: str, user_id: str) -> Optional[Dict]:
    """简单 KMeans 聚类匹配用户群体"""
    df = pd.read_csv(dataset_path, encoding="utf-8")
    required_cols = {"客户 ID", "订单日期", "销售额", "订单 ID"}
    if not required_cols.issubset(set(df.columns)):
        return None

    df["订单日期"] = pd.to_datetime(df["订单日期"])
    reference_date = df["订单日期"].max() + pd.Timedelta(days=1)

    customer_data = df.groupby("客户 ID").agg(
        R_最近购买天数=("订单日期", lambda x: (reference_date - x.max()).days),
        F_购买频次=("订单 ID", "nunique"),
        M_消费金额=("销售额", "sum"),
    ).reset_index()

    if len(customer_data) < 2:
        return None

    # 填充防止除零
    customer_data["F_购买频次"] = customer_data["F_购买频次"].replace(0, 1)
    customer_data["客单价"] = customer_data["M_消费金额"] / customer_data["F_购买频次"]

    features = customer_data[["R_最近购买天数", "F_购买频次", "M_消费金额", "客单价"]]
    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    n_clusters = max(2, min(6, len(customer_data)//20 or 2))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    customer_data["cluster"] = labels

    def name_cluster(row, med_r, med_m):
        if row["R_最近购买天数"] < med_r and row["M_消费金额"] > med_m:
            return "高价值活跃客户"
        if row["R_最近购买天数"] < med_r and row["M_消费金额"] <= med_m:
            return "普通活跃客户"
        if row["R_最近购买天数"] >= med_r and row["M_消费金额"] > med_m:
            return "高价值流失预警"
        return "低价值流失客户"

    med_r = customer_data["R_最近购买天数"].median()
    med_m = customer_data["M_消费金额"].median()
    customer_data["cluster_name"] = customer_data.apply(lambda r: name_cluster(r, med_r, med_m), axis=1)

    user_row = customer_data[customer_data["客户 ID"] == user_id]
    if user_row.empty:
        return None

    row = user_row.iloc[0]
    return {
        "user_id": user_id,
        "cluster_id": int(row["cluster"]),
        "cluster_name": row["cluster_name"],
        "recency": float(row["R_最近购买天数"]),
        "frequency": float(row["F_购买频次"]),
        "monetary": float(row["M_消费金额"]),
        "aov": float(row["客单价"]),
    }


def query_item_relations(item_name: str, dataset_path: Optional[str] = None) -> Dict:
    """
    输入一个商品名，输出该商品在前项和后项中的关联规则。
    """
    item = _normalize_item(item_name)
    rules_df = load_rules(dataset_path)

    if rules_df.empty or not item:
        return {"item": item, "as_antecedent": [], "as_consequent": []}

    def _contains_item(iterable_value, target: str) -> bool:
        try:
            return target in iterable_value
        except Exception:
            return False

    # 筛选前项、后项
    as_ant = rules_df[rules_df["antecedents"].apply(lambda x: _contains_item(x, item))]
    as_con = rules_df[rules_df["consequents"].apply(lambda x: _contains_item(x, item))]

    def _format_rules(df: pd.DataFrame, current_in_antecedent: bool) -> List[Dict]:
        if df.empty:
            return []
        df_sorted = df.sort_values(by="confidence", ascending=False).head(200)

        # 如果当前商品在前项，按后项去重，聚合所有共同前项组合
        if current_in_antecedent:
            grouped: Dict[tuple, Dict] = {}
            for _, row in df_sorted.iterrows():
                antecedents = list(row["antecedents"]) if not isinstance(row["antecedents"], list) else row["antecedents"]
                consequents = list(row["consequents"]) if not isinstance(row["consequents"], list) else row["consequents"]
                to_key = tuple(sorted(consequents))
                co_items = [itm for itm in antecedents if itm != item]

                if to_key not in grouped:
                    grouped[to_key] = {
                        "from_items": [item],
                        "to_items": list(consequents),
                        "support": float(row.get("support", 0)),
                        "confidence": float(row.get("confidence", 0)),
                        "lift": float(row.get("lift", 0)),
                        "strategy": _extract_strategy(row, antecedents, consequents),
                        "co_antecedents": [co_items] if co_items else [],
                    }
                else:
                    # 收集合并共同前项组合，并保留最高置信度
                    grouped[to_key]["co_antecedents"].append(co_items if co_items else [])
                    if float(row.get("confidence", 0)) > grouped[to_key]["confidence"]:
                        grouped[to_key]["support"] = float(row.get("support", 0))
                        grouped[to_key]["confidence"] = float(row.get("confidence", 0))
                        grouped[to_key]["lift"] = float(row.get("lift", 0))
                        grouped[to_key]["strategy"] = _extract_strategy(row, antecedents, consequents)

            # 返回按置信度排序的去重结果，最多 20 条
            return sorted(grouped.values(), key=lambda x: x["confidence"], reverse=True)[:20]

        # 当前商品在后项，按置信度排序取前 20 条
        formatted = []
        for _, row in df_sorted.head(20).iterrows():
            antecedents = list(row["antecedents"]) if not isinstance(row["antecedents"], list) else row["antecedents"]
            consequents = list(row["consequents"]) if not isinstance(row["consequents"], list) else row["consequents"]
            formatted.append(
                {
                    "from_items": antecedents,
                    "to_items": consequents,
                    "support": float(row.get("support", 0)),
                    "confidence": float(row.get("confidence", 0)),
                    "lift": float(row.get("lift", 0)),
                    "strategy": _extract_strategy(row, antecedents, consequents),
                }
            )
        return formatted

    return {
        "item": item,
        "as_antecedent": _format_rules(as_ant, current_in_antecedent=True),
        "as_consequent": _format_rules(as_con, current_in_antecedent=False),
    }
