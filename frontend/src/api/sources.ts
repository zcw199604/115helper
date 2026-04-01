import { http } from './http'
import type { SourceFormInput, SyncSource } from '@/types/source'

function normalizePayload(input: SourceFormInput) {
  return {
    name: input.name,
    local_path: input.local_path,
    remote_path: input.remote_path,
    upload_mode: input.upload_mode,
    suffix_rules: input.suffix_rules,
    exclude_rules: input.exclude_rules,
    cron_expr: input.cron_expr.trim(),
    enabled: input.enabled,
    duplicate_check_mode: input.duplicate_check_mode,
    force_refresh_remote_cache: input.force_refresh_remote_cache,
  }
}

export async function listSources(): Promise<SyncSource[]> {
  const { data } = await http.get('/tasks')
  return data.data
}

export async function getSource(id: number): Promise<SyncSource | undefined> {
  const { data } = await http.get(`/tasks/${id}`)
  return data.data
}

export async function saveSource(input: SourceFormInput, id?: number) {
  const payload = normalizePayload(input)
  if (id) {
    const { data } = await http.put(`/sources/${id}`, payload)
    return data.data
  }
  const { data } = await http.post('/sources', payload)
  return data.data
}

export async function triggerSourceRun(id: number) {
  const { data } = await http.post(`/sources/${id}/run`)
  return data.data
}

export async function toggleTaskEnabled(id: number, enabled: boolean) {
  const { data } = await http.post(`/tasks/${id}/toggle`, { enabled })
  return data.data
}
