import { useEffect, useState } from 'react'
import { AppLayout } from './components/AppLayout'
import { useSessions } from './hooks/useSessions'
import { useCurrentSession } from './hooks/useCurrentSession'
import { useAgents } from './hooks/useAgents'
import { useTools } from './hooks/useTools'
import { useSkills } from './hooks/useSkills'
import { useModels } from './hooks/useModels'
import { useAccounts } from './hooks/useAccounts'
import { useMessages } from './hooks/useMessages'
import { useSessionThemeStream } from './hooks/useSessionThemeStream'
import { useSessionTelemetryStream } from './hooks/useSessionTelemetryStream'
import { useSelectedAgent, useSelectedAccount, useSelectedModel, useSetSelectedAgent, useSetSelectedAccount, useSetSelectedModel } from './store'

function App() {
  const { currentSession, setCurrent } = useCurrentSession()
  const { sessions, fetchSessions, createSession } = useSessions()
  const { fetchMessages } = useMessages()
  const { agents, fetchAgents } = useAgents()
  const { fetchTools } = useTools()
  const { fetchSkills } = useSkills()
  const { models, fetchModels } = useModels()
  const { accounts, fetchAccounts } = useAccounts()
  const selectedAgent = useSelectedAgent()
  const selectedModel = useSelectedModel()
  const selectedAccount = useSelectedAccount()
  const setSelectedAgent = useSetSelectedAgent()
  const setSelectedModel = useSetSelectedModel()
  const setSelectedAccount = useSetSelectedAccount()
  const [sessionsLoaded, setSessionsLoaded] = useState(false)

  useSessionThemeStream({ sessionId: currentSession?.id || '' })
  useSessionTelemetryStream({ sessionId: currentSession?.id || '' })

  useEffect(() => {
    let isMounted = true

    fetchSessions()
      .then(() => {
        if (isMounted) {
          setSessionsLoaded(true)
        }
      })
      .catch((error) => {
        console.error('Failed to load sessions:', error)
        if (isMounted) {
          setSessionsLoaded(true)
        }
      })

    fetchAgents().catch((error) => console.error('Failed to load agents:', error))
    fetchTools().catch((error) => console.error('Failed to load tools:', error))
    fetchSkills().catch((error) => console.error('Failed to load skills:', error))
    fetchModels().catch((error) => console.error('Failed to load models:', error))
    fetchAccounts().catch((error) => console.error('Failed to load accounts:', error))

    return () => {
      isMounted = false
    }
  }, [fetchAccounts, fetchAgents, fetchModels, fetchSessions, fetchSkills, fetchTools])

  useEffect(() => {
    if (!sessionsLoaded) return
    if (currentSession) return

    if (sessions.length === 0) {
      createSession('Default Session')
        .then((session) => {
          setCurrent(session)
        })
        .catch((error) => console.error('Failed to create default session:', error))
      return
    }

    setCurrent(sessions[0])
  }, [createSession, currentSession, sessions, sessionsLoaded, setCurrent])

  useEffect(() => {
    if (!currentSession) return
    fetchMessages(currentSession.id).catch((error) => console.error('Failed to load messages:', error))
  }, [currentSession, fetchMessages])

  useEffect(() => {
    if (!selectedAgent && agents.length > 0) {
      setSelectedAgent(agents[0].name)
    }
  }, [agents, selectedAgent, setSelectedAgent])

  useEffect(() => {
    if (!selectedModel && models.length > 0) {
      const defaultModel = models.find((model) => model.is_default)?.model
      setSelectedModel(defaultModel || models[0].model || null)
    }
  }, [models, selectedModel, setSelectedModel])

  useEffect(() => {
    if (!selectedAccount && accounts.length > 0) {
      const defaultAccount = accounts.find((account) => account.is_default)?.name
      setSelectedAccount(defaultAccount || accounts[0].name)
    }
  }, [accounts, selectedAccount, setSelectedAccount])

  return (
    <AppLayout />
  )
}

export default App
