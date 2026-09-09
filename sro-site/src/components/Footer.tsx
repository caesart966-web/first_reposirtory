import { Mail, MapPin, Phone } from 'lucide-react'
import { CONFIGURED, CONTACTS, LINKS } from '../content/contacts'
import { REQUISITES, isPlaceholder } from '../content/facts'
import { MENU, SERVICES_GROUP, TYPES_GROUP, isGroup, navHref, type NavLink } from '../content/nav'
import { ScalesMark } from './illustrations'
import { useLegalDocs } from './LegalDocs'
import { MESSENGERS } from './messengers'
import { MessengerLink } from './MessengerLink'

// Юридическая строка внизу: имя, ИНН, КПП, ОГРН (когда назовут). Без
// заголовка «Реквизиты» — заказчик попросил убрать слово; строка и так
// читается как реквизиты по содержанию. Адрес отдельной строкой со значком.
const LEGAL_ROWS = [
  { label: 'ИНН', value: REQUISITES.inn },
  { label: 'КПП', value: REQUISITES.kpp },
  { label: 'ОГРН', value: REQUISITES.ogrn },
].filter((row) => !isPlaceholder(row.value))

// Разделы главной без групп и без «Контактов»: якорь на контакты ведёт на
// сам подвал, и внутри подвала это ссылка в никуда.
const PAGE_SECTIONS = MENU.filter((item): item is NavLink => !isGroup(item) && item.href !== '#contacts')

// Заголовок колонки — той же капителью с разрядкой, что подзаголовки групп
// в «Услугах»: подвал читается частью той же системы, а не набором списков.
function Heading({ children, className = '' }: { children: string; className?: string }) {
  return (
    <p className={`text-xs font-semibold uppercase tracking-[0.16em] text-accent-200 ${className}`}>
      {children}
    </p>
  )
}

// Подпись в нижней полосе. Та же капитель, что у заголовков колонок выше,
// но тише цветом: полоса под чертой — служебная, она не должна спорить с
// навигацией. Один стиль на метки реквизитов и на заголовок документов —
// поэтому три реквизита и колонка документов читаются одним рядом, а не
// двумя разными блоками, случайно оказавшимися рядом.
//
// Цвет neutral-400, а не более тихий neutral-500: на тёмном фоне подвала
// пятисотый даёт 3.66:1 при норме 4.5:1, и набор t23-27 это ловит. Мелкая
// капитель под исключение для крупного текста не подпадает — оно начинается
// с 24px, а здесь 11px.
function BarLabel({ children }: { children: string }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {children}
    </p>
  )
}

function LinkList({ items }: { items: NavLink[] }) {
  return (
    <ul className="mt-4 space-y-2.5 text-sm text-neutral-300">
      {items.map((item) => (
        <li key={item.href}>
          <a href={navHref(item)} className="transition hover:text-white">
            {item.label}
          </a>
        </li>
      ))}
    </ul>
  )
}

export function Footer() {
  const openLegal = useLegalDocs()

  return (
    // Тёмный, в цвет блока заявки: страница закрывается плотной полосой,
    // а не растворяется в подложке. Заодно снимается вопрос контраста над
    // гравюрой Фемиды — подвал непрозрачный.
    //
    // id="contacts" — на подвале: отдельной секции контактов нет, якорь на
    // неё ведёт из меню и из запасных ссылок в contacts.ts.
    <footer id="contacts" className="bg-accent-950 text-neutral-300">
      <div className="mx-auto w-full max-w-6xl px-4 pb-8 pt-14 sm:px-6 lg:px-8">
        {/* Четвёртой колонке ширины больше остальных: ряд из трёх плашек
            мессенджеров занимает ~330px, и на 1.05fr он ломался на две строки. */}
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.15fr_0.8fr_0.95fr_1.3fr] lg:gap-10">
          <div>
            {/* Тот же знак, что в шапке: подвал — вторая точка, где страница
                называет себя, и называть себя дважды по-разному незачем. */}
            <div className="flex items-center gap-2.5">
              <ScalesMark className="h-[24px] w-auto shrink-0 text-accent-300" />
              <span className="flex flex-col leading-tight">
                <span className="font-bold text-white">{CONTACTS.brand}</span>
                <span className="text-xs text-neutral-400">{CONTACTS.role}</span>
              </span>
            </div>
            <p className="mt-5 max-w-xs text-sm leading-relaxed text-neutral-300">
              Вступление в СРО строителей, проектировщиков и изыскателей. Подготовка документов,
              специалисты НРС, сопровождение.
            </p>
            {/* Формулировка «и первая, и все следующие» — условие заказчика:
                консультация бесплатна всегда, а не в первый разговор. */}
            <p className="mt-4 text-sm font-medium text-accent-200">
              Консультация бесплатная — и первая, и все следующие
            </p>
          </div>

          <div>
            <Heading>{TYPES_GROUP.label}</Heading>
            <LinkList items={TYPES_GROUP.items} />
            <Heading className="mt-8">Разделы</Heading>
            <LinkList items={PAGE_SECTIONS} />
          </div>

          <div>
            <Heading>{SERVICES_GROUP.label}</Heading>
            <LinkList items={SERVICES_GROUP.items} />
          </div>

          {/* Единственное место на странице, где собраны все способы связи.
              Сверху вниз — от самого прямого канала к самому отложенному:
              звонок, почта, мессенджеры плашками, адрес. Подпись у каждого
              мессенджера обязательна: MAX по значку знаком не всем.
              Всё внутри одного <ul>: у проверок это единый список каналов. */}
          {(CONFIGURED.phone || CONFIGURED.email || MESSENGERS.length > 0) && (
            <div>
              <Heading>Связаться</Heading>
              <ul className="mt-4 space-y-3.5 text-sm">
                {CONFIGURED.phone && (
                  <li>
                    <a
                      href={LINKS.tel}
                      className="inline-flex items-center gap-2.5 text-white transition hover:text-accent-200"
                    >
                      <Phone className="h-4 w-4 shrink-0 text-accent-300" aria-hidden="true" />
                      {/* Телефон крупнее остальных строк: из всех каналов он
                          самый быстрый, и глаз должен находить его первым. */}
                      <span className="text-xl font-semibold tracking-tight">{CONTACTS.phone}</span>
                    </a>
                  </li>
                )}
                {CONFIGURED.email && (
                  <li>
                    <a
                      href={LINKS.mail}
                      className="inline-flex items-start gap-2.5 text-neutral-300 transition hover:text-white"
                    >
                      <Mail className="mt-0.5 h-4 w-4 shrink-0 text-accent-300" aria-hidden="true" />
                      <span className="min-w-0 break-all">{CONTACTS.email}</span>
                    </a>
                  </li>
                )}
                {MESSENGERS.length > 0 && (
                  <li className="flex flex-wrap gap-1.5 pt-1">
                    {/* На компьютере откроется в новой вкладке, на телефоне —
                        сразу приложение; см. MessengerLink. */}
                    {MESSENGERS.map((channel) => (
                      <MessengerLink
                        key={channel.label}
                        channel={channel.id}
                        label={channel.label}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/5 px-2.5 py-1.5 text-[13px] font-medium text-white transition hover:border-accent-300 hover:bg-white/10"
                      >
                        <channel.icon className="h-4 w-4 shrink-0 text-accent-300" />
                        {channel.label}
                      </MessengerLink>
                    ))}
                  </li>
                )}
                <li className="flex items-start gap-2.5 pt-1 text-neutral-300">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-accent-300" aria-hidden="true" />
                  <span>{REQUISITES.address}</span>
                </li>
              </ul>
            </div>
          )}
        </div>

        {/* Нижняя полоса. Реквизиты — подписанными парами, как в выписке:
            метка капителью, значение под ней. Раньше они шли одной строкой
            через пробелы, и три числа подряд читались сплошной лентой, в
            которой не найти нужное.

            Заголовка «Реквизиты» нет намеренно — заказчик попросил убрать
            слово; подписи ИНН, КПП и ОГРН называют содержимое сами.

            Имя компании здесь одно, в копирайте. Прежде оно стояло дважды —
            и над реквизитами, и в копирайте строкой ниже, — из-за чего
            полоса выглядела как два обрывка одного и того же. */}
        <div className="mt-14 border-t border-white/10 pt-8">
          <div className="flex flex-col gap-8 lg:flex-row lg:justify-between lg:gap-12">
            <dl className="flex flex-wrap gap-x-8 gap-y-5 sm:gap-x-12">
              {LEGAL_ROWS.map((row) => (
                <div key={row.label}>
                  <dt>
                    <BarLabel>{row.label}</BarLabel>
                  </dt>
                  <dd className="mt-1.5 text-sm tabular-nums text-neutral-100">{row.value}</dd>
                </div>
              ))}
            </dl>

            {/* Открывают типовые тексты под 152-ФЗ; оператор назван реквизитами */}
            <div className="lg:text-right">
              <BarLabel>Документы</BarLabel>
              <ul className="mt-1.5 space-y-1.5 text-sm text-neutral-300">
                <li>
                  <button
                    type="button"
                    onClick={() => openLegal('privacy')}
                    className="text-left underline-offset-4 transition hover:text-white hover:underline"
                  >
                    Политика конфиденциальности
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={() => openLegal('consent')}
                    className="text-left underline-offset-4 transition hover:text-white hover:underline"
                  >
                    Согласие на обработку персональных данных
                  </button>
                </li>
              </ul>
            </div>
          </div>

          {/* Копирайт с оговоркой про оферту — самая тихая строка страницы:
              её читают, только когда ищут специально. */}
          <p className="mt-8 border-t border-white/5 pt-6 text-xs text-neutral-400">
            © {new Date().getFullYear()} {REQUISITES.legalName}. Информация на сайте не является
            публичной офертой.
          </p>
        </div>
      </div>
    </footer>
  )
}
