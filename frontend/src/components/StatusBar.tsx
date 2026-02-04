import { useMemoryUsage, useModelStatus, useTokenUsage } from '../store'

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
    <div className={`flex items-center justify-between bg-surface-panel border border-normal rounded-[14px] px-3 py-2 h-9 text-xs flex-shrink-0 ${className}`}>
      <div className="flex items-center gap-2">
        <span className={`inline-flex items-center ${modelStatus.connected ? 'text-success' : 'text-tertiary'}`}>
          {modelStatus.connected ? '●' : '○'}
        </span>
        <span className="text-secondary font-medium">{modelStatus.name}</span>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-secondary" title="Memory usage">
          {formattedMemory}
        </span>
        <span className="text-border-normal opacity-50">|</span>
        <span className="text-secondary" title="Token usage">
          {formattedTokens}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-tertiary">Ctrl+K</span>
        <span className="text-border-normal opacity-50">|</span>
        <span className="text-tertiary">Ctrl+D</span>
        <span className="text-border-normal opacity-50">|</span>
        <span className="text-tertiary">Esc</span>
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
