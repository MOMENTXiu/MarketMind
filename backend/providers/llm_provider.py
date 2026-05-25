"""LLM provider interface."""

from typing import Protocol

from backend.providers.dtos import LLMRequestDTO, LLMResponseDTO


class LLMProvider(Protocol):
    async def generate_text(self, request: LLMRequestDTO) -> LLMResponseDTO:
        """Generate text from an internal LLM request DTO."""
