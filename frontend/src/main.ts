import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/main.css'
import App from './App.vue'
import router from './router'
import { installAuthInterceptors, setTokenGetter } from './api/client'
import { useAuthStore } from './stores/auth'

async function bootstrap() {
  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)

  const authStore = useAuthStore()

  // 先设置 token getter，让 loadMe() 的请求能带上 Authorization header
  setTokenGetter(() => authStore.accessToken)

  await authStore.loadMe().catch(() => {
    // ignore
  })

  app.use(router)

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

  app.use(ElementPlus)
  app.mount('#app')
}

bootstrap()
