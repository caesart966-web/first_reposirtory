import { db } from '../db/db'
import type { Client, Order, Setting, Source, Task } from '../db/types'
import { ORDER_STATUS_LABEL, PRIORITY_LABEL } from '../db/types'
import { balance, commission, net } from './calc'
import { toIsoDate } from './utils'

export interface Backup {
  app: 'orders-app'
  version: 1
  exportedAt: string
  sources: Source[]
  clients: Client[]
  orders: Order[]
  tasks: Task[]
  settings: Setting[]
}

/** Полная выгрузка данных в объект. */
export async function buildBackup(): Promise<Backup> {
  const [sources, clients, orders, tasks, settings] = await Promise.all([
    db.sources.toArray(),
    db.clients.toArray(),
    db.orders.toArray(),
    db.tasks.toArray(),
    db.settings.toArray(),
  ])
  return {
    app: 'orders-app',
    version: 1,
    exportedAt: new Date().toISOString(),
    sources,
    clients,
    orders,
    tasks,
    settings,
  }
}

/** Скачивание файла — работает и офлайн, файл собирается прямо в браузере. */
export function downloadFile(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Даём браузеру время начать скачивание, потом освобождаем память
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function exportJson(): Promise<void> {
  const backup = await buildBackup()
  downloadFile(`zakazy-${toIsoDate(new Date())}.json`, JSON.stringify(backup, null, 2), 'application/json')
}

/** CSV с разделителем «;» и BOM — так его нормально открывает русский Excel. */
export async function exportCsv(): Promise<void> {
  const [orders, clients, sources] = await Promise.all([
    db.orders.toArray(),
    db.clients.toArray(),
    db.sources.toArray(),
  ])
  const clientName = new Map(clients.map((c) => [c.id, c.name]))
  const sourceName = new Map(sources.map((s) => [s.id, s.name]))

  const head = [
    'Дата',
    'Клиент',
    'Источник',
    'Услуга',
    'Статус',
    'Сумма',
    'Комиссия %',
    'Комиссия',
    'На руки',
    'Аванс',
    'Остаток',
    'Дедлайн',
    'Приоритет',
    'Заметки',
  ]

  const rows = orders
    .sort((a, b) => b.date.localeCompare(a.date))
    .map((o) => [
      o.date,
      clientName.get(o.clientId) ?? '',
      o.sourceId ? (sourceName.get(o.sourceId) ?? '') : '',
      o.service,
      ORDER_STATUS_LABEL[o.status],
      round(o.amount),
      round(o.commissionRate * 100),
      round(commission(o)),
      round(net(o)),
      round(o.prepayment),
      round(balance(o)),
      o.deadline ?? '',
      PRIORITY_LABEL[o.priority],
      o.notes.replace(/\r?\n/g, ' '),
    ])

  const csv = [head, ...rows].map((r) => r.map(csvCell).join(';')).join('\r\n')
  downloadFile(`zakazy-${toIsoDate(new Date())}.csv`, '﻿' + csv, 'text/csv')
}

function round(n: number): string {
  return String(Math.round(n * 100) / 100)
}

function csvCell(value: string | number): string {
  const s = String(value)
  return /[";\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export interface ImportResult {
  sources: number
  clients: number
  orders: number
  tasks: number
}

/**
 * Импорт из JSON. Данные полностью заменяют текущие —
 * это восстановление из резервной копии, а не слияние.
 */
export async function importJson(text: string): Promise<ImportResult> {
  let data: Partial<Backup>
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error('Файл не похож на JSON. Выбери файл, скачанный кнопкой «Экспорт JSON».')
  }
  if (!data || data.app !== 'orders-app' || !Array.isArray(data.orders)) {
    throw new Error('Это не резервная копия приложения «Заказы».')
  }

  const sources = (data.sources ?? []) as Source[]
  const clients = (data.clients ?? []) as Client[]
  const orders = (data.orders ?? []) as Order[]
  const tasks = (data.tasks ?? []) as Task[]
  const settings = (data.settings ?? []) as Setting[]

  await db.transaction('rw', db.sources, db.clients, db.orders, db.tasks, db.settings, async () => {
    await Promise.all([
      db.sources.clear(),
      db.clients.clear(),
      db.orders.clear(),
      db.tasks.clear(),
      db.settings.clear(),
    ])
    await db.sources.bulkAdd(sources)
    await db.clients.bulkAdd(clients)
    await db.orders.bulkAdd(orders)
    await db.tasks.bulkAdd(tasks)
    if (settings.length) await db.settings.bulkAdd(settings)
  })

  return { sources: sources.length, clients: clients.length, orders: orders.length, tasks: tasks.length }
}
