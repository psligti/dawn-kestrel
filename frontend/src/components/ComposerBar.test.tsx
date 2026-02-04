import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ComposerBar } from './ComposerBar'

// Global mock setup - this runs once for all tests
vi.mock('../store', () => ({
  useStore: vi.fn(),
  useCurrentSession: vi.fn(() => ({
    id: 'test-session',
  })),
  useComposer: vi.fn(() => ({
    draft: '',
    isSending: false,
  })),
  useSetComposerDraft: vi.fn(() => vi.fn(() => {})),
  useSetComposerSending: vi.fn(() => vi.fn(() => {})),
  useAgentsState: vi.fn(() => []),
  useSelectedAgent: vi.fn(() => null),
  useSetSelectedAgent: vi.fn(() => vi.fn(() => {})),
}))

vi.mock('../hooks/useMessages', () => ({
  useMessages: () => ({
    createUserMessage: () => Promise.resolve(),
  }),
}))

describe('ComposerBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render without crashing (basic smoke test)', () => {
    expect(() => {
      render(<ComposerBar />)
    }).not.toThrow()
  })

  it('should render placeholder text "Start by typing..."', () => {
    render(<ComposerBar />)

    const textarea = screen.getByPlaceholderText(/start by typing/i)
    expect(textarea).toBeInTheDocument()
    expect(textarea.getAttribute('placeholder')).toBe('Start by typing...')
  })

  it('should render textarea', () => {
    render(<ComposerBar />)

    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement
    expect(textarea).toBeInTheDocument()
    expect(textarea.tagName).toBe('TEXTAREA')
  })

  it('should render send button', () => {
    render(<ComposerBar />)

    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeInTheDocument()
  })

  it('should be disabled when empty', () => {
    render(<ComposerBar />)

    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDisabled()
  })

  it('should not be disabled when there is text', () => {
    render(<ComposerBar />)
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement

    // Type some text - this should make the button enabled
    fireEvent.change(textarea, { target: { value: 'Test message' } })

    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).not.toBeDisabled()
  })

  it('should update draft when typing in textarea', () => {
    render(<ComposerBar />)
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement

    fireEvent.change(textarea, { target: { value: 'Hello world' } })

    expect(textarea.value).toBe('Hello world')
  })

  it('should allow clicking send without crashing', () => {
    render(<ComposerBar />)
    const sendButton = screen.getByRole('button', { name: /send/i })
    fireEvent.click(sendButton)
    expect(sendButton).toBeInTheDocument()
  })

  it('should focus textarea on mount', () => {
    const { container } = render(<ComposerBar />)

    const textarea = container.querySelector('textarea')
    expect(document.activeElement).toBe(textarea)
  })

  it('should render container with proper styling classes', () => {
    const { container } = render(<ComposerBar />)

    const containerElement = container.querySelector('.bg-surface-base')
    expect(containerElement).toBeInTheDocument()
  })
})
