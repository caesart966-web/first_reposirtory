import { ArrowRight, Check, FileText, Scale } from 'lucide-react'
import { useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import type { SroDetail } from '../content/sroDetails'
import {
  DOCS_LAW,
  DOCS_SPECIALISTS,
  DOCS_IP,
  DOCS_OOO,
  FUNDS_CONFIRMED,
  LAW,
  STEPS,
} from '../content/sroDetails'
import { home, page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { Footer } from './Footer'
import { Header } from './Header'
import { Contact } from './Contact'
import { PageExtras } from './PageExtras'
import { PageHero } from './PageHero'
import { MobileBar } from './MobileBar'
import { Reveal } from './ui/Reveal'

// Ссылка на норму. Не украшение: на странице есть суммы и пороги, и каждый
// из них посетитель должен уметь проверить сам, не веря нам на слово.
//
// С 28.09.2026 — сноской, а не плашкой: серые плашки у каждого абзаца
// рябили сильнее самого текста, а на кремовом фоне разделов их фон
// и вовсе пропадал. Значок весов — латунью, номер статьи — мелким
// текстом, как ссылка на источник в документе.
export function Law({ children }: { children: string }) {
  return (
    <span className="mt-2 flex items-center gap-1.5 text-xs font-medium text-neutral-600">
      <Scale className="h-3.5 w-3.5 shrink-0 text-accent-500" aria-hidden="true" />
      {children}
    </span>
  )
}

// Шаг порядка вступления. Номер крупный и приглушённый, чтобы лента шагов
// читалась лентой, а не списком; исполнитель помечен отдельно — половину шагов
// делает не кандидат, и это стоит видеть сразу.
export function Step({
  index,
  step,
}: {
  index: number
  step: { title: string; detail: string; law?: string; who: 'кандидат' | 'СРО' | 'мы' }
}) {
  return (
    <>
      {/* Вертикаль между номерами: без неё шаги читаются отдельными
          карточками, а это одна последовательность. Последний линию не тянет. */}
      <span
        aria-hidden="true"
        className="absolute left-[19px] top-11 h-[calc(100%-2.75rem)] w-px bg-neutral-200 transition-colors duration-200 group-hover:bg-accent-200 group-last:hidden"
      />
      <span className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-accent-100 bg-accent-50 text-sm font-bold text-accent-700 transition-colors duration-200 group-hover:border-accent-600 group-hover:bg-accent-600 group-hover:text-white">
        {index + 1}
      </span>
      <div className="min-w-0 pt-1.5">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h3 className="font-semibold text-neutral-950 transition-colors duration-200 group-hover:text-accent-700">
            {step.title}
          </h3>
          <span className="rounded-md bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-600 transition-colors duration-200 group-hover:bg-accent-50 group-hover:text-accent-700">
            {step.who === 'мы' ? 'делаю я' : step.who === 'СРО' ? 'делает СРО' : 'от вас'}
          </span>
        </div>
        <p className="mt-2 text-sm leading-relaxed text-neutral-600">{step.detail}</p>
        {step.law && <Law>{step.law}</Law>}
      </div>
    </>
  )
}

export function DocGroup({
  title,
  hint,
  items,
  tone,
}: {
  title: string
  hint: string
  items: { title: string; detail: string; law?: string }[]
  tone: 'law' | 'sro'
}) {
  return (
    <div
      className={`h-full rounded-2xl border p-5 transition-colors duration-200 sm:p-6 ${
        tone === 'law'
          ? 'border-accent-100 bg-accent-50/40 hover:border-accent-300'
          : 'border-neutral-200 bg-white hover:border-accent-300'
      }`}
    >
      <h3 className="font-semibold text-neutral-950">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-neutral-600">{hint}</p>
      <ul className="mt-4 -mx-2 space-y-0.5">
        {items.map((item) => (
          /* Подсветка строки, а не подъём: список читается, а не кликается,
             и подъём обещал бы клик, которого нет (см. ui/card.ts). Отклик
             всё равно нужен — иначе на длинном перечне взгляд теряет строку. */
          <li
            key={item.title}
            className="group/doc flex gap-3 rounded-xl px-2 py-1.5 transition-colors duration-150 hover:bg-white/70"
          >
            <FileText
              className="mt-[3px] h-4 w-4 shrink-0 text-accent-600/70 transition-colors duration-150 group-hover/doc:text-accent-600"
              aria-hidden="true"
            />
            <div className="min-w-0 text-sm">
              <span className="font-medium text-neutral-900">{item.title}</span>
              {item.detail && (
                <span className="block leading-relaxed text-neutral-600">{item.detail}</span>
              )}
              {item.law && <Law>{item.law}</Law>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

// ─── Страница вида СРО ───────────────────────────────────────────────────
//
// Переделана 28.09.2026 дважды, по двум просьбам заказчика: сначала «чтобы
// информация была компактной и профессиональной» (рамки и карточки ушли,
// строки разделены линейкой), затем «информации куча, хотелось бы
// структурированно и понятно». Второе — про объём текста, а не про рамки,
// поэтому страница собрана заново вокруг того, что человек ищет глазами:
//
// 1. ключевые цифры сразу под шапкой — порог, специалисты, срок, взнос;
// 2. «Кому нужно членство» — таблица «ситуация → ответ» с меткой «Нужно /
//    Не нужно» вместо абзацев, из середины которых ответ приходилось
//    вычитывать;
// 3. шаги — одной строкой каждый;
// 4. документы — только названия, три колонки; что входит в каждый —
//    на странице услуги «Подготовка документов», ссылка там же;
// 5. фонды — две таблицы минимумов и одна строка оговорок.
// Каждая цифра по-прежнему со статьёй (Law): это главный довод сайта.
//
// Заголовки разделов — сверху, как на главной: под ними сетки в две-три
// колонки, которым левая рейка оставляла бы треть ширины.

// Заголовок раздела: слева заголовок, справа — одна строка пояснения.
// Кегль — по самому длинному слову заголовков страницы («Компенсационные»):
// на 320 px он обязан влезать (test-site.mjs, «заголовки не шире колонки»).
function Head({ title, lead }: { title: string; lead?: string }) {
  return (
    <Reveal className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] lg:items-end lg:gap-16">
      <h2 className="font-display text-[1.9rem] font-medium leading-[1.04] tracking-[-0.01em] text-neutral-950 min-[380px]:text-[2.2rem] sm:text-[2.7rem] lg:text-[3.1rem]">
        {nbsp(title)}
      </h2>
      {lead && <p className="text-[15px] leading-relaxed text-neutral-600 sm:text-base">{nbsp(lead)}</p>}
    </Reveal>
  )
}

function Part({ id, tint = false, children }: { id?: string; tint?: boolean; children: ReactNode }) {
  return (
    <section id={id} className={`py-14 sm:py-20 ${tint ? 'bg-neutral-100' : ''}`}>
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">{children}</div>
    </section>
  )
}

// Ключевые цифры: то, что человек ищет на такой странице первым. Кегль —
// по самому длинному значению («Без порога», «100 000 ₽») в плитке на 320
// и 1024 px, где она уже всего; стережёт test-site.mjs. Все четыре —
// из закона и со статьёй; четвёртая (взнос первого уровня) — только когда
// таблицы фондов сверены (FUNDS_CONFIRMED), иначе на её месте регион.
function KeyFacts({ detail }: { detail: SroDetail }) {
  const facts = [
    detail.threshold,
    {
      value: 'От 2',
      label: 'специалистов в НРС на основном месте работы',
      law: LAW.specialists,
    },
    {
      value: '2 месяца',
      label: 'предельный срок рассмотрения заявления',
      law: LAW.term,
    },
    FUNDS_CONFIRMED
      ? {
          value: detail.funds.harm.rows[0].amount,
          label: 'минимальный взнос в фонд возмещения вреда',
          law: LAW.funds,
        }
      : detail.regional
        ? {
            value: 'Свой регион',
            label: 'строитель вступает в СРО своего субъекта РФ',
            law: LAW.membership,
          }
        : {
            value: 'Любой регион',
            label: 'региональный принцип — только для строителей',
            law: LAW.membership,
          },
  ]
  return (
    <section aria-label="Коротко" className="border-b border-neutral-200 bg-neutral-100">
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <dl className="grid grid-cols-2 lg:grid-cols-4">
          {facts.map((fact, index) => (
            <Reveal
              key={fact.label}
              delay={index * 60}
              className={`flex flex-col-reverse justify-end gap-2 py-7 sm:py-9 lg:px-8 lg:first:pl-0 ${
                index % 2 ? 'border-l border-neutral-300 pl-4 sm:pl-6' : 'pr-4 sm:pr-6'
              } ${index > 1 ? 'border-t border-neutral-300 lg:border-t-0' : ''} ${index === 2 ? 'lg:border-l lg:border-neutral-300 lg:pl-8' : ''}`}
            >
              <dt className="text-sm leading-snug text-neutral-600">
                {nbsp(fact.label)}
                <Law>{fact.law}</Law>
              </dt>
              <dd className="whitespace-nowrap font-display text-[1.5rem] font-medium leading-none text-neutral-950 min-[380px]:text-[1.85rem] sm:text-[2.4rem] lg:text-[2.1rem] xl:text-[2.6rem]">
                {fact.value}
              </dd>
            </Reveal>
          ))}
        </dl>
        <div className="flex flex-wrap items-center gap-2 border-t border-neutral-300 py-5">
          <span className="mr-2 text-sm text-neutral-600">Виды работ</span>
          {detail.scope.map((item) => (
            <span
              key={item}
              className="rounded-full border border-neutral-300 bg-neutral-50 px-3.5 py-1.5 text-sm text-neutral-800"
            >
              {item}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

// Метка ответа в таблице «Кому нужно членство».
const TONE = {
  yes: 'bg-accent-950 text-neutral-50',
  no: 'border border-neutral-300 bg-neutral-50 text-neutral-800',
  note: 'bg-accent-100 text-accent-800',
} as const

type Case = SroDetail['cases'][number]

function Cases({ detail }: { detail: SroDetail }) {
  // Строка про регион — общая для трёх видов, различается только ответом.
  const rows: Case[] = [
    ...detail.cases,
    detail.regional
      ? {
          situation: 'В какую СРО вступать',
          answer: 'Только своего региона',
          tone: 'note',
          note: 'зарегистрированную в том же субъекте РФ, что и компания',
          law: LAW.membership,
        }
      : {
          situation: 'В какую СРО вступать',
          answer: 'Любого региона',
          tone: 'note',
          note: 'региональный принцип действует только для строителей',
          law: LAW.membership,
        },
  ]
  return (
    <ul className="mt-10 border-t border-neutral-300">
      {rows.map((row) => (
        <li
          key={row.situation}
          className="grid gap-x-10 gap-y-2.5 border-b border-neutral-200 py-5 sm:grid-cols-[minmax(0,1fr)_minmax(0,17rem)] sm:items-start lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]"
        >
          <div className="min-w-0">
            <p className="text-base font-medium leading-snug text-neutral-950">{nbsp(row.situation)}</p>
            <Law>{row.law}</Law>
          </div>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5 sm:flex-col sm:items-start">
            <span className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${TONE[row.tone]}`}>
              {row.answer}
            </span>
            {row.note && <span className="text-sm leading-snug text-neutral-600">{nbsp(row.note)}</span>}
          </div>
        </li>
      ))}
    </ul>
  )
}

// Перечень документов — только названия. Что входит в каждый документ,
// рассказано на странице услуги «Подготовка документов»: здесь человеку
// нужен объём комплекта, а не опись.
function DocColumn({
  title,
  hint,
  items,
  law,
}: {
  title: string
  hint: string
  items: { title: string }[]
  law?: string
}) {
  return (
    <div>
      {/* Строка заголовка той же высоты, что у колонки с переключателем
          ООО / ИП: иначе третий список начинался ниже двух соседних. */}
      <h3 className="flex min-h-11 items-center text-lg font-semibold leading-snug text-neutral-950">{title}</h3>
      <p className="mt-1 min-h-10 text-sm leading-snug text-neutral-600">{nbsp(hint)}</p>
      <ul className="mt-4 border-t border-neutral-300">
        {items.map((item) => (
          <li
            key={item.title}
            className="flex gap-3 border-b border-neutral-200 py-3 text-[15px] leading-snug text-neutral-900"
          >
            <Check className="mt-[3px] h-4 w-4 shrink-0 text-accent-500" aria-hidden="true" />
            <span className="min-w-0">{item.title}</span>
          </li>
        ))}
      </ul>
      {law && <Law>{law}</Law>}
    </div>
  )
}

// Что просит сама СРО — у ООО и у ИП списки разные, и человеку нужен один
// из двух. Переключатель вместо двух колонок рядом: второй список ему
// не нужен, а на телефоне он добавлял полэкрана. Кнопки, а не радиокнопки:
// полей ввода на сайте нет и быть не должно (test-site.mjs).
const FORMS = [
  { key: 'ooo', label: 'ООО', items: DOCS_OOO },
  { key: 'ip', label: 'ИП', items: DOCS_IP },
] as const

function SroDocs() {
  const [form, setForm] = useState<(typeof FORMS)[number]['key']>('ooo')
  const tabs = useRef<(HTMLButtonElement | null)[]>([])
  const current = FORMS.find((f) => f.key === form) ?? FORMS[0]
  // Стрелки влево-вправо переключают вкладку, как положено у tablist.
  const onKey = (event: KeyboardEvent, index: number) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    const next = (index + (event.key === 'ArrowRight' ? 1 : FORMS.length - 1)) % FORMS.length
    setForm(FORMS[next].key)
    tabs.current[next]?.focus()
  }
  return (
    <div>
      <div className="flex min-h-11 items-center justify-between gap-4">
        <h3 className="text-lg font-semibold leading-snug text-neutral-950">Запрашивает СРО</h3>
        <div
          role="tablist"
          aria-label="Форма организации"
          className="inline-flex shrink-0 rounded-full bg-neutral-200/80 p-1"
        >
          {FORMS.map((f, index) => {
            const on = f.key === form
            return (
              <button
                key={f.key}
                ref={(el) => {
                  tabs.current[index] = el
                }}
                type="button"
                role="tab"
                id={`docs-tab-${f.key}`}
                aria-selected={on}
                aria-controls="docs-panel"
                tabIndex={on ? 0 : -1}
                onClick={() => setForm(f.key)}
                onKeyDown={(event) => onKey(event, index)}
                className={`min-h-9 rounded-full px-4 text-sm font-medium transition-colors duration-300 ease-silk ${
                  on ? 'bg-white text-neutral-950 shadow-sm' : 'text-neutral-600 hover:text-neutral-950'
                }`}
              >
                {f.label}
              </button>
            )
          })}
        </div>
      </div>
      <p className="mt-1 min-h-10 text-sm leading-snug text-neutral-600">Обычный запрос сверх кодекса.</p>
      <ul
        id="docs-panel"
        role="tabpanel"
        aria-labelledby={`docs-tab-${current.key}`}
        className="mt-4 border-t border-neutral-300"
      >
        {current.items.map((item) => (
          <li
            key={item.title}
            className="flex gap-3 border-b border-neutral-200 py-3 text-[15px] leading-snug text-neutral-900"
          >
            <FileText className="mt-[3px] h-4 w-4 shrink-0 text-accent-500" aria-hidden="true" />
            <span className="min-w-0">{item.title}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

// Фонд: одна строка «кто платит и от чего зависит уровень» и таблица
// минимумов (если суммы сверены — FUNDS_CONFIRMED).
function Fund({
  title,
  text,
  // Шапка колонки задаётся снаружи, а не зашита: у фонда возмещения вреда
  // уровень считают по ОДНОМУ договору, у фонда договорных обязательств —
  // по СОВОКУПНОМУ размеру обязательств. Общая шапка «по одному договору»
  // делала вторую таблицу неверной.
  basis,
  rows,
  law,
}: {
  title: string
  text: string
  basis: string
  rows?: { limit: string; amount: string }[]
  law: string
}) {
  return (
    <div className="flex h-full flex-col">
      <h3 className="text-lg font-semibold leading-snug text-neutral-950">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-neutral-600">{nbsp(text)}</p>
      {rows && (
        <table className="mt-5 w-full border-collapse text-sm">
          <caption className="sr-only">{`${title}: минимальный взнос по уровням ответственности`}</caption>
          <thead>
            <tr className="border-b border-neutral-300 text-left align-bottom text-xs text-neutral-600">
              {/* Номер уровня — не украшение: в разговоре с СРО оперируют
                  именно им, и человек должен знать свой. */}
              <th scope="col" className="w-9 pb-2 font-medium">
                Ур.
              </th>
              <th scope="col" className="pb-2 pr-3 font-medium">
                {basis}
              </th>
              <th scope="col" className="pb-2 text-right font-medium">
                Взнос
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={row.limit} className="border-b border-neutral-200">
                <td className="py-2.5 tabular-nums text-neutral-500">{index + 1}</td>
                <td className="py-2.5 pr-3 text-neutral-700">{row.limit}</td>
                <td className="whitespace-nowrap py-2.5 text-right font-semibold tabular-nums text-neutral-950">
                  {row.amount}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="mt-auto pt-3">
        <Law>{law}</Law>
      </div>
    </div>
  )
}

const WHO_LABEL = {
  мы: 'делаю я',
  СРО: 'делает СРО',
  кандидат: 'от вас',
} as const

// Оглавление шапки и услуги по теме — одинаковые у трёх видов СРО: разделы
// у страниц видов общие, а подбор, документы и специалисты — три вопроса,
// которые у вступающего возникают следующими.
const DETAIL_TOC = [
  { id: 'komu', title: 'Кому нужно членство' },
  { id: 'poryadok', title: 'Порядок вступления' },
  { id: 'dokumenty', title: 'Документы' },
  { id: 'vznosy', title: 'Компенсационные фонды' },
  { id: 'stoimost', title: 'Сколько стоит' },
]
const DETAIL_RELATED = ['podbor', 'dokumenty', 'nrs']

export function DetailPage({ detail }: { detail: SroDetail }) {
  return (
    <div id="top">
      <Header />
      <main>
        {/* Первый экран: крошка на главную (там список трёх видов), заголовок,
            строка о том, что я делаю, и кадр своего вида. */}
        <PageHero
          backHref={home()}
          backLabel="Все виды СРО"
          title={detail.title}
          lead={detail.lead}
          image={detail.card.image}
          transitionName={`sro-${detail.slug}`}
          toc={DETAIL_TOC}
        />

        <KeyFacts detail={detail} />

        {/* Кому нужно членство — ситуация и ответ. Отвечать на «а мне точно
            надо» без ссылки на закон значило бы продавать, а не объяснять. */}
        <Part id="komu">
          <Head
            title="Кому нужно членство"
            lead="Решает не вид работ, а с кем заключён договор. Не уверены, какая строка про вас, — пришлите договор, проверю до подачи документов."
          />
          <Reveal>
            <Cases detail={detail} />
            {/* На каждой странице: «допуск СРО» до сих пор ищут в поиске,
                и пришедший за ним должен сразу понять, что искать другое. */}
            <p className="mt-6 max-w-3xl text-sm leading-relaxed text-neutral-600">
              <strong className="font-semibold text-neutral-950">Допусков СРО нет с 1 июля 2017 года.</strong>{' '}
              {nbsp(
                'Право выполнять работы подтверждает выписка из реестра членов СРО; предложения «купить допуск» закону не соответствуют.',
              )}
            </p>
            <Law>{LAW.noAdmission}</Law>
          </Reveal>
        </Part>

        {/* Шаги — одной строкой каждый. У каждого помечен исполнитель:
            половину делает не кандидат, и это видно сразу. */}
        <Part id="poryadok" tint>
          <Head
            title="Как проходит вступление"
            lead="Порядок установлен законом и одинаков для трёх видов СРО. Сроки — только законные: фактический срок назначает сама организация."
          />
          <ol className="mt-10 grid border-t border-neutral-300 sm:grid-cols-2 sm:gap-x-10 lg:grid-cols-3">
            {STEPS.map((step, index) => (
              <li key={step.title} className="border-b border-neutral-300 py-6">
                <Reveal delay={(index % 3) * 60}>
                  <div className="flex items-center justify-between gap-4">
                    <span className="font-display text-[2rem] font-medium leading-none tabular-nums text-accent-500">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                        step.who === 'мы'
                          ? 'bg-accent-950 text-neutral-50'
                          : 'border border-neutral-300 text-neutral-700'
                      }`}
                    >
                      {WHO_LABEL[step.who]}
                    </span>
                  </div>
                  <h3 className="mt-4 text-[17px] font-semibold leading-snug text-neutral-950">{nbsp(step.title)}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-neutral-600">{nbsp(step.detail)}</p>
                  {step.law && <Law>{step.law}</Law>}
                </Reveal>
              </li>
            ))}
          </ol>
        </Part>

        {/* Документы: закон и СРО — раздельно. У посредников списки слиты,
            и человек уверен, что договор аренды офиса требует кодекс. */}
        <Part id="dokumenty">
          <Head
            title="Документы"
            lead="Закон называет основу и отсылает к требованиям самой СРО, поэтому комплект всегда шире перечня в кодексе."
          />
          <Reveal className="mt-10 grid gap-10 md:grid-cols-2 lg:grid-cols-3 lg:gap-12">
            <DocColumn title="Требует закон" hint="Одинаково для любой СРО." items={DOCS_LAW} law={LAW.membership} />
            <DocColumn
              title="Специалисты в НРС"
              hint={`Не менее двух, на основном месте работы; специализация — ${detail.specialistsField}.`}
              items={DOCS_SPECIALISTS}
              law={LAW.specialists}
            />
            <SroDocs />
          </Reveal>
          <Reveal>
            <a
              href={page('uslugi/dokumenty')}
              className="group mt-8 inline-flex items-center gap-2 text-[15px] font-medium text-accent-700 transition-colors hover:text-accent-800"
            >
              Что входит в каждый документ
              <ArrowRight
                className="h-4 w-4 transition-transform duration-500 ease-silk group-hover:translate-x-1"
                aria-hidden="true"
              />
            </a>
          </Reveal>
        </Part>

        {/* Компенсационные фонды: суммы — установленные законом минимумы
            (ст. 55.16), сверены в сентябре 2026 (FUNDS_CONFIRMED). Пока флаг
            снят, таблиц нет, а объяснение фондов остаётся. */}
        <Part id="vznosy" tint>
          <Head
            title="Компенсационные фонды"
            lead={
              FUNDS_CONFIRMED
                ? 'Взносы в таблицах — минимумы по закону: СРО может установить больше, но не меньше.'
                : 'Размер взноса зависит от уровня ответственности; минимумы установлены законом.'
            }
          />
          <Reveal className="mt-10 grid gap-12 md:grid-cols-2">
            <Fund
              title="Фонд возмещения вреда"
              text="Платят все члены СРО. Уровень — по сумме обязательств по одному договору."
              basis="Обязательства по одному договору"
              rows={FUNDS_CONFIRMED ? detail.funds.harm.rows : undefined}
              law={detail.funds.harm.law}
            />
            <Fund
              title="Фонд обеспечения договорных обязательств"
              text="Только для конкурентных закупок. Уровень — по совокупной сумме таких договоров."
              basis="Совокупный размер обязательств"
              rows={FUNDS_CONFIRMED ? detail.funds.contract.rows : undefined}
              law={detail.funds.contract.law}
            />
          </Reveal>
          <Reveal>
            <p className="mt-10 max-w-3xl text-sm leading-relaxed text-neutral-600">
              {nbsp(
                'Вступительный и членские взносы устанавливает сама СРО — сумму по выбранной организации назову до оплаты. Взнос в компенсационный фонд нельзя платить в рассрочку или третьими лицами, освободить от него тоже нельзя.',
              )}
            </p>
            <Law>{LAW.funds}</Law>
          </Reveal>
        </Part>

        <PageExtras related={DETAIL_RELATED} />

        {/* Вместо квиза с выбранным видом — «Связаться» со строкой про этот
            вид. Название вида подставляем как есть: toLowerCase()
            превращал аббревиатуру в «сро строителей». */}
        <Contact
          lead={`Отвечу на вопросы по ${detail.card.title}, подберу организацию и назову порядок действий. Консультация бесплатная — и первая, и все следующие.`}
        />
      </main>
      <Footer />
      <div className="md:hidden" style={{ height: 'calc(4rem + env(safe-area-inset-bottom))' }} aria-hidden="true" />
      <MobileBar />
    </div>
  )
}
