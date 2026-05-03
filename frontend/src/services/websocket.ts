/**
 * WebSocket for real-time scan progress.
 * Connects to ws://host/api/ws/scan, sends {domain}, receives progress and results.
 */

import i18n from '../i18n'

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

export interface ScanErrorMessage {
  stage?: 'error'
  error: string
}

export type ScanWsMessage = ScanProgressMessage | ScanDoneMessage | ScanErrorMessage

export function isDoneMessage(msg: ScanWsMessage): msg is ScanDoneMessage {
  return msg.stage === 'done'
}

function isErrorMessage(msg: ScanWsMessage): msg is ScanErrorMessage {
  return 'error' in msg
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
      if (isErrorMessage(data)) {
        callbacks.onError?.(data.error)
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
      callbacks.onError?.(i18n.t('errors.wsInvalidResponse'))
    }
  }

  ws.onerror = () => {
    callbacks.onError?.(i18n.t('errors.wsConnectionFailed'))
  }

  ws.onclose = () => {}

  return () => ws.close()
}
