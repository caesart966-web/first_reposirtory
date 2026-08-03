import type { ReactNode } from 'react'
import { cn } from '../lib/utils'
import { Button } from './Button'

/** Пустое состояние: иконка, человеческая фраза, кнопка действия. */
export function EmptyState({
  icon,
  title,
  text,
  actionLabel,
  onAction,
  className,
}: {
  icon: ReactNode
  title: string
  text?: string
  actionLabel?: string
  onAction?: () => void
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center px-6 py-12 text-center', className)}>
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-card bg-surface-2 text-muted">
        {icon}
      </div>
      <h3 className="text-body-lg font-semibold tracking-tight">{title}</h3>
      {text && <p className="mt-1.5 max-w-xs text-body text-muted">{text}</p>}
      {actionLabel && onAction && (
        <Button className="mt-5" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}

/** Скелетон вместо спиннера, пока данные читаются из базы. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-chip bg-surface-2',
        'after:absolute after:inset-0 after:-translate-x-full after:animate-[shimmer_1.4s_infinite]',
        'after:bg-gradient-to-r after:from-transparent after:via-ink/[0.04] after:to-transparent',
        className,
      )}
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="rounded-card border border-line bg-surface p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-5 w-20 rounded-chip" />
      </div>
      <Skeleton className="mt-3 h-4 w-48" />
      <div className="mt-4 flex items-center justify-between">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-4 w-20" />
      </div>
    </div>
  )
}

export function SkeletonList({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}
