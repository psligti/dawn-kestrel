import { useEffect } from 'react'
import { useSessions as useSessionsStore, useSetCurrentSession } from '../store'
import type { Session } from '../types/api'
import { fetchApi, deleteApi, postApi } from './useApiClient'

/**
 * Hook to manage sessions with API integration
 * Provides functions to fetch, create, and delete sessions
 */
export function useSessions() {
  const setSessions = useSessionsStore((state) => state.setSessions)
  const setCurrentSession = useSetCurrentSession()

  /**
   * Fetch all sessions from API
   */
  const fetchSessions = async (): Promise<void> => {
    try {
      const sessions = await fetchApi<Session[]>('/sessions')
      setSessions(sessions)
    } catch (error) {
      console.error('Failed to fetch sessions:', error)
      throw error
    }
  }

  /**
   * Create a new session
   */
  const createSession = async (title: string = 'New Session'): Promise<Session> => {
    try {
      const session = await postApi<Session>('/sessions', { title })
      setSessions((prev) => [session, ...prev])
      return session
    } catch (error) {
      console.error('Failed to create session:', error)
      throw error
    }
  }

  /**
   * Delete a session by ID
   */
  const deleteSession = async (sessionId: string): Promise<void> => {
    try {
      await deleteApi(`/sessions/${sessionId}`)
      setSessions((prev) => prev.filter((s) => s.id !== sessionId))
      setCurrentSession(null)
    } catch (error) {
      console.error('Failed to delete session:', error)
      throw error
    }
  }

  // Load sessions on mount
  useEffect(() => {
    fetchSessions()
  }, [])

  return {
    fetchSessions,
    createSession,
    deleteSession,
  }
}
