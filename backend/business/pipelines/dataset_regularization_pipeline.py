"""Dataset regularization pipeline: raw upload -> normalized dataset + sidecars."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from backend.abilities.regularization.check_analysis_capability import check_analysis_capability
from backend.abilities.regularization.check_data_quality import check_data_quality
from backend.abilities.regularization.infer_schema_mapping import infer_schema_mapping
from backend.abilities.regularization.normalize_business_fields import normalize_business_fields
from backend.abilities.regularization.normalize_field_types import normalize_field_types
from backend.abilities.regularization.profile_source_schema import profile_source_schema
from backend.abilities.regularization.read_source_table import read_source_table
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import (
    RegularizationSidecarReferenceDTO,
    RegularizedDatasetReferenceDTO,
)

VERSION = "v1.0.0"


@dataclass(frozen=True)
class DatasetRegularizationResult:
    normalized_dataset_ref: RegularizedDatasetReferenceDTO
    mapping_ref: RegularizationSidecarReferenceDTO
    mapping_detail_ref: RegularizationSidecarReferenceDTO
    profile_ref: RegularizationSidecarReferenceDTO
    quality_ref: RegularizationSidecarReferenceDTO
    capability_ref: RegularizationSidecarReferenceDTO
    manifest_ref: RegularizationSidecarReferenceDTO
    preview_ref: RegularizationSidecarReferenceDTO
    quality: dict[str, Any]
    capability: dict[str, Any]
    mapping_detail: list[dict[str, Any]]
    needs_review: bool


class DatasetRegularizationPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self,
        project_id: str,
        job_id: str,
        filename: str,
        content: bytes,
    ) -> DatasetRegularizationResult:
        raw_df, meta = read_source_table(content, filename)
        n_raw = len(raw_df)
        raw_df = raw_df.drop_duplicates().reset_index(drop=True)
        dup_removed = n_raw - len(raw_df)

        profile = profile_source_schema(raw_df)
        mapping, mapping_detail = infer_schema_mapping(list(raw_df.columns), profile)

        type_df, type_stats = normalize_field_types(raw_df, mapping)
        biz_df, rules = normalize_business_fields(type_df)
        quality = check_data_quality(raw_df, biz_df, mapping, dup_removed)
        capability = check_analysis_capability(biz_df)

        manifest = {
            "regularization_version": VERSION,
            "raw_filename": meta.get("raw_filename", filename),
            "format": meta.get("format"),
            "encoding": meta.get("encoding"),
            "sheet_name": meta.get("sheet_name"),
            "header_row": meta.get("header_row"),
            "created_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "rules_applied": ["field_alias_mapping", "type_normalization"] + rules,
            "type_stats": type_stats,
        }

        self.providers.regularized_dataset.save_raw_upload(project_id, job_id, filename, content)
        norm_ref = self.providers.regularized_dataset.save_normalized_dataset(
            project_id, job_id, biz_df
        )
        mapping_ref = self.providers.regularized_dataset.save_sidecar(
            project_id, job_id, "schema_mapping", mapping
        )
        mapping_detail_ref = self.providers.regularized_dataset.save_sidecar(
            project_id, job_id, "schema_mapping_detail", mapping_detail
        )
        profile_ref = self.providers.regularized_dataset.save_sidecar(
            project_id, job_id, "field_profile", profile
        )
        quality_ref = self.providers.regularized_dataset.save_sidecar(
            project_id, job_id, "quality_report", quality
        )
        capability_ref = self.providers.regularized_dataset.save_sidecar(
            project_id, job_id, "capability", capability
        )
        manifest_ref = self.providers.regularized_dataset.save_sidecar(
            project_id, job_id, "manifest", manifest
        )
        preview_ref = self.providers.regularized_dataset.save_sidecar(
            project_id, job_id, "preview_rows", biz_df.head(8).astype(str).to_dict("records")
        )

        needs_review = any(d.get("status") == "need_review" for d in mapping_detail)

        return DatasetRegularizationResult(
            normalized_dataset_ref=norm_ref,
            mapping_ref=mapping_ref,
            mapping_detail_ref=mapping_detail_ref,
            profile_ref=profile_ref,
            quality_ref=quality_ref,
            capability_ref=capability_ref,
            manifest_ref=manifest_ref,
            preview_ref=preview_ref,
            quality=quality,
            capability=capability,
            mapping_detail=mapping_detail,
            needs_review=needs_review,
        )
