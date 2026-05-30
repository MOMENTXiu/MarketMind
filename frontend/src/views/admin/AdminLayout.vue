<script setup lang="ts">
import { RouterView, useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'
import { LayoutDashboard, Settings, ScrollText, Users, ArrowLeft } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

const navItems = [
  { path: '/admin/status', label: '运行状态', icon: LayoutDashboard },
  { path: '/admin/settings', label: '系统设置', icon: Settings },
  { path: '/admin/logs', label: '系统日志', icon: ScrollText },
  { path: '/admin/users', label: '用户管理', icon: Users },
]

const currentPath = computed(() => route.path)
</script>

<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="sidebar-header">
        <button class="back-link" @click="router.push('/projects')">
          <ArrowLeft :size="16" />
          <span>返回</span>
        </button>
        <h2 class="sidebar-title">管理控制台</h2>
      </div>
      <nav class="sidebar-nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="sidebar-item"
          :class="{ active: currentPath.startsWith(item.path) }"
        >
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </aside>
    <main class="admin-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: calc(100vh - 72px);
  background: #f8fafc;
}

html.dark .admin-layout {
  background: #0f0f14;
}

.admin-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid rgba(15, 23, 42, 0.06);
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

html.dark .admin-sidebar {
  background: #1a1a20;
  border-color: rgba(255, 255, 255, 0.06);
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #6366f1;
  font-size: 0.85rem;
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  text-decoration: none;
}

.back-link:hover {
  color: #4f46e5;
}

.sidebar-title {
  font-size: 1rem;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

html.dark .sidebar-title {
  color: #f1f5f9;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  color: #475569;
  font-size: 0.9rem;
  font-weight: 500;
  text-decoration: none;
  transition: all 160ms ease;
}

html.dark .sidebar-item {
  color: #94a3b8;
}

.sidebar-item:hover {
  color: #111827;
  background: rgba(15, 23, 42, 0.04);
}

html.dark .sidebar-item:hover {
  color: #f1f5f9;
  background: rgba(255, 255, 255, 0.06);
}

.sidebar-item.active {
  color: #4f46e5;
  background: rgba(99, 102, 241, 0.10);
  font-weight: 600;
}

.admin-main {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}
</style>
