"""Generated asset provider interface."""

from typing import Protocol

from backend.providers.dtos import AssetReferenceDTO


class GeneratedAssetProvider(Protocol):
    def save_project_report(
        self, project_id: str, filename: str, content: str
    ) -> AssetReferenceDTO:
        """Persist a generated Markdown report for a project."""

    def resolve_project_report(self, project_id: str) -> AssetReferenceDTO | None:
        """Resolve the current project report asset."""
