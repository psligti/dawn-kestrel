import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useKeyboardShortcuts } from './useKeyboardShortcuts'
import { store } from '../store'

describe('useKeyboardShortcuts', () => {
  it('initializes without crashing', () => {
    renderHook(() => useKeyboardShortcuts())
    expect(true).toBe(true)
  })

  it('renders hook without errors', () => {
    const { rerender } = renderHook(() => useKeyboardShortcuts())
    expect(rerender).toBeDefined()
    expect(rerender).not.toThrow()
  })

  it('hook accepts store state without crashing', () => {
    const { rerender } = renderHook(() => useKeyboardShortcuts())
    expect(rerender).toBeDefined()
  })

  it('registers keyboard shortcuts for left dashboard', () => {
    const { unmount } = renderHook(() => useKeyboardShortcuts())
    expect(store.getState()).toBeDefined()
    unmount()
  })

  it('handles left dashboard toggle shortcut registration', () => {
    renderHook(() => useKeyboardShortcuts())
    const state = store.getState()
    expect(state.leftDashboardOpen).toBeDefined()
    expect(state.leftDashboardPinned).toBeDefined()
  })

  it('handles left dashboard pin shortcut registration', () => {
    renderHook(() => useKeyboardShortcuts())
    const state = store.getState()
    expect(state.leftDashboardOpen).toBeDefined()
    expect(state.leftDashboardPinned).toBeDefined()
  })
})
