import { useEffect, type ReactNode } from 'react'
import { markMounted } from './mounted'

// Обёртка корня каждой точки входа: отмечает, что страница подхвачена
// (lib/mounted.ts). Разметки не добавляет — готовая страница и подхваченная
// совпадают узел в узел.
export function Mounted({ children }: { children: ReactNode }) {
  useEffect(() => {
    markMounted()
  }, [])
  return <>{children}</>
}
