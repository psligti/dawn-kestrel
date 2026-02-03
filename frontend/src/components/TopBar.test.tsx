import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useCurrentSession, useModelStatus } from '../store'
import { TopBar } from './TopBar'

vi.mock('../store', () => ({
  useCurrentSession: vi.fn(),
  useModelStatus: vi.fn(),
}))

describe('TopBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render OpenCode logo', () => {
    useCurrentSession.mockReturnValue(null)
    useModelStatus.mockReturnValue({ name: 'Agent', connected: true })
    render(<TopBar />)

    expect(screen.getByText('OpenCode')).toBeInTheDocument()
  })

  it('should render session title when session exists', () => {
    useCurrentSession.mockReturnValue({
      id: 'session-1',
      title: 'Test Session',
      time_created: 1234567890,
      time_updated: 1234567890,
      message_count: 0,
    })
    useModelStatus.mockReturnValue({ name: 'Agent', connected: true })
    render(<TopBar />)

    expect(screen.getByText('Test Session')).toBeInTheDocument()
  })

  it('should truncate session title that is too long', () => {
    const longTitle = 'This is a very long session title that should be truncated'
    useCurrentSession.mockReturnValue({
      id: 'session-1',
      title: longTitle,
      time_created: 1234567890,
      time_updated: 1234567890,
      message_count: 0,
    })
    useModelStatus.mockReturnValue({ name: 'Agent', connected: true })
    render(<TopBar />)

    const titleElement = screen.getByText(longTitle)
    expect(titleElement.getAttribute('title')).toBe(longTitle)
    expect(titleElement).toHaveAttribute('title', longTitle)
  })

  it('should render model name with connected status indicator', () => {
    useCurrentSession.mockReturnValue(null)
    useModelStatus.mockReturnValue({ name: 'Agent', connected: true })
    render(<TopBar />)

    expect(screen.getByText('● Agent')).toBeInTheDocument()
  })

  it('should render disconnected status indicator when not connected', () => {
    useCurrentSession.mockReturnValue(null)
    useModelStatus.mockReturnValue({ name: 'Agent', connected: false })
    render(<TopBar />)

    expect(screen.getByText('○ Agent')).toBeInTheDocument()
  })

  it('should render GitHub link', () => {
    useCurrentSession.mockReturnValue(null)
    useModelStatus.mockReturnValue({ name: 'Agent', connected: true })
    render(<TopBar />)

    const githubLink = screen.getByRole('link')
    expect(githubLink).toBeInTheDocument()
    expect(githubLink.getAttribute('href')).toBe('https://github.com/opencode-ai/opencode')
  })

  it('should render Run button when onRun handler is provided', () => {
    useCurrentSession.mockReturnValue(null)
    useModelStatus.mockReturnValue({ name: 'Agent', connected: true })
    const onRun = vi.fn()
    render(<TopBar onRun={onRun} />)

    const runButton = screen.getByText('Run')
    expect(runButton).toBeInTheDocument()
    expect(runButton).toHaveClass('topbar__button--run')
  })

  it('should render Stop button when onStop handler is provided', () => {
    useCurrentSession.mockReturnValue(null)
    useModelStatus.mockReturnValue({ name: 'Agent', connected: true })
    const onStop = vi.fn()
    render(<TopBar onStop={onStop} />)

    const stopButton = screen.getByText('Stop')
    expect(stopButton).toBeInTheDocument()
    expect(stopButton).toHaveClass('topbar__button--stop')
  })

  it('should call onRun when Run button is clicked', () => {
    useCurrentSession.mockReturnValue(null)
    useModelStatus.mockReturnValue({ name: 'Agent', connected: true })
    const onRun = vi.fn()
    render(<TopBar onRun={onRun} />)

    const runButton = screen.getByText('Run')
    fireEvent.click(runButton)

    expect(onRun).toHaveBeenCalledTimes(1)
  })

  it('should call onStop when Stop button is clicked', () => {
    useCurrentSession.mockReturnValue(null)
    useModelStatus.mockReturnValue({ name: 'Agent', connected: true })
    const onStop = vi.fn()
    render(<TopBar onStop={onStop} />)

    const stopButton = screen.getByText('Stop')
    fireEvent.click(stopButton)

    expect(onStop).toHaveBeenCalledTimes(1)
  })

  it('should call both Run and Stop handlers', () => {
    useCurrentSession.mockReturnValue(null)
    useModelStatus.mockReturnValue({ name: 'Agent', connected: true })
    const onRun = vi.fn()
    const onStop = vi.fn()
    render(<TopBar onRun={onRun} onStop={onStop} />)

    const stopButton = screen.getByText('Stop')
    fireEvent.click(stopButton)

    expect(onStop).toHaveBeenCalledTimes(1)
    expect(onRun).not.toHaveBeenCalled()
  })
})
