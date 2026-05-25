"""Project workspace file provider interface."""

from pathlib import Path
from typing import Any, BinaryIO, Protocol

from backend.providers.dtos import AssetReferenceDTO, DatasetReferenceDTO, UploadedFileDTO


class ProjectFileStorageProvider(Protocol):
    def get_project_dir(self, project_id: str) -> Path:
        """Return the project workspace directory."""

    def save_uploaded_dataset(
        self,
        project_id: str,
        upload: UploadedFileDTO,
        content: bytes,
    ) -> DatasetReferenceDTO:
        """Persist an uploaded dataset using the current project path layout."""

    def save_dataset(
        self,
        project_id: str,
        filename: str,
        stream: BinaryIO,
    ) -> DatasetReferenceDTO:
        """Persist an uploaded dataset stream using current path layout."""

    def read_customers(self, project_id: str) -> list[dict[str, Any]]:
        """Read normalized customer records for a project."""

    def write_customers(self, project_id: str, rows: list[dict[str, Any]]) -> AssetReferenceDTO:
        """Persist generated customer rows for a project."""

    def resolve_dataset(self, project_id: str) -> DatasetReferenceDTO | None:
        """Resolve the current dataset for a project."""
