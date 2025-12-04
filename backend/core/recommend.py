"""
商品关联推荐 - 基于关联规则 DataFrame
优先从项目数据集计算关联规则，无需额外规则文件；如存在持久化文件则直接加载。
"""
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

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
        df_sorted = df.sort_values(by="confidence", ascending=False).head(20)
        formatted = []
        for _, row in df_sorted.iterrows():
            antecedents = list(row["antecedents"]) if not isinstance(row["antecedents"], list) else row["antecedents"]
            consequents = list(row["consequents"]) if not isinstance(row["consequents"], list) else row["consequents"]

            if current_in_antecedent:
                # 当前查询商品作为前项，前项统一显示当前商品即可
                from_items = [item]
                to_items = consequents
            else:
                from_items = antecedents
                to_items = consequents

            formatted.append(
                {
                    "from_items": list(from_items),
                    "to_items": list(to_items),
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
