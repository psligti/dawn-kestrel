import { useCurrentSession, useModelStatus } from '../store'
import './TopBar.css'

interface TopBarProps {
  onRun?: () => void
  onStop?: () => void
}

export function TopBar({ onRun, onStop }: TopBarProps) {
  const currentSession = useCurrentSession()
  const modelStatus = useModelStatus()

  return (
    <div className="topbar">
      <div className="topbar__left">
        <div className="topbar__logo">
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
          <span className="topbar__logo-text">OpenCode</span>
        </div>
        {currentSession && (
          <span className="topbar__title" title={currentSession.title}>
            {currentSession.title}
          </span>
        )}
      </div>

      <div className="topbar__right">
        <span className={`topbar__chip topbar__chip--${modelStatus.connected ? 'connected' : 'disconnected'}`}>
          {modelStatus.connected ? '●' : '○'} {modelStatus.name}
        </span>
        <a
          href="https://github.com/opencode-ai/opencode"
          target="_blank"
          rel="noopener noreferrer"
          className="topbar__link"
          aria-label="GitHub repository"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="currentColor"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M12 0C5.37 0 0 5.37 0 12C0 17.31 3.435 21.795 8.205 23.385C8.805 23.49 9 23.13 9 22.815C9 22.53 9 21.735 9 20.745C5.73 21.345 5.025 19.085 5.025 19.085C4.485 17.8 3.825 17.44 3.825 17.44C2.91 16.875 3.915 16.875 3.915 16.875C4.98 16.92 5.535 17.925 5.535 17.925C6.495 19.545 8.055 19.005 8.67 18.72C8.73 18.06 8.96 17.665 9.225 17.43C7.14 17.19 4.935 16.365 4.935 12.915C4.935 11.865 5.295 10.995 5.895 10.32C5.835 10.08 5.52 9.015 6.015 7.605C6.015 7.605 6.81 7.365 9 9.315C9.795 9.105 10.635 9 11.475 9C12.315 9 13.155 9.105 13.95 9.315C16.14 7.365 16.935 7.605 16.935 7.605C17.43 9.015 17.115 10.08 17.055 10.32C17.655 10.995 18.015 11.865 18.015 12.915C18.015 16.365 15.81 17.19 13.725 17.43C14.055 17.73 14.34 18.345 14.34 19.265C14.34 20.625 14.34 21.735 14.34 22.015C14.34 22.33 14.53 22.685 15.135 22.575C19.92 20.985 23.355 16.505 23.355 11.195C23.355 5.37 17.985 0 11.355 0H12Z" />
          </svg>
        </a>
        {onRun && (
          <button className="topbar__button topbar__button--run" onClick={onRun}>
            Run
          </button>
        )}
        {onStop && (
          <button className="topbar__button topbar__button--stop" onClick={onStop}>
            Stop
          </button>
        )}
      </div>
    </div>
  )
}
