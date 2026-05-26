"""Business pipeline tests for Retail V2 analysis orchestration."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.business.pipelines.retail_association_pipeline import RetailAssociationPipeline
from backend.business.pipelines.retail_dataset_preparation_pipeline import (
    RetailDatasetPreparationPipeline,
)
from backend.business.pipelines.retail_feature_engineering_pipeline import (
    RetailFeatureEngineeringPipeline,
)
from backend.business.pipelines.retail_marketer_insight_pipeline import (
    RetailMarketerInsightPipeline,
)
from backend.business.pipelines.retail_recommendation_pipeline import RetailRecommendationPipeline
from backend.business.pipelines.retail_report_pipeline import RetailReportPipeline
from backend.business.pipelines.retail_segmentation_pipeline import RetailSegmentationPipeline
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
    FakeRetailDatasetProvider,
    FakeSpeechSynthesisProvider,
    FakeTelemetryProvider,
)

ROOT = Path(__file__).resolve().parents[2]
RAW_FIXTURE = ROOT / "tests" / "fixtures" / "analysis_v2" / "retail_sales_raw_gbk.csv"


def _make_container(
    tmp_path: Path,
) -> tuple[
    ProvidersContainer,
    FakeRetailDatasetProvider,
    FakeAnalysisArtifactProvider,
    FakeAnalysisModelStoreProvider,
]:
    retail_dataset = FakeRetailDatasetProvider()
    analysis_artifacts = FakeAnalysisArtifactProvider()
    analysis_models = FakeAnalysisModelStoreProvider()
    container = ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        retail_dataset=retail_dataset,
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        analysis_artifacts=analysis_artifacts,
        analysis_models=analysis_models,
        speech=FakeSpeechSynthesisProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
    )
    return container, retail_dataset, analysis_artifacts, analysis_models


def _make_clean_sales() -> pd.DataFrame:
    items = [
        ("10", "蔬果", "100", "蔬菜", "1001", "I001", 12.0, "生鲜"),
        ("10", "蔬果", "101", "水果", "1002", "I002", 16.0, "生鲜"),
        ("20", "粮油", "200", "米面", "2001", "I003", 20.0, "一般商品"),
        ("20", "粮油", "201", "食用油", "2002", "I004", 35.0, "一般商品"),
        ("30", "休闲", "300", "零食", "3001", "I005", 10.0, "一般商品"),
        ("40", "日配", "400", "乳品", "4001", "I006", 14.0, "一般商品"),
    ]
    basket_by_group = {
        "high": [0, 1, 2],
        "low": [3, 4, 5],
    }
    rows: list[dict[str, object]] = []
    sale_dates = pd.to_datetime(["2025-01-05", "2025-02-05", "2025-03-05", "2025-04-05"])

    for user_index in range(16):
        user_id = f"U{user_index:03d}"
        high_value = user_index < 8
        basket_name = "high" if high_value else "low"
        quantity = 2.0 if high_value else 1.0
        for month_index, sale_date in enumerate(sale_dates):
            for item_position, item_index in enumerate(basket_by_group[basket_name]):
                (
                    cat_l1_code,
                    cat_l1_name,
                    cat_l2_code,
                    cat_l3_name,
                    cat_l3_code,
                    item_id,
                    price,
                    item_type,
                ) = items[item_index]
                is_promo = int((user_index + month_index + item_position) % 3 == 0)
                rows.append(
                    {
                        "user_id": user_id,
                        "cat_l1_code": cat_l1_code,
                        "cat_l1_name": cat_l1_name,
                        "cat_l2_code": cat_l2_code,
                        "cat_l2_name": cat_l3_name,
                        "cat_l3_code": cat_l3_code,
                        "cat_l3_name": cat_l3_name,
                        "sale_date": sale_date,
                        "sale_month": sale_date.year * 100 + sale_date.month,
                        "item_id": item_id,
                        "spec": "standard",
                        "item_type": item_type,
                        "unit": "个",
                        "quantity": quantity,
                        "amount": price * quantity + (4.0 if is_promo else 0.0),
                        "unit_price": price,
                        "is_promo": is_promo,
                        "is_return": 0,
                        "weekday": sale_date.weekday(),
                        "is_weekend": int(sale_date.weekday() >= 5),
                        "week_of_year": int(sale_date.isocalendar().week),
                    }
                )
    return pd.DataFrame(rows)


def test_dataset_preparation_cleans_raw_sales_and_saves_quality_artifact(tmp_path: Path) -> None:
    container, retail_dataset, analysis_artifacts, _ = _make_container(tmp_path)

    result = RetailDatasetPreparationPipeline(container).run(
        "project-retail",
        "sales.csv",
        RAW_FIXTURE.read_bytes(),
    )

    assert result.project_id == "project-retail"
    assert result.raw_dataset_ref.type == "raw"
    assert result.clean_dataset_ref.type == "clean"
    assert len(result.clean_sales) == 5
    assert result.quality_summary["duplicate_rows_removed"] == 1
    assert "project-retail" in retail_dataset.clean_sales
    assert (
        "project-retail",
        "json:retail_quality_summary.json",
    ) in analysis_artifacts.refs


def test_feature_engineering_and_segmentation_save_expected_tables(tmp_path: Path) -> None:
    container, _, analysis_artifacts, analysis_models = _make_container(tmp_path)
    project_id = "project-retail"

    feature_result = RetailFeatureEngineeringPipeline(container).run(
        project_id, _make_clean_sales()
    )
    segmentation_result = RetailSegmentationPipeline(container).run(
        project_id,
        feature_result.customer_profile,
        segment_count=2,
    )

    assert not feature_result.customer_profile.empty
    assert not feature_result.product_profile.empty
    assert set(feature_result.artifact_refs) == {
        "price_rank",
        "repurchase_cycle",
        "customer_profile",
        "product_profile",
        "weights",
    }
    assert "promotion_weights" in feature_result.weights
    assert len(segmentation_result.customer_segments) == len(feature_result.customer_profile)
    assert segmentation_result.best_segment_count == 2
    assert segmentation_result.model_ref.model_type == "retail_customer_segmentation"
    assert analysis_models.load_model(project_id, "retail_customer_segmentation") == {
        "feature_columns": segmentation_result.feature_columns,
        "best_segment_count": 2,
    }
    assert (
        project_id,
        "table:retail_customer_segments.csv",
    ) in analysis_artifacts.refs


def test_downstream_pipelines_run_on_synthetic_clean_data(tmp_path: Path) -> None:
    container, _, analysis_artifacts, analysis_models = _make_container(tmp_path)
    project_id = "project-retail"
    clean_sales = _make_clean_sales()
    feature_result = RetailFeatureEngineeringPipeline(container).run(project_id, clean_sales)
    segmentation_result = RetailSegmentationPipeline(container).run(
        project_id,
        feature_result.customer_profile,
        segment_count=2,
    )

    association_result = RetailAssociationPipeline(container).run(project_id, clean_sales)
    recommendation_result = RetailRecommendationPipeline(container).run(
        project_id,
        clean_sales,
        users=["U000", "U008"],
        top_k=3,
    )
    marketer_result = RetailMarketerInsightPipeline(container).run(
        project_id,
        clean_sales,
        feature_result.customer_profile,
        segmentation_result.customer_segments,
        high_utility_itemsets=association_result.high_utility_itemsets,
        association_rules=association_result.category_rules,
        top_bundles=5,
    )
    report_result = RetailReportPipeline(container).run(
        project_id,
        feature_result=feature_result,
        segmentation_result=segmentation_result,
        association_result=association_result,
        recommendation_result=recommendation_result,
        marketer_result=marketer_result,
    )

    assert not association_result.comparison_summary.empty
    assert not association_result.high_utility_itemsets.empty
    assert not recommendation_result.recommendations.empty
    assert recommendation_result.model_ref.model_type == "retail_recommendation_signals"
    assert analysis_models.load_model(project_id, "retail_recommendation_signals") is not None
    assert not marketer_result.segment_value.empty
    assert not marketer_result.bundle_strategy.empty
    assert not marketer_result.category_strategy.empty
    assert "Retail V2 Analysis Report" in report_result.markdown
    assert "retail_analysis_report.md" == report_result.artifact_ref.name
    assert (
        project_id,
        "markdown:retail_analysis_report.md",
    ) in analysis_artifacts.refs
