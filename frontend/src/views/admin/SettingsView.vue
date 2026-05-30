<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  getSettings, testLlmConnection, testBarkAlert,
  getLlmConfigs, createLlmConfig, updateLlmConfig,
  deleteLlmConfig, activateLlmConfig, updateEnvSettings,
  type AllSettings, type TestResult,
  type LlmConfigItem, type LlmConfigSaveInput,
} from '@/api/admin'
import { Zap, Server, Bell, CheckCircle, XCircle, Loader2, Plus, Pencil, Trash2, Star } from 'lucide-vue-next'

// ── State ──
const settings = ref<AllSettings | null>(null)
const llmConfigs = ref<LlmConfigItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const activeTab = ref<'llm' | 'infra' | 'alert'>('llm')

const llmTesting = ref(false)
const llmTestResult = ref<TestResult | null>(null)
const barkTesting = ref(false)
const barkTestResult = ref<TestResult | null>(null)

// Form state
const showForm = ref(false)
const editingId = ref<string | null>(null)
const formName = ref('')
const formProvider = ref('openai')
const formBaseUrl = ref('')
const formApiKey = ref('')
const formModel = ref('')
const formTimeout = ref(30)
const formActive = ref(false)
const formSaving = ref(false)
const formError = ref<string | null>(null)

// Env edit
const envSaving = ref(false)
const envMessage = ref<string | null>(null)

const boolIcon = (v: boolean) => v ? CheckCircle : XCircle
const boolColor = (v: boolean) => v ? '#10B981' : '#EF4444'

async function fetchData() {
  loading.value = true; error.value = null
  try {
    const [s, c] = await Promise.all([getSettings(), getLlmConfigs()])
    settings.value = s
    llmConfigs.value = c || []
  } catch (e: any) { error.value = e?.message || '加载失败' }
  finally { loading.value = false }
}

// ── LLM Config CRUD ──
function openCreate() {
  editingId.value = null
  formName.value = ''; formProvider.value = 'openai'; formBaseUrl.value = ''
  formApiKey.value = ''; formModel.value = ''; formTimeout.value = 30
  formActive.value = false; formError.value = null
  showForm.value = true
}

function openEdit(config: LlmConfigItem) {
  editingId.value = config.id
  formName.value = config.name; formProvider.value = config.provider
  formBaseUrl.value = config.baseUrl || ''; formApiKey.value = ''
  formModel.value = config.model || ''; formTimeout.value = config.timeoutSeconds
  formActive.value = config.isActive; formError.value = null
  showForm.value = true
}

function closeForm() { showForm.value = false }

async function saveForm() {
  if (!formName.value.trim()) { formError.value = 'Name is required'; return }
  formSaving.value = true; formError.value = null
  const data: LlmConfigSaveInput = {
    name: formName.value.trim(), provider: formProvider.value,
    baseUrl: formBaseUrl.value || null,
    apiKey: formApiKey.value || null,
    model: formModel.value || null,
    timeoutSeconds: formTimeout.value, isActive: formActive.value,
  }
  try {
    if (editingId.value) {
      await updateLlmConfig(editingId.value, data)
    } else {
      await createLlmConfig(data)
    }
    showForm.value = false
    llmConfigs.value = await getLlmConfigs()
  } catch (e: any) { formError.value = e?.message || '保存失败' }
  finally { formSaving.value = false }
}

async function handleDelete(configId: string) {
  if (!confirm('确定要删除此模型配置吗？')) return
  try {
    await deleteLlmConfig(configId)
    llmConfigs.value = await getLlmConfigs()
  } catch (e: any) { alert(e?.message || '删除失败') }
}

async function handleActivate(configId: string) {
  try {
    await activateLlmConfig(configId)
    llmConfigs.value = await getLlmConfigs()
  } catch (e: any) { alert(e?.message || '激活失败') }
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

async function saveEnv() {
  envSaving.value = true; envMessage.value = null
  try {
    const result = await updateEnvSettings([
      { key: 'LLM_PROVIDER', value: formProvider.value },
      { key: 'LLM_BASE_URL', value: formBaseUrl.value || '' },
      { key: 'LLM_MODEL', value: formModel.value || '' },
      { key: 'LLM_TIMEOUT_SECONDS', value: String(formTimeout.value) },
      { key: 'LLM_API_KEY', value: formApiKey.value || null, isSensitive: true },
    ])
    envMessage.value = result.message
  } catch (e: any) { envMessage.value = e?.message || '保存失败' }
  finally { envSaving.value = false }
}

const providerLabel = (p: string) => ({ openai: 'OpenAI', anthropic: 'Anthropic', deepseek: 'DeepSeek', custom: 'Custom' })[p] || p
const activeConfig = computed(() => llmConfigs.value.find(c => c.isActive))

onMounted(fetchData)
</script>

<template>
  <div class="settings-view">
    <header class="page-header">
      <div>
        <h1 class="page-title">系统设置</h1>
        <p class="page-sub">管理外部服务接入与运行配置</p>
      </div>
    </header>

    <div v-if="loading" class="loading-state"><div class="spinner"></div></div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <template v-if="settings">
      <div class="tabs">
        <button class="tab" :class="{ active: activeTab === 'llm' }" @click="activeTab = 'llm'"><Zap class="w-3.5 h-3.5" />LLM 接入</button>
        <button class="tab" :class="{ active: activeTab === 'infra' }" @click="activeTab = 'infra'"><Server class="w-3.5 h-3.5" />基础设施</button>
        <button class="tab" :class="{ active: activeTab === 'alert' }" @click="activeTab = 'alert'"><Bell class="w-3.5 h-3.5" />Alert 通知</button>
      </div>

      <!-- ═══ LLM Tab ═══ -->
      <div v-if="activeTab === 'llm'" class="tab-content">
        <!-- Config list -->
        <section class="setting-card">
          <div class="card-header-row">
            <h3>模型配置 ({{ llmConfigs.length }})</h3>
            <button class="btn-action-sm" @click="openCreate"><Plus class="w-3.5 h-3.5" />新增模型</button>
          </div>

          <div v-if="llmConfigs.length === 0" class="empty-hint">暂无模型配置，点击「新增模型」开始</div>

          <div v-for="config in llmConfigs" :key="config.id" class="llm-card" :class="{ active: config.isActive }">
            <div class="llm-card-left">
              <div class="llm-card-name">
                {{ config.name }}
                <Star v-if="config.isActive" class="w-3 h-3 active-star" />
              </div>
              <div class="llm-card-meta">
                <span class="provider-tag">{{ providerLabel(config.provider) }}</span>
                <span class="meta-item">{{ config.model || 'No model' }}</span>
                <span class="meta-item">{{ config.timeoutSeconds }}s</span>
                <span class="meta-item">
                  <component :is="boolIcon(config.apiKeyConfigured)" class="w-3 h-3" :color="boolColor(config.apiKeyConfigured)" />
                  {{ config.apiKeyConfigured ? 'Key 已配置' : 'Key 未配置' }}
                </span>
              </div>
            </div>
            <div class="llm-card-actions">
              <button v-if="!config.isActive" class="action-btn promote" @click="handleActivate(config.id)" title="激活">激活</button>
              <span v-else class="active-badge">当前使用</span>
              <button class="action-btn edit" @click="openEdit(config)" title="编辑"><Pencil class="w-3.5 h-3.5" /></button>
              <button class="action-btn del" @click="handleDelete(config.id)" :disabled="llmConfigs.length <= 1" title="删除"><Trash2 class="w-3.5 h-3.5" /></button>
            </div>
          </div>

          <!-- Test -->
          <div class="test-row">
            <button class="btn-action" :disabled="llmTesting" @click="testLlm">
              <Loader2 v-if="llmTesting" class="w-3.5 h-3.5 animate-spin" />测试连接
            </button>
            <div v-if="llmTestResult" class="test-result" :class="llmTestResult.success ? 'success' : 'fail'">
              {{ llmTestResult.message }}
              <span v-if="llmTestResult.latencyMs != null">({{ llmTestResult.latencyMs }}ms)</span>
            </div>
          </div>
        </section>

        <!-- Runtime env settings -->
        <section v-if="activeConfig" class="setting-card">
          <h3>运行时环境变量 (LLM)</h3>
          <p class="card-desc">这些值写入 .env，重启后端后生效。</p>
          <div class="field-grid">
            <div class="field"><span class="field-label">Provider</span><span class="field-value">{{ activeConfig.provider }}</span></div>
            <div class="field"><span class="field-label">Base URL</span><span class="field-value mono">{{ activeConfig.baseUrl || '-' }}</span></div>
            <div class="field"><span class="field-label">Model</span><span class="field-value">{{ activeConfig.model || '-' }}</span></div>
            <div class="field"><span class="field-label">Timeout</span><span class="field-value">{{ activeConfig.timeoutSeconds }}s</span></div>
          </div>
          <button class="btn-action" :disabled="envSaving" @click="saveEnv">
            <Loader2 v-if="envSaving" class="w-3.5 h-3.5 animate-spin" />同步到 .env
          </button>
          <div v-if="envMessage" class="test-result" :class="envMessage.includes('失败') ? 'fail' : 'success'">{{ envMessage }}</div>
        </section>
      </div>

      <!-- ═══ Infra Tab ═══ -->
      <div v-if="activeTab === 'infra' && settings.infra" class="tab-content">
        <section v-if="settings.infra.postgres" class="setting-card">
          <h3>PostgreSQL</h3>
          <div class="field-grid">
            <div class="field"><span class="field-label">Host</span><span class="field-value mono">{{ settings.infra.postgres.host }}:{{ settings.infra.postgres.port }}</span></div>
            <div class="field"><span class="field-label">Database</span><span class="field-value">{{ settings.infra.postgres.database }}</span></div>
            <div class="field"><span class="field-label">Username</span><span class="field-value">{{ settings.infra.postgres.username }}</span></div>
            <div class="field"><span class="field-label">Password</span><span class="field-value"><component :is="boolIcon(settings.infra.postgres.passwordConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.infra.postgres.passwordConfigured)" /> 已配置</span></div>
          </div>
        </section>
        <section v-if="settings.infra.redis" class="setting-card">
          <h3>Redis</h3>
          <div class="field-grid">
            <div class="field"><span class="field-label">Host</span><span class="field-value mono">{{ settings.infra.redis.host }}:{{ settings.infra.redis.port }}</span></div>
            <div class="field"><span class="field-label">Password</span><span class="field-value"><component :is="boolIcon(settings.infra.redis.passwordConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.infra.redis.passwordConfigured)" /> {{ settings.infra.redis.passwordConfigured ? '已配置' : '未配置' }}</span></div>
          </div>
        </section>
        <section v-if="settings.infra.minio" class="setting-card">
          <h3>MinIO</h3>
          <div class="field-grid">
            <div class="field"><span class="field-label">Endpoint</span><span class="field-value mono">{{ settings.infra.minio.endpoint }}</span></div>
            <div class="field"><span class="field-label">Bucket</span><span class="field-value">{{ settings.infra.minio.bucket }}</span></div>
            <div class="field"><span class="field-label">Secure</span><span class="field-value"><component :is="boolIcon(settings.infra.minio.secure)" class="w-3.5 h-3.5" :color="boolColor(settings.infra.minio.secure)" /></span></div>
            <div class="field"><span class="field-label">Access Key</span><span class="field-value"><component :is="boolIcon(settings.infra.minio.accessKeyConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.infra.minio.accessKeyConfigured)" /> {{ settings.infra.minio.accessKeyConfigured ? '已配置' : '未配置' }}</span></div>
            <div class="field"><span class="field-label">Secret Key</span><span class="field-value"><component :is="boolIcon(settings.infra.minio.secretKeyConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.infra.minio.secretKeyConfigured)" /> {{ settings.infra.minio.secretKeyConfigured ? '已配置' : '未配置' }}</span></div>
          </div>
        </section>
      </div>

      <!-- ═══ Alert Tab ═══ -->
      <div v-if="activeTab === 'alert' && settings.alert" class="tab-content">
        <section class="setting-card">
          <h3>Bark 通知设置</h3>
          <div class="field-grid">
            <div class="field"><span class="field-label">状态</span><span class="field-value"><component :is="boolIcon(settings.alert.enabled)" class="w-3.5 h-3.5" :color="boolColor(settings.alert.enabled)" /> {{ settings.alert.enabled ? '已启用' : '未启用' }}</span></div>
            <div class="field"><span class="field-label">Server URL</span><span class="field-value mono">{{ settings.alert.serverUrl || '-' }}</span></div>
            <div class="field"><span class="field-label">Device Key</span><span class="field-value"><component :is="boolIcon(settings.alert.deviceKeyConfigured)" class="w-3.5 h-3.5" :color="boolColor(settings.alert.deviceKeyConfigured)" /> {{ settings.alert.deviceKeyConfigured ? '已配置' : '未配置' }}</span></div>
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

    <!-- ═══ Form Modal ═══ -->
    <div v-if="showForm" class="modal-overlay" @click.self="closeForm">
      <div class="modal">
        <h2 class="modal-title">{{ editingId ? '编辑模型' : '新增模型' }}</h2>
        <div class="form-body">
          <div class="field"><label>名称</label><input v-model="formName" placeholder="GPT-4o" class="form-input" /></div>
          <div class="field">
            <label>Provider</label>
            <select v-model="formProvider" class="form-input">
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="deepseek">DeepSeek</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div class="field"><label>Base URL</label><input v-model="formBaseUrl" placeholder="https://api.openai.com/v1" class="form-input mono" /></div>
          <div class="field"><label>API Key</label><input v-model="formApiKey" type="password" :placeholder="editingId ? '留空保留现有 Key' : 'sk-...'" class="form-input mono" /></div>
          <div class="field"><label>Model ID</label><input v-model="formModel" placeholder="gpt-4o" class="form-input mono" /></div>
          <div class="field"><label>Timeout (秒)</label><input v-model.number="formTimeout" type="number" min="1" max="300" class="form-input" /></div>
          <div class="field">
            <label class="checkbox-label">
              <input v-model="formActive" type="checkbox" />
              设为当前激活模型
            </label>
          </div>
          <div v-if="formError" class="form-error">{{ formError }}</div>
        </div>
        <div class="form-actions">
          <button class="btn-cancel" @click="closeForm">取消</button>
          <button class="btn-action" :disabled="formSaving" @click="saveForm">
            <Loader2 v-if="formSaving" class="w-3.5 h-3.5 animate-spin" />保存
          </button>
        </div>
      </div>
    </div>
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
.tab.active { color: #6366F1; background: rgba(99, 102, 241, 0.08); font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }

/* ─── cards ─── */
.setting-card {
  background: var(--color-surface); border: 1px solid var(--border-subtle);
  border-radius: 20px; padding: 24px 28px; margin-bottom: 18px;
  box-shadow: var(--shadow-xs);
}
.setting-card h3 { font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin: 0 0 16px; }
.card-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-header-row h3 { margin: 0; }
.card-desc { font-size: 0.82rem; color: var(--text-tertiary); margin: 0 0 14px; }
.empty-hint { text-align: center; padding: 20px; color: var(--text-tertiary); font-size: 0.85rem; }

.field-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field-label { font-size: 0.72rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; }
.field-value { font-size: 0.88rem; color: var(--text-secondary); font-weight: 500; display: flex; align-items: center; gap: 4px; }
.mono { font-family: 'SF Mono', monospace; font-size: 0.82rem; }
.level-tag { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.7rem; font-weight: 600; margin-right: 4px; background: rgba(148, 163, 184, 0.08); color: var(--text-tertiary); }

/* ─── LLM config cards ─── */
.llm-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-radius: 14px; border: 1px solid var(--border-subtle);
  margin-bottom: 8px; background: var(--color-surface-hover); gap: 14px;
  transition: border-color 0.15s;
}
.llm-card.active { border-color: rgba(99,102,241,0.3); background: rgba(99,102,241,0.03); }
.llm-card-left { flex: 1; min-width: 0; }
.llm-card-name { font-weight: 600; font-size: 0.9rem; color: var(--text-primary); display: flex; align-items: center; gap: 6px; }
.active-star { color: #6366F1; fill: #6366F1; }
.llm-card-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; flex-wrap: wrap; }
.provider-tag { padding: 1px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 600; background: rgba(99,102,241,0.07); color: #6366F1; }
.meta-item { font-size: 0.78rem; color: var(--text-tertiary); display: flex; align-items: center; gap: 3px; }
.llm-card-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.active-badge { font-size: 0.72rem; font-weight: 600; color: #059669; padding: 3px 10px; border-radius: 999px; background: rgba(16,185,129,0.06); white-space: nowrap; }

/* ─── buttons ─── */
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
.btn-action-sm {
  display: inline-flex; align-items: center; gap: 4px;
  height: 34px; padding: 0 14px; border-radius: 12px; border: 1px solid var(--border-subtle);
  background: var(--color-surface); color: var(--text-secondary); font-size: 0.8rem; font-weight: 500;
  cursor: pointer; transition: all 0.15s;
}
.btn-action-sm:hover { border-color: rgba(99,102,241,0.3); color: #6366F1; }
.action-btn {
  width: 30px; height: 30px; border-radius: 8px; display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border-subtle); background: transparent; color: var(--text-tertiary);
  cursor: pointer; transition: all 0.15s; font-size: 0.72rem; font-weight: 500;
}
.action-btn.promote { width: auto; padding: 0 10px; color: #6366F1; }
.action-btn.promote:hover { background: rgba(99,102,241,0.08); border-color: rgba(99,102,241,0.3); }
.action-btn.edit:hover { background: rgba(99,102,241,0.08); color: #6366F1; border-color: rgba(99,102,241,0.3); }
.action-btn.del:hover { background: rgba(239,68,68,0.06); color: #dc2626; border-color: rgba(239,68,68,0.15); }
.action-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.btn-cancel {
  height: 42px; padding: 0 20px; border-radius: 20px; border: 1px solid var(--border-subtle);
  background: transparent; color: var(--text-secondary); font-size: 0.85rem; font-weight: 500; cursor: pointer;
}

/* ─── test ─── */
.test-row { margin-top: 16px; }
.test-result { margin-top: 12px; padding: 10px 16px; border-radius: 12px; font-size: 0.85rem; font-weight: 500; }
.test-result.success { background: rgba(16, 185, 129, 0.06); color: #059669; border: 1px solid rgba(16, 185, 129, 0.12); }
.test-result.fail { background: rgba(239, 68, 68, 0.05); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.08); }

/* ─── modal ─── */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 300; display: flex; align-items: center; justify-content: center; }
.modal {
  background: var(--color-surface); border-radius: 24px; padding: 32px;
  width: 480px; max-width: 90vw; box-shadow: 0 24px 64px rgba(0,0,0,0.12);
}
.modal-title { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin: 0 0 24px; }
.form-body .field { margin-bottom: 14px; }
.form-body label { font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input {
  width: 100%; height: 42px; padding: 0 14px; border-radius: 12px; font-size: 0.85rem;
  border: 1px solid var(--border-subtle); background: var(--color-bg-base);
  color: var(--text-primary); outline: none; box-sizing: border-box;
  transition: border-color 0.15s;
}
.form-input:focus { border-color: rgba(99,102,241,0.4); box-shadow: 0 0 0 3px rgba(99,102,241,0.05); }
select.form-input { cursor: pointer; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 500 !important; }
.checkbox-label input { width: 16px; height: 16px; accent-color: #6366F1; }
.form-error { padding: 8px 12px; border-radius: 8px; background: rgba(239,68,68,0.06); color: #dc2626; font-size: 0.82rem; }
.form-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.animate-spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-state { display: flex; justify-content: center; padding: 60px 0; }
.spinner { width: 36px; height: 36px; border: 3px solid var(--border-subtle); border-radius: 50%; border-top-color: #6366F1; animation: spin 0.8s linear infinite; }
.error-state { text-align: center; padding: 60px 0; color: #EF4444; font-size: 0.9rem; }
</style>
