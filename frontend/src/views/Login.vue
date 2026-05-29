<template>
  <div class="auth-container">
    <el-card class="auth-card">
      <h2 class="auth-title">登录 MarketMind</h2>
      <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent="handleSubmit">
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            placeholder="邮箱"
            prefix-icon="Message"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item v-if="authStore.authError">
          <el-alert :title="authStore.authError" type="error" :closable="false" />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="auth-submit"
            :loading="authStore.isLoading"
            @click="handleSubmit"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="auth-footer">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()

const form = reactive({
  email: '',
  password: ''
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    const redirect = (route.query.redirect as string) || '/projects'
    await authStore.login({ email: form.email, password: form.password })
    router.push(redirect)
  } catch {
    // error handled by store
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}
.auth-card {
  width: 420px;
  padding: 24px;
}
.auth-title {
  text-align: center;
  margin-bottom: 24px;
  font-size: 24px;
  color: #303133;
}
.auth-submit {
  width: 100%;
}
.auth-footer {
  text-align: center;
  margin-top: 16px;
  color: #606266;
}
.auth-footer a {
  color: #409eff;
  text-decoration: none;
}
</style>
