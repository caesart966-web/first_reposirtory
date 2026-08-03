import { db } from '../db/db'
import { DEFAULT_NOTIFICATIONS, SETTING_KEYS, getSetting, setSetting } from '../db/repo'
import type { NotificationSettings } from '../db/types'
import { isStaleDelivered, isDueToday, isOverdue } from './calc'
import { plural, today } from './utils'

// ─────────────────────────────────────────────────────────────────
// Локальные напоминания через Notification API.
// Разрешение спрашиваем только когда пользователь сам включает
// уведомления в настройках. Нет поддержки — приложение работает как есть.
// ─────────────────────────────────────────────────────────────────

export function notificationsSupported(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window
}

export function permission(): NotificationPermission | 'unsupported' {
  return notificationsSupported() ? Notification.permission : 'unsupported'
}

export async function requestPermission(): Promise<NotificationPermission> {
  if (!notificationsSupported()) return 'denied'
  return Notification.requestPermission()
}

async function show(title: string, body: string, tag: string): Promise<void> {
  if (permission() !== 'granted') return
  const icon = `${import.meta.env.BASE_URL}icons/icon-192.png`
  try {
    const reg = await navigator.serviceWorker?.getRegistration()
    if (reg) {
      await reg.showNotification(title, { body, tag, icon, badge: icon })
      return
    }
  } catch {
    // Падать из-за уведомления нельзя — просто пробуем обычный путь
  }
  new Notification(title, { body, tag, icon })
}

/**
 * Проверка напоминаний. Вызывается при запуске приложения и раз в час,
 * пока оно открыто. Утреннее напоминание — не чаще одного раза в день.
 */
export async function checkReminders(): Promise<void> {
  const settings = await getSetting<NotificationSettings>(
    SETTING_KEYS.notifications,
    DEFAULT_NOTIFICATIONS,
  )
  if (!settings.enabled || permission() !== 'granted') return

  const now = new Date()
  const day = today()
  const lastDay = await getSetting<string>(SETTING_KEYS.lastNotifyDate, '')
  if (lastDay === day) return
  if (now.getHours() < settings.morningHour) return

  const [orders, tasks] = await Promise.all([db.orders.toArray(), db.tasks.toArray()])

  const dueOrders = orders.filter(isDueToday)
  const overdueOrders = orders.filter(isOverdue)
  const openTasks = tasks.filter((t) => t.status !== 'done')
  const dueTasks = openTasks.filter((t) => t.deadline === day)
  const overdueTasks = openTasks.filter((t) => t.deadline && t.deadline < day)
  const stale = orders.filter((o) => isStaleDelivered(o, 7))

  const lines: string[] = []
  if (dueOrders.length) lines.push(`сегодня сдать: ${plural(dueOrders.length, 'заказ', 'заказа', 'заказов')}`)
  if (dueTasks.length) lines.push(`задач на сегодня: ${dueTasks.length}`)
  if (lines.length) await show('Что горит сегодня', capitalize(lines.join(', ')), 'today')

  if (settings.overdue && (overdueOrders.length || overdueTasks.length)) {
    const parts: string[] = []
    if (overdueOrders.length)
      parts.push(plural(overdueOrders.length, 'заказ', 'заказа', 'заказов'))
    if (overdueTasks.length) parts.push(plural(overdueTasks.length, 'задача', 'задачи', 'задач'))
    await show('Просрочено', `${capitalize(parts.join(' и '))} с прошедшим сроком`, 'overdue')
  }

  if (settings.unpaid && stale.length) {
    await show(
      'Деньги не пришли',
      `${plural(stale.length, 'заказ', 'заказа', 'заказов')} в статусе «Сдан» дольше недели — напомни клиенту`,
      'unpaid',
    )
  }

  await setSetting(SETTING_KEYS.lastNotifyDate, day)
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/** Тестовое уведомление — чтобы сразу проверить, что всё работает. */
export async function sendTestNotification(): Promise<void> {
  await show('Заказы', 'Уведомления включены — буду напоминать про сроки и деньги', 'test')
}
