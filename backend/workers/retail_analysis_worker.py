"""Stable RQ worker entry point for Retail analysis jobs."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from backend.business.flows.retail_analysis_flow import RetailAnalysisFlow
from backend.core.config import Settings
from backend.core.errors import ValidationError
from backend.infrastructure.factories.provider_factory import create_providers
from backend.providers.container import ProvidersContainer


class RetailAnalysisWorkerPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    trigger: str = Field(min_length=1)
    attempt: int = Field(ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


def validate_retail_analysis_job_payload(payload: dict[str, Any]) -> RetailAnalysisWorkerPayload:
    try:
        return RetailAnalysisWorkerPayload.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError("Invalid Retail analysis worker payload") from exc


def execute_retail_analysis_business_entry(
    providers: ProvidersContainer,
    project_id: str,
    *,
    job_id: str,
    trace_id: str,
    attempt: int,
) -> None:
    RetailAnalysisFlow(providers).execute_scheduled_analysis(
        project_id,
        job_id=job_id,
        trace_id=trace_id,
        attempt=attempt,
    )


def execute_retail_analysis_job(
    payload: dict[str, Any],
    *,
    dry_run: bool = False,
    settings: Settings | None = None,
    provider_factory: Callable[..., ProvidersContainer] = create_providers,
) -> dict[str, Any]:
    validated = validate_retail_analysis_job_payload(payload)
    worker_settings = settings or Settings()
    providers = provider_factory(worker_settings)

    if dry_run:
        return {
            "status": "dry_run",
            "project_id": validated.project_id,
            "job_id": validated.job_id,
            "trace_id": validated.trace_id,
            "attempt": validated.attempt,
            "task_queue_backend": worker_settings.TASK_QUEUE_BACKEND,
            "providers": {
                "retail_analysis_state": type(providers.retail_analysis_state).__name__,
                "analysis_job_queue": type(providers.analysis_job_queue).__name__,
                "analysis_event_stream": type(providers.analysis_event_stream).__name__,
            },
        }

    execute_retail_analysis_business_entry(
        providers,
        validated.project_id,
        job_id=validated.job_id,
        trace_id=validated.trace_id,
        attempt=validated.attempt,
    )
    return {
        "status": "completed",
        "project_id": validated.project_id,
        "job_id": validated.job_id,
        "trace_id": validated.trace_id,
        "attempt": validated.attempt,
    }
