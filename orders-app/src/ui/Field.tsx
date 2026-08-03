import { forwardRef, type ComponentProps, type ReactNode } from 'react'
import { cn } from '../lib/utils'

export function Field({
  label,
  hint,
  children,
  className,
}: {
  label?: string
  hint?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <label className={cn('block', className)}>
      {label && <span className="mb-1.5 block text-caption font-medium text-muted">{label}</span>}
      {children}
      {hint && <span className="mt-1.5 block text-caption text-muted">{hint}</span>}
    </label>
  )
}

const base =
  'w-full rounded-btn border border-line bg-surface px-3.5 text-body text-ink placeholder:text-muted/70 ' +
  'transition-all duration-150 ease-out outline-none focus:border-accent focus:ring-2 focus:ring-accent/15'

export const Input = forwardRef<HTMLInputElement, ComponentProps<'input'>>(function Input(
  { className, ...rest },
  ref,
) {
  return <input ref={ref} className={cn(base, 'tap h-12', className)} {...rest} />
})

export const Textarea = forwardRef<HTMLTextAreaElement, ComponentProps<'textarea'>>(function Textarea(
  { className, ...rest },
  ref,
) {
  return <textarea ref={ref} className={cn(base, 'min-h-[88px] resize-none py-3', className)} {...rest} />
})

/** Поле поиска с иконкой слева. */
export function SearchInput({
  icon,
  className,
  ...rest
}: ComponentProps<'input'> & { icon?: ReactNode }) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted">
        {icon}
      </span>
      <input className={cn(base, 'tap h-12 pl-11', className)} {...rest} />
    </div>
  )
}
