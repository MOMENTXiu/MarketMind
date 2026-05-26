import { apiClient, requestDirect } from './client'
import type { HealthResponse } from './types'

export function getHealth(): Promise<HealthResponse> {
  return requestDirect(apiClient.get<HealthResponse>('/api/health/'))
}
