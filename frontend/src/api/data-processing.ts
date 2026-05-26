import { apiClient, unwrapApiEnvelope } from './client'
import type {
  ApiRef,
  DataProcessingJob,
  DataProcessingOutputsResponse,
  DataProcessingSidecarId
} from './types'

export interface DataProcessingJobCreatePayload {
  project_id: string
  name: string
}

export function createDataProcessingJob(payload: DataProcessingJobCreatePayload): Promise<DataProcessingJob> {
  return unwrapApiEnvelope(apiClient.post('/api/analysis/jobs', payload))
}

export function uploadRawDataset(projectId: string, jobId: string, file: File): Promise<DataProcessingJob> {
  const formData = new FormData()
  formData.append('file', file)
  return unwrapApiEnvelope(
    apiClient.post(`/api/analysis/jobs/${encodeURIComponent(jobId)}/raw-dataset`, formData, {
      params: { project_id: projectId }
    })
  )
}

export function regularizeDataProcessingJob(projectId: string, jobId: string): Promise<DataProcessingJob> {
  return unwrapApiEnvelope(
    apiClient.post(`/api/analysis/jobs/${encodeURIComponent(jobId)}/regularize`, undefined, {
      params: { project_id: projectId }
    })
  )
}

export function runDataProcessingJob(projectId: string, jobId: string): Promise<DataProcessingJob> {
  return unwrapApiEnvelope(
    apiClient.post(`/api/analysis/jobs/${encodeURIComponent(jobId)}/run`, undefined, {
      params: { project_id: projectId }
    })
  )
}

export function getDataProcessingJob(projectId: string, jobId: string): Promise<DataProcessingJob> {
  return unwrapApiEnvelope(
    apiClient.get(`/api/analysis/jobs/${encodeURIComponent(jobId)}`, {
      params: { project_id: projectId }
    })
  )
}

export function listDataProcessingOutputs(
  projectId: string,
  jobId: string
): Promise<DataProcessingOutputsResponse> {
  return unwrapApiEnvelope(
    apiClient.get(`/api/analysis/jobs/${encodeURIComponent(jobId)}/outputs`, {
      params: { project_id: projectId }
    })
  )
}

export function getDataProcessingDatasetRef(
  projectId: string,
  jobId: string,
  datasetId: string
): Promise<ApiRef> {
  return unwrapApiEnvelope(
    apiClient.get(`/api/analysis/jobs/${encodeURIComponent(jobId)}/datasets/${encodeURIComponent(datasetId)}`, {
      params: { project_id: projectId }
    })
  )
}

export function getDataProcessingSidecar(
  projectId: string,
  jobId: string,
  sidecarId: DataProcessingSidecarId
): Promise<Record<string, unknown>> {
  return unwrapApiEnvelope(
    apiClient.get(`/api/analysis/jobs/${encodeURIComponent(jobId)}/sidecars/${encodeURIComponent(sidecarId)}`, {
      params: { project_id: projectId }
    })
  )
}