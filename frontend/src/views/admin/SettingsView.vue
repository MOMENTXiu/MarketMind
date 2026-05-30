<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getSettings, testLlmConnection, testBarkAlert,
  type AllSettings, type TestResult,
} from '@/api/admin'
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
  llmTesting.value = true; llmTestResult.value = null
  try { llmTestResult.value = await testLlmConnection() }
  catch (e: any) { llmTestResult.value = { success: false, message: e?.message || '测试失败' } }
  finally { llmTesting.value = false }
}

async function testBark() {
  barkTesting.value = true; barkTestResult.value = null
  try { barkTestResult.value = await testBarkAlert() }
  catch (e: any) { barkTestResult.value = { success: false, message: e?.message || '测试失败' } }
  finally { barkTesting.value = false }
}

onMounted(fetchSettings)

const BoolIcon = (v: boolean) => v ? CheckCircle : XCircle
const boolColor = (v: boolean) => v ? '#10B981' : '#EF4444'
</script>

<template>
  <div class="settings-view">
    <header class="page-header">
      <div>
        <h1 class="page-title">系统设置</h1>
        <p class="page-sub">查看当前系统接入的外部服务与关键配置</p>
      </div>
    </header>

    <div v-if="loading" class="loading-state"><div class="spinner"></div></div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <template v-if="settings">
      <!-- Tabs -->
      <div class="tabs">
        <button class="tab" :class="{ active: activeTab === 'llm' }" @click="activeTab = 'llm'">
          <Zap class="w-3.5 h-3.5" />LLM 接入
        </button>
        <button class="tab" :class="{ active: activeTab === 'infra' }" @click="activeTab = 'infra'">
          <Server class="w-3.5 h-3.5" />基础设施
        </button>
        <button class="tab" :class="{ active: activeTab === 'alert' }" @click="activeTab = 'alert'">
          <Bell class="w-3.5 h-3.5" />Alert 通知
        </button>
      </div>

      <!-- LLM -->
      <div v-if="activeTab === 'llm' && settings.llm" class="tab-content">
        <section class="setting-card">
          <h3>LLM 接入设置</h3>
          <div class="field-grid">
            <div class="field"><span class="field-label">Provider</span><span class="field-value">{{ settings.llm.provider || '未配置' }}</span></div>
            <div class="field"><span class="field-label">Base URL</span><span class="field-value mono">{{ settings.llm.baseUrl || '-' }}</span></div>
            <div class="field"><span class="field-label">Model</span><span class="field-value">{{ settings.llm.model || '-' }}</span></div>
            <div class="field">
              <span class="field-label">API Key</span>
              <span class="field-value">
                <component :is="BoolIcon(settings.llm.apiKeyConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.llm.apiKeyConfigured)" />
                {{ settings.llm.apiKeyConfigured ? '已配置' : '未配置' }}
              </span>
            </div>
            <div class="field"><span class="field-label">Timeout</span><span class="field-value">{{ settings.llm.timeoutSeconds || '-' }}s</span></div>
            <div class="field">
              <span class="field-label">状态</span>
              <span class="field-value">
                <component :is="BoolIcon(settings.llm.enabled)" class="w-3.5 h-3.5" :color="boolColor(settings.llm.enabled)" />
                {{ settings.llm.enabled ? '已启用' : '未启用' }}
              </span>
            </div>
          </div>
          <button class="btn-action" :disabled="llmTesting" @click="testLlm">
            <Loader2 v-if="llmTesting" class="w-3.5 h-3.5 animate-spin" />测试连接
          </button>
          <div v-if="llmTestResult" class="test-result" :class="llmTestResult.success ? 'success' : 'fail'">
            {{ llmTestResult.message }}
            <span v-if="llmTestResult.latencyMs != null">({{ llmTestResult.latencyMs }}ms)</span>
          </div>
        </section>
      </div>

      <!-- Infra -->
      <div v-if="activeTab === 'infra' && settings.infra" class="tab-content">
        <section v-if="settings.infra.postgres" class="setting-card">
          <h3>PostgreSQL</h3>
          <div class="field-grid">
            <div class="field"><span class="field-label">Host</span><span class="field-value mono">{{ settings.infra.postgres.host }}:{{ settings.infra.postgres.port }}</span></div>
            <div class="field"><span class="field-label">Database</span><span class="field-value">{{ settings.infra.postgres.database }}</span></div>
            <div class="field"><span class="field-label">Username</span><span class="field-value">{{ settings.infra.postgres.username }}</span></div>
            <div class="field">
              <span class="field-label">Password</span>
              <span class="field-value"><component :is="BoolIcon(settings.infra.postgres.passwordConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.infra.postgres.passwordConfigured)" /> 已配置</span>
            </div>
          </div>
        </section>
        <section v-if="settings.infra.redis" class="setting-card">
          <h3>Redis</h3>
          <div class="field-grid">
            <div class="field"><span class="field-label">Host</span><span class="field-value mono">{{ settings.infra.redis.host }}:{{ settings.infra.redis.port }}</span></div>
            <div class="field">
              <span class="field-label">Password</span>
              <span class="field-value"><component :is="BoolIcon(settings.infra.redis.passwordConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.infra.redis.passwordConfigured)" /> {{ settings.infra.redis.passwordConfigured ? '已配置' : '未配置' }}</span>
            </div>
          </div>
        </section>
        <section v-if="settings.infra.minio" class="setting-card">
          <h3>MinIO</h3>
          <div class="field-grid">
            <div class="field"><span class="field-label">Endpoint</span><span class="field-value mono">{{ settings.infra.minio.endpoint }}</span></div>
            <div class="field"><span class="field-label">Bucket</span><span class="field-value">{{ settings.infra.minio.bucket }}</span></div>
            <div class="field"><span class="field-label">Secure</span><span class="field-value"><component :is="BoolIcon(settings.infra.minio.secure)" class="w-3.5 h-3.5" :color="boolColor(settings.infra.minio.secure)" /></span></div>
            <div class="field"><span class="field-label">Access Key</span><span class="field-value"><component :is="BoolIcon(settings.infra.minio.accessKeyConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.infra.minio.accessKeyConfigured)" /> {{ settings.infra.minio.accessKeyConfigured ? '已配置' : '未配置' }}</span></div>
            <div class="field"><span class="field-label">Secret Key</span><span class="field-value"><component :is="BoolIcon(settings.infra.minio.secretKeyConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.infra.minio.secretKeyConfigured)" /> {{ settings.infra.minio.secretKeyConfigured ? '已配置' : '未配置' }}</span></div>
          </div>
        </section>
      </div>

      <!-- Alert -->
      <div v-if="activeTab === 'alert' && settings.alert" class="tab-content">
        <section class="setting-card">
          <h3>Bark 通知设置</h3>
          <div class="field-grid">
            <div class="field"><span class="field-label">状态</span><span class="field-value"><component :is="BoolIcon(settings.alert.enabled)" class="w-3.5 h-3.5" :color="boolColor(settings.alert.enabled)" /> {{ settings.alert.enabled ? '已启用' : '未启用' }}</span></div>
            <div class="field"><span class="field-label">Server URL</span><span class="field-value mono">{{ settings.alert.serverUrl || '-' }}</span></div>
            <div class="field"><span class="field-label">Device Key</span><span class="field-value"><component :is="BoolIcon(settings.alert.deviceKeyConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.alert.deviceKeyConfigured)" /> {{ settings.alert.deviceKeyConfigured ? '已配置' : '未配置' }}</span></div>
            <div class="field"><span class="field-label">Default Group</span><span class="field-value">{{ settings.alert.defaultGroup || '-' }}</span></div>
            <div class="field"><span class="field-label">Alert Levels</span><span class="field-value"><span v-for="lvl in settings.alert.alertLevels" :key="lvl" class="level-tag">{{ lvl }}</span></span></div>
          </div>
          <button class="btn-action" :disabled="barkTesting || !settings.alert.enabled" @click="testBark">
            <Loader2 v-if="barkTesting" class="w-3.5 h-3.5 animate-spin" />发送测试通知
          </button>
          <div v-if="barkTestResult" class="test-result" :class="barkTestResult.success ? 'success' : 'fail'">
            {{ barkTestResult.message }}
            <span v-if="barkTestResult.latencyMs != null">({{ barkTestResult.latencyMs }}ms)</span>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-header { margin-bottom: 32px; }
.page-title { font-size: 1.75rem; font-weight: 800; color: var(--text-primary); margin: 0 0 4px 0; letter-spacing: -0.02em; }
.page-sub { font-size: 0.9rem; color: var(--text-tertiary); margin: 0; }

/* ─── tabs ─── */
.tabs { display: flex; gap: 4px; margin-bottom: 24px; }
.tab {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 10px 20px; border-radius: 14px; border: none;
  font-size: 0.85rem; font-weight: 500; color: var(--text-secondary);
  background: transparent; cursor: pointer; transition: all 0.2s ease;
}
.tab:hover { color: var(--text-primary); background: var(--color-surface-hover); }
.tab.active {
  color: #6366F1; background: rgba(99, 102, 241, 0.08);
  font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* ─── cards ─── */
.setting-card {
  background: var(--color-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 20px; padding: 24px 28px; margin-bottom: 18px;
  box-shadow: var(--shadow-xs);
}
.setting-card h3 { font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin: 0 0 16px; }

.field-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field-label { font-size: 0.72rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; }
.field-value { font-size: 0.88rem; color: var(--text-secondary); font-weight: 500; display: flex; align-items: center; gap: 4px; }
.mono { font-family: 'SF Mono', monospace; font-size: 0.82rem; }
.level-tag {
  display: inline-block; padding: 2px 8px; border-radius: 999px;
  font-size: 0.7rem; font-weight: 600; margin-right: 4px;
  background: rgba(148, 163, 184, 0.08); color: var(--text-tertiary);
}

/* ─── button ─── */
.btn-action {
  display: inline-flex; align-items: center; gap: 8px; margin-top: 18px;
  height: 42px; padding: 0 20px; border-radius: 20px; border: none;
  background: #6366F1; color: #fff;
  font-size: 0.85rem; font-weight: 600;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.18);
  cursor: pointer; transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
}
.btn-action:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 12px 28px rgba(99, 102, 241, 0.24); }
.btn-action:disabled { opacity: 0.45; cursor: not-allowed; }

/* ─── test result ─── */
.test-result { margin-top: 12px; padding: 10px 16px; border-radius: 12px; font-size: 0.85rem; font-weight: 500; }
.test-result.success { background: rgba(16, 185, 129, 0.06); color: #059669; border: 1px solid rgba(16, 185, 129, 0.12); }
.test-result.fail { background: rgba(239, 68, 68, 0.05); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.08); }

.animate-spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-state { display: flex; justify-content: center; padding: 60px 0; }
.spinner { width: 36px; height: 36px; border: 3px solid var(--border-subtle); border-radius: 50%; border-top-color: #6366F1; animation: spin 0.8s linear infinite; }
.error-state { text-align: center; padding: 60px 0; color: #EF4444; font-size: 0.9rem; }
</style>
