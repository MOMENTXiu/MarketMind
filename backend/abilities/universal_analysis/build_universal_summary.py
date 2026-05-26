"""Build universal summary from all module results."""

from __future__ import annotations

from typing import Any


def build_universal_summary(
    overview: dict[str, Any],
    profile_segments: dict[str, Any],
    associations: dict[str, Any],
    recommendations: dict[str, Any],
    promotion: dict[str, Any],
) -> dict[str, Any]:
    """Return cross-module summary dict."""
    summary = {
        "基础销售统计": overview.get("overview", {}),
        "顾客画像": {
            "分群数": profile_segments.get("n_segments"),
            "轮廓系数": profile_segments.get("silhouette"),
            "状态": profile_segments.get("status", "ok"),
        },
        "关联规则": {
            "状态": associations.get("status", "ok"),
            "规则数": associations.get("n_rules"),
            "top_rule": associations.get("top_rule"),
        },
        "个性化推荐": {
            "状态": recommendations.get("status", "ok"),
            "最佳模型": recommendations.get("best_model"),
            "融合HitRate@10": recommendations.get("fusion_hit"),
        },
        "促销分析": {
            "状态": promotion.get("status", "ok"),
            "朴素差": promotion.get("naive_diff"),
            "DML_ATE": promotion.get("dml_ate"),
        },
    }
    return summary
