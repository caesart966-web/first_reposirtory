import { ChevronDown, Plus, Trash2, UserPlus } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { SourceEditorSheet } from '../components/SourceEditorSheet'
import { useAppData, useSourceUsage } from '../hooks/useData'
import {
  createOrder,
  deleteOrder,
  findOrCreateClient,
  updateOrder,
} from '../db/repo'
import {
  ORDER_STATUSES,
  ORDER_STATUS_LABEL,
  PRIORITIES,
  PRIORITY_LABEL,
  type Order,
  type OrderStatus,
  type Priority,
  type Source,
} from '../db/types'
import { cn, addDays, money, parseAmount, percent, today } from '../lib/utils'
import { Button } from '../ui/Button'
import { Choice } from '../ui/Choice'
import { Field, Input, Textarea } from '../ui/Field'
import { ConfirmSheet, Sheet } from '../ui/Sheet'
import { useToast } from '../ui/Toast'

interface Props {
  open: boolean
  onClose: () => void
  /** Заказ для редактирования. Пусто — создаём новый. */
  order?: Order | null
}

/**
 * Форма заказа. Главная цель — внести заказ меньше чем за 20 секунд:
 * обязательны только клиент, услуга и сумма, остальное свёрнуто.
 */
export function OrderForm({ open, onClose, order }: Props) {
  const toast = useToast()
  const { clients, sources, orders, clientById } = useAppData()
  const usage = useSourceUsage(orders)

  const [clientId, setClientId] = useState<string | null>(null)
  const [clientQuery, setClientQuery] = useState('')
  const [service, setService] = useState('')
  const [amount, setAmount] = useState('')
  const [prepayment, setPrepayment] = useState('')
  const [sourceId, setSourceId] = useState<string | null>(null)
  const [status, setStatus] = useState<OrderStatus>('in_work')
  const [priority, setPriority] = useState<Priority>('medium')
  const [deadline, setDeadline] = useState<string | null>(null)
  const [date, setDate] = useState(today())
  const [notes, setNotes] = useState('')
  const [more, setMore] = useState(false)
  const [newSource, setNewSource] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  // Заполняем форму при открытии
  useEffect(() => {
    if (!open) return
    setClientId(order?.clientId ?? null)
    setClientQuery(order ? (clientById.get(order.clientId)?.name ?? '') : '')
    setService(order?.service ?? '')
    setAmount(order ? String(order.amount) : '')
    setPrepayment(order && order.prepayment ? String(order.prepayment) : '')
    setSourceId(order?.sourceId ?? null)
    setStatus(order?.status ?? 'in_work')
    setPriority(order?.priority ?? 'medium')
    setDeadline(order?.deadline ?? null)
    setDate(order?.date ?? today())
    setNotes(order?.notes ?? '')
    setMore(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, order])

  // Источники: часто используемые — вверх
  const sortedSources = useMemo(() => {
    const list = [...(sources ?? [])]
    list.sort((a, b) => (usage.get(b.id) ?? 0) - (usage.get(a.id) ?? 0) || a.order - b.order)
    return list
  }, [sources, usage])

  const selectedSource = sourceId ? sortedSources.find((s) => s.id === sourceId) : undefined

  // Комиссия: у нового заказа — текущая ставка источника,
  // у существующего — сохранённый снимок, пока источник не поменяли.
  const rate = useMemo(() => {
    if (order && order.sourceId === sourceId) return order.commissionRate
    return selectedSource?.commissionRate ?? 0
  }, [order, sourceId, selectedSource])

  const amountNum = parseAmount(amount)
  const commissionNum = amountNum * rate
  const netNum = amountNum - commissionNum

  // Подсказки по клиентам под полем ввода
  const suggestions = useMemo(() => {
    const q = clientQuery.trim().toLowerCase()
    const list = clients ?? []
    if (!q) return list.slice(0, 6)
    return list.filter((c) => c.name.toLowerCase().includes(q)).slice(0, 6)
  }, [clients, clientQuery])

  const exactMatch = (clients ?? []).find(
    (c) => c.name.toLowerCase() === clientQuery.trim().toLowerCase(),
  )

  // Часто вводимые услуги — подставляются в один тап
  const recentServices = useMemo(() => {
    const seen = new Map<string, number>()
    for (const o of orders ?? []) {
      if (!o.service) continue
      seen.set(o.service, (seen.get(o.service) ?? 0) + 1)
    }
    return [...seen.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([s]) => s)
  }, [orders])

  const pickClient = (id: string, name: string, defaultSourceId: string | null) => {
    setClientId(id)
    setClientQuery(name)
    // У клиента может быть источник по умолчанию — подставим, если ещё не выбран
    if (!sourceId && defaultSourceId) setSourceId(defaultSourceId)
  }

  const save = async () => {
    const name = clientQuery.trim()
    if (!name) return toast('Впиши клиента', 'error')
    if (!service.trim()) return toast('Впиши, что делаем', 'error')
    if (amountNum <= 0) return toast('Впиши сумму заказа', 'error')

    const client = clientId && exactMatch?.id === clientId
      ? { id: clientId }
      : await findOrCreateClient(name, sourceId)

    const payload = {
      date,
      clientId: client.id,
      sourceId,
      commissionRate: rate,
      service: service.trim(),
      status,
      amount: amountNum,
      prepayment: parseAmount(prepayment),
      deadline,
      priority,
      notes: notes.trim(),
    }

    if (order) {
      await updateOrder(order.id, payload)
      toast('Заказ обновлён')
    } else {
      await createOrder(payload)
      toast('Заказ добавлен')
    }
    onClose()
  }

  const remove = async () => {
    if (!order) return
    await deleteOrder(order.id)
    toast('Заказ удалён')
    onClose()
  }

  const quickDeadlines: Array<[string, string | null]> = [
    ['Сегодня', today()],
    ['Завтра', addDays(today(), 1)],
    ['+3 дня', addDays(today(), 3)],
    ['+неделя', addDays(today(), 7)],
    ['Без срока', null],
  ]

  return (
    <>
      <Sheet
        open={open}
        onClose={onClose}
        title={order ? 'Заказ' : 'Новый заказ'}
        subtitle={order ? undefined : 'Клиент, услуга и сумма — остальное можно потом'}
        footer={
          <div className="flex gap-3">
            {order && (
              <Button variant="danger" size="lg" onClick={() => setConfirmDelete(true)} aria-label="Удалить">
                <Trash2 size={18} />
              </Button>
            )}
            <Button full size="lg" onClick={save}>
              {order ? 'Сохранить' : 'Добавить заказ'}
            </Button>
          </div>
        }
      >
        <div className="space-y-5">
          {/* ── Клиент ─────────────────────────────────────────── */}
          <div>
            <Field label="Клиент">
              <Input
                value={clientQuery}
                onChange={(e) => {
                  setClientQuery(e.target.value)
                  setClientId(null)
                }}
                placeholder="Имя или компания"
                autoComplete="off"
              />
            </Field>
            {suggestions.length > 0 && !exactMatch && (
              <div className="no-scrollbar -mx-5 mt-2 flex gap-2 overflow-x-auto px-5">
                {suggestions.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => pickClient(c.id, c.name, c.defaultSourceId)}
                    className="tap shrink-0 rounded-chip border border-line bg-surface px-3 py-2 text-caption font-medium text-muted transition-colors duration-150 ease-out hover:text-ink"
                  >
                    {c.name}
                  </button>
                ))}
              </div>
            )}
            {clientQuery.trim() && !exactMatch && (
              <p className="mt-2 flex items-center gap-1.5 text-caption text-muted">
                <UserPlus size={14} /> Новый клиент «{clientQuery.trim()}» создастся при сохранении
              </p>
            )}
          </div>

          {/* ── Услуга ─────────────────────────────────────────── */}
          <div>
            <Field label="Что делаем">
              <Input
                value={service}
                onChange={(e) => setService(e.target.value)}
                placeholder="Например, настройка Яндекс.Директа"
              />
            </Field>
            {recentServices.length > 0 && (
              <div className="no-scrollbar -mx-5 mt-2 flex gap-2 overflow-x-auto px-5">
                {recentServices.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setService(s)}
                    className="tap shrink-0 rounded-chip border border-line bg-surface px-3 py-2 text-caption font-medium text-muted transition-colors duration-150 ease-out hover:text-ink"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* ── Сумма и живой расчёт денег ─────────────────────── */}
          <div>
            <Field label="Сумма, ₽">
              <Input
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                inputMode="numeric"
                placeholder="10 000"
                className="tnum text-title font-semibold"
              />
            </Field>
            {amountNum > 0 && (
              <div className="mt-2 flex items-center gap-4 rounded-btn bg-surface-2 px-3.5 py-2.5 text-caption">
                <span className="text-muted">
                  Комиссия {percent(rate)}:{' '}
                  <b className="tnum font-semibold text-ink">{money(commissionNum)}</b>
                </span>
                <span className="text-muted">
                  На руки: <b className="tnum font-semibold text-money">{money(netNum)}</b>
                </span>
              </div>
            )}
          </div>

          {/* ── Источник ───────────────────────────────────────── */}
          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Источник</span>
            <SourcePicker
              sources={sortedSources}
              value={sourceId}
              onChange={setSourceId}
              onCreate={() => setNewSource(true)}
            />
          </div>

          {/* ── Статус ─────────────────────────────────────────── */}
          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Статус</span>
            <Choice
              options={ORDER_STATUSES.map((s) => ({ value: s, label: ORDER_STATUS_LABEL[s] }))}
              value={status}
              onChange={setStatus}
            />
          </div>

          {/* ── Дедлайн ────────────────────────────────────────── */}
          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Срок сдачи</span>
            <div className="flex flex-wrap gap-2">
              {quickDeadlines.map(([label, value]) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => setDeadline(value)}
                  className={cn(
                    'tap rounded-btn border px-3.5 py-2.5 text-body font-medium transition-colors duration-150 ease-out',
                    deadline === value
                      ? 'border-accent bg-accent/10 text-accent dark:bg-accent/15'
                      : 'border-line bg-surface text-muted hover:text-ink',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <Input
              type="date"
              value={deadline ?? ''}
              onChange={(e) => setDeadline(e.target.value || null)}
              className="mt-2"
            />
          </div>

          {/* ── Остальное ──────────────────────────────────────── */}
          <button
            type="button"
            onClick={() => setMore((v) => !v)}
            className="tap flex w-full items-center justify-between rounded-btn border border-line bg-surface px-3.5 text-body font-medium text-muted transition-colors duration-150 ease-out hover:text-ink"
          >
            Остальное: аванс, приоритет, дата, заметки
            <ChevronDown
              size={18}
              className={cn('transition-transform duration-200 ease-out', more && 'rotate-180')}
            />
          </button>

          {more && (
            <div className="space-y-5">
              <Field label="Аванс, ₽" hint={amountNum > 0 ? `Останется получить ${money(Math.max(0, amountNum - parseAmount(prepayment)))}` : undefined}>
                <Input
                  value={prepayment}
                  onChange={(e) => setPrepayment(e.target.value)}
                  inputMode="numeric"
                  placeholder="0"
                  className="tnum"
                />
              </Field>

              <div>
                <span className="mb-1.5 block text-caption font-medium text-muted">Приоритет</span>
                <Choice
                  options={PRIORITIES.map((p) => ({ value: p, label: PRIORITY_LABEL[p] }))}
                  value={priority}
                  onChange={setPriority}
                />
              </div>

              <Field label="Дата заказа">
                <Input type="date" value={date} onChange={(e) => setDate(e.target.value || today())} />
              </Field>

              <Field label="Заметки">
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Договорённости, доступы, что важно не забыть"
                />
              </Field>
            </div>
          )}
        </div>
      </Sheet>

      <SourceEditorSheet
        open={newSource}
        onClose={() => setNewSource(false)}
        onCreated={(s) => setSourceId(s.id)}
      />

      <ConfirmSheet
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={remove}
        title="Удалить заказ?"
        text="Заказ исчезнет из списков и из расчёта денег. Отменить не получится."
      />
    </>
  )
}

/** Выбор источника: сначала частые, остальные — под кнопкой «Ещё». */
function SourcePicker({
  sources,
  value,
  onChange,
  onCreate,
}: {
  sources: Source[]
  value: string | null
  onChange: (id: string | null) => void
  onCreate: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const top = expanded ? sources : sources.slice(0, 6)
  const hidden = sources.length - top.length
  const selectedHidden = value && !top.some((s) => s.id === value)
  const extra = selectedHidden ? sources.filter((s) => s.id === value) : []

  return (
    <div className="flex flex-wrap gap-2">
      {[...top, ...extra].map((s) => (
        <button
          key={s.id}
          type="button"
          onClick={() => onChange(s.id === value ? null : s.id)}
          className={cn(
            'tap inline-flex items-center gap-2 rounded-btn border px-3.5 py-2.5 text-body font-medium transition-colors duration-150 ease-out',
            s.id === value
              ? 'border-accent bg-accent/10 text-accent dark:bg-accent/15'
              : 'border-line bg-surface text-muted hover:text-ink',
          )}
        >
          <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: s.color }} />
          {s.name}
          {s.commissionRate > 0 && (
            <span className="tnum text-caption opacity-70">{percent(s.commissionRate)}</span>
          )}
        </button>
      ))}

      {hidden > 0 && !expanded && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="tap rounded-btn border border-line bg-surface px-3.5 py-2.5 text-body font-medium text-muted transition-colors duration-150 ease-out hover:text-ink"
        >
          Ещё {hidden}
        </button>
      )}

      <button
        type="button"
        onClick={onCreate}
        className="tap inline-flex items-center gap-1.5 rounded-btn border border-dashed border-line bg-surface px-3.5 py-2.5 text-body font-medium text-accent transition-colors duration-150 ease-out hover:border-accent/40"
      >
        <Plus size={16} /> Новый
      </button>
    </div>
  )
}
