"""Fake provider implementations that avoid network and persistent side effects."""

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from backend.models.project import Project, ProjectCreate, ProjectStatus, ProjectUpdate
from backend.providers.analysis_event_stream_provider import InMemoryAnalysisEventStreamProvider
from backend.providers.analysis_job_queue_provider import InMemoryAnalysisJobQueueProvider
from backend.providers.dtos import (
    AnalysisArtifactPayloadDTO,
    AnalysisArtifactReferenceDTO,
    AnalysisJobDTO,
    AnalysisModelReferenceDTO,
    AssetReferenceDTO,
    DatasetReferenceDTO,
    LLMRequestDTO,
    LLMResponseDTO,
    ModelArtifactDTO,
    RegularizationSidecarReferenceDTO,
    RegularizedDatasetReferenceDTO,
    RetailDatasetReferenceDTO,
    UploadedFileDTO,
)
from backend.providers.retail_analysis_state_provider import InMemoryRetailAnalysisStateProvider
from backend.providers.telemetry_dtos import (
    AuditEvent,
    DebugEvent,
    ErrorEvent,
    SpanContext,
    SpanHandle,
    TelemetryResult,
)

FakeRetailAnalysisStateProvider = InMemoryRetailAnalysisStateProvider
FakeAnalysisJobQueueProvider = InMemoryAnalysisJobQueueProvider
FakeAnalysisEventStreamProvider = InMemoryAnalysisEventStreamProvider


class FakeLLMProvider:
    def __init__(self, text: str = "fake generated script") -> None:
        self.text = text
        self.requests: list[LLMRequestDTO] = []

    async def generate_text(self, request: LLMRequestDTO) -> LLMResponseDTO:
        self.requests.append(request)
        return LLMResponseDTO(text=self.text, provider=request.provider, model=request.model)


class FakeAnalysisJobProvider:
    def __init__(self) -> None:
        self.jobs: list[AnalysisJobDTO] = []

    def submit_project_analysis(self, job: AnalysisJobDTO, handler: Any | None = None) -> None:
        self.jobs.append(job)


class FakeTelemetryProvider:
    def __init__(self) -> None:
        self.debug_events: list[DebugEvent] = []
        self.audit_events: list[AuditEvent] = []
        self.error_events: list[ErrorEvent] = []

    def emit_debug(self, event: DebugEvent) -> TelemetryResult:
        self.debug_events.append(event)
        return TelemetryResult(success=True, sink="fake")

    def emit_audit(self, event: AuditEvent) -> TelemetryResult:
        self.audit_events.append(event)
        return TelemetryResult(success=True, sink="fake")

    def emit_error(self, event: ErrorEvent) -> TelemetryResult:
        self.error_events.append(event)
        return TelemetryResult(success=True, sink="fake")

    def start_span(self, name: str, context: SpanContext | None = None) -> SpanHandle:
        span_context = context or SpanContext(trace_id="trace-test", span_id="span-test")
        return SpanHandle(context=span_context, name=name)

    def end_span(self, span: SpanHandle, status: str = "completed") -> TelemetryResult:
        return TelemetryResult(success=True, sink=f"fake:{span.name}:{status}")


class FakeProjectFileStorageProvider:
    def __init__(self, root: Path) -> None:
        self.root = root

    def get_project_dir(self, project_id: str) -> Path:
        return self.root / project_id

    def save_uploaded_dataset(
        self,
        project_id: str,
        upload: UploadedFileDTO,
        content: bytes,
    ) -> DatasetReferenceDTO:
        path = self.get_project_dir(project_id) / "dataset.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return DatasetReferenceDTO(project_id=project_id, path=path, filename=upload.filename)

    def save_dataset(
        self,
        project_id: str,
        filename: str,
        stream: Any,
    ) -> DatasetReferenceDTO:
        path = self.get_project_dir(project_id) / "dataset.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = stream.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        path.write_bytes(data)
        return DatasetReferenceDTO(project_id=project_id, path=path, filename=filename)

    def read_customers(self, project_id: str) -> list[dict[str, Any]]:
        return [{"id": "fake-customer", "name": "Fake Customer"}]

    def write_customers(self, project_id: str, rows: list[dict[str, Any]]) -> AssetReferenceDTO:
        path = self.get_project_dir(project_id) / "customers.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(rows), encoding="utf-8")
        return AssetReferenceDTO(path=path, media_type="text/csv")

    def resolve_dataset(self, project_id: str) -> DatasetReferenceDTO | None:
        path = self.get_project_dir(project_id) / "dataset.csv"
        if not path.exists():
            return None
        return DatasetReferenceDTO(project_id=project_id, path=path, filename="dataset.csv")


class FakeRecommendationModelStoreProvider:
    def __init__(self) -> None:
        self.artifact: ModelArtifactDTO | None = None
        self.cache_cleared = False

    def load_model(self) -> ModelArtifactDTO | None:
        return self.artifact

    def save_model(self, payload: Any) -> ModelArtifactDTO:
        self.artifact = ModelArtifactDTO(path=Path("fake-model.pkl"), payload=payload)
        return self.artifact

    def clear_cache(self) -> None:
        self.cache_cleared = True


class FakeProjectRepositoryProvider:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    def create_project(self, data: ProjectCreate) -> Project:
        kwargs: dict[str, Any] = {"name": data.name, "description": data.description}
        if data.parameters is not None:
            kwargs["parameters"] = data.parameters
        if data.owner_user_id is not None:
            kwargs["owner_user_id"] = data.owner_user_id
        project = Project(**kwargs)
        self.projects[project.id] = project
        return project

    def get_project(self, project_id: str, owner_user_id: str | None = None) -> Project | None:
        project = self.projects.get(project_id)
        if project is None:
            return None
        if owner_user_id is not None and project.owner_user_id != owner_user_id:
            return None
        return project

    def list_projects(
        self, skip: int = 0, limit: int = 100, owner_user_id: str | None = None
    ) -> list[Project]:
        items = list(self.projects.values())
        if owner_user_id is not None:
            items = [p for p in items if p.owner_user_id == owner_user_id]
        return items[skip : skip + limit]

    def update_project(self, project_id: str, update_data: ProjectUpdate) -> Project | None:
        project = self.projects.get(project_id)
        if project is None:
            return None
        data = update_data.model_dump(exclude_none=True)
        updated = project.model_copy(update=data)
        self.projects[project_id] = updated
        return updated

    def mark_analysis_completed(self, project_id: str, results: Any) -> Project | None:
        project = self.projects.get(project_id)
        if project is None:
            return None
        updated = project.model_copy(
            update={
                "status": ProjectStatus.COMPLETED,
                "results": results,
                "error_message": None,
            }
        )
        self.projects[project_id] = updated
        return updated

    def mark_analysis_failed(self, project_id: str, error_message: str) -> Project | None:
        project = self.projects.get(project_id)
        if project is None:
            return None
        updated = project.model_copy(
            update={
                "status": ProjectStatus.FAILED,
                "error_message": error_message,
            }
        )
        self.projects[project_id] = updated
        return updated

    def delete_project(self, project_id: str, owner_user_id: str | None = None) -> bool:
        project = self.projects.get(project_id)
        if project is None:
            return False
        if owner_user_id is not None and project.owner_user_id != owner_user_id:
            return False
        return self.projects.pop(project_id, None) is not None

    def count_projects(self, owner_user_id: str | None = None) -> int:
        if owner_user_id is None:
            return len(self.projects)
        return sum(1 for p in self.projects.values() if p.owner_user_id == owner_user_id)


class FakeDatasetProvider:
    def __init__(
        self,
        default_dataset: pd.DataFrame | None = None,
        project_datasets: dict[str, pd.DataFrame] | None = None,
    ) -> None:
        self.default_dataset = default_dataset
        self.project_datasets = project_datasets or {}
        self.saved: list[tuple[Path, Any]] = []

    def load_dataset(self, path: Path) -> pd.DataFrame:
        if self.default_dataset is None:
            raise FileNotFoundError(str(path))
        return self.default_dataset.copy()

    def load_project_dataset(self, project_id: str) -> pd.DataFrame:
        if project_id not in self.project_datasets:
            raise FileNotFoundError(project_id)
        return self.project_datasets[project_id].copy()

    def load_default(self) -> pd.DataFrame:
        if self.default_dataset is None:
            raise FileNotFoundError("default dataset missing")
        return self.default_dataset.copy()

    def resolve_default_path(self) -> Path | None:
        return Path("data/dataset.csv") if self.default_dataset is not None else None

    def save_dataset(self, path: Path, rows: Any) -> None:
        self.saved.append((path, rows))


class FakeRetailDatasetProvider:
    def __init__(self) -> None:
        self.raw_sales: dict[str, pd.DataFrame] = {}
        self.clean_sales: dict[str, pd.DataFrame] = {}
        self.raw_uploads: list[tuple[str, str, bytes]] = []

    def save_raw_sales(
        self,
        project_id: str,
        filename: str,
        content: bytes,
    ) -> RetailDatasetReferenceDTO:
        self.raw_uploads.append((project_id, filename, content))
        try:
            self.raw_sales[project_id] = pd.read_csv(BytesIO(content))
        except UnicodeDecodeError:
            self.raw_sales[project_id] = pd.read_csv(BytesIO(content), encoding="gbk")
        return self._ref(project_id, "raw", "raw_sales.csv")

    def load_raw_sales(self, project_id: str) -> pd.DataFrame:
        if project_id not in self.raw_sales:
            raise FileNotFoundError(project_id)
        return self.raw_sales[project_id].copy()

    def validate_raw_schema(self, raw_sales: Any) -> None:
        if not isinstance(raw_sales, pd.DataFrame):
            raise TypeError("raw_sales must be a DataFrame")

    def save_clean_sales(
        self,
        project_id: str,
        rows: Any,
        name: str = "clean_sales.csv",
    ) -> RetailDatasetReferenceDTO:
        self.clean_sales[project_id] = (
            rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
        )
        return self._ref(project_id, "clean", name)

    def load_clean_sales(self, project_id: str) -> pd.DataFrame:
        if project_id not in self.clean_sales:
            raise FileNotFoundError(project_id)
        return self.clean_sales[project_id].copy()

    @staticmethod
    def _ref(project_id: str, dataset_type: str, name: str) -> RetailDatasetReferenceDTO:
        return RetailDatasetReferenceDTO(
            id=f"{dataset_type}-sales",
            project_id=project_id,
            type=dataset_type,
            name=name,
            storage_key=f"analysis/datasets/{name}",
            url=f"/api/analysis/projects/{project_id}/datasets/{dataset_type}-sales",
        )


class FakeAnalysisArtifactProvider:
    def __init__(self) -> None:
        self.refs: dict[tuple[str, str], AnalysisArtifactReferenceDTO] = {}

    def save_table(self, project_id: str, name: str, rows: Any) -> AnalysisArtifactReferenceDTO:
        return self._save(project_id, "table", name, {"rows": rows})

    def save_figure(
        self,
        project_id: str,
        name: str,
        content: bytes,
        media_type: str = "image/png",
    ) -> AnalysisArtifactReferenceDTO:
        return self._save(
            project_id, "figure", name, {"size_bytes": len(content), "media_type": media_type}
        )

    def save_markdown(
        self,
        project_id: str,
        name: str,
        content: str,
    ) -> AnalysisArtifactReferenceDTO:
        return self._save(
            project_id, "markdown", name, {"size_bytes": len(content.encode("utf-8"))}
        )

    def save_json(
        self,
        project_id: str,
        name: str,
        payload: dict[str, Any],
    ) -> AnalysisArtifactReferenceDTO:
        return self._save(project_id, "json", name, {"payload": dict(payload)})

    def resolve_artifact(
        self,
        project_id: str,
        artifact_id: str,
    ) -> AnalysisArtifactReferenceDTO | None:
        return self.refs.get((project_id, artifact_id))

    def load_payload(
        self,
        project_id: str,
        artifact_id: str,
    ) -> AnalysisArtifactPayloadDTO | None:
        ref = self.refs.get((project_id, artifact_id))
        if ref is None:
            return None
        if ref.type == "table":
            rows = ref.metadata.get("rows", [])
            if hasattr(rows, "to_dict"):
                rows = rows.to_dict(orient="records")
            return AnalysisArtifactPayloadDTO(ref=ref, payload_type="table", rows=_jsonable(rows))
        if ref.type == "json":
            return AnalysisArtifactPayloadDTO(
                ref=ref,
                payload_type="json",
                payload=_jsonable(ref.metadata.get("payload")),
            )
        if ref.type == "markdown":
            return AnalysisArtifactPayloadDTO(
                ref=ref,
                payload_type="markdown",
                content=str(ref.metadata.get("content", "")),
            )
        return AnalysisArtifactPayloadDTO(ref=ref, payload_type=ref.type)

    def _save(
        self,
        project_id: str,
        artifact_type: str,
        name: str,
        metadata: dict[str, Any],
    ) -> AnalysisArtifactReferenceDTO:
        artifact_id = f"{artifact_type}:{name}"
        ref = AnalysisArtifactReferenceDTO(
            id=artifact_id,
            project_id=project_id,
            type=artifact_type,
            name=name,
            url=f"/api/analysis/projects/{project_id}/artifacts/{artifact_id}",
            storage_key=f"analysis/artifacts/{artifact_type}/{name}",
            metadata=metadata,
        )
        self.refs[(project_id, artifact_id)] = ref
        return ref


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(inner) for key, inner in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(inner) for inner in value]
    if isinstance(value, str | int | bool) or value is None:
        return value
    if isinstance(value, float):
        return value if pd.notna(value) else None
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _jsonable(item())
        except (TypeError, ValueError):
            pass
    return str(value)


class FakeAnalysisModelStoreProvider:
    def __init__(self) -> None:
        self.payloads: dict[tuple[str, str, str], Any] = {}

    def save_model(
        self,
        project_id: str,
        model_type: str,
        payload: Any,
        version: str = "current",
        metadata: dict[str, Any] | None = None,
    ) -> AnalysisModelReferenceDTO:
        self.payloads[(project_id, model_type, version)] = payload
        return self._ref(project_id, model_type, version, metadata or {})

    def load_model(self, project_id: str, model_type: str, version: str = "current") -> Any | None:
        return self.payloads.get((project_id, model_type, version))

    def resolve_model(
        self,
        project_id: str,
        model_type: str,
        version: str = "current",
    ) -> AnalysisModelReferenceDTO | None:
        if (project_id, model_type, version) not in self.payloads:
            return None
        return self._ref(project_id, model_type, version, {})

    def list_models(self, project_id: str) -> list[AnalysisModelReferenceDTO]:
        return [
            self._ref(stored_project_id, model_type, version, {})
            for stored_project_id, model_type, version in sorted(self.payloads)
            if stored_project_id == project_id
        ]

    def delete_model(self, project_id: str, model_type: str, version: str = "current") -> bool:
        return self.payloads.pop((project_id, model_type, version), None) is not None

    @staticmethod
    def _ref(
        project_id: str,
        model_type: str,
        version: str,
        metadata: dict[str, Any],
    ) -> AnalysisModelReferenceDTO:
        return AnalysisModelReferenceDTO(
            id=f"{model_type}:{version}",
            project_id=project_id,
            type="model",
            name=model_type,
            model_type=model_type,
            version=version,
            url=f"/api/analysis/projects/{project_id}/models/{model_type}/{version}",
            storage_key=f"analysis/models/{model_type}/{version}.pkl",
            metadata=metadata,
        )


class FakeAssociationRuleStoreProvider:
    def __init__(self, rules: pd.DataFrame | None = None) -> None:
        self.rules = rules if rules is not None else pd.DataFrame()
        self.appended: list[list[dict[str, Any]]] = []
        self.saved: list[tuple[Path, Any]] = []

    def load_rules(
        self, project_id: str | None = None, dataset_path: Path | None = None
    ) -> pd.DataFrame:
        return self.rules.copy()

    def append_dynamic_rules(self, rows: list[dict[str, Any]]) -> None:
        self.appended.append(list(rows))

    def save_rules(self, path: Path, rows: Any) -> None:
        self.saved.append((path, rows))


class FakeGeneratedAssetProvider:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.report_calls: list[tuple[str, str, str]] = []

    def save_project_report(
        self, project_id: str, filename: str, content: str
    ) -> AssetReferenceDTO:
        self.report_calls.append((project_id, filename, content))
        path = self.root / project_id / filename
        return AssetReferenceDTO(path=path, media_type="text/markdown")

    def resolve_project_report(self, project_id: str) -> AssetReferenceDTO | None:
        return None


class FakeRegularizedDatasetProvider:
    def __init__(self) -> None:
        self.raw_uploads: dict[tuple[str, str], tuple[str, bytes]] = {}
        self.normalized: dict[tuple[str, str], pd.DataFrame] = {}
        self.sidecars: dict[tuple[str, str, str], dict[str, Any]] = {}

    def save_raw_upload(
        self,
        project_id: str,
        job_id: str,
        filename: str,
        content: bytes,
    ) -> RegularizedDatasetReferenceDTO:
        self.raw_uploads[(project_id, job_id)] = (filename, content)
        return self._dataset_ref(project_id, job_id, "raw_upload", filename)

    def load_raw_upload(
        self,
        project_id: str,
        job_id: str,
        ref: RegularizedDatasetReferenceDTO,
    ) -> bytes:
        return self.raw_uploads.get((project_id, job_id), ("", b""))[1]

    def save_normalized_dataset(
        self,
        project_id: str,
        job_id: str,
        dataframe: Any,
    ) -> RegularizedDatasetReferenceDTO:
        self.normalized[(project_id, job_id)] = (
            dataframe.copy() if hasattr(dataframe, "copy") else dataframe
        )
        return self._dataset_ref(project_id, job_id, "normalized_dataset", "dataset.csv")

    def load_normalized_dataset(
        self,
        project_id: str,
        job_id: str,
        ref: RegularizedDatasetReferenceDTO,
    ) -> Any:
        return self.normalized.get((project_id, job_id))

    def save_sidecar(
        self,
        project_id: str,
        job_id: str,
        sidecar_type: str,
        payload: dict[str, Any],
    ) -> RegularizationSidecarReferenceDTO:
        import copy

        self.sidecars[(project_id, job_id, sidecar_type)] = copy.deepcopy(payload)
        return self._sidecar_ref(project_id, job_id, sidecar_type)

    def load_sidecar(
        self,
        project_id: str,
        job_id: str,
        ref: RegularizationSidecarReferenceDTO,
    ) -> dict[str, Any]:
        import copy

        return copy.deepcopy(self.sidecars.get((project_id, job_id, ref.sidecar_type), {}))

    def resolve_dataset_ref(
        self,
        project_id: str,
        job_id: str,
        ref_id: str,
    ) -> RegularizedDatasetReferenceDTO | None:
        if ref_id == "raw-upload" and (project_id, job_id) in self.raw_uploads:
            return self._dataset_ref(
                project_id, job_id, "raw_upload", self.raw_uploads[(project_id, job_id)][0]
            )
        if ref_id == "normalized-dataset" and (project_id, job_id) in self.normalized:
            return self._dataset_ref(project_id, job_id, "normalized_dataset", "dataset.csv")
        return None

    def resolve_sidecar_ref(
        self,
        project_id: str,
        job_id: str,
        ref_id: str,
    ) -> RegularizationSidecarReferenceDTO | None:
        prefix = "sidecar:"
        if not ref_id.startswith(prefix):
            return None
        sidecar_type = ref_id[len(prefix) :]
        if (project_id, job_id, sidecar_type) in self.sidecars:
            return self._sidecar_ref(project_id, job_id, sidecar_type)
        return None

    def list_sidecars(
        self,
        project_id: str,
        job_id: str,
    ) -> list[RegularizationSidecarReferenceDTO]:
        refs: list[RegularizationSidecarReferenceDTO] = []
        for key in sorted(self.sidecars):
            if key[:2] == (project_id, job_id):
                refs.append(self._sidecar_ref(project_id, job_id, key[2]))
        return refs

    @staticmethod
    def _dataset_ref(
        project_id: str, job_id: str, ds_type: str, name: str
    ) -> RegularizedDatasetReferenceDTO:
        ref_id = "raw-upload" if ds_type == "raw_upload" else "normalized-dataset"
        return RegularizedDatasetReferenceDTO(
            id=ref_id,
            project_id=project_id,
            job_id=job_id,
            type=ds_type,
            name=name,
            storage_key=f"analysis/regularization/{job_id}/{name}",
            url=f"/api/analysis/jobs/{job_id}/datasets/{ref_id}?project_id={project_id}",
            metadata={},
        )

    @staticmethod
    def _sidecar_ref(
        project_id: str, job_id: str, sidecar_type: str
    ) -> RegularizationSidecarReferenceDTO:
        return RegularizationSidecarReferenceDTO(
            id=f"sidecar:{sidecar_type}",
            project_id=project_id,
            job_id=job_id,
            sidecar_type=sidecar_type,
            name=f"{sidecar_type}.json",
            storage_key=f"analysis/regularization/{job_id}/{sidecar_type}.json",
            url=f"/api/analysis/jobs/{job_id}/sidecars/sidecar:{sidecar_type}?project_id={project_id}",
            metadata={},
        )
