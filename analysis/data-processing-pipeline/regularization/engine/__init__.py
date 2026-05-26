# -*- coding: utf-8 -*-
"""MarketMind 数据正则化引擎（Data Regularization Engine）。
将任意来源零售数据 → 识别/映射/校验/清洗/补全 → MarketMind 标准 Schema。"""
from .pipeline import RegularizationPipeline, save_all, VERSION
from .field_aliases import STANDARD_SCHEMA, FIELD_ALIASES

__all__ = ["RegularizationPipeline", "save_all", "VERSION",
           "STANDARD_SCHEMA", "FIELD_ALIASES"]
