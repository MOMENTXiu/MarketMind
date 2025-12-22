"""
客户聚类服务 - 基于KMeans的RFM客户分群
"""
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from datetime import timedelta
from typing import Dict, Any, List


class ClusteringService:
    """客户聚类服务类"""

    def __init__(self, data_path: str):
        self.data_path = data_path
        self.scaler = StandardScaler()
        self.kmeans = None

    async def analyze(self, n_clusters: int = 4, save_path: str = None) -> Dict[str, Any]:
        """
        执行客户聚类分析

        Args:
            n_clusters: 聚类数量
            save_path: 完整结果保存路径

        Returns:
            聚类结果字典
        """
        try:
            # 1. 加载数据
            df = pd.read_csv(self.data_path, encoding='utf-8')
            df['订单日期'] = pd.to_datetime(df['订单日期'])

            # 2. 计算RFM特征
            customer_data = self._calculate_rfm(df)

            # 3. 准备聚类特征
            cluster_features = ['R_最近购买天数', 'F_购买频次', 'M_消费金额', '平均折扣', '客单价']
            X_cluster = customer_data[cluster_features].values

            if len(X_cluster) < 2:
                raise ValueError("数据量过少，无法进行聚类分析")

            # 4. 标准化
            X_scaled = self.scaler.fit_transform(X_cluster)

            # 5. 确定最佳聚类数（如果需要）
            if n_clusters == 0:
                best_k, silhouette_scores = self._find_optimal_k(X_scaled)
            else:
                best_k = min(max(2, n_clusters), len(X_cluster))
                silhouette_scores = []

            # 6. 执行最终聚类
            self.kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            customer_data['客户分群'] = self.kmeans.fit_predict(X_scaled)

            # 保存完整结果
            if save_path:
                customer_data.to_csv(save_path, index=False, encoding='utf-8')

            # 7. 分析各群体特征
            cluster_profiles = self._analyze_clusters(customer_data)

            # 8. 计算各群体贡献度
            contribution_data = self._calculate_contribution(customer_data)

            # 9. 提取每个聚类的客户详细列表（TOP 20）
            cluster_customers = self._get_cluster_customers(customer_data)

            # 10. 分析每个聚类的关联规则（前推后、后推前 TOP5）
            cluster_rules = self._analyze_cluster_rules(customer_data, df)

            try:
                silhouette = round(float(silhouette_score(X_scaled, customer_data['客户分群'])), 4)
            except Exception:
                silhouette = 0.0

            return {
                "success": True,
                "message": "客户聚类完成",
                "data": {
                    "total_customers": len(customer_data),
                    "n_clusters": best_k,
                    "silhouette_score": silhouette,
                    "cluster_profiles": cluster_profiles,
                    "contribution": contribution_data,
                    "cluster_customers": cluster_customers,
                    "cluster_rules": cluster_rules
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"聚类分析失败: {str(e)}",
                "data": {}
            }

    def _calculate_rfm(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算RFM特征"""
        reference_date = df['订单日期'].max() + timedelta(days=1)

        customer_data = df.groupby('客户 ID').agg({
            '订单日期': lambda x: (reference_date - x.max()).days,  # R: 最近一次购买距今天数
            '订单 ID': 'nunique',  # F: 购买频次
            '销售额': 'sum',  # M: 消费金额
            '利润': 'sum',
            '数量': 'sum',
            '折扣': 'mean',
            '细分': 'first' if '细分' in df.columns else lambda x: '未知',
            '地区': 'first' if '地区' in df.columns else lambda x: '未知'
        }).reset_index()

        customer_data.columns = [
            '客户ID', 'R_最近购买天数', 'F_购买频次', 'M_消费金额',
            '总利润', '购买数量', '平均折扣', '客户细分', '地区'
        ]

        # 添加衍生特征
        customer_data['客单价'] = customer_data['M_消费金额'] / customer_data['F_购买频次'].replace(0, np.nan)
        customer_data['件单价'] = customer_data['M_消费金额'] / customer_data['购买数量'].replace(0, np.nan)
        customer_data['利润率'] = customer_data['总利润'] / customer_data['M_消费金额'].replace(0, np.nan) * 100

        # 清理无限与缺失
        customer_data = customer_data.replace([np.inf, -np.inf], np.nan).fillna(0)

        return customer_data

    def _find_optimal_k(self, X_scaled: np.ndarray) -> tuple:
        """使用轮廓系数找到最佳聚类数"""
        silhouettes = []
        K_range = [k for k in range(2, 8) if k <= len(X_scaled)]

        if not K_range:
            return 2, []

        for k in K_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(X_scaled)
            silhouettes.append(silhouette_score(X_scaled, kmeans.labels_))

        best_k = K_range[int(np.argmax(silhouettes))] if silhouettes else 2
        return best_k, silhouettes

    def _analyze_clusters(self, customer_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """分析各群体特征"""
        cluster_profiles = customer_data.groupby('客户分群').agg({
            '客户ID': 'count',
            'R_最近购买天数': 'mean',
            'F_购买频次': 'mean',
            'M_消费金额': 'mean',
            '总利润': 'mean',
            '平均折扣': 'mean',
            '客单价': 'mean'
        }).round(2)

        cluster_profiles.columns = ['客户数', '平均R', '平均F', '平均M', '平均利润', '平均折扣', '平均客单价']

        # 命名各群体
        profiles_list = []
        for idx, row in cluster_profiles.iterrows():
            name = self._get_cluster_name(row, cluster_profiles)
            strategy = self._get_marketing_strategy(name)

            profiles_list.append({
                "cluster_id": int(idx),
                "cluster_name": name,
                "customer_count": int(row['客户数']),
                "avg_recency": round(float(row['平均R']), 2),
                "avg_frequency": round(float(row['平均F']), 2),
                "avg_monetary": round(float(row['平均M']), 2),
                "avg_profit": round(float(row['平均利润']), 2),
                "avg_discount": round(float(row['平均折扣']), 4),
                "avg_order_value": round(float(row['平均客单价']), 2),
                "marketing_strategy": strategy
            })

        return profiles_list

    def _get_cluster_name(self, row: pd.Series, all_profiles: pd.DataFrame) -> str:
        """根据RFM特征命名群体"""
        r_median = all_profiles['平均R'].median()
        m_median = all_profiles['平均M'].median()

        if row['平均R'] < r_median and row['平均M'] > m_median:
            return "高价值活跃客户"
        elif row['平均R'] < r_median and row['平均M'] <= m_median:
            return "普通活跃客户"
        elif row['平均R'] >= r_median and row['平均M'] > m_median:
            return "高价值流失预警"
        else:
            return "低价值流失客户"

    def _get_marketing_strategy(self, name: str) -> str:
        """获取营销策略"""
        strategies = {
            "高价值活跃客户": "VIP专属优惠、会员积分加倍、新品优先体验、专属客服",
            "普通活跃客户": "满减优惠券、推荐升级产品、交叉销售、积分兑换活动",
            "高价值流失预警": "召回优惠券、专属折扣、限时特惠、电话回访关怀",
            "低价值流失客户": "大额满减券、限时秒杀、清仓特价、短信推送唤醒"
        }
        return strategies.get(name, "常规营销活动")

    def _calculate_contribution(self, customer_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """计算各群体贡献度"""
        total_sales = customer_data['M_消费金额'].sum()
        total_profit = customer_data['总利润'].sum()

        contribution = customer_data.groupby('客户分群').agg({
            'M_消费金额': 'sum',
            '总利润': 'sum'
        })

        contribution['销售额占比'] = (contribution['M_消费金额'] / total_sales * 100).round(2)
        contribution['利润占比'] = (contribution['总利润'] / total_profit * 100).round(2)

        contribution_list = []
        for idx, row in contribution.iterrows():
            contribution_list.append({
                "cluster_id": int(idx),
                "total_sales": round(float(row['M_消费金额']), 2),
                "total_profit": round(float(row['总利润']), 2),
                "sales_percentage": round(float(row['销售额占比']), 2),
                "profit_percentage": round(float(row['利润占比']), 2)
            })

        return contribution_list

    def _get_cluster_customers(self, customer_data: pd.DataFrame) -> Dict[int, List[Dict[str, Any]]]:
        """获取每个聚类的客户详细列表（TOP 20按消费金额排序）"""
        cluster_customers = {}

        for cluster_id in customer_data['客户分群'].unique():
            cluster_df = customer_data[customer_data['客户分群'] == cluster_id].copy()

            # 按消费金额降序排序，取TOP 20
            cluster_df = cluster_df.sort_values('M_消费金额', ascending=False).head(20)

            customers = []
            for _, row in cluster_df.iterrows():
                customers.append({
                    "customer_id": str(row['客户ID']),
                    "customer_name": str(row['客户ID']),  # 客户名称就是ID
                    "avg_order_value": round(float(row['客单价']), 2),
                    "frequency": int(row['F_购买频次']),
                    "total_monetary": round(float(row['M_消费金额']), 2),
                    "recency_days": int(row['R_最近购买天数']),
                    "profit_margin": round(float(row['利润率']), 2)
                })

            cluster_customers[int(cluster_id)] = customers

        return cluster_customers

    def _analyze_cluster_rules(self, customer_data: pd.DataFrame, df: pd.DataFrame) -> Dict[int, Dict[str, List]]:
        """分析每个聚类的关联规则（前推后、后推前 TOP5）"""
        from mlxtend.frequent_patterns import apriori, association_rules
        from mlxtend.preprocessing import TransactionEncoder

        cluster_rules = {}

        for cluster_id in customer_data['客户分群'].unique():
            # 获取该聚类的客户ID列表
            cluster_customer_ids = customer_data[customer_data['客户分群'] == cluster_id]['客户ID'].tolist()

            # 过滤该聚类的订单
            cluster_orders = df[df['客户 ID'].isin(cluster_customer_ids)]

            if len(cluster_orders) < 10:  # 订单太少跳过
                cluster_rules[int(cluster_id)] = {
                    "antecedent_to_consequent": [],  # 前推后
                    "consequent_to_antecedent": []   # 后推前
                }
                continue

            try:
                # 构建购物篮
                basket_data = cluster_orders.groupby('订单 ID')['子类别'].apply(list).reset_index()
                basket_data = basket_data[basket_data['子类别'].apply(len) > 1]

                if len(basket_data) < 5:  # 购物篮太少
                    cluster_rules[int(cluster_id)] = {
                        "antecedent_to_consequent": [],
                        "consequent_to_antecedent": []
                    }
                    continue

                transactions = basket_data['子类别'].tolist()

                # 事务编码
                te = TransactionEncoder()
                te_ary = te.fit_transform(transactions)
                basket_df = pd.DataFrame(te_ary, columns=te.columns_)

                # Apriori
                frequent_itemsets = apriori(basket_df, min_support=0.05, use_colnames=True)

                if frequent_itemsets.empty:
                    cluster_rules[int(cluster_id)] = {
                        "antecedent_to_consequent": [],
                        "consequent_to_antecedent": []
                    }
                    continue

                # 生成关联规则
                rules = association_rules(
                    frequent_itemsets,
                    metric="confidence",
                    min_threshold=0.2,
                    num_itemsets=len(frequent_itemsets)
                )

                # 前推后 TOP5（按置信度排序）
                antecedent_to_consequent = []
                for _, rule in rules.sort_values('confidence', ascending=False).head(5).iterrows():
                    antecedent_to_consequent.append({
                        "antecedent": list(rule['antecedents']),
                        "consequent": list(rule['consequents']),
                        "confidence": round(float(rule['confidence']), 4),
                        "support": round(float(rule['support']), 4),
                        "lift": round(float(rule['lift']), 2)
                    })

                # 后推前 TOP5（交换前后项）
                consequent_to_antecedent = []
                for _, rule in rules.sort_values('confidence', ascending=False).head(5).iterrows():
                    consequent_to_antecedent.append({
                        "antecedent": list(rule['consequents']),  # 交换
                        "consequent": list(rule['antecedents']),  # 交换
                        "confidence": round(float(rule['confidence']), 4),  # 注意：这里的置信度是原方向的
                        "support": round(float(rule['support']), 4),
                        "lift": round(float(rule['lift']), 2)
                    })

                cluster_rules[int(cluster_id)] = {
                    "antecedent_to_consequent": antecedent_to_consequent,
                    "consequent_to_antecedent": consequent_to_antecedent
                }

            except Exception as e:
                print(f"聚类 {cluster_id} 关联规则分析失败: {e}")
                cluster_rules[int(cluster_id)] = {
                    "antecedent_to_consequent": [],
                    "consequent_to_antecedent": []
                }

        return cluster_rules
