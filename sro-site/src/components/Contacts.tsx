import { Mail, Phone } from 'lucide-react'
import type { ComponentType } from 'react'
import { CONFIGURED, CONTACTS, LINKS, externalLinkProps } from '../content/contacts'
import { MaxIcon, TelegramIcon, WhatsAppIcon } from './icons'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

type Channel = {
  label: string
  hint: string
  href: string
  icon: ComponentType<{ className?: string }>
}

// Канал попадает в список только когда для него настроена рабочая ссылка.
const MESSENGERS: Channel[] = [
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

// Классы перечислены целиком: Tailwind собирает только то, что видит в коде,
// и класс, собранный подстановкой, в CSS не попадёт. Мессенджеров от одного
// до трёх — сколько настроено в contacts.ts.
//
// Три плитки встают в ряд только с lg. На планшете панель ужимается вместе с
// экраном, плитка выходит 205px, и подпись WhatsApp — номер телефона — режется
// многоточием. Обрезанный номер читается как ошибка вёрстки, поэтому до lg
// три плитки идут в две колонки.
const GRID_BY_COUNT: Record<number, string> = {
  1: 'sm:grid-cols-1',
  2: 'sm:grid-cols-2',
  3: 'sm:grid-cols-2 lg:grid-cols-3',
}

export function Contacts() {
  return (
    <Section id="contacts">
      <SectionHeading
        eyebrow="Контакты"
        title="Свяжитесь удобным способом"
        subtitle="Консультация бесплатная — и первая, и все следующие. Платите только за работу."
      />
      {/* Вся секция — одна панель-визитка (rounded-3xl, как у панелей этого
          масштаба: карточка героя, квиз, «Что войдёт в пакет»). Внутри —
          два яруса сверху вниз, а не две колонки бок о бок: колонки делили
          каналы поровну только при трёх мессенджерах, а их от одного до трёх,
          и правый столбец то перевешивал левый, то не добирал до него. */}
      <Reveal className="mx-auto mt-10 max-w-3xl">
        <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-card sm:p-10">
          {/* Заголовок показываем только если под ним что-то будет: пока номер
              или адрес стоят плейсхолдером, они не выводятся, и подпись
              «Позвонить или написать» повисла бы над пустотой. */}
          {(CONFIGURED.phone || CONFIGURED.email) && (
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-600">
              Позвонить или написать
            </p>
          )}
          {(CONFIGURED.phone || CONFIGURED.email) && (
          <div className="mt-4 divide-y divide-neutral-200">
            {CONFIGURED.phone && (
              <a
                href={LINKS.tel}
                className="flex items-center gap-4 py-4 transition-colors duration-200 hover:bg-accent-50/40"
              >
                <Phone className="h-5 w-5 shrink-0 text-accent-600" aria-hidden="true" />
                <span className="text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl">
                  {CONTACTS.phone}
                </span>
              </a>
            )}
            {CONFIGURED.email && (
              <a
                href={LINKS.mail}
                className="flex items-center gap-4 py-4 transition-colors duration-200 hover:bg-accent-50/40"
              >
                <Mail className="h-5 w-5 shrink-0 text-accent-600" aria-hidden="true" />
                {/* break-all: без него длинный адрес рядом с иконкой вылезал
                    за карточку на узких экранах. */}
                <span className="min-w-0 break-all text-lg text-neutral-700">{CONTACTS.email}</span>
              </a>
            )}
          </div>
          )}

          {MESSENGERS.length > 0 && (
            <>
              <p
                className={`text-sm font-semibold uppercase tracking-[0.16em] text-neutral-600 ${
                  CONFIGURED.phone || CONFIGURED.email ? 'mt-8' : ''
                }`}
              >
                Мессенджеры
              </p>
              {/* Плитки, а не строки списка: у телефона и почты по одному
                  адресу на строку, а мессенджеры — равнозначный ряд, и ряд
                  должен читаться рядом. Иконка в скруглённом квадрате —
                  тот же приём, что у карточек услуг. */}
              <div
                className={`mt-4 grid gap-3 ${GRID_BY_COUNT[MESSENGERS.length] ?? 'sm:grid-cols-3'}`}
              >
                {MESSENGERS.map((channel) => (
                  <a
                    key={channel.label}
                    href={channel.href}
                    {...externalLinkProps(true)}
                    className="flex items-center gap-3 rounded-2xl border border-neutral-200 p-4 transition-colors duration-200 hover:border-accent-300 hover:bg-accent-50/40"
                  >
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-50 text-accent-600">
                      <channel.icon className="h-5 w-5" />
                    </span>
                    <span className="min-w-0">
                      <span className="block font-medium text-neutral-950">{channel.label}</span>
                      <span className="block truncate text-sm text-neutral-600">
                        {channel.hint}
                      </span>
                    </span>
                  </a>
                ))}
              </div>
            </>
          )}
        </div>
      </Reveal>
    </Section>
  )
}
