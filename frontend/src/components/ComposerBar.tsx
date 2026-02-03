import { useEffect, useRef, useState } from 'react'
import { useCurrentSession, useComposer, useAddMessage, useSetComposerDraft } from '../store'
import './ComposerBar.css'

const MAX_LINES = 10

export function ComposerBar() {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [currentHeight, setCurrentHeight] = useState<number | undefined>(undefined)
  const [localDraft, setLocalDraft] = useState('')

  // Hooks from store
  const { currentSession } = useCurrentSession()
  const { draft: storeDraft, isSending } = useComposer()
  const addMessage = useAddMessage()
  const setComposerDraft = useSetComposerDraft()

  // Sync store draft to local state when it changes
  useEffect(() => {
    setLocalDraft(storeDraft)
  }, [storeDraft])

  // Auto-grow textarea on mount
  useEffect(() => {
    if (textareaRef.current && !currentHeight) {
      // Auto-focus on mount
      textareaRef.current.focus()

      // Calculate initial height
      const lineHeight = 24 // CSS line-height
      const maxHeight = lineHeight * MAX_LINES
      const newHeight = Math.min(textareaRef.current.scrollHeight, maxHeight)
      setCurrentHeight(newHeight)
    }
  }, [currentHeight])

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setLocalDraft(value)
    setComposerDraft(value)

    const textarea = textareaRef.current
    if (textarea) {
      // Calculate new height based on content
      const lineHeight = 24
      const maxHeight = lineHeight * MAX_LINES
      const newHeight = Math.min(textarea.scrollHeight, maxHeight)
      setCurrentHeight(newHeight)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl+Enter to send
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault()
      if (localDraft.trim() && !isSending) {
        addMessage({
          session_id: currentSession?.id || '',
          role: 'user' as const,
          text: localDraft,
          parts: [],
          timestamp: Date.now(),
        })
      }
    }
  }

  const handleSend = () => {
    if (localDraft.trim() && !isSending) {
      addMessage({
        session_id: currentSession?.id || '',
        role: 'user' as const,
        text: localDraft,
        parts: [],
        timestamp: Date.now(),
      })
    }
  }

  const isDisabled = localDraft.trim().length === 0 || isSending

  return (
    <div className="composer-bar">
      <textarea
        ref={textareaRef}
        value={localDraft}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="Start by typing..."
        style={{
          height: `${currentHeight}px`,
          minHeight: '48px',
          maxHeight: `${24 * MAX_LINES}px`,
        }}
        disabled={isSending}
      />
      <button
        onClick={handleSend}
        disabled={isDisabled}
        className="composer-bar__send"
        aria-label="Send message"
      >
        Send
      </button>
    </div>
  )
}
