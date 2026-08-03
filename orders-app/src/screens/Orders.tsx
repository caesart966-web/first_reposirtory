import { Plus, Receipt, Search, SlidersHorizontal, X } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { Header } from '../components/Header'
import { OrderCard } from '../components/OrderCard'
import { useAppData } from '../hooks/useData'
import { updateOrder } from '../db/repo'
import {
  ORDER_STATUSES,
  ORDER_STATUS_LABEL,
  ORDER_STATUS_SHORT,
  type Order,
  type OrderStatus,
} from '../db/types'
import { balance, daysLeft, isActive, net } from '../lib/calc'
import { cn, money, plural } from '../lib/utils'
import { Button } from '../ui/Button'
import { Choice } from '../ui/Choice'
import { SearchInput } from '../ui/Field'
import { EmptyState, SkeletonList } from '../ui/Feedback'
import { Sheet } from '../ui/Sheet'
import { useToast } from '../ui/Toast'

type Sort = 'deadline' | 'date' | 'amount'

const SORT_LABEL: Record<Sort, string> = {
  deadline: 'По сроку',
  date: 'По дате',
  amount: 'По сумме',
}

/** Следующий статус по свайпу — обычный путь заказа. */
const NEXT_STATUS: Partial<Record<OrderStatus, OrderStatus>> = {
  response: 'negotiation',
  negotiation: 'in_work',
  in_work: 'delivered',
  delivered: 'paid',
}

interface Props {
  params: Record<string, string>
  onNewOrder: () => void
  onOpenOrder: (order: Order) => void
  onResetParams: () => void
}

export function Orders({ params, onNewOrder, onOpenOrder, onResetParams }: Props) {
  const { orders, clients, sources, clientById, sourceById, loading } = useAppData()
  const toast = useToast()

  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<OrderStatus | null>((params.status as OrderStatus) ?? null)
  const [sourceId, setSourceId] = useState<string | null>(params.source ?? null)
  const [clientId, setClientId] = useState<string | null>(params.client ?? null)
  const [view, setView] = useState<string | null>(params.view ?? null)
  const [sort, setSort] = useState<Sort>('deadline')
  const [filtersOpen, setFiltersOpen] = useState(false)

  // Пришли с дашборда с готовым фильтром — подхватываем его
  const paramsKey = JSON.stringify(params)
  const [lastKey, setLastKey] = useState(paramsKey)
  if (paramsKey !== lastKey) {
    setLastKey(paramsKey)
    setStatus((params.status as OrderStatus) ?? null)
    setSourceId(params.source ?? null)
    setClientId(params.client ?? null)
    setView(params.view ?? null)
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    let list = (orders ?? []).filter((o) => {
      if (status && o.status !== status) return false
      if (sourceId && o.sourceId !== sourceId) return false
      if (clientId && o.clientId !== clientId) return false
      if (view === 'overdue' && !((daysLeft(o) ?? 1) < 0)) return false
      if (view === 'today' && (daysLeft(o) ?? 1) > 0) return false
      if (view === 'debt' && !(isActive(o) && balance(o) > 0)) return false
      if (q) {
        const client = clientById.get(o.clientId)?.name.toLowerCase() ?? ''
        if (!client.includes(q) && !o.service.toLowerCase().includes(q)) return false
      }
      return true
    })

    list = [...list].sort((a, b) => {
      if (sort === 'amount') return b.amount - a.amount
      if (sort === 'date') return b.date.localeCompare(a.date)
      // По сроку: сначала те, у кого срок есть и он ближе
      const da = a.deadline && isActive(a) ? a.deadline : '9999-12-31'
      const dbb = b.deadline && isActive(b) ? b.deadline : '9999-12-31'
      return da.localeCompare(dbb)
    })
    return list
  }, [orders, query, status, sourceId, clientId, view, sort, clientById])

  const sums = useMemo(() => {
    let amount = 0
    let rest = 0
    let onHand = 0
    for (const o of filtered) {
      amount += o.amount
      onHand += net(o)
      if (isActive(o)) rest += balance(o)
    }
    return { amount, rest, onHand }
  }, [filtered])

  const activeFilters = [status, sourceId, clientId, view].filter(Boolean).length

  const resetFilters = () => {
    setStatus(null)
    setSourceId(null)
    setClientId(null)
    setView(null)
    onResetParams()
  }

  const advance = async (o: Order) => {
    const next = NEXT_STATUS[o.status]
    if (!next) return
    await updateOrder(o.id, { status: next })
    toast(`Статус: ${ORDER_STATUS_LABEL[next]}`)
  }

  return (
    <div>
      <Header
        title="Заказы"
        subtitle={
          filtered.length
            ? `${plural(filtered.length, 'заказ', 'заказа', 'заказов')} · ${money(sums.amount)}`
            : undefined
        }
        action={
          <button
            onClick={() => setFiltersOpen(true)}
            className={cn(
              'tap relative flex items-center justify-center rounded-btn border border-line px-3',
              activeFilters > 0 ? 'border-accent/40 bg-accent/10 text-accent' : 'bg-surface text-muted',
            )}
            aria-label="Фильтры"
          >
            <SlidersHorizontal size={18} />
            {activeFilters > 0 && (
              <span className="tnum absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-caption font-semibold leading-none text-white">
                {activeFilters}
              </span>
            )}
          </button>
        }
      />

      <div className="px-4">
        <SearchInput
          icon={<Search size={18} />}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Клиент или услуга"
          inputMode="search"
        />
      </div>

      {/* Быстрые фильтры по статусу */}
      <div className="no-scrollbar mt-3 flex gap-2 overflow-x-auto px-4 pb-1">
        <FilterChip active={!status && !view} onClick={() => { setStatus(null); setView(null) }}>
          Все
        </FilterChip>
        {ORDER_STATUSES.map((s) => (
          <FilterChip key={s} active={status === s} onClick={() => setStatus(status === s ? null : s)}>
            {ORDER_STATUS_SHORT[s]}
          </FilterChip>
        ))}
      </div>

      {/* Активные фильтры отдельной строкой — видно, что список сужен */}
      {(sourceId || clientId || view) && (
        <div className="mt-3 flex flex-wrap gap-2 px-4">
          {view && (
            <ActiveFilter
              label={view === 'overdue' ? 'Просрочено' : view === 'today' ? 'Сегодня' : 'Есть долг'}
              onClear={() => setView(null)}
            />
          )}
          {sourceId && (
            <ActiveFilter
              label={sourceById.get(sourceId)?.name ?? 'Источник'}
              onClear={() => setSourceId(null)}
            />
          )}
          {clientId && (
            <ActiveFilter
              label={clientById.get(clientId)?.name ?? 'Клиент'}
              onClear={() => setClientId(null)}
            />
          )}
        </div>
      )}

      {/* Итоги по видимому списку */}
      {filtered.length > 0 && (
        <div className="mt-4 flex gap-3 px-4 text-caption text-muted">
          <span>
            На руки: <b className="tnum font-semibold text-ink">{money(sums.onHand)}</b>
          </span>
          {sums.rest > 0 && (
            <span>
              Ждём: <b className="tnum font-semibold text-ink">{money(sums.rest)}</b>
            </span>
          )}
        </div>
      )}

      <div className="mt-4 space-y-3 px-4">
        {loading ? (
          <SkeletonList />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Receipt size={26} />}
            title={activeFilters || query ? 'Ничего не нашлось' : 'Заказов пока нет'}
            text={
              activeFilters || query
                ? 'Попробуй сбросить фильтры или поискать иначе.'
                : 'Добавь первый заказ — это меньше двадцати секунд.'
            }
            actionLabel={activeFilters || query ? 'Сбросить' : 'Добавить заказ'}
            onAction={activeFilters || query ? () => { resetFilters(); setQuery('') } : onNewOrder}
          />
        ) : (
          filtered.map((o) => (
            <OrderCard
              key={o.id}
              order={o}
              client={clientById.get(o.clientId)}
              source={o.sourceId ? sourceById.get(o.sourceId) : undefined}
              onClick={() => onOpenOrder(o)}
              onSwipe={NEXT_STATUS[o.status] ? () => advance(o) : undefined}
              swipeHint={
                NEXT_STATUS[o.status] ? `→ ${ORDER_STATUS_LABEL[NEXT_STATUS[o.status]!]}` : undefined
              }
            />
          ))
        )}
      </div>

      {/* Плавающая кнопка «плюс» */}
      <button
        onClick={onNewOrder}
        aria-label="Новый заказ"
        className="fixed bottom-[calc(78px+env(safe-area-inset-bottom,0px))] right-4 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-accent text-white shadow-lift transition-transform duration-150 ease-out active:scale-95"
      >
        <Plus size={26} />
      </button>

      {/* Шторка фильтров */}
      <Sheet
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        title="Фильтры"
        footer={
          <div className="flex gap-3">
            <Button variant="secondary" full onClick={resetFilters}>
              Сбросить
            </Button>
            <Button full onClick={() => setFiltersOpen(false)}>
              Показать
            </Button>
          </div>
        }
      >
        <div className="space-y-5">
          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Сортировка</span>
            <Choice
              options={(Object.keys(SORT_LABEL) as Sort[]).map((s) => ({ value: s, label: SORT_LABEL[s] }))}
              value={sort}
              onChange={setSort}
            />
          </div>

          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Источник</span>
            <Choice
              options={(sources ?? []).map((s) => ({ value: s.id, label: s.name, color: s.color }))}
              value={sourceId}
              onChange={(id) => setSourceId(id === sourceId ? null : id)}
            />
          </div>

          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Клиент</span>
            <Choice
              options={(clients ?? []).map((c) => ({ value: c.id, label: c.name }))}
              value={clientId}
              onChange={(id) => setClientId(id === clientId ? null : id)}
            />
          </div>
        </div>
      </Sheet>
    </div>
  )
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'tap shrink-0 rounded-chip border px-3.5 py-2 text-caption font-medium transition-colors duration-150 ease-out',
        active
          ? 'border-accent bg-accent/10 text-accent dark:bg-accent/15'
          : 'border-line bg-surface text-muted hover:text-ink',
      )}
    >
      {children}
    </button>
  )
}

function ActiveFilter({ label, onClear }: { label: string; onClear: () => void }) {
  return (
    <button
      onClick={onClear}
      className="inline-flex items-center gap-1.5 rounded-chip bg-accent/10 px-2.5 py-1.5 text-caption font-medium text-accent dark:bg-accent/15"
    >
      {label}
      <X size={13} />
    </button>
  )
}
