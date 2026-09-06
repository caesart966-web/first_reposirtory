import { Mail, Phone } from 'lucide-react'
import { CONFIGURED, CONTACTS, LINKS } from '../content/contacts'
import { REQUISITES, isPlaceholder } from '../content/facts'
import { MENU, SERVICES_GROUP, TYPES_GROUP, isGroup, navHref, type NavLink } from '../content/nav'
import { ScalesMark } from './illustrations'
import { useLegalDocs } from './LegalDocs'
import { MESSENGERS } from './messengers'

// Строки реквизитов; плейсхолдеры отфильтрованы, появятся сами с данными.
const REQUISITE_ROWS = [
  { label: 'Наименование', value: REQUISITES.legalName },
  { label: 'ИНН', value: REQUISITES.inn },
  { label: 'КПП', value: REQUISITES.kpp },
  { label: 'ОГРН', value: REQUISITES.ogrn },
  { label: 'Адрес', value: REQUISITES.address },
].filter((row) => !isPlaceholder(row.value))

// Разделы главной без групп и без «Контактов»: якорь на контакты ведёт на
// сам подвал, и внутри подвала это ссылка в никуда.
const PAGE_SECTIONS = MENU.filter((item): item is NavLink => !isGroup(item) && item.href !== '#contacts')

// Заголовок колонки — той же капителью с разрядкой, что подзаголовки групп
// в «Услугах»: подвал читается частью той же системы, а не набором списков.
function Heading({ children, className = '' }: { children: string; className?: string }) {
  return (
    <p className={`text-xs font-semibold uppercase tracking-[0.16em] text-neutral-600 ${className}`}>
      {children}
    </p>
  )
}

function LinkList({ items }: { items: NavLink[] }) {
  return (
    <ul className="mt-4 space-y-2.5 text-sm text-neutral-600">
      {items.map((item) => (
        <li key={item.href}>
          <a href={navHref(item)} className="transition hover:text-accent-700">
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
    // id="contacts" — на подвале, а не на секции: отдельной секции контактов
    // больше нет, но якорь на неё ведёт из меню и из запасных ссылок в
    // contacts.ts. Подвал и есть место, где собраны все способы связи.
    <footer id="contacts" className="border-t border-neutral-200 bg-neutral-50/55">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        {/* Четыре колонки одной высоты вместо одной длинной: когда появились
            страницы услуг, список «Разделы» вырос до четырнадцати строк и
            стоял столбом рядом с двумя короткими колонками. Теперь виды СРО,
            услуги и разделы главной — отдельные списки, а реквизиты ушли
            полосой вниз, где им и место. */}
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.25fr_0.85fr_1fr_1fr] lg:gap-12">
          <div>
            {/* Тот же знак, что в шапке: подвал — вторая точка, где страница
                называет себя, и называть себя дважды по-разному незачем. */}
            <div className="flex items-center gap-2.5">
              <ScalesMark className="h-[22px] w-auto shrink-0 text-accent-600" />
              <span className="flex flex-col leading-tight">
                <span className="font-bold text-neutral-950">{CONTACTS.brand}</span>
                {/* neutral-600, а не 500: под подвалом фоновая гравюра Фемиды,
                    и над её самой тёмной точкой контраст 500 падал до 4.39:1
                    при норме 4.5 — замерено на странице (проверка T26). */}
                <span className="text-xs text-neutral-600">{CONTACTS.role}</span>
              </span>
            </div>
            <p className="mt-4 max-w-xs text-sm text-neutral-600">
              Вступление в СРО строителей, проектировщиков и изыскателей. Подготовка документов,
              специалисты НРС, сопровождение.
            </p>
            {/* Формулировка «и первая, и все следующие» — условие заказчика:
                консультация бесплатна всегда, а не в первый разговор. Больше
                нигде дословно не повторяется, поэтому сказана здесь прямо. */}
            <p className="mt-3 text-sm font-medium text-accent-700">
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
              звонок, почта, мессенджеры. Мессенджеры строками, а не рядом
              плашек: в колонке шириной в четверть ряд из трёх плашек ломался
              на две строки, и «MAX» висел один. Подпись у каждого обязательна:
              значок без подписи опознаётся по силуэту, а MAX знаком не всем.
              Всё внутри одного <ul>: у проверок это единый список каналов. */}
          <div>
            {(CONFIGURED.phone || CONFIGURED.email || MESSENGERS.length > 0) && (
              <>
                <Heading>Связаться</Heading>
                <ul className="mt-4 space-y-3 text-sm text-neutral-600">
                  {CONFIGURED.phone && (
                    <li>
                      <a
                        href={LINKS.tel}
                        className="inline-flex items-center gap-2.5 transition hover:text-accent-700"
                      >
                        <Phone className="h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                        {/* Телефон крупнее остальных строк: из всех каналов он
                            самый быстрый, и глаз должен находить его первым. */}
                        <span className="text-lg font-semibold tracking-tight text-neutral-950">
                          {CONTACTS.phone}
                        </span>
                      </a>
                    </li>
                  )}
                  {CONFIGURED.email && (
                    <li>
                      <a
                        href={LINKS.mail}
                        className="inline-flex items-start gap-2.5 transition hover:text-accent-700"
                      >
                        <Mail className="mt-0.5 h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                        <span className="min-w-0 break-all">{CONTACTS.email}</span>
                      </a>
                    </li>
                  )}
                  {MESSENGERS.map((channel) => (
                    <li key={channel.label}>
                      <a
                        href={channel.href}
                        data-channel={channel.label}
                        className="inline-flex items-center gap-2.5 font-medium text-neutral-700 transition hover:text-accent-700"
                      >
                        <channel.icon className="h-4 w-4 shrink-0 text-accent-600" />
                        {channel.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </>
            )}

            <Heading className="mt-8">Документы</Heading>
            <ul className="mt-4 space-y-2.5 text-sm text-neutral-600">
              {/* Открывают типовые тексты под 152-ФЗ; оператор назван реквизитами */}
              <li>
                <button
                  type="button"
                  onClick={() => openLegal('privacy')}
                  className="text-left transition hover:text-accent-700"
                >
                  Политика конфиденциальности
                </button>
              </li>
              <li>
                <button
                  type="button"
                  onClick={() => openLegal('consent')}
                  className="text-left transition hover:text-accent-700"
                >
                  Согласие на обработку персональных данных
                </button>
              </li>
            </ul>
          </div>
        </div>

        {/* Реквизиты — полосой во всю ширину, отдельно от навигации: в подвале
            их ищут по привычке, и здесь они стоят рядом с юридическим именем
            в копирайте. Незаполненные строки (ОГРН) не показываются —
            квадратные скобки на сайте читаются как «сломано». */}
        <div className="mt-10 border-t border-neutral-200 pt-6">
          <Heading>Реквизиты</Heading>
          <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-1.5 text-sm">
            {REQUISITE_ROWS.map((row) => (
              <div key={row.label} className="flex gap-2">
                <dt className="shrink-0 text-neutral-600">{row.label}</dt>
                <dd className="text-neutral-800">{row.value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="mt-6 flex flex-col gap-2 border-t border-neutral-200 pt-6 text-sm text-neutral-600 sm:flex-row sm:items-center sm:justify-between">
          <p>
            {/* В копирайте — юридическое имя и ИНН, а не бренд: это то место
                на странице, где компания названа так, как в реестре. */}
            © {new Date().getFullYear()} {REQUISITES.legalName} · ИНН {REQUISITES.inn}
          </p>
          {/* Цен на странице нет, сроков тоже — оговорка про оферту это
              фиксирует, а не прикрывает. */}
          <p>Информация на сайте не является публичной офертой.</p>
        </div>
      </div>
    </footer>
  )
}
