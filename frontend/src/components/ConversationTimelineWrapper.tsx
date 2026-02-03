import { ConversationTimeline } from './ConversationTimeline'
import { ComposerBar } from './ComposerBar'
import { Message } from '../types/api'

interface ConversationTimelineWrapperProps {
  sessionId: string
  initialMessages?: Message[]
  autoScroll?: boolean
  onSend?: (text: string) => void
  onRun?: () => void
  onStop?: () => void
}

export function ConversationTimelineWrapper({
  sessionId,
  initialMessages = [],
  autoScroll = true,
  onSend,
  onRun,
  onStop,
}: ConversationTimelineWrapperProps) {
  return (
    <div className="app-layout">
      <ConversationTimeline
        sessionId={sessionId}
        autoScroll={autoScroll}
        onRun={onRun}
        onStop={onStop}
      />
      <ComposerBar onSend={onSend} />
    </div>
  )
}
