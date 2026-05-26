"""CSV-backed Retail V2 dataset adapter."""

from pathlib import Path
from typing import Any

import pandas as pd

from backend.core.errors import InfrastructureError, ValidationError
from backend.providers.dtos import RETAIL_RAW_SALES_COLUMNS, RetailDatasetReferenceDTO


class CsvRetailDatasetAdapter:
    """Load and save project-scoped Retail V2 CSV datasets."""

    RAW_FILENAME = "raw_sales.csv"
    CLEAN_FILENAME = "clean_sales.csv"

    def __init__(self, data_dir: str = "data") -> None:
        self.projects_dir = Path(data_dir) / "projects"

    def save_raw_sales(
        self,
        project_id: str,
        filename: str,
        content: bytes,
    ) -> RetailDatasetReferenceDTO:
        self._validate_identifier(project_id, "project_id")
        self._validate_filename(filename)
        path = self._dataset_dir(project_id) / self.RAW_FILENAME
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        except OSError as error:
            raise InfrastructureError(
                f"Failed to save Retail V2 raw sales for {project_id}"
            ) from error
        return self._ref(project_id, "raw", self.RAW_FILENAME, {"source_filename": filename})

    def load_raw_sales(self, project_id: str) -> pd.DataFrame:
        self._validate_identifier(project_id, "project_id")
        frame = self._load_csv(
            self._dataset_dir(project_id) / self.RAW_FILENAME, ("utf-8-sig", "gbk")
        )
        self.validate_raw_schema(frame)
        return frame

    def validate_raw_schema(self, raw_sales: Any) -> None:
        if not isinstance(raw_sales, pd.DataFrame):
            raise ValidationError("Retail V2 raw sales dataset must be a pandas DataFrame")
        missing = [column for column in RETAIL_RAW_SALES_COLUMNS if column not in raw_sales.columns]
        if missing:
            raise ValidationError(
                f"Retail V2 raw sales dataset missing columns: {', '.join(missing)}"
            )

    def save_clean_sales(
        self,
        project_id: str,
        rows: Any,
        name: str = CLEAN_FILENAME,
    ) -> RetailDatasetReferenceDTO:
        self._validate_identifier(project_id, "project_id")
        self._validate_filename(name)
        path = self._dataset_dir(project_id) / self.CLEAN_FILENAME
        frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(path, index=False, encoding="utf-8")
        except (OSError, ValueError) as error:
            raise InfrastructureError(
                f"Failed to save Retail V2 clean sales for {project_id}"
            ) from error
        return self._ref(project_id, "clean", self.CLEAN_FILENAME, {"name": name})

    def load_clean_sales(self, project_id: str) -> pd.DataFrame:
        self._validate_identifier(project_id, "project_id")
        return self._load_csv(
            self._dataset_dir(project_id) / self.CLEAN_FILENAME,
            ("utf-8",),
            dtype={
                "user_id": str,
                "item_id": str,
                "cat_l1_code": str,
                "cat_l2_code": str,
                "cat_l3_code": str,
            },
        )

    def _dataset_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id / "analysis" / "datasets"

    def _ref(
        self,
        project_id: str,
        dataset_type: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> RetailDatasetReferenceDTO:
        dataset_id = f"{dataset_type}-sales"
        return RetailDatasetReferenceDTO(
            id=dataset_id,
            project_id=project_id,
            type=dataset_type,
            name=name,
            storage_key=f"analysis/datasets/{name}",
            url=f"/api/analysis/projects/{project_id}/datasets/{dataset_id}",
            metadata=metadata or {},
        )

    @staticmethod
    def _load_csv(
        path: Path,
        encodings: tuple[str, ...],
        dtype: dict[str, type[str]] | None = None,
    ) -> pd.DataFrame:
        if not path.exists():
            raise InfrastructureError(f"Retail V2 dataset does not exist: {path.name}")

        last_error: Exception | None = None
        for encoding in encodings:
            try:
                return pd.read_csv(path, encoding=encoding, dtype=dtype)
            except UnicodeDecodeError as error:
                last_error = error
            except (OSError, pd.errors.ParserError) as error:
                raise InfrastructureError(
                    f"Failed to read Retail V2 dataset: {path.name}"
                ) from error

        raise InfrastructureError(
            f"Failed to decode Retail V2 dataset: {path.name}"
        ) from last_error

    @staticmethod
    def _validate_identifier(value: str, label: str) -> None:
        if not value or any(part in {"", ".", ".."} for part in Path(value).parts):
            raise ValidationError(f"Invalid {label}: {value}")
        if Path(value).name != value:
            raise ValidationError(f"Invalid {label}: {value}")

    @staticmethod
    def _validate_filename(filename: str) -> None:
        if not filename or Path(filename).name != filename or ".." in Path(filename).parts:
            raise ValidationError(f"Invalid Retail V2 dataset filename: {filename}")
