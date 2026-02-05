import { useEffect, useState } from 'react'
import {
  useLeftDashboard,
  useSetLeftDashboardOpen,
  useSetLeftDashboardPinned,
  useTelemetry,
  useDrawer,
  useSetDrawerOpen,
} from '../store'

export default function LeftDashboardDrawer() {
  const { open, pinned } = useLeftDashboard()
  const setLeftDashboardOpen = useSetLeftDashboardOpen()
  const setLeftDashboardPinned = useSetLeftDashboardPinned()
  const telemetry = useTelemetry()
  const drawer = useDrawer()
  const setDrawerOpen = useSetDrawerOpen()

  const [isNarrowScreen, setIsNarrowScreen] = useState(false)

  useEffect(() => {
    const checkWidth = () => {
      setIsNarrowScreen(window.innerWidth < 1024)
    }
    checkWidth()
    window.addEventListener('resize', checkWidth)
    return () => window.removeEventListener('resize', checkWidth)
  }, [])

  useEffect(() => {
    if (open && drawer.open) {
      setDrawerOpen(false)
    }
  }, [open, drawer.open, setDrawerOpen])

  useEffect(() => {
    if (!open) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        setLeftDashboardOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, setLeftDashboardOpen])

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !pinned) {
      setLeftDashboardOpen(false)
    }
  }

  const isPinned = pinned && !isNarrowScreen

  if (!open && !isPinned) return null

  const getEffortEmoji = (score?: number): string => {
    if (score === undefined || score === null) return '🤓'
    switch (score) {
      case 0: return '🤓'
      case 1: return '🧐'
      case 2: return '🧠'
      case 3: return '🧠⚡'
      case 4: return '🧠🔥'
      case 5: return '🧠💥'
      default: return '🤓'
    }
  }

  const drawerContent = (
    <div
      data-testid="left-dashboard"
      className="flex flex-col h-full bg-surface-raised border-r border-normal shadow-[0_0_30px_rgba(0,0,0,0.3)]"
    >
      <div className="flex items-center justify-between px-3 py-2 border-b border-normal bg-surface-panel">
        <span className="text-xs text-secondary uppercase tracking-widest font-semibold">Now</span>
        <div className="flex items-center gap-1">
          {!isNarrowScreen && (
            <button
              data-testid="left-dashboard-pin"
              className={`p-1 rounded transition-all duration-150 ease-in-out ${
                isPinned
                  ? 'bg-accent-primary text-accent-primary'
                  : 'text-secondary hover:text-primary hover:bg-[rgba(99,102,241,0.05)]'
              }`}
              onClick={() => setLeftDashboardPinned(!pinned)}
              title={isPinned ? 'Unpin drawer' : 'Pin drawer'}
            >
              {isPinned ? '📌' : '📍'}
            </button>
          )}
          <button
            data-testid="left-dashboard-close"
            className="p-1 rounded text-secondary hover:text-primary hover:bg-[rgba(99,102,241,0.05)] transition-all duration-150 ease-in-out"
            onClick={() => setLeftDashboardOpen(false)}
            title="Close drawer (Esc)"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <div className="text-[11px] text-secondary uppercase tracking-wide">Git</div>
          {telemetry.git.is_repo ? (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-primary font-mono">{telemetry.git.branch || 'detached'}</span>
              {telemetry.git.dirty_count !== undefined && telemetry.git.dirty_count > 0 && (
                <span className="text-accent-primary font-mono">+{telemetry.git.dirty_count}</span>
              )}
              {telemetry.git.staged_count !== undefined && telemetry.git.staged_count > 0 && (
                <span className="text-success font-mono">*{telemetry.git.staged_count}</span>
              )}
            </div>
          ) : (
            <div className="text-xs text-tertiary">Not a git repo</div>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <div className="text-[11px] text-secondary uppercase tracking-wide">Tools</div>
          {telemetry.tools.running ? (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-accent-primary animate-pulse">●</span>
              <span className="text-primary font-mono">{telemetry.tools.running.tool_id}</span>
            </div>
          ) : telemetry.tools.last ? (
            <div className="flex items-center gap-2 text-xs">
              <span className={`${
                telemetry.tools.last.status === 'completed' ? 'text-success' :
                telemetry.tools.last.status === 'failed' ? 'text-error' :
                telemetry.tools.last.status === 'cancelled' ? 'text-tertiary' :
                'text-secondary'
              }`}>●</span>
              <span className="text-primary font-mono">{telemetry.tools.last.tool_id}</span>
            </div>
          ) : (
            <div className="text-xs text-tertiary">No tools run</div>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <div className="text-[11px] text-secondary uppercase tracking-wide">Effort</div>
          <div className="text-xl leading-none">
            {getEffortEmoji(telemetry.effort.effort_score)}
          </div>
        </div>

        <div className="mt-auto pt-3 border-t border-normal">
          <div className="text-[11px] text-secondary uppercase tracking-wide mb-2">Quick Actions</div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-tertiary">Toggle dashboard</span>
              <span className="font-mono text-secondary">Ctrl+L</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-tertiary">Command palette</span>
              <span className="font-mono text-secondary">Ctrl+K</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-tertiary">Settings</span>
              <span className="font-mono text-secondary">Ctrl+D</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )

  if (isPinned) {
    return (
      <div className="fixed left-0 top-0 bottom-0 w-64 z-[900] animate-slide-in-left">
        {drawerContent}
        <style>{`
          @keyframes slideInLeft {
            from {
              transform: translateX(-100%);
            }
            to {
              transform: translateX(0);
            }
          }
          .animate-slide-in-left {
            animation: slideInLeft 0.2s ease-out;
          }
          @media (prefers-reduced-motion: reduce) {
            .animate-slide-in-left {
              animation: none;
            }
          }
        `}</style>
      </div>
    )
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[1000] flex items-center justify-start"
      onClick={handleOverlayClick}
    >
      <div className="w-64 max-w-full h-full" onMouseDown={(e) => e.stopPropagation()}>
        {drawerContent}
      </div>
    </div>
  )
}
