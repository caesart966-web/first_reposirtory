import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../lib/utils'
import { Button, IconButton } from './Button'

interface Props {
  open: boolean
  onClose: () => void
  title?: string
  subtitle?: string
  children: ReactNode
  /** Прилипшая снизу панель — кнопка сохранения не уезжает под клавиатуру. */
  footer?: ReactNode
  className?: string
}

/**
 * Нижняя шторка (bottom sheet) — основной способ показывать формы.
 * Тянется вниз пальцем, закрывается по фону и по Esc.
 */
export function Sheet({ open, onClose, title, subtitle, children, footer, className }: Props) {
  // Пока шторка открыта — фон под ней не скроллится
  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = prev
      window.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            onClick={onClose}
            className="absolute inset-0 bg-[#0B0F17]/40 backdrop-blur-[2px]"
          />
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 32, stiffness: 340 }}
            drag="y"
            dragDirectionLock
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.4 }}
            onDragEnd={(_, info) => {
              if (info.offset.y > 120 || info.velocity.y > 600) onClose()
            }}
            className={cn(
              'relative flex max-h-[92dvh] w-full flex-col overflow-hidden rounded-t-[24px]',
              'border border-line bg-surface shadow-sheet sm:mb-6 sm:max-w-lg sm:rounded-[24px]',
              className,
            )}
          >
            {/* «Ручка» для перетаскивания */}
            <div className="flex shrink-0 justify-center pb-1 pt-3">
              <div className="h-1 w-10 rounded-full bg-line" />
            </div>

            {title && (
              <div className="flex shrink-0 items-start gap-3 px-5 pb-3 pt-1">
                <div className="min-w-0 flex-1">
                  <h2 className="text-title font-semibold tracking-tight">{title}</h2>
                  {subtitle && <p className="mt-0.5 text-caption text-muted">{subtitle}</p>}
                </div>
                <IconButton onClick={onClose} aria-label="Закрыть" className="-mr-2 -mt-1">
                  <X size={20} />
                </IconButton>
              </div>
            )}

            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-5">{children}</div>

            {footer && (
              <div className="shrink-0 border-t border-line bg-surface px-5 pb-[calc(16px+env(safe-area-inset-bottom,0px))] pt-4">
                {footer}
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}

/** Шторка-подтверждение вместо системного confirm(). */
export function ConfirmSheet({
  open,
  onClose,
  onConfirm,
  title,
  text,
  confirmLabel = 'Удалить',
  danger = true,
}: {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  text?: string
  confirmLabel?: string
  danger?: boolean
}) {
  return (
    <Sheet open={open} onClose={onClose} title={title}>
      {text && <p className="text-body text-muted">{text}</p>}
      <div className="mt-6 flex gap-3">
        <Button variant="secondary" full onClick={onClose}>
          Отмена
        </Button>
        <Button
          variant={danger ? 'danger' : 'primary'}
          full
          onClick={() => {
            onConfirm()
            onClose()
          }}
        >
          {confirmLabel}
        </Button>
      </div>
    </Sheet>
  )
}
