import { http } from './http'
import { mockRunDetails, mockRuns } from './mockData'
import type { JobRun, RunDetail, TaskLogRecord } from '@/types/run'

const useMock = import.meta.env.VITE_USE_MOCK !== 'false'

export async function listRuns(): Promise<JobRun[]> {
  if (useMock) {
    return Promise.resolve(mockRuns)
  }
  const { data } = await http.get('/runs')
  return data.data
}

export async function getRunDetail(id: number): Promise<RunDetail | undefined> {
  if (useMock) {
    return Promise.resolve(mockRunDetails.find((item) => item.id === id))
  }
  const [detailResponse, logsResponse] = await Promise.all([http.get(`/runs/${id}`), http.get(`/runs/${id}/logs`)])
  return { ...detailResponse.data.data, logs: logsResponse.data.data }
}

export async function listRunLogs(id: number): Promise<TaskLogRecord[]> {
  if (useMock) {
    return Promise.resolve(mockRunDetails.find((item) => item.id === id)?.logs ?? [])
  }
  const { data } = await http.get(`/runs/${id}/logs`)
  return data.data
}

export async function retryRun(id: number) {
  if (useMock) {
    return Promise.resolve({ id: Date.now(), run_id: Date.now(), retry_of: id, status: 'pending' })
  }
  const { data } = await http.post(`/runs/${id}/retry`)
  return data.data
}

export async function cancelRun(id: number) {
  if (useMock) {
    return Promise.resolve({ run_id: id, status: 'cancelled' })
  }
  const { data } = await http.post(`/runs/${id}/cancel`)
  return data.data
}
