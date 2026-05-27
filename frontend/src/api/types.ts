export interface ApiEnvelope<T> {
  success: boolean
  data: T
}

export interface ApiRef {
  id: string
  type?: string
  sidecar_type?: string
  name?: string
  url?: string | null
  project_id?: string
  job_id?: string
  storage_key?: string
  metadata?: Record<string, unknown>
  created_at?: string | null
}

export interface AnalysisArtifactPayload {
  project_id: string
  artifact: ApiRef
  payload_type: 'table' | 'json' | 'markdown' | string
  rows: Array<Record<string, unknown>>
  payload?: unknown
  content?: string | null
}

export type RetailProjectStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'needs_review'
export type LegacyRetailProjectStatus = '待处理' | '处理中' | '已完成' | '失败'
export type RetailStageName =
  | 'dataset_preparation'
  | 'feature_engineering'
  | 'segmentation'
  | 'association'
  | 'recommendation'
  | 'marketer_insights'
  | 'report'
export type StageStatus = 'queued' | 'processing' | 'completed' | 'skipped' | 'failed'

export interface RetailStage {
  stage: RetailStageName | string
  status: StageStatus | string
  error?: string | null
  artifact_refs?: ApiRef[]
}

export interface RetailRecommendation {
  customer_id?: string
  item: string
  score: number
  reason?: string
  score_breakdown?: Record<string, unknown>
}

export type RetailMarketerInsights = Record<string, Array<Record<string, unknown>>>

export interface RetailProject {
  id: string
  name: string
  description?: string
  analysis_kind?: string | null
  status: RetailProjectStatus | LegacyRetailProjectStatus | string
  dataset_ref?: ApiRef | null
  dataset_filename?: string | null
  quality_summary?: Record<string, unknown>
  artifact_refs?: ApiRef[]
  recommendations?: RetailRecommendation[]
  marketer_insights?: RetailMarketerInsights
  stage_statuses?: RetailStage[]
  summary?: Record<string, unknown>
  job_id?: string | null
  trace_id?: string | null
  error?: string | null
  error_message?: string | null
  created_at?: string | null
  updated_at?: string | null
  results?: RetailLegacyResults
}

export interface RetailLegacyResults {
  association_rules?: Array<Record<string, unknown>>
  prediction_data?: Record<string, unknown>
  clustering_data?: Record<string, unknown>
  report_path?: string
}

export interface RetailProjectList {
  projects: RetailProject[]
}

export interface AnalysisSseEvent {
  event_id?: string | null
  event: string
  resource: 'retail_project' | 'data_processing_job' | string
  resource_id: string
  project_id?: string | null
  job_id?: string | null
  trace_id?: string | null
  status?: string | null
  stage?: string | null
  payload?: Record<string, unknown>
  fallback_url?: string | null
  occurred_at?: string | null
  heartbeat?: boolean
  retry_ms?: number | null
  terminal?: boolean
}

export interface RetailRecommendationsResponse {
  project_id?: string
  recommendations: RetailRecommendation[]
}

export type DataProcessingJobStatus =
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'needs_review'

export type DataProcessingStageName =
  | 'dataset_regularization'
  | 'overview'
  | 'profile_segmentation'
  | 'association'
  | 'recommendation'
  | 'promotion'
  | 'summary'

export type DataProcessingStageStatus = StageStatus | 'needs_review'

export interface DataProcessingStage {
  stage: DataProcessingStageName | string
  status: DataProcessingStageStatus | string
  error?: string | null
  artifact_refs?: ApiRef[]
}

export interface RegularizationQuality {
  raw_rows?: number
  normalized_rows?: number
  duplicate_rows_removed?: number
  mapped_field_count?: number
  available_standard_fields?: string[]
  missing_rates?: Record<string, number | null>
  invalid_date_count?: number | null
  invalid_amount_count?: number | null
  invalid_user_id_count?: number | null
  return_rows?: number
  scores?: Record<string, number>
  analysis_ready_score?: number
  grade?: string
}

export interface RegularizationCapability {
  can_run_sales_stats?: boolean
  can_run_time_trend?: boolean
  can_run_customer_profile?: boolean
  can_run_association?: boolean
  can_run_recommendation?: boolean
  can_run_forecast?: boolean
  can_run_promotion_analysis?: boolean
  can_run_profit_analysis?: boolean
  can_run_price_sensitivity?: boolean
  can_run_discount_analysis?: boolean
  degraded_fields?: Record<string, string>
  capability_zh?: Record<string, boolean>
  runnable_count?: number
  [key: string]: unknown
}

export interface DataProcessingJob {
  job_id: string
  project_id: string
  name: string
  status: DataProcessingJobStatus | string
  stages: DataProcessingStage[]
  quality?: RegularizationQuality | null
  capability?: RegularizationCapability | null
  output_refs?: ApiRef[]
  skipped_reasons?: Record<string, string>
  error?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface DataProcessingOutputsResponse {
  project_id: string
  job_id: string
  outputs: ApiRef[]
}

export type DataProcessingSidecarId =
  | 'sidecar:schema_mapping_detail'
  | 'sidecar:quality_report'
  | 'sidecar:capability'
  | 'sidecar:manifest'
  | 'sidecar:preview_rows'

export interface CustomerSuggestionRequest {
  data: Record<string, unknown>
  llm_config?: Record<string, string | null | undefined>
}

export interface CustomerSuggestionResponse {
  success: boolean
  text: string
  metadata?: Record<string, unknown>
}

export interface HealthResponse {
  status: string
  service?: string
  version?: string
  [key: string]: unknown
}

export interface StatusConfig {
  color: string
  label: string
}

export function normalizeRetailProjectStatus(status: string | undefined | null): RetailProjectStatus | 'unknown' {
  const map: Record<string, RetailProjectStatus> = {
    queued: 'queued',
    processing: 'processing',
    completed: 'completed',
    failed: 'failed',
    needs_review: 'needs_review',
    待处理: 'queued',
    处理中: 'processing',
    已完成: 'completed',
    失败: 'failed'
  }
  return status ? map[status] ?? 'unknown' : 'unknown'
}

export function getRetailProjectStatusConfig(status: string | undefined | null): StatusConfig {
  const map: Record<RetailProjectStatus | 'unknown', StatusConfig> = {
    queued: { color: '#9CA3AF', label: '待处理' },
    processing: { color: '#F59E0B', label: '进行中' },
    completed: { color: '#10B981', label: '已完成' },
    failed: { color: '#EF4444', label: '失败' },
    needs_review: { color: '#F97316', label: '需审查' },
    unknown: { color: '#9CA3AF', label: status || '未知' }
  }
  return map[normalizeRetailProjectStatus(status)]
}

export function isActiveRetailProjectStatus(status: string | undefined | null): boolean {
  const normalized = normalizeRetailProjectStatus(status)
  return normalized === 'processing'
}

export function isTerminalDataProcessingStatus(status: string | undefined | null): boolean {
  return status === 'completed' || status === 'failed' || status === 'needs_review'
}
