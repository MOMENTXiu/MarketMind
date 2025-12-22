import axios from 'axios'

// Create a custom instance
const http = axios.create({
  // Default to relative path / which will be proxied by Vite if not overridden
  // or simple /api if we want to rely on the interceptor
})

// Request interceptor to set base URL dynamically
http.interceptors.request.use(config => {
  const dynamicUrl = localStorage.getItem('API_BASE_URL')
  
  if (dynamicUrl) {
    // If dynamic URL is set, use it.
    // Note: If the request url starts with /api, we might need to be careful.
    // Usually baseURL + url = full url.
    // If baseURL is http://localhost:8000 and url is /api/health, result is http://localhost:8000/api/health.
    // This is what we want.
    config.baseURL = dynamicUrl
  } else {
    // Fallback or default behavior (e.g. relative path for Vite proxy)
    // We don't set baseURL here so it uses the window.location.origin (effectively)
  }
  return config
}, error => {
  return Promise.reject(error)
})

export default http
