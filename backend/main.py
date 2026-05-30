"""
FastAPI 主应用入口
"""

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import admin as admin_api
from backend.api import analysis, auth, samples
from backend.api.dependencies import get_providers
from backend.core.config import settings
from backend.providers.container import ProvidersContainer

# 创建 FastAPI 应用
app = FastAPI(
    title="MarketMind API",
    description="超市AI营销系统 - RESTful API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务（用于提供生成的图表和报告）
outputs_dir = Path("outputs")
outputs_dir.mkdir(exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# 注册路由
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Retail Analysis V2"])
app.include_router(samples.router, prefix="/api", tags=["Sample Files"])

# Admin Console routes
app.include_router(admin_api.status.router, prefix="/api/admin", tags=["Admin - Status"])
app.include_router(admin_api.settings.router, prefix="/api/admin", tags=["Admin - Settings"])
app.include_router(admin_api.logs.router, prefix="/api/admin", tags=["Admin - Logs"])
app.include_router(admin_api.users.router, prefix="/api/admin", tags=["Admin - Users"])


@app.get("/")
async def root():
    """根路径 - API 健康检查"""
    return {"message": "MarketMind API is running", "version": "1.0.0", "docs": "/api/docs"}


@app.get("/api/health/")
async def health_check(providers: ProvidersContainer = Depends(get_providers)):
    """健康检查接口 - 探测后端、Postgres、Redis、MinIO 状态"""
    if providers.health is None:
        return {"status": "healthy", "service": "MarketMind Backend"}

    components = providers.health.check_all()
    overall = "healthy"
    for name, info in components.items():
        if info.get("status") == "down":
            overall = "degraded" if overall == "healthy" else overall
        elif info.get("status") == "degraded" and overall == "healthy":
            overall = "degraded"

    # If any core infra is down, mark as degraded at minimum
    core = ["postgres", "redis"]
    if any(components.get(c, {}).get("status") == "down" for c in core):
        overall = "degraded"

    return {
        "status": overall,
        "service": "MarketMind Backend",
        "version": "1.0.0",
        "components": components,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
