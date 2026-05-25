"""Speech synthesis ability."""

from pathlib import Path

from backend.providers.dtos import SpeechSynthesisRequestDTO, SpeechSynthesisResultDTO
from backend.providers.speech_synthesis_provider import SpeechSynthesisProvider


async def synthesize_speech(
    text: str,
    output_path: str | Path,
    speech_provider: SpeechSynthesisProvider,
    voice: str | None = None,
    rate: str | None = None,
    volume: str | None = None,
) -> SpeechSynthesisResultDTO:
    """Synthesize speech through a provider boundary."""

    return await speech_provider.synthesize(
        SpeechSynthesisRequestDTO(
            text=text,
            output_path=Path(output_path),
            voice=voice,
            rate=rate,
            volume=volume,
        )
    )
