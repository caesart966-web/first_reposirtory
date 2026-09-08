import { ArrowRight, ChevronDown, Menu, Phone, X } from 'lucide-react'
import { useEffect, useRef, useState, type FocusEvent } from 'react'
import { CONFIGURED, CONTACTS, LINKS } from '../content/contacts'
import { HEADER_NAV, MENU, isGroup, navHref, type NavGroup, type NavLink } from '../content/nav'
import { anchor, home } from '../lib/site'
import { ScalesMark } from './illustrations'
import { ButtonLink } from './ui/Button'

// Ссылка на текущую страницу вида СРО подсвечивается: посетитель видит,
// где он. На главной подсвечивать нечего — секции якорями не считаются.
const isHere = (link: NavLink) =>
  link.kind === 'page' && typeof window !== 'undefined' && window.location.pathname.includes(`/${link.href}/`)

// Выпадающее меню шапки.
//
// Мышью открывается наведением, касанием и клавиатурой — нажатием на кнопку;
// закрывается уходом курсора, Escape, уходом фокуса и нажатием мимо.
//
// Наведение считается только для мыши. Касание тоже порождает mouseenter,
// и меню открывалось бы от него, а следующий за ним click тут же закрывал —
// на планшете шире 1024px оно бы мигало и не открывалось. По той же причине
// щелчок мышью не переключает, а открывает: меню под курсором уже открыто
// наведением, и намерение щелчка — «открой», а не «закрой».
//
// Задержка закрытия 120 мс и «мостик» pt-3 между кнопкой и карточкой — одно
// лекарство от одной болезни: курсор по дороге к пункту на миг выходит за
// кнопку, и без них меню схлопывалось прямо под рукой.
function Dropdown({ group }: { group: NavGroup }) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const timer = useRef<number>()
  const pointer = useRef<string | null>(null)

  const show = () => {
    window.clearTimeout(timer.current)
    setOpen(true)
  }
  const hide = () => {
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setOpen(false), 120)
  }
  useEffect(() => () => window.clearTimeout(timer.current), [])

  // Нажатие мимо меню. iOS не переводит фокус на кнопку при касании, так
  // что на onBlur там рассчитывать нельзя — слушаем документ, пока открыто.
  useEffect(() => {
    if (!open) return
    const onDown = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onDown)
    return () => document.removeEventListener('pointerdown', onDown)
  }, [open])

  // Фокус ушёл из меню целиком (Tab дальше) — закрываем. Внутри меню фокус
  // гуляет свободно: relatedTarget тогда — наш же элемент.
  const onBlur = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false)
  }

  return (
    <div
      ref={root}
      className="relative"
      onPointerEnter={(event) => event.pointerType === 'mouse' && show()}
      onPointerLeave={(event) => event.pointerType === 'mouse' && hide()}
      onBlur={onBlur}
      onKeyDown={(event) => event.key === 'Escape' && setOpen(false)}
    >
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="true"
        onPointerDown={(event) => {
          pointer.current = event.pointerType
        }}
        onClick={() => {
          // Клавиатура (Enter, пробел) pointerdown не даёт — переключает.
          setOpen(pointer.current === 'mouse' ? true : (value) => !value)
          pointer.current = null
        }}
        className={`inline-flex items-center gap-1 text-sm font-medium transition-colors ${
          open ? 'text-neutral-950' : 'text-neutral-600 hover:text-neutral-950'
        }`}
      >
        {group.label}
        <ChevronDown
          className={`h-4 w-4 text-neutral-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {/* Пока закрыто — invisible, а не display:none: так остаётся анимация
          появления, а ссылки внутри всё равно не получают фокус и Tab их
          пропускает. */}
      <div
        className={`absolute left-1/2 top-full z-50 w-[22rem] -translate-x-1/2 pt-3 transition duration-150 ease-out ${
          open ? 'visible translate-y-0 opacity-100' : 'invisible -translate-y-1 opacity-0'
        }`}
      >
        {/* Пункт — не одна строка, а название с подсказкой: человек ещё не
            знает, «строители» он или «проектировщики», и три голых слова
            ему не помогают. Подсказка — область деятельности со страницы вида. */}
        <div className="rounded-2xl border border-neutral-200 bg-white p-2 shadow-card-hover">
          {group.items.map((item) => {
            const here = isHere(item)
            return (
              <a
                key={item.href}
                href={navHref(item)}
                aria-current={here ? 'page' : undefined}
                onClick={() => setOpen(false)}
                className={`group/item flex items-start gap-3 rounded-xl px-3 py-2.5 transition-colors ${
                  here ? 'bg-accent-50' : 'hover:bg-accent-50'
                }`}
              >
                <span
                  className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-accent-500 transition-transform group-hover/item:scale-125"
                  aria-hidden="true"
                />
                <span className="min-w-0 flex-1">
                  <span
                    className={`block text-sm font-semibold ${
                      here ? 'text-accent-800' : 'text-neutral-900 group-hover/item:text-accent-800'
                    }`}
                  >
                    {item.label}
                  </span>
                  {item.hint && (
                    <span className="mt-0.5 block text-xs leading-snug text-neutral-600">{item.hint}</span>
                  )}
                </span>
                <ArrowRight
                  className="mt-0.5 h-4 w-4 shrink-0 -translate-x-1 text-accent-500 opacity-0 transition group-hover/item:translate-x-0 group-hover/item:opacity-100"
                  aria-hidden="true"
                />
              </a>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export function Header() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={`sticky top-0 z-50 border-b backdrop-blur transition-colors duration-300 ${
        scrolled || open
          ? 'border-neutral-200/80 bg-white/95 shadow-sm shadow-neutral-900/[0.03]'
          : 'border-transparent bg-white/85'
      }`}
    >
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Знак aria-hidden: имя рядом уже озвучено, второй раз объяснять
            картинку скринридеру нечем. */}
        <a href={home()} className="flex items-center gap-2.5">
          <ScalesMark className="h-[22px] w-auto shrink-0 text-accent-600" />
          <span className="flex flex-col leading-tight">
            <span className="text-[15px] font-bold tracking-tight text-neutral-950">{CONTACTS.brand}</span>
            {/* neutral-600, а не 500: тёплая нейтральная шкала темнее прежней серой
                по цвету, но светлее по контрасту, и на 500 подпись давала
                4.46:1 при норме 4.5. Замерено на странице. */}
            <span className="text-xs text-neutral-600">{CONTACTS.role}</span>
          </span>
        </a>

        {/* gap-5 до xl: на 1024-1279 пять пунктов с двумя стрелками иначе
            не умещаются рядом с логотипом, телефоном и кнопкой. */}
        <nav className="hidden items-center gap-5 lg:flex xl:gap-7" aria-label="Основная навигация">
          {HEADER_NAV.map((item) =>
            isGroup(item) ? (
              <Dropdown key={item.label} group={item} />
            ) : (
              <a
                key={item.href}
                href={navHref(item)}
                className="text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-950"
              >
                {item.label}
              </a>
            ),
          )}
        </nav>

        <div className="hidden items-center gap-5 lg:flex">
          {/* Номер текстом только с xl. На 1024-1279 поля хватает ровно на
              иконку: логотип, меню и кнопка съедают почти всё. */}
          {CONFIGURED.phone && (
            <a
              href={LINKS.tel}
              aria-label={`Позвонить: ${CONTACTS.phone}`}
              className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-neutral-200 text-accent-600 transition hover:bg-neutral-50 xl:h-auto xl:w-auto xl:gap-2 xl:rounded-none xl:border-0 xl:text-sm xl:font-semibold xl:text-neutral-800 xl:hover:bg-transparent xl:hover:text-accent-700"
            >
              <Phone className="h-5 w-5 shrink-0 xl:h-4 xl:w-4 xl:text-accent-600" aria-hidden="true" />
              <span className="hidden xl:inline">{CONTACTS.phone}</span>
            </a>
          )}
          <ButtonLink href={anchor('#quiz')}>Оставить заявку</ButtonLink>
        </div>

        <div className="flex items-center gap-2 lg:hidden">
          {CONFIGURED.phone && (
            <a
              href={LINKS.tel}
              aria-label={`Позвонить: ${CONTACTS.phone}`}
              className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-neutral-200 text-accent-600 transition hover:bg-neutral-50"
            >
              <Phone className="h-5 w-5" aria-hidden="true" />
            </a>
          )}
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-neutral-200 text-neutral-700 transition hover:bg-neutral-50"
            aria-expanded={open}
            aria-controls={open ? 'mobile-menu' : undefined}
            aria-label={open ? 'Закрыть меню' : 'Открыть меню'}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <div id="mobile-menu" className="max-h-[calc(100dvh-4rem)] overflow-y-auto border-t border-neutral-200 bg-white lg:hidden">
          <nav className="mx-auto flex w-full max-w-6xl flex-col px-4 py-3 sm:px-6" aria-label="Мобильная навигация">
            {/* Группы в мобильном меню не сворачиваются: два лишних тапа ради
                трёх строк — плохой размен. Заголовок группы набран как
                подпись, пункты под ним с отступом. Всё меню, включая
                «Контакты»: с телефона иначе они доступны только через подвал. */}
            {MENU.map((item) =>
              isGroup(item) ? (
                <div key={item.label} className="py-1.5">
                  <p className="px-2 pb-1 pt-2 text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">
                    {item.label}
                  </p>
                  {item.items.map((link) => (
                    <a
                      key={link.href}
                      href={navHref(link)}
                      onClick={() => setOpen(false)}
                      className="flex items-start gap-3 rounded-xl px-2 py-2.5 transition hover:bg-neutral-50"
                    >
                      <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-accent-500" aria-hidden="true" />
                      <span className="min-w-0">
                        <span className="block text-base font-medium text-neutral-800">{link.label}</span>
                        {link.hint && <span className="block text-sm text-neutral-600">{link.hint}</span>}
                      </span>
                    </a>
                  ))}
                </div>
              ) : (
                <a
                  key={item.href}
                  href={navHref(item)}
                  onClick={() => setOpen(false)}
                  className="rounded-xl px-2 py-3 text-base font-medium text-neutral-700 transition hover:bg-neutral-50 hover:text-neutral-950"
                >
                  {item.label}
                </a>
              ),
            )}
            <ButtonLink href={anchor('#quiz')} onClick={() => setOpen(false)} className="mb-2 mt-3 w-full">
              Оставить заявку
            </ButtonLink>
          </nav>
        </div>
      )}
    </header>
  )
}
