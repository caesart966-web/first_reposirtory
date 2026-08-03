import { CLOSED_STATUSES, type Order } from '../db/types'
import { daysFromToday } from './utils'

// ─────────────────────────────────────────────────────────────────
// Производные величины заказа. Их НЕ храним в базе — считаем на лету,
// чтобы данные всегда сходились.
// ─────────────────────────────────────────────────────────────────

/** Комиссия площадки, ₽. */
export function commission(o: Pick<Order, 'amount' | 'commissionRate'>): number {
  return o.amount * o.commissionRate
}

/** Сколько получу на руки, ₽. */
export function net(o: Pick<Order, 'amount' | 'commissionRate'>): number {
  return o.amount - commission(o)
}

/** Сколько ещё должны, ₽ (сумма минус аванс, не меньше нуля). */
export function balance(o: Pick<Order, 'amount' | 'prepayment'>): number {
  return Math.max(0, o.amount - o.prepayment)
}

/**
 * Сколько дней до дедлайна. null — если срока нет или заказ уже закрыт
 * (оплачен либо отказ): для них сроки не считаем.
 */
export function daysLeft(o: Pick<Order, 'deadline' | 'status'>): number | null {
  if (!o.deadline) return null
  if (CLOSED_STATUSES.includes(o.status)) return null
  return daysFromToday(o.deadline)
}

/** Просрочен: срок в прошлом и заказ ещё в работе. */
export function isOverdue(o: Pick<Order, 'deadline' | 'status'>): boolean {
  const d = daysLeft(o)
  return d !== null && d < 0
}

/** Горит сегодня. */
export function isDueToday(o: Pick<Order, 'deadline' | 'status'>): boolean {
  return daysLeft(o) === 0
}

/** Заказ активен: деньги ещё в работе (не оплачен и не отказ). */
export function isActive(o: Pick<Order, 'status'>): boolean {
  return !CLOSED_STATUSES.includes(o.status)
}

export interface Totals {
  /** Сколько ещё должны получить по всем незакрытым заказам. */
  outstanding: number
  /** Деньги в работе: суммы «на руки» по заказам в работе / переговорах / сданным. */
  inWork: number
  /** Заработано: «на руки» по оплаченным. */
  earned: number
  /** Заработано за текущий месяц. */
  earnedThisMonth: number
  /** Комиссия площадок по оплаченным. */
  commissionPaid: number
  overdue: number
  dueToday: number
  dueWeek: number
}

/** Сводка по деньгам и срокам для дашборда. */
export function totals(orders: Order[]): Totals {
  const monthPrefix = new Date().toISOString().slice(0, 7)
  const t: Totals = {
    outstanding: 0,
    inWork: 0,
    earned: 0,
    earnedThisMonth: 0,
    commissionPaid: 0,
    overdue: 0,
    dueToday: 0,
    dueWeek: 0,
  }

  for (const o of orders) {
    if (o.status === 'paid') {
      t.earned += net(o)
      t.commissionPaid += commission(o)
      if (o.date.startsWith(monthPrefix)) t.earnedThisMonth += net(o)
      continue
    }
    if (o.status === 'rejected') continue

    // Незакрытые заказы
    t.outstanding += balance(o)
    if (o.status === 'in_work' || o.status === 'negotiation' || o.status === 'delivered') {
      t.inWork += net(o)
    }
    const d = daysLeft(o)
    if (d !== null) {
      if (d < 0) t.overdue += 1
      else if (d === 0) t.dueToday += 1
      else if (d <= 7) t.dueWeek += 1
    }
  }
  return t
}

/** Заказ «Сдан» висит дольше N дней — деньги не пришли, пора напомнить. */
export function isStaleDelivered(o: Order, days = 7): boolean {
  if (o.status !== 'delivered') return false
  const changed = new Date(o.updatedAt).getTime()
  return Date.now() - changed > days * 86_400_000
}
