import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import type { LoginRequest, RegisterRequest, UserResponse } from '@/api/auth'

type AuthStatus = 'idle' | 'loading' | 'authenticated' | 'anonymous'

const STORAGE_KEY = 'marketmind_access_token'

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function writeStoredToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(STORAGE_KEY, token)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  } catch {
    // ignore storage errors
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserResponse | null>(null)
  const accessToken = ref<string | null>(readStoredToken())
  const status = ref<AuthStatus>('idle')
  const authError = ref<string | null>(null)
  const returnTo = ref<string | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value && status.value === 'authenticated')
  const isLoading = computed(() => status.value === 'loading')

  function setToken(token: string | null) {
    accessToken.value = token
    writeStoredToken(token)
  }

  function clearAuth() {
    user.value = null
    setToken(null)
    status.value = 'anonymous'
    authError.value = null
  }

  async function loadMe() {
    if (!accessToken.value) {
      status.value = 'anonymous'
      return
    }
    try {
      const data = await authApi.me()
      user.value = data
      status.value = 'authenticated'
    } catch {
      clearAuth()
    }
  }

  async function login(data: LoginRequest, options?: { redirect?: string }) {
    status.value = 'loading'
    authError.value = null
    try {
      const result = await authApi.login(data)
      setToken(result.access_token)
      user.value = result.user
      status.value = 'authenticated'
      const target = options?.redirect || returnTo.value || '/projects'
      returnTo.value = null
      return target
    } catch (error: any) {
      clearAuth()
      authError.value = error?.message || '登录失败'
      throw error
    }
  }

  async function register(data: RegisterRequest) {
    status.value = 'loading'
    authError.value = null
    try {
      await authApi.register(data)
      status.value = 'anonymous'
      return await login({ email: data.email, password: data.password })
    } catch (error: any) {
      status.value = 'anonymous'
      authError.value = error?.message || '注册失败'
      throw error
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // ignore
    } finally {
      clearAuth()
    }
  }

  function setReturnTo(path: string | null) {
    returnTo.value = path
  }

  return {
    user,
    accessToken,
    status,
    authError,
    returnTo,
    isAuthenticated,
    isLoading,
    loadMe,
    login,
    register,
    logout,
    clearAuth,
    setReturnTo,
  }
})
