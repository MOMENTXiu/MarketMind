"""
关联规则分析服务
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

from backend.core.config import settings
from backend.models.schemas import AssociationRule, AssociationRuleResponse


class AssociationService:
    """关联规则分析服务类"""

    def __init__(self, data_path: str = None):
        self.data_path = data_path or settings.DATA_PATH
        self.output_dir = Path(settings.CHARTS_DIR) if hasattr(settings, 'CHARTS_DIR') else Path('outputs/charts')
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def analyze(
        self,
        min_support: float = 0.02,
        min_confidence: float = 0.3,
        min_lift: float = 1.0,
        top_n: int = 10
    ) -> AssociationRuleResponse:
        """
        执行关联规则分析

        Args:
            min_support: 最小支持度
            min_confidence: 最小置信度
            min_lift: 最小提升度
            top_n: 返回Top N规则

        Returns:
            AssociationRuleResponse: 分析结果
        """
        try:
            # 1. 加载数据
            df = pd.read_csv(self.data_path, encoding='utf-8')

            # 2. 构建购物篮数据
            basket_data = df.groupby('订单 ID')['子类别'].apply(list).reset_index()
            basket_data.columns = ['订单 ID', '商品列表']
            basket_data = basket_data[basket_data['商品列表'].apply(len) > 1]

            transactions = basket_data['商品列表'].tolist()

            # 3. 事务编码
            te = TransactionEncoder()
            te_ary = te.fit_transform(transactions)
            basket_df = pd.DataFrame(te_ary, columns=te.columns_)

            # 4. 挖掘频繁项集
            frequent_itemsets = apriori(
                basket_df,
                min_support=min_support,
                use_colnames=True
            )

            # 5. 生成关联规则
            rules = association_rules(
                frequent_itemsets,
                metric="lift",
                min_threshold=min_lift,
                num_itemsets=len(frequent_itemsets)
            )
            rules = rules.sort_values(['confidence', 'lift'], ascending=[False, False])

            # 6. 筛选后项为单一商品的规则
            rules['后项商品'] = rules['consequents'].apply(
                lambda x: list(x)[0] if len(x) == 1 else None
            )
            rules_single = rules[rules['后项商品'].notna()].copy()

            # 7. 生成响应数据
            rules_list = []
            for idx, row in rules_single.head(top_n).iterrows():
                antecedents = list(row['antecedents'])
                consequent = row['后项商品']
                confidence = row['confidence']

                rule = AssociationRule(
                    antecedents=antecedents,
                    consequent=consequent,
                    support=float(row['support']),
                    confidence=float(confidence),
                    lift=float(row['lift']),
                    strategy=f"购买{', '.join(antecedents)}的顾客有{confidence:.1%}概率购买{consequent}，建议组合促销"
                )
                rules_list.append(rule)

            # 8. 统计信息
            stats = {
                "total_orders": len(basket_data),
                "frequent_itemsets": len(frequent_itemsets),
                "total_rules": len(rules),
                "single_consequent_rules": len(rules_single)
            }

            return AssociationRuleResponse(
                success=True,
                message="关联规则分析完成",
                data=stats,
                rules=rules_list,
                charts={}  # TODO: 添加图表生成
            )

        except Exception as e:
            return AssociationRuleResponse(
                success=False,
                message=f"分析失败: {str(e)}",
                data={},
                rules=[],
                charts={}
            )
