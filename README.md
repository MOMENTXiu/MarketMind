# MarketMind - AI营销决策支持系统

> **Vue3 + FastAPI 全栈架构** | 基于机器学习的智能营销分析平台

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13+-green.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.0+-brightgreen.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)

## 📋 目录

- [项目简介](#-项目简介)
- [核心功能](#-核心功能)
- [技术架构](#-技术架构)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [API文档](#-api文档)
- [前端路由](#-前端路由)
- [数据流架构](#-数据流架构)
- [开发指南](#-开发指南)
- [部署说明](#-部署说明)
- [数据格式](#-数据格式)

---

## 🎯 项目简介

MarketMind 是一个现代化的AI营销分析系统，专为零售行业设计，通过机器学习算法提供数据驱动的营销决策支持。系统采用前后端分离架构，结合预训练模型和实时计算，为企业提供客户分析、商品推荐、关联规则挖掘等智能化营销工具。

### 核心价值

- **数据驱动决策**: 基于RFM模型和机器学习算法，提供科学的客户分群和商品推荐
- **实时分析**: 支持预训练模型快速加载和实时关联规则计算
- **AI辅助**: 集成LLM生成专业营销建议，支持语音播报
- **可视化洞察**: 丰富的图表展示和思维导图式关联分析

---

## ✨ 核心功能

### 1. 项目管理

- **多项目支持**: 创建、管理多个营销分析项目
- **数据集上传**: 支持CSV格式数据导入
- **项目仪表盘**: 聚合展示关联规则、聚类分析、销售预测结果

### 2. 客户分析

- **RFM聚类**: 基于最近购买时间(R)、购买频次(F)、消费金额(M)的客户分群
- **个性化推荐**: 根据客户分群特征推荐适合的商品
- **AI营销建议**: 使用LLM自动生成针对性营销方案
- **客户画像**: 完整的客户消费行为分析和价值评估

### 3. 商品关联分析

- **Apriori算法**: 基于支持度、置信度、提升度的购物篮分析
- **双向关联**: 支持上游商品(什么导致购买该商品)和下游商品(购买该商品会带动什么)分析
- **实时计算**: 对于新商品或特殊场景，支持on-demand实时关联规则计算
- **可视化展示**: 思维导图式商品关联网络图

### 4. 智能推荐系统

- **协同过滤**: 基于客户分群的商品推荐
- **关联规则推荐**: 基于购物篮分析的商品搭配推荐
- **混合推荐**: 结合聚类特征和关联规则的综合推荐引擎
- **目标客群定位**: 为商品推荐找到最适合的客户群体

### 5. 销售预测

- **时间序列分析**: 基于历史数据预测未来销售趋势
- **线性回归模型**: 预测销售额和利润
- **趋势可视化**: 直观展示预测结果和置信区间

### 6. AI语音播报

- **LLM文案生成**: 支持OpenAI GPT-4和Claude Sonnet多种模型
- **场景化Prompt**: 针对聚类、关联、预测、客户分析等不同场景定制化提示词
- **Edge-TTS语音合成**: 免费的高质量中文语音合成
- **专业输出格式**: 三段式结构(核心现状→关键洞察→行动方案)

---

## 🏗️ 技术架构

### 技术栈总览

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue3)                      │
│  Vue 3 + TypeScript + Element Plus + ECharts + Vue Router  │
│                      Port: 5173                             │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/JSON
┌─────────────────────────────────────────────────────────────┐
│                       Backend (FastAPI)                     │
│    FastAPI + Pydantic + pandas + scikit-learn + mlxtend    │
│                      Port: 8000                             │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    External Services                        │
│          OpenAI GPT-4 / Claude API + Edge-TTS              │
└─────────────────────────────────────────────────────────────┘
```

### 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.13.9 | 编程语言 |
| FastAPI | 0.115+ | Web框架 |
| Uvicorn | Latest | ASGI服务器 |
| Pydantic | 2.0+ | 数据验证 |
| pandas | Latest | 数据处理 |
| numpy | Latest | 数值计算 |
| scikit-learn | Latest | 机器学习(KMeans, LinearRegression) |
| mlxtend | Latest | 关联规则挖掘(Apriori) |
| httpx | Latest | 异步HTTP客户端(调用LLM API) |
| edge-tts | Latest | 语音合成 |

### 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.0+ | 渐进式框架 |
| TypeScript | 5.0+ | 类型安全 |
| Vite | 5.0+ | 构建工具 |
| Element Plus | Latest | UI组件库 |
| Vue Router | 4.0+ | 路由管理 |
| Pinia | Latest | 状态管理 |
| Axios | Latest | HTTP客户端 |
| ECharts | 5.0+ | 数据可视化 |
| vue-echarts | Latest | ECharts Vue包装器 |

### 核心算法

1. **RFM模型**: 客户价值评估模型
2. **KMeans聚类**: 客户分群算法(使用StandardScaler标准化)
3. **Apriori算法**: 关联规则挖掘(支持度、置信度、提升度)
4. **线性回归**: 时间序列销售预测
5. **协同过滤**: 基于分群的推荐算法

---

## 📁 项目结构

```
MarketMind/
├── backend/                           # FastAPI 后端
│   ├── api/                          # API 路由层
│   │   ├── projects.py               # 项目管理API
│   │   ├── recommend.py              # 推荐系统API
│   │   ├── association.py            # 关联规则API
│   │   ├── ai_voice.py               # AI语音播报API
│   │   └── voice.py                  # TTS语音API
│   ├── core/                         # 核心配置
│   │   └── config.py                 # 应用配置
│   ├── models/                       # 数据模型
│   │   └── schemas.py                # Pydantic模型
│   ├── services/                     # 业务逻辑层
│   │   ├── recommender_service.py    # 推荐引擎(加载预训练模型)
│   │   ├── ai_voice_service.py       # AI语音服务(LLM+TTS)
│   │   ├── association_service.py    # 关联规则服务
│   │   └── prediction_service.py     # 预测服务
│   ├── data/                         # 数据存储
│   │   ├── model_data.pkl            # 预训练模型(KMeans+关联规则)
│   │   ├── dynamic_rules.csv         # 实时计算的关联规则
│   │   └── audio/                    # 语音文件缓存
│   └── main.py                       # FastAPI入口
│
├── frontend/                          # Vue3 前端
│   ├── src/
│   │   ├── api/                      # API调用封装
│   │   │   ├── association.ts        # 关联规则API
│   │   │   ├── prediction.ts         # 预测API
│   │   │   ├── clustering.ts         # 聚类API
│   │   │   └── voice.ts              # 语音API
│   │   ├── views/                    # 页面组件
│   │   │   ├── Home.vue              # 项目列表首页
│   │   │   ├── ProjectDetail.vue     # 项目详情(仪表盘)
│   │   │   ├── CustomerAnalysis.vue  # 客户详情分析
│   │   │   ├── ProductRecommend.vue  # 商品关联思维导图
│   │   │   └── Settings.vue          # LLM/TTS配置页
│   │   ├── components/               # 可复用组件
│   │   │   ├── Association/          # 关联分析组件
│   │   │   ├── Prediction/           # 预测组件
│   │   │   ├── Clustering/           # 聚类组件
│   │   │   └── Common/               # 通用组件
│   │   ├── router/                   # 路由配置
│   │   │   └── index.ts              # 路由定义
│   │   ├── stores/                   # Pinia状态管理
│   │   ├── styles/                   # 全局样式
│   │   │   └── main.css              # CSS变量+暗色模式
│   │   ├── utils/                    # 工具函数
│   │   ├── App.vue                   # 根组件
│   │   └── main.ts                   # 入口文件
│   ├── public/                       # 静态资源
│   ├── index.html                    # HTML模板
│   ├── package.json                  # 依赖配置
│   ├── tsconfig.json                 # TypeScript配置
│   ├── vite.config.ts                # Vite构建配置
│   └── README.md                     # 前端开发文档
│
├── analysis/                          # 数据分析脚本
│   ├── dataset.csv                   # 原始数据集
│   └── marketing_modeling.py         # 模型训练脚本
│
├── outputs/                           # 运行时输出
│   ├── charts/                       # 图表文件
│   ├── reports/                      # 分析报告
│   └── audio/                        # 语音文件
│
├── data/                             # 项目数据目录(用户上传)
│   └── dataset.csv                   # 当前使用的数据集
│
├── pyproject.toml                    # Python项目配置(uv)
├── uv.lock                           # 依赖锁定文件
├── start-backend.sh                  # 后端启动脚本
└── README.md                         # 本文档
```

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.13+ (推荐使用 `uv` 包管理器)
- **Node.js**: 18.0+
- **包管理器**: npm 或 pnpm

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd MarketMind
```

#### 2. 后端设置

```bash
# 安装 uv (如果未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装Python依赖
uv sync

# 准备数据集(将CSV文件放到 data/dataset.csv)
# 或使用示例数据集
cp analysis/dataset.csv data/dataset.csv

# 启动后端服务
./start-backend.sh
# 或手动启动
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将运行在: http://localhost:8000

API文档: http://localhost:8000/api/docs

#### 3. 前端设置

```bash
cd frontend

# 安装依赖
npm install
# 或
pnpm install

# 启动开发服务器
npm run dev
# 或
pnpm dev
```

前端应用将运行在: http://localhost:5173

### 初始化数据

#### 训练预训练模型

```bash
# 在项目根目录执行
cd analysis
python marketing_modeling.py

# 模型将保存到 backend/data/model_data.pkl
```

模型包含:
- KMeans聚类模型
- StandardScaler标准化器
- 关联规则(单商品规则)
- 客户分群结果
- 特征统计信息

### 配置LLM和TTS

1. 访问 http://localhost:5173/settings
2. 配置LLM API:
   - Provider: OpenAI 或 Claude
   - Base URL: API端点地址
   - API Key: 你的API密钥
   - Model Name: 模型名称(如 gpt-4, claude-sonnet-4)
3. 配置TTS(可选):
   - Voice: zh-CN-XiaoxiaoNeural (默认)
   - Rate: 语速调整
   - Volume: 音量调整

---

## 📡 API文档

### Base URL

```
http://localhost:8000/api
```

### 1. 项目管理

#### 创建项目

```http
POST /api/projects
Content-Type: application/json

{
  "name": "2024年Q1营销分析",
  "description": "第一季度客户行为分析",
  "dataset_path": "data/dataset.csv"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "proj_123",
    "name": "2024年Q1营销分析",
    "created_at": "2024-12-23T10:00:00Z"
  }
}
```

#### 获取项目列表

```http
GET /api/projects
```

#### 获取项目详情

```http
GET /api/projects/{project_id}
```

**响应**: 包含关联规则、聚类结果、预测数据的完整项目信息

#### 获取项目客户列表

```http
GET /api/projects/{project_id}/customers
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": "CG-12345",
      "name": "丁娇-12345",
      "cluster_id": 2,
      "cluster_name": "普通活跃客户",
      "monetary": 5247,
      "frequency": 12,
      "recency": 3
    }
  ]
}
```

### 2. 推荐系统

#### 用户推荐(基于协同过滤)

```http
GET /api/recommend/user?user_id=CG-12345&top_n=10
```

**响应**:
```json
{
  "recommends": [
    {
      "item": "办公椅",
      "category": "家具",
      "score": 0.85,
      "avg_price": 1200,
      "reason": "普通活跃客户偏好度 23.5%"
    }
  ],
  "cluster": {
    "cluster_id": 2,
    "cluster_name": "普通活跃客户",
    "strategy": "提升客单价和复购率"
  },
  "target_customers": [
    {
      "cluster_id": 2,
      "cluster_name": "普通活跃客户",
      "strategy": "提升客单价和复购率"
    }
  ]
}
```

#### 商品推荐(基于关联规则)

```http
GET /api/recommend/item?item=办公椅&top_n=8
```

**响应**:
```json
{
  "item": "办公椅",
  "upstream": [
    {
      "item": "显示器",
      "confidence": 0.65,
      "lift": 2.3,
      "support": 0.08
    }
  ],
  "downstream": [
    {
      "item": "键盘",
      "confidence": 0.72,
      "lift": 2.8,
      "support": 0.12
    }
  ],
  "target_customers": [
    {
      "cluster_name": "高价值客户",
      "buyer_count": 45,
      "lift_index": 2.5,
      "strategy": "保持满意度，推高端产品"
    }
  ]
}
```

### 3. AI语音播报

#### 生成AI营销建议

```http
POST /api/ai-voice/broadcast
Content-Type: application/json

{
  "data": {
    "customer_name": "丁娇",
    "customer_id": "CG-12345",
    "cluster_name": "普通活跃客户",
    "cluster_id": 2,
    "monetary": 5247,
    "frequency": 12,
    "recency": 3,
    "recommendations": [
      {
        "item": "办公椅",
        "score": 0.85,
        "reason": "普通活跃客户偏好度 23.5%"
      }
    ]
  },
  "llm_config": {
    "provider": "openai",
    "baseUrl": "https://api.openai.com/v1",
    "apiKey": "sk-...",
    "modelName": "gpt-4"
  },
  "tts_config": {
    "voice": "zh-CN-XiaoxiaoNeural",
    "rate": "+0%",
    "volume": "+0%"
  },
  "scene_type": "summary"
}
```

**响应**:
```json
{
  "success": true,
  "text": "客户丁娇-CG-12345被分类为'普通活跃客户'，其消费行为特征如下：最近3天购买，累计消费12次，客单价约437元。该客户属于中等价值稳定型，复购意愿强但客单价有提升空间。建议：1)推送高价值商品组合优惠，提升客单价至600元；2)设置会员专属福利，巩固忠诚度；3)定期发送个性化推荐，预计可提升20%消费额。",
  "audio_url": "/outputs/audio/summary_12345.mp3"
}
```

#### 仅TTS语音合成

```http
POST /api/voice/tts
Content-Type: application/json

{
  "text": "这是要转换为语音的文本",
  "voice": "zh-CN-XiaoxiaoNeural",
  "rate": "+0%",
  "volume": "+0%"
}
```

### 4. 关联规则分析

```http
POST /api/association/analyze
Content-Type: application/json

{
  "min_support": 0.02,
  "min_confidence": 0.3,
  "min_lift": 1.0,
  "top_n": 10
}
```

### 健康检查

```http
GET /api/health
```

**响应**:
```json
{
  "status": "healthy",
  "service": "MarketMind Backend"
}
```

---

## 🗺️ 前端路由

| 路径 | 组件 | 功能 |
|------|------|------|
| `/` | Home.vue | 项目列表首页 |
| `/projects/:id` | ProjectDetail.vue | 项目仪表盘(关联+聚类+预测) |
| `/projects/:id/customer/:customerId` | CustomerAnalysis.vue | 客户详情分析页 |
| `/projects/:id/recommend` | ProductRecommend.vue | 商品关联思维导图 |
| `/settings` | Settings.vue | LLM/TTS配置 |

### 路由参数

**ProjectDetail**:
- `:id` - 项目ID

**CustomerAnalysis**:
- `:id` - 项目ID
- `:customerId` - 客户ID

**ProductRecommend**:
- `:id` - 项目ID
- Query参数: `item` - 商品名称(用于自动搜索)

**导航示例**:
```typescript
// 跳转到客户详情
router.push(`/projects/${projectId}/customer/${customerId}`)

// 跳转到商品推荐(自动搜索"办公椅")
router.push(`/projects/${projectId}/recommend?item=${encodeURIComponent('办公椅')}`)
```

---

## 🔄 数据流架构

### 用户推荐流程

```
用户访问客户详情页
    ↓
调用 /api/recommend/user?user_id=xxx
    ↓
后端加载预训练模型(model_data.pkl)
    ↓
提取客户RFM特征 → StandardScaler标准化
    ↓
KMeans预测客户分群
    ↓
查询该分群的商品偏好统计
    ↓
返回推荐列表 + 分群信息
    ↓
前端展示推荐商品
    ↓
用户点击"生成AI建议"
    ↓
调用 /api/ai-voice/broadcast
    ↓
后端调用LLM API生成专业文案
    ↓
(可选)调用Edge-TTS生成语音
    ↓
返回文本 + 音频URL
    ↓
前端展示AI建议并播放语音
```

### 商品关联分析流程

```
用户点击商品卡片
    ↓
路由跳转到 ProductRecommend 页面
    ↓
调用 /api/recommend/item?item=商品名
    ↓
后端查询预训练的关联规则(rules_single)
    ↓
IF 规则存在:
    返回 upstream + downstream 关联商品
ELSE:
    调用 calculate_realtime_rules()
    实时计算Apriori关联规则
    保存到 dynamic_rules.csv
    返回新规则
    ↓
前端渲染思维导图:
    中心节点: 当前商品
    左侧节点: upstream(什么带动它)
    右侧节点: downstream(它带动什么)
    ↓
用户点击关联商品节点
    ↓
递归查询该商品的关联规则
```

---

## 🛠️ 开发指南

### 后端开发

#### 添加新的API端点

```python
# backend/api/example.py
from fastapi import APIRouter
from backend.models.schemas import ExampleRequest, ExampleResponse

router = APIRouter()

@router.post("/example", response_model=ExampleResponse)
async def example_endpoint(request: ExampleRequest):
    # 业务逻辑
    result = process_data(request)
    return {"success": True, "data": result}
```

```python
# backend/main.py
from backend.api import example

app.include_router(example.router, prefix="/api", tags=["示例"])
```

#### 使用推荐系统服务

```python
from backend.services.recommender_service import get_recommender

# 获取推荐引擎实例(单例,自动加载模型)
recommender = get_recommender()

# 用户推荐
result = recommender.recommend_user(user_id="CG-12345", top_n=10)

# 商品推荐
result = recommender.recommend_item(item_name="办公椅", top_n=8)

# 实时计算关联规则
rules = recommender.calculate_realtime_rules(item_name="新商品", min_confidence=0.1)
```

#### 调用AI语音服务

```python
from backend.services.ai_voice_service import AIVoiceService

# 生成AI文案
script = await AIVoiceService.generate_script(
    data=customer_data,
    llm_config={"provider": "openai", "baseUrl": "...", "apiKey": "...", "modelName": "gpt-4"},
    scene_type="summary"
)

# TTS语音合成
audio_path = await AIVoiceService.text_to_speech(
    text=script,
    output_path="outputs/audio/test.mp3",
    voice="zh-CN-XiaoxiaoNeural"
)

# 完整流程(LLM + TTS)
result = await AIVoiceService.generate_voice_broadcast(
    data=customer_data,
    llm_config=llm_config,
    scene_type="summary",
    tts_config=tts_config
)
```

### 前端开发

#### 使用Composition API

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()

const data = ref<any>(null)
const loading = ref(false)

const fetchData = async () => {
  loading.value = true
  try {
    const { data: response } = await axios.get('/api/endpoint')
    data.value = response.data
  } catch (error) {
    console.error('Error:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div v-loading="loading">
    <div v-if="data">{{ data }}</div>
  </div>
</template>
```

#### API调用封装

```typescript
// src/api/recommend.ts
import axios from 'axios'

export const recommendApi = {
  getUserRecommendations: async (userId: string, topN: number = 10) => {
    const { data } = await axios.get('/api/recommend/user', {
      params: { user_id: userId, top_n: topN }
    })
    return data
  },

  getItemAssociations: async (itemName: string, topN: number = 8) => {
    const { data } = await axios.get('/api/recommend/item', {
      params: { item: itemName, top_n: topN }
    })
    return data
  }
}
```

#### 路由导航

```typescript
// 编程式导航
import { useRouter } from 'vue-router'

const router = useRouter()

// 跳转到客户详情
router.push(`/projects/${projectId}/customer/${customerId}`)

// 跳转到商品推荐并自动搜索
router.push({
  path: `/projects/${projectId}/recommend`,
  query: { item: encodeURIComponent(itemName) }
})

// 返回上一页
router.back()
```

---

## 🚢 部署说明

### 开发环境

```bash
# 后端
./start-backend.sh

# 前端(新终端)
cd frontend
npm run dev
```

访问:
- 前端: http://localhost:5173
- 后端API文档: http://localhost:8000/api/docs

### 生产环境

#### 后端部署

```bash
# 使用gunicorn + uvicorn workers
uv run gunicorn backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

#### 前端部署

```bash
cd frontend

# 构建生产版本
npm run build

# 输出到 dist/ 目录
# 部署到静态文件服务器(Nginx/Vercel/Netlify)
```

#### Nginx配置示例

```nginx
# 前端静态文件
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 静态输出文件
    location /outputs {
        proxy_pass http://localhost:8000;
    }
}
```

### Docker部署

#### Dockerfile(后端)

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装uv
RUN pip install uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖
RUN uv sync --no-dev

# 复制代码
COPY backend/ ./backend/
COPY analysis/dataset.csv ./data/dataset.csv

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "gunicorn", "backend.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./outputs:/app/outputs
    environment:
      - PYTHONUNBUFFERED=1

  frontend:
    image: node:18
    working_dir: /app
    volumes:
      - ./frontend:/app
    ports:
      - "5173:5173"
    command: npm run dev
```

启动:
```bash
docker-compose up -d
```

---

## 📊 数据格式

### 输入数据集(CSV)

必需字段:

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| 订单 ID | String | 订单唯一标识 | CA-2020-123456 |
| 订单日期 | Date | 订单日期 | 2020-11-08 |
| 客户 ID | String | 客户唯一标识 | CG-12345 |
| 客户姓名 | String | 客户姓名 | 丁娇 |
| 子类别 | String | 商品子类别 | 办公椅 |
| 类别 | String | 商品大类 | 家具 |
| 销售额 | Float | 订单金额 | 1200.50 |
| 数量 | Integer | 商品数量 | 2 |
| 折扣 | Float | 折扣率 | 0.2 |
| 利润 | Float | 订单利润 | 300.00 |

可选字段:
- 地区
- 细分
- 邮政编码

### 预训练模型(model_data.pkl)

使用 `analysis/marketing_modeling.py` 生成,包含:

```python
{
    "kmeans_model": KMeans对象,
    "cluster_scaler": StandardScaler对象,
    "best_k": int,  # 最佳聚类数
    "cluster_features": List[str],  # 特征列表
    "cluster_profiles": DataFrame,  # 聚类画像
    "cluster_contribution": List[float],  # 各群体贡献度
    "customer_data": DataFrame,  # 客户RFM数据
    "rules_single": DataFrame,  # 关联规则(单商品)
    "feature_stats": Dict,  # 特征统计
    "reference_date": Timestamp,  # 参考日期
    "categories": List[str],  # 类别列表
    "subcategories": List[str],  # 子类别列表
    "regions": List[str],  # 地区列表
    "segments": List[str]  # 细分列表
}
```

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request!

### 开发流程

1. Fork本仓库
2. 创建特性分支: `git checkout -b feature/AmazingFeature`
3. 提交更改: `git commit -m 'Add some AmazingFeature'`
4. 推送到分支: `git push origin feature/AmazingFeature`
5. 提交Pull Request

### 代码规范

- **后端**: 遵循PEP 8 Python编码规范
- **前端**: 使用ESLint + Prettier格式化代码
- **提交信息**: 使用语义化提交规范(Conventional Commits)

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Element Plus](https://element-plus.org/) - Vue 3组件库
- [scikit-learn](https://scikit-learn.org/) - 机器学习库
- [mlxtend](http://rasbt.github.io/mlxtend/) - 关联规则挖掘
- [Edge-TTS](https://github.com/rany2/edge-tts) - 免费TTS服务

---

**当前版本**: 2.0.0
**最后更新**: 2025-12-23
**架构**: Vue3 + FastAPI 全栈分离
**团队**: MarketMind Development Team
