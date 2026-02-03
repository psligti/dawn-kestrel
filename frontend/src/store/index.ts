import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface Session {
  id: string
  title: string
  time_created: number
  time_updated: number
  message_count: number
}

export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system' | 'tool' | 'question'
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
  tab: 'todos' | 'tools' | 'agents' | 'sessions' | 'navigator'
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

export interface AppState {
  // Sessions
  sessions: Session[]
  currentSession: Session | null

  // Messages
  messages: Record<string, Message[]>

  // Theme
  theme: 'dark' | 'light'

  // UI State
  paletteOpen: boolean
  drawerOpen: boolean
  drawerTab: 'todos' | 'tools' | 'agents' | 'sessions' | 'navigator'

  // Model Status
  modelStatus: ModelStatus

  // Token Usage
  tokenUsage: TokenUsage

  // Memory Usage
  memoryUsage: MemoryUsage

  // Actions
  setSessions: (sessions: Session[]) => void
  setCurrentSession: (session: Session | null) => void
  addMessage: (sessionId: string, message: Message) => void
  updateMessage: (sessionId: string, messageId: string, message: Partial<Message>) => void
  setTheme: (theme: 'dark' | 'light') => void
  setPaletteOpen: (open: boolean) => void
  setDrawerOpen: (open: boolean) => void
  setDrawerTab: (tab: 'todos' | 'tools' | 'agents' | 'sessions' | 'navigator') => void
  setComposerDraft: (draft: string) => void
  setComposerSending: (isSending: boolean) => void
  setModelStatus: (status: ModelStatus) => void
  setTokenUsage: (usage: TokenUsage) => void
  setMemoryUsage: (usage: MemoryUsage) => void
}

const defaultTheme = 'dark'
const defaultDraft = ''

const useStoreBase = create<AppState>((set, get) => ({
  // Initial state
  sessions: [],
  currentSession: null,
  messages: {},
  theme: defaultTheme,
  paletteOpen: false,
  drawerOpen: false,
  drawerTab: 'todos',
  composer: {
    draft: defaultDraft,
    isSending: false,
  },
  modelStatus: {
    name: 'Agent',
    connected: true,
  },
  tokenUsage: {
    input: 0,
    output: 0,
    total: 0,
  },
  memoryUsage: {
    used: 0,
    total: 8,
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
  setTheme: (theme) => set({ theme }),
  setPaletteOpen: (open) => set({ paletteOpen: open }),
  setDrawerOpen: (open) => set({ drawerOpen: open }),
  setDrawerTab: (tab) => set({ drawerTab: tab }),
  setComposerDraft: (draft) => set((state) => ({ composer: { ...state.composer, draft } })),
  setComposerSending: (isSending) => set((state) => ({ composer: { ...state.composer, isSending } })),
  setModelStatus: (status) => set({ modelStatus: status }),
  setTokenUsage: (usage) => set({ tokenUsage: usage }),
  setMemoryUsage: (usage) => set({ memoryUsage: usage }),
}))

export const useStore = devtools(useStoreBase)

// Typed hooks with shallow comparison
export const useSessions = () => useStore((state) => state.sessions)
export const useCurrentSession = () => useStore((state) => state.currentSession)
export const useTheme = () => useStore((state) => state.theme)
export const usePalette = () => useStore((state) => state.paletteOpen)
export const useDrawer = () => useStore((state) => ({ open: state.drawerOpen, tab: state.drawerTab }))
export const useComposer = () => useStore((state) => state.composer)
export const useModelStatus = () => useStore((state) => state.modelStatus)
export const useTokenUsage = () => useStore((state) => state.tokenUsage)
export const useMemoryUsage = () => useStore((state) => state.memoryUsage)
export const useSetComposerDraft = () => useStore((state) => state.setComposerDraft)
