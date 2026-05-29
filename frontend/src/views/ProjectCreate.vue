<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UploadInstance, UploadProps, UploadUserFile } from 'element-plus'
import {
  Upload,
  ArrowLeft,
  FileSpreadsheet,
  Check,
  Sparkles,
  FileCheck,
  ChevronRight,
  AlertCircle,
} from 'lucide-vue-next'
import {
  createRetailProject,
  getApiErrorMessage,
  uploadRetailDataset,
  regularizeProjectDataset,
  runRetailAnalysis,
} from '../api'

const router = useRouter()
const currentStep = ref(0)

const projectForm = ref({
  name: '',
  description: '',
})

const uploadRef = ref<UploadInstance>()
const fileList = ref<UploadUserFile[]>([])
const uploading = ref(false)
const statusMessage = ref('')
const isDragOver = ref(false)

const steps = [
  {
    title: '基本信息',
    desc: 'Project Details',
    icon: Sparkles,
  },
  {
    title: '数据上传',
    desc: 'Upload Dataset',
    icon: Upload,
  },
  {
    title: '确认分析',
    desc: 'Confirmation',
    icon: FileCheck,
  },
]

const nextStep = () => {
  if (currentStep.value === 0 && !projectForm.value.name) {
    return ElMessage.warning('请输入项目名称')
  }
  if (currentStep.value === 1 && fileList.value.length === 0) {
    return ElMessage.warning('请上传数据集文件')
  }
  currentStep.value++
}

const prevStep = () => {
  if (currentStep.value > 0) currentStep.value--
}

const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  if (!/\.(csv|xls|xlsx)$/i.test(file.name)) {
    ElMessage.error('仅支持 CSV、XLS、XLSX 文件')
    return false
  }
  if (file.size / 1024 / 1024 > 100) {
    ElMessage.error('文件大小需小于 100MB')
    return false
  }
  return false // prevent auto-upload; we handle it manually
}

const handleFileChange: UploadProps['onChange'] = (_, files) => {
  fileList.value = files
}

const handleDragOver = () => {
  isDragOver.value = true
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const fileSizeText = computed(() => {
  const file = fileList.value[0]?.raw
  if (!file) return ''
  const mb = file.size / 1024 / 1024
  return mb >= 1 ? `${mb.toFixed(2)} MB` : `${(file.size / 1024).toFixed(1)} KB`
})

const removeFile = () => {
  fileList.value = []
  uploadRef.value?.clearFiles()
}

const createProject = async () => {
  if (fileList.value.length === 0) return ElMessage.warning('请上传数据集')
  uploading.value = true
  statusMessage.value = '正在创建项目...'
  try {
    const project = await createRetailProject({
      name: projectForm.value.name,
      description: projectForm.value.description,
      analysis_kind: 'data_processing',
    })

    if (project.analysis_kind !== 'data_processing') {
      throw new Error('项目类型创建异常，请刷新页面后重试')
    }

    statusMessage.value = '正在上传数据...'
    const rawFile = fileList.value[0]?.raw
    if (!(rawFile instanceof File)) {
      throw new Error('无法读取上传文件')
    }

    await uploadRetailDataset(project.id, rawFile)

    statusMessage.value = '正在数据标准化...'
    const regularized = await regularizeProjectDataset(project.id)

    if (regularized.status === 'needs_review') {
      ElMessage.warning('数据标准化需要审查，请查看详情')
      await router.push({ path: `/projects/${project.id}` })
      return
    }

    if (regularized.status === 'failed') {
      ElMessage.error(`数据标准化失败: ${regularized.error || '未知错误'}`)
      await router.push({ path: `/projects/${project.id}` })
      return
    }

    statusMessage.value = '正在启动分析...'
    await runRetailAnalysis(project.id)
    ElMessage.success('项目已创建，开始分析')
    await router.push({ path: `/projects/${project.id}`, query: { poll: '1' } })
  } catch (error) {
    const message = getApiErrorMessage(error)
    if (message.includes('Retail V2 raw sales dataset missing columns')) {
      ElMessage.error(
        '项目类型不匹配：系统仍按旧版 Retail V2 处理。请尝试清除浏览器缓存后刷新页面，或重新创建项目。',
      )
    } else {
      ElMessage.error(`创建失败: ${message}`)
    }
  } finally {
    uploading.value = false
    statusMessage.value = ''
  }
}
</script>

<template>
  <div class="create-page">
    <!-- Header -->
    <div class="page-header">
      <button class="back-btn" @click="router.push('/projects')">
        <ArrowLeft :size="18" />
      </button>
      <h1 class="page-title">新建项目</h1>
    </div>

    <!-- Card -->
    <div class="create-card">
      <!-- Stepper -->
      <div class="stepper">
        <div
          v-for="(step, idx) in steps"
          :key="idx"
          class="step"
          :class="{ active: currentStep === idx, completed: currentStep > idx }"
        >
          <div class="step-body">
            <div class="step-badge">
              <span v-if="currentStep > idx"><Check :size="16" /></span>
              <component v-else :is="step.icon" :size="18" />
            </div>
            <div class="step-text">
              <span class="step-title">{{ step.title }}</span>
              <span class="step-desc">{{ step.desc }}</span>
            </div>
          </div>
          <div v-if="idx < steps.length - 1" class="step-connector">
            <div class="step-track">
              <div class="step-fill" :style="{ width: currentStep > idx ? '100%' : '0%' }" />
            </div>
          </div>
        </div>
      </div>

      <!-- Content -->
      <div class="card-body">
        <!-- Step 1: Basic Info -->
        <transition name="slide-step" mode="out-in">
          <div v-if="currentStep === 0" class="step-content" key="step1">
            <div class="field-group">
              <label class="field-label">
                项目名称
                <span class="required">*</span>
              </label>
              <el-input
                v-model="projectForm.name"
                placeholder="例如：2024 Q1 销售分析"
                size="large"
                clearable
                :prefix-icon="Sparkles"
              />
              <p class="field-hint">给你的分析项目起一个好记的名字</p>
            </div>

            <div class="field-group">
              <label class="field-label">
                项目描述
                <span class="optional">可选</span>
              </label>
              <el-input
                v-model="projectForm.description"
                type="textarea"
                :rows="4"
                placeholder="简要描述本次分析的目标，便于日后回顾..."
                resize="none"
              />
            </div>
          </div>

          <!-- Step 2: Upload -->
          <div v-else-if="currentStep === 1" class="step-content" key="step2">
            <div class="upload-wrapper">
              <el-upload
                ref="uploadRef"
                v-model:file-list="fileList"
                :auto-upload="false"
                :limit="1"
                :before-upload="beforeUpload"
                :on-change="handleFileChange"
                accept=".csv,.xls,.xlsx"
                drag
                action="#"
                class="upload-el"
                @dragover="handleDragOver"
                @dragleave="handleDragLeave"
              >
                <div class="upload-zone" :class="{ 'has-file': fileList.length > 0, 'drag-over': isDragOver }">
                  <div v-if="fileList.length === 0" class="upload-empty">
                    <div class="upload-icon-wrap">
                      <Upload :size="32" />
                    </div>
                    <div class="upload-headline">点击或拖拽上传数据集</div>
                    <div class="upload-subline">支持 .csv / .xls / .xlsx（最大 100MB）</div>
                  </div>

                  <div v-else class="upload-file">
                    <div class="file-preview">
                      <FileSpreadsheet :size="28" />
                    </div>
                    <div class="file-info">
                      <div class="file-name">{{ fileList[0].name }}</div>
                      <div class="file-meta">{{ fileSizeText }}</div>
                    </div>
                    <button class="file-remove" @click.stop.prevent="removeFile">
                      <AlertCircle :size="16" />
                      移除
                    </button>
                  </div>
                </div>
              </el-upload>
            </div>
          </div>

          <!-- Step 3: Review -->
          <div v-else-if="currentStep === 2" class="step-content" key="step3">
            <div class="review-card">
              <div class="review-head">
                <div class="review-icon">
                  <FileCheck :size="20" />
                </div>
                <div class="review-head-text">确认项目信息</div>
              </div>

              <div class="review-body">
                <div class="review-row">
                  <span class="review-key">项目名称</span>
                  <span class="review-value">{{ projectForm.name }}</span>
                </div>
                <div class="review-divider" />
                <div v-if="projectForm.description" class="review-row">
                  <span class="review-key">项目描述</span>
                  <span class="review-value review-value-multiline">{{ projectForm.description }}</span>
                </div>
                <div v-if="projectForm.description" class="review-divider" />
                <div class="review-row">
                  <span class="review-key">数据集</span>
                  <span class="review-value file-badge">
                    <FileSpreadsheet :size="14" />
                    {{ fileList[0]?.name }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <!-- Footer -->
      <div class="card-footer">
        <div class="footer-left">
          <a
            v-if="currentStep === 1"
            href="/api/samples/order-sample-2/download"
            download
            class="sample-link"
          >
            <FileSpreadsheet :size="14" />
            下载示例数据
          </a>
        </div>

        <div class="footer-right">
          <el-button
            v-if="currentStep > 0"
            @click="prevStep"
            plain
            size="large"
            class="btn-prev"
          >
            上一步
          </el-button>

          <el-button
            type="primary"
            size="large"
            :loading="uploading"
            class="btn-next"
            @click="currentStep === 2 ? createProject() : nextStep()"
          >
            <template v-if="uploading">
              <span class="loading-text">{{ statusMessage }}</span>
            </template>
            <template v-else>
              {{ currentStep === 2 ? '开始智能分析' : '下一步' }}
              <ChevronRight v-if="currentStep < 2" :size="16" style="margin-left: 4px" />
            </template>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Page shell ── */
.create-page {
  min-height: calc(100vh - 88px);
  padding: 32px 24px 64px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  max-width: 680px;
  margin: 0 auto 28px;
}

.back-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: var(--color-surface);
  border: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: var(--color-surface-hover);
  color: var(--text-primary);
  border-color: var(--border-focus);
}

.page-title {
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  margin: 0;
}

/* ── Card ── */
.create-card {
  max-width: 680px;
  margin: 0 auto;
  background: var(--color-surface);
  border-radius: 24px;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

/* ── Stepper ── */
.stepper {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 32px 40px 0;
  gap: 0;
}

.step {
  display: flex;
  align-items: flex-start;
  gap: 0;
  flex: 1;
}

.step-body {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.step-badge {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: var(--color-surface-hover);
  border: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  transition: all 0.3s var(--ease-smooth);
  flex-shrink: 0;
}

.step.active .step-badge {
  background: var(--text-primary);
  color: var(--color-surface);
  border-color: var(--text-primary);
  box-shadow: 0 0 0 4px rgba(0, 0, 0, 0.05);
}

.step.completed .step-badge {
  background: #10b981;
  color: #fff;
  border-color: #10b981;
}

.step-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-title {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-tertiary);
  transition: color 0.3s ease;
  white-space: nowrap;
}

.step.active .step-title {
  color: var(--text-primary);
}

.step-desc {
  font-size: 0.72rem;
  color: var(--text-tertiary);
  opacity: 0.7;
  white-space: nowrap;
}

.step-connector {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 0 12px;
  margin-top: 20px;
  min-width: 40px;
}

.step-track {
  width: 100%;
  height: 2px;
  background: var(--color-surface-hover);
  border-radius: 1px;
  overflow: hidden;
  position: relative;
}

.step-fill {
  height: 100%;
  background: #10b981;
  border-radius: 1px;
  transition: width 0.5s var(--ease-smooth);
}

/* ── Card body ── */
.card-body {
  padding: 36px 40px 24px;
  min-height: 320px;
}

.step-content {
  width: 100%;
}

/* ── Form fields ── */
.field-group {
  margin-bottom: 24px;
}

.field-group:last-child {
  margin-bottom: 0;
}

.field-label {
  display: block;
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 10px;
  letter-spacing: -0.01em;
}

.required {
  color: #ef4444;
  margin-left: 2px;
}

.optional {
  font-weight: 400;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  margin-left: 4px;
}

.field-hint {
  margin: 8px 0 0;
  font-size: 0.78rem;
  color: var(--text-tertiary);
}

/* ── Upload zone ── */
.upload-wrapper {
  width: 100%;
}

:deep(.upload-el .el-upload) {
  width: 100% !important;
}

:deep(.upload-el .el-upload-dragger) {
  width: 100% !important;
  padding: 0 !important;
  border: none !important;
  background: transparent !important;
}

.upload-zone {
  min-height: 260px;
  border: 2px dashed var(--border-subtle);
  border-radius: 16px;
  background: var(--color-bg-base);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s var(--ease-smooth);
  cursor: pointer;
  overflow: hidden;
}

.upload-zone:hover,
.upload-zone.drag-over {
  border-color: var(--color-accent);
  background: var(--color-accent-soft);
  transform: scale(1.005);
}

.upload-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 24px;
}

.upload-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: var(--color-surface);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  transition: all 0.3s ease;
}

.upload-zone:hover .upload-icon-wrap {
  color: var(--color-accent);
  border-color: var(--border-focus);
  box-shadow: var(--shadow-sm);
}

.upload-headline {
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-primary);
}

.upload-subline {
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

/* File selected state */
.upload-file {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  padding: 24px 28px;
  background: var(--color-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
}

.file-preview {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--color-accent-soft);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 0.78rem;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.file-remove {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-tertiary);
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.file-remove:hover {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.15);
}

/* ── Review card ── */
.review-card {
  background: var(--color-bg-base);
  border-radius: 16px;
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

.review-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 24px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--border-subtle);
}

.review-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--color-accent-soft);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
}

.review-head-text {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.review-body {
  padding: 16px 24px;
}

.review-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 0;
}

.review-key {
  font-size: 0.85rem;
  color: var(--text-tertiary);
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.review-value {
  font-size: 0.9rem;
  color: var(--text-primary);
  font-weight: 600;
  text-align: right;
}

.review-value-multiline {
  white-space: pre-wrap;
  line-height: 1.5;
  text-align: left;
  max-width: 70%;
  word-break: break-word;
}

.file-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--color-accent-soft);
  color: var(--color-accent);
  border-radius: 8px;
  font-size: 0.8rem;
}

.review-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: 0;
}

/* ── Footer ── */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 40px 32px;
}

.footer-left {
  display: flex;
  align-items: center;
}

.footer-right {
  display: flex;
  gap: 12px;
}

.sample-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--color-accent);
  font-weight: 500;
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.sample-link:hover {
  background: var(--color-accent-soft);
  text-decoration: none;
}

.btn-prev {
  padding: 0 24px !important;
  height: 44px !important;
  border-radius: 12px !important;
  font-weight: 500 !important;
}

.btn-next {
  padding: 0 28px !important;
  height: 44px !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
  background: linear-gradient(135deg, var(--color-accent) 0%, #7c3aed 100%) !important;
  border: none !important;
  box-shadow: 0 8px 20px rgba(94, 106, 210, 0.3) !important;
  transition: all 0.25s ease !important;
}

.btn-next:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 12px 28px rgba(94, 106, 210, 0.38) !important;
}

.btn-next:active {
  transform: translateY(0) !important;
}

.loading-text {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

/* ── Transitions ── */
.slide-step-enter-active,
.slide-step-leave-active {
  transition: all 0.35s var(--ease-smooth);
}

.slide-step-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.slide-step-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* ── Responsive ── */
@media (max-width: 640px) {
  .create-page {
    padding: 20px 16px 40px;
  }

  .stepper {
    padding: 24px 20px 0;
  }

  .step-body {
    flex-direction: column;
    gap: 6px;
    align-items: center;
  }

  .step-text {
    align-items: center;
  }

  .card-body {
    padding: 24px 20px 20px;
  }

  .card-footer {
    padding: 16px 20px 24px;
    flex-direction: column;
    align-items: stretch;
  }

  .footer-left {
    justify-content: center;
  }

  .footer-right {
    justify-content: stretch;
  }

  .btn-next,
  .btn-prev {
    flex: 1;
  }
}

@media (max-width: 480px) {
  .step-title,
  .step-desc {
    display: none;
  }

  .step-connector {
    padding: 0 8px;
  }
}
</style>
