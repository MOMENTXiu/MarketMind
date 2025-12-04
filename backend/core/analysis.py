"""
行为推荐分析入口
"""
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from backend.core.recommend import (
    load_rules,
    query_user_basket,
    customer_cluster_match,
    query_item_relations,
)


def recommend_from_behavior(data_path: str, entity: str) -> Dict:
    """
    根据用户或商品进行行为学习与推荐。
    - 输入 user_id：基于其历史购物篮 + 关联规则生成商品推荐，并返回群体匹配与语音说明
    - 输入 item 名：查找以该商品为后项的规则，推荐潜在目标客户群与用户列表
    返回结构：
    {item, recommends[], target_customers[], speech, model_tries:3, human_fallback:false}
    """
    model_tries = 3  # 计数记录，未实际重试
    human_fallback = False

    dataset_path = Path(data_path)
    if not dataset_path.exists():
        return {
            "item": entity,
            "recommends": [],
            "target_customers": [],
            "speech": f"数据集 {data_path} 不存在，无法生成推荐。",
            "model_tries": model_tries,
            "human_fallback": human_fallback,
        }

    df = pd.read_csv(dataset_path, encoding="utf-8")
    rules_df = load_rules(str(dataset_path))

    # 识别是用户还是商品：优先匹配用户 ID
    is_user = "客户 ID" in df.columns and (df["客户 ID"] == entity).any()

    if is_user:
        user_id = entity
        basket = query_user_basket(str(dataset_path), user_id)
        basket_set = set(basket)

        # 规则推荐：前项与用户篮子有交集，后项不在篮子
        candidates = rules_df[
            rules_df["antecedents"].apply(lambda s: len(set(s) & basket_set) > 0)
            & rules_df["consequents"].apply(lambda s: len(set(s) & basket_set) == 0)
        ]

        recommends: List[Dict] = []
        for _, row in candidates.sort_values("confidence", ascending=False).head(10).iterrows():
            consequents = list(row["consequents"])
            antecedents = list(row["antecedents"]) if not isinstance(row["antecedents"], list) else row["antecedents"]
            recommends.append(
                {
                    "items": consequents,
                    "from_items": antecedents,
                    "support": float(row.get("support", 0)),
                    "confidence": float(row.get("confidence", 0)),
                    "lift": float(row.get("lift", 0)),
                    "reason": row.get("strategy", "")
                    or f"您购买过{', '.join(set(antecedents))}的顾客有{row.get('confidence', 0):.1%}概率再买{', '.join(consequents)}",
                }
            )

        # 群体匹配
        cluster_info = customer_cluster_match(str(dataset_path), user_id)

        speech_parts = [
            f"为用户 {user_id} 生成推荐。",
            f"历史篮子包含：{', '.join(basket) if basket else '暂无购买记录'}。",
        ]
        if recommends:
            top_item = recommends[0]["items"][0]
            speech_parts.append(
                f"依据关联规则，优先推荐 {top_item}，置信度约 {recommends[0]['confidence']:.1%}，提升度 {recommends[0]['lift']:.2f}。"
            )
        if cluster_info:
            speech_parts.append(f"用户聚类：{cluster_info.get('cluster_name', '未知群体')}。")

        return {
            "item": user_id,
            "recommends": recommends,
            "target_customers": [cluster_info] if cluster_info else [],
            "speech": " ".join(speech_parts),
            "model_tries": model_tries,
            "human_fallback": human_fallback,
        }

    # 商品逆向：找以该商品为后项的规则，定位潜在客户
    item = entity.strip()
    matches = rules_df[rules_df["consequents"].apply(lambda s: item in s)]
    rule_views = query_item_relations(item, dataset_path=str(dataset_path))

    target_customers: List[Dict] = []
    if not matches.empty:
        # 找到购买过前项组合的客户列表
        if "客户 ID" in df.columns and "订单 ID" in df.columns:
            for _, row in matches.head(10).iterrows():
                antecedent_items = set(row["antecedents"])
                orders = df.groupby("订单 ID")["子类别"].apply(set).reset_index()
                hit_orders = orders[orders["子类别"].apply(lambda s: antecedent_items.issubset(s))]
                customer_ids = df[df["订单 ID"].isin(hit_orders["订单 ID"])]["客户 ID"].unique().tolist()
                target_customers.append(
                    {
                        "from_items": list(antecedent_items),
                        "to_items": [item],
                        "support": float(row.get("support", 0)),
                        "confidence": float(row.get("confidence", 0)),
                        "lift": float(row.get("lift", 0)),
                        "customers": customer_ids[:20],
                    }
                )

    speech = (
        f"针对商品 {item} 的推荐分析。"
        f"{' 找到相关规则，筛选潜在客户。' if target_customers else ' 暂无匹配规则。'}"
    )

    return {
        "item": item,
        "recommends": [],
        "target_customers": target_customers,
        "rules_as_antecedent": rule_views.get("as_antecedent", []),
        "rules_as_consequent": rule_views.get("as_consequent", []),
        "speech": speech,
        "model_tries": model_tries,
        "human_fallback": human_fallback,
    }
