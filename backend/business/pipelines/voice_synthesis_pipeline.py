"""Generic text-to-speech synthesis pipeline."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from backend.core.errors import ProviderError, ValidationError
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import SpeechSynthesisRequestDTO


class VoiceSynthesisPipeline:
    """Synthesize speech and publish via the public audio outputs directory."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        rate: str | None = None,
        volume: str | None = None,
    ) -> dict[str, Any]:
        if not text or not text.strip():
            raise ValidationError("文本不能为空")

        filename = f"tts_{uuid.uuid4().hex}.mp3"
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
            raise ProviderError(f"语音合成失败: {exc}") from exc

        asset = self.providers.assets.save_public_audio(filename, result.audio_path)
        return {
            "success": True,
            "audio_url": asset.url or f"/outputs/audio/{filename}",
            "text": text,
        }
