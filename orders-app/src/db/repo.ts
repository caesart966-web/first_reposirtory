import { db } from './db'
import type { Client, NotificationSettings, Order, Source, Task, ThemeMode } from './types'
import { nowIso, uid } from '../lib/utils'

// ─────────────────────────────────────────────────────────────────
// Все операции записи собраны здесь — экраны не лезут в базу напрямую.
// ─────────────────────────────────────────────────────────────────

type New<T> = Omit<T, 'id' | 'createdAt' | 'updatedAt'>

// ── Источники ────────────────────────────────────────────────────

export async function createSource(data: Pick<Source, 'name' | 'commissionRate' | 'color'>): Promise<Source> {
  const ts = nowIso()
  const maxOrder = (await db.sources.orderBy('order').last())?.order ?? -1
  const source: Source = { id: uid(), order: maxOrder + 1, createdAt: ts, updatedAt: ts, ...data }
  await db.sources.add(source)
  return source
}

export async function updateSource(id: string, patch: Partial<Source>): Promise<void> {
  await db.sources.update(id, { ...patch, updatedAt: nowIso() })
}

/**
 * Удаление источника, который уже используется в заказах.
 * mode 'reassign' — перенести заказы на другой источник (комиссия заказов НЕ меняется),
 * mode 'clear'    — оставить заказы без источника.
 */
export async function deleteSource(
  id: string,
  mode: 'reassign' | 'clear' = 'clear',
  targetId?: string,
): Promise<void> {
  await db.transaction('rw', db.sources, db.orders, db.clients, async () => {
    const affected = await db.orders.where('sourceId').equals(id).toArray()
    const newSourceId = mode === 'reassign' && targetId ? targetId : null
    const ts = nowIso()
    for (const o of affected) {
      await db.orders.update(o.id, { sourceId: newSourceId, updatedAt: ts })
    }
    // У клиентов этот источник мог стоять источником по умолчанию
    const clients = await db.clients.filter((c) => c.defaultSourceId === id).toArray()
    for (const c of clients) {
      await db.clients.update(c.id, { defaultSourceId: newSourceId, updatedAt: ts })
    }
    await db.sources.delete(id)
  })
}

/** Сколько заказов использует источник — нужно перед удалением. */
export async function countOrdersBySource(sourceId: string): Promise<number> {
  return db.orders.where('sourceId').equals(sourceId).count()
}

// ── Клиенты ──────────────────────────────────────────────────────

export async function createClient(data: Partial<New<Client>> & { name: string }): Promise<Client> {
  const ts = nowIso()
  const client: Client = {
    id: uid(),
    name: data.name.trim(),
    contact: data.contact ?? '',
    defaultSourceId: data.defaultSourceId ?? null,
    niche: data.niche ?? '',
    status: data.status ?? 'active',
    notes: data.notes ?? '',
    createdAt: ts,
    updatedAt: ts,
  }
  await db.clients.add(client)
  return client
}

export async function updateClient(id: string, patch: Partial<Client>): Promise<void> {
  await db.clients.update(id, { ...patch, updatedAt: nowIso() })
}

/** Удаляем клиента вместе с его заказами и задачами — иначе останутся «висяки». */
export async function deleteClient(id: string): Promise<void> {
  await db.transaction('rw', db.clients, db.orders, db.tasks, async () => {
    await db.orders.where('clientId').equals(id).delete()
    const tasks = await db.tasks.where('clientId').equals(id).toArray()
    for (const t of tasks) await db.tasks.update(t.id, { clientId: null, updatedAt: nowIso() })
    await db.clients.delete(id)
  })
}

/** Найти клиента по имени или завести нового — используется в форме заказа. */
export async function findOrCreateClient(name: string, defaultSourceId?: string | null): Promise<Client> {
  const trimmed = name.trim()
  const existing = await db.clients.filter((c) => c.name.toLowerCase() === trimmed.toLowerCase()).first()
  if (existing) return existing
  return createClient({ name: trimmed, defaultSourceId: defaultSourceId ?? null })
}

// ── Заказы ───────────────────────────────────────────────────────

export async function createOrder(data: New<Order>): Promise<Order> {
  const ts = nowIso()
  const order: Order = { id: uid(), createdAt: ts, updatedAt: ts, ...data }
  await db.orders.add(order)
  return order
}

export async function updateOrder(id: string, patch: Partial<Order>): Promise<void> {
  await db.orders.update(id, { ...patch, updatedAt: nowIso() })
}

export async function deleteOrder(id: string): Promise<void> {
  await db.orders.delete(id)
}

// ── Задачи ───────────────────────────────────────────────────────

export async function createTask(data: Partial<New<Task>> & { title: string }): Promise<Task> {
  const ts = nowIso()
  const task: Task = {
    id: uid(),
    title: data.title.trim(),
    clientId: data.clientId ?? null,
    deadline: data.deadline ?? null,
    status: data.status ?? 'new',
    priority: data.priority ?? 'medium',
    notes: data.notes ?? '',
    createdAt: ts,
    updatedAt: ts,
  }
  await db.tasks.add(task)
  return task
}

export async function updateTask(id: string, patch: Partial<Task>): Promise<void> {
  await db.tasks.update(id, { ...patch, updatedAt: nowIso() })
}

export async function deleteTask(id: string): Promise<void> {
  await db.tasks.delete(id)
}

// ── Настройки ────────────────────────────────────────────────────

export async function getSetting<T>(key: string, fallback: T): Promise<T> {
  const row = await db.settings.get(key)
  return row ? (row.value as T) : fallback
}

export async function setSetting(key: string, value: unknown): Promise<void> {
  await db.settings.put({ key, value })
}

export const SETTING_KEYS = {
  theme: 'theme',
  notifications: 'notifications',
  lastNotifyDate: 'lastNotifyDate',
} as const

export const DEFAULT_NOTIFICATIONS: NotificationSettings = {
  enabled: false,
  morningHour: 9,
  overdue: true,
  unpaid: true,
}

export const DEFAULT_THEME: ThemeMode = 'system'

/** Полная очистка данных (кнопка в настройках, с подтверждением). */
export async function wipeAll(): Promise<void> {
  await db.transaction('rw', db.sources, db.clients, db.orders, db.tasks, db.settings, async () => {
    await Promise.all([
      db.orders.clear(),
      db.clients.clear(),
      db.tasks.clear(),
      db.sources.clear(),
      db.settings.clear(),
    ])
  })
}
