<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const healthStatus = ref<string>('checking')

// 检查后端健康状态
const checkBackendHealth = async () => {
  try {
    const response = await axios.get('/api/health')
    if (response.data.status === 'healthy') {
      healthStatus.value = 'healthy'
      ElMessage.success('后端API连接正常')
    }
  } catch (error) {
    healthStatus.value = 'error'
    ElMessage.error('无法连接到后端API，请确保后端已启动')
  }
}

onMounted(() => {
  checkBackendHealth()
})

const goToProjects = () => {
  router.push('/projects')
}

const goToMyProjects = () => {
  router.push('/me/projects')
}
</script>

<template>
  <div class="home-container">
    <header class="header">
      <h1>🛒 MarketMind</h1>
      <p class="subtitle">超市AI营销系统</p>
      <div class="status-badge" :class="healthStatus">
        <span v-if="healthStatus === 'healthy'">✅ 后端连接正常</span>
        <span v-else-if="healthStatus === 'error'">❌ 后端未启动</span>
        <span v-else>⏳ 检查中...</span>
      </div>
    </header>

    <main class="main-content">
      <div class="intro-section">
        <h2>项目分析管理</h2>
        <p>创建、管理和分析您的营销数据项目</p>
      </div>

      <div class="action-buttons">
        <el-button type="primary" size="large" @click="goToProjects">
          ➕ 新建项目
        </el-button>
        <el-button type="default" size="large" @click="goToMyProjects">
          📋 我的项目
        </el-button>
        <el-button type="success" size="large" @click="$router.push('/settings')">
          ⚙️ 设置
        </el-button>
      </div>

      <div class="features-grid">
        <el-card class="info-card">
          <div class="card-icon">📊</div>
          <h3>关联规则分析</h3>
          <p>基于Apriori算法的购物篮分析</p>
          <p class="detail">发现商品组合规律，制定促销策略</p>
        </el-card>

        <el-card class="info-card">
          <div class="card-icon">📈</div>
          <h3>销售预测</h3>
          <p>时间序列预测模型</p>
          <p class="detail">预测未来销售额和利润趋势</p>
        </el-card>

        <el-card class="info-card">
          <div class="card-icon">👥</div>
          <h3>客户聚类</h3>
          <p>RFM模型 + K-Means聚类</p>
          <p class="detail">精准客户分群，实现定向营销</p>
        </el-card>

        <el-card class="info-card">
          <div class="card-icon">🔊</div>
          <h3>语音播报</h3>
          <p>AI自动生成分析报告</p>
          <p class="detail">智能语音播报分析结果</p>
        </el-card>
      </div>

      <div class="tech-stack">
        <h3>技术栈</h3>
        <div class="tech-tags">
          <el-tag>Vue 3</el-tag>
          <el-tag type="success">FastAPI</el-tag>
          <el-tag type="info">TypeScript</el-tag>
          <el-tag type="warning">Element Plus</el-tag>
          <el-tag type="danger">ECharts</el-tag>
        </div>
      </div>
    </main>

    <footer class="footer">
      <p>MarketMind v1.0.0 | Vue3 + FastAPI 前后端分离架构</p>
    </footer>
  </div>
</template>

<style scoped>
.home-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 3rem 2rem;
  text-align: center;
}

.header h1 {
  font-size: 3rem;
  margin: 0;
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 1.2rem;
  margin: 0;
  opacity: 0.9;
}

.status-badge {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  display: inline-block;
  font-size: 0.9rem;
}

.status-badge.healthy {
  background-color: rgba(103, 194, 58, 0.2);
}

.status-badge.error {
  background-color: rgba(245, 108, 108, 0.2);
}

.main-content {
  flex: 1;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  width: 100%;
}

.intro-section {
  text-align: center;
  margin-bottom: 3rem;
}

.intro-section h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.intro-section p {
  color: #666;
  font-size: 1.1rem;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.info-card {
  text-align: center;
  padding: 1rem;
  transition: all 0.3s ease;
}

.info-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.card-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  color: #333;
  margin-bottom: 0.5rem;
}

.feature-card p {
  color: #666;
  margin: 0.5rem 0;
}

.detail {
  font-size: 0.9rem;
  color: #999;
  margin-bottom: 1rem;
}

.tech-stack {
  text-align: center;
  padding: 2rem;
  background: white;
  border-radius: 8px;
}

.tech-stack h3 {
  color: #333;
  margin-bottom: 1rem;
}

.tech-tags {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.footer {
  background-color: #333;
  color: white;
  text-align: center;
  padding: 1.5rem;
  margin-top: auto;
}

.footer p {
  margin: 0;
  opacity: 0.8;
}
</style>
