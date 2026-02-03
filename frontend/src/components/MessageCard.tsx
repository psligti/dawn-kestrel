import { Message } from '../types/api'

interface MessageCardProps {
  message: Message
  onJump?: (id: string) => void
}

/**
 * MessageCard component for rendering individual messages in the timeline
 */
export function MessageCard({ message, onJump }: MessageCardProps) {
  return (
    <div className="message-card">
      <div className="message-role">
        {message.role.charAt(0).toUpperCase() + message.role.slice(1)}
      </div>
      <div className="message-text">{message.text}</div>
      {onJump && (
        <button
          className="message-jump"
          onClick={() => onJump(message.id)}
          title="Jump to message"
        >
          Jump
        </button>
      )}
    </div>
  )
}
