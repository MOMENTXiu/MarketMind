"""Generated asset provider interface."""

from pathlib import Path
from typing import Protocol

from backend.providers.dtos import AssetReferenceDTO


class GeneratedAssetProvider(Protocol):
    def save_project_report(
        self, project_id: str, filename: str, content: str
    ) -> AssetReferenceDTO:
        """Persist a generated Markdown report for a project."""

    def resolve_project_report(self, project_id: str) -> AssetReferenceDTO | None:
        """Resolve the current project report asset."""

    def save_project_audio(
        self, project_id: str, filename: str, source_path: Path
    ) -> AssetReferenceDTO:
        """Persist or register generated project audio."""

    def resolve_project_audio(self, project_id: str) -> AssetReferenceDTO | None:
        """Resolve the current project audio asset."""

    def save_public_audio(self, filename: str, source_path: Path) -> AssetReferenceDTO:
        """Persist audio served from the public outputs directory."""

    def save_ai_audio(self, filename: str, source_path: Path) -> AssetReferenceDTO:
        """Persist audio served by the AI voice broadcast endpoint."""

    def resolve_ai_audio(self, filename: str) -> AssetReferenceDTO | None:
        """Resolve AI voice audio using the current lookup order."""
