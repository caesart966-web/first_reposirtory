import { FileText, Scale } from 'lucide-react'
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
import { home } from '../lib/site'
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

// Фонд: что это, кто платит и — если суммы сверены — таблица минимумов.
// Раньше объяснение и таблица стояли в разных карточках, и подпись таблицы
// («уровень зависит от…») повторяла карточку над ней.
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
      <p className="mt-2 text-[15px] leading-relaxed text-neutral-600">{nbsp(text)}</p>
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

// Раздел страницы вида. На компьютере заголовок стоит слева и едет вместе
// с разделом (sticky), содержимое — справа; на телефоне заголовок над ним.
//
// Так страница стала вдвое короче (28.09.2026, просьба заказчика: «чтобы
// информация была компактной и профессиональной»): раньше заголовок занимал
// свою строку во всю ширину, а под ним карточки в рамках — пять рамок с
// галочками в «Кому обязательно», четыре в «Документах», отдельные карточки
// для объяснения фондов и для их таблиц. Теперь рамок нет вовсе, строки
// разделены тонкой линейкой, как в справочнике или спецификации.
function Part({
  id,
  title,
  intro,
  tint = false,
  children,
}: {
  id?: string
  title: string
  intro?: string
  tint?: boolean
  children: ReactNode
}) {
  return (
    <section id={id} className={`py-14 sm:py-20 ${tint ? 'bg-neutral-100' : ''}`}>
      <div className="mx-auto grid w-full max-w-6xl grid-cols-[minmax(0,1fr)] gap-7 px-4 sm:px-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,9fr)] lg:gap-16 lg:px-8">
        <Reveal className="lg:sticky lg:top-24 lg:self-start">
          {/* Кегль и ширина колонки — по самой длинной неразрывной группе,
              «в компенсационные» (предлог приклеен неразрывным пробелом):
              на 2,6rem в трети ширины она вылезала на содержимое справа.
              Стережёт test-site.mjs («заголовки не шире своей колонки»). */}
          <h2 className="font-display text-[1.75rem] font-medium leading-[1.05] min-[380px]:text-[2rem] tracking-[-0.01em] text-neutral-950 sm:text-[2.5rem] lg:text-[1.95rem] xl:text-[2.2rem]">
            {nbsp(title)}
          </h2>
          {intro && <p className="mt-4 text-[15px] leading-relaxed text-neutral-600">{nbsp(intro)}</p>}
        </Reveal>
        <Reveal delay={80} className="min-w-0">
          {children}
        </Reveal>
      </div>
    </section>
  )
}

// Строка перечня: суть слева, подробности справа (с 640 px), на телефоне —
// одна под другой.
function Row({ title, children }: { title: string; children: ReactNode }) {
  return (
    <li className="grid gap-1.5 py-4 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)] sm:gap-8">
      <h3 className="font-semibold leading-snug text-neutral-950">{nbsp(title)}</h3>
      <div className="min-w-0">{children}</div>
    </li>
  )
}

// Перечень документов: название, пояснение, норма. Без значков и рамок.
function DocList({ title, hint, items }: { title: string; hint: string; items: { title: string; detail: string; law?: string }[] }) {
  return (
    <div>
      <h3 className="text-lg font-semibold leading-snug text-neutral-950">{nbsp(title)}</h3>
      <p className="mt-1 text-sm text-neutral-600">{nbsp(hint)}</p>
      <ul className="mt-4 divide-y divide-neutral-200 border-y border-neutral-200">
        {items.map((item) => (
          <li key={item.title} className="py-3.5">
            <span className="block text-[15px] font-medium leading-snug text-neutral-900">{item.title}</span>
            {item.detail && (
              <span className="mt-1 block text-sm leading-relaxed text-neutral-600">{nbsp(item.detail)}</span>
            )}
            {item.law && <Law>{item.law}</Law>}
          </li>
        ))}
      </ul>
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
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
        <h3 className="text-lg font-semibold leading-snug text-neutral-950">Запрашивает СРО</h3>
        <div role="tablist" aria-label="Форма организации" className="inline-flex rounded-full bg-neutral-200/80 p-1">
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
                className={`min-h-9 rounded-full px-5 text-sm font-medium transition-colors duration-300 ease-silk ${
                  on ? 'bg-white text-neutral-950 shadow-sm' : 'text-neutral-600 hover:text-neutral-950'
                }`}
              >
                {f.label}
              </button>
            )
          })}
        </div>
      </div>
      <p className="mt-1 text-sm text-neutral-600">Обычный запрос организации сверх того, что требует кодекс.</p>
      <ul
        id="docs-panel"
        role="tabpanel"
        aria-labelledby={`docs-tab-${current.key}`}
        className="mt-4 grid border-t border-neutral-200 sm:grid-cols-2 sm:gap-x-10"
      >
        {current.items.map((item) => (
          <li key={item.title} className="flex gap-3 border-b border-neutral-200 py-3">
            <FileText className="mt-[3px] h-4 w-4 shrink-0 text-accent-500" aria-hidden="true" />
            <span className="min-w-0 text-[15px] leading-snug text-neutral-900">
              {item.title}
              {item.detail && <span className="mt-0.5 block text-sm text-neutral-600">{nbsp(item.detail)}</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

const WHO_LABEL = { мы: 'делаю я', СРО: 'делает СРО', кандидат: 'от вас' } as const

// Оглавление шапки и услуги по теме — одинаковые у трёх видов СРО: разделы
// у страниц видов общие, а подбор, документы и специалисты — три вопроса,
// которые у вступающего возникают следующими.
const DETAIL_TOC = [
  { id: 'komu', title: 'Кому нужно членство' },
  { id: 'oblast', title: 'Область деятельности' },
  { id: 'poryadok', title: 'Как проходит вступление' },
  { id: 'dokumenty', title: 'Документы' },
  { id: 'vznosy', title: 'Взносы в фонды' },
  { id: 'stoimost', title: 'Сколько стоит' },
]
const DETAIL_RELATED = ['podbor', 'dokumenty', 'nrs']

export function DetailPage({ detail }: { detail: SroDetail }) {
  return (
    <div id="top">
          <Header />
          <main>
            {/* Первый экран: крошка на главную (там список трёх видов), заголовок,
                короткая строка и кадр своего вида. */}
            <PageHero
              backHref={home()}
              backLabel="Все виды СРО"
              title={detail.title}
              lead={detail.lead}
              image={detail.card.image}
              transitionName={`sro-${detail.slug}`}
              toc={DETAIL_TOC}
            />

            {/* Кому нужно членство. Каждый пункт — с нормой: это ответ
                на вопрос «а мне точно надо», и отвечать на него без ссылки
                на закон значило бы продавать, а не объяснять. Региональный
                принцип — последней строкой здесь же: он тоже про то, куда
                вступать, а раньше стоял отдельной карточкой в конце страницы. */}
            <Part id="komu" title="Кому нужно членство">
              <ul className="divide-y divide-neutral-200 border-y border-neutral-200">
                {detail.who.map((item) => (
                  <Row key={item.text} title={item.title}>
                    <p className="text-[15px] leading-relaxed text-neutral-700">{nbsp(item.text)}</p>
                    <Law>{item.law}</Law>
                  </Row>
                ))}
                <Row title={detail.regional ? 'Только СРО своего региона' : 'СРО в любом регионе'}>
                  <p className="text-[15px] leading-relaxed text-neutral-700">
                    {nbsp(
                      detail.regional
                        ? 'Строительная компания или предприниматель вступает только в ту СРО, которая зарегистрирована в том же субъекте Российской Федерации, где зарегистрирована сама компания.'
                        : 'Региональный принцип действует только для строителей. Проектировщики и изыскатели выбирают СРО в любом регионе.',
                    )}
                  </p>
                  <Law>{LAW.membership}</Law>
                </Row>
              </ul>
              {/* Отдельной строкой и на каждой странице: «допуск СРО» до сих
                  пор ищут в поиске, и человек, пришедший за ним, должен
                  сразу понять, что искать нужно другое. */}
              <div className="mt-8 border-l-2 border-accent-400 pl-5 text-[15px] leading-relaxed text-neutral-700">
                <strong className="font-semibold text-neutral-950">
                  Свидетельств о допуске СРО не существует с 1 июля 2017 года.
                </strong>{' '}
                {nbsp(
                  'Право выполнять работы подтверждается членством в саморегулируемой организации и выпиской из реестра её членов. Предложения «купить допуск» не соответствуют действующему законодательству.',
                )}
                <Law>{LAW.noAdmission}</Law>
              </div>
            </Part>

            {/* Область деятельности: что именно закрывает этот вид СРО.
                Узкой полосой: это перечень из двух–пяти слов, а не раздел. */}
            <section id="oblast" className="bg-neutral-100 py-10 sm:py-14">
              <div className="mx-auto grid w-full max-w-6xl grid-cols-[minmax(0,1fr)] gap-5 px-4 sm:px-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,9fr)] lg:items-center lg:gap-16 lg:px-8">
                <h2 className="font-display text-[1.6rem] font-medium leading-tight text-neutral-950 sm:text-[1.9rem]">
                  Область деятельности
                </h2>
                <ul className="flex flex-wrap gap-2">
                  {detail.scope.map((item) => (
                    <li
                      key={item}
                      className="rounded-full border border-neutral-300 bg-neutral-50 px-4 py-2 text-sm font-medium text-neutral-800"
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            {/* ШАГИ — то, ради чего человек и открыл страницу: что будет
                происходить и что от него потребуется. У каждого шага помечен
                исполнитель: половину делает не кандидат, и это видно сразу.
                Две колонки вместо вертикальной ленты: шесть шагов ложатся
                в три строки, а номер по-прежнему задаёт порядок чтения. */}
            <Part
              id="poryadok"
              title="Как проходит вступление"
              intro="Порядок установлен законом и одинаков для всех трёх видов СРО. Сроки указаны только те, что установлены законом; фактический срок рассмотрения определяет сама организация."
            >
              <ol className="grid border-t border-neutral-200 sm:grid-cols-2 sm:gap-x-10">
                {STEPS.map((step, index) => (
                  <li key={step.title} className="border-b border-neutral-200 py-6">
                    <div className="flex items-center justify-between gap-4">
                      <span className="font-display text-[2rem] font-medium leading-none text-accent-500 tabular-nums">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                          step.who === 'мы' ? 'bg-accent-50 text-accent-700' : 'bg-neutral-100 text-neutral-600'
                        }`}
                      >
                        {WHO_LABEL[step.who]}
                      </span>
                    </div>
                    <h3 className="mt-4 font-semibold leading-snug text-neutral-950">{nbsp(step.title)}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-neutral-600">{nbsp(step.detail)}</p>
                    {step.law && <Law>{step.law}</Law>}
                  </li>
                ))}
              </ol>
            </Part>

            {/* ДОКУМЕНТЫ. Закон и СРО — раздельно: у посредников списки слиты,
                и человек уверен, что договор аренды офиса требует кодекс. */}
            <Part
              id="dokumenty"
              title="Какие документы понадобятся"
              intro="Закон отсылает к внутренним требованиям самой СРО, поэтому фактический комплект всегда шире установленного кодексом. Ниже оба перечня."
              tint
            >
              <div className="grid gap-10 md:grid-cols-2">
                <DocList title="Требует закон" hint="Одинаково для любой СРО." items={DOCS_LAW} />
                <DocList
                  title="Специалисты в НРС"
                  hint={`Не менее двух, по основному месту работы; специализация — ${detail.specialistsField}.`}
                  items={DOCS_SPECIALISTS}
                />
              </div>
              <div className="mt-12">
                <SroDocs />
              </div>
            </Part>

            {/* ВЗНОСЫ. Суммы — установленные законом минимумы (ст. 55.16),
                сверены в сентябре 2026 (см. FUNDS_CONFIRMED в sroDetails.ts).
                Пока FUNDS_CONFIRMED не выставлен, таблиц нет, а объяснение
                устройства фондов остаётся: оно верно независимо от сумм. */}
            <Part
              id="vznosy"
              title="Взносы в компенсационные фонды"
              intro={
                FUNDS_CONFIRMED
                  ? 'В таблицах — установленные законом минимумы. Меньше СРО установить не вправе, но своими внутренними документами может установить больше.'
                  : undefined
              }
            >
              <div className="grid gap-10 md:grid-cols-2">
                <Fund
                  title="Фонд возмещения вреда"
                  text="Платят все члены СРО. Уровень ответственности, а с ним и взнос, зависит от суммы обязательств по одному договору: чем крупнее планируемые договоры, тем выше."
                  basis="Обязательства по одному договору"
                  rows={FUNDS_CONFIRMED ? detail.funds.harm.rows : undefined}
                  law={detail.funds.harm.law}
                />
                <Fund
                  title="Фонд обеспечения договорных обязательств"
                  text="Платят только те, кто заявил о намерении заключать договоры конкурентными способами. Если участие в закупках не планируется, этот взнос не требуется."
                  basis="Совокупный размер обязательств"
                  rows={FUNDS_CONFIRMED ? detail.funds.contract.rows : undefined}
                  law={detail.funds.contract.law}
                />
              </div>
              <p className="mt-10 border-l-2 border-accent-400 pl-5 text-[15px] leading-relaxed text-neutral-700">
                {nbsp(
                  'Кроме взносов в компенсационные фонды каждая организация устанавливает вступительный и членские взносы; их размер определяет сама СРО, и точную сумму по конкретной организации назову до оплаты. Уплата взноса в компенсационный фонд в рассрочку или третьими лицами, а также освобождение от него законом не допускаются.',
                )}
                <Law>{LAW.funds}</Law>
              </p>
            </Part>

            {/* Отдельной карточки «Срок рассмотрения» больше нет: тот же срок
                с той же нормой стоит в четвёртом шаге. Региональный принцип
                переехал в «Кому нужно членство». */}
            <PageExtras related={DETAIL_RELATED} />

            {/* Вместо квиза с выбранным видом — «Связаться» со строкой про этот
                вид. Название вида подставляем как есть: toLowerCase()
                превращал аббревиатуру в «сро строителей». */}
            <Contact
              lead={`Отвечу на вопросы по ${detail.card.title}, подберу организацию и назову порядок действий. Консультация бесплатная — и первая, и все следующие.`}
            />
          </main>
          <Footer />
          <div
            className="md:hidden"
            style={{ height: 'calc(4rem + env(safe-area-inset-bottom))' }}
            aria-hidden="true"
          />
          <MobileBar />
    </div>
  )
}
