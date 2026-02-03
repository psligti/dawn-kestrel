import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { ConversationTimeline } from './ConversationTimeline'
import { Message } from '../types/api'

describe('ConversationTimeline', () => {
  it('should render without crashing (basic smoke test)', () => {
    const mockMessages: Message[] = [
      {
        id: '1',
        session_id: 'test-session',
        role: 'user',
        text: 'Test message',
        parts: [],
        timestamp: Date.now(),
      },
    ]

    // Mock useStore to return our messages
    vi.stubGlobal('useStore', vi.fn(() => ({
      messages: {
        'test-session': mockMessages,
      },
    })))

    expect(() => {
      render(<ConversationTimeline sessionId="test-session" />)
    }).not.toThrow()
  })

  it('should render empty state when no messages', () => {
    vi.stubGlobal('useStore', vi.fn(() => ({
      messages: {},
    })))

    const { container } = render(<ConversationTimeline sessionId="test-session" />)

    expect(container).toBeTruthy()
    expect(container.textContent).toContain('No messages yet')
  })
})
