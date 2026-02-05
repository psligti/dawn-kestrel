import { useEffect, useRef } from 'react'
import { getApi } from './useApiClient'
import { useSetTelemetry } from '../store'
import type { TelemetryData } from '../store'

/**
 * SSE event types from the backend for session updates
 */
type SessionSSEEventType =
  | 'session_theme'
  | 'telemetry'
  | 'ping'

/**
 * SSE event data structure for session updates
 */
interface SessionSSEEvent {
  type: SessionSSEEventType
  session_id?: string
  theme_id?: string
  telemetry?: TelemetryData
}

/**
 * Hook options for session telemetry stream connection
 */
export interface UseSessionTelemetryStreamOptions {
  sessionId: string
  maxRetries?: number
}

/**
 * Hook to subscribe to session telemetry updates via SSE streaming
 * Manages connection, reconnection with exponential backoff, and event handling
 * Refetches the telemetry snapshot on reconnect to avoid stale state
 */
export function useSessionTelemetryStream(options: UseSessionTelemetryStreamOptions) {
  const {
    sessionId,
    maxRetries = 5,
  } = options

  const eventSourceRef = useRef<EventSource | null>(null)
  const retryCountRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isConnectingRef = useRef(false)
  const setTelemetry = useSetTelemetry()

  /**
   * Fetch the current telemetry snapshot from API
   * Used on reconnect to avoid stale telemetry state
   */
  const refetchTelemetry = async () => {
    try {
      const response = await getApi<TelemetryData>(`/sessions/${sessionId}/telemetry`)
      setTelemetry(response)
      console.log('Refetched telemetry snapshot:', response)
    } catch (error) {
      console.error('Failed to refetch telemetry snapshot:', error)
    }
  }

  /**
   * Connect to SSE endpoint with exponential backoff reconnection
   */
  const connect = () => {
    if (eventSourceRef.current || isConnectingRef.current) {
      return
    }

    isConnectingRef.current = true
    retryCountRef.current = 0

    const sseUrl = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}/sessions/${sessionId}/stream`

    try {
      const eventSource = new EventSource(sseUrl)
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        isConnectingRef.current = false
        retryCountRef.current = 0
        console.log('Session telemetry SSE connected:', sseUrl)

        refetchTelemetry()
      }

      eventSource.onmessage = (event) => {
        try {
          const data: SessionSSEEvent = JSON.parse(event.data)

          switch (data.type) {
            case 'telemetry':
              if (data.session_id === sessionId && data.telemetry) {
                setTelemetry(data.telemetry)
                console.log('Telemetry updated:', data.telemetry)
              }
              break

            case 'session_theme':
              break

            case 'ping':
              break
          }
        } catch (error) {
          console.error('Failed to parse SSE event:', error)
        }
      }

      eventSource.onerror = (error) => {
        console.error('Session telemetry SSE connection error:', error)
        isConnectingRef.current = false

        if (eventSourceRef.current) {
          eventSourceRef.current.close()
          eventSourceRef.current = null
        }

        if (retryCountRef.current < maxRetries) {
          const retryDelay = Math.pow(2, retryCountRef.current) * 1000

          reconnectTimeoutRef.current = setTimeout(() => {
            retryCountRef.current++
            console.log(`Attempting session telemetry SSE reconnection (attempt ${retryCountRef.current}/${maxRetries})`)
            connect()
          }, retryDelay)
        } else {
          console.error('Max session telemetry SSE reconnection attempts reached')
        }
      }
    } catch (error) {
      isConnectingRef.current = false
      console.error('Failed to connect to session telemetry SSE stream:', error)
    }
  }

  /**
   * Disconnect SSE connection
   */
  const disconnect = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    isConnectingRef.current = false
  }

  useEffect(() => {
    if (!sessionId) return

    connect()

    return () => {
      disconnect()
    }
  }, [sessionId])

  return {
    connect,
    disconnect,
  }
}
