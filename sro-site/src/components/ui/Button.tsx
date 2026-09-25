import { ArrowUpRight } from 'lucide-react'
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from 'react'

// Кнопки — «пилюли», как в ориентирах заказчика (Apple, LeonHome).
//
// primary       — графит на светлом фоне, главное действие раздела;
// secondary     — контур на светлом, второе действие рядом с главным;
// inverse       — крем на тёмном фоне;
// outlineInverse — контур на тёмном.
//
// arrow — кружок со стрелкой справа внутри кнопки (приём из LeonHome и
// woodland). Ставится только на главное действие: стрелка в каждой кнопке
// перестаёт что-либо значить.
export type ButtonVariant = 'primary' | 'secondary' | 'inverse' | 'outlineInverse'
export type ButtonSize = 'md' | 'lg'

const VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-neutral-950 text-neutral-50 hover:bg-neutral-800',
  secondary:
    'border border-neutral-300 bg-transparent text-neutral-950 hover:border-neutral-950',
  inverse: 'bg-neutral-50 text-neutral-950 hover:bg-white focus-visible:ring-offset-0',
  outlineInverse:
    'border border-white/30 text-neutral-50 hover:border-white/70 focus-visible:ring-offset-0',
}

// Кружок стрелки красится от варианта: на тёмной кнопке — светлый, на
// светлой — тёмный. Иначе он сливается с фоном кнопки.
const ARROW: Record<ButtonVariant, string> = {
  primary: 'bg-neutral-50 text-neutral-950',
  secondary: 'bg-neutral-950 text-neutral-50',
  inverse: 'bg-neutral-950 text-neutral-50',
  outlineInverse: 'bg-neutral-50 text-neutral-950',
}

const SIZES: Record<ButtonSize, string> = {
  md: 'h-11 px-5 text-sm',
  lg: 'h-14 px-7 text-[15px]',
}

// С кружком справа отступ меньше: кружок сам работает полем.
const SIZES_ARROW: Record<ButtonSize, string> = {
  md: 'h-11 pl-5 pr-1.5 text-sm',
  lg: 'h-14 pl-7 pr-2 text-[15px]',
}

export function buttonClasses(
  variant: ButtonVariant = 'primary',
  size: ButtonSize = 'md',
  className = '',
  arrow = false,
): string {
  return [
    'group/btn inline-flex items-center justify-center gap-3 rounded-full font-medium transition-colors duration-500 ease-silk disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2',
    VARIANTS[variant],
    arrow ? SIZES_ARROW[size] : SIZES[size],
    className,
  ].join(' ')
}

function Arrow({ variant, size }: { variant: ButtonVariant; size: ButtonSize }) {
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full transition-transform duration-700 ease-silk group-hover/btn:rotate-45 ${
        size === 'lg' ? 'h-10 w-10' : 'h-8 w-8'
      } ${ARROW[variant]}`}
      aria-hidden="true"
    >
      <ArrowUpRight className="h-4 w-4" />
    </span>
  )
}

type Common = {
  variant?: ButtonVariant
  size?: ButtonSize
  /** Кружок со стрелкой справа — только у главного действия. */
  arrow?: boolean
  children: ReactNode
}

type ButtonLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & Common

export function ButtonLink({
  variant = 'primary',
  size = 'md',
  arrow = false,
  className = '',
  children,
  ...rest
}: ButtonLinkProps) {
  return (
    <a className={buttonClasses(variant, size, className, arrow)} {...rest}>
      {children}
      {arrow && <Arrow variant={variant} size={size} />}
    </a>
  )
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & Common

export function Button({
  variant = 'primary',
  size = 'md',
  arrow = false,
  className = '',
  type = 'button',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button type={type} className={buttonClasses(variant, size, className, arrow)} {...rest}>
      {children}
      {arrow && <Arrow variant={variant} size={size} />}
    </button>
  )
}
