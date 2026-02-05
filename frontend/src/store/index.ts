import { useStore as useZustandStore } from 'zustand/react'
import { createStore } from 'zustand/vanilla'
import type { AccountSummary, AgentSummary, ModelSummary, SkillSummary, ToolSummary } from '../types/api'

export interface Session {
  id: string
  title: string
  time_created: number
  time_updated: number
  message_count: number
  theme_id?: string
}

export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system' | 'tool' | 'question' | 'thinking' | 'error'
  text: string
  parts: any[]
  token_usage?: {
    prompt: number
    completion: number
    total: number
  }
  timestamp?: number
}

export interface ComposerState {
  draft: string
  isSending: boolean
}

export interface DrawerState {
  open: boolean
  tab: 'todos' | 'tools' | 'agents' | 'sessions' | 'navigator' | 'models' | 'skills' | 'accounts' | 'settings' | 'info'
}

export interface ModelStatus {
  name: string
  connected: boolean
}

export interface TokenUsage {
  input: number
  output: number
  total: number
  limit?: number
}

export interface MemoryUsage {
  used: number
  total: number
}

export interface GitTelemetry {
  is_repo: boolean
  branch?: string
  dirty_count?: number
  staged_count?: number
  ahead?: number
  behind?: number
  conflict?: boolean
}

export interface ToolTelemetry {
  running?: {
    tool_id: string
    since: number
  }
  last?: {
    tool_id: string
    status: 'running' | 'completed' | 'failed' | 'cancelled'
    duration_ms?: number
  }
  error_count?: number
  recent?: Array<{
    tool_id: string
    status: 'running' | 'completed' | 'failed' | 'cancelled'
  }>
}

export interface EffortTelemetry {
  duration_ms?: number
  token_total?: number
  tool_count?: number
  effort_score?: number
}

export interface TelemetryData {
  git: GitTelemetry
  tools: ToolTelemetry
  effort: EffortTelemetry
  directory_scope?: string
}

export interface AppState {
  // Sessions
  sessions: Session[]
  currentSession: Session | null

  // Messages
  messages: Record<string, Message[]>

  // Composer
  composer: ComposerState

  // Theme
  theme: 'dark' | 'light'

  // UI State
  paletteOpen: boolean
  drawerOpen: boolean
  drawerTab: 'todos' | 'tools' | 'agents' | 'sessions' | 'navigator' | 'models' | 'skills' | 'accounts' | 'settings' | 'info'

  // Model Status
  modelStatus: ModelStatus

  // Agents
  agents: AgentSummary[]
  selectedAgent: string | null

  // Tools
  tools: ToolSummary[]

  // Models
  models: ModelSummary[]
  selectedModel: string | null

  // Skills
  skills: SkillSummary[]
  selectedSkills: string[]

  // Accounts
  accounts: AccountSummary[]
  selectedAccount: string | null

  // Token Usage
  tokenUsage: TokenUsage

  // Memory Usage
  memoryUsage: MemoryUsage

  // Left Dashboard
  leftDashboardOpen: boolean
  leftDashboardPinned: boolean

  // Telemetry
  telemetry: TelemetryData

  // Actions
  setSessions: (sessions: Session[]) => void
  setCurrentSession: (session: Session | null) => void
  addMessage: (sessionId: string, message: Message) => void
  updateMessage: (sessionId: string, messageId: string, message: Partial<Message>) => void
  setMessages: (sessionId: string, messages: Message[]) => void
  setTheme: (theme: 'dark' | 'light') => void
  setPaletteOpen: (open: boolean) => void
  setDrawerOpen: (open: boolean) => void
  setDrawerTab: (tab: 'todos' | 'tools' | 'agents' | 'sessions' | 'navigator' | 'models' | 'skills' | 'accounts' | 'settings' | 'info') => void
  setComposerDraft: (draft: string) => void
  setComposerSending: (isSending: boolean) => void
  setModelStatus: (status: ModelStatus) => void
  setTokenUsage: (usage: TokenUsage) => void
  setMemoryUsage: (usage: MemoryUsage) => void
  setAgents: (agents: AgentSummary[]) => void
  setSelectedAgent: (agentName: string | null) => void
  setTools: (tools: ToolSummary[]) => void
  setModels: (models: ModelSummary[]) => void
  setSelectedModel: (model: string | null) => void
  setSkills: (skills: SkillSummary[]) => void
  setSelectedSkills: (skills: string[]) => void
  setAccounts: (accounts: AccountSummary[]) => void
  setSelectedAccount: (accountName: string | null) => void

  // Left Dashboard Actions
  setLeftDashboardOpen: (open: boolean) => void
  setLeftDashboardPinned: (pinned: boolean) => void

  // Telemetry Actions
  setTelemetry: (telemetry: TelemetryData) => void
}

const defaultTheme = 'dark'
const defaultDraft = ''

const store = createStore<AppState>((set) => ({
  // Initial state
  sessions: [],
  currentSession: null,
  messages: {},
  theme: defaultTheme,
  paletteOpen: false,
  drawerOpen: false,
  drawerTab: 'sessions',
  composer: {
    draft: defaultDraft,
    isSending: false,
  },
  modelStatus: {
    name: 'Agent',
    connected: true,
  },
  agents: [],
  selectedAgent: null,
  tools: [],
  models: [],
  selectedModel: null,
  skills: [],
  selectedSkills: [],
  accounts: [],
  selectedAccount: null,
  tokenUsage: {
    input: 0,
    output: 0,
    total: 0,
  },
  memoryUsage: {
    used: 0,
    total: 8,
  },
  leftDashboardOpen: false,
  leftDashboardPinned: false,
  telemetry: {
    git: {
      is_repo: false,
    },
    tools: {},
    effort: {},
  },

  // Actions
  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (currentSession) => set({ currentSession }),
  addMessage: (sessionId, message) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: [...(state.messages[sessionId] || []), message],
      },
    })),
  updateMessage: (sessionId, messageId, update) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: (state.messages[sessionId] || []).map((msg) =>
          msg.id === messageId ? { ...msg, ...update } : msg
        ),
      },
    })),
  setMessages: (sessionId, messages) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: messages,
      },
    })),
  setTheme: (theme) => set({ theme }),
  setPaletteOpen: (open) => set({ paletteOpen: open }),
  setDrawerOpen: (open) => set({ drawerOpen: open }),
  setDrawerTab: (tab) => set({ drawerTab: tab }),
  setComposerDraft: (draft) => set((state) => ({ composer: { ...state.composer, draft } })),
  setComposerSending: (isSending) => set((state) => ({ composer: { ...state.composer, isSending } })),
  setModelStatus: (status) => set({ modelStatus: status }),
  setTokenUsage: (usage) => set({ tokenUsage: usage }),
  setMemoryUsage: (usage) => set({ memoryUsage: usage }),
  setAgents: (agents) => set({ agents }),
  setSelectedAgent: (selectedAgent) => set({ selectedAgent }),
  setTools: (tools) => set({ tools }),
  setModels: (models) => set({ models }),
  setSelectedModel: (selectedModel) => set({ selectedModel }),
  setSkills: (skills) => set({ skills }),
  setSelectedSkills: (selectedSkills) => set({ selectedSkills }),
  setAccounts: (accounts) => set({ accounts }),
  setSelectedAccount: (selectedAccount) => set({ selectedAccount }),
  setLeftDashboardOpen: (open) => set({ leftDashboardOpen: open }),
  setLeftDashboardPinned: (pinned) => set({ leftDashboardPinned: pinned }),
  setTelemetry: (telemetry) => set({ telemetry }),
}))

export { store }
export function useStore(): AppState
export function useStore<T>(selector: (state: AppState) => T): T
export function useStore<T>(selector?: (state: AppState) => T) {
  return selector ? useZustandStore(store, selector) : useZustandStore(store)
}

// Typed hooks with shallow comparison
export const useSessions = () => useStore((state) => state.sessions)
export const useSetSessions = () => useStore((state) => state.setSessions)
export const useCurrentSession = () => useStore((state) => state.currentSession)
export const useCurrentSessionThemeId = () => useStore((state) => state.currentSession?.theme_id)
export const useMessagesState = () => useStore((state) => state.messages)
export const useTheme = () => useStore((state) => state.theme)
export const usePalette = () => useStore((state) => state.paletteOpen)
export const useSetPaletteOpen = () => useStore((state) => state.setPaletteOpen)
export const useDrawer = () => useStore((state) => ({ open: state.drawerOpen, tab: state.drawerTab }))
export const useSetDrawerOpen = () => useStore((state) => state.setDrawerOpen)
export const useSetDrawerTab = () => useStore((state) => state.setDrawerTab)
export const useComposer = () => useStore((state) => state.composer)
export const useModelStatus = () => useStore((state) => state.modelStatus)
export const useTokenUsage = () => useStore((state) => state.tokenUsage)
export const useMemoryUsage = () => useStore((state) => state.memoryUsage)
export const useSetComposerDraft = () => useStore((state) => state.setComposerDraft)
export const useSetComposerSending = () => useStore((state) => state.setComposerSending)
export const useSetCurrentSession = () => useStore((state) => state.setCurrentSession)
export const useAddMessage = () => useStore((state) => state.addMessage)
export const useSetMessages = () => useStore((state) => state.setMessages)
export const useAgentsState = () => useStore((state) => state.agents)
export const useSetAgents = () => useStore((state) => state.setAgents)
export const useSelectedAgent = () => useStore((state) => state.selectedAgent)
export const useSetSelectedAgent = () => useStore((state) => state.setSelectedAgent)
export const useToolsState = () => useStore((state) => state.tools)
export const useSetTools = () => useStore((state) => state.setTools)
export const useModelsState = () => useStore((state) => state.models)
export const useSetModels = () => useStore((state) => state.setModels)
export const useSelectedModel = () => useStore((state) => state.selectedModel)
export const useSetSelectedModel = () => useStore((state) => state.setSelectedModel)
export const useSkillsState = () => useStore((state) => state.skills)
export const useSetSkills = () => useStore((state) => state.setSkills)
export const useSelectedSkills = () => useStore((state) => state.selectedSkills)
export const useSetSelectedSkills = () => useStore((state) => state.setSelectedSkills)
export const useAccountsState = () => useStore((state) => state.accounts)
export const useSetAccounts = () => useStore((state) => state.setAccounts)
export const useSelectedAccount = () => useStore((state) => state.selectedAccount)
export const useSetSelectedAccount = () => useStore((state) => state.setSelectedAccount)
export const useLeftDashboard = () => useStore((state) => ({ open: state.leftDashboardOpen, pinned: state.leftDashboardPinned }))
export const useSetLeftDashboardOpen = () => useStore((state) => state.setLeftDashboardOpen)
export const useSetLeftDashboardPinned = () => useStore((state) => state.setLeftDashboardPinned)
export const useTelemetry = () => useStore((state) => state.telemetry)
export const useSetTelemetry = () => useStore((state) => state.setTelemetry)
