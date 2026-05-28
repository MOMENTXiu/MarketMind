<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Sparkles, Eye, Brain, Zap, BarChart3, Shield } from 'lucide-vue-next'

const router = useRouter()

const goToProjects = () => {
  router.push('/projects')
}

const goToIntro = () => {
  router.push('/project-intro')
}
</script>

<template>
  <div class="home-wrapper">

    <!-- 背景网格线装饰 -->
    <div class="bg-grid" aria-hidden="true"></div>

    <!-- 右侧装饰圆环 -->
    <div class="bg-decoration" aria-hidden="true">
      <div class="ring ring-1"></div>
      <div class="ring ring-2"></div>
      <div class="ring ring-3"></div>
    </div>

    <div class="hero-section">
      <div class="hero-content">

        <div class="product-badge">
          <Sparkles class="badge-icon" />
          <span>新一代 AI 数据分析平台</span>
        </div>

        <h1 class="main-title">
          数据<span class="gradient-text">洞察</span> 触手可及
        </h1>

        <p class="subtitle">
          上传数据，自动生成销售概览、客户分群、关联规则、个性化推荐与促销分析结果。
        </p>

        <div class="hero-actions">
          <button class="btn-secondary" @click="goToIntro">
            <Eye class="btn-icon" />
            <span>探索演示</span>
          </button>
          <button class="btn-primary" @click="goToProjects">
            <span>开始分析</span>
          </button>
        </div>

        <div class="feature-grid">
          <div class="feature-item">
            <div class="feature-icon">
              <Brain />
            </div>
            <h3 class="feature-title">AI 智能分析</h3>
            <p class="feature-desc">自动识别销售、客户与商品结构</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <Zap />
            </div>
            <h3 class="feature-title">实时洞察</h3>
            <p class="feature-desc">快速生成可读的业务分析结果</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <BarChart3 />
            </div>
            <h3 class="feature-title">可视化呈现</h3>
            <p class="feature-desc">输出图表、指标与业务建议</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <Shield />
            </div>
            <h3 class="feature-title">安全可靠</h3>
            <p class="feature-desc">数据处理过程清晰可追溯</p>
          </div>
        </div>

      </div>
    </div>

    <footer class="minimal-footer">
      <p>Powered by MarketMind Intelligence Engine v1.0</p>
    </footer>
  </div>
</template>

<style scoped>
.home-wrapper {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 85% 55%, rgba(99, 102, 241, 0.12), transparent 34%),
    radial-gradient(circle at 50% 50%, rgba(168, 85, 247, 0.08), transparent 30%),
    linear-gradient(135deg, #f8fbff 0%, #f7f5ff 45%, #ffffff 100%);
  overflow: hidden;
}

html.dark .home-wrapper {
  background:
    radial-gradient(circle at 85% 55%, rgba(99, 102, 241, 0.10), transparent 34%),
    radial-gradient(circle at 50% 50%, rgba(168, 85, 247, 0.06), transparent 30%),
    linear-gradient(135deg, #0f0f17 0%, #12101f 45%, #0a0a10 100%);
}

/* 背景网格线装饰 */
.bg-grid {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(99, 102, 241, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99, 102, 241, 0.06) 1px, transparent 1px);
  background-size: 72px 48px;
}

html.dark .bg-grid {
  background-image:
    linear-gradient(rgba(99, 102, 241, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99, 102, 241, 0.05) 1px, transparent 1px);
}

/* 右侧装饰圆环 */
.bg-decoration {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(99, 102, 241, 0.12);
  right: -180px;
  top: 50%;
  transform: translateY(-50%);
}

.ring-1 { width: 500px; height: 500px; }
.ring-2 { width: 620px; height: 620px; opacity: 0.6; }
.ring-3 { width: 740px; height: 740px; opacity: 0.3; }

/* Hero */
.hero-section {
  position: relative;
  z-index: 1;
  min-height: calc(100vh - 72px);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 80px 0;
}

.hero-content {
  max-width: 880px;
  margin: 0 auto;
  padding: 0 40px;
}

/* Product Badge */
.product-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(99, 102, 241, 0.18);
  color: #4f46e5;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.08);
  margin-bottom: 32px;
}

html.dark .product-badge {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(99, 102, 241, 0.24);
  color: #a5b4fc;
}

.badge-icon {
  width: 16px;
  height: 16px;
}

/* Main Title */
.main-title {
  font-size: clamp(48px, 6vw, 76px);
  line-height: 1.08;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: #111827;
  margin: 0;
}

html.dark .main-title {
  color: #f1f5f9;
}

.gradient-text {
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Subtitle */
.subtitle {
  margin-top: 24px;
  font-size: 18px;
  line-height: 1.8;
  color: #64748b;
  max-width: 720px;
  margin-left: auto;
  margin-right: auto;
}

html.dark .subtitle {
  color: #94a3b8;
}

/* CTA Buttons */
.hero-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 36px;
}

.btn-secondary,
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 52px;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  font-family: inherit;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, border-color 160ms ease;
}

.btn-secondary {
  padding: 0 30px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(99, 102, 241, 0.26);
  color: #334155;
  font-weight: 600;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(16px);
}

html.dark .btn-secondary {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(99, 102, 241, 0.3);
  color: #cbd5e1;
}

.btn-secondary:hover {
  background: #fff;
  border-color: rgba(99, 102, 241, 0.42);
  transform: translateY(-1px);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.10);
}

html.dark .btn-secondary:hover {
  background: rgba(255, 255, 255, 0.12);
}

.btn-primary {
  padding: 0 34px;
  border-radius: 999px;
  background: linear-gradient(135deg, #6366f1 0%, #7c3aed 52%, #2563eb 100%);
  color: #fff;
  font-weight: 700;
  box-shadow:
    0 16px 36px rgba(99, 102, 241, 0.32),
    inset 0 1px 0 rgba(255, 255, 255, 0.28);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow:
    0 20px 44px rgba(99, 102, 241, 0.38),
    inset 0 1px 0 rgba(255, 255, 255, 0.32);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-icon {
  width: 18px;
  height: 18px;
}

/* Feature Highlights */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 32px;
  margin-top: 72px;
}

.feature-item {
  text-align: center;
}

.feature-icon {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.10);
  color: #6366f1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.feature-icon svg {
  width: 20px;
  height: 20px;
}

.feature-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 6px;
}

html.dark .feature-title {
  color: #f1f5f9;
}

.feature-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
  margin: 0;
}

html.dark .feature-desc {
  color: #94a3b8;
}

/* Footer */
.minimal-footer {
  position: relative;
  z-index: 1;
  text-align: center;
  padding-bottom: 32px;
}

.minimal-footer p {
  font-size: 12px;
  color: rgba(100, 116, 139, 0.45);
  margin: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .hero-content {
    padding: 0 24px;
  }

  .hero-actions {
    flex-direction: column;
    align-items: center;
    width: 100%;
    max-width: 320px;
    margin-left: auto;
    margin-right: auto;
  }

  .btn-secondary,
  .btn-primary {
    width: 100%;
    justify-content: center;
  }

  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }
}

@media (max-width: 480px) {
  .feature-grid {
    grid-template-columns: 1fr;
  }
}
</style>
