import { useEffect } from 'react'
import { useHotkeys } from 'react-hotkeys-hook'
import { useStore } from '../store'

/**
 * Keyboard shortcuts hook for global shortcuts:
 * - Ctrl+K: Toggle command palette
 * - Ctrl+D: Toggle right drawer
 * - Esc: Close palette and drawer
 * - Ctrl+Enter: Don't trigger palette when open (pass-through to forms)
 */
export function useKeyboardShortcuts() {
  const paletteOpen = useStore((state) => state.paletteOpen)
  const drawerOpen = useStore((state) => state.drawerOpen)
  const setPaletteOpen = useStore((state) => state.setPaletteOpen)
  const setDrawerOpen = useStore((state) => state.setDrawerOpen)

  // Ctrl+K: Toggle command palette
  useHotkeys('ctrl+k, meta+k', (event) => {
    event.preventDefault()
    setPaletteOpen(!paletteOpen)
    if (!paletteOpen) {
      setDrawerOpen(false)
    }
  }, {
    enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT'],
    enableOnHiddenElements: true,
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
    enableOnHiddenElements: true,
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
    enableOnHiddenElements: true,
  })

  // Ctrl+Enter: Don't trigger palette when open (pass-through to forms)
  useHotkeys('ctrl+enter', (event) => {
    if (paletteOpen) {
      event.preventDefault()
      event.stopPropagation()
    }
  }, {
    enableOnFormTags: ['INPUT', 'TEXTAREA', 'SELECT'],
    enableOnHiddenElements: true,
  })
}
