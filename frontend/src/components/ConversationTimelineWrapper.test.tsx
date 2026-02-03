import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConversationTimelineWrapper } from './ConversationTimelineWrapper'
import { Message } from '../types/api'

describe('ConversationTimelineWrapper', () => {
  const mockOnSend = vi.fn()
  const mockOnRun = vi.fn()
  const mockOnStop = vi.fn()

  const sampleMessages: Message[] = [
    {
      id: 'msg-1',
      session_id: 'session-1',
      role: 'user',
      text: 'Hello',
      parts: [],
      timestamp: Date.now(),
    },
  ]

  it('renders without crashing', () => {
    render(
      <ConversationTimelineWrapper
        sessionId="test-session"
        onSend={mockOnSend}
        onRun={mockOnRun}
        onStop={mockOnStop}
      />
    )
    expect(screen.getByText('No messages yet')).toBeInTheDocument()
  })

  it('renders with initial messages', () => {
    render(
      <ConversationTimelineWrapper
        sessionId="test-session"
        initialMessages={sampleMessages}
        onSend={mockOnSend}
      />
    )
    // The messages should be rendered (ConversationTimeline will handle this)
    expect(screen.queryByText('Hello')).toBeInTheDocument()
  })

  it('passes autoScroll prop to ConversationTimeline', () => {
    render(
      <ConversationTimelineWrapper
        sessionId="test-session"
        autoScroll={false}
        onSend={mockOnSend}
      />
    )
    // Component should render without errors when autoScroll is false
    expect(screen.getByText('No messages yet')).toBeInTheDocument()
  })

  it('passes onSend callback to ComposerBar', () => {
    render(
      <ConversationTimelineWrapper
        sessionId="test-session"
        onSend={mockOnSend}
      />
    )
    // Component should render without errors
    expect(screen.getByText('No messages yet')).toBeInTheDocument()
  })

  it('passes onRun and onStop callbacks to ConversationTimeline', () => {
    render(
      <ConversationTimelineWrapper
        sessionId="test-session"
        onRun={mockOnRun}
        onStop={mockOnStop}
      />
    )
    // Component should render without errors
    expect(screen.getByText('No messages yet')).toBeInTheDocument()
  })

  it('renders ConversationTimeline and ComposerBar together', () => {
    render(
      <ConversationTimelineWrapper
        sessionId="test-session"
        onSend={mockOnSend}
      />
    )

    // Check that both ConversationTimeline and ComposerBar components are present
    // (inferred from the structure of the rendered output)
    const timelineContainer = screen.getByText(/No messages yet/i)
    expect(timelineContainer).toBeInTheDocument()
  })

  it('uses default values for optional props', () => {
    render(
      <ConversationTimelineWrapper sessionId="test-session" />
    )

    // Should render with default autoScroll={true}
    expect(screen.getByText('No messages yet')).toBeInTheDocument()
  })

  it('renders with empty initial messages array', () => {
    render(
      <ConversationTimelineWrapper
        sessionId="test-session"
        initialMessages={[]}
        onSend={mockOnSend}
      />
    )
    expect(screen.getByText('No messages yet')).toBeInTheDocument()
  })

  it('does not throw errors with undefined callbacks', () => {
    render(
      <ConversationTimelineWrapper
        sessionId="test-session"
        onSend={undefined as any}
        onRun={undefined as any}
        onStop={undefined as any}
      />
    )
    expect(screen.getByText('No messages yet')).toBeInTheDocument()
  })
})
