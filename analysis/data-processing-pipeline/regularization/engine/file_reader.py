# -*- coding: utf-8 -*-
"""FileReader：文件读取正则化（设计报告 §8）。
支持 CSV 多编码自动识别、Excel 多 Sheet、说明行/表头自动检测。"""
import os
import pandas as pd

CSV_ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb18030", "big5", "latin1"]


class FileReader:
    def read(self, path):
        """返回 (df, meta)。meta 含 encoding/sheet/header_row/raw_filename。"""
        ext = os.path.splitext(path)[1].lower()
        if ext in (".xlsx", ".xls"):
            return self._read_excel(path)
        return self._read_csv(path)

    # ---------- CSV ----------
    def _detect_encoding(self, path):
        for enc in CSV_ENCODINGS:
            try:
                with open(path, "r", encoding=enc) as f:
                    f.read(8192)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        # 兜底：charset-normalizer
        try:
            from charset_normalizer import from_path
            best = from_path(path).best()
            if best:
                return best.encoding
        except Exception:
            pass
        return "latin1"

    def _read_csv(self, path):
        enc = self._detect_encoding(path)
        # 先读若干行探测表头位置（说明行/空行）
        probe = pd.read_csv(path, encoding=enc, header=None, nrows=15, dtype=str,
                            sep=None, engine="python")
        header_row = self._detect_header_row(probe)
        df = pd.read_csv(path, encoding=enc, header=header_row, sep=None, engine="python")
        df = self._dedup_columns(df)
        meta = {"encoding": enc, "sheet_name": None, "header_row": header_row,
                "raw_filename": os.path.basename(path), "format": "csv"}
        return df, meta

    # ---------- Excel ----------
    def _read_excel(self, path):
        xl = pd.ExcelFile(path)
        # 选第一个非空 Sheet
        chosen, best_rows = xl.sheet_names[0], -1
        for s in xl.sheet_names:
            tmp = xl.parse(s, header=None, nrows=50)
            if len(tmp.dropna(how="all")) > best_rows:
                best_rows, chosen = len(tmp.dropna(how="all")), s
        probe = xl.parse(chosen, header=None, nrows=15, dtype=str)
        header_row = self._detect_header_row(probe)
        df = xl.parse(chosen, header=header_row)
        df = self._dedup_columns(df)
        meta = {"encoding": None, "sheet_name": chosen, "header_row": header_row,
                "raw_filename": os.path.basename(path), "format": "excel",
                "all_sheets": xl.sheet_names}
        return df, meta

    # ---------- 表头识别（设计报告 §8.3）----------
    def _detect_header_row(self, probe):
        """选择最像表头的行：非空比例高、字符串比例高、与后续行类型不同。"""
        best_row, best_score = 0, -1
        n = len(probe)
        for i in range(min(n, 8)):
            row = probe.iloc[i]
            nonnull = row.notna().mean()
            if nonnull < 0.5:
                continue
            strlike = row.dropna().apply(lambda v: not _is_number(v)).mean()
            # 表头下方应出现数值/日期
            below_numeric = 0.0
            if i + 1 < n:
                below = probe.iloc[i + 1].dropna()
                below_numeric = below.apply(_is_number).mean() if len(below) else 0
            score = nonnull * 0.4 + strlike * 0.4 + below_numeric * 0.2
            if score > best_score:
                best_score, best_row = score, i
        return best_row

    def _dedup_columns(self, df):
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
        # 丢弃全空列
        df = df.dropna(axis=1, how="all")
        return df


def _is_number(v):
    try:
        float(str(v).replace(",", "").replace("￥", "").replace("¥", "").strip())
        return True
    except (ValueError, TypeError):
        return False
