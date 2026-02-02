import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { create } from 'zustand'
import { persist, devtools } from 'zustand/middleware'
import { useStore, useSessions, useCurrentSession, useTheme, usePalette, useDrawer, useComposer } from '../store'

describe('Zustand Store', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
  })

  afterEach(() => {
    // Clear localStorage after each test
    localStorage.clear()
  })

  describe('useStore', () => {
    it('should initialize with default state', () => {
      const { result } = renderHook(() => useStore())

      expect(result.current.sessions).toEqual([])
      expect(result.current.currentSession).toBeNull()
      expect(result.current.messages).toEqual({})
      expect(result.current.theme).toBe('dark')
      expect(result.current.paletteOpen).toBe(false)
      expect(result.current.drawerOpen).toBe(false)
      expect(result.current.drawerTab).toBe('todos')
      expect(result.current.composer.draft).toBe('')
      expect(result.current.composer.isSending).toBe(false)
    })

    it('should set theme successfully', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setTheme('light')
      })

      expect(result.current.theme).toBe('light')
    })

    it('should set sessions successfully', () => {
      const sessions = [
        { id: '1', title: 'Test Session', time_created: 1234567890, time_updated: 1234567890, message_count: 0 }
      ]

      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setSessions(sessions)
      })

      expect(result.current.sessions).toEqual(sessions)
    })

    it('should set current session successfully', () => {
      const session = { id: '1', title: 'Test Session', time_created: 1234567890, time_updated: 1234567890, message_count: 0 }

      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setCurrentSession(session)
      })

      expect(result.current.currentSession).toEqual(session)
    })

    it('should open palette successfully', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setPaletteOpen(true)
      })

      expect(result.current.paletteOpen).toBe(true)
    })

    it('should close palette successfully', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setPaletteOpen(false)
      })

      expect(result.current.paletteOpen).toBe(false)
    })

    it('should open drawer successfully', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setDrawerOpen(true)
      })

      expect(result.current.drawerOpen).toBe(true)
    })

    it('should close drawer successfully', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setDrawerOpen(false)
      })

      expect(result.current.drawerOpen).toBe(false)
    })

    it('should set drawer tab successfully', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setDrawerTab('agents')
      })

      expect(result.current.drawerTab).toBe('agents')
    })

    it('should set composer draft successfully', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setComposerDraft('Hello, world!')
      })

      expect(result.current.composer.draft).toBe('Hello, world!')
    })

    it('should set composer isSending state successfully', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setComposerSending(true)
      })

      expect(result.current.composer.isSending).toBe(true)
    })
  })

  describe('Persist middleware', () => {
    it('should save theme to localStorage on theme change', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setTheme('light')
      })

      expect(localStorage.getItem('theme')).toBe('light')
    })

    it('should load theme from localStorage on initialization', () => {
      localStorage.setItem('theme', 'light')

      const { result } = renderHook(() => useStore())

      expect(result.current.theme).toBe('light')
    })

    it('should save composer draft to localStorage', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setComposerDraft('Saved draft')
      })

      expect(localStorage.getItem('draft')).toBe('Saved draft')
    })

    it('should load composer draft from localStorage', () => {
      localStorage.setItem('draft', 'Loaded draft')

      const { result } = renderHook(() => useStore())

      expect(result.current.composer.draft).toBe('Loaded draft')
    })

    it('should clear persisted state when localStorage is cleared', () => {
      localStorage.setItem('theme', 'light')
      localStorage.setItem('draft', 'test')

      // Clear localStorage
      localStorage.clear()

      const { result } = renderHook(() => useStore())

      expect(result.current.theme).toBe('dark') // default
      expect(result.current.composer.draft).toBe('') // default
    })
  })

  describe('Typed hooks', () => {
    it('should useSessions hook return sessions array', () => {
      const sessions = [
        { id: '1', title: 'Session 1', time_created: 1234567890, time_updated: 1234567890, message_count: 0 }
      ]

      const { result } = renderHook(() => useStore(), {
        initialProps: { sessions }
      })

      const sessionsHook = useSessions()

      expect(sessionsHook).toEqual(sessions)
    })

    it('should useCurrentSession hook return current session', () => {
      const session = { id: '1', title: 'Session 1', time_created: 1234567890, time_updated: 1234567890, message_count: 0 }

      const { result } = renderHook(() => useStore(), {
        initialProps: { currentSession: session }
      })

      const currentSessionHook = useCurrentSession()

      expect(currentSessionHook).toEqual(session)
    })

    it('should useTheme hook return theme', () => {
      const { result } = renderHook(() => useStore())

      const themeHook = useTheme()

      expect(themeHook).toBe('dark')
    })

    it('should usePalette hook return paletteOpen state', () => {
      const { result } = renderHook(() => useStore())

      const paletteHook = usePalette()

      expect(paletteHook).toBe(false)
    })

    it('should useDrawer hook return drawerOpen state', () => {
      const { result } = renderHook(() => useStore())

      const drawerHook = useDrawer()

      expect(drawerHook.open).toBe(false)
      expect(drawerHook.tab).toBe('todos')
    })

    it('should useComposer hook return composer state', () => {
      const { result } = renderHook(() => useStore())

      const composerHook = useComposer()

      expect(composerHook.draft).toBe('')
      expect(composerHook.isSending).toBe(false)
    })
  })
})
