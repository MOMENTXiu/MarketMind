"""Global recommendation pipeline (user, item, realtime rules, tts, cache)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.abilities.association.calculate_realtime_rules import calculate_realtime_rules
from backend.abilities.recommendation.recommend_for_item import recommend_for_item
from backend.abilities.recommendation.recommend_for_user import recommend_for_user
from backend.core.errors import InfrastructureError, ProviderError
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import SpeechSynthesisRequestDTO


class RecommendationPipeline:
    """Global recommendation orchestration shared by /api/recommend/* endpoints."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def recommend_user(self, user_id: str, top_n: int = 10) -> dict[str, Any]:
        dataset = self.providers.dataset.load_default()
        artifact = self.providers.recommendation_models.load_model()
        model_data = artifact.payload if artifact is not None else None
        result = recommend_for_user(dataset, model_data, user_id, top_n=top_n)

        cluster = result.get("cluster")
        recommends = result.get("recommends", [])
        response: dict[str, Any] = {
            "item": user_id,
            "recommends": recommends,
            "target_customers": [cluster] if cluster else [],
            "speech": self._speech_from_cluster(cluster, recommends),
            "model_tries": 3,
            "human_fallback": False,
        }
        if artifact is None:
            response["warning"] = "预训练模型未加载，使用热门商品推荐"
        return response

    def recommend_item(self, item: str, top_n: int = 8) -> dict[str, Any]:
        dataset = self.providers.dataset.load_default()
        artifact = self.providers.recommendation_models.load_model()
        model_data = artifact.payload if artifact is not None else None
        result = recommend_for_item(
            model_data=model_data, item_name=item, top_n=top_n, dataset=dataset
        )
        return {"success": True, **result}

    def calculate_rules(
        self, item: str, min_confidence: float = 0.1, top_n: int = 10
    ) -> dict[str, Any]:
        dataset = self.providers.dataset.load_default()
        subcategories = self._extract_subcategories(dataset)
        if subcategories is not None and item not in subcategories:
            return {
                "success": False,
                "message": "商品不存在于数据集中",
                "item": item,
                "rules": [],
            }

        calculation = calculate_realtime_rules(
            dataset, item_name=item, min_confidence=min_confidence, top_n=top_n
        )
        if calculation.rows_to_persist:
            try:
                self.providers.association_rules.append_dynamic_rules(calculation.rows_to_persist)
            except Exception as exc:
                raise InfrastructureError(f"动态关联规则持久化失败: {exc}") from exc

        return {
            "success": True,
            "item": item,
            "rules": calculation.rules,
            "source": "realtime_calculation",
        }

    async def play_tts(self, project_id: str, speech: str) -> dict[str, Any]:
        filename = f"recommend_{project_id}.mp3"
        target = Path("outputs/audio") / filename
        try:
            result = await self.providers.speech.synthesize(
                SpeechSynthesisRequestDTO(text=speech, output_path=target)
            )
        except Exception as exc:
            raise ProviderError(f"语音合成失败: {exc}") from exc

        asset = self.providers.assets.save_public_audio(filename, result.audio_path)
        return {"success": True, "audio_url": asset.url or f"/outputs/audio/{filename}"}

    def clear_model_cache(self) -> None:
        self.providers.recommendation_models.clear_cache()

    @staticmethod
    def _speech_from_cluster(cluster: Any, recommends: list[dict[str, Any]]) -> str:
        items = "、".join(item.get("item", "") for item in recommends[:3])
        if not cluster:
            return f"为您精选热门商品：{items}。" if items else "暂无可用推荐。"
        cluster_name = cluster.get("cluster_name", "")
        strategy = cluster.get("strategy", "")
        suffix = f"。建议策略：{strategy}" if strategy else ""
        if not items:
            return f"您属于{cluster_name}{suffix}。"
        return f"您属于{cluster_name}，为您推荐：{items}{suffix}。"

    @staticmethod
    def _extract_subcategories(dataset: Any) -> list[str] | None:
        try:
            if "子类别" in getattr(dataset, "columns", []):
                return list(dataset["子类别"].dropna().unique())
        except Exception:
            return None
        return None
