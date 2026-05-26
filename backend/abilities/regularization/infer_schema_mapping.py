"""Schema mapping inference: score raw columns against standard fields."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from backend.abilities.regularization.field_aliases import FIELD_ALIASES, STANDARD_SCHEMA


def _norm(s: str) -> str:
    return re.sub(r"[\s_\-　/]+", "", str(s).strip().lower())


_ALIAS_NORM = {std: {_norm(a) for a in al} for std, al in FIELD_ALIASES.items()}

AUTO, REVIEW, WEAK = 0.90, 0.70, 0.50


def infer_schema_mapping(
    df_columns: list[str],
    profile: dict[str, dict[str, Any]],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Return (mapping raw->std, detail list)."""
    cols = list(df_columns)
    scores: list[tuple[float, str, str, str]] = []
    for raw in cols:
        for std in STANDARD_SCHEMA:
            sc, src = _score(raw, std, profile.get(raw, {}))
            if sc > 0:
                scores.append((sc, raw, std, src))
    scores.sort(reverse=True, key=lambda x: x[0])

    mapping: dict[str, str] = {}
    detail: list[dict[str, Any]] = []
    used_raw: set[str] = set()
    used_std: set[str] = set()
    for sc, raw, std, src in scores:
        if raw in used_raw or std in used_std:
            continue
        if sc < WEAK:
            continue
        used_raw.add(raw)
        used_std.add(std)
        status = _level(sc)
        detail.append(
            {
                "raw_column": raw,
                "standard_field": std,
                "confidence": round(sc, 4),
                "source": src,
                "status": status,
            }
        )
        if sc >= AUTO:
            mapping[raw] = std
    for raw in cols:
        if raw not in used_raw:
            detail.append(
                {
                    "raw_column": raw,
                    "standard_field": None,
                    "confidence": 0.0,
                    "source": "unmatched",
                    "status": "missing",
                }
            )
    detail.sort(key=lambda d: -d["confidence"])
    return mapping, detail


def _level(sc: float) -> str:
    if sc >= AUTO:
        return "auto_confirmed"
    if sc >= REVIEW:
        return "need_review"
    return "weak_candidate"


def _score(raw: str, std: str, prof: dict[str, Any]) -> tuple[float, str]:
    s_name, src = _name_score(raw, std)
    s_type = _type_score(std, prof)
    s_pattern = _pattern_score(std, prof)
    s_dist = _dist_score(std, prof)
    if src == "alias_exact":
        return min(1.0, 0.90 + 0.10 * max(s_type, s_pattern)), src
    score = 0.45 * s_name + 0.25 * s_type + 0.20 * s_pattern + 0.10 * s_dist
    if s_name < 0.5:
        score = min(score, 0.65)
    return score, src


def _name_score(raw: str, std: str) -> tuple[float, str]:
    rn = _norm(raw)
    if rn in _ALIAS_NORM[std]:
        return 1.0, "alias_exact"
    best = 0.0
    for a in _ALIAS_NORM[std]:
        r = SequenceMatcher(None, rn, a).ratio()
        if a and (a in rn or rn in a):
            r = max(r, 0.85)
        best = max(best, r)
    return best, "alias_fuzzy"


def _type_score(std: str, prof: dict[str, Any]) -> float:
    if not prof:
        return 0.0
    exp = STANDARD_SCHEMA[std][2]
    if exp == "date":
        return float(prof.get("date_rate", 0) > 0.8)
    if exp == "num":
        return float(prof.get("numeric_rate", 0) > 0.8)
    if exp == "binary":
        return float(prof.get("is_binary", False))
    if exp == "id":
        return float(prof.get("numeric_rate", 0) > 0.5 or prof.get("avg_len", 0) >= 3)
    if exp in ("cat", "text"):
        return float(prof.get("numeric_rate", 1) < 0.5)
    return 0.0


def _pattern_score(std: str, prof: dict[str, Any]) -> float:
    if not prof:
        return 0.0
    if std == "sale_date":
        return float(prof.get("date_rate", 0) > 0.7)
    if std == "is_promo":
        return float(prof.get("is_binary", False))
    if std in ("amount", "unit_price", "quantity", "profit", "discount"):
        return float(prof.get("numeric_rate", 0) > 0.8)
    if std in ("user_id", "item_id", "order_id"):
        return float(prof.get("unique_ratio", 0) > 0.05)
    return 0.5


def _dist_score(std: str, prof: dict[str, Any]) -> float:
    if not prof:
        return 0.0
    ur = prof.get("unique_ratio", 0)
    if std in ("user_id", "item_id", "order_id"):
        return ur
    if std in (
        "cat_l1_name",
        "cat_l2_name",
        "cat_l3_name",
        "segment",
        "gender",
        "region",
        "item_type",
        "unit",
    ):
        return float(prof.get("n_unique", 999) <= 200)
    if std == "discount":
        mx = prof.get("max")
        return float(mx is not None and mx <= 1.5)
    return 0.5
