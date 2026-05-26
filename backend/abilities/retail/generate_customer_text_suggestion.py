"""Customer text suggestion generation ability."""

from __future__ import annotations

from typing import Any

from backend.providers.dtos import LLMMessageDTO, LLMRequestDTO
from backend.providers.llm_provider import LLMProvider

CUSTOMER_TEXT_SUGGESTION_PROMPT = """你是一位专业数据分析师，正在为运营团队提供客户分析建议。

关键要求：
1. 直接以核心发现开头，格式："客户[姓名-ID]被分类为'[分群名称]'，其消费行为特征如下："
2. 采用三段式结构，每段简洁有力：
   - 【核心现状】用具体数字描述客户的RFM特征和消费水平
   - 【关键洞察】基于分群特征，分析该客户的价值潜力和行为模式
   - 【行动方案】给出2-3条具体可执行的营销建议，包含预期效果
3. 控制在80-120字以内
4. 严禁输出代码、JSON、markdown格式或任何非文本内容"""


async def generate_customer_text_suggestion(
    data: dict[str, Any],
    llm_provider: LLMProvider,
    llm_config: dict[str, str | None],
) -> str:
    """Generate a customer suggestion with LLM and current deterministic fallback."""

    request = LLMRequestDTO(
        provider=str(llm_config.get("provider") or "openai"),
        base_url=str(llm_config.get("baseUrl") or ""),
        api_key=llm_config.get("apiKey"),
        model=str(llm_config.get("modelName") or ""),
        messages=[
            LLMMessageDTO(role="system", content=CUSTOMER_TEXT_SUGGESTION_PROMPT),
            LLMMessageDTO(role="user", content=f"数据：{data}"),
        ],
        timeout_seconds=30.0,
        extra={"scene_type": "customer", "max_tokens": 400, "temperature": 0.7},
    )
    try:
        response = await llm_provider.generate_text(request)
        return response.text.strip()
    except Exception:
        return generate_customer_text_suggestion_fallback(data)


def generate_customer_text_suggestion_fallback(data: dict[str, Any]) -> str:
    """Generate deterministic customer suggestion text when LLM generation fails."""

    customer_name = data.get("customer_name", "客户")
    customer_id = data.get("customer_id", "未知")
    cluster_name = data.get("cluster_name", "客户群体")
    monetary = _to_float(data.get("monetary"), default=0.0)
    frequency = _to_float(data.get("frequency"), default=0.0)
    recency = data.get("recency", 0)
    average_order = monetary / frequency if frequency > 0 else 0
    return (
        f"客户{customer_name}-{customer_id}被分类为'{cluster_name}'，其消费行为特征如下："
        f"最近{recency}天购买，累计消费{frequency:.0f}次，客单价约{average_order:.0f}元。"
        "该客户属于稳定型消费者，复购意愿较强。建议：1)推送个性化商品推荐，提升客单价；"
        "2)设置会员专属福利，巩固忠诚度；3)定期触达维护客户关系，预计可提升15%消费额。"
    )


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
