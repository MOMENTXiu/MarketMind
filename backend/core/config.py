"""
应用配置
"""

from typing import List

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # 应用基本信息
    APP_NAME: str = "MarketMind"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # API配置
    API_PREFIX: str = "/api"

    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",  # Vite 默认端口
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # 数据文件路径
    DATA_PATH: str = "analysis/dataset.csv"

    # 输出目录
    OUTPUT_DIR: str = "outputs"
    CHARTS_DIR: str = "outputs/charts"
    REPORTS_DIR: str = "outputs/reports"

    # 算法参数 - 关联规则
    ASSOCIATION_MIN_SUPPORT: float = 0.02
    ASSOCIATION_MIN_CONFIDENCE: float = 0.3
    ASSOCIATION_MIN_LIFT: float = 1.0

    # 算法参数 - 预测
    FORECAST_WEEKS: int = 13
    RIDGE_ALPHA: float = 10.0

    # 算法参数 - 聚类
    CLUSTER_N_CLUSTERS: int = 4

    model_config = ConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
