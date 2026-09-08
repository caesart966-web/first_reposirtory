import { AppWindow, Globe } from 'lucide-react'
import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type FocusEvent,
  type ReactNode,
} from 'react'
import { LINKS, MESSENGER_TARGETS, type MessengerKey } from '../content/contacts'
import { useDesktopPointer } from '../lib/useDesktopPointer'

// Ссылка на мессенджер, которая ведёт себя по-разному на телефоне и на
// компьютере, — и это вся её суть.
//
// Телефон и планшет: обычный переход по универсальной ссылке (wa.me, t.me,
// max.ru) в той же вкладке. Только так iOS и Android открывают приложение;
// с target="_blank" вместо него открывалась пустая страница — заказчик
// поймал это на живом сайте, подробности в README.
//
// Компьютер: раньше та же ссылка уводила на страницу-прокладку мессенджера
// («Продолжить в чате», «Отправить сообщение»), и до самого чата было ещё
// два нажатия и ожидание. Теперь кнопка сразу предлагает выбор: веб-версия
// открывается в новой вкладке напрямую, минуя прокладку, а приложение —
// по его собственной схеме (whatsapp://, tg://), которую перехватывает
// установленная программа. Страница при этом никуда не уходит.
//
// У MAX опубликованного адреса веб-версии чата нет, а ссылка профиля
// получена из QR-кода заказчика — единственный адрес, который точно работает.
// Поэтому на компьютере она открывается в новой вкладке без выбора.
type Props = {
  channel: MessengerKey
  /** Имя канала на экране — оно же идёт в data-channel для проверок. */
  label: string
  /** Готовый текст сообщения; умеет принимать только WhatsApp. */
  text?: string
  className?: string
  /** Куда раскрывать меню: в подвале — вверх, иначе уйдёт за край экрана. */
  direction?: 'down' | 'up'
  /** По центру кнопки или по её правому краю — для крайней кнопки в ряду. */
  align?: 'center' | 'end'
  children: ReactNode
}

// Меню не должно выходить за экран: в узком окне кнопка может стоять у
// самого края. Отступ от края, при котором его ещё сдвигаем.
const EDGE = 12

const ITEM =
  'flex items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-accent-50 focus-visible:bg-accent-50 focus-visible:outline-none'

export function MessengerLink({
  channel,
  label,
  text,
  className = '',
  direction = 'down',
  align = 'center',
  children,
}: Props) {
  const desktop = useDesktopPointer()
  const targets = MESSENGER_TARGETS[channel]
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLSpanElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const menuId = useId()

  // Сдвиг меню внутрь экрана, если в раскрытом виде оно за него выходит.
  // Меряем до отрисовки кадра, поэтому прыжка не видно.
  const [shift, setShift] = useState(0)
  useLayoutEffect(() => {
    if (!open || !menu.current) {
      setShift(0)
      return
    }
    const rect = menu.current.getBoundingClientRect()
    const width = document.documentElement.clientWidth
    let dx = 0
    if (rect.right > width - EDGE) dx = width - EDGE - rect.right
    if (rect.left + dx < EDGE) dx = EDGE - rect.left
    setShift(Math.round(dx))
  }, [open])

  // Нажатие мимо меню закрывает его. Слушаем документ, а не onBlur кнопки:
  // после клика по пункту фокус уходит на новую вкладку, и onBlur там не
  // всегда успевает.
  useEffect(() => {
    if (!open) return
    const onDown = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onDown)
    return () => document.removeEventListener('pointerdown', onDown)
  }, [open])

  if (!targets) {
    // Канал не настроен (плейсхолдер в contacts.ts) — к подвалу, где все каналы.
    return (
      <a href={LINKS[channel]} className={className} data-channel={label}>
        {children}
      </a>
    )
  }

  if (!desktop) {
    return (
      <a href={targets.universal(text)} className={className} data-channel={label}>
        {children}
      </a>
    )
  }

  if (!targets.web || !targets.app) {
    return (
      <a
        href={targets.universal(text)}
        target="_blank"
        rel="noopener noreferrer"
        className={className}
        data-channel={label}
      >
        {children}
      </a>
    )
  }

  // Фокус ушёл из меню целиком (Tab дальше) — закрываем.
  const onBlur = (event: FocusEvent<HTMLSpanElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false)
  }

  return (
    <span
      ref={root}
      className="relative inline-flex"
      onBlur={onBlur}
      onKeyDown={(event) => event.key === 'Escape' && setOpen(false)}
    >
      <button
        type="button"
        className={className}
        data-channel={label}
        data-chooser=""
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((value) => !value)}
      >
        {children}
      </button>

      {open && (
        <div
          ref={menu}
          id={menuId}
          role="menu"
          aria-label={`Как открыть ${label}`}
          className={`absolute z-50 w-64 animate-chooser ${align === 'end' ? 'right-0' : 'left-1/2'} ${
            direction === 'up' ? 'bottom-full pb-2' : 'top-full pt-2'
          }`}
          // Смещение к центру и сдвиг от края — одним transform: анимация
          // меняет только прозрачность и с ним не спорит.
          style={{ transform: `translateX(calc(${align === 'end' ? '0px' : '-50%'} + ${shift}px))` }}
        >
          <div className="rounded-2xl border border-neutral-200 bg-white p-1.5 text-neutral-900 shadow-card">
            <a
              role="menuitem"
              data-choice="web"
              href={targets.web(text)}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className={ITEM}
            >
              <Globe className="mt-0.5 h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block text-sm font-semibold">{label} Web</span>
                <span className="block text-xs text-neutral-500">Откроется в новой вкладке</span>
              </span>
            </a>
            <a
              role="menuitem"
              data-choice="app"
              href={targets.app(text)}
              onClick={() => setOpen(false)}
              className={ITEM}
            >
              <AppWindow className="mt-0.5 h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block text-sm font-semibold">Приложение {label}</span>
                <span className="block text-xs text-neutral-500">
                  Если оно установлено на компьютере
                </span>
              </span>
            </a>
          </div>
        </div>
      )}
    </span>
  )
}
