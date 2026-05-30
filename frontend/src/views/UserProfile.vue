<template>
  <div class="profile-container">
    <div class="profile-card">
      <div class="profile-header">
        <div class="avatar">{{ avatarLetter }}</div>
        <div class="profile-info">
          <h2 class="profile-name">{{ authStore.user?.display_name || authStore.user?.email || '用户' }}</h2>
          <p class="profile-email">{{ authStore.user?.email }}</p>
          <el-tag size="small" type="success">{{ statusText }}</el-tag>
        </div>
      </div>

      <el-divider />

      <div class="profile-section">
        <h3 class="section-title">基本信息</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="用户ID">{{ authStore.user?.id }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ authStore.user?.email }}</el-descriptions-item>
          <el-descriptions-item label="昵称">{{ authStore.user?.display_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ authStore.user?.status }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <el-divider />

      <div class="profile-actions">
        <el-button type="danger" plain @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const avatarLetter = computed(() => {
  const name = authStore.user?.display_name || authStore.user?.email || 'U'
  return name.charAt(0).toUpperCase()
})

const statusText = computed(() => {
  return authStore.user?.status === 'active' ? '正常' : '已禁用'
})

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.profile-container {
  max-width: 720px;
  margin: 40px auto;
  padding: 0 24px;
}

.profile-card {
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

html.dark .profile-card {
  background: #1e1e2e;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 20px;
}

.avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
  color: #fff;
  font-size: 28px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.profile-name {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: #111827;
}

html.dark .profile-name {
  color: #f1f5f9;
}

.profile-email {
  margin: 0 0 8px;
  font-size: 14px;
  color: #6b7280;
}

.section-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: #374151;
}

html.dark .section-title {
  color: #d1d5db;
}

.profile-actions {
  display: flex;
  gap: 12px;
}
</style>
