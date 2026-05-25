"""Association rule analysis ability."""

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

from backend.models.schemas import AssociationRule, AssociationRuleResponse


def analyze_association_rules(
    dataset: pd.DataFrame,
    min_support: float = 0.02,
    min_confidence: float = 0.3,
    min_lift: float = 1.0,
    top_n: int = 10,
) -> AssociationRuleResponse:
    """Analyze association rules from an explicit dataset."""

    try:
        basket_data = dataset.groupby("订单 ID")["子类别"].apply(list).reset_index()
        basket_data.columns = ["订单 ID", "商品列表"]
        basket_data = basket_data[basket_data["商品列表"].apply(len) > 1]
        if basket_data.empty:
            return AssociationRuleResponse(
                success=True,
                message="关联规则分析完成",
                data={
                    "total_orders": 0,
                    "frequent_itemsets": 0,
                    "total_rules": 0,
                    "single_consequent_rules": 0,
                },
                rules=[],
                charts={},
            )

        transactions = basket_data["商品列表"].tolist()
        encoder = TransactionEncoder()
        encoded = encoder.fit_transform(transactions)
        basket_frame = pd.DataFrame(encoded, columns=encoder.columns_)
        frequent_itemsets = apriori(basket_frame, min_support=min_support, use_colnames=True)
        if frequent_itemsets.empty:
            return AssociationRuleResponse(
                success=True,
                message="关联规则分析完成",
                data={
                    "total_orders": len(basket_data),
                    "frequent_itemsets": 0,
                    "total_rules": 0,
                    "single_consequent_rules": 0,
                },
                rules=[],
                charts={},
            )

        rules = _association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
        rules = rules.sort_values(["confidence", "lift"], ascending=[False, False])
        rules = rules[rules["confidence"] >= min_confidence]
        rules["后项商品"] = rules["consequents"].apply(
            lambda value: list(value)[0] if len(value) == 1 else None
        )
        rules_single = rules[rules["后项商品"].notna()].copy()

        rules_list = []
        for _, row in rules_single.head(top_n).iterrows():
            antecedents = list(row["antecedents"])
            consequent = row["后项商品"]
            confidence = float(row["confidence"])
            rules_list.append(
                AssociationRule(
                    antecedents=antecedents,
                    consequent=consequent,
                    support=float(row["support"]),
                    confidence=confidence,
                    lift=float(row["lift"]),
                    strategy=f"购买{', '.join(antecedents)}的顾客有{confidence:.1%}概率购买{consequent}，建议组合促销",
                )
            )

        return AssociationRuleResponse(
            success=True,
            message="关联规则分析完成",
            data={
                "total_orders": len(basket_data),
                "frequent_itemsets": len(frequent_itemsets),
                "total_rules": len(rules),
                "single_consequent_rules": len(rules_single),
            },
            rules=rules_list,
            charts={},
        )
    except Exception as exc:
        return AssociationRuleResponse(
            success=False,
            message=f"分析失败: {exc}",
            data={},
            rules=[],
            charts={},
        )


def _association_rules(
    frequent_itemsets: pd.DataFrame,
    metric: str,
    min_threshold: float,
) -> pd.DataFrame:
    try:
        return association_rules(
            frequent_itemsets,
            metric=metric,
            min_threshold=min_threshold,
            num_itemsets=len(frequent_itemsets),
        )
    except TypeError:
        return association_rules(
            frequent_itemsets,
            metric=metric,
            min_threshold=min_threshold,
        )
