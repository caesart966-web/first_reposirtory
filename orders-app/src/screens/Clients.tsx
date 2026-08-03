import { Plus, Search, Trash2, Users } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Header } from '../components/Header'
import { useAppData } from '../hooks/useData'
import { createClient, deleteClient, updateClient } from '../db/repo'
import {
  CLIENT_STATUSES,
  CLIENT_STATUS_LABEL,
  CLIENT_STATUS_TONE,
  ORDER_STATUS_SHORT,
  ORDER_STATUS_TONE,
  type Client,
  type ClientStatus,
  type Order,
} from '../db/types'
import type { Tab } from '../hooks/useRoute'
import { isActive, net } from '../lib/calc'
import { formatDate, money, plural } from '../lib/utils'
import { Button, IconButton } from '../ui/Button'
import { Card } from '../ui/Card'
import { Choice } from '../ui/Choice'
import { Field, Input, SearchInput, Textarea } from '../ui/Field'
import { EmptyState, SkeletonList } from '../ui/Feedback'
import { Pill } from '../ui/Pill'
import { ConfirmSheet, Sheet } from '../ui/Sheet'
import { useToast } from '../ui/Toast'

interface Props {
  onNavigate: (tab: Tab, params?: Record<string, string>) => void
  onOpenOrder: (order: Order) => void
}

export function Clients({ onNavigate, onOpenOrder }: Props) {
  const { clients, orders, sources, loading } = useAppData()
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState<Client | null>(null)
  const [creating, setCreating] = useState(false)

  // По каждому клиенту считаем число заказов и деньги
  const stats = useMemo(() => {
    const m = new Map<string, { count: number; amount: number; onHand: number; open: number }>()
    for (const o of orders ?? []) {
      const cur = m.get(o.clientId) ?? { count: 0, amount: 0, onHand: 0, open: 0 }
      cur.count += 1
      cur.amount += o.amount
      cur.onHand += net(o)
      if (isActive(o)) cur.open += 1
      m.set(o.clientId, cur)
    }
    return m
  }, [orders])

  const list = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (clients ?? [])
      .filter((c) => !q || c.name.toLowerCase().includes(q) || c.niche.toLowerCase().includes(q))
      .sort((a, b) => (stats.get(b.id)?.amount ?? 0) - (stats.get(a.id)?.amount ?? 0))
  }, [clients, query, stats])

  return (
    <div>
      <Header
        title="Клиенты"
        subtitle={clients?.length ? plural(clients.length, 'клиент', 'клиента', 'клиентов') : undefined}
        action={
          <IconButton
            onClick={() => setCreating(true)}
            aria-label="Новый клиент"
            className="border border-line bg-surface"
          >
            <Plus size={20} />
          </IconButton>
        }
      />

      {(clients?.length ?? 0) > 0 && (
        <div className="px-4">
          <SearchInput
            icon={<Search size={18} />}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Имя или ниша"
          />
        </div>
      )}

      <div className="mt-4 space-y-3 px-4">
        {loading ? (
          <SkeletonList count={3} />
        ) : list.length === 0 ? (
          <EmptyState
            icon={<Users size={26} />}
            title={query ? 'Никого не нашлось' : 'Клиентов пока нет'}
            text={
              query
                ? 'Попробуй другое имя или нишу.'
                : 'Клиенты появятся сами, когда добавишь заказы. Или заведи вручную.'
            }
            actionLabel={query ? undefined : 'Добавить клиента'}
            onAction={query ? undefined : () => setCreating(true)}
          />
        ) : (
          list.map((c) => {
            const s = stats.get(c.id)
            return (
              <Card key={c.id} pressable onClick={() => setEditing(c)} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="truncate text-body-lg font-semibold tracking-tight">{c.name}</h3>
                    <p className="mt-0.5 truncate text-caption text-muted">
                      {c.niche || 'Ниша не указана'}
                      {c.contact ? ` · ${c.contact}` : ''}
                    </p>
                  </div>
                  <Pill tone={CLIENT_STATUS_TONE[c.status]}>{CLIENT_STATUS_LABEL[c.status]}</Pill>
                </div>
                <div className="mt-3 flex items-end justify-between gap-3">
                  <span className="tnum text-body-lg font-semibold">{money(s?.amount ?? 0)}</span>
                  <span className="text-caption text-muted">
                    {plural(s?.count ?? 0, 'заказ', 'заказа', 'заказов')}
                    {s?.open ? ` · ${s.open} в работе` : ''}
                  </span>
                </div>
              </Card>
            )
          })
        )}
      </div>

      <ClientSheet
        open={creating || !!editing}
        client={editing}
        sources={sources ?? []}
        orders={(orders ?? []).filter((o) => o.clientId === editing?.id)}
        onClose={() => {
          setCreating(false)
          setEditing(null)
        }}
        onOpenOrder={onOpenOrder}
        onShowAll={(id) => {
          setEditing(null)
          onNavigate('orders', { client: id })
        }}
      />
    </div>
  )
}

/** Карточка клиента: правка полей, его заказы и заметки. */
function ClientSheet({
  open,
  client,
  sources,
  orders,
  onClose,
  onOpenOrder,
  onShowAll,
}: {
  open: boolean
  client: Client | null
  sources: Array<{ id: string; name: string; color: string }>
  orders: Order[]
  onClose: () => void
  onOpenOrder: (order: Order) => void
  onShowAll: (clientId: string) => void
}) {
  const toast = useToast()
  const [name, setName] = useState('')
  const [contact, setContact] = useState('')
  const [niche, setNiche] = useState('')
  const [status, setStatus] = useState<ClientStatus>('active')
  const [defaultSourceId, setDefaultSourceId] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  const [confirm, setConfirm] = useState(false)

  useEffect(() => {
    if (!open) return
    setName(client?.name ?? '')
    setContact(client?.contact ?? '')
    setNiche(client?.niche ?? '')
    setStatus(client?.status ?? 'active')
    setDefaultSourceId(client?.defaultSourceId ?? null)
    setNotes(client?.notes ?? '')
  }, [open, client])

  const save = async () => {
    if (!name.trim()) return toast('Впиши имя клиента', 'error')
    const payload = { name: name.trim(), contact, niche, status, defaultSourceId, notes }
    if (client) {
      await updateClient(client.id, payload)
      toast('Клиент обновлён')
    } else {
      await createClient(payload)
      toast('Клиент добавлен')
    }
    onClose()
  }

  const remove = async () => {
    if (!client) return
    await deleteClient(client.id)
    toast('Клиент и его заказы удалены')
    onClose()
  }

  const total = orders.reduce((sum, o) => sum + o.amount, 0)

  return (
    <>
      <Sheet
        open={open}
        onClose={onClose}
        title={client ? client.name : 'Новый клиент'}
        subtitle={
          client && orders.length
            ? `${plural(orders.length, 'заказ', 'заказа', 'заказов')} на ${money(total)}`
            : undefined
        }
        footer={
          <div className="flex gap-3">
            {client && (
              <Button variant="danger" size="lg" onClick={() => setConfirm(true)} aria-label="Удалить">
                <Trash2 size={18} />
              </Button>
            )}
            <Button full size="lg" onClick={save}>
              Сохранить
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <Field label="Имя или компания">
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Как записать" />
          </Field>

          <Field label="Контакт">
            <Input
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              placeholder="Телефон, telegram, почта"
            />
          </Field>

          <Field label="Ниша">
            <Input
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
              placeholder="Например, стоматология"
            />
          </Field>

          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Статус</span>
            <Choice
              options={CLIENT_STATUSES.map((s) => ({ value: s, label: CLIENT_STATUS_LABEL[s] }))}
              value={status}
              onChange={setStatus}
            />
          </div>

          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Источник по умолчанию</span>
            <Choice
              options={sources.map((s) => ({ value: s.id, label: s.name, color: s.color }))}
              value={defaultSourceId}
              onChange={(id) => setDefaultSourceId(id === defaultSourceId ? null : id)}
            />
          </div>

          <Field label="Заметки">
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Доступы, договорённости, особенности"
            />
          </Field>

          {client && orders.length > 0 && (
            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="text-caption font-medium text-muted">Заказы</span>
                <button
                  onClick={() => onShowAll(client.id)}
                  className="text-caption font-medium text-accent"
                >
                  Показать списком
                </button>
              </div>
              <div className="divide-y divide-line overflow-hidden rounded-card border border-line">
                {orders.slice(0, 8).map((o) => (
                  <button
                    key={o.id}
                    onClick={() => {
                      onClose()
                      onOpenOrder(o)
                    }}
                    className="flex w-full items-center gap-3 px-3.5 py-3 text-left transition-colors duration-150 ease-out hover:bg-surface-2"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-body">{o.service}</div>
                      <div className="text-caption text-muted">{formatDate(o.date)}</div>
                    </div>
                    <span className="tnum shrink-0 text-body font-semibold">{money(o.amount)}</span>
                    <Pill tone={ORDER_STATUS_TONE[o.status]} size="sm">
                      {ORDER_STATUS_SHORT[o.status]}
                    </Pill>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </Sheet>

      <ConfirmSheet
        open={confirm}
        onClose={() => setConfirm(false)}
        onConfirm={remove}
        title="Удалить клиента?"
        text="Вместе с ним удалятся все его заказы. Это не отменить."
      />
    </>
  )
}
