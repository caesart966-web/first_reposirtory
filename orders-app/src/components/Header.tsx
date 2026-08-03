import type { ReactNode } from 'react'

/** Шапка экрана: крупный заголовок слева, действие справа. */
export function Header({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <header className="flex items-start justify-between gap-3 px-4 pb-4 pt-5">
      <div className="min-w-0">
        <h1 className="text-title-lg font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-0.5 text-caption text-muted">{subtitle}</p>}
      </div>
      {action}
    </header>
  )
}
