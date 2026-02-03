import { useEffect, useRef, useState } from 'react'
import { MessageCard } from './MessageCard'
import { TopBar } from './TopBar'
import { StatusBar } from './StatusBar'
import { Message } from '../types/api'

interface ConversationTimelineProps {
  sessionId: string
  autoScroll?: boolean
  onRun?: () => void
  onStop?: () => void
}

export function ConversationTimeline({ sessionId, autoScroll = true, onRun, onStop }: ConversationTimelineProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const addMessageRef = useRef((msg: Message) => setMessages(prev => [...prev, msg]))
  const sessionIdRef = useRef(sessionId)

  // Update refs when values change
  useEffect(() => {
    sessionIdRef.current = sessionId
    addMessageRef.current = (msg: Message) => setMessages(prev => [...prev, msg])
  }, [sessionId])

  useEffect(() => {
    const token = sessionIdRef.current
    const sseUrl = `http://localhost:8000/api/v1/tasks/${token}/stream`
    let eventSource: EventSource | null = null

    try {
      eventSource = new EventSource(sseUrl)
      setIsLoading(true)

      eventSource.onopen = () => {
        setIsConnected(true)
        setIsLoading(false)
        console.log('SSE connected:', sseUrl)
      }

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'message') {
            const newMessage: Message = {
              id: data.id || `msg-${Date.now()}`,
              session_id: sessionIdRef.current,
              role: data.role as 'user' | 'assistant' | 'system',
              text: data.content || '',
              parts: [],
              timestamp: Date.now(),
            }
            addMessageRef.current(newMessage)
            if (autoScroll && containerRef.current) {
              containerRef.current.scrollTop = containerRef.current.scrollHeight
            }
          }
        } catch (error) {
          console.error('Failed to parse SSE event:', error)
        }
      }

      eventSource.onerror = () => {
        console.error('SSE connection error')
        setIsLoading(false)
        setIsConnected(false)
        if (eventSource) {
          eventSource.close()
          eventSource = null
        }
      }

      return () => {
        if (eventSource) {
          eventSource.close()
          eventSource = null
        }
      }
    } catch (error) {
      console.error('Failed to create EventSource:', error)
      setIsLoading(false)
    }
  }, [])

  return (
    <>
      <TopBar onRun={onRun} onStop={onStop} />
      <div
        ref={containerRef}
        className="timeline-container"
        data-connected={isConnected}
        data-loading={isLoading}
      >
        {isLoading && !isConnected && <div className="timeline-loading">Connecting to stream...</div>}
        {messages.length === 0 && !isLoading && <div className="timeline-empty">No messages yet. Start a conversation!</div>}
        {messages.length > 0 && (
          <div className="timeline-messages">
            {messages.map((message) => (
              <div key={message.id} className="timeline-message">
                <MessageCard message={message} />
              </div>
            ))}
          </div>
        )}
      </div>
      <StatusBar />
    </>
  )
}
