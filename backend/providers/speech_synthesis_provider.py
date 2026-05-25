"""Speech synthesis provider interface."""

from typing import Protocol

from backend.providers.dtos import SpeechSynthesisRequestDTO, SpeechSynthesisResultDTO


class SpeechSynthesisProvider(Protocol):
    async def synthesize(self, request: SpeechSynthesisRequestDTO) -> SpeechSynthesisResultDTO:
        """Generate speech audio from text."""

    async def list_voices(self) -> list[dict[str, str]]:
        """Return available voice summaries."""
