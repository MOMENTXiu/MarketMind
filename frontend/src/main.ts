import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/main.css'
import App from './App.vue'
import router from './router'
import axios from 'axios'

// Global Axios Configuration
axios.interceptors.request.use(config => {
  const dynamicUrl = localStorage.getItem('API_BASE_URL')
  if (dynamicUrl) {
    // Check if the URL is absolute or relative
    if (!config.url?.startsWith('http')) {
       config.baseURL = dynamicUrl
    }
  }
  return config
})

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus)

app.mount('#app')
