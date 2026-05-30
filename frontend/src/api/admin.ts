import { apiClient, unwrapApiEnvelope } from './client'

// ── Types ────────────────────────────────────────────────────────────────────

export type ServiceStatus = 'healthy' | 'degraded' | 'down' | 'unknown'
export type ServiceCategory = 'app' | 'infra' | 'external'

export interface ServiceHealth {
  key: string
  name: string
  category: ServiceCategory
  status: ServiceStatus
  latencyMs?: number | null
  checkedAt?: string | null
  message?: string | null
  version?: string | null
}

export interface AdminStatusSummary {
  overallStatus: ServiceStatus
  services: ServiceHealth[]
  generatedAt: string | null
}

export interface LlmSettings {
  provider: string
  baseUrl?: string | null
  model?: string | null
  apiKeyConfigured: boolean
  timeoutSeconds?: number | null
  enabled: boolean
}

export interface InfraComponentSettings {
  host: string
  port: number
  database?: string | null
  username?: string | null
  passwordConfigured: boolean
}

export interface MinioSettings {
  endpoint: string
  bucket: string
  accessKeyConfigured: boolean
  secretKeyConfigured: boolean
  secure: boolean
}

export interface InfraSettings {
  postgres?: InfraComponentSettings | null
  redis?: InfraComponentSettings | null
  minio?: MinioSettings | null
}

export interface AlertSettings {
  enabled: boolean
  serverUrl?: string | null
  deviceKeyConfigured: boolean
  defaultGroup?: string | null
  alertLevels: string[]
}

export interface AllSettings {
  llm?: LlmSettings | null
  infra?: InfraSettings | null
  alert?: AlertSettings | null
}

export interface TestResult {
  success: boolean
  message: string
  latencyMs?: number | null
}

export interface AdminLogRecord {
  id: string
  level: 'info' | 'warning' | 'error' | 'critical'
  eventType: string
  message: string
  actorUserId?: string | null
  resourceType?: string | null
  resourceId?: string | null
  projectId?: string | null
  jobId?: string | null
  requestId?: string | null
  traceId?: string | null
  createdAt?: string | null
  metadata?: Record<string, unknown> | null
}

export interface AdminLogPage {
  items: AdminLogRecord[]
  total: number
  offset: number
  limit: number
}

export interface AdminUserListItem {
  id: string
  email: string
  displayName?: string | null
  role: 'user' | 'admin'
  status: 'active' | 'disabled'
  projectCount: number
  lastLoginAt?: string | null
  createdAt?: string | null
}

export interface AdminUserProject {
  id: string
  name: string
  status?: string | null
  createdAt?: string | null
}

export interface AdminUserDetail {
  id: string
  email: string
  displayName?: string | null
  role: 'user' | 'admin'
  status: 'active' | 'disabled'
  projectCount: number
  projects: AdminUserProject[]
  lastLoginAt?: string | null
  createdAt?: string | null
  updatedAt?: string | null
}

// ── Status ───────────────────────────────────────────────────────────────────

export function getAdminStatusSummary(): Promise<AdminStatusSummary> {
  return unwrapApiEnvelope(apiClient.get('/api/admin/status/summary'))
}

// ── Settings ─────────────────────────────────────────────────────────────────

export function getSettings(): Promise<AllSettings> {
  return unwrapApiEnvelope(apiClient.get('/api/admin/settings'))
}

export function testLlmConnection(): Promise<TestResult> {
  return unwrapApiEnvelope(apiClient.post('/api/admin/settings/llm/test'))
}

export function testBarkAlert(): Promise<TestResult> {
  return unwrapApiEnvelope(apiClient.post('/api/admin/settings/alert/bark/test'))
}

// ── Logs ─────────────────────────────────────────────────────────────────────

export interface LogQueryParams {
  level?: string
  eventType?: string
  actorUserId?: string
  projectId?: string
  jobId?: string
  fromDate?: string
  toDate?: string
  offset?: number
  limit?: number
}

export function getEventLogs(params: LogQueryParams = {}): Promise<AdminLogPage> {
  return unwrapApiEnvelope(apiClient.get('/api/admin/logs/events', { params }))
}

export function getEventLogDetail(eventId: string): Promise<AdminLogRecord | null> {
  return unwrapApiEnvelope(apiClient.get(`/api/admin/logs/events/${eventId}`))
}

export function getAuditLogs(params: LogQueryParams = {}): Promise<AdminLogPage> {
  return unwrapApiEnvelope(apiClient.get('/api/admin/logs/audit', { params }))
}

export function getAuditLogDetail(auditId: string): Promise<AdminLogRecord | null> {
  return unwrapApiEnvelope(apiClient.get(`/api/admin/logs/audit/${auditId}`))
}

export function getExportUrl(type: 'events' | 'audit', format: 'json' | 'csv' = 'json', params: Record<string, string> = {}): string {
  const base = apiClient.defaults.baseURL || ''
  const qs = new URLSearchParams({ format, ...params }).toString()
  return `${base}/api/admin/logs/${type}/export?${qs}`
}

// ── Users ────────────────────────────────────────────────────────────────────

export function getAdminUsers(search?: string): Promise<AdminUserListItem[]> {
  return unwrapApiEnvelope(apiClient.get('/api/admin/users', { params: search ? { search } : {} }))
}

export function getAdminUserDetail(userId: string): Promise<AdminUserDetail> {
  return unwrapApiEnvelope(apiClient.get(`/api/admin/users/${userId}`))
}

export function updateUserRole(userId: string, role: 'user' | 'admin'): Promise<AdminUserListItem> {
  return unwrapApiEnvelope(apiClient.patch(`/api/admin/users/${userId}/role`, { role }))
}

export function updateUserStatus(userId: string, status: 'active' | 'disabled'): Promise<AdminUserListItem> {
  return unwrapApiEnvelope(apiClient.patch(`/api/admin/users/${userId}/status`, { status }))
}
