"""Contract tests for Retail V2 customer segmentation abilities."""

from __future__ import annotations

import pandas as pd
import pytest

from backend.abilities.retail.cluster_retail_customers import (
    SEGMENT_FEATURES,
    cluster_retail_customers,
)
from backend.core.errors import ValidationError


def make_customer_profile() -> pd.DataFrame:
    rows = []
    for index in range(8):
        high_value = index < 4
        rows.append(
            {
                "user_id": f"{index + 1:04d}",
                "R_最近购买间隔": 2 + index if high_value else 35 + index,
                "F_购买频次": 8 + index if high_value else 1 + index % 2,
                "M_消费金额": 800 + index * 40 if high_value else 90 + index * 8,
                "客单价": 90 + index * 5 if high_value else 45 + index,
                "类目熵": 1.4 if high_value else 0.25,
                "占比_蔬果": 0.30 if high_value else 0.05,
                "占比_粮油": 0.15,
                "占比_日配": 0.20 if high_value else 0.05,
                "占比_休闲": 0.10 if high_value else 0.65,
                "小类购买数": 7 if high_value else 2,
                "促销金额占比": 0.12 if high_value else 0.75,
                "促销频次占比": 0.10 if high_value else 0.80,
                "低价带占比": 0.20 if high_value else 0.85,
                "高价带占比": 0.35 if high_value else 0.02,
                "生鲜占比": 0.40 if high_value else 0.03,
                "复购紧迫度均值": 1.3 if high_value else 0.1,
                "促销敏感度": 0.11 if high_value else 0.78,
            }
        )
    return pd.DataFrame(rows)


def test_cluster_retail_customers_returns_segments_profiles_and_metrics() -> None:
    result = cluster_retail_customers(make_customer_profile(), segment_count=2)

    assert result.best_segment_count == 2
    assert result.feature_columns == SEGMENT_FEATURES
    assert len(result.customer_segments) == 8
    assert {"user_id", "segment_id", "segment", "segment_confidence", "P_0", "P_1"}.issubset(
        result.customer_segments.columns
    )
    assert result.customer_segments["segment_confidence"].between(0, 1).all()
    assert set(result.segment_profile["segment_id"]) == set(
        result.customer_segments["segment_id"].unique()
    )
    assert {"segment", "sales_share", "customer_share"}.issubset(result.segment_profile.columns)
    assert result.model_comparison.loc[0, "model"] == "GMM"
    assert result.model_comparison.loc[0, "segment_count"] == 2


def test_cluster_retail_customers_auto_selects_gmm_segment_count() -> None:
    result = cluster_retail_customers(make_customer_profile(), max_segments=3)

    assert 2 <= result.best_segment_count <= 3
    assert result.customer_segments["segment"].notna().all()


def test_cluster_retail_customers_reports_missing_profile_columns() -> None:
    profile = make_customer_profile().drop(columns=["M_消费金额"])

    with pytest.raises(ValidationError, match="M_消费金额"):
        cluster_retail_customers(profile, segment_count=2)
