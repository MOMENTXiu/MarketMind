<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '@/utils/http'
import type { UploadInstance, UploadProps } from 'element-plus'
import { UploadFilled, ArrowLeft } from '@element-plus/icons-vue'

const router = useRouter()
const currentStep = ref(0)

const projectForm = ref({
  name: '',
  description: '',
  parameters: {
    min_support: 0.02,
    min_confidence: 0.3,
    min_lift: 1.0,
    forecast_weeks: 13,
    n_clusters: 4
  }
})

const uploadRef = ref<UploadInstance>()
const fileList = ref<any[]>([])
const uploading = ref(false)

const steps = [
  { title: '基本信息', desc: 'Project Details' },
  { title: '数据上传', desc: 'Upload Dataset' },
  { title: '确认分析', desc: 'Confirmation' }
]

const nextStep = () => {
  if (currentStep.value === 0 && !projectForm.value.name) return ElMessage.warning('请输入项目名称')
  if (currentStep.value === 1 && fileList.value.length === 0) return ElMessage.warning('请上传数据集文件')
  currentStep.value++
}

const prevStep = () => currentStep.value--

const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  if (!/\.(csv|xlsx|xls)$/.test(file.name)) {
    ElMessage.error('仅支持 CSV 或 Excel 文件')
    return false
  }
  if (file.size / 1024 / 1024 > 100) {
    ElMessage.error('文件大小需小于 100MB')
    return false
  }
  return true
}

const handleFileChange: UploadProps['onChange'] = (_, files) => fileList.value = files

const createProject = async () => {
  if (fileList.value.length === 0) return ElMessage.warning('请上传数据集')
  uploading.value = true
  try {
    const { data: res } = await http.post('/api/projects/', projectForm.value)
    if (!res.success) throw new Error('创建项目失败')

    const formData = new FormData()
    formData.append('file', fileList.value[0].raw)
    const { data: uploadRes } = await http.post(`/api/projects/${res.data.id}/upload/`, formData)
    
    if (uploadRes.success) {
      ElMessage.success('项目已创建，开始分析')
      setTimeout(() => router.push(`/projects/${res.data.id}`), 1000)
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="container-breath">
    <!-- Header -->
    <div class="focus-header">
      <button class="btn-back" @click="$router.push('/projects')">
        <el-icon><ArrowLeft /></el-icon>
      </button>
      <h1 class="text-display" style="font-size: 1.8rem;">新建项目</h1>
    </div>

    <div class="focus-card">
      <!-- Custom Stepper -->
      <div class="custom-stepper">
        <div 
          v-for="(step, idx) in steps" 
          :key="idx"
          class="step-item"
          :class="{ active: currentStep === idx, completed: currentStep > idx }"
        >
          <div class="step-indicator">
            <span v-if="currentStep > idx">✓</span>
            <span v-else>{{ idx + 1 }}</span>
          </div>
          <div class="step-info">
            <span class="step-title">{{ step.title }}</span>
            <span class="step-desc">{{ step.desc }}</span>
          </div>
          <div class="step-line" v-if="idx < steps.length - 1"></div>
        </div>
      </div>

      <!-- Content Area -->
      <div class="form-content">
        <!-- Step 1 -->
        <div v-if="currentStep === 0" class="step-pane fade-in">
          <div class="input-group">
            <label>项目名称</label>
            <el-input 
              v-model="projectForm.name" 
              placeholder="例如：2024 Q1 销售分析" 
              size="large"
              class="large-input"
            />
          </div>
          <div class="input-group">
            <label>项目描述 <span class="optional">(可选)</span></label>
            <el-input 
              v-model="projectForm.description" 
              type="textarea" 
              :rows="4" 
              placeholder="简要描述本次分析的目标..." 
            />
          </div>
        </div>

        <!-- Step 2 -->
        <div v-if="currentStep === 1" class="step-pane fade-in">
          <div class="upload-area">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              :before-upload="beforeUpload"
              :on-change="handleFileChange"
              accept=".csv,.xlsx,.xls"
              drag
              action="#"
              class="full-width-upload"
            >
              <div class="upload-placeholder">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="upload-text">点击或拖拽上传数据集</div>
                <div class="upload-hint">支持 .csv, .xlsx (Max 100MB)</div>
              </div>
            </el-upload>
          </div>

          <div class="params-section">
            <h3 class="params-title">高级参数设定</h3>
            <div class="params-grid">
              <div class="param-item">
                <span class="param-label">最小支持度</span>
                <el-slider v-model="projectForm.parameters.min_support" :min="0.01" :max="0.1" :step="0.01" />
              </div>
              <div class="param-item">
                <span class="param-label">最小置信度</span>
                <el-slider v-model="projectForm.parameters.min_confidence" :min="0.1" :max="0.9" :step="0.1" />
              </div>
              <div class="param-item">
                <span class="param-label">预测周数 ({{ projectForm.parameters.forecast_weeks }}周)</span>
                <el-slider v-model="projectForm.parameters.forecast_weeks" :min="4" :max="52" />
              </div>
              <div class="param-item">
                <span class="param-label">聚类分组数 ({{ projectForm.parameters.n_clusters }}组)</span>
                <el-slider v-model="projectForm.parameters.n_clusters" :min="2" :max="8" />
              </div>
            </div>
          </div>
        </div>

        <!-- Step 3 -->
        <div v-if="currentStep === 2" class="step-pane fade-in">
          <div class="review-box">
            <div class="review-item">
              <span class="label">项目名称</span>
              <span class="value">{{ projectForm.name }}</span>
            </div>
            <div class="review-item">
              <span class="label">数据集</span>
              <span class="value">{{ fileList[0]?.name }}</span>
            </div>
            <div class="review-divider"></div>
            <div class="review-item">
              <span class="label">最小支持度</span>
              <span class="value">{{ (projectForm.parameters.min_support * 100).toFixed(0) }}%</span>
            </div>
            <div class="review-item">
              <span class="label">预测时长</span>
              <span class="value">{{ projectForm.parameters.forecast_weeks }} 周</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <el-button v-if="currentStep > 0" @click="prevStep" plain class="btn-secondary">上一步</el-button>
        <el-button 
          type="primary" 
          @click="currentStep === 2 ? createProject() : nextStep()" 
          :loading="uploading"
          class="btn-primary-large"
        >
          {{ currentStep === 2 ? '开始智能分析' : '下一步' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.focus-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 40px;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.btn-back {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--text-tertiary);
  transition: color 0.2s;
}

.btn-back:hover { color: var(--text-primary); }

.focus-card {
  max-width: 800px;
  margin: 0 auto;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 40px;
  border: 1px solid var(--border-subtle);
  position: relative;
}

.custom-stepper {
  display: flex;
  justify-content: space-between;
  margin-bottom: 48px;
  position: relative;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  z-index: 2;
  flex: 1;
}

.step-indicator {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-surface-hover);
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  transition: all 0.3s ease;
  border: 1px solid var(--border-subtle);
}

.step-item.active .step-indicator {
  background: var(--text-primary);
  color: var(--color-surface);
  border-color: var(--text-primary);
  box-shadow: 0 0 0 4px rgba(0,0,0,0.05);
}

.step-item.completed .step-indicator {
  background: #10B981;
  color: white;
  border-color: #10B981;
}

.step-info {
  display: flex;
  flex-direction: column;
}

.step-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-tertiary);
}

.step-item.active .step-title { color: var(--text-primary); }
.step-desc { font-size: 0.75rem; color: var(--text-tertiary); opacity: 0.7; }

.step-line {
  flex: 1;
  height: 2px;
  background: var(--color-surface-hover);
  margin: 0 16px;
}

.form-content {
  min-height: 300px;
}

.input-group {
  margin-bottom: 24px;
}

.input-group label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.optional {
  font-weight: 400;
  color: var(--text-tertiary);
  font-size: 0.85rem;
}

.upload-area {
  margin-bottom: 32px;
}

.upload-placeholder {
  padding: 40px;
  text-align: center;
  border: 2px dashed var(--border-subtle);
  border-radius: var(--radius-md);
  transition: all 0.2s ease;
  background: var(--color-bg-base);
}

.upload-placeholder:hover {
  border-color: var(--color-accent);
  background: var(--color-surface-hover);
}

.upload-icon {
  font-size: 48px;
  color: var(--text-tertiary);
  margin-bottom: 16px;
}

.upload-text {
  font-weight: 600;
  color: var(--text-primary);
}

.upload-hint {
  font-size: 0.85rem;
  color: var(--text-tertiary);
  margin-top: 8px;
}

.params-section {
  background: var(--color-bg-base);
  padding: 24px;
  border-radius: var(--radius-md);
}

.params-title {
  font-size: 0.95rem;
  color: var(--text-secondary);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.params-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.param-label {
  display: block;
  font-size: 0.85rem;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.review-box {
  background: var(--color-bg-base);
  border-radius: var(--radius-md);
  padding: 32px;
}

.review-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
  font-size: 1rem;
}

.review-item .label { color: var(--text-secondary); }
.review-item .value { font-weight: 600; color: var(--text-primary); }

.review-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: 24px 0;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 40px;
  padding-top: 24px;
  border-top: 1px solid var(--border-subtle);
}

.btn-primary-large {
  padding: 12px 32px !important;
  font-size: 1rem !important;
}

.fade-in {
  animation: fadeIn 0.4s var(--ease-smooth);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>