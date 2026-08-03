import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { DEFAULT_THEME, SETTING_KEYS, getSetting, setSetting } from '../db/repo'
import type { ThemeMode } from '../db/types'

interface ThemeCtx {
  mode: ThemeMode
  /** Что реально показано сейчас. */
  resolved: 'light' | 'dark'
  setMode: (mode: ThemeMode) => void
}

const Ctx = createContext<ThemeCtx>({ mode: 'system', resolved: 'light', setMode: () => {} })

export function useTheme() {
  return useContext(Ctx)
}

function systemDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(DEFAULT_THEME)
  const [resolved, setResolved] = useState<'light' | 'dark'>(() =>
    systemDark() ? 'dark' : 'light',
  )

  // Читаем сохранённую тему один раз при запуске
  useEffect(() => {
    getSetting<ThemeMode>(SETTING_KEYS.theme, DEFAULT_THEME).then(setModeState)
  }, [])

  // Применяем тему к <html> и красим строку состояния Android
  useEffect(() => {
    const apply = () => {
      const dark = mode === 'dark' || (mode === 'system' && systemDark())
      document.documentElement.classList.toggle('dark', dark)
      setResolved(dark ? 'dark' : 'light')
      const meta = document.querySelector('meta[name="theme-color"]')
      meta?.setAttribute('content', dark ? '#12151C' : '#F7F8FA')
    }
    apply()
    if (mode !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [mode])

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next)
    void setSetting(SETTING_KEYS.theme, next)
  }, [])

  return <Ctx.Provider value={{ mode, resolved, setMode }}>{children}</Ctx.Provider>
}
