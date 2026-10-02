import { Check, FileText } from 'lucide-react'
import { useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import type { DocItem } from '../content/sroDetails'
import { DOCS_IP, DOCS_LAW, DOCS_OOO, DOCS_SPECIALISTS, LAW, SRO_DETAILS, STEPS } from '../content/sroDetails'
import { TYPES_GROUP } from '../content/nav'
import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { GoTo } from './ui/GoTo'
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
// самого текста. Перед номером статьи — короткая латунная черта, как перед
// подписью источника в документе. До 01.10.2026 там стоял значок весов, но
// весы — знак компании: повторённый у каждой нормы (на странице вида их
// полтора десятка), он превращался в маркер списка, а в 14 px его рисунок
// сливался в пятно.
//
// Номер закона («№ 99-ФЗ») не рвётся по дефису (02.10.2026): в узкой
// колонке строка уходила на «№ 99-» и «ФЗ», а неразрывного дефиса в шрифте
// нет — поэтому хвост с «№» набран неразрывным куском.
export function Law({ children }: { children: string }) {
  const at = children.lastIndexOf('№')
  return (
    <span className="mt-2 flex items-center gap-2 text-xs font-medium tracking-[0.01em] text-neutral-600">
      <span className="h-px w-4 shrink-0 bg-accent-500" aria-hidden="true" />
      {at < 0 ? (
        children
      ) : (
        <span>
          {children.slice(0, at)}
          <span className="whitespace-nowrap">{children.slice(at)}</span>
        </span>
      )}
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
      <div className="mx-auto w-full max-w-6xl min-[1800px]:max-w-7xl px-4 sm:px-6 lg:px-8">{children}</div>
    </section>
  )
}

// Заголовок раздела: слева заголовок, справа — одна строка пояснения.
// Короткое пояснение («Три законных варианта.») стоит под заголовком
// (01.10.2026): справа, напротив заголовка в две строки, оно висело
// одиноким обрывком у правого края. Справа — пояснения длиннее SIDE_LEAD.
// Кегль — по самому длинному слову заголовков («Компенсационные»): на 320 px
// оно обязано влезать (test-site.mjs, «заголовки не шире своей колонки»).
export const H2 =
  'font-display text-[1.9rem] font-medium leading-[1.04] tracking-[-0.01em] text-balance text-neutral-950 min-[380px]:text-[2.2rem] sm:text-[2.7rem] lg:text-[3.1rem]'

const SIDE_LEAD = 50

export function Head({ title, lead }: { title: string; lead?: string }) {
  const side = lead !== undefined && lead.length > SIDE_LEAD
  return (
    <Reveal
      className={`grid gap-4 ${side ? 'lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] lg:items-end lg:gap-16' : ''}`}
    >
      <h2 className={H2}>{nbsp(title)}</h2>
      {lead && <p className="max-w-xl text-[0.9375rem] leading-relaxed text-neutral-600 sm:text-base">{nbsp(lead)}</p>}
    </Reveal>
  )
}

// Строка-переход на страницу, где тема разобрана целиком: слева крупно —
// что там, справа — куда (название страницы со стрелкой). На страницах
// видов ею кончаются «Документы»; на главной (01.10.2026) — «Документы»
// и «Специалисты НРС»: полный разбор живёт на страницах услуг, а главная
// показывает суть и ведёт туда, не повторяя их дословно.
export function PageLink({ href, text, to, className = '' }: { href: string; text: string; to: string; className?: string }) {
  return (
    <a
      href={href}
      className={`group grid gap-4 border-y border-neutral-300 py-6 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-10 ${className}`}
    >
      <span className="font-display text-[1.4rem] font-medium leading-snug text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-accent-700 sm:text-[1.6rem]">
        {nbsp(text)}
      </span>
      <GoTo className="text-base sm:justify-self-end sm:text-[1.0625rem]">{to}</GoTo>
    </a>
  )
}

// Шаги вступления: номер, название, одна-две строки и норма.
// Сеткой в три колонки, а не вертикальной лентой: шесть шагов ложатся
// в две строки, а номер по-прежнему задаёт порядок чтения. Половину шагов
// делает не кандидат — это сказано в самом названии («Проверяю…»,
// «Вы оплачиваете…», «СРО вносит…»), меток рядом нет (см. Step).
export function StepsGrid() {
  return (
    <ol className="mt-10 grid border-t border-neutral-300 sm:grid-cols-2 sm:gap-x-10 lg:grid-cols-3">
      {STEPS.map((step, index) => (
        <li key={step.title} className="border-b border-neutral-300 py-6">
          {/* На телефоне номер слева от текста, как в «Как проходит работа»
              на главной: отдельной строкой над заголовком он добавлял
              к шести шагам почти полэкрана. */}
          <Reveal delay={(index % 3) * 60} className="grid grid-cols-[3rem_minmax(0,1fr)] sm:block">
            <span className="block font-display text-[1.75rem] font-medium leading-none tabular-nums text-accent-500 sm:text-[2rem]">
              {String(index + 1).padStart(2, '0')}
            </span>
            <div>
              <h3 className="text-[1.0625rem] font-semibold leading-snug text-neutral-950 sm:mt-4">{nbsp(step.title)}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-neutral-600">{nbsp(step.detail)}</p>
              {step.law && <Law>{step.law}</Law>}
            </div>
          </Reveal>
        </li>
      ))}
    </ol>
  )
}

// Строка перечня документов. С details — пояснение и норма под названием
// (блок list на страницах услуг); без — только название (страницы видов:
// там нужен объём комплекта, а опись — по ссылке на «Подготовку документов»).
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
    <li className="flex gap-3 border-b border-neutral-200 py-3.5 text-[0.9375rem] leading-snug text-neutral-900">
      <Icon className="mt-[0.1875rem] h-4 w-4 shrink-0 text-accent-500" aria-hidden="true" />
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

// Колонка перечня на страницах видов: только названия, опись с пояснениями —
// на «Подготовке документов» (DocInventory ниже).
export function DocColumn({ title, hint, items, law }: { title: string; hint: string; items: DocItem[]; law?: string }) {
  return (
    <div>
      {/* Строка заголовка той же высоты, что у колонки с переключателем
          ООО / ИП: иначе соседние списки начинались бы на разной высоте. */}
      <h3 className="flex min-h-11 items-center text-lg font-semibold leading-snug text-neutral-950">{title}</h3>
      <p className="mt-1 min-h-10 text-sm leading-snug text-neutral-600">{nbsp(hint)}</p>
      <ul className="mt-4 border-t border-neutral-300">
        {items.map((item) => (
          <DocRow key={item.title} item={item} icon="check" details={false} known={law} />
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
type FormKey = (typeof FORMS)[number]['key']
const SRO_HINT = 'Типовой список сверх закона. У другой СРО он может отличаться.'

function useForm() {
  const [form, setForm] = useState<FormKey>('ooo')
  return [FORMS.find((f) => f.key === form) ?? FORMS[0], setForm] as const
}

function FormTabs({ form, onChange }: { form: FormKey; onChange: (key: FormKey) => void }) {
  const tabs = useRef<(HTMLButtonElement | null)[]>([])
  // Стрелки влево-вправо переключают вкладку, как положено у tablist.
  const onKey = (event: KeyboardEvent, index: number) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    const next = (index + (event.key === 'ArrowRight' ? 1 : FORMS.length - 1)) % FORMS.length
    onChange(FORMS[next].key)
    tabs.current[next]?.focus()
  }
  return (
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
            onClick={() => onChange(f.key)}
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
  )
}

// Страницы видов: три колонки названий, третья — с переключателем.
export function SroDocs() {
  const [current, setForm] = useForm()
  return (
    <div>
      <div className="flex min-h-11 items-center justify-between gap-4">
        <h3 className="text-lg font-semibold leading-snug text-neutral-950">Запрашивает СРО</h3>
        <FormTabs form={current.key} onChange={setForm} />
      </div>
      <p className="mt-1 min-h-10 text-sm leading-snug text-neutral-600">{nbsp(SRO_HINT)}</p>
      <ul id="docs-panel" role="tabpanel" aria-labelledby={`docs-tab-${current.key}`} className="mt-4 border-t border-neutral-300">
        {current.items.map((item) => (
          <DocRow key={item.title} item={item} icon="file" details={false} />
        ))}
      </ul>
    </div>
  )
}

// Опись документов — страница «Подготовка документов» (29.09.2026).
// Раньше здесь стояли две колонки рядом («закон» и «специалисты») и под ними
// третья сеткой в две колонки: у соседних пунктов разная длина пояснений,
// строки расходились по высоте, а в сетке короткий пункт растягивался
// под длинного соседа пустотой. Теперь — как лист описи: слева группа
// (что это, для кого, норма, у СРО — переключатель ООО / ИП), справа
// документы одной колонкой, по порядку, с номером и пояснением. Номер здесь
// уместен: это опись, в ней у документа есть место в перечне.
// На телефоне группа встаёт над своим списком.
// Слово через дефис не рвётся по строкам: «акт приёма-/передачи» на телефоне
// читался как два слова.
function keepHyphens(text: string): ReactNode {
  return text
    .split(/(\S+-\S+)/)
    .map((part, index) => (index % 2 ? <span key={index} className="whitespace-nowrap">{part}</span> : nbsp(part)))
}

function DocGroup({
  title,
  hint,
  law,
  items,
  control,
  panel,
}: {
  title: string
  hint: string
  law?: string
  items: readonly DocItem[]
  control?: ReactNode
  panel?: { id: string; labelledBy: string }
}) {
  return (
    <Reveal className="grid gap-6 border-t border-neutral-400 pt-8 pb-12 last:pb-0 lg:grid-cols-[minmax(0,19rem)_minmax(0,1fr)] lg:gap-16 lg:pt-10">
      <div>
        <h3 className="font-display text-[1.6rem] font-medium leading-tight text-neutral-950 sm:text-[1.85rem]">{title}</h3>
        <p className="mt-2 text-[0.9375rem] leading-relaxed text-neutral-600">{nbsp(hint)}</p>
        {law && <Law>{law}</Law>}
        {control && <div className="mt-5">{control}</div>}
      </div>
      <ol
        id={panel?.id}
        role={panel ? 'tabpanel' : undefined}
        aria-labelledby={panel?.labelledBy}
        className="border-t border-neutral-200 lg:border-t-0"
      >
        {items.map((item, index) => (
          <li
            key={item.title}
            className="grid grid-cols-[2.25rem_minmax(0,1fr)] border-b border-neutral-200 py-4 last:border-b-0 lg:first:pt-1"
          >
            <span className="font-display text-lg font-medium leading-snug tabular-nums text-accent-600">
              {String(index + 1).padStart(2, '0')}
            </span>
            <span className="min-w-0">
              <span className="block text-[1.0625rem] font-medium leading-snug text-neutral-950">{keepHyphens(item.title)}</span>
              {item.detail && (
                <span className="mt-1 block text-[0.9375rem] leading-relaxed text-neutral-600">{nbsp(item.detail)}</span>
              )}
              {item.law && item.law !== law && <Law>{item.law}</Law>}
            </span>
          </li>
        ))}
      </ol>
    </Reveal>
  )
}

export function DocInventory() {
  const [current, setForm] = useForm()
  return (
    <div className="mt-12">
      <DocGroup title="Требует закон" hint="Одинаково для любой СРО." law={LAW.membership} items={DOCS_LAW} />
      <DocGroup
        title="Специалисты в НРС"
        hint="На каждого из двух специалистов, по основному месту работы."
        law={LAW.specialists}
        items={DOCS_SPECIALISTS}
      />
      <DocGroup
        title="Запрашивает СРО"
        hint={SRO_HINT}
        items={current.items}
        control={<FormTabs form={current.key} onChange={setForm} />}
        panel={{ id: 'docs-panel', labelledBy: `docs-tab-${current.key}` }}
      />
    </div>
  )
}

// Три вида СРО строками — как список на первом экране главной: название,
// подсказка из меню и стрелка (ui/GoTo.tsx). До 01.10.2026 у строки были
// миниатюра кадра 48 px и кружок со стрелкой — миниатюра в монохроме
// не читалась, а кружок с 01.10 только у кнопок «Связаться».
export function TypeRows() {
  return (
    <ul className="mt-10 border-b border-neutral-300">
      {SRO_DETAILS.map((detail) => {
        const hint = TYPES_GROUP.items.find((item) => item.href === detail.path)?.hint
        return (
          <li key={detail.slug} className="border-t border-neutral-300">
            <a href={page(detail.path)} className="group flex min-h-16 items-center gap-6 py-4 sm:py-5">
              <span className="min-w-0 flex-1">
                <span className="block font-display text-[1.3rem] font-medium leading-tight text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-accent-700 sm:text-2xl">
                  {detail.card.title}
                </span>
                {hint && <span className="mt-1 block text-sm leading-snug text-neutral-600">{hint}</span>}
              </span>
              <GoTo />
            </a>
          </li>
        )
      })}
    </ul>
  )
}
