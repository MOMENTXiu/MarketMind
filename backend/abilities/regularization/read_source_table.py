"""Read source table from bytes: CSV multi-encoding, Excel multi-sheet."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

CSV_ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb18030", "big5", "latin1"]


def _is_number(v: Any) -> bool:
    try:
        float(str(v).replace(",", "").replace("￥", "").replace("¥", "").strip())
        return True
    except (ValueError, TypeError):
        return False


def _detect_encoding(content: bytes) -> str:
    for enc in CSV_ENCODINGS:
        try:
            content.decode(enc, errors="strict")[:8192]
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    try:
        from charset_normalizer import from_bytes

        best = from_bytes(content).best()
        if best:
            return best.encoding
    except Exception:
        pass
    return "latin1"


def _detect_header_row(probe: pd.DataFrame) -> int:
    best_row, best_score = 0, -1.0
    n = len(probe)
    for i in range(min(n, 8)):
        row = probe.iloc[i]
        nonnull = row.notna().mean()
        if nonnull < 0.5:
            continue
        strlike = row.dropna().apply(lambda v: not _is_number(v)).mean()
        below_numeric = 0.0
        if i + 1 < n:
            below = probe.iloc[i + 1].dropna()
            below_numeric = below.apply(_is_number).mean() if len(below) else 0.0
        score = nonnull * 0.4 + strlike * 0.4 + below_numeric * 0.2
        if score > best_score:
            best_score, best_row = score, i
    return best_row


def _dedup_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols, seen = [], {}
    for c in df.columns:
        c = str(c).strip()
        if c in seen:
            seen[c] += 1
            c = f"{c}.{seen[c]}"
        else:
            seen[c] = 0
        cols.append(c)
    df.columns = cols
    df = df.dropna(axis=1, how="all")
    return df


def read_source_table(content: bytes, filename: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return (dataframe, meta). Meta contains encoding/sheet/header_row/raw_filename/format."""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext in ("xlsx", "xls"):
        return _read_excel(content, filename)
    return _read_csv(content, filename)


def _read_csv(content: bytes, filename: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    enc = _detect_encoding(content)
    probe = pd.read_csv(
        BytesIO(content), encoding=enc, header=None, nrows=15, dtype=str, sep=None, engine="python"
    )
    header_row = _detect_header_row(probe)
    df = pd.read_csv(BytesIO(content), encoding=enc, header=header_row, sep=None, engine="python")
    df = _dedup_columns(df)
    meta = {
        "encoding": enc,
        "sheet_name": None,
        "header_row": header_row,
        "raw_filename": filename,
        "format": "csv",
    }
    return df, meta


def _read_excel(content: bytes, filename: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    xl = pd.ExcelFile(BytesIO(content))
    chosen, best_rows = xl.sheet_names[0], -1
    for s in xl.sheet_names:
        tmp = xl.parse(s, header=None, nrows=50)
        if len(tmp.dropna(how="all")) > best_rows:
            best_rows, chosen = len(tmp.dropna(how="all")), s
    probe = xl.parse(chosen, header=None, nrows=15, dtype=str)
    header_row = _detect_header_row(probe)
    df = xl.parse(chosen, header=header_row)
    df = _dedup_columns(df)
    meta = {
        "encoding": None,
        "sheet_name": chosen,
        "header_row": header_row,
        "raw_filename": filename,
        "format": "excel",
        "all_sheets": xl.sheet_names,
    }
    return df, meta
