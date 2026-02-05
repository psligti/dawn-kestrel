import { render, screen } from '@testing-library/react'
import App from '../App'

vi.mock('../components/AppLayout', () => ({
  AppLayout: () => <div>OpenCode</div>,
}))

vi.mock('../hooks/useCurrentSession', () => ({
  useCurrentSession: () => ({ currentSession: null, setCurrent: vi.fn() }),
}))

vi.mock('../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: [],
    fetchSessions: () => Promise.resolve(),
    createSession: () => Promise.resolve({
      id: 'session-1',
      title: 'Session 1',
      time_created: 0,
      time_updated: 0,
      message_count: 0,
    }),
  }),
}))

vi.mock('../hooks/useMessages', () => ({
  useMessages: () => ({
    fetchMessages: () => Promise.resolve(),
  }),
}))

vi.mock('../hooks/useAgents', () => ({
  useAgents: () => ({ agents: [], fetchAgents: () => Promise.resolve() }),
}))

vi.mock('../hooks/useTools', () => ({
  useTools: () => ({ tools: [], fetchTools: () => Promise.resolve() }),
}))

vi.mock('../hooks/useSkills', () => ({
  useSkills: () => ({ skills: [], fetchSkills: () => Promise.resolve() }),
}))

vi.mock('../hooks/useModels', () => ({
  useModels: () => ({ models: [], fetchModels: () => Promise.resolve() }),
}))

vi.mock('../hooks/useAccounts', () => ({
  useAccounts: () => ({ accounts: [], fetchAccounts: () => Promise.resolve() }),
}))

vi.mock('../store', () => ({
  useSelectedAgent: () => null,
  useSelectedModel: () => null,
  useSelectedAccount: () => null,
  useSetSelectedAgent: () => vi.fn(),
  useSetSelectedModel: () => vi.fn(),
  useSetSelectedAccount: () => vi.fn(),
  useSetCurrentSession: () => vi.fn(),
  useAgentsState: () => [],
  useSetTelemetry: () => vi.fn(),
}))

vi.mock('../hooks/useSessionThemeStream', () => ({
  useSessionThemeStream: () => ({ connect: vi.fn(), disconnect: vi.fn() }),
}))

vi.mock('../hooks/useSessionTelemetryStream', () => ({
  useSessionTelemetryStream: () => ({ connect: vi.fn(), disconnect: vi.fn() }),
}))

describe('App', () => {
  it('renders the OpenCode header', async () => {
    render(<App />)
    expect(screen.getByText('OpenCode')).toBeInTheDocument()
  })
})
