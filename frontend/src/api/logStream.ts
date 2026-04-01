import type { TaskLogRecord } from '@/types/run'

export interface LogStreamHandlers {
  onLog?: (log: TaskLogRecord) => void
  onStatus?: (status: string) => void
  onOpen?: () => void
  onError?: () => void
}

export interface LogStreamClient {
  close: () => void
}


export function subscribeRunLogStream(runId: number, handlers: LogStreamHandlers): LogStreamClient {
  const eventSource = new EventSource(`/api/v1/runs/${runId}/logs/stream`)
  eventSource.addEventListener('open', () => {
    handlers.onOpen?.()
  })
  eventSource.addEventListener('log', (event) => {
    const data = JSON.parse((event as MessageEvent).data) as TaskLogRecord
    handlers.onLog?.(data)
  })
  eventSource.addEventListener('status', (event) => {
    const data = JSON.parse((event as MessageEvent).data) as { status: string }
    handlers.onStatus?.(data.status)
  })
  eventSource.addEventListener('heartbeat', () => {
    handlers.onStatus?.('heartbeat')
  })
  eventSource.onerror = () => {
    handlers.onError?.()
  }
  return {
    close: () => eventSource.close(),
  }
}
