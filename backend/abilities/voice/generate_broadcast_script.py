"""AI broadcast script generation ability."""

from typing import Any

from backend.providers.dtos import LLMMessageDTO, LLMRequestDTO
from backend.providers.llm_provider import LLMProvider

PROMPTS = {
    "clustering": """你是一位资深零售数据分析师。请将以下客户聚类分析数据转化为一段专业的营销播报词（100-150字）。

播报要求：
1. 说明这是哪个客户群体，有多少人
2. 描述该群体的核心消费特征（用具体数字）
3. 给出2-3条具体的营销建议
4. 用商业播报的语气，简洁有力

严禁输出代码、JSON或markdown格式，只输出纯文字播报内容。""",
    "association": """你是一位资深零售数据分析师。请将以下商品关联规则分析数据转化为一段专业的营销播报词（100-150字）。

播报要求：
1. 说明发现了哪些商品关联
2. 用具体数字说明关联强度
3. 给出具体的捆绑销售建议
4. 用商业播报的语气，简洁有力

严禁输出代码、JSON或markdown格式，只输出纯文字播报内容。""",
    "prediction": """你是一位资深零售数据分析师。请将以下销售预测数据转化为一段专业的营销播报词（100-150字）。

播报要求：
1. 说明预测的时间范围和趋势
2. 用具体数字描述预测结果
3. 给出备货和促销建议
4. 用商业播报的语气，简洁有力

严禁输出代码、JSON或markdown格式，只输出纯文字播报内容。""",
    "summary": """你是一位专业数据分析师，正在为管理团队提供客户分析报告。

关键要求：
1. 严格禁止使用："各位同事"、"大家好"、"请注意"、"亲爱的"等任何客套话或开场白
2. 必须直接以核心发现开头，格式："客户[姓名-ID]被分类为'[分群名称]'，其消费行为特征如下："
3. 采用三段式结构，每段简洁有力：
   - 【核心现状】用具体数字描述客户的RFM特征和消费水平
   - 【关键洞察】基于分群特征，分析该客户的价值潜力和行为模式
   - 【行动方案】给出2-3条具体可执行的营销建议，包含预期效果

4. 控制在80-120字以内
5. 严禁输出代码、JSON、markdown格式或任何非文本内容""",
}


async def generate_broadcast_script(
    data: dict[str, Any],
    llm_provider: LLMProvider,
    llm_config: dict[str, str],
    scene_type: str,
) -> str:
    """Generate broadcast text through an LLM provider with current fallback text."""

    system_prompt = PROMPTS.get(scene_type, PROMPTS["summary"])
    request = LLMRequestDTO(
        provider=llm_config["provider"],
        base_url=llm_config["baseUrl"],
        api_key=llm_config.get("apiKey"),
        model=llm_config["modelName"],
        messages=[
            LLMMessageDTO(role="system", content=system_prompt),
            LLMMessageDTO(role="user", content=f"数据：{data}"),
        ],
        timeout_seconds=30.0,
        extra={"scene_type": scene_type, "max_tokens": 400, "temperature": 0.7},
    )
    try:
        response = await llm_provider.generate_text(request)
        return response.text.strip()
    except Exception:
        return generate_fallback_script(data, scene_type)


def generate_fallback_script(data: dict[str, Any], scene_type: str) -> str:
    """Generate current fallback broadcast script when LLM generation fails."""

    if scene_type == "clustering":
        return (
            f"根据RFM聚类分析，识别出{data.get('cluster_name', '客户群体')}，"
            f"共{data.get('customer_count', '若干')}位客户，最近消费距今{data.get('recency', 0)}天，"
            f"平均消费{data.get('frequency', 0)}次，客单价{data.get('avg_order_value', 0)}元。"
            f"建议{data.get('marketing_strategy', '采取针对性营销策略')}，"
            "通过优化商品推荐和专属优惠活动，提升该群体的复购率和客单价。"
        )
    if scene_type == "association":
        return "通过商品关联规则分析，发现多组商品存在显著购买关联性，支持度和置信度均达标。建议将关联商品就近摆放，推出组合促销套餐，预计可提升15%到25%的连带销售率，并在收银台设置关联商品提醒。"
    if scene_type == "prediction":
        return "基于时间序列预测模型，销售数据呈现季节性波动和上升趋势，预计未来销量保持稳定增长。建议提前做好库存准备，确保热销商品充足供应，关注天气和节假日因素，灵活调整备货和促销策略。"

    customer_name = data.get("customer_name", "客户")
    customer_id = data.get("customer_id", "未知")
    cluster_name = data.get("cluster_name", "客户群体")
    monetary = data.get("monetary", 0)
    frequency = data.get("frequency", 0)
    recency = data.get("recency", 0)
    avg_order = monetary / frequency if frequency > 0 else 0
    return (
        f"客户{customer_name}-{customer_id}被分类为'{cluster_name}'，其消费行为特征如下："
        f"最近{recency}天购买，累计消费{frequency}次，客单价约{avg_order:.0f}元。"
        "该客户属于稳定型消费者，复购意愿较强。建议：1)推送个性化商品推荐，提升客单价；"
        "2)设置会员专属福利，巩固忠诚度；3)定期触达维护客户关系，预计可提升15%消费额。"
    )
