import { apiClient, createEventSourceWithTicket, unwrapApiEnvelope } from './client'
import type {
  AnalysisArtifactPayload,
  ApiRef,
  RetailMarketerInsights,
  RetailProject,
  RetailProjectList,
  RetailRecommendationsResponse
} from './types'

export interface RetailProjectCreatePayload {
  name: string
  description?: string
  analysis_kind?: string
}

export interface RetailRecommendationParams {
  customer_id?: string
  top_k?: number
}

export function createRetailProject(payload: RetailProjectCreatePayload): Promise<RetailProject> {
  return unwrapApiEnvelope(apiClient.post('/api/analysis/projects', payload))
}

export function listRetailProjects(): Promise<RetailProjectList> {
  return unwrapApiEnvelope(apiClient.get('/api/analysis/projects'))
}

export function getRetailProject(projectId: string): Promise<RetailProject> {
  return unwrapApiEnvelope(apiClient.get(`/api/analysis/projects/${encodeURIComponent(projectId)}`))
}

export function deleteRetailProject(projectId: string): Promise<Record<string, unknown>> {
  return unwrapApiEnvelope(apiClient.delete(`/api/analysis/projects/${encodeURIComponent(projectId)}`))
}

export function uploadRetailDataset(projectId: string, file: File): Promise<RetailProject> {
  const formData = new FormData()
  formData.append('file', file)
  return unwrapApiEnvelope(apiClient.post(`/api/analysis/projects/${encodeURIComponent(projectId)}/dataset`, formData))
}

export function runRetailAnalysis(projectId: string): Promise<RetailProject> {
  return unwrapApiEnvelope(apiClient.post(`/api/analysis/projects/${encodeURIComponent(projectId)}/run`))
}

export async function openRetailProjectEvents(projectId: string): Promise<EventSource> {
  return createEventSourceWithTicket(`/api/analysis/projects/${encodeURIComponent(projectId)}/events`, {
    resource_type: 'project',
    resource_id: projectId,
    project_id: projectId,
    stream_type: 'retail-analysis',
  })
}

export function listRetailArtifacts(projectId: string): Promise<{ artifacts: ApiRef[] } | ApiRef[]> {
  return unwrapApiEnvelope(apiClient.get(`/api/analysis/projects/${encodeURIComponent(projectId)}/artifacts`))
}

export function getRetailArtifactPayload(
  projectId: string,
  artifactId: string
): Promise<AnalysisArtifactPayload> {
  return unwrapApiEnvelope(
    apiClient.get(
      `/api/analysis/projects/${encodeURIComponent(projectId)}/artifacts/${encodeURIComponent(artifactId)}/payload`
    )
  )
}

export function listRetailRecommendations(
  projectId: string,
  params: RetailRecommendationParams = {}
): Promise<RetailRecommendationsResponse> {
  return unwrapApiEnvelope(apiClient.get(`/api/analysis/projects/${encodeURIComponent(projectId)}/recommendations`, { params }))
}

export function getRetailMarketerInsights(projectId: string): Promise<RetailMarketerInsights> {
  return unwrapApiEnvelope(apiClient.get(`/api/analysis/projects/${encodeURIComponent(projectId)}/marketer-insights`))
}
