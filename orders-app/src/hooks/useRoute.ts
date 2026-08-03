import { useCallback, useEffect, useState } from 'react'

export type Tab = 'dashboard' | 'orders' | 'clients' | 'tasks' | 'settings'

export const TABS: Tab[] = ['dashboard', 'orders', 'clients', 'tasks', 'settings']

export interface Route {
  tab: Tab
  /** Параметры вида #/orders?status=in_work — фильтры при переходе с дашборда. */
  params: Record<string, string>
}

function parse(hash: string): Route {
  const clean = hash.replace(/^#\/?/, '')
  const [path, query = ''] = clean.split('?')
  const tab = (TABS as string[]).includes(path) ? (path as Tab) : 'dashboard'
  const params: Record<string, string> = {}
  new URLSearchParams(query).forEach((v, k) => (params[k] = v))
  return { tab, params }
}

/**
 * Простейшая навигация по адресу (#/orders). Так работает
 * системная кнопка «Назад» на Android.
 */
export function useRoute() {
  const [route, setRoute] = useState<Route>(() => parse(window.location.hash))

  useEffect(() => {
    const onChange = () => setRoute(parse(window.location.hash))
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  const navigate = useCallback((tab: Tab, params: Record<string, string> = {}) => {
    const query = new URLSearchParams(params).toString()
    const next = `#/${tab}${query ? `?${query}` : ''}`
    if (window.location.hash === next) setRoute(parse(next))
    else window.location.hash = next
  }, [])

  return { route, navigate }
}
