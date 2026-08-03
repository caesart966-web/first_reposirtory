import { useLiveQuery } from 'dexie-react-hooks'
import { useMemo } from 'react'
import { db } from '../db/db'
import type { Client, Order, Source, Task } from '../db/types'

// ─────────────────────────────────────────────────────────────────
// Живые подписки на базу: любое изменение данных само перерисовывает
// экраны. Пока данные читаются — хук возвращает undefined (показываем
// скелетоны).
// ─────────────────────────────────────────────────────────────────

export function useSources(): Source[] | undefined {
  return useLiveQuery(() => db.sources.orderBy('order').toArray(), [])
}

export function useClients(): Client[] | undefined {
  return useLiveQuery(
    () => db.clients.toArray().then((list) => list.sort((a, b) => a.name.localeCompare(b.name, 'ru'))),
    [],
  )
}

export function useOrders(): Order[] | undefined {
  return useLiveQuery(
    () => db.orders.toArray().then((list) => list.sort((a, b) => b.date.localeCompare(a.date))),
    [],
  )
}

export function useTasks(): Task[] | undefined {
  return useLiveQuery(() => db.tasks.toArray(), [])
}

export function useMap<T extends { id: string }>(list: T[] | undefined): Map<string, T> {
  return useMemo(() => new Map((list ?? []).map((x) => [x.id, x])), [list])
}

/** Всё сразу — так удобнее большинству экранов. */
export function useAppData() {
  const sources = useSources()
  const clients = useClients()
  const orders = useOrders()
  const tasks = useTasks()
  const sourceById = useMap(sources)
  const clientById = useMap(clients)
  const loading = !sources || !clients || !orders || !tasks
  return { sources, clients, orders, tasks, sourceById, clientById, loading }
}

/** Часто используемые источники — их показываем в форме заказа первыми. */
export function useSourceUsage(orders: Order[] | undefined): Map<string, number> {
  return useMemo(() => {
    const m = new Map<string, number>()
    for (const o of orders ?? []) {
      if (!o.sourceId) continue
      m.set(o.sourceId, (m.get(o.sourceId) ?? 0) + 1)
    }
    return m
  }, [orders])
}
