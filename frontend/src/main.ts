import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/main.css'
import App from './App.vue'
import router from './router'
import { installAuthInterceptors } from './api/client'
import { useAuthStore } from './stores/auth'

async function bootstrap() {
  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)
  app.use(ElementPlus)

  const authStore = useAuthStore()

  installAuthInterceptors(
    () => authStore.accessToken,
    () => {
      authStore.clearAuth()
      const current = router.currentRoute.value
      if (current.path !== '/login') {
        router.push({ path: '/login', query: { redirect: current.fullPath } })
      }
    }
  )

  await authStore.loadMe().catch(() => {
    // ignore
  })

  app.mount('#app')
}

bootstrap()
