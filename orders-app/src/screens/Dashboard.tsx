import { motion } from 'framer-motion'
import {
  AlarmClock,
  ArrowRight,
  CalendarDays,
  Coins,
  Sparkles,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import { useMemo, type ReactNode } from 'react'
import { Header } from '../components/Header'
import { useAppData } from '../hooks/useData'
import type { Tab } from '../hooks/useRoute'
import { balance, daysLeft, isActive, net, totals } from '../lib/calc'
import { cn, formatDeadline, money, moneyShort, plural } from '../lib/utils'
import {
  ORDER_STATUSES,
  ORDER_STATUS_LABEL,
  ORDER_STATUS_TONE,
  type Order,
} from '../db/types'
import { Card, SectionTitle } from '../ui/Card'
import { CountUp } from '../ui/CountUp'
import { EmptyState, SkeletonList } from '../ui/Feedback'
import { pillTone, textTone } from '../ui/tones'

interface Props {
  onNavigate: (tab: Tab, params?: Record<string, string>) => void
  onNewOrder: () => void
  onOpenOrder: (order: Order) => void
}

/** Дашборд: bento-сетка — карточки разного размера, а не одинаковые плитки. */
export function Dashboard({ onNavigate, onNewOrder, onOpenOrder }: Props) {
  const { orders, tasks, sources, clientById, loading } = useAppData()

  const t = useMemo(() => totals(orders ?? []), [orders])

  // Что горит сегодня: просроченные и сегодняшние заказы + задачи
  const todayOrders = useMemo(() => {
    return (orders ?? [])
      .filter((o) => {
        const d = daysLeft(o)
        return d !== null && d <= 0
      })
      .sort((a, b) => (a.deadline ?? '').localeCompare(b.deadline ?? ''))
  }, [orders])

  const todayTasks = useMemo(() => {
    const day = new Date().toISOString().slice(0, 10)
    return (tasks ?? []).filter((t) => t.status !== 'done' && t.deadline && t.deadline <= day)
  }, [tasks])

  const statusCounts = useMemo(() => {
    const m = new Map<string, number>()
    for (const o of orders ?? []) m.set(o.status, (m.get(o.status) ?? 0) + 1)
    return m
  }, [orders])

  // Аналитика по источникам: сколько заказов и денег принёс каждый
  const sourceStats = useMemo(() => {
    const m = new Map<string, { count: number; amount: number; net: number }>()
    for (const o of orders ?? []) {
      const key = o.sourceId ?? '—'
      const cur = m.get(key) ?? { count: 0, amount: 0, net: 0 }
      cur.count += 1
      cur.amount += o.amount
      cur.net += net(o)
      m.set(key, cur)
    }
    return [...m.entries()]
      .map(([id, v]) => ({
        id,
        name: id === '—' ? 'Без источника' : ((sources ?? []).find((s) => s.id === id)?.name ?? 'Удалён'),
        color: id === '—' ? '#8792A3' : ((sources ?? []).find((s) => s.id === id)?.color ?? '#8792A3'),
        ...v,
      }))
      .sort((a, b) => b.amount - a.amount)
  }, [orders, sources])

  const maxSourceAmount = sourceStats[0]?.amount ?? 0
  const activeCount = (orders ?? []).filter(isActive).length

  if (loading) {
    return (
      <div>
        <Header title="Обзор" />
        <div className="space-y-3 px-4">
          <SkeletonList count={3} />
        </div>
      </div>
    )
  }

  if ((orders ?? []).length === 0) {
    return (
      <div>
        <Header title="Обзор" />
        <EmptyState
          icon={<Sparkles size={26} />}
          title="Пока пусто"
          text="Добавь первый заказ, и здесь появится картина по деньгам: сколько в работе, сколько должны и что горит."
          actionLabel="Добавить заказ"
          onAction={onNewOrder}
        />
      </div>
    )
  }

  return (
    <div className="pb-2">
      <Header
        title="Обзор"
        subtitle={`${plural(activeCount, 'активный заказ', 'активных заказа', 'активных заказов')} в работе`}
      />

      {/* ── Bento-сетка ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 px-4 sm:grid-cols-4">
        {/* Главная цифра */}
        <Card
          pressable
          onClick={() => onNavigate('orders', { view: 'debt' })}
          className="col-span-2 overflow-hidden p-5 sm:row-span-2 sm:flex sm:flex-col sm:justify-center"
          raised
        >
          {/* Единственный мягкий градиент в приложении */}
          <div className="relative overflow-hidden">
            <div
              className="absolute -right-10 -top-14 h-40 w-40 rounded-full opacity-[0.12] blur-2xl"
              style={{ background: 'radial-gradient(circle, rgb(var(--c-accent)) 0%, transparent 70%)' }}
            />
            <div className="flex items-center gap-2 text-caption font-medium text-muted">
              <Wallet size={15} /> Осталось получить
            </div>
            <div className="mt-2 text-metric font-semibold tracking-tight sm:text-metric-lg">
              <CountUp value={t.outstanding} format={(n) => money(n)} />
            </div>
            <div className="mt-1.5 text-caption text-muted">
              По незакрытым заказам · комиссия площадок уже учтена в «на руки»
            </div>
          </div>
        </Card>

        <StatTile
          icon={<Coins size={15} />}
          label="В работе"
          value={t.inWork}
          tone="accent"
          hint="на руки"
          onClick={() => onNavigate('orders', { status: 'in_work' })}
        />
        <StatTile
          icon={<TrendingUp size={15} />}
          label="Заработано"
          value={t.earned}
          tone="money"
          hint={t.earnedThisMonth > 0 ? `${moneyShort(t.earnedThisMonth)} в этом месяце` : 'всего'}
          onClick={() => onNavigate('orders', { status: 'paid' })}
        />
        <CountTile
          icon={<AlarmClock size={15} />}
          label="Просрочено"
          value={t.overdue}
          tone={t.overdue > 0 ? 'danger' : 'muted'}
          onClick={() => onNavigate('orders', { view: 'overdue' })}
        />
        <CountTile
          icon={<CalendarDays size={15} />}
          label="Сегодня"
          value={t.dueToday}
          tone={t.dueToday > 0 ? 'warn' : 'muted'}
          onClick={() => onNavigate('orders', { view: 'today' })}
        />
      </div>

      {/* ── Полоса «Сегодня» ────────────────────────────────────── */}
      {(todayOrders.length > 0 || todayTasks.length > 0) && (
        <section className="mt-7">
          <div className="px-4">
            <SectionTitle
              action={
                <button
                  onClick={() => onNavigate('orders', { view: 'today' })}
                  className="flex items-center gap-1 text-caption font-medium text-accent"
                >
                  Всё <ArrowRight size={14} />
                </button>
              }
            >
              Сегодня
            </SectionTitle>
          </div>
          <div className="no-scrollbar flex snap-x gap-3 overflow-x-auto px-4 pb-1">
            {todayOrders.map((o) => {
              const overdue = (daysLeft(o) ?? 0) < 0
              return (
                <motion.button
                  key={o.id}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onOpenOrder(o)}
                  className="w-[230px] shrink-0 snap-start rounded-card border border-line bg-surface p-4 text-left shadow-soft"
                >
                  <div className="flex items-center gap-2">
                    <span className={cn('h-1.5 w-1.5 rounded-full', overdue ? 'bg-danger' : 'bg-warn')} />
                    <span
                      className={cn(
                        'text-caption font-medium',
                        overdue ? 'text-danger' : 'text-warn',
                      )}
                    >
                      {formatDeadline(o.deadline)}
                    </span>
                  </div>
                  <div className="mt-2 truncate text-body-lg font-semibold tracking-tight">
                    {clientById.get(o.clientId)?.name ?? 'Без клиента'}
                  </div>
                  <div className="truncate text-caption text-muted">{o.service}</div>
                  <div className="tnum mt-2.5 text-body font-semibold">{money(balance(o))}</div>
                </motion.button>
              )
            })}
            {todayTasks.map((task) => (
              <motion.button
                key={task.id}
                whileTap={{ scale: 0.98 }}
                onClick={() => onNavigate('tasks')}
                className="w-[230px] shrink-0 snap-start rounded-card border border-line bg-surface p-4 text-left shadow-soft"
              >
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                  <span className="text-caption font-medium text-accent">Задача</span>
                </div>
                <div className="mt-2 line-clamp-2 text-body-lg font-semibold tracking-tight">
                  {task.title}
                </div>
                <div className="mt-2.5 text-caption text-muted">{formatDeadline(task.deadline)}</div>
              </motion.button>
            ))}
          </div>
        </section>
      )}

      {/* ── Статусы ─────────────────────────────────────────────── */}
      <section className="mt-7 px-4">
        <SectionTitle>Статусы</SectionTitle>
        <Card className="p-2">
          <div className="flex flex-wrap gap-2">
            {ORDER_STATUSES.map((s) => {
              const count = statusCounts.get(s) ?? 0
              return (
                <button
                  key={s}
                  onClick={() => onNavigate('orders', { status: s })}
                  disabled={count === 0}
                  className={cn(
                    'tap inline-flex items-center gap-2 rounded-chip px-3 py-2 text-caption font-medium transition-opacity duration-150 ease-out',
                    pillTone[ORDER_STATUS_TONE[s]],
                    count === 0 && 'opacity-40',
                  )}
                >
                  {ORDER_STATUS_LABEL[s]}
                  <span className="tnum font-semibold">{count}</span>
                </button>
              )
            })}
          </div>
        </Card>
      </section>

      {/* ── Источники ───────────────────────────────────────────── */}
      <section className="mt-7 px-4">
        <SectionTitle
          action={
            <button
              onClick={() => onNavigate('settings', { section: 'sources' })}
              className="text-caption font-medium text-accent"
            >
              Настроить
            </button>
          }
        >
          Откуда приходят деньги
        </SectionTitle>
        <Card className="divide-y divide-line">
          {sourceStats.map((s) => (
            <button
              key={s.id}
              onClick={() => s.id !== '—' && onNavigate('orders', { source: s.id })}
              className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors duration-150 ease-out hover:bg-surface-2"
            >
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: s.color }} />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="truncate text-body font-medium">{s.name}</span>
                  <span className="tnum shrink-0 text-body font-semibold">{moneyShort(s.amount)}</span>
                </div>
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-surface-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{
                        width: `${maxSourceAmount ? (s.amount / maxSourceAmount) * 100 : 0}%`,
                      }}
                      transition={{ duration: 0.5, ease: 'easeOut' }}
                      className="h-full rounded-full"
                      style={{ backgroundColor: s.color }}
                    />
                  </div>
                  <span className="tnum shrink-0 text-caption text-muted">
                    {plural(s.count, 'заказ', 'заказа', 'заказов')}
                  </span>
                </div>
              </div>
            </button>
          ))}
        </Card>
      </section>
    </div>
  )
}

/** Небольшая карточка с денежной цифрой. */
function StatTile({
  icon,
  label,
  value,
  tone,
  hint,
  onClick,
}: {
  icon: ReactNode
  label: string
  value: number
  tone: 'accent' | 'money'
  hint?: string
  onClick?: () => void
}) {
  return (
    <Card pressable={!!onClick} onClick={onClick} className="p-4">
      <div className="flex items-center gap-1.5 text-caption font-medium text-muted">
        <span className={textTone[tone]}>{icon}</span>
        {label}
      </div>
      <div className={cn('mt-2 text-[22px] font-semibold leading-7 tracking-tight', textTone[tone])}>
        <CountUp value={value} format={(n) => moneyShort(n)} />
      </div>
      {hint && <div className="mt-0.5 text-caption text-muted">{hint}</div>}
    </Card>
  )
}

/** Небольшая карточка со счётчиком (штуки, не деньги). */
function CountTile({
  icon,
  label,
  value,
  tone,
  onClick,
}: {
  icon: ReactNode
  label: string
  value: number
  tone: 'danger' | 'warn' | 'muted'
  onClick?: () => void
}) {
  return (
    <Card pressable={!!onClick} onClick={onClick} className="p-4">
      <div className="flex items-center gap-1.5 text-caption font-medium text-muted">
        <span className={textTone[tone]}>{icon}</span>
        {label}
      </div>
      <div className={cn('mt-2 text-[22px] font-semibold leading-7 tracking-tight', textTone[tone])}>
        <CountUp value={value} format={(n) => String(Math.round(n))} />
      </div>
      <div className="mt-0.5 text-caption text-muted">
        {value === 0 ? 'всё спокойно' : plural(value, 'заказ', 'заказа', 'заказов')}
      </div>
    </Card>
  )
}
