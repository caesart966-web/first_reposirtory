import { Phone } from 'lucide-react'
import type { ComponentType } from 'react'
import { CONFIGURED, LINKS, externalLinkProps } from '../content/contacts'
import { MaxIcon, TelegramIcon, WhatsAppIcon } from './icons'

const itemClasses =
  'flex min-h-[56px] flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-neutral-700 transition active:bg-neutral-50'

type Channel = {
  label: string
  href: string
  icon: ComponentType<{ className?: string }>
  external: boolean
}

// Канал попадает в панель только если для него настроена рабочая ссылка.
const CHANNELS: Channel[] = [
  { label: 'Позвонить', href: LINKS.tel, icon: Phone, external: false },
  ...(CONFIGURED.whatsapp
    ? [{ label: 'WhatsApp', href: LINKS.whatsapp, icon: WhatsAppIcon, external: true }]
    : []),
  ...(CONFIGURED.telegram
    ? [{ label: 'Telegram', href: LINKS.telegram, icon: TelegramIcon, external: true }]
    : []),
  ...(CONFIGURED.max ? [{ label: 'MAX', href: LINKS.max, icon: MaxIcon, external: true }] : []),
]

// Классы перечислены целиком: Tailwind собирает только то, что видит в коде.
const GRID_BY_COUNT: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
}

// Фиксированная нижняя панель быстрых контактов — только на мобильных.
export function MobileBar() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 border-t border-neutral-200 bg-white/95 backdrop-blur md:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      aria-label="Быстрая связь"
    >
      <div
        className={`grid divide-x divide-neutral-200 ${GRID_BY_COUNT[CHANNELS.length] ?? 'grid-cols-3'}`}
      >
        {CHANNELS.map((channel) => (
          <a
            key={channel.label}
            href={channel.href}
            {...externalLinkProps(channel.external)}
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
