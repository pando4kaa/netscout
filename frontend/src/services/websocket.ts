/**
 * WebSocket for real-time scan progress.
 * Connects to ws://host/api/ws/scan, sends {domain}, receives progress and results.
 */

export interface ScanProgressMessage {
  stage: string
  progress: number
  message?: string
}

export interface ScanDoneMessage {
  stage: 'done'
  progress: number
  scan_id: string
  results: Record<string, unknown>
  saved?: boolean
}

export type ScanWsMessage = ScanProgressMessage | ScanDoneMessage

export function isDoneMessage(msg: ScanWsMessage): msg is ScanDoneMessage {
  return msg.stage === 'done'
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const getWsUrl = () => {
  const wsBase = API_BASE.replace(/^http/, 'ws')
  return `${wsBase}/api/ws/scan`
}

export interface ScanWebSocketCallbacks {
  onProgress?: (progress: number, message: string) => void
  onDone?: (scanId: string, results: Record<string, unknown>, saved?: boolean) => void
  onError?: (error: string) => void
}

export function runScanViaWebSocket(
  domain: string,
  callbacks: ScanWebSocketCallbacks,
  token?: string | null
): () => void {
  const wsUrl = getWsUrl()
  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    const payload: { domain: string; token?: string } = { domain }
    if (token) payload.token = token
    ws.send(JSON.stringify(payload))
  }

  ws.onmessage = (event) => {
    try {
      const data: ScanWsMessage = JSON.parse(event.data)
      if (data.error) {
        callbacks.onError?.(data.error as unknown as string)
        ws.close()
        return
      }
      if (isDoneMessage(data)) {
        callbacks.onDone?.(data.scan_id, data.results, (data as { saved?: boolean }).saved)
        ws.close()
      } else {
        callbacks.onProgress?.(data.progress, data.message || '')
      }
    } catch (e) {
      callbacks.onError?.('Invalid response')
    }
  }

  ws.onerror = () => {
    callbacks.onError?.('WebSocket connection failed')
  }

  ws.onclose = () => {}

  return () => ws.close()
}
