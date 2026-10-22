import { Phone } from 'lucide-react'
import { useEffect, useState, type ComponentType } from 'react'
import { LINKS, messengerHref } from '../content/contacts'
import { TOPICS, type Topic } from '../content/topics'
import { MESSENGERS } from './messengers'

const itemClasses =
  'flex min-h-[3.5rem] flex-col items-center justify-center gap-0.5 text-[0.6875rem] font-medium text-neutral-700 transition-colors active:bg-neutral-100'

type Channel = {
  id: string
  label: string
  href: string
  icon: ComponentType<{ className?: string }>
  external: boolean
}

// Звонок плюс мессенджеры из общего списка (components/messengers.ts):
// раньше каналы перечислялись здесь заново, и панель могла разойтись с
// подвалом.
const CHANNELS: Channel[] = [
  { id: 'tel', label: 'Позвонить', href: LINKS.tel, icon: Phone, external: false },
  ...MESSENGERS.map((m) => ({ id: m.id, label: m.label, href: m.href, icon: m.icon, external: true })),
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
// видит первый экран с кнопками «Связаться» и «Позвонить», панель дублировала
// бы их и съедала нижнюю кромку экрана.
// topic — тема страницы (content/topics.ts): у WhatsApp уже набрано начало
// сообщения, как в разделе «Связаться».
export function MobileBar({ topic = TOPICS.general }: { topic?: Topic }) {
  const [visible, setVisible] = useState(false)

  // Прячется и в конце страницы (29.09.2026): как только на экран
  // въезжает раздел «Связаться», панель повторяла бы его — тот же номер и
  // те же мессенджеры крупно прямо над ней, — а ниже закрывала бы
  // реквизиты и оговорку в подвале.
  useEffect(() => {
    const onScroll = () => {
      const contacts = document.getElementById('contacts')
      const atContacts = contacts ? contacts.getBoundingClientRect().top < window.innerHeight : false
      setVisible(window.scrollY > window.innerHeight * 0.8 && !atContacts)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [])

  return (
    <nav
      className={`fixed inset-x-0 bottom-0 z-50 border-t border-neutral-200 bg-neutral-50/95 backdrop-blur transition-transform duration-500 ease-silk md:hidden ${
        visible ? 'translate-y-0' : 'pointer-events-none translate-y-full'
      }`}
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      aria-label="Быстрая связь"
      aria-hidden={!visible}
      // Спрятанная панель не только не видна, но и недоступна с клавиатуры
      // (inert, 22.10.2026): до этого Tab заходил в невидимые ссылки, а диктор
      // их не читал (aria-hidden) — проверка доступности axe отмечала это
      // ошибкой. React 18 не знает inert, поэтому атрибут — строкой.
      {...(visible ? {} : { inert: '' })}
    >
      <div
        className={`grid divide-x divide-neutral-200 ${GRID_BY_COUNT[CHANNELS.length] ?? 'grid-cols-3'}`}
      >
        {CHANNELS.map((channel) => (
          <a
            key={channel.label}
            href={channel.id === 'whatsapp' ? messengerHref('whatsapp', topic.text) : channel.href}
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
