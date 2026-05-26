# -*- coding: utf-8 -*-
"""SchemaMapper：字段识别与映射（设计报告 §7、§17.3）。
Score(f,s)=0.45*S_name + 0.25*S_type + 0.20*S_pattern + 0.10*S_distribution
置信度分级：≥0.90 auto_confirmed / 0.70-0.90 need_review / 0.50-0.70 weak / <0.50 missing。
"""
import re
from difflib import SequenceMatcher
from .field_aliases import FIELD_ALIASES, STANDARD_SCHEMA


def _norm(s):
    return re.sub(r"[\s_\-　/]+", "", str(s).strip().lower())


# 预归一别名
_ALIAS_NORM = {std: {_norm(a) for a in al} for std, al in FIELD_ALIASES.items()}


class SchemaMapper:
    AUTO, REVIEW, WEAK = 0.90, 0.70, 0.50

    def infer(self, df, profile):
        """返回 mapping(raw->std), detail(list)。贪心：按全局最高分逐一指派，1:1。"""
        cols = list(df.columns)
        scores = []  # (score, raw, std, source)
        for raw in cols:
            for std in STANDARD_SCHEMA:
                sc, src = self._score(raw, std, profile.get(raw, {}))
                if sc > 0:
                    scores.append((sc, raw, std, src))
        scores.sort(reverse=True, key=lambda x: x[0])

        mapping, detail = {}, []
        used_raw, used_std = set(), set()
        for sc, raw, std, src in scores:
            if raw in used_raw or std in used_std:
                continue
            if sc < self.WEAK:
                continue
            used_raw.add(raw); used_std.add(std)
            status = self._level(sc)
            detail.append({"raw_column": raw, "standard_field": std,
                           "confidence": round(sc, 4), "source": src,
                           "status": status})
            # 自动模式仅采用高置信(≥0.90)映射；0.70-0.90 留待人工确认，<0.70 仅作候选（设计 §15.4）
            if sc >= self.AUTO:
                mapping[raw] = std
        # 未映射列
        for raw in cols:
            if raw not in used_raw:
                detail.append({"raw_column": raw, "standard_field": None,
                               "confidence": 0.0, "source": "unmatched", "status": "missing"})
        detail.sort(key=lambda d: -d["confidence"])
        return mapping, detail

    def _level(self, sc):
        if sc >= self.AUTO:
            return "auto_confirmed"
        if sc >= self.REVIEW:
            return "need_review"
        return "weak_candidate"

    # ---------- 四维打分 ----------
    def _score(self, raw, std, prof):
        s_name, src = self._name_score(raw, std)
        s_type = self._type_score(std, prof)
        s_pattern = self._pattern_score(std, prof)
        s_dist = self._dist_score(std, prof)
        # 名称完全命中直接给高分（别名精确匹配）
        if src == "alias_exact":
            return min(1.0, 0.90 + 0.10 * max(s_type, s_pattern)), src
        score = 0.45 * s_name + 0.25 * s_type + 0.20 * s_pattern + 0.10 * s_dist
        # 列名证据不足时设上限，防止仅靠类型/模式"蹭分"造成错配（封顶于自动采用阈值之下）
        if s_name < 0.5:
            score = min(score, 0.65)
        return score, src

    def _name_score(self, raw, std):
        rn = _norm(raw)
        if rn in _ALIAS_NORM[std]:
            return 1.0, "alias_exact"
        # 模糊：与该字段所有别名的最大相似度
        best = 0.0
        for a in _ALIAS_NORM[std]:
            r = SequenceMatcher(None, rn, a).ratio()
            if a and (a in rn or rn in a):
                r = max(r, 0.85)
            best = max(best, r)
        return best, "alias_fuzzy"

    def _type_score(self, std, prof):
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

    def _pattern_score(self, std, prof):
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

    def _dist_score(self, std, prof):
        if not prof:
            return 0.0
        ur = prof.get("unique_ratio", 0)
        if std in ("user_id", "item_id", "order_id"):
            return ur                      # ID 唯一度高
        if std in ("cat_l1_name", "cat_l2_name", "cat_l3_name", "segment", "gender",
                   "region", "item_type", "unit"):
            return float(prof.get("n_unique", 999) <= 200)  # 类目唯一值少
        if std == "discount":
            mx = prof.get("max");
            return float(mx is not None and mx <= 1.5)      # 折扣多在 0-1
        return 0.5
