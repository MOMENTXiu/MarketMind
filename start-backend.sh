#!/bin/bash
# FastAPI 后端启动脚本

echo "======================================"
echo "🚀 MarketMind 后端启动"
echo "======================================"

# 检查数据文件
if [ ! -f "analysis/dataset.csv" ]; then
    echo "❌ 数据文件不存在: analysis/dataset.csv"
    exit 1
fi

echo "✅ 数据文件检查通过"

# 创建输出目录
mkdir -p outputs/charts
mkdir -p outputs/reports
mkdir -p outputs/audio

echo "✅ 输出目录创建完成"

# 启动 FastAPI
echo ""
echo "🌐 启动 FastAPI 服务..."
echo "📍 API 文档: http://localhost:8000/api/docs"
echo "📍 健康检查: http://localhost:8000/api/health"
echo ""

uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
