import { Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { CONTACTS } from '../content/contacts'
import { ButtonLink } from './ui/Button'

const NAV = [
  { href: '#services', label: 'Услуги' },
  { href: '#process', label: 'Как работаем' },
  { href: '#about', label: 'О специалисте' },
  { href: '#faq', label: 'FAQ' },
  { href: '#contacts', label: 'Контакты' },
]

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
        <a href="#top" className="flex flex-col leading-tight">
          <span className="text-[15px] font-bold tracking-tight text-neutral-950">
            {CONTACTS.fullName}
          </span>
          <span className="text-xs text-neutral-500">{CONTACTS.role}</span>
        </a>

        <nav className="hidden items-center gap-7 lg:flex" aria-label="Основная навигация">
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-950"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="hidden lg:block">
          <ButtonLink href="#quiz">Оставить заявку</ButtonLink>
        </div>

        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-neutral-200 text-neutral-700 transition hover:bg-neutral-50 lg:hidden"
          aria-expanded={open}
          aria-controls={open ? 'mobile-menu' : undefined}
          aria-label={open ? 'Закрыть меню' : 'Открыть меню'}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div id="mobile-menu" className="border-t border-neutral-200 bg-white lg:hidden">
          <nav
            className="mx-auto flex w-full max-w-6xl flex-col px-4 py-3 sm:px-6"
            aria-label="Мобильная навигация"
          >
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="rounded-xl px-2 py-3 text-base font-medium text-neutral-700 transition hover:bg-neutral-50 hover:text-neutral-950"
              >
                {item.label}
              </a>
            ))}
            <ButtonLink href="#quiz" onClick={() => setOpen(false)} className="mt-2 w-full">
              Оставить заявку
            </ButtonLink>
          </nav>
        </div>
      )}
    </header>
  )
}
