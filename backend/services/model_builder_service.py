"""
模型构建服务 - 生成预训练推荐模型
"""
import pickle
from pathlib import Path
from datetime import timedelta
from typing import Dict, Any
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


class ModelBuilderService:
    """构建和保存推荐系统所需的预训练模型"""

    def __init__(self, data_path: str):
        self.data_path = data_path
        self.df = None
        self.model_data = {}

    async def build_and_save(
        self,
        n_clusters: int = 4,
        association_rules: list = None,
        output_path: str = "backend/data/model_data.pkl"
    ) -> Dict[str, Any]:
        """
        构建完整的推荐模型并保存

        Args:
            n_clusters: 聚类数量
            association_rules: 关联规则列表（从 association_service 获取）
            output_path: 输出路径

        Returns:
            构建结果统计
        """
        try:
            # 1. 加载数据
            self.df = pd.read_csv(self.data_path, encoding='utf-8')
            self._preprocess_data()

            # 2. 计算 RFM 和客户特征
            customer_data = self._calculate_customer_features()

            # 3. 客户聚类
            kmeans_model, cluster_scaler, cluster_features = self._perform_clustering(
                customer_data, n_clusters
            )

            # 4. 生成聚类画像
            cluster_profiles = self._generate_cluster_profiles(customer_data)

            # 5. 计算聚类贡献度
            cluster_contribution = self._calculate_cluster_contribution(customer_data)

            # 6. 提取特征统计
            feature_stats = self._extract_feature_stats(customer_data)

            # 7. 处理关联规则
            rules_single = self._process_association_rules(association_rules)

            # 8. 提取分类信息
            categories = self.df['类别'].unique().tolist() if '类别' in self.df.columns else []
            subcategories = self.df['子类别'].unique().tolist() if '子类别' in self.df.columns else []
            regions = self.df['地区'].unique().tolist() if '地区' in self.df.columns else []
            segments = self.df['细分'].unique().tolist() if '细分' in self.df.columns else []

            # 9. 组装模型数据
            self.model_data = {
                'kmeans_model': kmeans_model,
                'cluster_scaler': cluster_scaler,
                'best_k': n_clusters,
                'cluster_features': cluster_features,
                'cluster_profiles': cluster_profiles,
                'cluster_contribution': cluster_contribution,
                'customer_data': customer_data,
                'rules_single': rules_single,
                'feature_stats': feature_stats,
                'reference_date': customer_data['参考日期'].iloc[0] if '参考日期' in customer_data.columns else pd.Timestamp.now(),
                'categories': categories,
                'subcategories': subcategories,
                'regions': regions,
                'segments': segments,
            }

            # 10. 保存模型
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'wb') as f:
                pickle.dump(self.model_data, f)

            print(f"✓ 推荐模型已生成: {output_path}")

            return {
                "success": True,
                "model_path": str(output_file),
                "total_customers": len(customer_data),
                "n_clusters": n_clusters,
                "n_rules": len(rules_single),
                "n_subcategories": len(subcategories),
            }

        except Exception as e:
            print(f"✗ 模型构建失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _preprocess_data(self):
        """预处理数据"""
        self.df['订单日期'] = pd.to_datetime(self.df['订单日期'])
        num_cols = ['销售额', '数量', '折扣', '利润']
        for c in num_cols:
            if c in self.df.columns:
                self.df[c] = pd.to_numeric(self.df[c], errors='coerce')

    def _calculate_customer_features(self) -> pd.DataFrame:
        """计算客户 RFM 特征"""
        reference_date = self.df['订单日期'].max() + timedelta(days=1)

        customer_data = self.df.groupby('客户 ID').agg({
            '订单日期': lambda x: (reference_date - x.max()).days,  # R
            '订单 ID': 'nunique',  # F
            '销售额': 'sum',  # M
            '利润': 'sum',
            '数量': 'sum',
            '折扣': 'mean',
            '细分': 'first' if '细分' in self.df.columns else lambda x: '未知',
            '地区': 'first' if '地区' in self.df.columns else lambda x: '未知'
        }).reset_index()

        customer_data.columns = [
            '客户ID', 'R_最近购买天数', 'F_购买频次', 'M_消费金额',
            '总利润', '购买数量', '平均折扣', '客户细分', '地区'
        ]

        # 衍生特征
        customer_data['客单价'] = customer_data['M_消费金额'] / customer_data['F_购买频次'].replace(0, np.nan)
        customer_data['件单价'] = customer_data['M_消费金额'] / customer_data['购买数量'].replace(0, np.nan)
        customer_data['利润率'] = customer_data['总利润'] / customer_data['M_消费金额'].replace(0, np.nan) * 100

        # 清理数据
        customer_data = customer_data.replace([np.inf, -np.inf], np.nan).fillna(0)
        customer_data['参考日期'] = reference_date

        return customer_data

    def _perform_clustering(self, customer_data: pd.DataFrame, n_clusters: int):
        """执行 KMeans 聚类"""
        cluster_features = ['R_最近购买天数', 'F_购买频次', 'M_消费金额', '平均折扣', '客单价']
        X = customer_data[cluster_features].values

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        customer_data['客户分群'] = kmeans.fit_predict(X_scaled)

        return kmeans, scaler, cluster_features

    def _generate_cluster_profiles(self, customer_data: pd.DataFrame) -> pd.DataFrame:
        """生成聚类画像"""
        cluster_profiles = customer_data.groupby('客户分群').agg({
            '客户ID': 'count',
            'R_最近购买天数': 'mean',
            'F_购买频次': 'mean',
            'M_消费金额': 'mean',
            '总利润': 'mean',
            '平均折扣': 'mean',
            '客单价': 'mean'
        }).round(2)

        cluster_profiles.columns = [
            '客户数', '平均R', '平均F', '平均M',
            '平均利润', '平均折扣', '平均客单价'
        ]

        # 命名和策略 - 需要临时创建副本来比较
        cluster_profiles_temp = cluster_profiles.reset_index()

        # 为每个群体生成名称
        names = []
        for _, row in cluster_profiles_temp.iterrows():
            name = self._get_cluster_name(row, cluster_profiles_temp)
            names.append(name)

        cluster_profiles['群体名称'] = names
        cluster_profiles['营销策略'] = [self._get_marketing_strategy(n) for n in names]

        return cluster_profiles

    def _get_cluster_name(self, row: pd.Series, all_profiles: pd.DataFrame) -> str:
        """根据 RFM 命名群体"""
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

    def _calculate_cluster_contribution(self, customer_data: pd.DataFrame) -> list:
        """计算聚类贡献度"""
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
                "total_sales": float(row['M_消费金额']),
                "total_profit": float(row['总利润']),
                "sales_percentage": float(row['销售额占比']),
                "profit_percentage": float(row['利润占比'])
            })

        return contribution_list

    def _extract_feature_stats(self, customer_data: pd.DataFrame) -> dict:
        """提取特征统计信息"""
        stats = {}
        for col in ['R_最近购买天数', 'F_购买频次', 'M_消费金额', '平均折扣', '客单价']:
            if col in customer_data.columns:
                stats[col] = {
                    'mean': float(customer_data[col].mean()),
                    'std': float(customer_data[col].std()),
                    'min': float(customer_data[col].min()),
                    'max': float(customer_data[col].max()),
                }
        return stats

    def _process_association_rules(self, association_rules: list) -> pd.DataFrame:
        """处理关联规则为 DataFrame"""
        if not association_rules:
            return pd.DataFrame()

        rules_data = []
        for rule in association_rules:
            # 确保后项是单一商品
            if hasattr(rule, 'consequent') and rule.consequent:
                rules_data.append({
                    'antecedents': frozenset(rule.antecedents),
                    'consequents': frozenset([rule.consequent]),
                    'support': rule.support,
                    'confidence': rule.confidence,
                    'lift': rule.lift,
                    '后项商品': rule.consequent
                })

        return pd.DataFrame(rules_data) if rules_data else pd.DataFrame()
