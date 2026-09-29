import { Mail, MapPin } from 'lucide-react'
import { CONFIGURED, CONTACTS, LINKS } from '../content/contacts'
import { REQUISITES } from '../content/facts'
import { MESSENGERS } from './messengers'
import { MessengerLink } from './MessengerLink'
import { Reveal, RevealText } from './ui/Reveal'

// Раздел «Связаться» — внизу КАЖДОЙ страницы, перед подвалом.
//
// Он заменил квиз. 24.09.2026 заказчик попросил убрать форму заявки: сайт
// рекламный, заявки принимаются звонком и в мессенджерах. Отсюда устройство
// раздела: номер набран крупнее всего на странице — это и есть главная
// кнопка, — под ним мессенджеры, ниже почта и адрес.
//
// id="contacts" живёт здесь, а не на подвале: на него ведут «Связаться» в
// шапке и кнопки в разделах, и на любой странице он местный — человек не
// уходит со страницы услуги на главную, чтобы позвонить.
//
// Ни формы, ни полей: сайт не собирает данные посетителей, и политика
// обработки персональных данных на нём больше не нужна (ч. 2 ст. 18.1
// 152-ФЗ касается данных, собираемых через сайт).
/**
 * lead — своя строка под заголовком у страниц видов и услуг
 * («Отвечу на вопросы по СРО строителей…»); на главной — общая.
 */
export function Contact({
  lead = 'Консультация бесплатная — и первая, и все следующие. Работаю дистанционно, личный визит не нужен.',
}: {
  lead?: string
}) {
  return (
    <section id="contacts" className="bg-accent-950 py-24 text-neutral-50 sm:py-32">
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-end lg:gap-16">
          <div>
            <RevealText
              text={"Расскажите о\u00A0задаче\u00A0— отвечу лично"}
              className="font-display text-[2.6rem] font-medium leading-[1.02] sm:text-5xl lg:text-[3.6rem]"
            />
            <Reveal delay={150}>
              <p className="mt-6 max-w-md text-lg leading-relaxed text-neutral-300">{lead}</p>
            </Reveal>
          </div>

          <Reveal delay={200}>
            {CONFIGURED.phone && (
              <a
                href={LINKS.tel}
                data-channel="Позвонить"
                className="group block whitespace-nowrap font-display text-[2.35rem] font-medium leading-none tracking-tight text-neutral-50 min-[380px]:text-[2.7rem] sm:text-6xl"
              >
                <span className="bg-[linear-gradient(currentColor,currentColor)] bg-[length:0%_1px] bg-left-bottom bg-no-repeat pb-1 transition-[background-size] duration-700 ease-silk group-hover:bg-[length:100%_1px]">
                  {CONTACTS.phone}
                </span>
              </a>
            )}
            {MESSENGERS.length > 0 && (
              // На телефоне три кнопки — ровным рядом равной ширины: в строку
              // по содержимому MAX уходил один на вторую строку. Уже 380 px
              // значок прячется, иначе «WhatsApp» не помещается в треть.
              <ul
                className="mt-8 grid gap-2 sm:flex sm:flex-wrap sm:gap-2.5"
                style={{ gridTemplateColumns: `repeat(${MESSENGERS.length}, minmax(0, 1fr))` }}
              >
                {MESSENGERS.map((channel) => (
                  <li key={channel.label}>
                    <MessengerLink
                      channel={channel.id}
                      label={channel.label}
                      className="flex h-12 items-center justify-center gap-2 rounded-full border border-white/20 px-2 text-sm font-medium text-neutral-50 transition-colors duration-500 ease-silk hover:border-white/60 hover:bg-white/5 sm:inline-flex sm:gap-2.5 sm:px-5 sm:text-[15px]"
                    >
                      <channel.icon className="hidden h-[18px] w-[18px] shrink-0 text-accent-300 min-[380px]:block" />
                      {channel.label}
                    </MessengerLink>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-10 space-y-3 border-t border-white/10 pt-8 text-sm text-neutral-300">
              {CONFIGURED.email && (
                <a
                  href={LINKS.mail}
                  className="flex items-start gap-3 transition-colors hover:text-neutral-50"
                >
                  <Mail className="mt-0.5 h-4 w-4 shrink-0 text-accent-300" aria-hidden="true" />
                  <span className="min-w-0 break-all">{CONTACTS.email}</span>
                </a>
              )}
              <p className="flex items-start gap-3">
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-accent-300" aria-hidden="true" />
                <span>{REQUISITES.address}</span>
              </p>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
