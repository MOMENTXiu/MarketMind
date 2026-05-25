"""Fake provider implementations that avoid network and persistent side effects."""

from pathlib import Path
from typing import Any

import pandas as pd

from backend.models.project import Project, ProjectCreate, ProjectStatus, ProjectUpdate
from backend.providers.dtos import (
    AnalysisJobDTO,
    AssetReferenceDTO,
    DatasetReferenceDTO,
    LLMRequestDTO,
    LLMResponseDTO,
    ModelArtifactDTO,
    SpeechSynthesisRequestDTO,
    SpeechSynthesisResultDTO,
    UploadedFileDTO,
)
from backend.providers.telemetry_dtos import (
    AuditEvent,
    DebugEvent,
    ErrorEvent,
    SpanContext,
    SpanHandle,
    TelemetryResult,
)


class FakeSpeechSynthesisProvider:
    def __init__(self) -> None:
        self.requests: list[SpeechSynthesisRequestDTO] = []

    async def synthesize(self, request: SpeechSynthesisRequestDTO) -> SpeechSynthesisResultDTO:
        self.requests.append(request)
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"fake-audio")
        return SpeechSynthesisResultDTO(
            audio_path=request.output_path, audio_url="/outputs/audio/fake.mp3"
        )

    async def list_voices(self) -> list[dict[str, str]]:
        return [{"name": "fake", "locale": "zh-CN"}]


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
        project = Project(**kwargs)
        self.projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Project | None:
        return self.projects.get(project_id)

    def list_projects(self, skip: int = 0, limit: int = 100) -> list[Project]:
        items = list(self.projects.values())
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

    def delete_project(self, project_id: str) -> bool:
        return self.projects.pop(project_id, None) is not None

    def count_projects(self) -> int:
        return len(self.projects)


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
        self.public_audio_calls: list[tuple[str, Path]] = []
        self.ai_audio_calls: list[tuple[str, Path]] = []
        self.report_calls: list[tuple[str, str, bytes]] = []
        self.project_audio_calls: list[tuple[str, str, Path]] = []

    def save_project_report(
        self, project_id: str, filename: str, content: bytes
    ) -> AssetReferenceDTO:
        self.report_calls.append((project_id, filename, content))
        path = self.root / project_id / filename
        return AssetReferenceDTO(path=path, media_type="text/markdown")

    def resolve_project_report(self, project_id: str, filename: str) -> AssetReferenceDTO | None:
        return None

    def save_project_audio(
        self, project_id: str, filename: str, source_path: Path
    ) -> AssetReferenceDTO:
        self.project_audio_calls.append((project_id, filename, source_path))
        path = self.root / project_id / filename
        return AssetReferenceDTO(path=path, url=f"/projects/{project_id}/audio/{filename}")

    def resolve_project_audio(self, project_id: str, filename: str) -> AssetReferenceDTO | None:
        return None

    def save_public_audio(self, filename: str, source_path: Path) -> AssetReferenceDTO:
        self.public_audio_calls.append((filename, source_path))
        path = self.root / "public" / filename
        return AssetReferenceDTO(
            path=path, url=f"/outputs/audio/{filename}", media_type="audio/mpeg"
        )

    def save_ai_audio(self, filename: str, source_path: Path) -> AssetReferenceDTO:
        self.ai_audio_calls.append((filename, source_path))
        path = self.root / "ai_audio" / filename
        return AssetReferenceDTO(
            path=path, url=f"/api/ai-voice/audio/{filename}/", media_type="audio/mpeg"
        )

    def resolve_ai_audio(self, filename: str) -> AssetReferenceDTO | None:
        return None
