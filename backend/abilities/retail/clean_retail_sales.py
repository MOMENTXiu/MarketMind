"""Clean Retail V2 raw sales records into the backend analysis schema."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.abilities.retail.normalize_unit import normalize_unit
from backend.abilities.retail.repair_shifted_sales_rows import repair_shifted_sales_rows
from backend.core.errors import ValidationError

RAW_TO_CLEAN_COLUMNS = {
    "顾客编号": "user_id",
    "大类编码": "cat_l1_code",
    "大类名称": "cat_l1_name",
    "中类编码": "cat_l2_code",
    "中类名称": "cat_l2_name",
    "小类编码": "cat_l3_code",
    "小类名称": "cat_l3_name",
    "销售日期": "sale_date",
    "销售月份": "sale_month",
    "商品编码": "item_id",
    "规格型号": "spec",
    "商品类型": "item_type",
    "单位": "unit",
    "销售数量": "quantity",
    "销售金额": "amount",
    "商品单价": "unit_price",
    "是否促销": "is_promo",
}

CLEAN_COLUMNS = [
    "user_id",
    "cat_l1_code",
    "cat_l1_name",
    "cat_l2_code",
    "cat_l2_name",
    "cat_l3_code",
    "cat_l3_name",
    "sale_date",
    "sale_month",
    "item_id",
    "spec",
    "item_type",
    "unit",
    "quantity",
    "amount",
    "unit_price",
    "is_promo",
    "is_return",
    "weekday",
    "is_weekend",
    "week_of_year",
]


@dataclass(frozen=True)
class RetailCleanQualitySummary:
    """Quality counters produced by the Retail V2 cleaning ability."""

    original_rows: int
    duplicate_rows_removed: int
    shifted_rows_repaired: int
    invalid_dates_corrected: int
    promo_rows: int
    return_rows: int
    blank_specs_filled: int
    bad_prices_filled: int
    missing_quantities_filled: int


@dataclass(frozen=True)
class RetailCleanResult:
    """Clean Retail V2 dataset plus quality counters."""

    clean_sales: pd.DataFrame
    quality_summary: RetailCleanQualitySummary


def clean_retail_sales(raw_sales: pd.DataFrame) -> RetailCleanResult:
    """Clean raw Retail V2 sales data without doing file or artifact IO."""

    _validate_raw_schema(raw_sales)
    original_rows = len(raw_sales)

    repaired_raw, shifted_rows = repair_shifted_sales_rows(raw_sales)
    deduplicated = repaired_raw.drop_duplicates().reset_index(drop=True)
    duplicate_rows_removed = original_rows - len(deduplicated)

    sales = deduplicated.rename(columns=RAW_TO_CLEAN_COLUMNS).copy()
    _normalize_identity_columns(sales)
    _normalize_numeric_columns(sales)
    invalid_dates_corrected = _normalize_dates(sales)

    sales["is_promo"] = sales["is_promo"].map({"是": 1, "否": 0}).fillna(0).astype(int)
    promo_rows = int(sales["is_promo"].sum())

    sales["is_return"] = ((sales["quantity"] <= 0) | (sales["amount"] <= 0)).astype(int)
    return_rows = int(sales["is_return"].sum())

    sales["unit"] = sales["unit"].map(normalize_unit)
    blank_specs_filled = _fill_blank_specs(sales)
    bad_prices_filled = _fill_bad_unit_prices(sales)
    missing_quantities_filled = _fill_missing_quantities(sales)

    clean_sales = sales[CLEAN_COLUMNS].reset_index(drop=True)
    summary = RetailCleanQualitySummary(
        original_rows=original_rows,
        duplicate_rows_removed=duplicate_rows_removed,
        shifted_rows_repaired=shifted_rows,
        invalid_dates_corrected=invalid_dates_corrected,
        promo_rows=promo_rows,
        return_rows=return_rows,
        blank_specs_filled=blank_specs_filled,
        bad_prices_filled=bad_prices_filled,
        missing_quantities_filled=missing_quantities_filled,
    )
    return RetailCleanResult(clean_sales=clean_sales, quality_summary=summary)


def _validate_raw_schema(raw_sales: pd.DataFrame) -> None:
    missing = [column for column in RAW_TO_CLEAN_COLUMNS if column not in raw_sales.columns]
    if missing:
        raise ValidationError(f"Retail V2 raw sales dataset missing columns: {', '.join(missing)}")


def _normalize_identity_columns(sales: pd.DataFrame) -> None:
    sales["user_id"] = pd.to_numeric(sales["user_id"], errors="raise").astype(int).astype(str)
    sales["user_id"] = sales["user_id"].str.zfill(4)
    sales["item_id"] = sales["item_id"].astype(str).str.strip()
    for column in ["cat_l1_code", "cat_l2_code", "cat_l3_code"]:
        sales[column] = pd.to_numeric(sales[column], errors="raise").astype(int).astype(str)


def _normalize_numeric_columns(sales: pd.DataFrame) -> None:
    for column in ["quantity", "amount", "unit_price"]:
        sales[column] = pd.to_numeric(sales[column], errors="coerce")


def _normalize_dates(sales: pd.DataFrame) -> int:
    sale_date_text = sales["sale_date"].astype(str).str.replace(r"\.0$", "", regex=True)
    sale_dates = pd.to_datetime(sale_date_text, format="%Y%m%d", errors="coerce")
    invalid_count = int(sale_dates.isna().sum())

    for index in sales.index[sale_dates.isna()]:
        raw_value = sale_date_text.at[index]
        if len(raw_value) < 6 or not raw_value[:6].isdigit():
            raise ValidationError(f"Retail V2 raw sales dataset has invalid sale_date: {raw_value}")
        year = int(raw_value[:4])
        month = int(raw_value[4:6])
        sale_dates.at[index] = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(1)

    sales["sale_date"] = sale_dates
    sales["sale_month"] = pd.to_numeric(sales["sale_month"], errors="raise").astype(int)
    sales["weekday"] = sales["sale_date"].dt.weekday
    sales["is_weekend"] = (sales["weekday"] >= 5).astype(int)
    sales["week_of_year"] = sales["sale_date"].dt.isocalendar().week.astype(int)
    return invalid_count


def _fill_blank_specs(sales: pd.DataFrame) -> int:
    blank_specs = sales["spec"].isna() | (sales["spec"].astype(str).str.strip() == "")
    count = int(blank_specs.sum())
    sales.loc[blank_specs, "spec"] = "未知规格"
    return count


def _fill_bad_unit_prices(sales: pd.DataFrame) -> int:
    bad_price = sales["unit_price"].isna() | (sales["unit_price"] <= 0)
    count = int(bad_price.sum())
    if count == 0:
        return 0

    valid_prices = sales.loc[~bad_price, ["item_id", "cat_l3_code", "unit_price"]]
    item_medians = valid_prices.groupby("item_id")["unit_price"].median()
    category_medians = valid_prices.groupby("cat_l3_code")["unit_price"].median()
    global_median = valid_prices["unit_price"].median()
    if pd.isna(global_median):
        raise ValidationError("Retail V2 raw sales dataset has no valid unit_price values")

    for index in sales.index[bad_price]:
        replacement = item_medians.get(sales.at[index, "item_id"], np.nan)
        if pd.isna(replacement):
            replacement = category_medians.get(sales.at[index, "cat_l3_code"], np.nan)
        if pd.isna(replacement):
            replacement = global_median
        sales.at[index, "unit_price"] = replacement

    return count


def _fill_missing_quantities(sales: pd.DataFrame) -> int:
    missing_quantity = sales["quantity"].isna()
    count = int(missing_quantity.sum())
    if count:
        sales.loc[missing_quantity, "quantity"] = (
            sales.loc[missing_quantity, "amount"] / sales.loc[missing_quantity, "unit_price"]
        ).round(4)
    return count
