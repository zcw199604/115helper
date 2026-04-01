import { http } from './http'
import { mockSources } from './mockData'
import type { SourceFormInput, SyncSource } from '@/types/source'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

function normalizePayload(input: SourceFormInput) {
  return {
    name: input.name,
    local_path: input.local_path,
    remote_path: input.remote_path,
    upload_mode: input.upload_mode,
    suffix_rules: input.suffix_rules_text
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean),
    exclude_rules: input.exclude_rules_text
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean),
    cron_expr: input.cron_expr.trim(),
    enabled: input.enabled,
  }
}

export async function listSources(): Promise<SyncSource[]> {
  if (useMock) {
    return Promise.resolve(mockSources)
  }
  const { data } = await http.get('/tasks')
  return data.data
}

export async function getSource(id: number): Promise<SyncSource | undefined> {
  if (useMock) {
    return Promise.resolve(mockSources.find((item) => item.id === id))
  }
  const { data } = await http.get(`/tasks/${id}`)
  return data.data
}

export async function saveSource(input: SourceFormInput, id?: number) {
  const payload = normalizePayload(input)
  if (useMock) {
    return Promise.resolve({ id: id ?? Date.now(), ...payload })
  }
  if (id) {
    const { data } = await http.put(`/sources/${id}`, payload)
    return data.data
  }
  const { data } = await http.post('/sources', payload)
  return data.data
}

export async function triggerSourceRun(id: number) {
  if (useMock) {
    return Promise.resolve({ id: Date.now(), run_id: Date.now(), source_id: id, status: 'pending' })
  }
  const { data } = await http.post(`/sources/${id}/run`)
  return data.data
}

export async function toggleTaskEnabled(id: number, enabled: boolean) {
  if (useMock) {
    return Promise.resolve({ id, enabled })
  }
  const { data } = await http.post(`/tasks/${id}/toggle`, { enabled })
  return data.data
}
