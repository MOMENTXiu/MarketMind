# -*- coding: utf-8 -*-
"""RegularizationPipeline：正则化编排（设计报告 §17.1）。
reader → profiler → mapper → type_normalizer → business_normalizer → quality → capability。"""
import os
import json
import datetime as dt
import pandas as pd

from .file_reader import FileReader
from .schema_profiler import SchemaProfiler
from .schema_mapper import SchemaMapper
from .type_normalizer import TypeNormalizer
from .business_normalizer import BusinessNormalizer
from .quality_checker import QualityChecker
from .capability_checker import CapabilityChecker

VERSION = "v1.0.0"


class RegularizationPipeline:
    def __init__(self):
        self.reader = FileReader()
        self.profiler = SchemaProfiler()
        self.mapper = SchemaMapper()
        self.type_normalizer = TypeNormalizer()
        self.business_normalizer = BusinessNormalizer()
        self.quality_checker = QualityChecker()
        self.capability_checker = CapabilityChecker()

    def preview(self, raw_path):
        raw_df, meta = self.reader.read(raw_path)
        profile = self.profiler.profile(raw_df)
        mapping, detail = self.mapper.infer(raw_df, profile)
        return {"meta": meta, "profile": profile, "mapping": mapping,
                "mapping_detail": detail,
                "preview_rows": raw_df.head(5).astype(str).to_dict("records")}

    def run(self, raw_path, mapping=None):
        raw_df, meta = self.reader.read(raw_path)
        n_raw = len(raw_df)
        raw_df = raw_df.drop_duplicates().reset_index(drop=True)
        dup_removed = n_raw - len(raw_df)

        profile = self.profiler.profile(raw_df)
        if mapping is None:
            mapping, detail = self.mapper.infer(raw_df, profile)
        else:
            detail = [{"raw_column": k, "standard_field": v, "confidence": 1.0,
                       "source": "user_confirmed", "status": "auto_confirmed"}
                      for k, v in mapping.items()]

        norm_df, type_stats = self.type_normalizer.normalize(raw_df, mapping)
        norm_df, rules = self.business_normalizer.normalize(norm_df)
        quality = self.quality_checker.check(raw_df, norm_df, mapping, dup_removed)
        capability = self.capability_checker.check(norm_df)

        manifest = {
            "regularization_version": VERSION,
            "raw_filename": meta["raw_filename"],
            "format": meta.get("format"),
            "encoding": meta.get("encoding"),
            "sheet_name": meta.get("sheet_name"),
            "header_row": meta.get("header_row"),
            "created_at": dt.datetime.now().isoformat(timespec="seconds"),
            "rules_applied": ["field_alias_mapping", "type_normalization"] + rules,
            "type_stats": type_stats,
        }
        return {"normalized": norm_df, "mapping": mapping, "mapping_detail": detail,
                "profile": profile, "quality": quality, "capability": capability,
                "manifest": manifest}


def save_all(result, out_dir):
    """落盘 normalized/dataset.csv + 各 json 产物（设计报告 §5）。"""
    os.makedirs(out_dir, exist_ok=True)
    norm = result["normalized"]
    norm.to_csv(os.path.join(out_dir, "dataset.csv"), index=False, encoding="utf-8-sig")
    _json(os.path.join(out_dir, "schema_mapping.json"), result["mapping"])
    _json(os.path.join(out_dir, "schema_mapping_detail.json"), result["mapping_detail"])
    _json(os.path.join(out_dir, "field_profile.json"), result["profile"])
    _json(os.path.join(out_dir, "quality_report.json"), result["quality"])
    _json(os.path.join(out_dir, "capability.json"), result["capability"])
    _json(os.path.join(out_dir, "manifest.json"), result["manifest"])
    _json(os.path.join(out_dir, "preview_rows.json"),
          norm.head(8).astype(str).to_dict("records"))


def _json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
