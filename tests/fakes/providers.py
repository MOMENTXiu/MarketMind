"""Fake provider implementations that avoid network and persistent side effects."""

from pathlib import Path
from typing import Any

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

    def submit_project_analysis(self, job: AnalysisJobDTO, handler: Any) -> None:
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
