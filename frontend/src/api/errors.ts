import axios from 'axios'

export interface NormalizedApiError {
  message: string
  status?: number
  details?: unknown
  raw?: unknown
}

export class ApiError extends Error {
  status?: number
  details?: unknown
  raw?: unknown

  constructor(error: NormalizedApiError) {
    super(error.message)
    this.name = 'ApiError'
    this.status = error.status
    this.details = error.details
    this.raw = error.raw
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function stringifyDetailItem(item: unknown): string {
  if (typeof item === 'string') return item
  if (!isRecord(item)) return String(item)

  const message = item.msg ?? item.message ?? item.detail
  const location = Array.isArray(item.loc) ? item.loc.join('.') : undefined
  if (typeof message === 'string' && location) return `${location}: ${message}`
  if (typeof message === 'string') return message
  return JSON.stringify(item)
}

function detailToMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(stringifyDetailItem).join('；')
  if (isRecord(detail)) {
    const message = detail.message ?? detail.error ?? detail.detail
    if (typeof message === 'string') return message
    return JSON.stringify(detail)
  }
  return '请求失败'
}

export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  if (axios.isAxiosError(error)) {
    const payload = error.response?.data
    const detail = isRecord(payload) ? payload.detail ?? payload.error ?? payload.message : undefined
    const message = detail !== undefined ? detailToMessage(detail) : error.message || '网络请求失败'
    return new ApiError({
      message,
      status: error.response?.status,
      details: detail,
      raw: payload ?? error
    })
  }

  if (error instanceof Error) {
    return new ApiError({ message: error.message, raw: error })
  }

  return new ApiError({ message: detailToMessage(error), raw: error })
}

export function getApiErrorMessage(error: unknown): string {
  return normalizeApiError(error).message
}