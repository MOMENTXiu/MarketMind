import { apiClient, unwrapApiEnvelope } from './client'
import type { AnalysisArtifactPayload } from './types'

export function getAnalysisArtifactPayload(
  projectId: string,
  artifactId: string
): Promise<AnalysisArtifactPayload> {
  return unwrapApiEnvelope(
    apiClient.get(
      `/api/analysis/projects/${encodeURIComponent(projectId)}/artifacts/${encodeURIComponent(artifactId)}/payload`
    )
  )
}
