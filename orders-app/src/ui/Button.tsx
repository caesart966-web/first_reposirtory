import { motion } from 'framer-motion'
import type { ComponentProps, ReactNode } from 'react'
import { cn } from '../lib/utils'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'md' | 'lg' | 'sm'

const variants: Record<Variant, string> = {
  primary: 'bg-accent text-white shadow-soft hover:brightness-105 active:brightness-95',
  secondary: 'bg-surface text-ink border border-line hover:bg-surface-2',
  ghost: 'text-muted hover:bg-ink/5 hover:text-ink',
  danger: 'bg-danger/10 text-danger hover:bg-danger/15 dark:bg-danger/15',
}

const sizes: Record<Size, string> = {
  sm: 'h-9 px-3 text-caption rounded-chip',
  md: 'tap h-11 px-4 text-body rounded-btn',
  lg: 'tap h-13 px-5 text-body-lg rounded-btn min-h-[52px]',
}

interface Props extends Omit<ComponentProps<typeof motion.button>, 'children'> {
  variant?: Variant
  size?: Size
  full?: boolean
  icon?: ReactNode
  children?: ReactNode
}

/** Кнопка: при нажатии слегка проседает (scale 0.97). */
export function Button({
  variant = 'primary',
  size = 'md',
  full,
  icon,
  children,
  className,
  ...rest
}: Props) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      transition={{ duration: 0.12 }}
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium transition-colors duration-150 ease-out',
        'disabled:opacity-40 disabled:pointer-events-none select-none',
        variants[variant],
        sizes[size],
        full && 'w-full',
        className,
      )}
      {...rest}
    >
      {icon}
      {children}
    </motion.button>
  )
}

/** Круглая кнопка-иконка (закрыть, назад, меню). */
export function IconButton({
  className,
  children,
  ...rest
}: ComponentProps<typeof motion.button>) {
  return (
    <motion.button
      whileTap={{ scale: 0.94 }}
      transition={{ duration: 0.12 }}
      className={cn(
        'tap inline-flex items-center justify-center rounded-full text-muted',
        'transition-colors duration-150 ease-out hover:bg-ink/5 hover:text-ink',
        className,
      )}
      {...rest}
    >
      {children}
    </motion.button>
  )
}
