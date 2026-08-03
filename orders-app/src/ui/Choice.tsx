import { motion } from 'framer-motion'
import type { ReactNode } from 'react'
import { cn } from '../lib/utils'

export interface ChoiceOption<T extends string> {
  value: T
  label: ReactNode
  /** Цвет точки (для источников). */
  color?: string
}

interface Props<T extends string> {
  options: Array<ChoiceOption<T>>
  value: T | null
  onChange: (value: T) => void
  /** В несколько рядов с переносом (по умолчанию) или в одну строку со скроллом. */
  wrap?: boolean
  className?: string
}

/**
 * Крупные кнопки-переключатели вместо выпадающих списков —
 * так выбор делается в один тап.
 */
export function Choice<T extends string>({ options, value, onChange, wrap = true, className }: Props<T>) {
  return (
    <div
      className={cn(
        wrap ? 'flex flex-wrap gap-2' : 'no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4',
        className,
      )}
    >
      {options.map((o) => {
        const active = o.value === value
        return (
          <motion.button
            key={o.value}
            type="button"
            whileTap={{ scale: 0.97 }}
            transition={{ duration: 0.12 }}
            onClick={() => onChange(o.value)}
            className={cn(
              'tap inline-flex shrink-0 items-center gap-2 rounded-btn border px-3.5 py-2.5 text-body font-medium',
              'transition-colors duration-150 ease-out',
              active
                ? 'border-accent bg-accent/10 text-accent dark:bg-accent/15'
                : 'border-line bg-surface text-muted hover:text-ink',
            )}
          >
            {o.color && (
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: o.color }} />
            )}
            {o.label}
          </motion.button>
        )
      })}
    </div>
  )
}
