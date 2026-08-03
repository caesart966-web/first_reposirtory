import { motion } from 'framer-motion'
import { CheckSquare, LayoutGrid, Receipt, Settings, Users } from 'lucide-react'
import type { Tab } from '../hooks/useRoute'
import { cn } from '../lib/utils'

const ITEMS: Array<{ tab: Tab; label: string; icon: typeof LayoutGrid }> = [
  { tab: 'dashboard', label: 'Обзор', icon: LayoutGrid },
  { tab: 'orders', label: 'Заказы', icon: Receipt },
  { tab: 'tasks', label: 'Задачи', icon: CheckSquare },
  { tab: 'clients', label: 'Клиенты', icon: Users },
  { tab: 'settings', label: 'Ещё', icon: Settings },
]

/** Нижняя навигация. Активная вкладка подсвечивается скользящим индикатором. */
export function BottomNav({ active, onSelect }: { active: Tab; onSelect: (tab: Tab) => void }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface/85 pb-[env(safe-area-inset-bottom,0px)] backdrop-blur-xl">
      <div className="mx-auto flex max-w-2xl items-stretch justify-around px-2">
        {ITEMS.map(({ tab, label, icon: Icon }) => {
          const isActive = tab === active
          return (
            <button
              key={tab}
              onClick={() => onSelect(tab)}
              className="tap relative flex flex-1 flex-col items-center gap-1 py-2.5"
              aria-current={isActive ? 'page' : undefined}
            >
              {isActive && (
                <motion.span
                  layoutId="nav-pill"
                  transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                  className="absolute inset-x-1.5 inset-y-1 -z-10 rounded-btn bg-accent/10 dark:bg-accent/15"
                />
              )}
              <Icon
                size={21}
                strokeWidth={isActive ? 2.2 : 1.8}
                className={cn(
                  'transition-colors duration-150 ease-out',
                  isActive ? 'text-accent' : 'text-muted',
                )}
              />
              <span
                className={cn(
                  'text-caption font-medium leading-none transition-colors duration-150 ease-out',
                  isActive ? 'text-accent' : 'text-muted',
                )}
              >
                {label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
