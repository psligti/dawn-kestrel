import { useMemo } from 'react'
import { CommandPalette } from './CommandPalette'
import RightDrawer from './RightDrawer'
import LeftDashboardDrawer from './LeftDashboardDrawer'
import { ComposerBar } from './ComposerBar'
import { StatusBar } from './StatusBar'
import { ThemeProvider } from './ThemeProvider'
import { TopBar } from './TopBar'
import { ConversationTimeline } from './ConversationTimeline'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { useSetPaletteOpen, useLeftDashboard } from '../store'
import './AppLayout.css'

export function AppLayout() {
  const commands = useMemo(() => [], [])
  const setPaletteOpen = useSetPaletteOpen()
  const { pinned } = useLeftDashboard()

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
