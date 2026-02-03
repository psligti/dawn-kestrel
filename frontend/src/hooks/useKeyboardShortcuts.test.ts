import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'

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
    // The hook internally uses Zustand to access store state
    // This test verifies it doesn't crash with default state
    const { rerender } = renderHook(() => useKeyboardShortcuts())
    expect(rerender).toBeDefined()
  })
})
