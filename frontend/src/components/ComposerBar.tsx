import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import { useCurrentSession, useComposer, useSetComposerDraft, useSetComposerSending, useAgentsState, useSelectedAgent, useSetSelectedAgent } from '../store'
import { useMessages } from '../hooks/useMessages'

const MAX_LINES = 13
export function ComposerBar() {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [currentHeight, setCurrentHeight] = useState<number | undefined>(undefined)
  const [localDraft, setLocalDraft] = useState('')

  // Hooks from store
  const currentSession = useCurrentSession()
  const { draft: storeDraft, isSending } = useComposer()
  const setComposerDraft = useSetComposerDraft()
  const setComposerSending = useSetComposerSending()
  const { createUserMessage } = useMessages()
  const agents = useAgentsState()
  const selectedAgent = useSelectedAgent()
  const setSelectedAgent = useSetSelectedAgent()

  // Sync store draft to local state when it changes
  useEffect(() => {
    setLocalDraft(storeDraft)
  }, [storeDraft])

  useEffect(() => {
    if (textareaRef.current && !currentHeight) {
      textareaRef.current.focus()

      const initialHeight = 48
      setCurrentHeight(initialHeight)
    }
  }, [currentHeight])

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setLocalDraft(value)
    setComposerDraft(value)

    const textarea = textareaRef.current
    if (textarea) {
      const lineHeight = 24
      const maxHeight = lineHeight * MAX_LINES
      const scrollHeight = textarea.scrollHeight
      const newHeight = Math.min(Math.max(scrollHeight, 48), maxHeight)
      setCurrentHeight(newHeight)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey) {
      e.preventDefault()
      if (!localDraft.trim() || isSending || !currentSession) return
      void handleSend()
    }
    if (e.key === 'Enter' && e.ctrlKey && !e.shiftKey) {
      e.preventDefault()
      const textarea = textareaRef.current
      if (textarea) {
        const startPos = textarea.selectionStart
        const endPos = textarea.selectionEnd
        const newValue = localDraft.substring(0, startPos) + '\n' + localDraft.substring(endPos)
        setLocalDraft(newValue)
        setComposerDraft(newValue)
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = startPos + 1
        }, 0)
      }
    }
    if (e.key === 'Tab') {
      e.preventDefault()
      if (agents.length === 0) return

      const currentIndex = selectedAgent
        ? agents.findIndex((agent) => agent.name === selectedAgent)
        : -1

      const nextIndex = (currentIndex + 1) % agents.length
      const nextAgent = agents[nextIndex]
      setSelectedAgent(nextAgent.name)
    }
  }

  const handleSend = async () => {
    if (!localDraft.trim() || isSending || !currentSession) return
    setComposerSending(true)
    try {
      await createUserMessage(currentSession.id, localDraft)
      setComposerDraft('')
      setLocalDraft('')
      setCurrentHeight(48)
    } catch (error) {
      console.error('Failed to send message:', error)
    } finally {
      setComposerSending(false)
    }
  }

  const isDisabled = localDraft.trim().length === 0 || isSending

  return (
    <div className="bg-surface-base rounded-0">
      <div className="relative flex items-end">
        <textarea
          ref={textareaRef}
          className="w-full px-2 py-3 pr-14 text-sm leading-6 font-inherit text-primary bg-surface-panel border border-normal rounded-0 resize-none overflow-hidden outline-none transition-all duration-200 ease-in-out transition-[height_0.1s] min-h-12 placeholder:text-tertiary focus:border-focus focus:shadow-[0_0_2px_rgba(99,99,99,0.2)] disabled:opacity-70 disabled:cursor-not-allowed"
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
          className="absolute right-2 bottom-2 px-2 py-3 text-sm font-medium text-primary bg-accent-primary border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10 hover:bg-accent-secondary hover:border-accent-secondary active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-text-tertiary disabled:border-text-tertiary"
          aria-label="Send message"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}
