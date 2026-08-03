import { motion } from 'framer-motion'
import type { ComponentProps, ReactNode } from 'react'
import { cn } from '../lib/utils'

interface CardProps extends ComponentProps<typeof motion.div> {
  /** Приподнятая карточка — чуть заметнее тень. */
  raised?: boolean
  /** Кликабельная — реагирует на нажатие. */
  pressable?: boolean
  children?: ReactNode
}

/** Базовая поверхность: белая (в тёмной теме — тёмно-серая), 16px скругление, мягкая тень. */
export function Card({ raised, pressable, className, children, ...rest }: CardProps) {
  return (
    <motion.div
      whileTap={pressable ? { scale: 0.985 } : undefined}
      transition={{ duration: 0.12 }}
      className={cn(
        'rounded-card border border-line bg-surface',
        raised ? 'shadow-lift' : 'shadow-soft',
        pressable && 'cursor-pointer transition-colors duration-150 ease-out hover:border-accent/30',
        className,
      )}
      {...rest}
    >
      {children}
    </motion.div>
  )
}

/** Заголовок раздела над группой карточек. */
export function SectionTitle({
  children,
  action,
}: {
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3 px-1">
      <h2 className="text-body-lg font-semibold tracking-tight">{children}</h2>
      {action}
    </div>
  )
}
