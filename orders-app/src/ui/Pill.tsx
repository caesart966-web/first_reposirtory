import type { ReactNode } from 'react'
import type { Tone } from '../db/types'
import { cn } from '../lib/utils'
import { pillTone } from './tones'

interface Props {
  tone?: Tone
  children: ReactNode
  className?: string
  /** Цветная точка слева — для источников с произвольным цветом. */
  dotColor?: string
  size?: 'sm' | 'md'
}

/** Плашка-«пилюля»: мягкий фон, текст того же оттенка. */
export function Pill({ tone = 'neutral', children, className, dotColor, size = 'md' }: Props) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 rounded-chip font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-caption' : 'px-2.5 py-1 text-caption',
        pillTone[tone],
        className,
      )}
    >
      {dotColor && (
        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: dotColor }} />
      )}
      {children}
    </span>
  )
}
