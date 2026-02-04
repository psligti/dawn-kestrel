import { useCurrentSession } from '../store'

export function TopBar() {
  const currentSession = useCurrentSession()

  return (
    <div className="flex items-center justify-between bg-surface-panel border border-normal rounded-[14px] px-3 py-2 h-12">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
            <path
              d="M12 6L12 18M6 12L18 12"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
          <span className="font-semibold text-sm text-primary tracking-tight">OpenCode</span>
        </div>
        {currentSession && (
          <span className="font-medium text-xs text-primary whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px]" title={currentSession.title}>
            {currentSession.title}
          </span>
        )}
      </div>
    </div>
  )
}
