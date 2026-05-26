"""Golden tests for regularization ability atoms."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.abilities.regularization.check_analysis_capability import check_analysis_capability
from backend.abilities.regularization.check_data_quality import check_data_quality
from backend.abilities.regularization.infer_schema_mapping import infer_schema_mapping
from backend.abilities.regularization.normalize_business_fields import normalize_business_fields
from backend.abilities.regularization.normalize_field_types import normalize_field_types
from backend.abilities.regularization.profile_source_schema import profile_source_schema
from backend.abilities.regularization.read_source_table import read_source_table

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "data_processing"


class TestReadSourceTable:
    def test_reads_csv_with_utf8(self) -> None:
        df, meta = read_source_table((FIXTURES / "mini_retail.csv").read_bytes(), "mini_retail.csv")
        assert len(df) == 5
        assert "user_id" in df.columns
        assert meta["format"] == "csv"

    def test_reads_csv_with_gbk(self) -> None:
        content = "顾客编号,销售金额\nU001,100\n".encode("gbk")
        df, meta = read_source_table(content, "sales.csv")
        assert len(df) == 1
        assert meta["encoding"] == "gbk"


class TestProfileSourceSchema:
    def test_profiles_mini_retail(self) -> None:
        df, _ = read_source_table((FIXTURES / "mini_retail.csv").read_bytes(), "mini_retail.csv")
        profile = profile_source_schema(df)
        assert "amount" in profile
        assert profile["amount"]["dtype"] == "object" or profile["amount"]["dtype"] == "int64"
        assert profile["amount"]["missing_rate"] == 0.0


class TestInferSchemaMapping:
    def test_maps_chinese_aliases(self) -> None:
        df, _ = read_source_table(
            (FIXTURES / "missing_optional.csv").read_bytes(), "missing_optional.csv"
        )
        profile = profile_source_schema(df)
        mapping, detail = infer_schema_mapping(list(df.columns), profile)
        assert "顾客编号" in mapping
        assert mapping["顾客编号"] == "user_id"
        assert "销售金额" in mapping
        assert mapping["销售金额"] == "amount"

    def test_need_review_for_weak_matches(self) -> None:
        df, _ = read_source_table((FIXTURES / "mini_retail.csv").read_bytes(), "mini_retail.csv")
        profile = profile_source_schema(df)
        mapping, detail = infer_schema_mapping(list(df.columns), profile)
        for d in detail:
            if d["raw_column"] in mapping:
                assert d["status"] in {"auto_confirmed", "need_review", "weak_candidate"}


class TestNormalizeFieldTypes:
    def test_normalizes_dates_and_numerics(self) -> None:
        df, _ = read_source_table((FIXTURES / "mini_retail.csv").read_bytes(), "mini_retail.csv")
        profile = profile_source_schema(df)
        mapping, _ = infer_schema_mapping(list(df.columns), profile)
        norm, stats = normalize_field_types(df, mapping)
        assert "sale_date" in norm.columns
        assert pd.api.types.is_datetime64_any_dtype(norm["sale_date"])
        assert "amount" in norm.columns
        assert pd.api.types.is_numeric_dtype(norm["amount"])
        assert stats["date_parsed_rate"] is not None


class TestNormalizeBusinessFields:
    def test_generates_order_id_when_missing(self) -> None:
        df, _ = read_source_table(
            (FIXTURES / "missing_optional.csv").read_bytes(), "missing_optional.csv"
        )
        profile = profile_source_schema(df)
        mapping, _ = infer_schema_mapping(list(df.columns), profile)
        norm, _ = normalize_field_types(df, mapping)
        biz, rules = normalize_business_fields(norm)
        assert "order_id" in biz.columns
        assert "order_id_source" in biz.columns
        assert any("pseudo" in r for r in rules)

    def test_computes_missing_unit_price(self) -> None:
        df = pd.DataFrame(
            {
                "amount": [100, 200],
                "quantity": [2, 4],
            }
        )
        biz, rules = normalize_business_fields(df)
        assert "unit_price" in biz.columns
        assert any("derived" in r for r in rules)
        assert biz["unit_price"].iloc[0] == 50.0


class TestCheckDataQuality:
    def test_quality_scores_present(self) -> None:
        df, _ = read_source_table((FIXTURES / "mini_retail.csv").read_bytes(), "mini_retail.csv")
        profile = profile_source_schema(df)
        mapping, _ = infer_schema_mapping(list(df.columns), profile)
        norm, _ = normalize_field_types(df, mapping)
        biz, _ = normalize_business_fields(norm)
        quality = check_data_quality(df, biz, mapping, 0)
        scores = quality["scores"]
        assert "S_field" in scores
        assert "S_valid" in scores
        assert "S_complete" in scores
        assert "S_volume" in scores
        assert 0 <= scores["S_field"] <= 1


class TestCheckAnalysisCapability:
    def test_full_capability_on_complete_data(self) -> None:
        df, _ = read_source_table((FIXTURES / "mini_retail.csv").read_bytes(), "mini_retail.csv")
        profile = profile_source_schema(df)
        mapping, _ = infer_schema_mapping(list(df.columns), profile)
        norm, _ = normalize_field_types(df, mapping)
        biz, _ = normalize_business_fields(norm)
        cap = check_analysis_capability(biz)
        assert cap["can_run_sales_stats"] is True
        assert cap["can_run_time_trend"] is True
        assert cap["can_run_customer_profile"] is True
        assert cap["can_run_association"] is True
        assert cap["can_run_recommendation"] is True
        assert cap["can_run_promotion_analysis"] is True

    def test_skipped_capabilities_on_sparse_data(self) -> None:
        df = pd.DataFrame(
            {
                "user_id": ["U001"],
                "amount": [10],
            }
        )
        cap = check_analysis_capability(df)
        assert cap["can_run_association"] is False
        assert cap["can_run_recommendation"] is False
        assert cap["can_run_promotion_analysis"] is False
