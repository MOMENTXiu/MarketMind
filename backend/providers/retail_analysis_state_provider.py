"""Retail Analysis state provider interface used before runtime cutover."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from backend.providers.dtos import (
    RetailAnalysisProjectStateDTO,
    RetailAnalysisProjectSummaryDTO,
    RetailAnalysisRunInfoDTO,
)


class RetailAnalysisStateProvider(Protocol):
    def save_state(self, state: RetailAnalysisProjectStateDTO) -> RetailAnalysisProjectStateDTO:
        """Persist one JSON-safe Retail V2 project state snapshot."""

    def get_state(self, project_id: str) -> RetailAnalysisProjectStateDTO | None:
        """Return one Retail V2 project state snapshot when it exists."""

    def save_run_info(
        self,
        project_id: str,
        run_info: RetailAnalysisRunInfoDTO,
    ) -> RetailAnalysisProjectStateDTO | None:
        """Persist latest run metadata without exposing storage primitives."""

    def list_projects(self) -> list[RetailAnalysisProjectSummaryDTO]:
        """List Retail V2 project summaries newest first."""

    def delete_project(self, project_id: str) -> bool:
        """Delete one Retail V2 project state snapshot when it exists."""


class InMemoryRetailAnalysisStateProvider:
    """Transitional in-memory implementation for Phase 1/2 contract coverage only."""

    def __init__(self) -> None:
        self._states: dict[str, RetailAnalysisProjectStateDTO] = {}

    def save_state(self, state: RetailAnalysisProjectStateDTO) -> RetailAnalysisProjectStateDTO:
        self._states[state.id] = state
        return state

    def get_state(self, project_id: str) -> RetailAnalysisProjectStateDTO | None:
        return self._states.get(project_id)

    def save_run_info(
        self,
        project_id: str,
        run_info: RetailAnalysisRunInfoDTO,
    ) -> RetailAnalysisProjectStateDTO | None:
        current = self._states.get(project_id)
        if current is None:
            return None

        updated = replace(
            current,
            run_info=run_info,
            status=run_info.status,
            error=run_info.error,
            updated_at=run_info.updated_at or current.updated_at,
        )
        self._states[project_id] = updated
        return updated

    def list_projects(self) -> list[RetailAnalysisProjectSummaryDTO]:
        states = sorted(
            self._states.values(),
            key=lambda state: (state.created_at or "", state.id),
            reverse=True,
        )
        return [_summary_from_state(state) for state in states]

    def delete_project(self, project_id: str) -> bool:
        return self._states.pop(project_id, None) is not None


def _summary_from_state(state: RetailAnalysisProjectStateDTO) -> RetailAnalysisProjectSummaryDTO:
    job_id = state.run_info.job_id if state.run_info is not None else None
    trace_id = state.run_info.trace_id if state.run_info is not None else None
    return RetailAnalysisProjectSummaryDTO(
        id=state.id,
        name=state.name,
        description=state.description,
        status=state.status,
        dataset_ref=state.dataset_ref,
        dataset_filename=_dataset_filename_from_state(state),
        quality_summary=state.quality_summary,
        artifact_refs=state.artifact_refs,
        recommendations=state.recommendations,
        marketer_insights=state.marketer_insights,
        stage_statuses=state.stage_statuses,
        summary=state.summary,
        job_id=job_id,
        trace_id=trace_id,
        run_info=state.run_info,
        error=state.error,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


def _dataset_filename(dataset_ref: dict[str, object] | None) -> str | None:
    if not isinstance(dataset_ref, dict):
        return None
    name = dataset_ref.get("name")
    return str(name) if name else None


def _dataset_filename_from_state(state: RetailAnalysisProjectStateDTO) -> str | None:
    ref = state.dataset_ref
    if isinstance(ref, dict):
        name = ref.get("name")
        if name:
            return str(name)
    summary = state.summary
    if isinstance(summary, dict):
        name = summary.get("dataset_filename")
        if name:
            return str(name)
    return None
