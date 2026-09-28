import { ArrowUpRight, Check, FileText, Scale } from 'lucide-react'
import { useRef, useState, type CSSProperties, type KeyboardEvent, type ReactNode } from 'react'
import type { DocItem } from '../content/sroDetails'
import { DOCS_IP, DOCS_OOO, SRO_DETAILS, STEPS } from '../content/sroDetails'
import { TYPES_GROUP } from '../content/nav'
import { asset, page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { Reveal } from './ui/Reveal'

// Общие части внутренних страниц — видов СРО и услуг (с 28.09.2026).
//
// Раньше страницы видов и услуг были свёрстаны по-разному: у видов уже
// стояли линейки и короткие строки, у услуг — карточки в рамках, лента
// шагов и четыре рамки документов. Заказчик прислал снимок «Подготовки
// документов» и попросил привести к тому же виду. Теперь у обоих типов
// страниц один набор: заголовок раздела, линейки вместо рамок, шаги
// сеткой с номером, списки документов, сноска-норма.

// Ссылка на норму. Не украшение: на странице есть суммы и пороги, и каждый
// из них посетитель должен уметь проверить сам, не веря нам на слово.
// Сноской, а не плашкой: серые плашки у каждого абзаца рябили сильнее
// самого текста. Значок весов — латунью, номер статьи — мелким текстом,
// как ссылка на источник в документе.
export function Law({ children }: { children: string }) {
  return (
    <span className="mt-2 flex items-center gap-1.5 text-xs font-medium text-neutral-600">
      <Scale className="h-3.5 w-3.5 shrink-0 text-accent-500" aria-hidden="true" />
      {children}
    </span>
  )
}

// Раздел страницы. tint — кремовый фон: разделы чередуются, чтобы длинная
// страница читалась частями, а не одним полотном.
// compact — для короткой оговорки между разделами.
export function Part({
  id,
  tint = false,
  compact = false,
  children,
}: {
  id?: string
  tint?: boolean
  compact?: boolean
  children: ReactNode
}) {
  return (
    <section id={id} className={`${compact ? 'py-10 sm:py-14' : 'py-14 sm:py-20'} ${tint ? 'bg-neutral-100' : ''}`}>
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">{children}</div>
    </section>
  )
}

// Заголовок раздела: слева заголовок, справа — одна строка пояснения.
// Кегль — по самому длинному слову заголовков («Компенсационные»): на 320 px
// оно обязано влезать (test-site.mjs, «заголовки не шире своей колонки»).
export const H2 =
  'font-display text-[1.9rem] font-medium leading-[1.04] tracking-[-0.01em] text-neutral-950 min-[380px]:text-[2.2rem] sm:text-[2.7rem] lg:text-[3.1rem]'

export function Head({ title, lead }: { title: string; lead?: string }) {
  return (
    <Reveal className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] lg:items-end lg:gap-16">
      <h2 className={H2}>{nbsp(title)}</h2>
      {lead && <p className="text-[15px] leading-relaxed text-neutral-600 sm:text-base">{nbsp(lead)}</p>}
    </Reveal>
  )
}

// Шаги вступления: номер, кто делает шаг, название, одна-две строки и норма.
// Сеткой в три колонки, а не вертикальной лентой: шесть шагов ложатся
// в две строки, а номер по-прежнему задаёт порядок чтения. Половину шагов
// делает не кандидат — это видно по метке.
const WHO_LABEL = { мы: 'делаю я', СРО: 'делает СРО', кандидат: 'от вас' } as const

export function StepsGrid() {
  return (
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
                  step.who === 'мы' ? 'bg-accent-950 text-neutral-50' : 'border border-neutral-300 text-neutral-700'
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
  )
}

// Строка перечня документов. С details — пояснение и норма под названием
// (страница «Подготовка документов»); без — только название (страницы видов:
// там нужен объём комплекта, а опись — по ссылке).
// Норма у строки не повторяется, если та же стоит под всей колонкой (known):
// у перечня из кодекса она одна на все четыре документа.
export function DocRow({
  item,
  icon,
  details,
  known,
}: {
  item: DocItem
  icon: 'check' | 'file'
  details: boolean
  known?: string
}) {
  const Icon = icon === 'check' ? Check : FileText
  return (
    <li className="flex gap-3 border-b border-neutral-200 py-3.5 text-[15px] leading-snug text-neutral-900">
      <Icon className="mt-[3px] h-4 w-4 shrink-0 text-accent-500" aria-hidden="true" />
      <span className="min-w-0">
        <span className={details ? 'font-medium' : undefined}>{item.title}</span>
        {details && item.detail && (
          <span className="mt-1 block text-sm leading-relaxed text-neutral-600">{nbsp(item.detail)}</span>
        )}
        {details && item.law && item.law !== known && <Law>{item.law}</Law>}
      </span>
    </li>
  )
}

export function DocColumn({
  title,
  hint,
  items,
  law,
  details = false,
}: {
  title: string
  hint: string
  items: DocItem[]
  law?: string
  details?: boolean
}) {
  return (
    <div>
      {/* Строка заголовка той же высоты, что у колонки с переключателем
          ООО / ИП: иначе соседние списки начинались бы на разной высоте. */}
      <h3 className="flex min-h-11 items-center text-lg font-semibold leading-snug text-neutral-950">{title}</h3>
      <p className="mt-1 min-h-10 text-sm leading-snug text-neutral-600">{nbsp(hint)}</p>
      <ul className="mt-4 border-t border-neutral-300">
        {items.map((item) => (
          <DocRow key={item.title} item={item} icon="check" details={details} known={law} />
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
// wide — список в две колонки (на странице услуги раздел во всю ширину).
const FORMS = [
  { key: 'ooo', label: 'ООО', items: DOCS_OOO },
  { key: 'ip', label: 'ИП', items: DOCS_IP },
] as const

export function SroDocs({ details = false, wide = false }: { details?: boolean; wide?: boolean }) {
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
        <div role="tablist" aria-label="Форма организации" className="inline-flex shrink-0 rounded-full bg-neutral-200/80 p-1">
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
      <p className="mt-1 min-h-10 text-sm leading-snug text-neutral-600">
        {nbsp('Обычный запрос сверх кодекса. У другой СРО список может отличаться.')}
      </p>
      <ul
        id="docs-panel"
        role="tabpanel"
        aria-labelledby={`docs-tab-${current.key}`}
        className={`mt-4 border-t border-neutral-300 ${wide ? 'grid sm:grid-cols-2 sm:gap-x-10' : ''}`}
      >
        {current.items.map((item) => (
          <DocRow key={item.title} item={item} icon="file" details={details} />
        ))}
      </ul>
    </div>
  )
}

// Три вида СРО строками — как список на первом экране главной: миниатюра
// своего кадра, название, подсказка из меню и кружок со стрелкой.
export function TypeRows() {
  return (
    <ul className="mt-10 border-b border-neutral-300">
      {SRO_DETAILS.map((detail) => {
        const image = detail.card.image
        const hint = TYPES_GROUP.items.find((item) => item.href === detail.path)?.hint
        return (
          <li key={detail.slug} className="border-t border-neutral-300">
            <a
              href={page(detail.path)}
              className="group -mx-2 flex min-h-16 items-center gap-4 rounded-2xl px-2 py-3 transition-colors duration-500 ease-silk hover:bg-neutral-50 sm:gap-6 sm:py-4"
            >
              {image.thumb && (
                <span
                  className="block h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-neutral-200 sm:h-14 sm:w-14"
                  style={{ viewTransitionName: `sro-${detail.slug}` } as CSSProperties}
                >
                  <picture>
                    {image.thumbAvif && <source type="image/avif" srcSet={asset(image.thumbAvif)} />}
                    <img
                      src={asset(image.thumb)}
                      alt=""
                      width={160}
                      height={160}
                      loading="lazy"
                      decoding="async"
                      className="h-full w-full object-cover transition-transform duration-700 ease-silk group-hover:scale-110"
                    />
                  </picture>
                </span>
              )}
              <span className="min-w-0 flex-1">
                <span className="block font-display text-[1.3rem] font-medium leading-tight text-neutral-950 sm:text-2xl">
                  {detail.card.title}
                </span>
                {hint && <span className="mt-1 block text-sm leading-snug text-neutral-600">{hint}</span>}
              </span>
              <span
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-neutral-300 text-neutral-950 transition-all duration-700 ease-silk group-hover:rotate-45 group-hover:border-neutral-950 group-hover:bg-neutral-950 group-hover:text-neutral-50"
                aria-hidden="true"
              >
                <ArrowUpRight className="h-5 w-5" />
              </span>
            </a>
          </li>
        )
      })}
    </ul>
  )
}
