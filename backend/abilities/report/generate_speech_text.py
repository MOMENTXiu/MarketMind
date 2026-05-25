"""Analysis speech text composition ability."""

from typing import Any


def generate_speech_text(project: Any, results: Any) -> str:
    """Generate the current analysis speech text from explicit inputs."""

    association_rules = _get(results, "association_rules", []) or []
    prediction_data = _get(results, "prediction_data", {}) or {}
    clustering_data = _get(results, "clustering_data", {}) or {}
    speech = f"""
{_get(project, "name")}营销分析报告播报。

本次分析共发现{len(association_rules)}条关联规则。

"""
    if association_rules:
        speech += "以下是支持度最高的前三条规则：\n\n"
        for index, rule in enumerate(association_rules[:3], 1):
            antecedents = "、".join(_rule_value(rule, "antecedents", []))
            speech += (
                f"第{index}条规则：{antecedents}，推荐搭配{_rule_value(rule, 'consequent', '')}。"
            )
            speech += f"置信度{_rule_value(rule, 'confidence', 0) * 100:.1f}%，提升度{_rule_value(rule, 'lift', 0):.2f}倍。"
            speech += f"建议策略：{_rule_value(rule, 'strategy', '')}。\n\n"

    if prediction_data.get("forecast_data"):
        forecast_list = prediction_data.get("forecast_data", [])[:3]
        speech += (
            f"\n销售预测模型训练完成，销售额预测R²得分{prediction_data.get('sales_r2', 0):.2f}，"
            f"利润预测R²得分{prediction_data.get('profit_r2', 0):.2f}。"
        )
        speech += f"未来{prediction_data.get('forecast_weeks', 0)}周预测显示，"
        if forecast_list:
            speech += f"第1周预计销售额{forecast_list[0]['sales']:,.0f}元，利润{forecast_list[0]['profit']:,.0f}元。"

    if clustering_data.get("cluster_profiles"):
        speech += (
            f"\n\n客户聚类分析将{clustering_data.get('total_customers', 0)}位客户"
            f"分为{clustering_data.get('n_clusters', 0)}个群体。"
        )
        profiles = sorted(
            clustering_data.get("cluster_profiles", []),
            key=lambda item: item["customer_count"],
            reverse=True,
        )[:2]
        for profile in profiles:
            speech += f"{profile['cluster_name']}共{profile['customer_count']}人，平均消费{profile['avg_monetary']:,.0f}元。"
            speech += f"建议策略：{profile['marketing_strategy'].split('、')[0]}。"

    speech += "\n\n报告播报完毕。"
    return speech


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _rule_value(rule: Any, key: str, default: Any = None) -> Any:
    return _get(rule, key, default)
