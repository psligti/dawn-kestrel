import { useHotkeys } from 'react-hotkeys-hook'
import { useStore, useSetLeftDashboardOpen, useSetLeftDashboardPinned } from '../store'

/**
 * Keyboard shortcuts hook for global shortcuts:
 * - Ctrl+K: Toggle command palette
 * - Ctrl+D: Toggle right drawer
 * - Ctrl+Shift+L: Toggle left dashboard
 * - Ctrl+Shift+P: Pin/unpin left dashboard
 * - Esc: Close palette and drawer
 * - Ctrl+Enter: Don't trigger palette when open (pass-through to forms)
 */
export function useKeyboardShortcuts() {
  const paletteOpen = useStore((state) => state.paletteOpen)
  const drawerOpen = useStore((state) => state.drawerOpen)
  const leftDashboardOpen = useStore((state) => state.leftDashboardOpen)
  const leftDashboardPinned = useStore((state) => state.leftDashboardPinned)
  const setPaletteOpen = useStore((state) => state.setPaletteOpen)
  const setDrawerOpen = useStore((state) => state.setDrawerOpen)
  const setLeftDashboardOpen = useSetLeftDashboardOpen()
  const setLeftDashboardPinned = useSetLeftDashboardPinned()

  // Ctrl+K: Toggle command palette
  useHotkeys('ctrl+k, meta+k', (event) => {
    event.preventDefault()
    setPaletteOpen(!paletteOpen)
    if (!paletteOpen) {
      setDrawerOpen(false)
    }
  }, {
    enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT'],
  })

  // Ctrl+D: Toggle right drawer
  useHotkeys('ctrl+d, meta+d', (event) => {
    event.preventDefault()
    setDrawerOpen(!drawerOpen)
    if (!drawerOpen) {
      setPaletteOpen(false)
    }
  }, {
    enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT'],
  })

  // Esc: Close palette and drawer
  useHotkeys('escape', (event) => {
    if (paletteOpen || drawerOpen) {
      event.preventDefault()
      setPaletteOpen(false)
      setDrawerOpen(false)
    }
  }, {
    enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT'],
  })

  // Ctrl+Shift+L: Toggle left dashboard
  useHotkeys('ctrl+shift+l, meta+shift+l', (event) => {
    event.preventDefault()
    const shouldOpen = !leftDashboardOpen
    setLeftDashboardOpen(shouldOpen)

    // Collision rule: on narrow screens (<1024px), opening left dashboard closes right drawer
    if (shouldOpen && window.innerWidth < 1024) {
      setDrawerOpen(false)
    }

    // Close palette when opening left dashboard
    if (shouldOpen) {
      setPaletteOpen(false)
    }
  }, {
    enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT'],
  })

  // Ctrl+Shift+P: Pin/unpin left dashboard
  useHotkeys('ctrl+shift+p, meta+shift+p', (event) => {
    event.preventDefault()
    setLeftDashboardPinned(!leftDashboardPinned)
    setPaletteOpen(false)
  }, {
    enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT'],
  })

  // Ctrl+Enter: Don't trigger palette when open (pass-through to forms)
  useHotkeys('ctrl+enter', (event) => {
    if (paletteOpen) {
      event.preventDefault()
      event.stopPropagation()
    }
  }, {
    enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT'],
  })
}
