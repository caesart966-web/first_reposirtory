import { Check, Copy, Mail, MapPin } from 'lucide-react'
import { useState, type CSSProperties } from 'react'
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
// кнопка, — под ним мессенджеры и почта, под линейкой — адрес.
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
    <section id="contacts" className="bg-accent-950 py-20 text-neutral-50 sm:py-32">
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
            <Channels />
            {CONFIGURED.email && <EmailLine />}
            <div className="mt-10 border-t border-white/10 pt-8 text-sm text-neutral-300">
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

// Мессенджеры кружками (30.09.2026, просьба заказчика: «мессенджеры
// красивыми выдвигающимися кружочками — но профессионально и не перемудрить»).
//
// С 640 px — пилюля с кружком-значком слева: при наведении светлый кружок
// выдвигается на всю пилюлю, надпись темнеет. Подпись видна всегда:
// кружок без подписи заставлял бы гадать, куда он ведёт.
// На телефоне наведения нет — там кружки в ряд, подпись под каждым,
// как значки приложений.
// Цвет у значков свой, а не фирменный: зелёный WhatsApp и синий Telegram
// выбились бы из тёплой палитры сайта (синего на сайте нет нарочно).
//
// Почты среди кружков нет (решение заказчика 30.09.2026): кружок «Почта»
// и адрес строкой ниже повторяли друг друга, а адрес нужнее — его
// переписывают и вставляют в веб-почту. Поэтому почта — одной строкой
// с адресом (EmailLine).
const PILL =
  'group flex flex-col items-center gap-2 focus-visible:outline-none sm:relative sm:isolate sm:flex-row sm:gap-0 sm:overflow-hidden sm:rounded-full sm:pr-5 sm:shadow-[inset_0_0_0_1px_rgba(255,255,255,0.2)] sm:focus-visible:ring-2 sm:focus-visible:ring-accent-300'

function Channels() {
  if (MESSENGERS.length === 0) return null
  return (
    // На телефоне — сеткой, кружки поровну в ряд; с 640 px — пилюли
    // по содержимому в строку: в колонке шириной 448 px (экран 1024)
    // три равные пилюли по 141 px «WhatsApp» не вмещали; с 1024 px
    // зазор меньше — запас, чтобы MAX не ушёл один на вторую строку.
    <ul
      className="mt-8 grid grid-cols-[repeat(var(--n),minmax(0,1fr))] gap-2 sm:flex sm:flex-wrap sm:gap-3 lg:gap-2"
      style={{ '--n': MESSENGERS.length } as CSSProperties}
    >
      {MESSENGERS.map(({ id, label, icon: Icon }) => (
        <li key={id}>
          <MessengerLink channel={id} label={label} className={PILL}>
            {/* Выдвигающаяся подложка: из кружка на всю пилюлю. */}
            <span
              className="absolute inset-y-0 left-0 -z-10 hidden w-14 rounded-full bg-neutral-50 transition-[width] duration-500 ease-silk group-hover:w-full group-focus-visible:w-full sm:block"
              aria-hidden="true"
            />
            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-neutral-50 text-neutral-950 transition-transform duration-300 ease-silk group-active:scale-95 sm:bg-transparent">
              <Icon className="h-6 w-6" />
            </span>
            <span className="text-[13px] font-medium text-neutral-300 sm:ml-2 sm:text-[15px] sm:text-neutral-50 sm:transition-colors sm:duration-500 sm:group-hover:text-neutral-950 sm:group-focus-visible:text-neutral-950">
              {label}
            </span>
          </MessengerLink>
        </li>
      ))}
    </ul>
  )
}

// Почта — адресом, крупно, и кнопка «Скопировать»: у многих на компьютере
// ссылка mailto не открывает ничего — почтовая программа не настроена,
// а адрес нужно вставить в веб-почту.
function EmailLine() {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(CONTACTS.email)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      window.location.href = LINKS.mail
    }
  }
  return (
    // Значок — отдельно от строки: на телефоне кнопка уходит под адрес
    // и встаёт ровно под его первой буквой, как адрес под значком ниже.
    <div className="mt-8 flex gap-3">
      <span className="flex h-10 shrink-0 items-center">
        <Mail className="h-5 w-5 text-accent-300 sm:h-6 sm:w-6" strokeWidth={1.8} aria-hidden="true" />
      </span>
      <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2">
        <a
          href={LINKS.mail}
          className="group flex min-h-10 min-w-0 items-center text-xl font-medium text-neutral-50 sm:text-2xl"
        >
          <span className="break-all bg-[linear-gradient(currentColor,currentColor)] bg-[length:0%_1px] bg-left-bottom bg-no-repeat pb-0.5 transition-[background-size] duration-700 ease-silk group-hover:bg-[length:100%_1px]">
            {CONTACTS.email}
          </span>
        </a>
        <button
          type="button"
          onClick={copy}
          className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-white/20 px-4 text-sm font-medium text-neutral-200 transition-colors duration-300 hover:border-white/60 hover:text-neutral-50"
        >
          {copied ? <Check className="h-4 w-4" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}
          <span aria-live="polite">{copied ? 'Скопировано' : 'Скопировать'}</span>
        </button>
      </div>
    </div>
  )
}

