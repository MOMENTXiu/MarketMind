"""Edge TTS speech synthesis adapter."""

from collections.abc import Awaitable, Callable

import edge_tts

from backend.core.errors import ProviderError
from backend.providers.dtos import SpeechSynthesisRequestDTO, SpeechSynthesisResultDTO


class EdgeTtsSpeechSynthesisAdapter:
    """Speech synthesis provider implemented with edge-tts."""

    def __init__(
        self,
        communicate_factory: Callable[..., object] | None = None,
        voice_list_provider: Callable[[], Awaitable[list[dict]]] | None = None,
    ) -> None:
        self.communicate_factory = communicate_factory or edge_tts.Communicate
        self.voice_list_provider = voice_list_provider or edge_tts.list_voices

    async def synthesize(self, request: SpeechSynthesisRequestDTO) -> SpeechSynthesisResultDTO:
        try:
            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            communicate = self.communicate_factory(
                request.text,
                request.voice,
                rate=request.rate or "+0%",
                volume=request.volume or "+0%",
            )
            await communicate.save(str(request.output_path))
            return SpeechSynthesisResultDTO(audio_path=request.output_path)
        except Exception as exc:
            raise ProviderError(f"Speech synthesis failed: {exc}") from exc

    async def list_voices(self) -> list[dict[str, str]]:
        try:
            voices = await self.voice_list_provider()
        except Exception as exc:
            raise ProviderError(f"Voice list failed: {exc}") from exc

        return [
            {
                "name": str(voice.get("ShortName", "")),
                "locale": str(voice.get("Locale", "")),
                "gender": str(voice.get("Gender", "")),
            }
            for voice in voices
        ]
