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
          <ArrowLeft class="w-3.5 h-3.5" />
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
          <component :is="item.icon" class="w-4 h-4" />
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
  background: var(--color-bg-base);
}

.admin-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--color-surface);
  border-right: 1px solid var(--border-subtle);
  padding: 28px 20px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-accent);
  font-size: 0.85rem;
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}
.back-link:hover { opacity: 0.8; }

.sidebar-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.02em;
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
  border-radius: 12px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s ease;
}

.sidebar-item:hover {
  color: var(--text-primary);
  background: var(--color-surface-hover);
}

.sidebar-item.active {
  color: var(--color-accent);
  background: var(--color-accent-soft);
  font-weight: 600;
}

.admin-main {
  flex: 1;
  padding: 40px 48px;
  overflow-y: auto;
}
</style>
