"""Local project workspace file storage adapter."""

from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd

from backend.providers.dtos import AssetReferenceDTO, DatasetReferenceDTO, UploadedFileDTO


class LocalProjectFileStorageAdapter:
    """Manage files under the current data/projects/{project_id} layout."""

    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = Path(data_dir)
        self.projects_dir = self.data_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def get_project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def save_uploaded_dataset(
        self,
        project_id: str,
        upload: UploadedFileDTO,
        content: bytes,
    ) -> DatasetReferenceDTO:
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        dataset_path = project_dir / "dataset.csv"
        dataset_path.write_bytes(content)
        return DatasetReferenceDTO(
            project_id=project_id, path=dataset_path, filename=upload.filename
        )

    def save_dataset(
        self,
        project_id: str,
        filename: str,
        stream: BinaryIO,
    ) -> DatasetReferenceDTO:
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        dataset_path = project_dir / "dataset.csv"
        content = stream.read()
        if isinstance(content, str):
            content = content.encode("utf-8")
        dataset_path.write_bytes(content)
        return DatasetReferenceDTO(project_id=project_id, path=dataset_path, filename=filename)

    def read_customers(self, project_id: str) -> list[dict[str, Any]]:
        customers_path = self.get_project_dir(project_id) / "customers.csv"
        if not customers_path.exists():
            return []
        return pd.read_csv(customers_path).to_dict(orient="records")

    def write_customers(self, project_id: str, rows: list[dict[str, Any]]) -> AssetReferenceDTO:
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        customers_path = project_dir / "customers.csv"
        pd.DataFrame(rows).to_csv(customers_path, index=False)
        return AssetReferenceDTO(path=customers_path, media_type="text/csv")

    def resolve_dataset(self, project_id: str) -> DatasetReferenceDTO | None:
        dataset_path = self.get_project_dir(project_id) / "dataset.csv"
        if not dataset_path.exists():
            return None
        return DatasetReferenceDTO(project_id=project_id, path=dataset_path, filename="dataset.csv")
