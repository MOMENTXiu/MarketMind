"""
FastAPI 主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.api import association, voice, projects, recommend, ai_voice
# 注释掉独立的 prediction 和 clustering API，现在通过 projects API 使用
# from backend.api import prediction, clustering
from backend.core.config import settings

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
app.include_router(projects.router, prefix="/api/projects", tags=["项目管理"])
app.include_router(association.router, prefix="/api/association", tags=["关联规则分析"])
# 暂时注释掉独立的 prediction 和 clustering API
# app.include_router(prediction.router, prefix="/api/prediction", tags=["销售预测"])
# app.include_router(clustering.router, prefix="/api/clustering", tags=["客户聚类"])
app.include_router(voice.router, prefix="/api/voice", tags=["语音播报"])
app.include_router(recommend.router, prefix="/api", tags=["行为推荐"])
app.include_router(ai_voice.router, prefix="/api", tags=["AI 语音播报"])


@app.get("/")
async def root():
    """根路径 - API 健康检查"""
    return {
        "message": "MarketMind API is running",
        "version": "1.0.0",
        "docs": "/api/docs"
    }


@app.get("/api/health/")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "MarketMind Backend"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
