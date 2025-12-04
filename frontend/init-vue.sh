#!/bin/bash
# Vue3 前端项目初始化脚本

echo "======================================"
echo "MarketMind Vue3 前端初始化"
echo "======================================"

cd "$(dirname "$0")"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js"
    exit 1
fi

echo "✅ Node.js 版本: $(node -v)"
echo "✅ npm 版本: $(npm -v)"

# 创建 Vue3 项目
echo ""
echo "📦 创建 Vue3 + TypeScript 项目..."
npm create vite@latest . -- --template vue-ts

# 安装核心依赖
echo ""
echo "📦 安装核心依赖..."
npm install

# 安装UI组件库
echo ""
echo "📦 安装 Element Plus..."
npm install element-plus

# 安装路由和状态管理
echo ""
echo "📦 安装 Vue Router 和 Pinia..."
npm install vue-router@4 pinia

# 安装HTTP客户端
echo ""
echo "📦 安装 Axios..."
npm install axios

# 安装图表库
echo ""
echo "📦 安装 ECharts..."
npm install echarts vue-echarts

# 安装工具库
echo ""
echo "📦 安装工具库..."
npm install @vueuse/core dayjs

# 创建环境变量文件
echo ""
echo "📝 创建环境变量文件..."
cat > .env.development << 'EOF'
VITE_API_BASE_URL=http://localhost:8000/api
VITE_API_TIMEOUT=30000
EOF

cat > .env.production << 'EOF'
VITE_API_BASE_URL=/api
VITE_API_TIMEOUT=30000
EOF

echo ""
echo "======================================"
echo "✅ Vue3 前端初始化完成！"
echo "======================================"
echo ""
echo "🚀 开始开发:"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "🏗️ 构建生产版本:"
echo "   npm run build"
echo ""
