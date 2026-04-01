export type RunStatus = 'pending' | 'running' | 'success' | 'partial_failed' | 'failed' | 'cancelled'
export type LogLevel = 'debug' | 'info' | 'warning' | 'error'

export interface RunSummary {
  total_files: number
  fast_uploaded: number
  multipart_uploaded: number
  skipped: number
  failed: number
}

export interface JobRun {
  id: number
  source_id: number
  source_name: string
  trigger_type: 'manual' | 'cron' | 'retry'
  status: RunStatus
  started_at: string
  finished_at?: string | null
  summary: RunSummary
  error_message?: string | null
}

export interface FileRecord {
  id: number
  relative_path: string
  file_size: number
  suffix: string
  action: 'skipped' | 'fast_uploaded' | 'multipart_uploaded' | 'failed'
  message?: string | null
  synced_at: string
}

export interface TaskLogRecord {
  id: number
  source_id: number
  run_id: number
  level: LogLevel
  stage: string
  message: string
  created_at: string
}

export interface RunDetail extends JobRun {
  records: FileRecord[]
  logs: TaskLogRecord[]
}
