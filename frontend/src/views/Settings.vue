<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const vendorOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: '阿里通义', value: 'qwen' },
  { label: '其他', value: 'custom' }
]

const form = ref({
  vendor: 'openai',
  apiKey: '',
  model: '',
  apiEndpoint: ''
})

const STORAGE_KEY = 'mm_llm_settings'

const loadSettings = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      form.value = {
        vendor: parsed.vendor || 'openai',
        apiKey: parsed.apiKey || '',
        model: parsed.model || '',
        apiEndpoint: parsed.apiEndpoint || ''
      }
    }
  } catch (e) {
    // ignore
  }
}

const saveSettings = () => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(form.value))
  ElMessage.success('已保存大模型配置（存于本地浏览器）')
}

const testConnection = async () => {
  try {
    if (form.value.vendor === 'custom' && !form.value.apiEndpoint) {
      ElMessage.warning('请填写自定义供应商的 API 地址')
      return
    }
    const target = form.value.vendor === 'custom' ? form.value.apiEndpoint : '/api/health'
    await axios.get(target)
    ElMessage.success('测试成功，接口可用')
  } catch (e: any) {
    ElMessage.error(`测试失败：${e?.message || '请检查网络或接口地址'}`)
  }
}

onMounted(() => loadSettings())
</script>

<template>
  <div class="page-container">
    <el-page-header @back="$router.push('/')" title="返回">
      <template #content>
        <span class="page-title">⚙️ 设置</span>
      </template>
    </el-page-header>

    <el-card class="settings-card">
      <el-form label-width="120px" :model="form">
        <el-form-item label="大模型供应商">
          <el-select v-model="form.vendor" placeholder="选择供应商" style="max-width: 300px;">
            <el-option
              v-for="item in vendorOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item v-if="form.vendor === 'custom'" label="API 地址">
          <el-input
            v-model="form.apiEndpoint"
            placeholder="请输入自定义供应商的 API 入口，例如：https://api.example.com/health"
            style="max-width: 420px;"
          />
        </el-form-item>

        <el-form-item label="大模型密钥">
          <el-input
            v-model="form.apiKey"
            show-password
            placeholder="请输入 API Key"
            style="max-width: 420px;"
          />
        </el-form-item>

        <el-form-item label="大模型名称">
          <el-input
            v-model="form.model"
            placeholder="例如：gpt-4o、claude-3-5、qwen-max"
            style="max-width: 420px;"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="saveSettings">保存</el-button>
          <el-button @click="loadSettings">恢复</el-button>
          <el-button type="success" @click="testConnection">测试</el-button>
        </el-form-item>
      </el-form>
      <p class="tip">提示：当前设置仅存储在浏览器本地，如需服务端持久化请后续接入后端。</p>
    </el-card>
  </div>
</template>

<style scoped>
.page-container {
  padding: 2rem;
  max-width: 960px;
  margin: 0 auto;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
}

.settings-card {
  margin-top: 1rem;
}

.tip {
  color: #94a3b8;
  font-size: 0.95rem;
  margin-top: 0.5rem;
}
</style>
