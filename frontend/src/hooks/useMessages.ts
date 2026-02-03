import { useAddMessage } from '../store'
import { fetchApi } from './useApiClient'
import type { Message, MessageRole } from '../types/api'

/**
 * Hook to manage messages with API integration
 * Provides functions to fetch and add messages
 */
export function useMessages() {
  const addMessage = useAddMessage()

  /**
   * Fetch messages for a session from the API
   */
  const fetchMessages = async (sessionId: string): Promise<void> => {
    try {
      const messages = await fetchApi<Message[]>(`/sessions/${sessionId}/messages`)
      messages.forEach((msg) => addMessage(sessionId, msg))
    } catch (error) {
      console.error('Failed to fetch messages:', error)
      throw error
    }
  }

  /**
   * Add a new message to a session
   */
  const addMessageToSession = async (
    sessionId: string,
    message: Omit<Message, 'id' | 'time'> & { time: Record<string, unknown> }
  ): Promise<Message> => {
    try {
      const newMessage = await fetchApi<Message>(`/sessions/${sessionId}/messages`, {
        method: 'POST',
        body: JSON.stringify(message),
      })
      addMessage(sessionId, newMessage)
      return newMessage
    } catch (error) {
      console.error('Failed to add message:', error)
      throw error
    }
  }

  /**
   * Create a user message
   */
  const createUserMessage = async (
    sessionId: string,
    text: string
  ): Promise<Message> => {
    const message: Omit<Message, 'id' | 'time' | 'metadata'> & {
      time: Record<string, unknown>
      metadata?: Record<string, unknown>
    } = {
      role: 'user',
      session_id: sessionId,
      text,
      time: {},
      metadata: {},
    }

    return addMessageToSession(sessionId, message)
  }

  /**
   * Create an assistant message
   */
  const createAssistantMessage = async (
    sessionId: string,
    text: string,
    parts: any[] = []
  ): Promise<Message> => {
    const message: Omit<Message, 'id' | 'time' | 'role' | 'metadata'> & {
      time: Record<string, unknown>
      role: MessageRole
      metadata?: Record<string, unknown>
    } = {
      role: 'assistant',
      session_id: sessionId,
      text,
      time: {},
      metadata: {},
      parts,
    }

    return addMessageToSession(sessionId, message)
  }

  /**
   * Create a system message
   */
  const createSystemMessage = async (
    sessionId: string,
    text: string
  ): Promise<Message> => {
    const message: Omit<Message, 'id' | 'time' | 'metadata'> & {
      time: Record<string, unknown>
      metadata?: Record<string, unknown>
    } = {
      role: 'system',
      session_id: sessionId,
      text,
      time: {},
      metadata: {},
    }

    return addMessageToSession(sessionId, message)
  }

  return {
    fetchMessages,
    addMessageToSession,
    createUserMessage,
    createAssistantMessage,
    createSystemMessage,
  }
}
