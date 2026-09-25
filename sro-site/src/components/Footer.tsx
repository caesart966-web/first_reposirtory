import { CONTACTS } from '../content/contacts'
import { REQUISITES, isPlaceholder } from '../content/facts'
import { MENU, SERVICES_GROUP, TYPES_GROUP, isGroup, navHref, type NavLink } from '../content/nav'
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

function Heading({ children }: { children: string }) {
  return <p className="text-sm text-neutral-400">{children}</p>
}

function LinkList({ items }: { items: NavLink[] }) {
  return (
    <ul className="mt-5 space-y-3 text-[15px] text-neutral-200">
      {items.map((item) => (
        <li key={item.href}>
          <a href={navHref(item)} className="transition-colors duration-500 hover:text-accent-200">
            {item.label}
          </a>
        </li>
      ))}
    </ul>
  )
}

export function Footer() {
  return (
    <footer className="bg-neutral-950 text-neutral-300">
      <div className="mx-auto w-full max-w-6xl px-4 pb-10 pt-16 sm:px-6 lg:px-8">
        <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-[1.3fr_0.9fr_1fr_0.8fr] lg:gap-10">
          <div>
            <div className="flex items-center gap-3">
              <ScalesMark className="h-8 w-auto shrink-0 text-accent-300" />
              <span className="font-display text-[1.45rem] font-medium leading-none text-neutral-50">
                {CONTACTS.brand}
              </span>
            </div>
            <p className="mt-5 max-w-xs text-sm leading-relaxed text-neutral-400">
              Вступление в СРО строителей, проектировщиков и изыскателей. Подготовка документов,
              специалисты НРС, сопровождение.
            </p>
          </div>

          <div>
            <Heading>{TYPES_GROUP.label}</Heading>
            <LinkList items={TYPES_GROUP.items} />
          </div>

          <div>
            <Heading>{SERVICES_GROUP.label}</Heading>
            <LinkList items={SERVICES_GROUP.items} />
          </div>

          <div>
            <Heading>Разделы</Heading>
            <LinkList items={PAGE_SECTIONS} />
          </div>
        </div>

        {/* Реквизиты и копирайт. Разметка <dl> — проверки ищут реквизиты
            именно в нём. */}
        <div className="mt-16 flex flex-col gap-8 border-t border-white/10 pt-8 lg:flex-row lg:items-end lg:justify-between">
          <dl className="flex flex-wrap gap-x-10 gap-y-5">
            {LEGAL_ROWS.map((row) => (
              <div key={row.label}>
                <dt className="text-xs text-neutral-400">{row.label}</dt>
                <dd className="mt-1 text-sm tabular-nums text-neutral-200">{row.value}</dd>
              </div>
            ))}
          </dl>
          <p className="max-w-md text-xs leading-relaxed text-neutral-400 lg:text-right">
            © {new Date().getFullYear()} {REQUISITES.legalName}. Информация на сайте носит
            справочный характер и не является публичной офертой (п. 2 ст. 437 ГК РФ).
          </p>
        </div>
      </div>
    </footer>
  )
}
