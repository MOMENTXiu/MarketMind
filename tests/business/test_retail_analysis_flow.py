"""Business flow tests for Retail Analysis V2 lifecycle state."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from backend.business.flows.retail_analysis_flow import RetailAnalysisFlow
from backend.business.flows.retail_analysis_state import empty_marketer_insights
from backend.core.errors import NotFoundError
from backend.providers.container import ProvidersContainer
from tests.fakes.providers import (
    FakeAnalysisArtifactProvider,
    FakeAnalysisJobProvider,
    FakeAnalysisModelStoreProvider,
    FakeAssociationRuleStoreProvider,
    FakeDatasetProvider,
    FakeGeneratedAssetProvider,
    FakeLLMProvider,
    FakeProjectFileStorageProvider,
    FakeProjectRepositoryProvider,
    FakeRecommendationModelStoreProvider,
    FakeRegularizedDatasetProvider,
    FakeRetailDatasetProvider,
    FakeSpeechSynthesisProvider,
    FakeTelemetryProvider,
)

ROOT = Path(__file__).resolve().parents[2]
RAW_FIXTURE = ROOT / "tests" / "fixtures" / "analysis_v2" / "retail_sales_raw_gbk.csv"
REQUIRED_STAGE_NAMES = {
    "dataset_preparation",
    "feature_engineering",
    "segmentation",
    "association",
    "recommendation",
    "marketer_insights",
    "report",
}
DOWNSTREAM_STAGE_NAMES = tuple(
    stage for stage in REQUIRED_STAGE_NAMES if stage != "dataset_preparation"
)


def _make_container(tmp_path: Path) -> tuple[ProvidersContainer, FakeAnalysisJobProvider]:
    jobs = FakeAnalysisJobProvider()
    container = ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        retail_dataset=FakeRetailDatasetProvider(),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        analysis_artifacts=FakeAnalysisArtifactProvider(),
        analysis_models=FakeAnalysisModelStoreProvider(),
        speech=FakeSpeechSynthesisProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=jobs,
        telemetry=FakeTelemetryProvider(),
        regularized_dataset=FakeRegularizedDatasetProvider(),
    )
    return container, jobs


def _stage(state: dict[str, Any], stage_name: str) -> dict[str, Any]:
    return next(stage for stage in state["stage_statuses"] if stage["stage"] == stage_name)


def _stale_ref(project_id: str, artifact_id: str, artifact_type: str = "table") -> dict[str, Any]:
    return {
        "id": artifact_id,
        "type": artifact_type,
        "name": artifact_id.split(":", maxsplit=1)[-1],
        "url": f"/api/analysis/projects/{project_id}/artifacts/{artifact_id}",
        "metadata": {},
    }


def _seed_downstream_outputs(flow: RetailAnalysisFlow, project_id: str) -> set[str]:
    state = flow._load_state(project_id)
    stale_refs = [
        _stale_ref(project_id, "table:old_recommendations.csv"),
        _stale_ref(project_id, "retail_old_model:current", "model"),
    ]
    state["status"] = "completed"
    state["artifact_refs"] = [*list(state.get("artifact_refs", [])), *stale_refs]
    state["recommendations"] = [{"customer_id": "C001", "item": "old", "score": 1.0}]
    state["marketer_insights"] = {key: [{"stale": True}] for key in empty_marketer_insights()}
    for stage_name in DOWNSTREAM_STAGE_NAMES:
        stage = _stage(state, stage_name)
        stage["status"] = "completed"
        stage["error"] = None
        stage["artifact_refs"] = stale_refs
    flow._save_state(state)
    return {str(ref["id"]) for ref in stale_refs}


def _assert_downstream_outputs_cleared(
    flow: RetailAnalysisFlow, project_id: str, stale_ids: set[str]
) -> None:
    state = flow._load_state(project_id)
    assert state["recommendations"] == []
    assert state["marketer_insights"] == empty_marketer_insights()
    assert stale_ids.isdisjoint({artifact["id"] for artifact in state["artifact_refs"]})
    for stage_name in DOWNSTREAM_STAGE_NAMES:
        stage = _stage(state, stage_name)
        assert stage["status"] == "queued"
        assert stage["error"] is None
        assert stage["artifact_refs"] == []


def test_retail_analysis_flow_persists_project_dataset_and_schedules_job(
    tmp_path: Path,
) -> None:
    container, jobs = _make_container(tmp_path)
    flow = RetailAnalysisFlow(container)

    project = flow.create_project("Retail Flow", "state contract")
    upload = flow.upload_dataset(project["id"], RAW_FIXTURE.name, RAW_FIXTURE.read_bytes())
    run = flow.start_analysis(project["id"])

    assert project["status"] == "queued"
    assert upload["status"] == "queued"
    assert upload["dataset_ref"]["url"].startswith("/api/analysis/projects/")
    assert run["status"] == "processing"
    assert [job.project_id for job in jobs.jobs] == [project["id"]]

    stored = flow.get_project(project["id"])
    assert stored["status"] == "processing"
    assert {stage["stage"] for stage in stored["stage_statuses"]} == REQUIRED_STAGE_NAMES
    dataset_stage = next(
        stage for stage in stored["stage_statuses"] if stage["stage"] == "dataset_preparation"
    )
    assert dataset_stage["status"] == "completed"
    assert dataset_stage["artifact_refs"]


def test_retail_analysis_flow_lists_and_deletes_projects(tmp_path: Path) -> None:
    container, _ = _make_container(tmp_path)
    flow = RetailAnalysisFlow(container)

    first = flow.create_project("First Retail Project")
    second = flow.create_project("Second Retail Project")

    listed = flow.list_projects()
    assert listed["total"] == 2
    assert {project["id"] for project in listed["projects"]} == {first["id"], second["id"]}

    delete_result = flow.delete_project(first["id"])
    assert delete_result["deleted"] is True
    assert flow.list_projects()["total"] == 1
    with pytest.raises(NotFoundError):
        flow.get_project(first["id"])


def test_retail_analysis_run_is_idempotent_while_processing(tmp_path: Path) -> None:
    container, jobs = _make_container(tmp_path)
    flow = RetailAnalysisFlow(container)
    project = flow.create_project("Retail Flow", "idempotent run")
    flow.upload_dataset(project["id"], RAW_FIXTURE.name, RAW_FIXTURE.read_bytes())

    first = flow.start_analysis(project["id"])
    second = flow.start_analysis(project["id"])

    assert second["status"] == "processing"
    assert second["job_id"] == first["job_id"]
    assert second["trace_id"] == first["trace_id"]
    assert [job.project_id for job in jobs.jobs] == [project["id"]]


def test_scheduled_analysis_records_missing_clean_dataset_failure(tmp_path: Path) -> None:
    container, _ = _make_container(tmp_path)
    flow = RetailAnalysisFlow(container)
    project = flow.create_project("Retail Flow", "missing clean dataset")
    flow.upload_dataset(project["id"], RAW_FIXTURE.name, RAW_FIXTURE.read_bytes())
    container.retail_dataset.clean_sales.pop(project["id"])
    flow.start_analysis(project["id"])

    flow.execute_scheduled_analysis(project["id"])

    stored = flow.get_project(project["id"])
    assert stored["status"] == "failed"
    assert _stage(stored, "dataset_preparation")["status"] == "failed"
    for stage_name in DOWNSTREAM_STAGE_NAMES:
        assert _stage(stored, stage_name)["status"] == "skipped"


def test_scheduled_analysis_records_final_formatting_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container, _ = _make_container(tmp_path)
    flow = RetailAnalysisFlow(container)
    project = flow.create_project("Retail Flow", "format failure")
    flow.upload_dataset(project["id"], RAW_FIXTURE.name, RAW_FIXTURE.read_bytes())
    flow.start_analysis(project["id"])

    stage_results = {
        "feature_engineering": SimpleNamespace(customer_profile=[]),
        "segmentation": SimpleNamespace(customer_segments=[]),
        "association": SimpleNamespace(high_utility_itemsets=[], category_rules=[]),
        "recommendation": SimpleNamespace(recommendations=[]),
        "marketer_insights": SimpleNamespace(),
        "report": SimpleNamespace(),
    }

    def complete_stage(
        flow_self: RetailAnalysisFlow,
        state: dict[str, Any],
        stage: str,
        runner: Any,
    ) -> Any:
        flow_self._set_stage(state, stage, "completed", error=None, artifact_refs=[])
        flow_self._save_state(state)
        return stage_results[stage]

    def fail_format_recommendations(table: Any) -> list[dict[str, Any]]:
        raise RuntimeError("format failed")

    monkeypatch.setattr(RetailAnalysisFlow, "_run_stage", complete_stage)
    monkeypatch.setattr(
        "backend.business.flows.retail_analysis_flow.format_recommendations",
        fail_format_recommendations,
    )

    flow.execute_scheduled_analysis(project["id"])

    stored = flow.get_project(project["id"])
    assert stored["status"] == "failed"
    assert _stage(stored, "report")["status"] == "failed"
    assert "format failed" in str(stored["summary"].get("error"))


def test_new_upload_and_rerun_clear_stale_downstream_outputs(tmp_path: Path) -> None:
    container, jobs = _make_container(tmp_path)
    flow = RetailAnalysisFlow(container)

    rerun_project = flow.create_project("Retail Flow", "rerun stale cleanup")
    flow.upload_dataset(rerun_project["id"], RAW_FIXTURE.name, RAW_FIXTURE.read_bytes())
    rerun_stale_ids = _seed_downstream_outputs(flow, rerun_project["id"])

    flow.start_analysis(rerun_project["id"])

    assert [job.project_id for job in jobs.jobs] == [rerun_project["id"]]
    _assert_downstream_outputs_cleared(flow, rerun_project["id"], rerun_stale_ids)

    upload_project = flow.create_project("Retail Flow", "upload stale cleanup")
    flow.upload_dataset(upload_project["id"], RAW_FIXTURE.name, RAW_FIXTURE.read_bytes())
    upload_stale_ids = _seed_downstream_outputs(flow, upload_project["id"])

    flow.upload_dataset(upload_project["id"], RAW_FIXTURE.name, RAW_FIXTURE.read_bytes())

    _assert_downstream_outputs_cleared(flow, upload_project["id"], upload_stale_ids)


def test_retail_analysis_flow_records_small_dataset_failure_without_raising(
    tmp_path: Path,
) -> None:
    container, _ = _make_container(tmp_path)
    flow = RetailAnalysisFlow(container)
    project = flow.create_project("Small Retail Flow")
    flow.upload_dataset(project["id"], RAW_FIXTURE.name, RAW_FIXTURE.read_bytes())

    flow.execute_scheduled_analysis(project["id"])

    stored = flow.get_project(project["id"])
    assert stored["status"] in {"completed", "failed"}
    assert isinstance(stored["summary"], dict)
    if stored["status"] == "failed":
        assert any(stage["status"] == "failed" for stage in stored["stage_statuses"])

    artifacts = flow.list_artifacts(project["id"])
    assert artifacts["project_id"] == project["id"]
    assert all("path" not in artifact for artifact in artifacts["artifacts"])
    recommendations = flow.list_recommendations(project["id"], top_k=5)["recommendations"]
    assert isinstance(recommendations, list)
    for recommendation in recommendations:
        assert {"item", "score", "reason", "score_breakdown"}.issubset(recommendation)
    insights = flow.get_marketer_insights(project["id"])
    assert {"segment_value", "promotion_effect", "bundle_strategy", "category_strategy"}.issubset(
        insights
    )
