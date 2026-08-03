import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { BottomNav } from './components/BottomNav'
import { seedIfEmpty } from './db/db'
import type { Order } from './db/types'
import { useRoute, type Tab } from './hooks/useRoute'
import { checkReminders } from './lib/notifications'
import { Clients } from './screens/Clients'
import { Dashboard } from './screens/Dashboard'
import { OrderForm } from './screens/OrderForm'
import { Orders } from './screens/Orders'
import { Settings } from './screens/Settings'
import { Tasks } from './screens/Tasks'

export function App() {
  const { route, navigate } = useRoute()
  const [formOpen, setFormOpen] = useState(false)
  const [editingOrder, setEditingOrder] = useState<Order | null>(null)

  // Первое открытие: заполняем справочник источников
  useEffect(() => {
    void seedIfEmpty()
  }, [])

  // Напоминания: проверяем при запуске и раз в час, пока приложение открыто
  useEffect(() => {
    void checkReminders()
    const id = setInterval(() => void checkReminders(), 60 * 60 * 1000)
    return () => clearInterval(id)
  }, [])

  const openNew = () => {
    setEditingOrder(null)
    setFormOpen(true)
  }

  const openOrder = (order: Order) => {
    setEditingOrder(order)
    setFormOpen(true)
  }

  const go = (tab: Tab, params?: Record<string, string>) => navigate(tab, params)

  return (
    <div className="mx-auto min-h-dvh max-w-2xl pb-[calc(84px+env(safe-area-inset-bottom,0px))]">
      {/* Экраны переключаются мягким сдвигом с затуханием */}
      <AnimatePresence mode="wait" initial={false}>
        <motion.main
          key={route.tab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
        >
          {route.tab === 'dashboard' && (
            <Dashboard onNavigate={go} onNewOrder={openNew} onOpenOrder={openOrder} />
          )}
          {route.tab === 'orders' && (
            <Orders
              params={route.params}
              onNewOrder={openNew}
              onOpenOrder={openOrder}
              onResetParams={() => navigate('orders')}
            />
          )}
          {route.tab === 'tasks' && <Tasks />}
          {route.tab === 'clients' && <Clients onNavigate={go} onOpenOrder={openOrder} />}
          {route.tab === 'settings' && <Settings params={route.params} />}
        </motion.main>
      </AnimatePresence>

      <BottomNav active={route.tab} onSelect={(tab) => navigate(tab)} />

      <OrderForm open={formOpen} onClose={() => setFormOpen(false)} order={editingOrder} />
    </div>
  )
}
