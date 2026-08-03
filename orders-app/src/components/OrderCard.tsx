import { motion, useMotionValue, useTransform } from 'framer-motion'
import { CalendarClock, ChevronRight } from 'lucide-react'
import type { Client, Order, Source } from '../db/types'
import { ORDER_STATUS_SHORT, ORDER_STATUS_TONE } from '../db/types'
import { balance, daysLeft } from '../lib/calc'
import { cn, formatDeadline, money } from '../lib/utils'
import { Pill } from '../ui/Pill'

interface Props {
  order: Order
  client?: Client
  source?: Source
  onClick?: () => void
  /** Свайп по карточке — быстрая смена статуса на следующий. */
  onSwipe?: () => void
  swipeHint?: string
}

/**
 * Карточка заказа: клиент и статус сверху, услуга ниже,
 * снизу деньги и срок. Просрочка — тонкая полоса слева, не заливка.
 */
export function OrderCard({ order, client, source, onClick, onSwipe, swipeHint }: Props) {
  const left = daysLeft(order)
  const overdue = left !== null && left < 0
  const dueToday = left === 0
  const rest = balance(order)

  const x = useMotionValue(0)
  const hintOpacity = useTransform(x, [0, 60, 110], [0, 0.5, 1])

  return (
    <div className="relative">
      {/* Подсказка, которая проступает под карточкой при свайпе */}
      {onSwipe && (
        <motion.div
          style={{ opacity: hintOpacity }}
          className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-caption font-medium text-accent"
        >
          {swipeHint}
        </motion.div>
      )}

      <motion.article
        drag={onSwipe ? 'x' : false}
        style={{ x }}
        dragDirectionLock
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={{ left: 0.02, right: 0.5 }}
        onDragEnd={(_, info) => {
          if (info.offset.x > 96) onSwipe?.()
        }}
        whileTap={onClick ? { scale: 0.99 } : undefined}
        transition={{ duration: 0.12 }}
        onClick={onClick}
        className={cn(
          'relative overflow-hidden rounded-card border border-line bg-surface p-4 shadow-soft',
          'transition-colors duration-150 ease-out',
          onClick && 'cursor-pointer hover:border-accent/30',
        )}
      >
        {/* Тонкая цветная полоса слева: просрочено / сегодня */}
        {(overdue || dueToday) && (
          <span
            className={cn(
              'absolute inset-y-0 left-0 w-[3px] rounded-r-full',
              overdue ? 'bg-danger' : 'bg-warn',
            )}
          />
        )}

        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-body-lg font-semibold tracking-tight">
              {client?.name ?? 'Без клиента'}
            </h3>
            <p className="mt-0.5 truncate text-body text-muted">{order.service || 'Без описания'}</p>
          </div>
          <Pill tone={ORDER_STATUS_TONE[order.status]}>{ORDER_STATUS_SHORT[order.status]}</Pill>
        </div>

        <div className="mt-3.5 flex items-end justify-between gap-3">
          <div className="min-w-0">
            <div className="tnum text-body-lg font-semibold">{money(order.amount)}</div>
            {rest > 0 && order.status !== 'rejected' && (
              <div className="tnum mt-0.5 text-caption text-muted">
                Остаток {money(rest)}
              </div>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-3">
            <div
              className={cn(
                'flex items-center gap-1.5 text-caption font-medium',
                overdue ? 'text-danger' : dueToday ? 'text-warn' : 'text-muted',
              )}
            >
              {order.deadline && left !== null && <CalendarClock size={14} />}
              <span>{left === null ? (source?.name ?? 'Без источника') : formatDeadline(order.deadline)}</span>
            </div>
            {onClick && <ChevronRight size={16} className="text-muted/60" />}
          </div>
        </div>

        {source && left !== null && (
          <div className="mt-2.5 flex items-center gap-1.5 text-caption text-muted">
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: source.color }} />
            {source.name}
          </div>
        )}
      </motion.article>
    </div>
  )
}
