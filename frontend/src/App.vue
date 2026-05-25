<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { computed, ref, onMounted } from 'vue'
import { Moon, Sunny, Plus } from '@element-plus/icons-vue'
import ServiceStatus from '@/components/ServiceStatus.vue'

const route = useRoute()
const isHome = computed(() => route.path === '/')
const isProjectsActive = computed(() => route.path.startsWith('/projects') || route.path.startsWith('/me/projects'))

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

        <div class="nav-links">
          <RouterLink to="/" class="nav-item" :class="{ active: isHome }">主页</RouterLink>
          <RouterLink to="/projects" class="nav-item" :class="{ active: isProjectsActive }">我的项目</RouterLink>
          <RouterLink to="/settings" class="nav-item" active-class="active">设置</RouterLink>
        </div>

        <div class="nav-actions">
          <button class="theme-toggle" @click="toggleTheme" :title="isDark ? '切换亮色' : '切换暗色'">
            <el-icon><Sunny v-if="isDark" /><Moon v-else /></el-icon>
          </button>

          <!-- Service Status Component -->
          <ServiceStatus />
          
          <RouterLink to="/projects/new">
            <el-button type="primary" round>
              <el-icon style="margin-right: 4px"><Plus /></el-icon>
              <span>新建项目</span>
            </el-button>
          </RouterLink>
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
  height: 64px;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s ease;
}

.navbar.glass {
  border-bottom: 1px solid var(--navbar-border);
  background: var(--navbar-bg);
  backdrop-filter: blur(16px);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.03); /* Subtle separation shadow */
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
  width: 24px;
  height: 24px;
  background: var(--text-primary);
  color: var(--color-bg-base);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 800;
}

.nav-links {
  display: flex;
  gap: 8px;
  background: var(--nav-pill-bg);
  padding: 4px;
  border-radius: var(--radius-pill);
}

.on-home .nav-links {
  background: var(--nav-pill-bg); 
}

.nav-item {
  color: var(--text-secondary);
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s var(--ease-smooth);
  padding: 8px 20px;
  border-radius: var(--radius-pill);
  position: relative;
  text-decoration: none !important;
}

.nav-item:hover {
  color: var(--text-primary);
  background: var(--nav-pill-hover);
}

.nav-item.active {
  color: var(--text-primary);
  background: var(--color-surface);
  font-weight: 700;
  box-shadow: var(--shadow-sm);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.theme-toggle {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 1.2rem;
  padding: 8px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.theme-toggle:hover {
  background: rgba(0,0,0,0.05);
  color: var(--text-primary);
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

.main-view {
  padding-top: 80px;
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