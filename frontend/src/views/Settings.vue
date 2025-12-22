<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { Connection, Setting, Check, Close } from '@element-plus/icons-vue'

const protocol = ref('http')
const ip = ref('127.0.0.1')
const port = ref('8000')
const testLoading = ref(false)
const connectionStatus = ref<'connected' | 'disconnected' | 'unknown'>('unknown')

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

// TTS Configuration
interface TTSConfig {
  voice: string
  rate: string
  volume: string
}

const ttsConfig = ref<TTSConfig>({
  voice: 'zh-CN-YunxiNeural',
  rate: '+0%',
  volume: '+0%'
})

const ttsTesting = ref(false)
const ttsSaving = ref(false)

// Slider values (for UI binding)
const rateValue = ref(0)
const volumeValue = ref(0)

// Convert slider value to percentage string
const updateRate = (val: number) => {
  ttsConfig.value.rate = val >= 0 ? `+${val}%` : `${val}%`
}

const updateVolume = (val: number) => {
  ttsConfig.value.volume = val >= 0 ? `+${val}%` : `${val}%`
}

// Get friendly voice name
const getVoiceName = (voice: string) => {
  const names: Record<string, string> = {
    'zh-CN-YunxiNeural': '云希 (男声 - 专业)',
    'zh-CN-XiaoxiaoNeural': '晓晓 (女声 - 温柔)',
    'zh-CN-YunyangNeural': '云扬 (男声 - 活力)',
    'zh-CN-XiaoyiNeural': '晓伊 (女声 - 活泼)',
    'zh-CN-YunjianNeural': '云健 (男声 - 稳重)',
    'zh-CN-XiaomengNeural': '晓梦 (女声 - 温暖)',
    'zh-CN-YunyeNeural': '云野 (男声 - 清晰)',
    'zh-CN-XiaomoNeural': '晓墨 (女声 - 知性)'
  }
  return names[voice] || voice
}

// Load existing config
const loadConfig = () => {
  const savedUrl = localStorage.getItem('API_BASE_URL')
  if (savedUrl) {
    try {
      const url = new URL(savedUrl)
      protocol.value = url.protocol.replace(':', '')
      ip.value = url.hostname
      port.value = url.port || (protocol.value === 'https' ? '443' : '80')
    } catch (e) {
      console.error('Failed to parse saved API URL', e)
    }
  }

  // Load LLM config
  const savedLLM = localStorage.getItem('llm_config')
  if (savedLLM) {
    try {
      llmConfig.value = JSON.parse(savedLLM)
    } catch (e) {
      console.error('Failed to parse LLM config', e)
    }
  }

  // Load TTS config
  const savedTTS = localStorage.getItem('tts_config')
  if (savedTTS) {
    try {
      ttsConfig.value = JSON.parse(savedTTS)
      // Initialize slider values
      rateValue.value = parseInt(ttsConfig.value.rate.replace('%', ''))
      volumeValue.value = parseInt(ttsConfig.value.volume.replace('%', ''))
    } catch (e) {
      console.error('Failed to parse TTS config', e)
    }
  }
}

const testAndSave = async () => {
  const baseUrl = `${protocol.value}://${ip.value}:${port.value}`
  testLoading.value = true
  
  try {
    // Attempt to ping the health endpoint at the NEW address
    const response = await axios.get(`${baseUrl}/api/health`, { timeout: 5000 })
    
    if (response.status === 200) {
      localStorage.setItem('API_BASE_URL', baseUrl)
      connectionStatus.value = 'connected'
      ElMessage.success('连接测试成功，配置已保存')
    } else {
      throw new Error('服务响应异常')
    }
  } catch (error: any) {
    connectionStatus.value = 'disconnected'
    ElMessage.error(`连接测试失败: ${error.message || '无法访问该地址'}`)
  } finally {
    testLoading.value = false
  }
}

const checkCurrentStatus = async () => {
  try {
    const response = await axios.get('/api/health', { timeout: 3000 })
    if (response.status === 200) connectionStatus.value = 'connected'
    else connectionStatus.value = 'disconnected'
  } catch (e) {
    connectionStatus.value = 'disconnected'
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
    const headers: Record<string, string> = {}

    if (llmConfig.value.provider === 'openai') {
      headers['Authorization'] = `Bearer ${llmConfig.value.apiKey}`
    } else if (llmConfig.value.provider === 'claude') {
      headers['x-api-key'] = llmConfig.value.apiKey
      headers['anthropic-version'] = '2023-06-01'
    }

    const response = await axios.get(`${llmConfig.value.baseUrl}/models`, {
      headers,
      timeout: 10000
    })

    if (response.status === 200) {
      ElMessage.success('连接成功！LLM API 配置正常')
    }
  } catch (error: any) {
    console.error('LLM connection test failed:', error)
    const msg = error.response?.data?.error?.message || error.message || '连接失败'
    ElMessage.error(`连接测试失败: ${msg}`)
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

// TTS functions
const saveTTSConfig = () => {
  ttsSaving.value = true
  try {
    localStorage.setItem('tts_config', JSON.stringify(ttsConfig.value))
    ElMessage.success('TTS 配置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    ttsSaving.value = false
  }
}

const testTTS = async () => {
  ttsTesting.value = true
  try {
    const response = await axios.post('/api/tts', {
      text: `您好，这是 ${ttsConfig.value.voice} 的语音测试，语速${ttsConfig.value.rate}，音量${ttsConfig.value.volume}。`,
      voice: ttsConfig.value.voice,
      rate: ttsConfig.value.rate,
      volume: ttsConfig.value.volume
    })

    if (response.data.success) {
      // 播放音频
      const audio = new Audio(response.data.audio_url)
      audio.play()
      ElMessage.success('语音测试成功')
    }
  } catch (error: any) {
    console.error('TTS test failed:', error)
    const msg = error.response?.data?.detail || error.message
    ElMessage.error(`测试失败: ${msg}`)
  } finally {
    ttsTesting.value = false
  }
}

onMounted(() => {
  loadConfig()
  checkCurrentStatus()
})
</script>

<template>
  <div class="settings-page-wrapper">
    <div class="settings-focus-container">
      <header class="settings-hero">
        <h1 class="slogan-display" style="font-size: 3rem; margin-bottom: 8px;">系统设置</h1>
        <p class="text-subtitle">管理您的服务连接与偏好</p>
      </header>

      <div class="settings-sections">
        <!-- 服务器地址配置卡片 -->
        <section class="glass-settings-card">
          <div class="card-header-minimal">
            <div class="header-info">
              <h3 class="card-title">服务器地址</h3>
              <p class="card-desc">配置后端 API 的访问基准地址</p>
            </div>
          </div>

          <div class="glass-form">
            <div class="form-row-adaptive">
              <div class="glass-form-item protocol">
                <label>协议</label>
                <el-select v-model="protocol" size="large">
                  <el-option label="http://" value="http" />
                  <el-option label="https://" value="https" />
                </el-select>
              </div>
              
              <div class="glass-form-item ip">
                <label>后端 IP / 域名</label>
                <el-input v-model="ip" placeholder="127.0.0.1" size="large" />
              </div>

              <div class="glass-form-item port">
                <label>端口</label>
                <el-input v-model="port" placeholder="8000" size="large" />
              </div>
            </div>

            <div class="glass-actions">
              <div class="connection-status-pill" :class="connectionStatus">
                <span class="pulse-dot"></span>
                <span class="status-label">
                  {{ connectionStatus === 'connected' ? '服务已连接' : (connectionStatus === 'disconnected' ? '连接已断开' : '等待测试') }}
                </span>
              </div>
              
              <el-button 
                type="primary" 
                @click="testAndSave" 
                :loading="testLoading"
                class="btn-glass-action"
              >
                测试并保存
              </el-button>
            </div>
          </div>
        </section>

        <!-- AI 模型设置卡片 -->
        <section class="glass-settings-card">
          <div class="card-header-minimal">
            <div class="header-info">
              <h3 class="card-title">🤖 AI 模型设置</h3>
              <p class="card-desc">配置 LLM 服务，用于生成智能播报文案</p>
            </div>
          </div>

          <div class="glass-form">
            <!-- 快捷模板 -->
            <div class="template-buttons">
              <span class="template-label">快捷模板：</span>
              <el-button size="small" @click="applyTemplate('openai')">OpenAI</el-button>
              <el-button size="small" @click="applyTemplate('claude')">Claude</el-button>
              <el-button size="small" @click="applyTemplate('deepseek')">DeepSeek</el-button>
            </div>

            <div class="form-row-adaptive">
              <div class="glass-form-item" style="flex: 1; min-width: 200px;">
                <label>模型类型</label>
                <el-select v-model="llmConfig.provider" size="large" style="width: 100%">
                  <el-option label="OpenAI 类型" value="openai" />
                  <el-option label="Claude 类型" value="claude" />
                </el-select>
              </div>

              <div class="glass-form-item" style="flex: 2; min-width: 250px;">
                <label>模型名称</label>
                <el-input
                  v-model="llmConfig.modelName"
                  placeholder="gpt-4o, claude-3-5-sonnet 等"
                  size="large"
                />
              </div>
            </div>

            <div class="glass-form-item">
              <label>API 服务器</label>
              <el-input
                v-model="llmConfig.baseUrl"
                placeholder="https://api.openai.com/v1"
                size="large"
              />
              <div class="form-hint">支持自定义代理地址</div>
            </div>

            <div class="glass-form-item">
              <label>API Key</label>
              <el-input
                v-model="llmConfig.apiKey"
                type="password"
                placeholder="sk-..."
                show-password
                size="large"
              />
              <div class="form-hint">密钥仅保存在本地浏览器，不会上传服务器</div>
            </div>

            <div class="glass-actions">
              <div class="llm-info-text">
                🔊 用于生成语音播报文案 (Edge-TTS)
              </div>

              <div style="display: flex; gap: 12px;">
                <el-button @click="testLLMConnection" :loading="llmTesting" class="btn-glass-action">
                  测试连接
                </el-button>
                <el-button type="primary" @click="saveLLMConfig" :loading="llmSaving" class="btn-glass-action">
                  保存配置
                </el-button>
              </div>
            </div>
          </div>
        </section>

        <!-- TTS 语音配置卡片 -->
        <section class="glass-settings-card">
          <div class="card-header-minimal">
            <div class="header-info">
              <h3 class="card-title">🔊 语音播报设置</h3>
              <p class="card-desc">配置 Edge-TTS 语音合成参数</p>
            </div>
          </div>

          <div class="glass-form">
            <div class="glass-form-item">
              <label>语音模型</label>
              <el-select v-model="ttsConfig.voice" size="large" style="width: 100%">
                <el-option label="云希 (男声 - 专业)" value="zh-CN-YunxiNeural" />
                <el-option label="晓晓 (女声 - 温柔)" value="zh-CN-XiaoxiaoNeural" />
                <el-option label="云扬 (男声 - 活力)" value="zh-CN-YunyangNeural" />
                <el-option label="晓伊 (女声 - 活泼)" value="zh-CN-XiaoyiNeural" />
                <el-option label="云健 (男声 - 稳重)" value="zh-CN-YunjianNeural" />
                <el-option label="晓梦 (女声 - 温暖)" value="zh-CN-XiaomengNeural" />
                <el-option label="云野 (男声 - 清晰)" value="zh-CN-YunyeNeural" />
                <el-option label="晓墨 (女声 - 知性)" value="zh-CN-XiaomoNeural" />
              </el-select>
              <div class="form-hint">选择播报语音的音色和风格</div>
            </div>

            <div class="form-row-adaptive">
              <div class="glass-form-item" style="flex: 1;">
                <label>语速调整 ({{ ttsConfig.rate }})</label>
                <el-slider
                  v-model="rateValue"
                  :min="-50"
                  :max="50"
                  :step="10"
                  :marks="{ '-50': '慢', '0': '正常', '50': '快' }"
                  @change="updateRate"
                />
              </div>

              <div class="glass-form-item" style="flex: 1;">
                <label>音量调整 ({{ ttsConfig.volume }})</label>
                <el-slider
                  v-model="volumeValue"
                  :min="-50"
                  :max="50"
                  :step="10"
                  :marks="{ '-50': '小', '0': '正常', '50': '大' }"
                  @change="updateVolume"
                />
              </div>
            </div>

            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">语音引擎</div>
                <div class="info-value">Microsoft Edge TTS</div>
              </div>
              <div class="info-item">
                <div class="info-label">当前语音</div>
                <div class="info-value">{{ getVoiceName(ttsConfig.voice) }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">工作流程</div>
                <div class="info-value">LLM 生成文案 → TTS 语音合成</div>
              </div>
            </div>

            <div class="glass-actions">
              <div style="display: flex; gap: 12px;">
                <el-button @click="testTTS" :loading="ttsTesting" class="btn-glass-action">
                  🎧 试听语音
                </el-button>
                <el-button type="primary" @click="saveTTSConfig" :loading="ttsSaving" class="btn-glass-action">
                  保存配置
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
.settings-page-wrapper {
  min-height: calc(100vh - 64px);
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

/* 75% 不透明度圆角矩形卡片 */
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
  display: flex;
  gap: 20px;
  align-items: center;
  margin-bottom: 32px;
}

.icon-circle {
  width: 48px;
  height: 48px;
  background: var(--text-primary);
  color: var(--color-bg-base);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 4px 0;
  color: var(--text-primary);
}

.card-desc {
  font-size: 0.9rem;
  color: var(--text-tertiary);
  margin: 0;
}

.glass-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-row-adaptive {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.glass-form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.glass-form-item label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  padding-left: 4px;
}

.protocol { width: 120px; }
.ip { flex: 1; min-width: 200px; }
.port { width: 100px; }

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

.btn-glass-action {
  border-radius: 12px !important;
  padding: 12px 28px !important;
  font-weight: 700 !important;
}

.placeholder-content-glass {
  color: var(--text-tertiary);
  font-style: italic;
  text-align: center;
  padding: 24px;
  border: 1px dashed var(--border-subtle);
  border-radius: 16px;
}

/* Element Plus Overrides for Glass effect */
:deep(.el-input__wrapper), :deep(.el-select .el-input__wrapper) {
  background-color: rgba(0, 0, 0, 0.02) !important;
  box-shadow: none !important;
  border: 1px solid transparent !important;
}

html.dark :deep(.el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.03) !important;
}

:deep(.el-input__wrapper.is-focus) {
  background-color: var(--color-surface) !important;
  border-color: var(--color-accent) !important;
  box-shadow: var(--shadow-glow) !important;
}

/* LLM Config Styles */
.template-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 12px;
  margin-bottom: 16px;
}

html.dark .template-buttons {
  background: rgba(255, 255, 255, 0.03);
}

.template-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-weight: 600;
}

.form-hint {
  font-size: 0.8rem;
  color: var(--text-tertiary);
  margin-top: 6px;
  padding-left: 4px;
}

.llm-info-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-weight: 600;
}

</style>
