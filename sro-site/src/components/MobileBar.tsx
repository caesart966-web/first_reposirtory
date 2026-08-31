import { Phone } from 'lucide-react'
import { useEffect, useState, type ComponentType } from 'react'
import { LINKS } from '../content/contacts'
import { MESSENGERS } from './messengers'

const itemClasses =
  'flex min-h-[56px] flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-neutral-700 transition active:bg-neutral-50'

type Channel = {
  label: string
  href: string
  icon: ComponentType<{ className?: string }>
  external: boolean
}

// Звонок плюс мессенджеры из общего списка (components/messengers.ts):
// раньше каналы перечислялись здесь заново, и панель могла разойтись с
// подвалом.
const CHANNELS: Channel[] = [
  { label: 'Позвонить', href: LINKS.tel, icon: Phone, external: false },
  ...MESSENGERS.map((m) => ({ label: m.label, href: m.href, icon: m.icon, external: true })),
]

// Классы перечислены целиком: Tailwind собирает только то, что видит в коде.
const GRID_BY_COUNT: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
}

// Фиксированная нижняя панель быстрых контактов — только на мобильных.
// Появляется после прокрутки ниже первого экрана (T18): пока посетитель
// видит герой с кнопкой «Позвонить» и карточкой квиза, панель дублировала бы
// их и съедала нижнюю кромку экрана.
export function MobileBar() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > window.innerHeight * 0.8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav
      className={`fixed inset-x-0 bottom-0 z-50 border-t border-neutral-200 bg-white/95 backdrop-blur transition-transform duration-300 md:hidden ${
        visible ? 'translate-y-0' : 'pointer-events-none translate-y-full'
      }`}
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      aria-label="Быстрая связь"
      aria-hidden={!visible}
    >
      <div
        className={`grid divide-x divide-neutral-200 ${GRID_BY_COUNT[CHANNELS.length] ?? 'grid-cols-3'}`}
      >
        {CHANNELS.map((channel) => (
          <a
            key={channel.label}
            href={channel.href}
            data-channel={channel.label}
            className={itemClasses}
          >
            <channel.icon className="h-5 w-5 text-accent-600" />
            {channel.label}
          </a>
        ))}
      </div>
    </nav>
  )
}
