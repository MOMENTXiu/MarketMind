"""Application settings."""

from typing import List, Literal

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

    # PostgreSQL 开发基础设施
    DATABASE_URL: str = (
        "postgresql+psycopg://marketmind:marketmind_dev_password@localhost:5432/marketmind"
    )
    TEST_DATABASE_URL: str | None = None
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_POOL_MAX_OVERFLOW: int = 10

    # Redis / queue runtime for Retail V2 analysis jobs and status events.
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True
    TASK_QUEUE_BACKEND: Literal["none", "redis"] = "redis"
    ANALYSIS_QUEUE_NAME: str = "retail-analysis"
    ANALYSIS_EVENT_HEARTBEAT_MS: int = 15000
    ANALYSIS_EVENT_RETRY_MS: int = 3000

    # Object Storage (MinIO / S3-compatible)
    OBJECT_STORAGE_BACKEND: Literal["local", "minio"] = "minio"
    OBJECT_STORAGE_BUCKET: str = "marketmind-dev"
    OBJECT_STORAGE_ENDPOINT: str = "http://localhost:9000"
    OBJECT_STORAGE_PUBLIC_ENDPOINT: str = "http://localhost:9000"
    OBJECT_STORAGE_ACCESS_KEY: str = "marketmind"
    OBJECT_STORAGE_SECRET_KEY: str = "marketmind_dev_password"
    OBJECT_STORAGE_REGION: str = "us-east-1"
    OBJECT_STORAGE_SECURE: bool = False
    OBJECT_STORAGE_PRESIGNED_URL_TTL_SECONDS: int = 900
    OBJECT_STORAGE_FORCE_PATH_STYLE: bool = True

    # Auth / JWT
    AUTH_SECRET_KEY: str = "dev-secret-change-in-production"
    AUTH_ALGORITHM: str = "HS256"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    AUTH_SSE_TICKET_EXPIRE_MINUTES: int = 5
    AUTH_TOKEN_AUDIENCE: str = "marketmind-api"
    AUTH_TOKEN_ISSUER: str = "marketmind"
    AUTH_PASSWORD_HASH_ROUNDS: int = 12
    AUTH_ENFORCE_ANALYSIS_AUTH: bool = False  # staged rollout flag

    # LLM Provider
    LLM_PROVIDER: str | None = None
    LLM_BASE_URL: str | None = None
    LLM_MODEL: str | None = None
    LLM_API_KEY: str | None = None
    LLM_TIMEOUT_SECONDS: int = 30

    # Bark Alert
    BARK_ENABLED: bool = False
    BARK_SERVER_URL: str | None = None
    BARK_DEVICE_KEY: str | None = None
    BARK_DEFAULT_GROUP: str | None = None

    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
