// ─────────────────────────────────────────────────────────────────
// Модель данных приложения. Всё хранится локально в браузере
// (IndexedDB), никакого сервера нет.
// ─────────────────────────────────────────────────────────────────

/** Дата в виде строки 'ГГГГ-ММ-ДД' — так её удобно сортировать и экспортировать. */
export type IsoDate = string
/** Дата и время в ISO — служебные поля createdAt / updatedAt. */
export type IsoDateTime = string

export type OrderStatus = 'response' | 'negotiation' | 'in_work' | 'delivered' | 'paid' | 'rejected'
export type Priority = 'high' | 'medium' | 'low'
export type ClientStatus = 'active' | 'potential' | 'finished'
export type TaskStatus = 'new' | 'in_work' | 'waiting' | 'done'

/** Источник заказа — справочник, которым полностью управляет пользователь. */
export interface Source {
  id: string
  name: string
  /** Комиссия долей единицы: 0.2 — это 20 %. В интерфейсе показываем проценты. */
  commissionRate: number
  /** HEX-цвет для списков и аналитики. */
  color: string
  /** Порядок в справочнике (для ручной сортировки). */
  order: number
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
}

export interface Client {
  id: string
  name: string
  contact: string
  defaultSourceId: string | null
  niche: string
  status: ClientStatus
  notes: string
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
}

export interface Order {
  id: string
  date: IsoDate
  clientId: string
  sourceId: string | null
  /** Снимок процента комиссии на момент создания заказа.
   *  Если потом поменять процент у источника — старые заказы не меняются. */
  commissionRate: number
  service: string
  status: OrderStatus
  amount: number
  prepayment: number
  deadline: IsoDate | null
  priority: Priority
  notes: string
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
}

export interface Task {
  id: string
  title: string
  clientId: string | null
  deadline: IsoDate | null
  status: TaskStatus
  priority: Priority
  notes: string
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
}

/** Настройки приложения — простое хранилище «ключ-значение». */
export interface Setting {
  key: string
  value: unknown
}

export type ThemeMode = 'light' | 'dark' | 'system'

export interface NotificationSettings {
  enabled: boolean
  /** Час утреннего напоминания, 0-23. */
  morningHour: number
  /** Напоминать о просроченном. */
  overdue: boolean
  /** Напоминать про «Сдан», но не оплачен дольше 7 дней. */
  unpaid: boolean
}

// ── Справочники подписей и цветов ────────────────────────────────

export const ORDER_STATUSES: OrderStatus[] = [
  'response',
  'negotiation',
  'in_work',
  'delivered',
  'paid',
  'rejected',
]

export const ORDER_STATUS_LABEL: Record<OrderStatus, string> = {
  response: 'Отклик отправлен',
  negotiation: 'Переговоры',
  in_work: 'В работе',
  delivered: 'Сдан',
  paid: 'Оплачен',
  rejected: 'Отказ',
}

/** Короткие подписи для тесных мест (плашки в списке, фильтры). */
export const ORDER_STATUS_SHORT: Record<OrderStatus, string> = {
  response: 'Отклик',
  negotiation: 'Переговоры',
  in_work: 'В работе',
  delivered: 'Сдан',
  paid: 'Оплачен',
  rejected: 'Отказ',
}

/** Смысловой цвет плашки: имя токена из дизайн-системы. */
export type Tone = 'neutral' | 'accent' | 'warn' | 'violet' | 'money' | 'danger' | 'muted'

export const ORDER_STATUS_TONE: Record<OrderStatus, Tone> = {
  response: 'neutral',
  negotiation: 'accent',
  in_work: 'warn',
  delivered: 'violet',
  paid: 'money',
  rejected: 'muted',
}

export const PRIORITIES: Priority[] = ['high', 'medium', 'low']

export const PRIORITY_LABEL: Record<Priority, string> = {
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

export const PRIORITY_TONE: Record<Priority, Tone> = {
  high: 'danger',
  medium: 'warn',
  low: 'neutral',
}

export const CLIENT_STATUSES: ClientStatus[] = ['active', 'potential', 'finished']

export const CLIENT_STATUS_LABEL: Record<ClientStatus, string> = {
  active: 'Активный',
  potential: 'Потенциальный',
  finished: 'Завершён',
}

export const CLIENT_STATUS_TONE: Record<ClientStatus, Tone> = {
  active: 'money',
  potential: 'accent',
  finished: 'muted',
}

export const TASK_STATUSES: TaskStatus[] = ['new', 'in_work', 'waiting', 'done']

export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  new: 'Новая',
  in_work: 'В работе',
  waiting: 'Ждёт клиента',
  done: 'Готово',
}

export const TASK_STATUS_TONE: Record<TaskStatus, Tone> = {
  new: 'neutral',
  in_work: 'accent',
  waiting: 'warn',
  done: 'money',
}

/** Статусы, для которых сроки уже неважны (дедлайн не считаем). */
export const CLOSED_STATUSES: OrderStatus[] = ['paid', 'rejected']
