"""
商品关联推荐 - 基于已持久化的关联规则 DataFrame
"""
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import pandas as pd

RULES_PATHS = [
    Path("data/association_rules.pkl"),
    Path("data/association_rules.csv"),
]


@lru_cache(maxsize=1)
def load_rules() -> pd.DataFrame:
    """
    从磁盘加载关联规则 DataFrame。
    优先加载 pkl，没有则尝试 csv。若均不存在，返回空 DataFrame。
    """
    for path in RULES_PATHS:
        if path.exists():
            if path.suffix == ".pkl":
                return pd.read_pickle(path)
            return pd.read_csv(path)

    # 返回空的占位 DataFrame
    return pd.DataFrame(
        columns=["antecedents", "consequents", "support", "confidence", "lift", "strategy"]
    )


def _normalize_item(name: str) -> str:
    return name.strip()


def _extract_strategy(row: pd.Series) -> str:
    if "strategy" in row and isinstance(row["strategy"], str):
        return row["strategy"]
    if "strategy_text" in row and isinstance(row["strategy_text"], str):
        return row["strategy_text"]
    return ""


def query_item_relations(item_name: str) -> Dict:
    """
    输入一个商品名，输出该商品在前项和后项中的关联规则。
    """
    item = _normalize_item(item_name)
    rules_df = load_rules()

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
                from_items = [itm for itm in antecedents if itm != item] or antecedents
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
                    "strategy": _extract_strategy(row),
                }
            )
        return formatted

    return {
        "item": item,
        "as_antecedent": _format_rules(as_ant, current_in_antecedent=True),
        "as_consequent": _format_rules(as_con, current_in_antecedent=False),
    }
