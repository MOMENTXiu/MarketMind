<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UploadProps, UploadUserFile } from 'element-plus'
import { ArrowLeft, UploadFilled, Refresh, VideoPlay, Document, Warning, View } from '@element-plus/icons-vue'
import {
  createDataProcessingJob,
  getApiErrorMessage,
  getDataProcessingSidecar,
  getDataProcessingJob,
  isTerminalDataProcessingStatus,
  listDataProcessingOutputs,
  regularizeDataProcessingJob,
  runDataProcessingJob,
  uploadRawDataset,
  type ApiRef,
  type DataProcessingJob,
  type DataProcessingSidecarId
} from '../api'

const route = useRoute()
const router = useRouter()

const sidecarIds: DataProcessingSidecarId[] = [
  'sidecar:schema_mapping_detail',
  'sidecar:quality_report',
  'sidecar:capability',
  'sidecar:manifest',
  'sidecar:preview_rows'
]

const sidecarLabels: Record<DataProcessingSidecarId, string> = {
  'sidecar:schema_mapping_detail': 'Schema Mapping',
  'sidecar:quality_report': 'Quality Report',
  'sidecar:capability': 'Capability',
  'sidecar:manifest': 'Manifest',
  'sidecar:preview_rows': 'Preview Rows'
}

const createForm = ref({
  project_id: typeof route.query.project_id === 'string' ? route.query.project_id : 'demo-project',
  name: ''
})
const fileList = ref<UploadUserFile[]>([])
const job = ref<DataProcessingJob | null>(null)
const outputs = ref<ApiRef[]>([])
const emptySidecars = (): Record<DataProcessingSidecarId, Record<string, unknown> | null> => ({
  'sidecar:schema_mapping_detail': null,
  'sidecar:quality_report': null,
  'sidecar:capability': null,
  'sidecar:manifest': null,
  'sidecar:preview_rows': null
})
const sidecars = ref(emptySidecars())

const creating = ref(false)
const uploading = ref(false)
const regularizing = ref(false)
const running = ref(false)
const loadingJob = ref(false)
let pollingTimer: number | undefined

const routeJobId = computed(() => typeof route.params.jobId === 'string' ? route.params.jobId : '')
const routeProjectId = computed(() => typeof route.query.project_id === 'string' ? route.query.project_id : '')
const currentProjectId = computed(() => job.value?.project_id || routeProjectId.value || createForm.value.project_id.trim())
const datasetStage = computed(() => job.value?.stages.find(stage => stage.stage === 'dataset_regularization'))
const needsReview = computed(() => job.value?.status === 'needs_review' || datasetStage.value?.status === 'needs_review')
const isJobProcessing = computed(() => job.value?.status === 'processing')
const canRunAnalysis = computed(() => {
  return Boolean(job.value && datasetStage.value?.status === 'completed' && !needsReview.value && !isJobProcessing.value)
})
const qualityMetrics = computed(() => {
  const quality = job.value?.quality
  return [
    ['原始行数', quality?.raw_rows],
    ['标准化行数', quality?.normalized_rows],
    ['字段映射数', quality?.mapped_field_count],
    ['就绪分', quality?.analysis_ready_score],
    ['质量等级', quality?.grade]
  ]
})
const capabilityEntries = computed(() => {
  const capability = job.value?.capability || {}
  return Object.entries(capability)
    .filter(([key, value]) => key.startsWith('can_run_') && typeof value === 'boolean')
    .map(([key, value]) => ({ key, value }))
})
const sidecarCards = computed(() => sidecarIds.map(id => ({ id, label: sidecarLabels[id], payload: sidecars.value[id] })))

const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  if (!/\.(csv|xlsx|xls)$/i.test(file.name)) {
    ElMessage.error('Data Processing 支持 CSV、XLS、XLSX')
    return false
  }
  if (file.size / 1024 / 1024 > 100) {
    ElMessage.error('文件大小需小于 100MB')
    return false
  }
  return true
}

const handleFileChange: UploadProps['onChange'] = (_, files) => {
  fileList.value = files
}

const formatValue = (value: unknown) => {
  if (value === undefined || value === null || value === '') return '-'
  if (typeof value === 'number') return Number.isFinite(value) ? value.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '-'
  if (typeof value === 'boolean') return value ? '可运行' : '跳过'
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

const prettyJson = (payload: Record<string, unknown> | null) => {
  if (!payload) return '暂无数据'
  return JSON.stringify(payload, null, 2)
}

const statusLabel = (status: string | undefined | null) => {
  const map: Record<string, string> = {
    queued: '待处理',
    processing: '运行中',
    completed: '已完成',
    failed: '失败',
    needs_review: '需复核',
    skipped: '已跳过'
  }
  return status ? map[status] || status : '-'
}

const stopPolling = () => {
  if (pollingTimer !== undefined) {
    window.clearInterval(pollingTimer)
    pollingTimer = undefined
  }
}

const loadSidecars = async () => {
  if (!job.value) return
  const projectId = job.value.project_id
  const jobId = job.value.job_id
  await Promise.all(sidecarIds.map(async (sidecarId) => {
    try {
      sidecars.value[sidecarId] = await getDataProcessingSidecar(projectId, jobId, sidecarId)
    } catch {
      sidecars.value[sidecarId] = null
    }
  }))
}

const loadOutputs = async () => {
  if (!job.value) return
  outputs.value = job.value.output_refs || []
  try {
    const result = await listDataProcessingOutputs(job.value.project_id, job.value.job_id)
    outputs.value = result.outputs
  } catch {
    outputs.value = job.value.output_refs || []
  }
}

const loadJob = async (jobId: string, projectId: string, silent = false) => {
  if (!silent) loadingJob.value = true
  try {
    job.value = await getDataProcessingJob(projectId, jobId)
    createForm.value.project_id = job.value.project_id
    createForm.value.name = job.value.name
    await loadOutputs()
    await loadSidecars()
    if (isTerminalDataProcessingStatus(job.value.status) || job.value.status !== 'processing') {
      stopPolling()
    }
  } catch (error) {
    if (!silent) ElMessage.error(`加载 Job 失败: ${getApiErrorMessage(error)}`)
    stopPolling()
  } finally {
    if (!silent) loadingJob.value = false
  }
}

const pollJob = async () => {
  if (!job.value) return
  await loadJob(job.value.job_id, job.value.project_id, true)
}

const startPolling = () => {
  stopPolling()
  pollingTimer = window.setInterval(pollJob, 2500)
}

const createJob = async () => {
  const projectId = createForm.value.project_id.trim()
  const name = createForm.value.name.trim()
  if (!projectId || !name) {
    ElMessage.warning('请填写 project_id 和 job 名称')
    return
  }
  creating.value = true
  try {
    const created = await createDataProcessingJob({ project_id: projectId, name })
    job.value = created
    outputs.value = created.output_refs || []
    ElMessage.success('Job 已创建')
    await router.push({ path: `/data-processing/jobs/${created.job_id}`, query: { project_id: created.project_id } })
  } catch (error) {
    ElMessage.error(`创建失败: ${getApiErrorMessage(error)}`)
  } finally {
    creating.value = false
  }
}

const uploadDataset = async () => {
  if (!job.value) {
    ElMessage.warning('请先创建 Job')
    return
  }
  const rawFile = fileList.value[0]?.raw
  if (!(rawFile instanceof File)) {
    ElMessage.warning('请选择要上传的数据文件')
    return
  }
  uploading.value = true
  try {
    job.value = await uploadRawDataset(job.value.project_id, job.value.job_id, rawFile)
    outputs.value = job.value.output_refs || []
    ElMessage.success('原始数据已上传')
  } catch (error) {
    ElMessage.error(`上传失败: ${getApiErrorMessage(error)}`)
  } finally {
    uploading.value = false
  }
}

const regularizeJob = async () => {
  if (!job.value) return
  regularizing.value = true
  try {
    job.value = await regularizeDataProcessingJob(job.value.project_id, job.value.job_id)
    await loadOutputs()
    await loadSidecars()
    if (needsReview.value) {
      ElMessage.warning('标准化完成，但需要人工复核')
    } else {
      ElMessage.success('标准化完成')
    }
  } catch (error) {
    ElMessage.error(`标准化失败: ${getApiErrorMessage(error)}`)
  } finally {
    regularizing.value = false
  }
}

const runJob = async () => {
  if (!job.value) return
  running.value = true
  try {
    job.value = await runDataProcessingJob(job.value.project_id, job.value.job_id)
    ElMessage.success('通用分析已启动')
    startPolling()
  } catch (error) {
    ElMessage.error(`启动失败: ${getApiErrorMessage(error)}`)
  } finally {
    running.value = false
  }
}

const refreshJob = async () => {
  if (!job.value) return
  await loadJob(job.value.job_id, job.value.project_id)
}

watch([routeJobId, routeProjectId], async ([jobId, projectId]) => {
  if (!jobId) {
    stopPolling()
    job.value = null
    outputs.value = []
    sidecars.value = emptySidecars()
    return
  }
  if (!projectId) {
    ElMessage.warning('缺少 project_id，无法读取 Job')
    return
  }
  await loadJob(jobId, projectId)
}, { immediate: true })

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="data-processing-page">
    <div class="container-breath-fixed">
      <header class="dp-header">
        <button class="btn-back-round" @click="router.push('/projects')">
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <div>
          <h1 class="dp-title">Data Processing</h1>
          <p class="dp-subtitle">通用 CSV / Excel 标准化与分析链路</p>
        </div>
        <div class="dp-header-actions">
          <el-button :icon="Refresh" plain round :loading="loadingJob" :disabled="!job" @click="refreshJob">刷新</el-button>
        </div>
      </header>

      <main class="dp-layout">
        <section class="dp-panel workflow-panel">
          <div class="panel-heading">
            <span class="step-number">01</span>
            <div>
              <h2>创建 Job</h2>
              <p>project_id 会作为后端状态隔离键</p>
            </div>
          </div>

          <div class="form-grid">
            <label>
              <span>Project ID</span>
              <el-input v-model="createForm.project_id" placeholder="demo-project" :disabled="Boolean(job)" />
            </label>
            <label>
              <span>Job 名称</span>
              <el-input v-model="createForm.name" placeholder="order_4 E2E" :disabled="Boolean(job)" />
            </label>
          </div>

          <el-button type="primary" :loading="creating" :disabled="Boolean(job)" @click="createJob" class="wide-action">
            创建 Data Processing Job
          </el-button>

          <div class="panel-heading with-divider">
            <span class="step-number">02</span>
            <div>
              <h2>上传 Raw Dataset</h2>
              <p>支持 .csv / .xls / .xlsx</p>
            </div>
          </div>

          <el-upload
            :auto-upload="false"
            :limit="1"
            :before-upload="beforeUpload"
            :on-change="handleFileChange"
            accept=".csv,.xls,.xlsx"
            drag
            action="#"
            class="dp-upload"
          >
            <div class="upload-placeholder">
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">选择通用数据文件</div>
              <div class="upload-hint">CSV / Excel，最大 100MB</div>
            </div>
          </el-upload>

          <el-button :loading="uploading" :disabled="!job || fileList.length === 0" @click="uploadDataset" class="wide-action">
            上传数据
          </el-button>

          <div class="action-row">
            <el-button :icon="Document" :loading="regularizing" :disabled="!job" @click="regularizeJob">
              标准化
            </el-button>
            <el-button type="primary" :icon="VideoPlay" :loading="running || isJobProcessing" :disabled="!canRunAnalysis" @click="runJob">
              运行分析
            </el-button>
          </div>

          <el-alert
            v-if="needsReview"
            title="标准化需要复核"
            type="warning"
            :closable="false"
            show-icon
          >
            <template #default>
              查看 Schema Mapping、Quality Report 和 Capability 后再决定后续处理；当前后端未提供 approval endpoint，运行按钮会保持禁用。
            </template>
          </el-alert>
        </section>

        <section class="dp-panel status-panel" v-loading="loadingJob">
          <div class="status-topline">
            <div>
              <span class="eyebrow">CURRENT JOB</span>
              <h2>{{ job?.name || '尚未创建 Job' }}</h2>
              <p>{{ job?.job_id || '创建后将显示 job_id' }}</p>
            </div>
            <div class="status-badge" :class="job?.status || 'queued'">
              {{ statusLabel(job?.status) }}
            </div>
          </div>

          <div v-if="job" class="job-meta-grid">
            <div><span>Project</span><strong>{{ currentProjectId }}</strong></div>
            <div><span>Updated</span><strong>{{ job.updated_at || '-' }}</strong></div>
            <div><span>Error</span><strong>{{ job.error || '-' }}</strong></div>
          </div>

          <div v-if="job?.stages.length" class="stage-board">
            <div v-for="stage in job.stages" :key="stage.stage" class="stage-card" :class="stage.status">
              <span>{{ stage.stage }}</span>
              <strong>{{ statusLabel(stage.status) }}</strong>
              <small v-if="stage.error">{{ stage.error }}</small>
            </div>
          </div>

          <div v-if="job?.skipped_reasons && Object.keys(job.skipped_reasons).length" class="skipped-box">
            <div class="mini-title"><el-icon><Warning /></el-icon> Skipped Reasons</div>
            <div v-for="([stage, reason]) in Object.entries(job.skipped_reasons)" :key="stage" class="skip-row">
              <span>{{ stage }}</span><strong>{{ reason }}</strong>
            </div>
          </div>
        </section>
      </main>

      <section v-if="job" class="dp-results-grid">
        <div class="dp-panel compact-panel">
          <div class="mini-title">Quality</div>
          <div class="metric-list">
            <div v-for="([label, value]) in qualityMetrics" :key="label" class="metric-row">
              <span>{{ label }}</span>
              <strong>{{ formatValue(value) }}</strong>
            </div>
          </div>
        </div>

        <div class="dp-panel compact-panel">
          <div class="mini-title">Capability</div>
          <div class="capability-list">
            <div v-for="entry in capabilityEntries" :key="entry.key" class="capability-row" :class="{ disabled: !entry.value }">
              <span>{{ entry.key }}</span>
              <strong>{{ formatValue(entry.value) }}</strong>
            </div>
            <el-empty v-if="!capabilityEntries.length" description="暂无能力数据" :image-size="56" />
          </div>
        </div>

        <div class="dp-panel compact-panel outputs-panel">
          <div class="mini-title">Outputs</div>
          <div class="ref-list">
            <div v-for="ref in outputs" :key="ref.id" class="ref-card">
              <div>
                <span>{{ ref.type || ref.sidecar_type || 'ref' }}</span>
                <strong>{{ ref.name || ref.id }}</strong>
                <small>{{ ref.id }}</small>
              </div>
              <a v-if="ref.url" :href="ref.url" target="_blank" rel="noreferrer">
                <el-icon><View /></el-icon>
              </a>
            </div>
            <el-empty v-if="!outputs.length" description="暂无输出" :image-size="56" />
          </div>
        </div>
      </section>

      <section v-if="job" class="dp-panel sidecar-section">
        <div class="panel-heading">
          <span class="step-number">03</span>
          <div>
            <h2>Sidecars</h2>
            <p>关键复核与结果 JSON</p>
          </div>
        </div>

        <el-tabs class="sidecar-tabs">
          <el-tab-pane v-for="item in sidecarCards" :key="item.id" :label="item.label">
            <pre class="json-viewer">{{ prettyJson(item.payload) }}</pre>
          </el-tab-pane>
        </el-tabs>
      </section>
    </div>
  </div>
</template>

<style scoped>
.data-processing-page { min-height: 100vh; background: var(--color-bg-base); padding-bottom: 80px; }
.container-breath-fixed { max-width: 1200px; margin: 0 auto; padding: 0 24px; }
.dp-header { height: 110px; display: flex; align-items: center; gap: 18px; }
.btn-back-round { width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--border-subtle); background: var(--color-surface); color: var(--text-primary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.2s; }
.btn-back-round:hover { transform: translateX(-4px); }
.dp-title { margin: 0; color: var(--text-primary); font-size: 1.9rem; font-weight: 850; letter-spacing: 0; }
.dp-subtitle { margin: 4px 0 0 0; color: var(--text-tertiary); font-size: 0.92rem; }
.dp-header-actions { margin-left: auto; }
.dp-layout { display: grid; grid-template-columns: 420px 1fr; gap: 24px; align-items: start; }
.dp-panel { background: var(--color-surface); border: 1px solid var(--border-subtle); border-radius: 24px; box-shadow: var(--shadow-sm); padding: 24px; }
.workflow-panel { display: flex; flex-direction: column; gap: 18px; }
.panel-heading { display: flex; gap: 14px; align-items: center; }
.panel-heading.with-divider { padding-top: 20px; border-top: 1px solid var(--border-subtle); }
.panel-heading h2 { margin: 0; color: var(--text-primary); font-size: 1.05rem; font-weight: 850; }
.panel-heading p { margin: 3px 0 0 0; color: var(--text-tertiary); font-size: 0.8rem; }
.step-number { display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 12px; color: var(--color-accent); background: var(--color-accent-soft); font-weight: 850; font-size: 0.78rem; }
.form-grid { display: grid; gap: 14px; }
.form-grid label { display: flex; flex-direction: column; gap: 8px; font-size: 0.8rem; color: var(--text-secondary); font-weight: 700; }
.wide-action { width: 100%; height: 44px !important; border-radius: 14px !important; font-weight: 800 !important; }
.dp-upload { width: 100%; }
.upload-placeholder { padding: 18px 0; color: var(--text-secondary); }
.upload-icon { font-size: 2rem; color: var(--color-accent); margin-bottom: 8px; }
.upload-text { font-weight: 800; color: var(--text-primary); }
.upload-hint { margin-top: 4px; color: var(--text-tertiary); font-size: 0.8rem; }
.action-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.status-panel { min-height: 420px; }
.status-topline { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; margin-bottom: 22px; }
.eyebrow { color: var(--text-tertiary); font-size: 0.72rem; font-weight: 850; letter-spacing: 0; }
.status-topline h2 { margin: 6px 0 4px 0; font-size: 1.5rem; color: var(--text-primary); }
.status-topline p { margin: 0; color: var(--text-tertiary); font-size: 0.82rem; word-break: break-all; }
.status-badge { padding: 8px 12px; border-radius: 999px; background: var(--nav-pill-bg); color: var(--text-secondary); font-size: 0.8rem; font-weight: 850; white-space: nowrap; }
.status-badge.processing, .stage-card.processing { color: #f59e0b; }
.status-badge.completed, .stage-card.completed { color: #10b981; }
.status-badge.failed, .stage-card.failed { color: #ef4444; }
.status-badge.needs_review, .stage-card.needs_review { color: #d97706; }
.job-meta-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 22px; }
.job-meta-grid div { background: var(--color-bg-base); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 14px; min-width: 0; }
.job-meta-grid span { display: block; color: var(--text-tertiary); font-size: 0.72rem; font-weight: 750; margin-bottom: 6px; }
.job-meta-grid strong { color: var(--text-primary); font-size: 0.82rem; word-break: break-word; }
.stage-board { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
.stage-card { display: flex; flex-direction: column; gap: 5px; background: var(--color-bg-base); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 14px; color: var(--text-secondary); }
.stage-card span { color: var(--text-tertiary); font-size: 0.74rem; }
.stage-card strong { font-size: 0.9rem; }
.stage-card small { color: #ef4444; line-height: 1.4; }
.skipped-box { margin-top: 18px; padding: 16px; border-radius: 16px; background: var(--nav-pill-bg); }
.mini-title { display: flex; align-items: center; gap: 8px; color: var(--text-primary); font-weight: 850; margin-bottom: 14px; }
.skip-row { display: flex; justify-content: space-between; gap: 16px; color: var(--text-tertiary); font-size: 0.82rem; padding: 8px 0; }
.skip-row strong { color: var(--text-primary); text-align: right; }
.dp-results-grid { display: grid; grid-template-columns: 1fr 1fr 1.2fr; gap: 24px; margin-top: 24px; align-items: start; }
.compact-panel { min-height: 260px; }
.metric-list, .capability-list, .ref-list { display: flex; flex-direction: column; gap: 10px; }
.metric-row, .capability-row { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 10px 0; border-bottom: 1px solid var(--border-subtle); color: var(--text-tertiary); font-size: 0.84rem; }
.metric-row strong, .capability-row strong { color: var(--text-primary); }
.capability-row.disabled strong { color: #ef4444; }
.ref-card { display: flex; justify-content: space-between; gap: 12px; align-items: center; background: var(--color-bg-base); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 14px; }
.ref-card div { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.ref-card span { color: var(--color-accent); font-size: 0.72rem; font-weight: 850; }
.ref-card strong { color: var(--text-primary); font-size: 0.88rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ref-card small { color: var(--text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ref-card a { color: var(--color-accent); font-size: 1.1rem; }
.sidecar-section { margin-top: 24px; }
.sidecar-tabs { margin-top: 18px; }
.json-viewer { min-height: 320px; max-height: 520px; overflow: auto; margin: 0; padding: 18px; border-radius: 18px; background: var(--color-bg-base); color: var(--text-secondary); border: 1px solid var(--border-subtle); font-size: 0.78rem; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
@media (max-width: 980px) {
  .dp-layout, .dp-results-grid { grid-template-columns: 1fr; }
  .job-meta-grid { grid-template-columns: 1fr; }
}
</style>