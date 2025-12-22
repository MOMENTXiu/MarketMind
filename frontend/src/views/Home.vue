<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goToProjects = () => {
  router.push('/projects')
}
</script>

<template>
  <div class="home-wrapper">
    <!-- 银色弥散背景装饰 -->
    <div class="silver-glass-background">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
    </div>

    <div class="container-breath content-overlay">
      <!-- Hero Section -->
      <header class="hero-section">
        <div class="hero-content">
          <h1 class="slogan-display">数据洞察 触手可及</h1>
          <p class="text-subtitle">
            MarketMind 是您的超市 AI 营销专家。<br>
            通过关联规则、预测模型与客户聚类，释放数据潜力。
          </p>
          
          <div class="hero-actions">
            <el-button type="primary" size="large" @click="goToProjects" class="btn-hero">
              开始探索
            </el-button>
          </div>
        </div>
      </header>

      <!-- Footer -->
      <footer class="minimal-footer">
        <p>Powered by MarketMind Intelligence Engine v1.0</p>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.home-wrapper {
  position: relative;
  min-height: 100vh; /* Changed from calc(100vh - 64px) to 100vh */
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 银色毛玻璃背景系统 */
.silver-glass-background {
  position: fixed; /* Changed from absolute to fixed for full viewport coverage */
  inset: 0;
  z-index: 0;
  height: 100vh;
  width: 100vw;
  background: radial-gradient(circle at 50% 50%, #f0f0f5 0%, #e5e5f0 100%);
  overflow: hidden;
  pointer-events: none; /* Ensure clicks pass through */
  transition: background 0.5s ease;
}

html.dark .silver-glass-background {
  background: radial-gradient(circle at 50% 50%, #1a1a1e 0%, #0d0d0f 100%);
}

.silver-glass-background::after {
  content: "";
  position: absolute;
  inset: 0;
  backdrop-filter: blur(120px) saturate(180%);
  background: rgba(255, 255, 255, 0.2);
}

html.dark .silver-glass-background::after {
  background: rgba(0, 0, 0, 0.4);
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  animation: float 20s infinite ease-in-out;
}

.orb-1 {
  width: 600px;
  height: 600px;
  top: -200px;
  left: -100px;
  background: linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%);
}

html.dark .orb-1 {
  background: linear-gradient(135deg, #374151 0%, #111827 100%);
}

.orb-2 {
  width: 500px;
  height: 500px;
  bottom: -150px;
  right: -50px;
  background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
  animation-delay: -5s;
}

html.dark .orb-2 {
  background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
}

.orb-3 {
  width: 400px;
  height: 400px;
  top: 10%; /* Adjusted from 20% to cover top better */
  right: 15%;
  background: radial-gradient(circle, #ffffff 0%, #f3f4f6 100%);
  animation-delay: -10s;
}

html.dark .orb-3 {
  background: radial-gradient(circle, #4b5563 0%, #1f2937 100%);
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(40px, -60px) scale(1.1); }
  66% { transform: translate(-30px, 30px) scale(0.9); }
}

.content-overlay {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-top: 64px; /* Maintain content spacing below navbar height */
}

.hero-section {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 80px 0;
}

.hero-content {
  max-width: 900px;
}

/* Slogan 字体增大 20% (3.5rem * 1.2 = 4.2rem) */
.slogan-display {
  font-size: 4.2rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.1;
  margin-bottom: 32px;
  background: linear-gradient(180deg, #1A1A1C 0%, #4A4A4E 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  color: var(--text-primary);
}

html.dark .slogan-display {
  background: linear-gradient(180deg, #FFFFFF 0%, #A1A1A6 100%);
  -webkit-background-clip: text;
}

.text-subtitle {
  font-size: 1.25rem;
  color: var(--text-secondary);
  line-height: 1.8;
  margin-bottom: 48px;
  font-weight: 400;
}

.btn-hero {
  padding: 16px 48px !important;
  font-size: 1.1rem !important;
  border-radius: var(--radius-pill) !important;
  box-shadow: 0 20px 40px -10px rgba(0,0,0,0.1) !important;
}

.minimal-footer {
  text-align: center;
  color: var(--text-tertiary);
  font-size: 0.8rem;
  padding-bottom: 40px;
  opacity: 0.5;
}

@media (max-width: 768px) {
  .slogan-display {
    font-size: 2.8rem;
  }
}
</style>
