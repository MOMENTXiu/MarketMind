"""Retail V2 dataset provider interface."""

from typing import Any, Protocol

from backend.providers.dtos import RetailDatasetReferenceDTO


class RetailDatasetProvider(Protocol):
    def save_raw_sales(
        self,
        project_id: str,
        filename: str,
        content: bytes,
    ) -> RetailDatasetReferenceDTO:
        """Persist a raw Retail V2 sales upload behind an opaque dataset ref."""

    def load_raw_sales(self, project_id: str) -> Any:
        """Load raw Retail V2 sales rows and validate the source schema."""

    def validate_raw_schema(self, raw_sales: Any) -> None:
        """Validate required Chinese Retail V2 source columns."""

    def save_clean_sales(
        self,
        project_id: str,
        rows: Any,
        name: str = "clean_sales.csv",
    ) -> RetailDatasetReferenceDTO:
        """Persist cleaned Retail V2 sales rows behind an opaque dataset ref."""

    def load_clean_sales(self, project_id: str) -> Any:
        """Load cleaned Retail V2 sales rows for a project."""
