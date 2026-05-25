"""Contract tests for the Retail V2 cleaning ability."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.abilities.retail.clean_retail_sales import CLEAN_COLUMNS, clean_retail_sales
from backend.core.errors import ValidationError

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "analysis_v2" / "retail_sales_raw_gbk.csv"


def load_raw_sales_fixture() -> pd.DataFrame:
    return pd.read_csv(FIXTURE)


def test_clean_retail_sales_returns_backend_clean_schema() -> None:
    result = clean_retail_sales(load_raw_sales_fixture())
    clean_sales = result.clean_sales

    assert clean_sales.columns.tolist() == CLEAN_COLUMNS
    assert len(clean_sales) == 5
    assert clean_sales["user_id"].tolist() == ["0001", "0002", "0003", "0004", "0005"]
    assert str(clean_sales["sale_date"].dtype).startswith("datetime64")
    assert pd.api.types.is_integer_dtype(clean_sales["sale_month"])
    assert pd.api.types.is_integer_dtype(clean_sales["is_promo"])
    assert pd.api.types.is_integer_dtype(clean_sales["is_return"])
    assert pd.api.types.is_integer_dtype(clean_sales["weekday"])
    assert pd.api.types.is_integer_dtype(clean_sales["is_weekend"])
    assert pd.api.types.is_integer_dtype(clean_sales["week_of_year"])


def test_clean_retail_sales_applies_v2_quality_rules() -> None:
    result = clean_retail_sales(load_raw_sales_fixture())
    clean_sales = result.clean_sales
    summary = result.quality_summary

    normal_sale = clean_sales.loc[clean_sales["user_id"] == "0001"].iloc[0]
    assert normal_sale["is_promo"] == 1
    assert normal_sale["is_return"] == 0
    assert normal_sale["unit"] == "千克"

    return_sale = clean_sales.loc[clean_sales["user_id"] == "0002"].iloc[0]
    assert return_sale["is_promo"] == 0
    assert return_sale["is_return"] == 1

    dirty_sale = clean_sales.loc[clean_sales["user_id"] == "0003"].iloc[0]
    assert dirty_sale["sale_date"] == pd.Timestamp("2025-02-28")
    assert dirty_sale["unit"] == "袋"
    assert dirty_sale["spec"] == "未知规格"
    assert dirty_sale["unit_price"] == 12

    shifted_sale = clean_sales.loc[clean_sales["user_id"] == "0005"].iloc[0]
    assert shifted_sale["spec"] == "牛魔空版 12g*8"
    assert shifted_sale["item_type"] == "一般商品"
    assert shifted_sale["unit"] == "未知单位"
    assert shifted_sale["quantity"] == 1
    assert shifted_sale["is_promo"] == 0

    assert summary.original_rows == 6
    assert summary.duplicate_rows_removed == 1
    assert summary.shifted_rows_repaired == 1
    assert summary.invalid_dates_corrected == 1
    assert summary.promo_rows == 1
    assert summary.return_rows == 1
    assert summary.blank_specs_filled == 1
    assert summary.bad_prices_filled == 1
    assert summary.missing_quantities_filled == 0


def test_clean_retail_sales_reports_missing_required_columns() -> None:
    raw_sales = load_raw_sales_fixture().drop(columns=["顾客编号", "销售日期"])

    with pytest.raises(ValidationError, match="顾客编号, 销售日期"):
        clean_retail_sales(raw_sales)
