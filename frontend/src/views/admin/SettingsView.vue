<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getSettings, testLlmConnection, testBarkAlert, type AllSettings, type TestResult } from '@/api/admin'
import { Zap, Server, Bell, CheckCircle, XCircle, Loader2 } from 'lucide-vue-next'

const settings = ref<AllSettings | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const activeTab = ref<'llm' | 'infra' | 'alert'>('llm')

const llmTesting = ref(false)
const llmTestResult = ref<TestResult | null>(null)

const barkTesting = ref(false)
const barkTestResult = ref<TestResult | null>(null)

async function fetchSettings() {
  try {
    settings.value = await getSettings()
    error.value = null
  } catch (e: any) {
    error.value = e?.message || '获取设置失败'
  } finally {
    loading.value = false
  }
}

async function testLlm() {
  llmTesting.value = true
  llmTestResult.value = null
  try {
    llmTestResult.value = await testLlmConnection()
  } catch (e: any) {
    llmTestResult.value = { success: false, message: e?.message || '测试失败' }
  } finally {
    llmTesting.value = false
  }
}

async function testBark() {
  barkTesting.value = true
  barkTestResult.value = null
  try {
    barkTestResult.value = await testBarkAlert()
  } catch (e: any) {
    barkTestResult.value = { success: false, message: e?.message || '测试失败' }
  } finally {
    barkTesting.value = false
  }
}

onMounted(fetchSettings)

function boolIcon(v: boolean) {
  return v ? CheckCircle : XCircle
}

function boolColor(v: boolean) {
  return v ? '#10B981' : '#EF4444'
}
</script>

<template>
  <div class="settings-view">
    <h1 class="page-title">系统设置</h1>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <template v-if="settings">
      <!-- Tab Navigation -->
      <div class="tabs">
        <button class="tab" :class="{ active: activeTab === 'llm' }" @click="activeTab = 'llm'">
          <Zap :size="16" /> LLM 接入
        </button>
        <button class="tab" :class="{ active: activeTab === 'infra' }" @click="activeTab = 'infra'">
          <Server :size="16" /> 基础设施
        </button>
        <button class="tab" :class="{ active: activeTab === 'alert' }" @click="activeTab = 'alert'">
          <Bell :size="16" /> Alert 通知
        </button>
      </div>

      <!-- LLM Tab -->
      <div v-if="activeTab === 'llm' && settings.llm" class="tab-content">
        <div class="setting-card">
          <h3>LLM 接入设置</h3>
          <div class="field-grid">
            <div class="field">
              <span class="field-label">Provider</span>
              <span class="field-value">{{ settings.llm.provider || '未配置' }}</span>
            </div>
            <div class="field">
              <span class="field-label">Base URL</span>
              <span class="field-value mono">{{ settings.llm.baseUrl || '-' }}</span>
            </div>
            <div class="field">
              <span class="field-label">Model</span>
              <span class="field-value">{{ settings.llm.model || '-' }}</span>
            </div>
            <div class="field">
              <span class="field-label">API Key</span>
              <span class="field-value">
                <component :is="boolIcon(settings.llm.apiKeyConfigured)" :size="14" :color="boolColor(settings.llm.apiKeyConfigured)" />
                {{ settings.llm.apiKeyConfigured ? '已配置' : '未配置' }}
              </span>
            </div>
            <div class="field">
              <span class="field-label">Timeout</span>
              <span class="field-value">{{ settings.llm.timeoutSeconds || '-' }}s</span>
            </div>
            <div class="field">
              <span class="field-label">状态</span>
              <span class="field-value">
                <component :is="boolIcon(settings.llm.enabled)" :size="14" :color="boolColor(settings.llm.enabled)" />
                {{ settings.llm.enabled ? '已启用' : '未启用' }}
              </span>
            </div>
          </div>
          <button class="test-btn" :disabled="llmTesting" @click="testLlm">
            <Loader2 v-if="llmTesting" :size="14" class="spin" />
            测试连接
          </button>
          <div v-if="llmTestResult" class="test-result" :class="{ success: llmTestResult.success, fail: !llmTestResult.success }">
            {{ llmTestResult.message }}
            <span v-if="llmTestResult.latencyMs != null"> ({{ llmTestResult.latencyMs }}ms)</span>
          </div>
        </div>
      </div>

      <!-- Infra Tab -->
      <div v-if="activeTab === 'infra' && settings.infra" class="tab-content">
        <!-- PostgreSQL -->
        <div v-if="settings.infra.postgres" class="setting-card">
          <h3>PostgreSQL</h3>
          <div class="field-grid">
            <div class="field">
              <span class="field-label">Host</span>
              <span class="field-value mono">{{ settings.infra.postgres.host }}:{{ settings.infra.postgres.port }}</span>
            </div>
            <div class="field">
              <span class="field-label">Database</span>
              <span class="field-value">{{ settings.infra.postgres.database }}</span>
            </div>
            <div class="field">
              <span class="field-label">Username</span>
              <span class="field-value">{{ settings.infra.postgres.username }}</span>
            </div>
            <div class="field">
              <span class="field-label">Password</span>
              <span class="field-value">
                <component :is="boolIcon(settings.infra.postgres.passwordConfigured)" :size="14" :color="boolColor(settings.infra.postgres.passwordConfigured)" />
                已配置
              </span>
            </div>
          </div>
        </div>

        <!-- Redis -->
        <div v-if="settings.infra.redis" class="setting-card">
          <h3>Redis</h3>
          <div class="field-grid">
            <div class="field">
              <span class="field-label">Host</span>
              <span class="field-value mono">{{ settings.infra.redis.host }}:{{ settings.infra.redis.port }}</span>
            </div>
            <div class="field">
              <span class="field-label">Password</span>
              <span class="field-value">
                <component :is="boolIcon(settings.infra.redis.passwordConfigured)" :size="14" :color="boolColor(settings.infra.redis.passwordConfigured)" />
                {{ settings.infra.redis.passwordConfigured ? '已配置' : '未配置' }}
              </span>
            </div>
          </div>
        </div>

        <!-- MinIO -->
        <div v-if="settings.infra.minio" class="setting-card">
          <h3>MinIO</h3>
          <div class="field-grid">
            <div class="field">
              <span class="field-label">Endpoint</span>
              <span class="field-value mono">{{ settings.infra.minio.endpoint }}</span>
            </div>
            <div class="field">
              <span class="field-label">Bucket</span>
              <span class="field-value">{{ settings.infra.minio.bucket }}</span>
            </div>
            <div class="field">
              <span class="field-label">Secure</span>
              <span class="field-value">
                <component :is="boolIcon(settings.infra.minio.secure)" :size="14" :color="boolColor(settings.infra.minio.secure)" />
              </span>
            </div>
            <div class="field">
              <span class="field-label">Access Key</span>
              <span class="field-value">
                <component :is="boolIcon(settings.infra.minio.accessKeyConfigured)" :size="14" :color="boolColor(settings.infra.minio.accessKeyConfigured)" />
                {{ settings.infra.minio.accessKeyConfigured ? '已配置' : '未配置' }}
              </span>
            </div>
            <div class="field">
              <span class="field-label">Secret Key</span>
              <span class="field-value">
                <component :is="boolIcon(settings.infra.minio.secretKeyConfigured)" :size="14" :color="boolColor(settings.infra.minio.secretKeyConfigured)" />
                {{ settings.infra.minio.secretKeyConfigured ? '已配置' : '未配置' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Alert Tab -->
      <div v-if="activeTab === 'alert' && settings.alert" class="tab-content">
        <div class="setting-card">
          <h3>Bark 通知设置</h3>
          <div class="field-grid">
            <div class="field">
              <span class="field-label">状态</span>
              <span class="field-value">
                <component :is="boolIcon(settings.alert.enabled)" :size="14" :color="boolColor(settings.alert.enabled)" />
                {{ settings.alert.enabled ? '已启用' : '未启用' }}
              </span>
            </div>
            <div class="field">
              <span class="field-label">Server URL</span>
              <span class="field-value mono">{{ settings.alert.serverUrl || '-' }}</span>
            </div>
            <div class="field">
              <span class="field-label">Device Key</span>
              <span class="field-value">
                <component :is="boolIcon(settings.alert.deviceKeyConfigured)" :size="14" :color="boolColor(settings.alert.deviceKeyConfigured)" />
                {{ settings.alert.deviceKeyConfigured ? '已配置' : '未配置' }}
              </span>
            </div>
            <div class="field">
              <span class="field-label">Default Group</span>
              <span class="field-value">{{ settings.alert.defaultGroup || '-' }}</span>
            </div>
            <div class="field">
              <span class="field-label">Alert Levels</span>
              <span class="field-value">{{ settings.alert.alertLevels.join(', ') }}</span>
            </div>
          </div>
          <button class="test-btn" :disabled="barkTesting || !settings.alert.enabled" @click="testBark">
            <Loader2 v-if="barkTesting" :size="14" class="spin" />
            发送测试通知
          </button>
          <div v-if="barkTestResult" class="test-result" :class="{ success: barkTestResult.success, fail: !barkTestResult.success }">
            {{ barkTestResult.message }}
            <span v-if="barkTestResult.latencyMs != null"> ({{ barkTestResult.latencyMs }}ms)</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 24px;
}

html.dark .page-title { color: #f1f5f9; }

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  padding: 4px;
  background: rgba(15, 23, 42, 0.04);
  border-radius: 12px;
  width: fit-content;
}

html.dark .tabs { background: rgba(255, 255, 255, 0.04); }

.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 500;
  color: #64748b;
  background: none;
  border: none;
  cursor: pointer;
  transition: all 160ms ease;
}

.tab:hover { color: #111827; }
html.dark .tab:hover { color: #f1f5f9; }

.tab.active {
  color: #4f46e5;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  font-weight: 600;
}

html.dark .tab.active {
  background: #2a2a30;
  color: #818cf8;
}

.setting-card {
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 16px;
}

html.dark .setting-card {
  background: #1a1a20;
  border-color: rgba(255, 255, 255, 0.06);
}

.setting-card h3 {
  font-size: 0.95rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 14px;
}

html.dark .setting-card h3 { color: #f1f5f9; }

.field-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 0.72rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.field-value {
  font-size: 0.88rem;
  color: #475569;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

html.dark .field-value { color: #cbd5e1; }

.mono { font-family: monospace; font-size: 0.82rem; }

.test-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  padding: 8px 18px;
  border-radius: 8px;
  background: #6366f1;
  color: #fff;
  border: none;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 160ms ease;
}

.test-btn:hover:not(:disabled) { background: #4f46e5; }
.test-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.test-result {
  margin-top: 10px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 500;
}

.test-result.success {
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
}

.test-result.fail {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.loading-state, .error-state {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
}

.error-state { color: #EF4444; }
</style>
