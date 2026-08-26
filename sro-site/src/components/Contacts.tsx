import { Globe, Mail, Phone } from 'lucide-react'
import { CONFIGURED, CONTACTS, LINKS, externalLinkProps } from '../content/contacts'
import { MaxIcon, TelegramIcon, WhatsAppIcon } from './icons'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

const CARDS = [
  {
    icon: Phone,
    label: 'Телефон',
    value: CONTACTS.phone,
    href: LINKS.tel,
    configured: false,
  },
  {
    icon: Mail,
    label: 'E-mail',
    value: CONTACTS.email,
    href: LINKS.mail,
    configured: false,
  },
  {
    icon: WhatsAppIcon,
    label: 'WhatsApp',
    value: CONTACTS.phone,
    href: LINKS.whatsapp,
    configured: CONFIGURED.whatsapp,
  },
  {
    icon: TelegramIcon,
    label: 'Telegram',
    value: 'Написать в Telegram',
    href: LINKS.telegram,
    configured: CONFIGURED.telegram,
  },
  {
    icon: MaxIcon,
    label: 'MAX',
    value: CONFIGURED.max ? 'Написать в MAX' : CONTACTS.max,
    href: LINKS.max,
    configured: CONFIGURED.max,
  },
]

export function Contacts() {
  return (
    <Section id="contacts">
      <SectionHeading
        eyebrow="Контакты"
        title="Свяжитесь удобным способом"
        subtitle="Телефон, почта или мессенджеры — отвечаю лично."
      />
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {CARDS.map((card, index) => (
          <Reveal key={card.label} delay={(index % 5) * 60} className="h-full">
            <a
              href={card.href}
              {...externalLinkProps(card.configured)}
              className="flex h-full flex-col items-start rounded-2xl border border-neutral-200 bg-white p-6 shadow-card transition-all duration-200 hover:-translate-y-1 hover:border-accent-200 hover:shadow-card-hover"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-50 text-accent-600">
                <card.icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <p className="mt-4 text-sm text-neutral-500">{card.label}</p>
              <p className="mt-1 break-words font-semibold text-neutral-950">{card.value}</p>
            </a>
          </Reveal>
        ))}
      </div>
      <Reveal className="mt-8">
        <p className="flex items-center justify-center gap-2 text-center text-sm text-neutral-500">
          <Globe className="h-4 w-4 text-accent-600" aria-hidden="true" />
          Вступление в СРО во всех регионах России — работаю дистанционно
        </p>
      </Reveal>
    </Section>
  )
}
