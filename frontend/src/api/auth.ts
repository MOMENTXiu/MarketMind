import { apiClient, unwrapApiEnvelope } from './client'

export interface RegisterRequest {
  email: string
  password: string
  display_name?: string | null
}

export interface LoginRequest {
  email: string
  password: string
}

export interface UserResponse {
  id: string
  email: string
  display_name: string | null
  status: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: UserResponse
}

export interface SseTicketRequest {
  resource_type: string
  resource_id: string
  project_id?: string | null
  job_id?: string | null
  stream_type?: string | null
}

export interface SseTicketResponse {
  ticket: string
  expires_at: string | null
}

export function register(data: RegisterRequest): Promise<{ id: string; email: string; display_name: string | null }> {
  return unwrapApiEnvelope(apiClient.post('/api/auth/register', data))
}

export function login(data: LoginRequest): Promise<LoginResponse> {
  return unwrapApiEnvelope(apiClient.post('/api/auth/login', data))
}

export function me(): Promise<UserResponse> {
  return unwrapApiEnvelope(apiClient.get('/api/auth/me'))
}

export function logout(): Promise<Record<string, unknown>> {
  return unwrapApiEnvelope(apiClient.post('/api/auth/logout'))
}

export function issueSseTicket(data: SseTicketRequest): Promise<SseTicketResponse> {
  return unwrapApiEnvelope(apiClient.post('/api/auth/sse-ticket', data))
}
