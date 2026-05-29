<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Cpu, ArrowLeft } from 'lucide-vue-next'
import { generateCustomerSuggestion, getApiErrorMessage } from '../api'

const router = useRouter()

// LLM Configuration
interface LLMConfig {
  provider: 'openai' | 'claude'
  baseUrl: string
  apiKey: string
  modelName: string
}

const llmConfig = ref<LLMConfig>({
  provider: 'openai',
  baseUrl: 'https://api.openai.com/v1',
  apiKey: '',
  modelName: 'gpt-4o'
})

const llmTesting = ref(false)
const llmSaving = ref(false)

const loadConfig = () => {
  const savedLLM = localStorage.getItem('llm_config')
  if (savedLLM) {
    try {
      llmConfig.value = JSON.parse(savedLLM)
    } catch (e) {
      console.error('Failed to parse LLM config', e)
    }
  }
}


// LLM functions
const saveLLMConfig = () => {
  llmSaving.value = true
  try {
    localStorage.setItem('llm_config', JSON.stringify(llmConfig.value))
    ElMessage.success('LLM 配置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    llmSaving.value = false
  }
}

const testLLMConnection = async () => {
  if (!llmConfig.value.apiKey) {
    ElMessage.warning('请先填写 API Key')
    return
  }

  llmTesting.value = true
  try {
    const response = await generateCustomerSuggestion({
      data: {
        scene_type: 'settings_test',
        customer_name: '配置测试',
        recommendations: []
      },
      llm_config: llmConfig.value
    })

    if (response.success) {
      ElMessage.success('后端建议接口测试成功')
    }
  } catch (error) {
    ElMessage.error(`连接测试失败: ${getApiErrorMessage(error)}`)
  } finally {
    llmTesting.value = false
  }
}

const applyTemplate = (template: 'openai' | 'claude' | 'deepseek') => {
  const templates = {
    openai: {
      provider: 'openai' as const,
      baseUrl: 'https://api.openai.com/v1',
      modelName: 'gpt-4o',
      apiKey: llmConfig.value.apiKey
    },
    claude: {
      provider: 'claude' as const,
      baseUrl: 'https://api.anthropic.com/v1',
      modelName: 'claude-3-5-sonnet-20241022',
      apiKey: llmConfig.value.apiKey
    },
    deepseek: {
      provider: 'openai' as const,
      baseUrl: 'https://api.deepseek.com/v1',
      modelName: 'deepseek-chat',
      apiKey: llmConfig.value.apiKey
    }
  }

  llmConfig.value = { ...llmConfig.value, ...templates[template] }
  ElMessage.info(`已应用 ${template.toUpperCase()} 模板`)
}

onMounted(() => {
  loadConfig()
})
</script>

<template>
  <div class="settings-page-wrapper">
    <div class="settings-focus-container">
      <nav class="settings-breadcrumb">
        <button class="breadcrumb-back" @click="router.push('/me/profile')">
          <ArrowLeft /> 返回个人信息
        </button>
      </nav>

      <header class="settings-hero">
        <h1 class="slogan-display" style="font-size: 3rem; margin-bottom: 8px;">系统设置</h1>
        <p class="text-subtitle">管理您的服务连接与偏好</p>
      </header>

      <div class="settings-sections">
        <!-- AI 模型设置卡片 -->
        <section class="glass-settings-card">
          <div class="card-header-minimal">
            <div class="header-info">
              <h3 class="card-title" style="display: flex; align-items: center; gap: 10px">
                <Cpu /> AI 模型设置
              </h3>
              <p class="card-desc">配置 LLM 服务，用于生成智能营销建议</p>
            </div>
          </div>

          <div class="glass-form">
            <div class="template-pills">
              <span class="template-label">快捷模板:</span>
              <button @click="applyTemplate('openai')">OpenAI</button>
              <button @click="applyTemplate('claude')">Claude</button>
              <button @click="applyTemplate('deepseek')">DeepSeek</button>
            </div>

            <div class="form-row-precise">
              <div style="flex: 1">
                <label>模型类型</label>
                <el-select v-model="llmConfig.provider" class="full-width">
                  <el-option label="OpenAI 类型" value="openai" />
                  <el-option label="Claude 类型" value="claude" />
                </el-select>
              </div>

              <div style="flex: 2">
                <label>模型名称</label>
                <el-input
                  v-model="llmConfig.modelName"
                  placeholder="gpt-4o, claude-3-5-sonnet 等"
                />
              </div>
            </div>

            <div class="glass-form-item">
              <label>API 服务器 (Base URL)</label>
              <el-input v-model="llmConfig.baseUrl" placeholder="https://api.openai.com/v1" />
              <p class="hint-text" style="margin-top: 4px">支持第三方转发代理或自建中转地址</p>
            </div>

            <div class="glass-form-item">
              <label>API Key</label>
              <el-input
                v-model="llmConfig.apiKey"
                type="password"
                placeholder="sk-..."
                show-password
              />
            </div>

            <div class="glass-actions">
              <div class="hint-text">
                用于生成客户建议和商品洞察文本
              </div>

              <div style="display: flex; gap: 12px;">
                <el-button @click="testLLMConnection" :loading="llmTesting">
                  测试连接
                </el-button>
                <el-button type="primary" @click="saveLLMConfig" :loading="llmSaving" class="btn-premium">
                  保存 AI 配置
                </el-button>
              </div>
            </div>
          </div>
        </section>

        <!-- 偏好设置卡片 -->
        <section class="glass-settings-card">
          <div class="card-header-minimal">
            <div class="header-info">
              <h3 class="card-title">视觉与交互</h3>
              <p class="card-desc">系统外观与视觉反馈选项</p>
            </div>
          </div>
          <div class="placeholder-content-glass">
            更多个性化选项（如动态模糊强度、动画节奏）即将上线
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-breadcrumb {
  display: flex;
  align-items: center;
}

.breadcrumb-back {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 6px 0;
  transition: color 160ms ease;
}

.breadcrumb-back:hover {
  color: #6366f1;
}

.settings-page-wrapper {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  padding: 60px 24px;
}

.settings-focus-container {
  width: 100%;
  max-width: 720px;
  display: flex;
  flex-direction: column;
  gap: 40px;
}

.settings-hero {
  text-align: center;
}

.settings-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.glass-settings-card {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 32px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  transition: transform 0.3s var(--ease-spring), box-shadow 0.3s ease;
}

html.dark .glass-settings-card {
  background: rgba(22, 22, 24, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.glass-settings-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.08);
}

.card-header-minimal {
  margin-bottom: 32px;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
}

.card-desc {
  font-size: 0.9rem;
  color: var(--text-tertiary);
  margin: 4px 0 0 0;
}

.glass-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-row-precise {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.field-protocol { flex: 0 0 140px; }
.field-ip { flex: 1; }
.field-port { flex: 0 0 100px; }

label {
  display: block;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 8px;
  padding-left: 4px;
}

.glass-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding-top: 24px;
  border-top: 1px solid var(--border-subtle);
}

.connection-status-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: var(--radius-pill);
  font-size: 0.85rem;
  font-weight: 600;
}

html.dark .connection-status-pill {
  background: rgba(255, 255, 255, 0.05);
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.connected .pulse-dot {
  background: #10b981;
  box-shadow: 0 0 12px #10b981;
  animation: pulse-ring 2s infinite;
}

.disconnected .pulse-dot {
  background: #ef4444;
  box-shadow: 0 0 12px #ef4444;
}

@keyframes pulse-ring {
  0% { transform: scale(0.95); opacity: 1; }
  50% { transform: scale(1.15); opacity: 0.7; }
  100% { transform: scale(0.95); opacity: 1; }
}

.status-label {
  color: var(--text-secondary);
}

.template-pills {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--nav-pill-bg);
  padding: 8px 16px;
  border-radius: 12px;
}

.template-pills button {
  border: none;
  background: var(--color-surface);
  padding: 4px 12px;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
  transition: 0.2s;
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
}

.template-pills button:hover {
  background: var(--color-accent);
  color: white;
}

.btn-premium {
  border-radius: 12px !important;
  padding: 12px 24px !important;
  font-weight: 700 !important;
}

.hint-text {
  font-size: 0.8rem;
  color: var(--text-tertiary);
  font-style: italic;
}

.info-grid-settings {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.info-tag-item {
  background: var(--nav-pill-bg);
  padding: 6px 14px;
  border-radius: 10px;
  display: flex;
  gap: 8px;
  font-size: 0.75rem;
  border: 1px solid var(--border-subtle);
}

.it-l { color: var(--text-tertiary); font-weight: 600; }
.it-v { color: var(--text-primary); font-weight: 700; }

.placeholder-content-glass {
  color: var(--text-tertiary);
  font-style: italic;
  text-align: center;
  padding: 24px;
  border: 1px dashed var(--border-subtle);
  border-radius: 16px;
}

.full-width { width: 100%; }
</style>
