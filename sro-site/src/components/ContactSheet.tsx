import { Mail, Phone, X } from 'lucide-react'
import { useEffect, useRef, useState, type ComponentType } from 'react'
import { CONFIGURED, CONTACTS, LINKS } from '../content/contacts'
import { isTopicKey, mailHref, TOPICS, type Topic } from '../content/topics'
import { nbsp } from '../lib/typo'
import { MESSENGERS } from './messengers'
import { MessengerLink } from './MessengerLink'

// «Связаться» на телефоне и планшете — панель со способами связи снизу
// экрана (22.10.2026, разбор удобства, пункт 2).
//
// Раньше любая кнопка «Связаться», «Обсудить задачу», «Проверить мои
// документы» вела к разделу «Связаться» в конце страницы: на главной это
// прыжок на 18 экранов вниз, и вернуться к тому месту, где читал, можно было
// только прокруткой. Теперь на ширине до 1024 px панель выезжает поверх
// страницы: позвонить, мессенджеры, почта, ниже часы офиса и ссылка на адрес
// и карту (раздел «Связаться»). Человек остаётся на своём месте.
// На компьютере кнопки по-прежнему ведут к разделу, а номер телефона
// и «Связаться» всегда стоят в шапке.
//
// Какие ссылки открывают панель: все ссылки на «#contacts», кроме пункта
// «Контакты» в меню телефона (data-direct: человек просил именно раздел)
// и ссылки внутри самой панели. Тема сообщения — data-topic у ссылки
// (ключ из content/topics.ts), иначе тема страницы (проп topic): в WhatsApp
// уже набрано начало сообщения, у письма — тема. Без скрипта ссылки
// работают как раньше — ведут к разделу.
//
// Панель — <dialog> с showModal(): фокус уходит в панель и не выходит из неё,
// страница под ней недоступна, Esc и жест «назад» на Android закрывают
// (событие cancel). Закрывают и касание затемнения, и крестик, и выбор
// способа связи. Выезд снизу и затемнение — CSS (index.css, .contact-sheet);
// при «уменьшить движение» панель стоит сразу.
const QUERY = '(max-width: 1023px)'

const ROW =
  'flex min-h-14 w-full items-center gap-3.5 rounded-2xl px-2 py-1.5 transition-colors active:bg-neutral-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 [@media(hover:hover)]:hover:bg-neutral-100'

function RowBody({ icon: Icon, label, detail }: { icon: ComponentType<{ className?: string }>; label: string; detail?: string }) {
  return (
    <>
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent-50 text-accent-700 ring-1 ring-inset ring-accent-200/70">
        <Icon className="h-5 w-5" />
      </span>
      <span className="min-w-0 flex-1 text-base font-medium text-neutral-950">{label}</span>
      {detail && <span className="min-w-0 truncate text-sm text-neutral-600">{detail}</span>}
    </>
  )
}

export function ContactSheet({ topic: pageTopic }: { topic: Topic }) {
  const ref = useRef<HTMLDialogElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  const [topic, setTopic] = useState<Topic>(pageTopic)

  const close = (after?: () => void) => {
    const dialog = ref.current
    if (!dialog?.open) return
    dialog.removeAttribute('data-shown')
    let done = false
    const finish = () => {
      if (done) return
      done = true
      panel.current?.removeEventListener('transitionend', onEnd)
      dialog.close()
      document.documentElement.classList.remove('sheet-open')
      after?.()
    }
    // Конец выезда самой панели, а не перехода цвета в её строках:
    // transitionend всплывает от любого потомка.
    const onEnd = (event: TransitionEvent) => {
      if (event.target === panel.current && event.propertyName === 'transform') finish()
    }
    panel.current?.addEventListener('transitionend', onEnd)
    // Запасной выход: при «уменьшить движение» и в браузере без переходов
    // transitionend может не прийти.
    window.setTimeout(finish, 600)
  }

  useEffect(() => {
    const narrow = matchMedia(QUERY)
    const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
      const link = (event.target as Element | null)?.closest?.('a[href="#contacts"]') as HTMLAnchorElement | null
      if (!link || link.closest('dialog') || link.hasAttribute('data-direct') || !narrow.matches) return
      const dialog = ref.current
      if (!dialog || dialog.open) return
      event.preventDefault()
      const key = link.dataset.topic
      setTopic(isTopicKey(key) ? TOPICS[key] : pageTopic)
      dialog.showModal()
      document.documentElement.classList.add('sheet-open')
      // Атрибут — со следующего кадра: иначе браузер не увидит начального
      // положения панели (за краем экрана), и она возникнет без выезда.
      requestAnimationFrame(() => requestAnimationFrame(() => dialog.setAttribute('data-shown', '')))
    }
    // Окно стало шире 1023 px при открытой панели (повернули планшет):
    // панель там скрыта (lg:hidden), но модальный <dialog> оставался открытым
    // и запирал страницу — ни прокрутки, ни нажатий. Закрываем сразу, без
    // выезда (23.10.2026, нашла экскурсия diff-tour; стережёт test-site.mjs).
    const onWide = () => {
      const dialog = ref.current
      if (narrow.matches || !dialog?.open) return
      dialog.removeAttribute('data-shown')
      dialog.close()
    }
    document.addEventListener('click', onClick)
    narrow.addEventListener('change', onWide)
    return () => {
      document.removeEventListener('click', onClick)
      narrow.removeEventListener('change', onWide)
    }
  }, [pageTopic])

  return (
    <dialog
      ref={ref}
      aria-labelledby="contact-sheet-title"
      data-contact-sheet
      className="contact-sheet m-0 mt-auto max-h-[100dvh] w-full max-w-none overflow-visible bg-transparent p-0 text-neutral-950 lg:hidden"
      onCancel={(event) => {
        event.preventDefault()
        close()
      }}
      // Любое закрытие — наше, браузерное (жест «назад» без недавнего
      // касания браузер может не дать отменить) или по смене ширины —
      // снимает блокировку прокрутки; повторное снятие безвредно.
      onClose={() => {
        ref.current?.removeAttribute('data-shown')
        document.documentElement.classList.remove('sheet-open')
      }}
      onClick={(event) => {
        // Касание затемнения приходит самому <dialog>, касания по панели —
        // её содержимому.
        if (event.target === event.currentTarget) close()
      }}
    >
      <div
        ref={panel}
        className="sheet-panel mx-auto max-h-[calc(100dvh-0.5rem)] max-w-lg overflow-y-auto overscroll-contain rounded-t-[1.75rem] bg-neutral-50 px-3 pt-2 shadow-[0_-18px_48px_-24px_rgba(20,17,15,0.45)]"
        style={{ paddingBottom: 'calc(0.75rem + env(safe-area-inset-bottom))' }}
      >
        <span className="mx-auto block h-1 w-10 rounded-full bg-neutral-300" aria-hidden="true" />
        <div className="flex items-start justify-between gap-3 px-2 pt-3">
          <div>
            <h2 id="contact-sheet-title" className="font-display text-[1.75rem] font-medium leading-tight">
              Связаться
            </h2>
            <p className="mt-1 text-[0.9375rem] text-neutral-600">{nbsp('Отвечу лично, консультация бесплатная.')}</p>
          </div>
          <button
            type="button"
            onClick={() => close()}
            aria-label="Закрыть"
            className="-mr-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-neutral-700 transition-colors active:bg-neutral-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 [@media(hover:hover)]:hover:bg-neutral-200"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <ul className="mt-3 grid gap-0.5">
          {CONFIGURED.phone && (
            <li>
              <a href={LINKS.tel} data-channel="Позвонить" className={ROW} onClick={() => close()}>
                <RowBody icon={Phone} label="Позвонить" detail={CONTACTS.phone} />
              </a>
            </li>
          )}
          {MESSENGERS.map((messenger) => (
            <li key={messenger.id}>
              <MessengerLink
                channel={messenger.id}
                label={messenger.label}
                text={messenger.id === 'whatsapp' ? topic.text : undefined}
                className={ROW}
                onClick={() => close()}
              >
                <RowBody icon={messenger.icon} label={messenger.label} />
              </MessengerLink>
            </li>
          ))}
          {CONFIGURED.email && (
            <li>
              <a href={mailHref(CONTACTS.email, topic)} data-channel="Почта" className={ROW} onClick={() => close()}>
                <RowBody icon={Mail} label="Почта" detail={CONTACTS.email} />
              </a>
            </li>
          )}
        </ul>
        {/* Строка и ссылка — рядом, если помещаются, иначе ссылка строкой
            ниже: ссылка высотой 44 px внутри абзаца раздвигала его строки.
            Часы не рвутся по тире («9:00–» и «17:00» на разных строках
            на 320 px). */}
        <div className="mt-2 flex flex-wrap items-center justify-between gap-x-4 border-t border-neutral-200 px-2 pt-1 text-sm text-neutral-600">
          <p className="py-2">
            {nbsp('Офис в Ростове-на-Дону,')} <span className="whitespace-nowrap">{CONTACTS.hours}</span>.
          </p>
          <a
            href="#contacts"
            className="inline-flex min-h-11 items-center font-medium text-accent-700 underline underline-offset-2"
            onClick={(event) => {
              event.preventDefault()
              close(() => document.getElementById('contacts')?.scrollIntoView({ block: 'start' }))
            }}
          >
            Адрес и карта
          </a>
        </div>
      </div>
    </dialog>
  )
}
