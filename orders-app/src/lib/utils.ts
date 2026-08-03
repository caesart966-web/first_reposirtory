import type { IsoDate, IsoDateTime } from '../db/types'

/** Склейка классов: cn('a', cond && 'b') */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}

/** Уникальный id. crypto.randomUUID есть во всех современных браузерах. */
export function uid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

export function nowIso(): IsoDateTime {
  return new Date().toISOString()
}

// ── Даты ─────────────────────────────────────────────────────────

/** Дата в строку 'ГГГГ-ММ-ДД' по локальному времени (не по UTC — иначе вечером «съезжает» день). */
export function toIsoDate(d: Date): IsoDate {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function today(): IsoDate {
  return toIsoDate(new Date())
}

export function addDays(iso: IsoDate, days: number): IsoDate {
  const d = parseIsoDate(iso)
  d.setDate(d.getDate() + days)
  return toIsoDate(d)
}

export function parseIsoDate(iso: IsoDate): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, (m ?? 1) - 1, d ?? 1)
}

/** Разница в днях: сколько дней от сегодня до даты (вчера → -1). */
export function daysFromToday(iso: IsoDate): number {
  const a = parseIsoDate(today()).getTime()
  const b = parseIsoDate(iso).getTime()
  return Math.round((b - a) / 86_400_000)
}

const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

/** «12 мар» или «12 мар 2025», если год не текущий. */
export function formatDate(iso: IsoDate | null): string {
  if (!iso) return '—'
  const d = parseIsoDate(iso)
  const base = `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}`
  return d.getFullYear() === new Date().getFullYear() ? base : `${base} ${d.getFullYear()}`
}

/** Человеческая подпись срока: «сегодня», «завтра», «просрочен на 3 дня». */
export function formatDeadline(iso: IsoDate | null): string {
  if (!iso) return 'Без срока'
  const diff = daysFromToday(iso)
  if (diff === 0) return 'Сегодня'
  if (diff === 1) return 'Завтра'
  if (diff === -1) return 'Вчера'
  if (diff < 0) return `Просрочен на ${plural(-diff, 'день', 'дня', 'дней')}`
  if (diff <= 7) return `Через ${plural(diff, 'день', 'дня', 'дней')}`
  return formatDate(iso)
}

/** Русское склонение: plural(2, 'день', 'дня', 'дней') → '2 дня'. */
export function plural(n: number, one: string, few: string, many: string): string {
  const abs = Math.abs(n) % 100
  const last = abs % 10
  let word = many
  if (abs < 11 || abs > 14) {
    if (last === 1) word = one
    else if (last >= 2 && last <= 4) word = few
  }
  return `${n} ${word}`
}

/** То же, но без самого числа. */
export function pluralWord(n: number, one: string, few: string, many: string): string {
  return plural(n, one, few, many).split(' ').slice(1).join(' ')
}

// ── Деньги ───────────────────────────────────────────────────────

/** 10000 → «10 000 ₽». Пробел неразрывный, чтобы не переносилось. */
export function money(value: number, withSign = true): string {
  const rounded = Math.round(value)
  const s = Math.abs(rounded)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
  const sign = rounded < 0 ? '−' : ''
  return withSign ? `${sign}${s} ₽` : `${sign}${s}`
}

/** Крупные суммы коротко: 1 250 000 → «1,25 млн». Для карточек дашборда. */
export function moneyShort(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `${trimZero((value / 1_000_000).toFixed(2))} млн ₽`
  if (abs >= 100_000) return `${trimZero((value / 1000).toFixed(0))} тыс. ₽`
  return money(value)
}

function trimZero(s: string): string {
  return s.replace(/\.?0+$/, '').replace('.', ',')
}

/** Разбор суммы из ввода: «10 000», «10к», «10.5» → число. */
export function parseAmount(input: string): number {
  const cleaned = input
    .replace(/[\s\u00A0\u2009\u202F]/g, '')
    .replace(',', '.')
    .replace(/[кk]$/i, '000')
  const n = Number(cleaned.replace(/[^\d.-]/g, ''))
  return Number.isFinite(n) ? n : 0
}

/** Процент из доли: 0.2 → «20 %». */
export function percent(rate: number): string {
  const p = rate * 100
  const s = Math.abs(p % 1) < 0.005 ? p.toFixed(0) : p.toFixed(1).replace('.', ',')
  return `${s} %`
}
