import axios from 'axios'

// Create axios instance with no baseURL - uses relative paths
const http = axios.create({
  // No baseURL needed - Vite proxy handles /api/* in development
  // In production, frontend and backend should be on same domain
})

export default http
