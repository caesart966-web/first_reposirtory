import { CONFIGURED, CONTACTS, LINKS, externalLinkProps } from '../content/contacts'
import { MaxIcon, TelegramIcon, WhatsAppIcon } from './icons'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Канал попадает в список только когда для него настроена рабочая ссылка.
const MESSENGERS = [
  ...(CONFIGURED.whatsapp
    ? [{ label: 'WhatsApp', hint: CONTACTS.phone, href: LINKS.whatsapp, icon: WhatsAppIcon }]
    : []),
  ...(CONFIGURED.telegram
    ? [{ label: 'Telegram', hint: 'Написать в чат', href: LINKS.telegram, icon: TelegramIcon }]
    : []),
  ...(CONFIGURED.max
    ? [{ label: 'MAX', hint: 'Написать в чат', href: LINKS.max, icon: MaxIcon }]
    : []),
]

export function Contacts() {
  return (
    <Section id="contacts">
      <SectionHeading
        eyebrow="Контакты"
        title="Свяжитесь удобным способом"
        subtitle="Телефон, почта или мессенджеры — как вам удобнее."
      />
      {/* Не пять одинаковых плиток: слева главный способ связи, справа —
          мессенджеры списком. Телефон должен быть самым крупным элементом. */}
      <div className="mx-auto mt-10 grid max-w-4xl gap-10 lg:grid-cols-2 lg:gap-16">
        <Reveal>
          <a
            href={LINKS.tel}
            className="block text-3xl font-bold tracking-tight text-neutral-950 transition-colors hover:text-accent-700 sm:text-4xl"
          >
            {CONTACTS.phone}
          </a>
          <a
            href={LINKS.mail}
            className="mt-4 block text-lg text-neutral-700 transition-colors hover:text-accent-700"
          >
            {CONTACTS.email}
          </a>
        </Reveal>

        <Reveal delay={100}>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-600">
            Мессенджеры
          </p>
          <div className="mt-4 divide-y divide-neutral-200 border-y border-neutral-200">
            {MESSENGERS.map((channel) => (
              <a
                key={channel.label}
                href={channel.href}
                {...externalLinkProps(true)}
                className="group flex items-center gap-4 py-4 transition-colors duration-200 hover:bg-accent-50/40"
              >
                <channel.icon className="h-5 w-5 shrink-0 text-accent-600" />
                <span className="min-w-0 flex-1">
                  <span className="block font-medium text-neutral-950">{channel.label}</span>
                  <span className="block text-sm text-neutral-600">{channel.hint}</span>
                </span>
              </a>
            ))}
          </div>
        </Reveal>
      </div>
    </Section>
  )
}
