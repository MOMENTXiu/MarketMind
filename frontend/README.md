# MarketMind Frontend - Vue3 前端

## 技术栈

- **Vue 3** - 渐进式JavaScript框架
- **Vite** - 新一代前端构建工具
- **TypeScript** - 类型安全
- **Pinia** - 状态管理
- **Vue Router** - 路由
- **Axios** - HTTP 客户端
- **Element Plus** - UI组件库
- **ECharts** - 数据可视化

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
# 或使用 pnpm
pnpm install
```

### 2. 开发运行

```bash
npm run dev
```

访问: http://localhost:5173

### 3. 构建生产版本

```bash
npm run build
```

## 项目结构

```
frontend/
├── src/
│   ├── assets/           # 静态资源
│   ├── components/       # 组件
│   ├── stores/           # Pinia 状态管理
│   ├── router/           # 路由配置
│   ├── views/            # 页面
│   │   ├── Home.vue
│   │   ├── ProjectList.vue
│   │   ├── ProjectCreate.vue
│   │   ├── ProjectDetail.vue
│   │   ├── CustomerAnalysis.vue
│   │   ├── ProductRecommend.vue
│   │   ├── Association.vue
│   │   ├── Prediction.vue
│   │   ├── Clustering.vue
│   │   ├── Voice.vue
│   │   └── Settings.vue
│   ├── styles/           # 样式
│   ├── utils/            # 工具函数
│   ├── App.vue
│   └── main.ts
├── public/               # 公共资源
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 初始化命令

在 `frontend/` 目录下执行：

```bash
# 使用 Vite 创建 Vue3 项目
npm create vite@latest . -- --template vue-ts

# 安装依赖
npm install

# 安装UI组件库
npm install element-plus

# 安装路由
npm install vue-router@4

# 安装状态管理
npm install pinia

# 安装 HTTP 客户端
npm install axios

# 安装图表库
npm install echarts vue-echarts

# 安装工具库
npm install @vueuse/core dayjs
```

## 环境变量

创建 `.env.development` 和 `.env.production`:

```env
# .env.development
VITE_API_BASE_URL=http://localhost:8000/api
VITE_API_TIMEOUT=30000

# .env.production
VITE_API_BASE_URL=/api
VITE_API_TIMEOUT=30000
```

## API 调用示例

```typescript
import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL })

// 当前 runtime：创建 Retail Analysis V2 项目
const project = await api.post('/analysis/projects', {
  name: 'Retail analysis',
  description: 'Store transaction analysis'
})
```

下一阶段后端计划切换到 `regularization -> analysis2` 的通用数据处理链路；
前端接口应以后端新 contract tests 和 architecture docs 为准，不要假设旧
Retail V2 响应结构长期稳定。

## 开发规范

- 使用 TypeScript 进行类型检查
- 组件使用 `<script setup>` 语法
- 遵循 Vue 3 Composition API
- 使用 ESLint + Prettier 格式化代码
