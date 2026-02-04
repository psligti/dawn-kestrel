import { useEffect, useState } from 'react'
import type {
  AnchorHTMLAttributes,
  BlockquoteHTMLAttributes,
  HTMLAttributes,
  LiHTMLAttributes,
  OlHTMLAttributes,
  ReactNode,
} from 'react'
import ReactMarkdown, { Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  useAccountsState,
  useAgentsState,
  useCurrentSession,
  useModelsState,
  useSelectedAccount,
  useSelectedAgent,
  useSelectedModel,
  useSelectedSkills,
  useSetCurrentSession,
  useSetDrawerOpen,
  useSetDrawerTab,
  useSetSelectedAccount,
  useSetSelectedAgent,
  useSetSelectedModel,
  useSetSelectedSkills,
  useStore,
  useToolsState,
  useSkillsState,
} from '../store'
import { useSessions } from '../hooks/useSessions'
import { useAccounts } from '../hooks/useAccounts'
import ThemePicker from './ThemePicker'


type DrawerTab = 'sessions' | 'agents' | 'models' | 'skills' | 'tools' | 'accounts' | 'settings' | 'info'

type MarkdownParagraphProps = HTMLAttributes<HTMLParagraphElement> & { children?: ReactNode; node?: unknown }
type MarkdownListProps = HTMLAttributes<HTMLUListElement> & { children?: ReactNode; node?: unknown }
type MarkdownOrderedListProps = OlHTMLAttributes<HTMLOListElement> & { children?: ReactNode; node?: unknown }
type MarkdownListItemProps = LiHTMLAttributes<HTMLLIElement> & { children?: ReactNode; node?: unknown }
type MarkdownStrongProps = HTMLAttributes<HTMLElement> & { children?: ReactNode; node?: unknown }
type MarkdownEmProps = HTMLAttributes<HTMLElement> & { children?: ReactNode; node?: unknown }
type MarkdownLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & { children?: ReactNode; node?: unknown }
type MarkdownCodeProps = HTMLAttributes<HTMLElement> & { children?: ReactNode; node?: unknown; className?: string }
type MarkdownPreProps = HTMLAttributes<HTMLPreElement> & { children?: ReactNode; node?: unknown }
type MarkdownBlockquoteProps = BlockquoteHTMLAttributes<HTMLQuoteElement> & { children?: ReactNode; node?: unknown }

const drawerMarkdownComponents: Components = {
  p: ({ children }: MarkdownParagraphProps) => (
    <p className="text-xs text-secondary leading-relaxed mb-2 break-words overflow-wrap-break-word last:mb-0">
      {children}
    </p>
  ),
  h1: ({ children }: MarkdownParagraphProps) => (
    <h3 className="text-xs font-semibold text-primary">
      {children}
    </h3>
  ),
  h2: ({ children }: MarkdownParagraphProps) => (
    <h4 className="text-xs font-semibold text-primary">
      {children}
    </h4>
  ),
  h3: ({ children }: MarkdownParagraphProps) => (
    <h5 className="text-xs font-semibold text-primary">
      {children}
    </h5>
  ),
  h4: ({ children }: MarkdownParagraphProps) => (
    <h6 className="text-xs font-semibold text-primary">
      {children}
    </h6>
  ),
  h5: ({ children }: MarkdownParagraphProps) => (
    <h6 className="text-xs font-semibold text-primary">
      {children}
    </h6>
  ),
  h6: ({ children }: MarkdownParagraphProps) => (
    <h6 className="text-xs font-semibold text-primary">
      {children}
    </h6>
  ),
  ul: ({ children }: MarkdownListProps) => (
    <ul className="list-disc pl-4 space-y-1 text-xs text-secondary">
      {children}
    </ul>
  ),
  ol: ({ children }: MarkdownOrderedListProps) => (
    <ol className="list-decimal pl-4 space-y-1 text-xs text-secondary">
      {children}
    </ol>
  ),
  li: ({ children }: MarkdownListItemProps) => (
    <li className="text-xs text-secondary leading-5">
      {children}
    </li>
  ),
  strong: ({ children }: MarkdownStrongProps) => (
    <strong className="font-semibold text-primary">
      {children}
    </strong>
  ),
  em: ({ children }: MarkdownEmProps) => (
    <em className="italic text-secondary">
      {children}
    </em>
  ),
  a: ({ href, children, ...props }: MarkdownLinkProps) => (
    <a
      className="text-accent-primary underline decoration-accent-primary/40 underline-offset-2 hover:decoration-accent-primary"
      href={href}
      target="_blank"
      rel="noreferrer"
      {...props}
    >
      {children}
    </a>
  ),
  code: ({ className, children, ...props }: MarkdownCodeProps) => {
    if (!className) {
      return (
        <code
          className="rounded bg-surface-panel border border-normal px-1 py-0.5 text-[11px] font-mono text-primary"
          {...props}
        >
          {children}
        </code>
      )
    }
    return (
      <code className="text-[11px] font-mono text-primary" {...props}>
        {children}
      </code>
    )
  },
  pre: ({ children }: MarkdownPreProps) => (
    <pre className="rounded-[10px] bg-surface-panel border border-normal p-2 text-[11px] leading-4 text-primary overflow-x-auto whitespace-pre-wrap break-words">
      {children}
    </pre>
  ),
  blockquote: ({ children }: MarkdownBlockquoteProps) => (
    <blockquote className="border-l-2 border-border-normal pl-3 text-xs text-secondary">
      {children}
    </blockquote>
  ),
  hr: () => (
    <hr className="border-border-normal/60" />
  ),
}

interface SessionsTabProps {
  onClose: () => void
}

interface AgentsTabProps {
  onClose: () => void
}

interface ModelsTabProps {
  onClose: () => void
}

interface SkillsTabProps {
  onClose: () => void
}

interface ToolsTabProps {
  onClose: () => void
}

interface AccountsTabProps {
  onClose: () => void
}

interface SettingsTabProps {
  onClose: () => void
}

interface InfoTabProps {
  onClose: () => void
}

/**
 * Sessions Tab Panel
 * Lists available sessions with search functionality
 */
function SessionsTab({ onClose }: SessionsTabProps) {
  const sessions = useStore((state) => state.sessions)
  const currentSession = useCurrentSession()
  const setCurrentSession = useSetCurrentSession()
  const { createSession, deleteSession } = useSessions()
  const [creating, setCreating] = useState(false)

  const handleCreate = async () => {
    setCreating(true)
    try {
      const session = await createSession(`Session ${Date.now()}`)
      setCurrentSession(session)
    } catch (error) {
      console.error('Failed to create session:', error)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (sessionId: string) => {
    try {
      await deleteSession(sessionId)
    } catch (error) {
      console.error('Failed to delete session:', error)
    }
  }

  return (
    <div className="p-2 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-secondary uppercase tracking-widest">Sessions</span>
        <span className="absolute right-2 bottom-2">
          <button className="inline-flex items-center gap-2 border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10 text-xs text-primary bg-accent-primary" onClick={handleCreate} disabled={creating}>
            New
          </button>
          <button className="inline-flex items-center gap-2 border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10 text-xs text-primary bg-accent-primary absolute right-2 bottom-2" onClick={onClose} title="Close drawer (Esc)">
            ×
          </button>
        </span>
      </div>
      {sessions.length === 0 ? (
        <div className="text-xs text-primary bg-accent-primary border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10">No sessions yet</div>
      ) : (
        sessions.map((session) => (
          <div key={session.id} className={`w-full text-left bg-transparent border border-transparent rounded-[14px] text-primary font-mono text-[13px] cursor-pointer transition-all duration-150 ease-in-out flex items-center gap-2 p-0 hover:bg-[rgba(99,102,241,0.05)] hover:border-normal focus-visible:outline-2 focus-visible:outline-focus focus-visible:-outline-offset-2 ${currentSession?.id === session.id ? 'border-accent-primary bg-[rgba(99,102,241,0.08)]' : ''}`}>
            <button
              className="flex-1 text-left px-3 bg-transparent border-transparent text-primary font-mono cursor-pointer"
              onClick={() => setCurrentSession(session)}
            >
              <span className="font-medium text-[13px]">{session.title}</span>
            </button>
            <button
              className="mr-2 px-[6px_10px] border border-normal border-transparent text-secondary text-xs cursor-pointer transition-all duration-150 ease-in-out hover:text-primary hover:border-accent-primary"
              onClick={() => handleDelete(session.id)}
              title="Delete session"
            >
              Delete
            </button>
          </div>
        ))
      )}
    </div>
  )
}

/**
 * Agents Tab Panel
 * Agent management and configuration (from PRD section 14)
 */
function AgentsTab({ onClose }: AgentsTabProps) {
  const agents = useAgentsState()
  const selectedAgent = useSelectedAgent()
  const setSelectedAgent = useSetSelectedAgent()

  return (
    <div className="p-2 flex flex-col gap-2" role="listbox" aria-label="Agents">
      <div className="flex items-center justify-between">
        <span className="text-xs text-secondary uppercase tracking-widest">Agents</span>
        <span className="absolute right-2 bottom-2">
          <button className="inline-flex items-center gap-2 border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10 text-xs text-primary bg-accent-primary" onClick={onClose} title="Close drawer (Esc)">
            ×
          </button>
        </span>
      </div>
      {agents.length === 0 ? (
        <div className="text-xs text-primary bg-accent-primary border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10">No agents available</div>
      ) : (
        agents.map((agent, index) => (
          <button
            key={agent.name}
            className={`w-full text-left px-3 py-3 border rounded-[14px] text-primary cursor-pointer transition-all duration-150 ease-in-out focus-visible:outline-2 focus-visible:outline-focus focus-visible:-outline-offset-2 ${selectedAgent === agent.name ? 'border-accent-primary bg-[rgba(99,102,241,0.08)]' : 'border-normal hover:bg-[rgba(99,102,241,0.05)]'}`}
            onClick={() => setSelectedAgent(agent.name)}
            role="option"
            aria-selected={selectedAgent === agent.name}
            data-agent-index={index}
          >
            <div className="font-semibold text-sm text-primary">{agent.name}</div>
            <div className="text-xs text-secondary mt-2">
              <ReactMarkdown components={drawerMarkdownComponents} remarkPlugins={[remarkGfm]}>{agent.description}</ReactMarkdown>
            </div>
          </button>
        ))
      )}
    </div>
  )
}

function ModelsTab({ onClose }: ModelsTabProps) {
  const models = useModelsState()
  const selectedModel = useSelectedModel()
  const setSelectedModel = useSetSelectedModel()

  return (
    <div className="p-2 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-secondary uppercase tracking-widest">Models</span>
        <span className="absolute right-2 bottom-2">
          <button className="inline-flex items-center gap-2 border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10 text-xs text-primary bg-accent-primary" onClick={onClose} title="Close drawer (Esc)">
            ×
          </button>
        </span>
      </div>
      {models.length === 0 ? (
        <div className="text-xs text-primary bg-accent-primary border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10">No models configured</div>
      ) : (
        models.map((model) => (
          <button
            key={`${model.name}-${model.model}`}
            className={`w-full text-left px-3 bg-transparent border border-transparent rounded-[14px] text-primary font-mono text-[13px] cursor-pointer transition-all duration-150 ease-in-out hover:bg-[rgba(99,102,241,0.05)] hover:border-normal focus-visible:outline-2 focus-visible:outline-focus focus-visible:-outline-offset-2 ${selectedModel === model.model ? 'border-accent-primary bg-[rgba(99,102,241,0.08)]' : ''}`}
            onClick={() => setSelectedModel(model.model || null)}
          >
            <div className="font-medium text-[13px]">{model.model || 'Unknown model'}</div>
            <div className="text-xs text-secondary mt-0.5">
              {model.provider_id || 'Unknown provider'}{model.is_default ? ' • Default' : ''}
            </div>
          </button>
        ))
      )}
    </div>
  )
}

function SkillsTab({ onClose }: SkillsTabProps) {
  const skills = useSkillsState()
  const selectedSkills = useSelectedSkills()
  const setSelectedSkills = useSetSelectedSkills()

  const toggleSkill = (name: string) => {
    if (selectedSkills.includes(name)) {
      setSelectedSkills(selectedSkills.filter((skill) => skill !== name))
      return
    }
    setSelectedSkills([...selectedSkills, name])
  }

  return (
    <div className="p-2 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-secondary uppercase tracking-widest">Skills</span>
        <span className="absolute right-2 bottom-2">
          <button className="inline-flex items-center gap-2 border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10 text-xs text-primary bg-accent-primary" onClick={onClose} title="Close drawer (Esc)">
            ×
          </button>
        </span>
      </div>
      {skills.length === 0 ? (
        <div className="text-xs text-primary bg-accent-primary border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10">No skills found</div>
      ) : (
        skills.map((skill) => (
          <label key={skill.name} className="flex items-start gap-2 p-3 border border-normal rounded-[14px] bg-transparent cursor-pointer">
            <input
              type="checkbox"
              checked={selectedSkills.includes(skill.name)}
              onChange={() => toggleSkill(skill.name)}
              className="mt-0.5"
            />
            <div>
              <div className="font-semibold text-sm text-primary">{skill.name}</div>
              <div className="text-xs text-secondary mt-2">
                <ReactMarkdown components={drawerMarkdownComponents} remarkPlugins={[remarkGfm]}>{skill.description}</ReactMarkdown>
              </div>
            </div>
          </label>
        ))
      )}
    </div>
  )
}

function ToolsTab({ onClose }: ToolsTabProps) {
  const tools = useToolsState()

  return (
    <div className="p-2 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-secondary uppercase tracking-widest">Tools</span>
        <span className="absolute right-2 bottom-2">
          <button className="inline-flex items-center gap-2 border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10 text-xs text-primary bg-accent-primary" onClick={onClose} title="Close drawer (Esc)">
            ×
          </button>
        </span>
      </div>
      {tools.length === 0 ? (
        <div className="text-xs text-primary bg-accent-primary border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10">No tools available</div>
      ) : (
        tools.map((tool) => (
          <div key={tool.id} className="flex flex-col gap-2 p-3 border border-normal rounded-[14px] bg-transparent">
            <div className="font-semibold text-sm text-primary">{tool.id}</div>
            <div className="text-xs text-secondary mt-0.5">
              <ReactMarkdown components={drawerMarkdownComponents} remarkPlugins={[remarkGfm]}>
                {tool.description}
              </ReactMarkdown>
            </div>
          </div>
        ))
      )}
    </div>
  )
}

function AccountsTab({ onClose }: AccountsTabProps) {
  const accounts = useAccountsState()
  const selectedAccount = useSelectedAccount()
  const setSelectedAccount = useSetSelectedAccount()
  const { createAccount, deleteAccount, setDefaultAccount } = useAccounts()
  const [formState, setFormState] = useState({
    name: '',
    provider_id: '',
    model: '',
    api_key: '',
  })
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!formState.name || !formState.provider_id || !formState.model) return
    setSubmitting(true)
    try {
      const created = await createAccount({
        name: formState.name,
        provider_id: formState.provider_id,
        model: formState.model,
        api_key: formState.api_key || undefined,
        is_default: accounts.length === 0,
      })
      setSelectedAccount(created.name)
      setFormState({ name: '', provider_id: '', model: '', api_key: '' })
    } catch (error) {
      console.error('Failed to create account:', error)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="p-2 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-secondary uppercase tracking-widest">Accounts</span>
        <span className="absolute right-2 bottom-2">
          <button className="inline-flex items-center gap-2 border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10 text-xs text-primary bg-accent-primary" onClick={onClose} title="Close drawer (Esc)">
            ×
          </button>
        </span>
      </div>
      {accounts.length === 0 ? (
        <div className="text-xs text-primary bg-accent-primary border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10">No accounts configured</div>
      ) : (
        accounts.map((account) => (
          <div key={account.name} className={`w-full text-left bg-transparent border border-transparent rounded-[14px] text-primary font-mono text-[13px] cursor-pointer transition-all duration-150 ease-in-out flex items-center gap-2 p-0 hover:bg-[rgba(99,102,241,0.05)] hover:border-normal focus-visible:outline-2 focus-visible:outline-focus focus-visible:-outline-offset-2 ${selectedAccount === account.name ? 'border-accent-primary bg-[rgba(99,102,241,0.08)]' : ''}`}>
            <button
              className="flex-1 text-left px-3 bg-transparent border-transparent text-primary font-mono cursor-pointer"
              onClick={() => setSelectedAccount(account.name)}
            >
              <span className="font-medium text-[13px]">{account.name}</span>
              <span className="text-xs text-secondary mt-0.5">
                {account.config.provider_id || 'provider'} • {account.config.model || 'model'}
                {account.is_default ? ' • Default' : ''}
              </span>
            </button>
            <button
              className="mr-2 px-[6px_10px] border border-normal border-transparent text-secondary text-xs cursor-pointer transition-all duration-150 ease-in-out hover:text-primary hover:border-accent-primary"
              onClick={() => setDefaultAccount(account.name)}
              title="Set default"
            >
              Default
            </button>
            <button
              className="mr-2 px-[6px_10px] border border-normal border-transparent text-secondary text-xs cursor-pointer transition-all duration-150 ease-in-out hover:text-primary hover:border-accent-primary"
              onClick={() => deleteAccount(account.name)}
              title="Delete account"
            >
              Delete
            </button>
          </div>
        ))
      )}

      <div className="flex flex-col gap-2 p-2 border-t border-normal">
        <div className="text-xs text-secondary uppercase tracking-widest">Add account</div>
        <input
          className="px-[10px] py-2 rounded-[14px] border border-normal bg-surface-muted text-primary font-mono text-[13px] focus:outline-2 focus:outline-focus focus:-outline-offset-2"
          placeholder="Account name"
          value={formState.name}
          onChange={(event) => setFormState({ ...formState, name: event.target.value })}
        />
        <input
          className="px-[10px] py-2 rounded-[14px] border border-normal bg-surface-muted text-primary font-mono text-[13px] focus:outline-2 focus:outline-focus focus:-outline-offset-2"
          placeholder="Provider ID"
          value={formState.provider_id}
          onChange={(event) => setFormState({ ...formState, provider_id: event.target.value })}
        />
        <input
          className="px-[10px] py-2 rounded-[14px] border border-normal bg-surface-muted text-primary font-mono text-[13px] focus:outline-2 focus:outline-focus focus:-outline-offset-2"
          placeholder="Model ID"
          value={formState.model}
          onChange={(event) => setFormState({ ...formState, model: event.target.value })}
        />
        <input
          className="px-[10px] py-2 rounded-[14px] border border-normal bg-surface-muted text-primary font-mono text-[13px] focus:outline-2 focus:outline-focus focus:-outline-offset-2"
          placeholder="API key (optional)"
          type="password"
          value={formState.api_key}
          onChange={(event) => setFormState({ ...formState, api_key: event.target.value })}
        />
        <button className="w-full text-left px-3 bg-transparent border border-transparent rounded-[14px] text-primary font-mono text-[13px] cursor-pointer transition-all duration-150 ease-in-out hover:bg-[rgba(99,102,241,0.05)] hover:border-normal focus-visible:outline-2 focus-visible:outline-focus focus-visible:-outline-offset-2" onClick={handleSubmit} disabled={submitting}>
          {submitting ? 'Adding...' : 'Add account'}
        </button>
      </div>
    </div>
  )
}

/**
 * Settings Tab Panel
 * Theme toggle and model status (from PRD section 4)
 */
function SettingsTab({ onClose }: SettingsTabProps) {
  const theme = useStore((state) => state.theme)
  const setTheme = useStore((state) => state.setTheme)

  return (
    <div className="p-2 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-secondary uppercase tracking-widest">Settings</span>
        <span className="absolute right-2 bottom-2">
          <button className="inline-flex items-center gap-2 border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10 text-xs text-primary bg-accent-primary" onClick={onClose} title="Close drawer (Esc)">
            ×
          </button>
        </span>
      </div>
      <div className="text-xs text-primary bg-accent-primary border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10">Mode: {theme === 'dark' ? 'Dark' : 'Light'}</div>
      <button className="w-full text-left px-3 bg-transparent border border-transparent rounded-[14px] text-primary font-mono text-[13px] cursor-pointer transition-all duration-150 ease-in-out hover:bg-[rgba(99,102,241,0.05)] hover:border-normal focus-visible:outline-2 focus-visible:outline-focus focus-visible:-outline-offset-2" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
        Toggle Mode
      </button>
      <ThemePicker />
    </div>
  )
}

/**
 * Info Tab Panel
 * About, help links, and credits (from PRD section 5)
 */
function InfoTab({ onClose }: InfoTabProps) {
  return (
    <div className="p-2 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-secondary uppercase tracking-widest">Info</span>
        <span className="absolute right-2 bottom-2">
          <button className="inline-flex items-center gap-2 border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10 text-xs text-primary bg-accent-primary" onClick={onClose} title="Close drawer (Esc)">
            ×
          </button>
        </span>
      </div>
      <div className="text-xs text-primary bg-accent-primary border border-accent-primary rounded-[999px] cursor-pointer transition-all duration-200 ease-in-out z-10">About and Help</div>
    </div>
  )
}

/**
 * RightDrawer Component
 * Overlay drawer with stacked vertical tabs
 * Trigger: Ctrl+D
 * Tab content:
 * - Sessions: Session list
 * - Agents: Agent management (PRD section 14)
 * - Settings: Theme toggle (PRD section 4)
 * - Info: About and help (PRD section 5)
 */
export default function RightDrawer() {
  const drawerOpen = useStore((state) => state.drawerOpen)
  const drawerTab = useStore((state) => state.drawerTab) as DrawerTab
  const setDrawerTab = useSetDrawerTab()
  const setDrawerOpen = useSetDrawerOpen()
  const agents = useAgentsState()
  const selectedAgent = useSelectedAgent()
  const setSelectedAgent = useSetSelectedAgent()

  // Handle keyboard navigation (Left/Right arrows)
  useEffect(() => {
    if (!drawerOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        const tabs: DrawerTab[] = ['sessions', 'agents', 'models', 'skills', 'tools', 'accounts', 'settings', 'info']
        const currentIndex = tabs.indexOf(drawerTab)
        const nextIndex = (currentIndex + 1) % tabs.length
        setDrawerTab(tabs[nextIndex])
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        const tabs: DrawerTab[] = ['sessions', 'agents', 'models', 'skills', 'tools', 'accounts', 'settings', 'info']
        const currentIndex = tabs.indexOf(drawerTab)
        const prevIndex = (currentIndex - 1 + tabs.length) % tabs.length
        setDrawerTab(tabs[prevIndex])
      } else if (e.key === 'Escape') {
        e.preventDefault()
        setDrawerOpen(false)
      } else if (e.key === 'Tab' && drawerTab === 'agents') {
        e.preventDefault()
        if (agents.length === 0) return
        const currentIndex = agents.findIndex((agent) => agent.name === selectedAgent)
        const nextIndex = (currentIndex + 1) % agents.length
        setSelectedAgent(agents[nextIndex].name)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [drawerOpen, drawerTab, setDrawerTab, setDrawerOpen, agents, selectedAgent, setSelectedAgent])

  // Handle click outside to close
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      setDrawerOpen(false)
    }
  }

  if (!drawerOpen) return null

  const tabs = [
    { id: 'sessions' as DrawerTab, label: 'Sessions' },
    { id: 'agents' as DrawerTab, label: 'Agents' },
    { id: 'models' as DrawerTab, label: 'Models' },
    { id: 'skills' as DrawerTab, label: 'Skills' },
    { id: 'tools' as DrawerTab, label: 'Tools' },
    { id: 'accounts' as DrawerTab, label: 'Accounts' },
    { id: 'settings' as DrawerTab, label: 'Settings' },
    { id: 'info' as DrawerTab, label: 'Info' },
  ]

  const tabComponents = {
    sessions: <SessionsTab onClose={() => setDrawerOpen(false)} />,
    agents: <AgentsTab onClose={() => setDrawerOpen(false)} />,
    models: <ModelsTab onClose={() => setDrawerOpen(false)} />,
    skills: <SkillsTab onClose={() => setDrawerOpen(false)} />,
    tools: <ToolsTab onClose={() => setDrawerOpen(false)} />,
    accounts: <AccountsTab onClose={() => setDrawerOpen(false)} />,
    settings: <SettingsTab onClose={() => setDrawerOpen(false)} />,
    info: <InfoTab onClose={() => setDrawerOpen(false)} />,
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[1000] flex items-center justify-end md:items-center md:justify-end" onClick={handleOverlayClick}>
      <div className="panel w-[35vw] min-w-[320px] max-w-[600px] h-[90vh] bg-surface-raised border-l border-normal flex flex-col shadow-[0_0_30px_rgba(0,0,0,0.3)] animate-slide-in md:w-[35vw] md:min-w-[320px] md:max-w-[600px] md:h-[90vh] max-sm:w-full max-sm:min-w-0 max-sm:h-screen" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex flex-col border-b border-normal gap-0">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`px-4 py-3 md:px-4 md:py-3 text-left bg-transparent border-transparent text-secondary font-mono text-[13px] font-normal cursor-pointer transition-all duration-150 ease-in-out rounded-0 relative z-10 hover:text-primary hover:bg-[rgba(99,102,241,0.05)] focus-visible:outline-2 focus-visible:outline-focus focus-visible:-outline-offset-2 ${drawerTab === tab.id ? 'text-accent-primary font-medium border-accent-primary' : ''}`}
              onClick={() => setDrawerTab(tab.id)}
              aria-selected={drawerTab === tab.id}
              role="tab"
            >
              {drawerTab === tab.id && (
                <span className="absolute left-0 top-[50%] -translate-y-[50%] w-[3px] h-[60%] bg-accent-primary rounded-r-[2px]"></span>
              )}
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-0 flex flex-col">
          {tabComponents[drawerTab]}
        </div>
      </div>
      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .animate-slide-in {
          animation: slideIn 0.2s ease-out;
        }
        @media (prefers-reduced-motion: reduce) {
          .animate-slide-in {
            animation: none;
          }
        }
      `}</style>
    </div>
  )
}
