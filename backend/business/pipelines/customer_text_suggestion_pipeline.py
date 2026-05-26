"""Text-only customer suggestion pipeline."""

from __future__ import annotations

from typing import Any

from backend.abilities.retail.generate_customer_text_suggestion import (
    generate_customer_text_suggestion,
)
from backend.providers.container import ProvidersContainer


class CustomerTextSuggestionPipeline:
    """Generate customer analysis suggestions without speech synthesis side effects."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    async def generate(
        self,
        data: dict[str, Any],
        llm_config: dict[str, str | None],
    ) -> dict[str, Any]:
        text = await generate_customer_text_suggestion(data, self.providers.llm, llm_config)
        return {
            "success": True,
            "text": text,
            "metadata": {
                "provider": llm_config.get("provider"),
                "model": llm_config.get("modelName"),
                "scene_type": "customer",
            },
        }
