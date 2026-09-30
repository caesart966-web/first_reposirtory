import { Check, Copy, Mail, MapPin } from 'lucide-react'
import { useState, type ComponentType, type CSSProperties } from 'react'
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
            <div className="mt-10 space-y-4 border-t border-white/10 pt-8 text-sm text-neutral-300">
              {CONFIGURED.email && <EmailLine />}
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

// Каналы связи кружками (30.09.2026, просьба заказчика: «мессенджеры
// красивыми выдвигающимися кружочками, почта тоже с кнопкой — но
// профессионально и не перемудрить»).
//
// С 640 px — пилюля с кружком-значком слева: при наведении светлый кружок
// выдвигается на всю пилюлю, надпись темнеет. Подпись видна всегда:
// кружок без подписи заставлял бы гадать, куда он ведёт.
// На телефоне наведения нет — там четыре кружка в ряд, подпись под каждым,
// как значки приложений; в строку по содержимому четыре пилюли
// на 390 px не помещаются.
// Цвет у значков свой, а не фирменный: зелёный WhatsApp и синий Telegram
// выбились бы из тёплой палитры сайта (синего на сайте нет нарочно).
type Channel = {
  key: string
  label: string
  href: string
  icon: ComponentType<{ className?: string }>
  messenger?: (typeof MESSENGERS)[number]['id']
}

const CHANNELS: Channel[] = [
  ...MESSENGERS.map((m) => ({ key: m.id, label: m.label, href: m.href, icon: m.icon, messenger: m.id })),
  ...(CONFIGURED.email ? [{ key: 'mail', label: 'Почта', href: LINKS.mail, icon: MailGlyph }] : []),
]

function MailGlyph({ className = '' }: { className?: string }) {
  return <Mail className={className} strokeWidth={1.8} />
}

const PILL =
  'group flex flex-col items-center gap-2 focus-visible:outline-none sm:relative sm:isolate sm:flex-row sm:gap-0 sm:overflow-hidden sm:w-full sm:rounded-full sm:pr-5 sm:shadow-[inset_0_0_0_1px_rgba(255,255,255,0.2)] sm:focus-visible:ring-2 sm:focus-visible:ring-accent-300'

function ChannelBody({ channel }: { channel: Channel }) {
  const Icon = channel.icon
  return (
    <>
      {/* Выдвигающаяся подложка: из кружка на всю пилюлю. */}
      <span
        className="absolute inset-y-0 left-0 -z-10 hidden w-14 rounded-full bg-neutral-50 transition-[width] duration-500 ease-silk group-hover:w-full group-focus-visible:w-full sm:block"
        aria-hidden="true"
      />
      <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-neutral-50 text-neutral-950 transition-transform duration-300 ease-silk group-active:scale-95 sm:bg-transparent">
        <Icon className="h-6 w-6" />
      </span>
      <span className="text-[13px] font-medium text-neutral-300 sm:ml-2 sm:text-[15px] sm:text-neutral-50 sm:transition-colors sm:duration-500 sm:group-hover:text-neutral-950 sm:group-focus-visible:text-neutral-950">
        {channel.label}
      </span>
    </>
  )
}

function Channels() {
  if (CHANNELS.length === 0) return null
  return (
    // Сеткой, а не строкой по содержимому: на телефоне кружки поровну
    // в ряд, на планшете пилюли в ряд, с 1024 px (колонка уже) — два
    // на два, иначе четвёртая пилюля уходила одна на вторую строку.
    <ul
      className="mt-8 grid grid-cols-[repeat(var(--n),minmax(0,1fr))] gap-2 sm:gap-3 lg:grid-cols-2"
      style={{ '--n': CHANNELS.length } as CSSProperties}
    >
      {CHANNELS.map((channel) => (
        <li key={channel.key}>
          {channel.messenger ? (
            <MessengerLink channel={channel.messenger} label={channel.label} className={PILL}>
              <ChannelBody channel={channel} />
            </MessengerLink>
          ) : (
            <a href={channel.href} className={PILL}>
              <ChannelBody channel={channel} />
            </a>
          )}
        </li>
      ))}
    </ul>
  )
}

// Адрес почты строкой и кнопка «Скопировать»: у многих на компьютере
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
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <Mail className="h-4 w-4 shrink-0 text-accent-300" aria-hidden="true" />
      <a href={LINKS.mail} className="min-w-0 break-all transition-colors hover:text-neutral-50">
        {CONTACTS.email}
      </a>
      <button
        type="button"
        onClick={copy}
        className="inline-flex min-h-9 items-center gap-1.5 rounded-full border border-white/20 px-3.5 text-xs font-medium text-neutral-200 transition-colors duration-300 hover:border-white/60 hover:text-neutral-50"
      >
        {copied ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
        <span aria-live="polite">{copied ? 'Скопировано' : 'Скопировать'}</span>
      </button>
    </div>
  )
}

