<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { computed, ref, onMounted } from 'vue'
import { Moon, Sun } from 'lucide-vue-next'
import ServiceStatus from '@/components/ServiceStatus.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

const isHome = computed(() => route.path === '/')
const isProjectsActive = computed(() => route.path.startsWith('/projects') || route.path.startsWith('/me/projects'))
const isProfileActive = computed(() => route.path.startsWith('/me'))

const isDark = ref(false)

const toggleTheme = () => {
  isDark.value = !isDark.value
  const html = document.documentElement
  if (isDark.value) {
    html.classList.add('dark')
    localStorage.setItem('mm-theme', 'dark')
  } else {
    html.classList.remove('dark')
    localStorage.setItem('mm-theme', 'light')
  }
}

const initTheme = () => {
  const storedTheme = localStorage.getItem('mm-theme')
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const html = document.documentElement

  if (storedTheme === 'dark' || (!storedTheme && systemDark)) {
    isDark.value = true
    html.classList.add('dark')
  } else {
    isDark.value = false
    html.classList.remove('dark')
  }

  // Listen for system changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (!localStorage.getItem('mm-theme')) {
      isDark.value = e.matches
      if (e.matches) html.classList.add('dark')
      else html.classList.remove('dark')
    }
  })
}

onMounted(() => {
  initTheme()
})
</script>

<template>
  <div class="app-shell" :class="{ 'on-home': isHome }">
    <nav class="navbar glass">
      <div class="nav-content">
        <RouterLink to="/" class="brand">
          <span class="brand-logo">M</span>
          <span class="brand-text">MarketMind</span>
        </RouterLink>

        <div v-if="authStore.isAuthenticated" class="nav-links">
          <RouterLink to="/" class="nav-item" :class="{ active: isHome }">主页</RouterLink>
          <RouterLink to="/projects" class="nav-item" :class="{ active: isProjectsActive }">我的项目</RouterLink>
          <RouterLink v-if="authStore.isAdmin" to="/admin" class="nav-item" :class="{ active: route.path.startsWith('/admin') }">管理</RouterLink>
        </div>

        <div class="nav-actions">
          <button class="theme-toggle" @click="toggleTheme" :title="isDark ? '切换亮色' : '切换暗色'">
            <Sun v-if="isDark" /><Moon v-else />
          </button>

          <!-- Service Status Component -->
          <ServiceStatus />

          <RouterLink
            v-if="authStore.isAuthenticated"
            to="/me/profile"
            class="user-pill"
            :class="{ active: isProfileActive }"
          >
            <div class="user-avatar">{{ (authStore.user?.display_name || authStore.user?.email || 'U').charAt(0).toUpperCase() }}</div>
            <span class="user-name">{{ authStore.user?.display_name || authStore.user?.email || '用户' }}</span>
          </RouterLink>

          <div v-else class="auth-buttons">
            <RouterLink to="/login" class="btn-auth btn-auth-login">登录</RouterLink>
            <RouterLink to="/register" class="btn-auth btn-auth-register">注册</RouterLink>
          </div>
        </div>
      </div>
    </nav>

    <main class="main-view" :class="{ 'no-padding': isHome }">
      <RouterView v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </RouterView>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 72px;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s ease;
}

.navbar.glass {
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px);
}

html.dark .navbar.glass {
  background: rgba(15, 15, 20, 0.78);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

/* Removed transparent class to enforce glass effect everywhere */

.nav-content {
  width: 100%;
  max-width: 1200px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text-primary);
  font-weight: 700;
  font-size: 1.1rem;
  letter-spacing: -0.02em;
}

.brand-logo {
  width: 32px;
  height: 32px;
  background: #111827;
  color: #fff;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 800;
}

.brand-text {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.02em;
}

html.dark .brand-text {
  color: #f1f5f9;
}

.nav-links {
  display: flex;
  gap: 4px;
  padding: 4px;
}

.on-home .nav-links {
  background: transparent;
}

.nav-item {
  color: #475569;
  font-size: 0.9rem;
  font-weight: 500;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, border-color 160ms ease, color 160ms ease;
  padding: 8px 20px;
  border-radius: 14px;
  position: relative;
  text-decoration: none !important;
}

html.dark .nav-item {
  color: #94a3b8;
}

.nav-item:hover {
  color: #111827;
  background: rgba(15, 23, 42, 0.04);
}

html.dark .nav-item:hover {
  color: #f1f5f9;
  background: rgba(255, 255, 255, 0.06);
}

.nav-item.active {
  color: #4f46e5;
  background: rgba(99, 102, 241, 0.10);
  font-weight: 600;
  box-shadow: none;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.theme-toggle {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(15, 23, 42, 0.08);
  cursor: pointer;
  color: #475569;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, border-color 160ms ease;
}

html.dark .theme-toggle {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.1);
  color: #94a3b8;
}

.theme-toggle:hover {
  background: #fff;
  border-color: rgba(99, 102, 241, 0.26);
  color: #111827;
}

html.dark .theme-toggle:hover {
  background: rgba(255, 255, 255, 0.14);
  color: #f1f5f9;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--nav-pill-bg);
  border-radius: var(--radius-pill);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.on-home .status-pill {
  background: var(--nav-pill-bg);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #ccc;
}

.status-pill.healthy .status-dot {
  background-color: #10B981;
  box-shadow: 0 0 4px #10B98166;
}

.status-pill.error .status-dot {
  background-color: #EF4444;
}

.btn-new-project {
  height: 42px;
  padding: 0 20px;
  border-radius: 999px;
  background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
  color: #fff;
  font-weight: 600;
  font-size: 0.9rem;
  box-shadow: 0 10px 24px rgba(99, 102, 241, 0.28);
  display: flex;
  align-items: center;
  gap: 6px;
  text-decoration: none !important;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, border-color 160ms ease;
}

.btn-new-project:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 34px rgba(99, 102, 241, 0.36);
}

.btn-new-project:active {
  transform: translateY(0);
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 42px;
  padding: 0 14px 0 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(15, 23, 42, 0.08);
  text-decoration: none !important;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, border-color 160ms ease;
  cursor: pointer;
}

html.dark .user-pill {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.1);
}

.user-pill:hover {
  background: #fff;
  border-color: rgba(99, 102, 241, 0.26);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.14);
}

html.dark .user-pill:hover {
  background: rgba(255, 255, 255, 0.14);
}

.user-pill.active {
  background: rgba(99, 102, 241, 0.10);
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08);
}

.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #374151;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

html.dark .user-name {
  color: #e2e8f0;
}

.auth-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-auth {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: none !important;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, border-color 160ms ease;
}

.btn-auth-login {
  color: #475569;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(15, 23, 42, 0.08);
}

html.dark .btn-auth-login {
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.1);
}

.btn-auth-login:hover {
  background: #fff;
  border-color: rgba(99, 102, 241, 0.26);
  color: #111827;
  transform: translateY(-1px);
}

html.dark .btn-auth-login:hover {
  background: rgba(255, 255, 255, 0.14);
  color: #f1f5f9;
}

.btn-auth-register {
  color: #fff;
  background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
  border: none;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.24);
}

.btn-auth-register:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(99, 102, 241, 0.32);
}

.main-view {
  padding-top: 88px;
  flex: 1;
  width: 100%;
}

.main-view.no-padding {
  padding-top: 0;
}

/* Page Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}
</style>
