import { useEffect, useState, useRef } from 'react'

interface WebSocketMessage {
  progress: number
  message?: string
  data?: any
}

export const useWebSocket = (scanId: string | null) => {
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState<string>('')
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!scanId) return

    const ws = new WebSocket(`ws://localhost:8000/ws/scan/${scanId}`)

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data)
        setProgress(data.progress || 0)
        if (data.message) {
          setMessage(data.message)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }

    wsRef.current = ws

    return () => {
      ws.close()
    }
  }, [scanId])

  return { progress, message }
}
