import { AnimatePresence, motion } from 'framer-motion'
import { Check, Info, TriangleAlert } from 'lucide-react'
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

type ToastKind = 'success' | 'error' | 'info'

interface ToastItem {
  id: number
  text: string
  kind: ToastKind
}

const ToastContext = createContext<(text: string, kind?: ToastKind) => void>(() => {})

/** Короткое сообщение внизу экрана, само исчезает. */
export function useToast() {
  return useContext(ToastContext)
}

let counter = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const push = useCallback((text: string, kind: ToastKind = 'success') => {
    const id = ++counter
    setItems((prev) => [...prev.slice(-2), { id, text, kind }])
    setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), 2600)
  }, [])

  const value = useMemo(() => push, [push])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-[calc(80px+env(safe-area-inset-bottom,0px))] z-[60] flex flex-col items-center gap-2 px-4">
        <AnimatePresence initial={false}>
          {items.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 16, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.98 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="pointer-events-auto flex max-w-sm items-center gap-2.5 rounded-btn border border-line bg-surface px-4 py-3 text-body shadow-lift"
            >
              <span
                className={
                  t.kind === 'success'
                    ? 'text-money'
                    : t.kind === 'error'
                      ? 'text-danger'
                      : 'text-accent'
                }
              >
                {t.kind === 'success' ? (
                  <Check size={18} />
                ) : t.kind === 'error' ? (
                  <TriangleAlert size={18} />
                ) : (
                  <Info size={18} />
                )}
              </span>
              <span className="min-w-0">{t.text}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
