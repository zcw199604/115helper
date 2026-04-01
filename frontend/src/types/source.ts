export type UploadMode = 'fast_only' | 'fast_then_multipart' | 'multipart_only'
export type DuplicateCheckMode = 'none' | 'name' | 'sha1'
export type RunStatus = 'pending' | 'running' | 'success' | 'partial_failed' | 'failed' | 'cancelled'

export interface TaskScheduleState {
  is_scheduled: boolean
  next_run_time?: string | null
  last_run_at?: string | null
  last_run_status?: RunStatus | null
}

export interface SyncSource {
  id: number
  name: string
  local_path: string
  remote_path: string
  upload_mode: UploadMode
  suffix_rules: string[]
  exclude_rules: string[]
  cron_expr?: string | null
  enabled: boolean
  duplicate_check_mode: DuplicateCheckMode
  force_refresh_remote_cache: boolean
  updated_at: string
  schedule_state?: TaskScheduleState
}

export interface SourceFormInput {
  name: string
  local_path: string
  remote_path: string
  upload_mode: UploadMode
  suffix_rules: string[]
  exclude_rules: string[]
  cron_expr: string
  enabled: boolean
  duplicate_check_mode: DuplicateCheckMode
  force_refresh_remote_cache: boolean
}
