import { MessageCircle, Phone, Send } from 'lucide-react'
import { CONFIGURED, LINKS, externalLinkProps } from '../content/contacts'

const itemClasses =
  'flex min-h-[56px] flex-col items-center justify-center gap-0.5 text-xs font-medium text-neutral-700 transition active:bg-neutral-50'

// Фиксированная нижняя панель быстрых контактов — только на мобильных.
export function MobileBar() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 border-t border-neutral-200 bg-white/95 backdrop-blur md:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      aria-label="Быстрая связь"
    >
      <div className="grid grid-cols-3 divide-x divide-neutral-200">
        <a href={LINKS.tel} className={itemClasses}>
          <Phone className="h-5 w-5 text-accent-600" aria-hidden="true" />
          Позвонить
        </a>
        <a
          href={LINKS.whatsapp}
          {...externalLinkProps(CONFIGURED.whatsapp)}
          className={itemClasses}
        >
          <MessageCircle className="h-5 w-5 text-accent-600" aria-hidden="true" />
          WhatsApp
        </a>
        <a href={LINKS.max} {...externalLinkProps(CONFIGURED.max)} className={itemClasses}>
          <Send className="h-5 w-5 text-accent-600" aria-hidden="true" />
          MAX
        </a>
      </div>
    </nav>
  )
}
