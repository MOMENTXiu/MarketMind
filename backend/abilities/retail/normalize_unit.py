"""Retail unit normalization ability."""

from __future__ import annotations

import pandas as pd

UNIT_MAP = {
    "千克": "千克",
    "KG": "千克",
    "kg": "千克",
    "Kg": "千克",
    "公斤": "千克",
    "散称": "千克",
    "袋": "袋",
    "d袋": "袋",
    "盒": "盒",
    "合": "盒",
    "副": "副",
    "付": "副",
    "代": "代",
}

UNIT_DIRTY = {"", "2", "0", "160g", "一般", "快", "装"}


def normalize_unit(value: object) -> str:
    """Normalize raw retail unit text to a stable business unit."""

    if pd.isna(value):
        return "未知单位"
    unit = str(value).replace("　", "").strip()
    if unit in UNIT_DIRTY:
        return "未知单位"
    return UNIT_MAP.get(unit, unit if unit else "未知单位")
