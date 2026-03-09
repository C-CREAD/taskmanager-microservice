import { useEffect, useRef, useCallback } from 'react'
import { createWebSocket } from '../api/notifications'

export function useWebSocket(onNotification) {
  const wsRef        = useRef(null)
  const reconnectRef = useRef(null)
  const mountedRef   = useRef(true)

  const connect = useCallback(() => {
    const token = localStorage.getItem('access_token')
    if (!token || !mountedRef.current) return

    const ws = createWebSocket(token, onNotification)

    ws.onclose = () => {
      if (!mountedRef.current) return
      // Reconnect after 3 seconds
      reconnectRef.current = setTimeout(connect, 3000)
    }

    wsRef.current = ws
  }, [onNotification])

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return wsRef
}
