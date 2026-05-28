"""Regularized dataset provider interface for the data-processing chain."""

from __future__ import annotations

from typing import Any, Protocol

from backend.providers.dtos import (
    RegularizationSidecarReferenceDTO,
    RegularizedDatasetReferenceDTO,
)


class RegularizedDatasetProvider(Protocol):
    def save_raw_upload(
        self,
        project_id: str,
        job_id: str,
        filename: str,
        content: bytes,
    ) -> RegularizedDatasetReferenceDTO:
        """Persist a raw data upload behind an opaque dataset ref."""

    def load_raw_upload(
        self,
        project_id: str,
        job_id: str,
        ref: RegularizedDatasetReferenceDTO,
    ) -> bytes:
        """Load raw upload bytes for a project/job."""

    def save_normalized_dataset(
        self,
        project_id: str,
        job_id: str,
        dataframe: Any,
    ) -> RegularizedDatasetReferenceDTO:
        """Persist a normalized dataset behind an opaque ref."""

    def load_normalized_dataset(
        self,
        project_id: str,
        job_id: str,
        ref: RegularizedDatasetReferenceDTO,
    ) -> Any:
        """Load normalized dataset dataframe for a project/job."""

    def save_sidecar(
        self,
        project_id: str,
        job_id: str,
        sidecar_type: str,
        payload: dict[str, Any],
    ) -> RegularizationSidecarReferenceDTO:
        """Persist a JSON sidecar (capability, mapping, quality, manifest, preview)."""

    def load_sidecar(
        self,
        project_id: str,
        job_id: str,
        ref: RegularizationSidecarReferenceDTO,
    ) -> dict[str, Any]:
        """Load a JSON sidecar payload for a project/job."""

    def resolve_dataset_ref(
        self,
        project_id: str,
        job_id: str,
        ref_id: str,
        owner_user_id: str | None = None,
    ) -> RegularizedDatasetReferenceDTO | None:
        """Resolve an opaque dataset ref id to a typed DTO, optionally scoped to an owner."""

    def resolve_sidecar_ref(
        self,
        project_id: str,
        job_id: str,
        ref_id: str,
        owner_user_id: str | None = None,
    ) -> RegularizationSidecarReferenceDTO | None:
        """Resolve an opaque sidecar ref id to a typed DTO, optionally scoped to an owner."""

    def list_sidecars(
        self,
        project_id: str,
        job_id: str,
        owner_user_id: str | None = None,
    ) -> list[RegularizationSidecarReferenceDTO]:
        """List all sidecar refs for a project/job, optionally scoped to an owner."""
