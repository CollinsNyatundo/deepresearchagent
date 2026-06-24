import { useState, useEffect, createContext, useContext, type ReactNode } from 'react'

type BackgroundMode = 'moonlit' | 'silk' | 'rain' | 'solid'
type SolidColor = '#000000' | '#1a1a2e' | '#1a1308' | '#0d1f0d'

interface BackgroundState {
  mode: BackgroundMode
  solidColor: SolidColor
}

const STORAGE_KEY = 'dr-bg-mode'
const STORAGE_COLOR_KEY = 'dr-bg-solid'

function getInitialState(): BackgroundState {
  try {
    const savedMode = localStorage.getItem(STORAGE_KEY) as BackgroundMode | null
    const savedColor = localStorage.getItem(STORAGE_COLOR_KEY) as SolidColor | null
    return {
      mode: savedMode ?? 'solid',
      solidColor: savedColor ?? '#000000',
    }
  } catch {
    return { mode: 'solid', solidColor: '#000000' }
  }
}

interface BackgroundContextValue {
  state: BackgroundState
  setMode: (mode: BackgroundMode) => void
  setSolidColor: (color: SolidColor) => void
}

const BackgroundContext = createContext<BackgroundContextValue | null>(null)

export function BackgroundProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<BackgroundState>(getInitialState)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, state.mode)
  }, [state.mode])

  useEffect(() => {
    localStorage.setItem(STORAGE_COLOR_KEY, state.solidColor)
  }, [state.solidColor])

  const setMode = (mode: BackgroundMode) => setState((s) => ({ ...s, mode }))
  const setSolidColor = (solidColor: SolidColor) => setState((s) => ({ ...s, solidColor }))

  return (
    <BackgroundContext.Provider value={{ state, setMode, setSolidColor }}>
      {children}
    </BackgroundContext.Provider>
  )
}

export function useBackground() {
  const ctx = useContext(BackgroundContext)
  if (!ctx) throw new Error('useBackground must be used within BackgroundProvider')
  return ctx
}
