import type { ComponentType } from 'react'
import { CONFIGURED, CONTACTS, LINKS } from '../content/contacts'
import { MaxIcon, TelegramIcon, WhatsAppIcon } from './icons'

// Мессенджеры одним списком. Раньше он был написан дважды — в секции
// «Контакты» и в мобильной панели, — и любой новый канал требовалось вносить
// в оба места. Забытое место означало бы канал, которого на сайте нет.
export type Messenger = {
  label: string
  href: string
  icon: ComponentType<{ className?: string }>
}

// Канал попадает в список только когда для него настроена рабочая ссылка:
// плейсхолдер в contacts.ts гасит канал везде сразу.
export const MESSENGERS: Messenger[] = [
  ...(CONFIGURED.whatsapp
    ? [{ label: 'WhatsApp', href: LINKS.whatsapp, icon: WhatsAppIcon }]
    : []),
  ...(CONFIGURED.telegram
    ? [{ label: 'Telegram', href: LINKS.telegram, icon: TelegramIcon }]
    : []),
  ...(CONFIGURED.max ? [{ label: 'MAX', href: LINKS.max, icon: MaxIcon }] : []),
]

export const CONTACT_PHONE = CONTACTS.phone
