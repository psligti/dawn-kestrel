import { useEffect } from 'react'
import { useCurrentSession as useCurrentSessionStore, useSetCurrentSession } from '../store'
import type { Session } from '../types/api'

/**
 * Hook to manage current session state with localStorage persistence
 * Provides functions to set and clear the current session
 */
export function useCurrentSession() {
  const currentSession = useCurrentSessionStore()
  const setCurrentSession = useSetCurrentSession()

  /**
   * Set current session
   */
  const setCurrent = (session: Session | null): void => {
    setCurrentSession(session)
  }

  /**
   * Clear current session
   */
  const clear = (): void => {
    setCurrentSession(null)
  }

  /**
   * Set current session from localStorage on mount
   */
  useEffect(() => {
    const saved = localStorage.getItem('currentSession')
    if (saved) {
      try {
        const session = JSON.parse(saved)
        setCurrent(session as Session)
      } catch (error) {
        console.error('Failed to parse saved session:', error)
        localStorage.removeItem('currentSession')
      }
    }
  }, [])

  /**
   * Persist current session to localStorage whenever it changes
   */
  useEffect(() => {
    const session = currentSession
    if (session) {
      localStorage.setItem('currentSession', JSON.stringify(session))
    } else {
      localStorage.removeItem('currentSession')
    }
  }, [currentSession])

  return {
    currentSession,
    setCurrent,
    clear,
  }
}
