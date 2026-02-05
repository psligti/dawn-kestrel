import { useMemo } from 'react'
import { CommandPalette, type Command } from './CommandPalette'
import RightDrawer from './RightDrawer'
import LeftDashboardDrawer from './LeftDashboardDrawer'
import { ComposerBar } from './ComposerBar'
import { StatusBar } from './StatusBar'
import { ThemeProvider } from './ThemeProvider'
import { TopBar } from './TopBar'
import { ConversationTimeline } from './ConversationTimeline'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { useSetPaletteOpen, useLeftDashboard, useSetDrawerOpen, useSetDrawerTab, useSetLeftDashboardOpen, useSetLeftDashboardPinned, useSetTelemetry, useCurrentSession } from '../store'
import { getApi } from '../hooks/useApiClient'
import type { TelemetryData } from '../store'
import './AppLayout.css'

export function AppLayout() {
  const setPaletteOpen = useSetPaletteOpen()
  const { open: leftDashboardOpen, pinned } = useLeftDashboard()
  const setLeftDashboardOpen = useSetLeftDashboardOpen()
  const setLeftDashboardPinned = useSetLeftDashboardPinned()
  const setDrawerOpen = useSetDrawerOpen()
  const setDrawerTab = useSetDrawerTab()
  const setTelemetry = useSetTelemetry()
  const currentSession = useCurrentSession()

  const commands = useMemo<Command[]>(() => [
    {
      id: 'toggle-left-dashboard',
      title: leftDashboardOpen ? 'Close Left Dashboard' : 'Open Left Dashboard',
      keywords: 'left dashboard sidebar panel toggle',
      run: () => {
        const shouldOpen = !leftDashboardOpen
        setLeftDashboardOpen(shouldOpen)
        if (shouldOpen && window.innerWidth < 1024) {
          setDrawerOpen(false)
        }
      },
    },
    {
      id: 'pin-left-dashboard',
      title: pinned ? 'Unpin Left Dashboard' : 'Pin Left Dashboard',
      keywords: 'left dashboard sidebar panel pin unpin',
      run: () => setLeftDashboardPinned(!pinned),
    },
    {
      id: 'open-drawer-tools',
      title: 'Open Tools Drawer',
      keywords: 'drawer right tools panel',
      run: () => {
        setDrawerOpen(true)
        setDrawerTab('tools')
      },
    },
    {
      id: 'open-drawer-sessions',
      title: 'Open Sessions Drawer',
      keywords: 'drawer right sessions panel',
      run: () => {
        setDrawerOpen(true)
        setDrawerTab('sessions')
      },
    },
    {
      id: 'open-drawer-agents',
      title: 'Open Agents Drawer',
      keywords: 'drawer right agents panel',
      run: () => {
        setDrawerOpen(true)
        setDrawerTab('agents')
      },
    },
    ...(currentSession ? [
      {
        id: 'refresh-telemetry',
        title: 'Refresh Telemetry',
        keywords: 'telemetry refresh update snapshot',
        run: async () => {
          try {
            const telemetry = await getApi<TelemetryData>(`/sessions/${currentSession.id}/telemetry`)
            setTelemetry(telemetry)
          } catch (error) {
            console.error('Failed to refresh telemetry:', error)
          }
        },
      },
    ] : []),
  ], [leftDashboardOpen, pinned, setLeftDashboardOpen, setLeftDashboardPinned, setDrawerOpen, setDrawerTab, setTelemetry, currentSession])

  useKeyboardShortcuts()

  return (
    <ThemeProvider>
      <div className="h-screen w-full flex bg-surface-base text-primary overflow-hidden">
        <LeftDashboardDrawer />
        <div className={`flex flex-col gap-2 p-2 overflow-hidden transition-all duration-200 ease-in-out ${pinned ? 'ml-64' : ''}`}>
          <TopBar />
          <ConversationTimeline />
          <ComposerBar />
          <StatusBar />
        </div>
        <CommandPalette commands={commands} onClose={() => setPaletteOpen(false)} />
        <RightDrawer />
      </div>
    </ThemeProvider>
  )
}
