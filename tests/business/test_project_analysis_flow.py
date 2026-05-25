"""Flow contract tests for ProjectAnalysisFlow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from backend.business.flows.project_analysis_flow import ProjectAnalysisFlow
from backend.models.project import Project, ProjectStatus
from backend.models.schemas import AssociationRule, AssociationRuleResponse
from backend.providers.container import ProvidersContainer
from tests.fakes.providers import (
    FakeAnalysisJobProvider,
    FakeAssociationRuleStoreProvider,
    FakeDatasetProvider,
    FakeGeneratedAssetProvider,
    FakeLLMProvider,
    FakeProjectFileStorageProvider,
    FakeProjectRepositoryProvider,
    FakeRecommendationModelStoreProvider,
    FakeSpeechSynthesisProvider,
    FakeTelemetryProvider,
)


def _make_container(tmp_path: Path, dataset: pd.DataFrame | None = None) -> ProvidersContainer:
    project_datasets: dict[str, pd.DataFrame] = {}
    return ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(project_datasets=project_datasets),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        speech=FakeSpeechSynthesisProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
    )


def _register_project(container: ProvidersContainer, dataset: pd.DataFrame | None) -> Project:
    repo: FakeProjectRepositoryProvider = container.repository  # type: ignore[assignment]
    project = Project(name="Flow Contract", status=ProjectStatus.PROCESSING)
    repo.projects[project.id] = project
    if dataset is not None:
        container.dataset.project_datasets[project.id] = dataset  # type: ignore[attr-defined]
        dataset_path = container.storage.get_project_dir(project.id) / "dataset.csv"
        dataset_path.parent.mkdir(parents=True, exist_ok=True)
        dataset_path.write_text("placeholder", encoding="utf-8")
    return project


def _patch_abilities(
    monkeypatch: pytest.MonkeyPatch,
    *,
    association: AssociationRuleResponse | None = None,
    prediction: dict[str, Any] | None = None,
    clustering: dict[str, Any] | None = None,
    model_build: dict[str, Any] | None = None,
    report_text: str = "# Flow Report",
    speech_text: str = "report speech",
) -> None:
    import backend.business.flows.project_analysis_flow as flow_module

    monkeypatch.setattr(
        flow_module,
        "analyze_association_rules",
        lambda *args, **kwargs: association
        or AssociationRuleResponse(
            success=True,
            message="ok",
            rules=[
                AssociationRule(
                    antecedents=["Milk"],
                    consequent="Bread",
                    support=0.2,
                    confidence=0.8,
                    lift=1.5,
                    strategy="bundle",
                )
            ],
        ),
    )
    monkeypatch.setattr(
        flow_module,
        "forecast_sales",
        lambda *args, **kwargs: prediction
        or {"success": True, "data": {"sales_r2": 0.91, "profit_r2": 0.82}},
    )
    monkeypatch.setattr(
        flow_module,
        "cluster_customers",
        lambda *args, **kwargs: clustering
        or {
            "success": True,
            "data": {
                "n_clusters": 4,
                "silhouette_score": 0.55,
                "total_customers": 1,
                "customer_rows": [{"客户ID": "C001", "客户分群": 0}],
            },
        },
    )
    monkeypatch.setattr(
        flow_module,
        "build_recommendation_model",
        lambda *args, **kwargs: model_build or {"success": True, "model_data": {"recipe": "fake"}},
    )
    monkeypatch.setattr(
        flow_module,
        "generate_analysis_report",
        lambda project, results: report_text,
    )
    monkeypatch.setattr(
        flow_module,
        "generate_speech_text",
        lambda project, results: speech_text,
    )


@pytest.mark.anyio
async def test_flow_completes_and_persists_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = _make_container(tmp_path)
    project = _register_project(container, pd.DataFrame({"x": [1, 2, 3]}))
    _patch_abilities(monkeypatch)

    flow = ProjectAnalysisFlow(container)
    await flow.run(project.id)

    stored = container.repository.get_project(project.id)
    assert stored is not None
    assert stored.status == ProjectStatus.COMPLETED
    assert stored.error_message is None
    assert stored.results is not None
    assert stored.results.association_rules == [
        {
            "antecedents": ["Milk"],
            "consequent": "Bread",
            "support": 0.2,
            "confidence": 0.8,
            "lift": 1.5,
            "strategy": "bundle",
        }
    ]
    assert stored.results.prediction_data == {"sales_r2": 0.91, "profit_r2": 0.82}
    assert stored.results.clustering_data is not None
    assert stored.results.clustering_data["customers_csv"].endswith("customers.csv")
    assert stored.results.report_path is not None
    assert stored.results.report_path.endswith(f"report_{project.id}.md")
    assert stored.results.audio_path is not None
    assert stored.results.audio_path.endswith(f"report_{project.id}.mp3")

    customers_path = container.storage.get_project_dir(project.id) / "customers.csv"
    assert customers_path.exists()

    assets: FakeGeneratedAssetProvider = container.assets  # type: ignore[assignment]
    assert assets.report_calls and assets.report_calls[0][0] == project.id
    assert assets.project_audio_calls and assets.project_audio_calls[0][0] == project.id

    models: FakeRecommendationModelStoreProvider = container.recommendation_models  # type: ignore[assignment]
    assert models.artifact is not None
    assert models.cache_cleared is True

    telemetry: FakeTelemetryProvider = container.telemetry  # type: ignore[assignment]
    actions = [event.action for event in telemetry.audit_events]
    assert "flow.started" in actions
    assert "flow.completed" in actions
    assert any(action == "flow.stage.completed" for action in actions)


@pytest.mark.anyio
async def test_flow_fails_when_dataset_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = _make_container(tmp_path)
    project = _register_project(container, dataset=None)
    _patch_abilities(monkeypatch)

    flow = ProjectAnalysisFlow(container)
    await flow.run(project.id)

    stored = container.repository.get_project(project.id)
    assert stored is not None
    assert stored.status == ProjectStatus.FAILED
    assert stored.error_message is not None
    assert "分析失败: 数据集不存在" in stored.error_message

    telemetry: FakeTelemetryProvider = container.telemetry  # type: ignore[assignment]
    failed_events = [
        event for event in telemetry.audit_events if event.action == "flow.stage.failed"
    ]
    assert failed_events
    assert failed_events[-1].redaction_summary.get("error_type") == "FileNotFoundError"


@pytest.mark.anyio
async def test_flow_marks_failed_when_report_persistence_breaks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = _make_container(tmp_path)
    project = _register_project(container, pd.DataFrame({"x": [1]}))
    _patch_abilities(monkeypatch)

    def _explode(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(container.assets, "save_project_report", _explode)

    flow = ProjectAnalysisFlow(container)
    await flow.run(project.id)

    stored = container.repository.get_project(project.id)
    assert stored is not None
    assert stored.status == ProjectStatus.FAILED
    assert stored.error_message is not None
    assert "分析失败: disk full" in stored.error_message

    telemetry: FakeTelemetryProvider = container.telemetry  # type: ignore[assignment]
    error_types = {
        event.redaction_summary.get("error_type")
        for event in telemetry.audit_events
        if event.action == "flow.stage.failed"
    }
    assert "RuntimeError" in error_types


@pytest.mark.anyio
async def test_flow_silently_returns_when_project_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = _make_container(tmp_path)
    flow = ProjectAnalysisFlow(container)

    await flow.run("non-existent-id")

    telemetry: FakeTelemetryProvider = container.telemetry  # type: ignore[assignment]
    assert telemetry.audit_events == []
