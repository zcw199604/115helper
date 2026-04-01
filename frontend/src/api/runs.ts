import { http } from './http'
import type { JobRun, RunDetail, TaskLogRecord } from '@/types/run'


export async function listRuns(): Promise<JobRun[]> {
  const { data } = await http.get('/runs')
  return data.data
}

export async function getRunDetail(id: number): Promise<RunDetail | undefined> {
  const [detailResponse, logsResponse] = await Promise.all([http.get(`/runs/${id}`), http.get(`/runs/${id}/logs`)])
  return { ...detailResponse.data.data, logs: logsResponse.data.data }
}

export async function listRunLogs(id: number): Promise<TaskLogRecord[]> {
  const { data } = await http.get(`/runs/${id}/logs`)
  return data.data
}

export async function retryRun(id: number) {
  const { data } = await http.post(`/runs/${id}/retry`)
  return data.data
}

export async function cancelRun(id: number) {
  const { data } = await http.post(`/runs/${id}/cancel`)
  return data.data
}
