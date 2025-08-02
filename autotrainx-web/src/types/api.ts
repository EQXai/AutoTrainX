// API Response Types - Simplified for CLI Bridge

// Training Response from CLI execution
export interface TrainingResponse {
  success: boolean
  command: string
  job_id?: string
  output?: string
  error?: string
}

// Job information from database (read-only)
export interface JobInfo {
  job_id: string
  dataset_name?: string
  pipeline_mode: string
  preset: string
  status: string
  created_at: string
  start_time?: string
  end_time?: string
  success?: boolean
  error_message?: string
  progress_percentage?: number
}

// Job Statistics
export interface JobStatistics {
  total_jobs: number
  status_breakdown: Record<string, number>
  mode_breakdown: Record<string, number>
  success_rate: number
  jobs_last_24h: number
}

// Preset Statistics
export interface PresetStatistics {
  total_jobs: number
  successful_jobs: number
  success_rate: number
  avg_duration_minutes?: number
}

// List Response
export interface JobsListResponse {
  jobs: JobInfo[]
  total: number
  page: number
  page_size: number
}

// Running Jobs Response
export interface RunningJobsResponse {
  running_jobs: JobInfo[]
  count: number
}

// Statistics Response
export interface StatisticsResponse {
  job_statistics: JobStatistics
  preset_statistics: Record<string, PresetStatistics>
  recent_completions: JobInfo[]
}

// Training Request Types - Simplified
export interface SingleTrainingRequest {
  source_path: string
  preset?: string
  dataset_name?: string
  preview_count?: number
  generate_configs?: boolean
  auto_clean?: boolean
}

export interface DatasetConfig {
  source_path: string
  preset?: string
  dataset_name?: string
}

export interface BatchTrainingRequest {
  datasets: DatasetConfig[]
  strategy?: 'sequential' | 'parallel'
  auto_clean?: boolean
}

export interface VariationsTrainingRequest {
  dataset_name: string
  base_preset: string
  variations: Record<string, any[]>
  auto_clean?: boolean
}

// Legacy types kept for compatibility
export enum JobStatus {
  PENDING = 'pending',
  IN_QUEUE = 'in_queue',
  PREPARING_DATASET = 'preparing_dataset',
  CONFIGURING_PRESET = 'configuring_preset',
  READY_FOR_TRAINING = 'ready_for_training',
  TRAINING = 'training',
  GENERATING_PREVIEW = 'generating_preview',
  DONE = 'done',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum PipelineMode {
  SINGLE = 'single',
  BATCH = 'batch',
  VARIATIONS = 'variations',
}

// Progress Update (WebSocket)
export interface ProgressUpdate {
  job_id: string
  status: JobStatus
  progress_percentage: number
  current_step: string
  completed_steps: number
  total_steps: number
  message: string
}

// Dataset Types (kept for compatibility)
export interface Dataset {
  name: string
  path: string
  total_images: number
  total_texts: number
  has_sample_prompts: boolean
  created_at?: string
  size_mb?: number
}

// Preset Types (kept for compatibility)
export interface Preset {
  name: string
  description: string
  category: string
  architecture?: string
  config_files: string[]
  parameters?: Record<string, any>
}

// Generic API Response (kept for compatibility)
export interface ApiResponse<T = any> {
  success: boolean
  message: string
  timestamp?: string
  data?: T
  error_code?: string
  details?: any
}

// Paginated Response (kept for compatibility)
export interface PaginatedResponse<T> {
  items: T[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
}