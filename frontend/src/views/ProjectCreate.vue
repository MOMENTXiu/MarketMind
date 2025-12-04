<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import type { UploadInstance, UploadProps } from 'element-plus'

const router = useRouter()

// 当前步骤
const currentStep = ref(0)

// 表单数据
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

// 上传文件
const uploadRef = ref<UploadInstance>()
const fileList = ref<any[]>([])
const uploading = ref(false)

// 步骤标题
const steps = [
  { title: '项目信息', description: '填写项目基本信息' },
  { title: '上传数据', description: '上传数据集并设置参数' },
  { title: '确认创建', description: '确认信息并开始分析' }
]

// 下一步
const nextStep = () => {
  if (currentStep.value === 0) {
    if (!projectForm.value.name) {
      ElMessage.warning('请填写项目名称')
      return
    }
  }

  if (currentStep.value === 1) {
    if (fileList.value.length === 0) {
      ElMessage.warning('请上传数据集文件')
      return
    }
  }

  currentStep.value++
}

// 上一步
const prevStep = () => {
  currentStep.value--
}

// 文件上传前校验
const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  const isCSV = file.name.endsWith('.csv') || file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
  if (!isCSV) {
    ElMessage.error('只能上传 CSV 或 Excel 文件！')
    return false
  }
  const isLt100M = file.size / 1024 / 1024 < 100
  if (!isLt100M) {
    ElMessage.error('文件大小不能超过 100MB！')
    return false
  }
  return true
}

// 文件列表变化
const handleFileChange: UploadProps['onChange'] = (_file, files) => {
  fileList.value = files
}

// 创建项目并上传
const createProject = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请上传数据集文件')
    return
  }

  uploading.value = true

  try {
    // 第1步：创建项目
    const createResponse = await axios.post('/api/projects', projectForm.value)

    if (!createResponse.data.success) {
      throw new Error('创建项目失败')
    }

    const projectId = createResponse.data.data.id

    // 第2步：上传文件
    const formData = new FormData()
    formData.append('file', fileList.value[0].raw)

    const uploadResponse = await axios.post(
      `/api/projects/${projectId}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )

    if (uploadResponse.data.success) {
      ElMessage.success('项目创建成功，正在分析中...')
      setTimeout(() => {
        router.push(`/projects/${projectId}`)
      }, 1000)
    }

  } catch (error: any) {
    console.error('创建项目失败:', error)
    ElMessage.error(error.response?.data?.detail || '创建项目失败')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <el-page-header @back="$router.push('/projects')" title="返回">
      <template #content>
        <span class="page-title">➕ 新建项目</span>
      </template>
    </el-page-header>

    <div class="content">
      <el-card>
        <el-steps :active="currentStep" align-center finish-status="success">
          <el-step
            v-for="(step, index) in steps"
            :key="index"
            :title="step.title"
            :description="step.description"
          />
        </el-steps>

        <div class="step-content">
          <!-- 步骤1: 项目信息 -->
          <div v-show="currentStep === 0">
            <el-form :model="projectForm" label-width="120px">
              <el-form-item label="项目名称" required>
                <el-input
                  v-model="projectForm.name"
                  placeholder="请输入项目名称"
                  maxlength="100"
                  show-word-limit
                />
              </el-form-item>

              <el-form-item label="项目描述">
                <el-input
                  v-model="projectForm.description"
                  type="textarea"
                  :rows="4"
                  placeholder="请输入项目描述（可选）"
                  maxlength="500"
                  show-word-limit
                />
              </el-form-item>
            </el-form>
          </div>

          <!-- 步骤2: 上传数据 -->
          <div v-show="currentStep === 1">
            <el-form :model="projectForm" label-width="140px">
              <el-form-item label="数据集文件" required>
                <el-upload
                  ref="uploadRef"
                  :auto-upload="false"
                  :limit="1"
                  :before-upload="beforeUpload"
                  :on-change="handleFileChange"
                  accept=".csv,.xlsx,.xls"
                  drag
                >
                  <div class="upload-content">
                    <i class="el-icon-upload"></i>
                    <div class="el-upload__text">
                      拖拽文件到此处，或<em>点击上传</em>
                    </div>
                    <div class="el-upload__tip">
                      支持 CSV 和 Excel 文件，大小不超过 100MB
                    </div>
                  </div>
                </el-upload>
              </el-form-item>

              <el-divider>分析参数（可选）</el-divider>

              <el-form-item label="最小支持度">
                <el-slider
                  v-model="projectForm.parameters.min_support"
                  :min="0.01"
                  :max="0.1"
                  :step="0.01"
                  :format-tooltip="(val: number) => (val * 100).toFixed(0) + '%'"
                  show-input
                />
              </el-form-item>

              <el-form-item label="最小置信度">
                <el-slider
                  v-model="projectForm.parameters.min_confidence"
                  :min="0.1"
                  :max="0.9"
                  :step="0.1"
                  :format-tooltip="(val: number) => (val * 100).toFixed(0) + '%'"
                  show-input
                />
              </el-form-item>

              <el-form-item label="最小提升度">
                <el-input-number
                  v-model="projectForm.parameters.min_lift"
                  :min="0.5"
                  :max="5"
                  :step="0.5"
                />
              </el-form-item>

              <el-form-item label="预测周数">
                <el-input-number
                  v-model="projectForm.parameters.forecast_weeks"
                  :min="1"
                  :max="52"
                />
              </el-form-item>

              <el-form-item label="聚类数量">
                <el-input-number
                  v-model="projectForm.parameters.n_clusters"
                  :min="2"
                  :max="10"
                />
              </el-form-item>
            </el-form>
          </div>

          <!-- 步骤3: 确认信息 -->
          <div v-show="currentStep === 2">
            <el-descriptions title="项目信息" :column="1" border>
              <el-descriptions-item label="项目名称">
                {{ projectForm.name }}
              </el-descriptions-item>
              <el-descriptions-item label="项目描述">
                {{ projectForm.description || '无' }}
              </el-descriptions-item>
              <el-descriptions-item label="数据集文件">
                {{ fileList[0]?.name || '未上传' }}
              </el-descriptions-item>
            </el-descriptions>

            <el-descriptions title="分析参数" :column="2" border style="margin-top: 20px;">
              <el-descriptions-item label="最小支持度">
                {{ (projectForm.parameters.min_support * 100).toFixed(0) }}%
              </el-descriptions-item>
              <el-descriptions-item label="最小置信度">
                {{ (projectForm.parameters.min_confidence * 100).toFixed(0) }}%
              </el-descriptions-item>
              <el-descriptions-item label="最小提升度">
                {{ projectForm.parameters.min_lift }}
              </el-descriptions-item>
              <el-descriptions-item label="预测周数">
                {{ projectForm.parameters.forecast_weeks }} 周
              </el-descriptions-item>
              <el-descriptions-item label="聚类数量">
                {{ projectForm.parameters.n_clusters }} 类
              </el-descriptions-item>
            </el-descriptions>

            <el-alert
              type="info"
              title="提示"
              description="点击'创建并开始分析'后，系统将自动开始分析您的数据，请耐心等待。"
              style="margin-top: 20px;"
              :closable="false"
              show-icon
            />
          </div>
        </div>

        <div class="step-buttons">
          <el-button v-if="currentStep > 0" @click="prevStep">
            上一步
          </el-button>
          <el-button v-if="currentStep < 2" type="primary" @click="nextStep">
            下一步
          </el-button>
          <el-button
            v-if="currentStep === 2"
            type="primary"
            :loading="uploading"
            @click="createProject"
          >
            {{ uploading ? '创建中...' : '创建并开始分析' }}
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  padding: 2rem;
  max-width: 900px;
  margin: 0 auto;
}

.page-title {
  font-size: 1.5rem;
  font-weight: bold;
}

.content {
  margin-top: 2rem;
}

.step-content {
  margin: 3rem 0;
  min-height: 400px;
}

.step-buttons {
  display: flex;
  justify-content: center;
  gap: 1rem;
  padding-top: 2rem;
  border-top: 1px solid #eee;
}

.upload-content {
  text-align: center;
  padding: 2rem;
}

.el-icon-upload {
  font-size: 67px;
  color: #C0C4CC;
  margin-bottom: 16px;
}

.el-upload__text {
  color: #606266;
  font-size: 14px;
}

.el-upload__text em {
  color: #409EFF;
  font-style: normal;
}

.el-upload__tip {
  color: #999;
  font-size: 12px;
  margin-top: 8px;
}
</style>
