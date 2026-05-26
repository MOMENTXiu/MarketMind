"""Contract tests for Analysis V2 provider adapters."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.core.errors import ValidationError
from backend.infrastructure.adapters.csv_retail_dataset_adapter import CsvRetailDatasetAdapter
from backend.infrastructure.adapters.local_analysis_artifact_adapter import (
    LocalAnalysisArtifactAdapter,
)
from backend.infrastructure.adapters.local_analysis_model_store_adapter import (
    LocalAnalysisModelStoreAdapter,
)
from backend.providers.dtos import RETAIL_RAW_SALES_COLUMNS

LOCAL_REF_MARKERS = (
    "/Users/",
    "analysis/output",
    "backend/data",
    "outputs/",
    "data/projects",
)


def _raw_csv_text() -> str:
    return "\n".join(
        [
            ",".join(RETAIL_RAW_SALES_COLUMNS),
            "1,10,生鲜,101,水果,1001,苹果,20250101,202501,9001,500g,一般商品,KG,2,20,10,是",
            "2,20,食品,201,零食,2001,饼干,20250228,202502,9002,250g,一般商品,袋,1,12,12,否",
        ]
    )


def _assert_opaque_ref(ref_url: str, storage_key: str) -> None:
    assert not any(marker in ref_url for marker in LOCAL_REF_MARKERS)
    assert not any(marker in storage_key for marker in LOCAL_REF_MARKERS)


def test_csv_retail_dataset_adapter_reads_gbk_and_utf8_sig_raw_sales(tmp_path: Path) -> None:
    adapter = CsvRetailDatasetAdapter(str(tmp_path / "data"))

    gbk_ref = adapter.save_raw_sales("project-gbk", "sales.csv", _raw_csv_text().encode("gbk"))
    gbk_frame = adapter.load_raw_sales("project-gbk")
    utf8_ref = adapter.save_raw_sales(
        "project-utf8",
        "sales.csv",
        _raw_csv_text().encode("utf-8-sig"),
    )
    utf8_frame = adapter.load_raw_sales("project-utf8")

    assert list(gbk_frame.columns) == list(RETAIL_RAW_SALES_COLUMNS)
    assert list(utf8_frame.columns) == list(RETAIL_RAW_SALES_COLUMNS)
    assert gbk_frame.loc[0, "大类名称"] == "生鲜"
    assert utf8_frame.loc[1, "小类名称"] == "饼干"
    _assert_opaque_ref(gbk_ref.url or "", gbk_ref.storage_key)
    _assert_opaque_ref(utf8_ref.url or "", utf8_ref.storage_key)


def test_csv_retail_dataset_adapter_rejects_missing_raw_columns(tmp_path: Path) -> None:
    adapter = CsvRetailDatasetAdapter(str(tmp_path / "data"))
    missing_columns = [column for column in RETAIL_RAW_SALES_COLUMNS if column != "是否促销"]
    content = (",".join(missing_columns) + "\n" + ",".join(["1"] * len(missing_columns))).encode(
        "utf-8"
    )
    adapter.save_raw_sales("project-1", "sales.csv", content)

    with pytest.raises(ValidationError, match="是否促销"):
        adapter.load_raw_sales("project-1")


def test_csv_retail_dataset_adapter_clean_save_load_roundtrip(tmp_path: Path) -> None:
    adapter = CsvRetailDatasetAdapter(str(tmp_path / "data"))
    clean_frame = pd.DataFrame(
        [
            {
                "user_id": "0001",
                "item_id": "9001",
                "quantity": 2,
                "amount": 20.0,
                "is_promo": 1,
            }
        ]
    )

    ref = adapter.save_clean_sales("project-1", clean_frame)
    loaded = adapter.load_clean_sales("project-1")

    assert loaded.to_dict(orient="records") == clean_frame.to_dict(orient="records")
    assert ref.type == "clean"
    _assert_opaque_ref(ref.url or "", ref.storage_key)


def test_local_analysis_artifact_adapter_returns_opaque_url_without_local_path(
    tmp_path: Path,
) -> None:
    adapter = LocalAnalysisArtifactAdapter(str(tmp_path / "data"))

    ref = adapter.save_markdown("project-1", "report", "# Retail report")

    assert ref.type == "markdown"
    assert ref.url == "/api/analysis/projects/project-1/artifacts/markdown:report.md"
    assert not hasattr(ref, "path")
    _assert_opaque_ref(ref.url, ref.storage_key)
    assert (tmp_path / "data/projects/project-1/analysis/artifacts/markdown/report.md").exists()
    assert adapter.resolve_artifact("project-1", ref.id) == ref


def test_local_analysis_model_store_ref_roundtrip(tmp_path: Path) -> None:
    adapter = LocalAnalysisModelStoreAdapter(str(tmp_path / "data"))
    payload = {"segments": ["value", "promo"]}

    ref = adapter.save_model("project-1", "segmentation", payload, version="v1")

    assert adapter.load_model("project-1", "segmentation", version="v1") == payload
    assert adapter.resolve_model("project-1", "segmentation", version="v1") == ref
    assert adapter.list_models("project-1") == [ref]
    assert ref.type == "model"
    assert not hasattr(ref, "path")
    _assert_opaque_ref(ref.url, ref.storage_key)


@pytest.mark.parametrize(
    ("project_id", "model_type", "version"),
    [
        ("../project", "segmentation", "v1"),
        ("project-1", "../segmentation", "v1"),
        ("project-1", "segmentation", "../../v1"),
    ],
)
def test_local_analysis_model_store_rejects_arbitrary_path_driven_access(
    tmp_path: Path,
    project_id: str,
    model_type: str,
    version: str,
) -> None:
    adapter = LocalAnalysisModelStoreAdapter(str(tmp_path / "data"))

    with pytest.raises(ValidationError):
        adapter.save_model(project_id, model_type, {"payload": True}, version=version)
