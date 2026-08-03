import { useEffect, useRef, useState } from 'react'
import { cn } from '../lib/utils'

/**
 * Короткий счётчик от предыдущего значения к новому (400-600 мс).
 * Оживляет дашборд, но не мешает: при системной настройке
 * «меньше движения» просто показывает итог.
 */
export function CountUp({
  value,
  format = (n) => String(Math.round(n)),
  duration = 550,
  className,
}: {
  value: number
  format?: (n: number) => string
  duration?: number
  className?: string
}) {
  const [display, setDisplay] = useState(value)
  const fromRef = useRef(value)
  const rafRef = useRef(0)

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const from = fromRef.current
    if (reduced || from === value) {
      fromRef.current = value
      setDisplay(value)
      return
    }
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3) // ease-out
      setDisplay(from + (value - from) * eased)
      if (t < 1) rafRef.current = requestAnimationFrame(tick)
      else fromRef.current = value
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [value, duration])

  return <span className={cn('tnum', className)}>{format(display)}</span>
}
