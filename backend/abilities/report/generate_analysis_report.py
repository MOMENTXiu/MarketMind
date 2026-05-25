"""Analysis report composition ability."""

from typing import Any


def generate_analysis_report(project: Any, results: Any) -> str:
    """Generate the current markdown analysis report from explicit inputs."""

    association_rules = _get(results, "association_rules", []) or []
    prediction_data = _get(results, "prediction_data", {}) or {}
    clustering_data = _get(results, "clustering_data", {}) or {}
    updated_at = _get(project, "updated_at")
    updated_text = updated_at.strftime("%Y-%m-%d %H:%M:%S") if updated_at else ""

    report = f"""# {_get(project, "name")} - 营销分析报告

**生成时间**: {updated_text}
**数据集**: {_get(project, "dataset_filename")}

---

## 1. 关联规则分析

本次分析发现 {len(association_rules)} 条关联规则。

### Top 10 规则

"""
    for index, rule in enumerate(association_rules[:10], 1):
        antecedents = ", ".join(_rule_value(rule, "antecedents", []))
        report += f"{index}. {antecedents} → **{_rule_value(rule, 'consequent', '')}**\n"
        report += f"   - 支持度: {_rule_value(rule, 'support', 0):.4f}\n"
        report += f"   - 置信度: {_rule_value(rule, 'confidence', 0):.4f}\n"
        report += f"   - 提升度: {_rule_value(rule, 'lift', 0):.4f}\n"
        report += f"   - 策略: {_rule_value(rule, 'strategy', '')}\n\n"

    report += """
---

## 2. 销售预测

"""
    if prediction_data.get("forecast_data"):
        report += f"""
**模型性能**:
- 销售额预测 R² 得分: {prediction_data.get("sales_r2", 0):.4f}
- 利润预测 R² 得分: {prediction_data.get("profit_r2", 0):.4f}
- 训练样本数: {prediction_data.get("train_samples", 0)}
- 预测周数: {prediction_data.get("forecast_weeks", 0)}

**未来{prediction_data.get("forecast_weeks", 0)}周预测**（显示前5周）:

"""
        for week_data in prediction_data.get("forecast_data", [])[:5]:
            report += f"- 第{week_data['week']}周: 销售额 {week_data['sales']:,.2f}元, 利润 {week_data['profit']:,.2f}元\n"
    else:
        report += "销售预测数据不可用\n"

    report += """
---

## 3. 客户聚类

"""
    if clustering_data.get("cluster_profiles"):
        report += f"""
**聚类概况**:
- 客户总数: {clustering_data.get("total_customers", 0)}
- 聚类数量: {clustering_data.get("n_clusters", 0)}
- 轮廓系数: {clustering_data.get("silhouette_score", 0):.4f}

**客户群体画像**:

"""
        for profile in clustering_data.get("cluster_profiles", []):
            report += f"""
### {profile["cluster_name"]} ({profile["customer_count"]}人)
- 平均最近购买天数: {profile["avg_recency"]:.0f}天
- 平均购买频次: {profile["avg_frequency"]:.1f}次
- 平均消费金额: {profile["avg_monetary"]:,.2f}元
- 平均客单价: {profile["avg_order_value"]:,.2f}元
- 营销策略: {profile["marketing_strategy"]}

"""
    else:
        report += "客户聚类数据不可用\n"

    report += """
---

## 总结

本报告基于 Apriori 算法进行关联规则分析、Ridge回归进行销售预测、K-Means算法进行客户聚类分析生成。
"""
    return report


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _rule_value(rule: Any, key: str, default: Any = None) -> Any:
    return _get(rule, key, default)
