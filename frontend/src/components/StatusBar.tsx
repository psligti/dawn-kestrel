import { useMemoryUsage, useModelStatus, useTokenUsage } from '../store'
import './StatusBar.css'

interface StatusBarProps {
  className?: string
}

export function StatusBar({ className = '' }: StatusBarProps) {
  const memoryUsage = useMemoryUsage()
  const modelStatus = useModelStatus()
  const tokenUsage = useTokenUsage()

  const formattedMemory = `${formatBytes(memoryUsage.used)} / ${formatBytes(memoryUsage.total)}`
  const formattedTokens = `${formatTokens(tokenUsage.total)} / ${tokenUsage.limit ? formatTokens(tokenUsage.limit) : '∞'}`

  return (
    <div className={`statusbar ${className}`}>
      <div className="statusbar__left">
        <span className={`statusbar__indicator statusbar__indicator--${modelStatus.connected ? 'connected' : 'disconnected'}`}>
          {modelStatus.connected ? '●' : '○'}
        </span>
        <span className="statusbar__model">{modelStatus.name}</span>
      </div>

      <div className="statusbar__center">
        <span className="statusbar__info" title="Memory usage">
          {formattedMemory}
        </span>
        <span className="statusbar__divider">|</span>
        <span className="statusbar__info" title="Token usage">
          {formattedTokens}
        </span>
      </div>

      <div className="statusbar__right">
        <span className="statusbar__hint">Ctrl+K</span>
        <span className="statusbar__divider">|</span>
        <span className="statusbar__hint">Ctrl+D</span>
        <span className="statusbar__divider">|</span>
        <span className="statusbar__hint">Esc</span>
      </div>
    </div>
  )
}

function formatBytes(bytes: number): string {
  const mb = bytes / (1024 * 1024)
  if (mb < 1) {
    const kb = bytes / 1024
    return `${kb.toFixed(1)} KB`
  }
  return `${mb.toFixed(1)} GB`
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) {
    return `${(tokens / 1_000_000).toFixed(1)}M`
  }
  if (tokens >= 1_000) {
    return `${(tokens / 1_000).toFixed(1)}K`
  }
  return tokens.toString()
}
