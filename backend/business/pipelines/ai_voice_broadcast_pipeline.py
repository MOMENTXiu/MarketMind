"""AI voice broadcast pipeline composing LLM and TTS abilities."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from backend.abilities.voice.generate_broadcast_script import generate_broadcast_script
from backend.core.errors import NotFoundError, ProviderError, ValidationError
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import SpeechSynthesisRequestDTO


class AIVoiceBroadcastPipeline:
    """Generate broadcast script via LLM then synthesize and publish AI audio."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    async def broadcast(
        self,
        data: dict[str, Any],
        llm_config: dict[str, str],
        scene_type: str,
        tts_config: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not scene_type:
            raise ValidationError("缺少 scene_type")

        text = await generate_broadcast_script(
            data=data,
            llm_provider=self.providers.llm,
            llm_config=llm_config,
            scene_type=scene_type,
        )

        filename = f"{scene_type}_{abs(hash(text)) % 100000}.mp3"
        target_path = Path(tempfile.gettempdir()) / filename
        tts_config = tts_config or {}
        try:
            result = await self.providers.speech.synthesize(
                SpeechSynthesisRequestDTO(
                    text=text,
                    output_path=target_path,
                    voice=tts_config.get("voice"),
                    rate=tts_config.get("rate"),
                    volume=tts_config.get("volume"),
                )
            )
        except Exception as exc:
            raise ProviderError(f"AI 语音合成失败: {exc}") from exc

        asset = self.providers.assets.save_ai_audio(filename, result.audio_path)
        return {
            "success": True,
            "text": text,
            "audio_url": asset.url or f"/api/ai-voice/audio/{filename}/",
        }

    async def synthesize_tts(
        self,
        text: str,
        voice: str | None = None,
        rate: str | None = None,
        volume: str | None = None,
    ) -> dict[str, Any]:
        """Pure TTS path serving via the AI voice asset URL pattern."""

        if not text or not text.strip():
            raise ValidationError("文本不能为空")

        filename = f"tts_{abs(hash(text)) % 100000}.mp3"
        target_path = Path(tempfile.gettempdir()) / filename
        try:
            result = await self.providers.speech.synthesize(
                SpeechSynthesisRequestDTO(
                    text=text,
                    output_path=target_path,
                    voice=voice,
                    rate=rate,
                    volume=volume,
                )
            )
        except Exception as exc:
            raise ProviderError(f"AI 语音合成失败: {exc}") from exc

        asset = self.providers.assets.save_ai_audio(filename, result.audio_path)
        return {
            "success": True,
            "audio_url": asset.url or f"/api/ai-voice/audio/{filename}/",
        }

    def resolve_audio_path(self, filename: str) -> Path:
        """Locate an AI voice audio asset using the configured lookup order."""

        ref = self.providers.assets.resolve_ai_audio(filename)
        if ref is None:
            raise NotFoundError("音频文件不存在")
        return ref.path
