import Dexie, { type Table } from 'dexie'
import type { Client, Order, Setting, Source, Task } from './types'
import { nowIso, uid } from '../lib/utils'

/**
 * База данных приложения. IndexedDB через Dexie — данные остаются
 * на телефоне и переживают закрытие приложения и перезагрузку.
 */
export class OrdersDB extends Dexie {
  sources!: Table<Source, string>
  clients!: Table<Client, string>
  orders!: Table<Order, string>
  tasks!: Table<Task, string>
  settings!: Table<Setting, string>

  constructor() {
    super('orders-app')
    this.version(1).stores({
      sources: 'id, name, order',
      clients: 'id, name, status',
      orders: 'id, clientId, sourceId, status, deadline, date',
      tasks: 'id, status, deadline, clientId',
      settings: 'key',
    })
  }
}

export const db = new OrdersDB()

/** Стартовый набор источников. Пользователь потом меняет его как хочет. */
const DEFAULT_SOURCES: Array<[string, number, string]> = [
  ['Прямой клиент', 0, '#4A6FE3'],
  ['Повторный клиент', 0, '#12A578'],
  ['Сарафан', 0, '#2FA8A0'],
  ['Знакомые', 0, '#7C6BE0'],
  ['Telegram', 0, '#2AA3E0'],
  ['ВКонтакте', 0, '#3E6FBF'],
  ['MAX', 0, '#5D5FEF'],
  ['TenChat', 0, '#0F9A8B'],
  ['Свой сайт', 0, '#E9A23B'],
  ['Авито', 0, '#39B54A'],
  ['Kwork', 20, '#E05A47'],
  ['FL.ru', 10, '#D4785C'],
  ['Профи.ру', 0, '#8E7CC3'],
  ['YouDo', 0, '#C9A227'],
  ['Workzilla', 0, '#B05FA8'],
  ['Хабр Фриланс', 0, '#6B7684'],
  ['Собственный бизнес', 0, '#0E8F6E'],
  ['Другое', 0, '#8792A3'],
]

/**
 * Первое открытие: заполняем справочник источников.
 * Если пользователь уже что-то менял (в базе есть источники) — не трогаем.
 */
export async function seedIfEmpty(): Promise<void> {
  const count = await db.sources.count()
  if (count > 0) return
  const ts = nowIso()
  await db.sources.bulkAdd(
    DEFAULT_SOURCES.map(([name, percent, color], i) => ({
      id: uid(),
      name,
      commissionRate: percent / 100,
      color,
      order: i,
      createdAt: ts,
      updatedAt: ts,
    })),
  )
}
