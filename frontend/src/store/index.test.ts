import { act, renderHook } from '@testing-library/react'
import { useStore } from '../store'

describe('store', () => {
  it('initializes with defaults', () => {
    const { result } = renderHook(() => useStore())

    expect(result.current.sessions).toEqual([])
    expect(result.current.currentSession).toBeNull()
    expect(result.current.messages).toEqual({})
    expect(result.current.drawerTab).toBe('sessions')
    expect(result.current.modelStatus.name).toBe('Agent')
    expect(result.current.agents).toEqual([])
    expect(result.current.tools).toEqual([])
    expect(result.current.skills).toEqual([])
    expect(result.current.models).toEqual([])
    expect(result.current.accounts).toEqual([])
  })

  it('updates selections', () => {
    const { result } = renderHook(() => useStore())

    act(() => {
      result.current.setSelectedAgent('build')
      result.current.setSelectedModel('gpt-4o-mini')
      result.current.setSelectedSkills(['git-master'])
      result.current.setSelectedAccount('default')
    })

    expect(result.current.selectedAgent).toBe('build')
    expect(result.current.selectedModel).toBe('gpt-4o-mini')
    expect(result.current.selectedSkills).toEqual(['git-master'])
    expect(result.current.selectedAccount).toBe('default')
  })

  it('initializes left dashboard closed and unpinned', () => {
    const { result } = renderHook(() => useStore())

    expect(result.current.leftDashboardOpen).toBe(false)
    expect(result.current.leftDashboardPinned).toBe(false)
  })

  it('updates left dashboard state', () => {
    const { result } = renderHook(() => useStore())

    act(() => {
      result.current.setLeftDashboardOpen(true)
    })
    expect(result.current.leftDashboardOpen).toBe(true)

    act(() => {
      result.current.setLeftDashboardPinned(true)
    })
    expect(result.current.leftDashboardPinned).toBe(true)

    act(() => {
      result.current.setLeftDashboardOpen(false)
    })
    expect(result.current.leftDashboardOpen).toBe(false)
  })

  it('initializes telemetry with default values', () => {
    const { result } = renderHook(() => useStore())

    expect(result.current.telemetry).toEqual({
      git: {
        is_repo: false,
      },
      tools: {},
      effort: {},
    })
  })

  it('updates telemetry state', () => {
    const { result } = renderHook(() => useStore())

    const newTelemetry = {
      git: {
        is_repo: true,
        branch: 'main',
        dirty_count: 3,
        staged_count: 1,
        conflict: false,
      },
      tools: {
        running: {
          tool_id: 'bash',
          since: 1730000000,
        },
        error_count: 0,
      },
      effort: {
        duration_ms: 1000,
        token_total: 100,
        tool_count: 5,
        effort_score: 2,
      },
      directory_scope: '/test/path',
    }

    act(() => {
      result.current.setTelemetry(newTelemetry)
    })

    expect(result.current.telemetry).toEqual(newTelemetry)
  })
})
