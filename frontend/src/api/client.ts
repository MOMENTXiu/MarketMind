import axios, { type AxiosResponse } from 'axios'

import { ApiError, normalizeApiError } from './errors'
import type { ApiEnvelope } from './types'

const DEFAULT_TIMEOUT = 30_000

function readTimeout(): number {
  const raw = import.meta.env.VITE_API_TIMEOUT
  if (!raw) return DEFAULT_TIMEOUT
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_TIMEOUT
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: readTimeout()
})

export async function unwrapApiEnvelope<T>(request: Promise<AxiosResponse<ApiEnvelope<T>>>): Promise<T> {
  try {
    const response = await request
    if (!response.data.success) {
      throw new ApiError({ message: '后端返回失败响应', raw: response.data })
    }
    return response.data.data
  } catch (error) {
    throw normalizeApiError(error)
  }
}

export async function requestDirect<T>(request: Promise<AxiosResponse<T>>): Promise<T> {
  try {
    const response = await request
    return response.data
  } catch (error) {
    throw normalizeApiError(error)
  }
}