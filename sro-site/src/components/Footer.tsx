import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { CONTACTS } from '../content/contacts'
import { REQUISITES, isPlaceholder } from '../content/facts'
import { MENU, SERVICES_GROUP, TYPES_GROUP, isGroup, navHref, type NavLink } from '../content/nav'
import { nbsp } from '../lib/typo'
import { ScalesMark } from './illustrations'

// Подвал с 24.09.2026.
//
// Колонки «Связаться» здесь больше нет: прямо над подвалом на каждой
// странице стоит раздел «Связаться» с тем же телефоном и мессенджерами, и
// второй раз подряд они были бы повтором. Ссылок на политику
// конфиденциальности тоже нет — квиз снят, сайт не собирает данные.
//
// Оговорка «Консультация бесплатная — и первая, и все следующие» тоже ушла
// в «Связаться»: прямо над подвалом она стояла бы дважды подряд.
//
// Подвал темнее раздела «Связаться» на ступень (neutral-950 против
// accent-950): два тёмных блока подряд читаются двумя, а не одним пятном.

// Реквизиты — подписанными парами, как в выписке. Плейсхолдеры не выводятся.
const LEGAL_ROWS = [
  { label: 'ИНН', value: REQUISITES.inn },
  { label: 'КПП', value: REQUISITES.kpp },
  { label: 'ОГРН', value: REQUISITES.ogrn },
].filter((row) => !isPlaceholder(row.value))

// Разделы главной без групп и без «Связаться» — он стоит прямо над подвалом.
const PAGE_SECTIONS = MENU.filter((item): item is NavLink => !isGroup(item) && item.href !== '#contacts')

// Группа ссылок. С 640 px — обычная колонка с подписью. На телефоне —
// строка, которая раскрывается по нажатию (29.09.2026): пятнадцать ссылок
// подряд занимали в подвале почти полтора экрана, и за ними терялись
// реквизиты. Подпись на телефоне — кнопка, на компьютере — просто текст:
// у колонки, которая всегда открыта, aria-expanded был бы неправдой.
// Ссылки при этом всегда в разметке — скрыты только стилем.
function Group({ id, title, items, columns = false }: { id: string; title: string; items: NavLink[]; columns?: boolean }) {
  const [open, setOpen] = useState(false)
  const listId = `footer-${id}`
  return (
    <div className="border-b border-white/10 sm:border-0">
      <h2 className="text-[0.8125rem] font-medium text-neutral-400">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={listId}
          onClick={() => setOpen((value) => !value)}
          className="flex min-h-14 w-full items-center justify-between gap-4 text-left text-[0.9375rem] text-neutral-100 sm:hidden"
        >
          {title}
          <ChevronDown
            className={`h-4 w-4 shrink-0 text-neutral-400 transition-transform duration-500 ease-silk ${open ? 'rotate-180' : ''}`}
            aria-hidden="true"
          />
        </button>
        <span className="hidden sm:block">{title}</span>
      </h2>
      <ul
        id={listId}
        className={`${open ? 'block' : 'hidden'} space-y-3 pb-6 text-[0.9375rem] text-neutral-200 sm:mt-5 sm:block sm:pb-0 sm:text-sm ${
          columns ? 'lg:grid lg:grid-flow-col lg:grid-rows-4 lg:gap-x-8 lg:gap-y-3 lg:space-y-0' : ''
        }`}
      >
        {items.map((item) => (
          <li key={item.href}>
            <a href={navHref(item)} className="transition-colors duration-500 hover:text-accent-200">
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

// Раскладка (29.09.2026): знак с одной строкой описания — отдельной строкой,
// как шапка бланка; под ним три группы ссылок. На компьютере семь услуг
// стоят в две колонки по четыре, и ни одна колонка не свисает ниже соседей;
// на телефоне — три раскрывающиеся строки. Описание под знаком — одна
// строка: перечень услуг стоит рядом, и повторять его словами незачем.
export function Footer() {
  return (
    <footer className="bg-neutral-950 text-neutral-300">
      {/* Запас снизу под полоску «домой» у iPhone: отступа-заглушки под
          нижней панелью больше нет, подвал идёт до самого края. */}
      <div className="mx-auto w-full max-w-6xl min-[1800px]:max-w-7xl px-4 pb-[calc(2.5rem+env(safe-area-inset-bottom))] pt-14 sm:px-6 sm:pt-16 lg:px-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:gap-10">
          <div className="flex items-center gap-3">
            <ScalesMark className="h-8 w-auto shrink-0 text-accent-300" />
            <span className="whitespace-nowrap font-display text-[1.25rem] font-medium leading-none text-neutral-50 min-[380px]:text-[1.45rem]">
              {CONTACTS.brand}
            </span>
          </div>
          <p className="max-w-xs text-sm leading-relaxed text-neutral-400 lg:max-w-none">
            Вступление в СРО строителей, проектировщиков и изыскателей.
          </p>
        </div>

        <nav
          aria-label="Разделы сайта"
          className="mt-10 border-t border-white/10 sm:grid sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.4fr)_minmax(0,0.8fr)] sm:gap-8 sm:border-0 lg:mt-12 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.6fr)_minmax(0,0.7fr)] lg:gap-10"
        >
          <Group id="types" title={TYPES_GROUP.label} items={TYPES_GROUP.items} />
          <Group id="services" title={SERVICES_GROUP.label} items={SERVICES_GROUP.items} columns />
          <Group id="sections" title="Разделы" items={PAGE_SECTIONS} />
        </nav>

        {/* Реквизиты строкой пар «ИНН 616…», как в шапке письма, и под ними
            копирайт с оговоркой. Разметка <dl> — реквизиты ищут именно в нём. */}
        <div className="mt-8 text-xs leading-relaxed text-neutral-400 sm:mt-14 sm:border-t sm:border-white/10 sm:pt-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-baseline lg:justify-between lg:gap-10">
            <dl className="flex flex-wrap gap-x-6 gap-y-1.5">
              {LEGAL_ROWS.map((row) => (
                <div key={row.label} className="flex gap-1.5">
                  <dt>{row.label}</dt>
                  <dd className="tabular-nums text-neutral-200">{row.value}</dd>
                </div>
              ))}
            </dl>
            <p>
              © {new Date().getFullYear()} {REQUISITES.legalName}
            </p>
          </div>
          <p className="mt-3 max-w-2xl">
            {nbsp('Информация на сайте носит справочный характер и не является публичной офертой (п. 2 ст. 437 ГК РФ).')}
          </p>
        </div>
      </div>
    </footer>
  )
}
