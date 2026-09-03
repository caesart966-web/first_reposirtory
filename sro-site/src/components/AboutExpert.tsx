import { Check, FileCheck, Globe } from 'lucide-react'
import { FACTS, REQUISITES, isPlaceholder } from '../content/facts'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'

// Максимум три и строками, а не карточками: карточки уже заняты услугами.
// «Стоимость до начала работы» и «пакет под конкретную СРО» отсюда убраны:
// первая мысль живёт в секции «Стоимость», вторая — в «Документах», а здесь
// они повторялись почти дословно.
const ADVANTAGES = [
  'Вы общаетесь напрямую со мной — без колл-центра и передачи задачи «по цепочке»',
  'Работаю с тремя видами СРО: строительство, проектирование, инженерные изыскания',
  'Помогаю и после вступления: проверки СРО, изменение видов работ, вопросы НРС',
]

// Строки с незаполненными реквизитами не показываем: квадратные скобки на
// сайте читаются как «сломано». Появятся данные — строки вернутся сами.
const REQUISITE_ROWS = [
  { label: 'Организация', value: REQUISITES.legalName },
  { label: 'ИНН', value: REQUISITES.inn },
  { label: 'КПП', value: REQUISITES.kpp },
  { label: 'ОГРН', value: REQUISITES.ogrn },
  { label: 'Адрес', value: REQUISITES.address },
].filter((row) => !isPlaceholder(row.value))

// Пока цифр практики нет, во вводном абзаце их не упоминаем вовсе —
// плейсхолдеры в прозе выглядят ещё хуже, чем в полосе фактов.
const FACTS_READY = !isPlaceholder(FACTS.yearsOfPractice) && !isPlaceholder(FACTS.companies)

// Пока реквизитов нет, правая карточка держала две строки на 40% ширины
// секции — читалось как недогрузившаяся страница. До появления данных
// раскладка одноколоночная, а обе строки живут чипами под буллетами;
// с реквизитами двухколонник вернётся сам.
const HAS_REQUISITES = REQUISITE_ROWS.length > 0

export function AboutExpert() {
  return (
    <Section id="about" className="bg-neutral-50/55">
      <div
        className={
          HAS_REQUISITES
            ? 'mx-auto grid max-w-5xl items-start gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:gap-16'
            : 'mx-auto max-w-3xl'
        }
      >
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent-600">
            О специалисте
          </p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
            Вы работаете непосредственно со специалистом, а не с отделом продаж
          </h2>
          <p className="mt-5 text-lg text-neutral-600">
            {FACTS_READY ? (
              <>
                Занимаюсь вопросами СРО {FACTS.yearsOfPractice} лет, за это время сопровождал{' '}
                {FACTS.companies} компаний из {FACTS.regions} регионов.
              </>
            ) : (
              <>
                Помогаю строительным, проектным и изыскательским компаниям вступать в СРО
                и решать связанные с этим задачи.
              </>
            )}
          </p>
          <p className="mt-4 text-neutral-600">
            Каждый проект веду самостоятельно: отвечаю на вопросы, готовлю документы и общаюсь
            с СРО — лично, без менеджеров и посредников. Вы всегда знаете, кто занимается вашей
            задачей и на каком она этапе.
          </p>
          <ul className="mt-7 space-y-3">
            {ADVANTAGES.map((advantage) => (
              <li key={advantage} className="flex items-start gap-3 text-neutral-700">
                <Check className="mt-1 h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                {advantage}
              </li>
            ))}
          </ul>
          {/* Без контейнеров: обведённый rounded-full пилюлей в системе нет,
              и рядом с настоящей кнопкой «Обсудить задачу» такие чипы читались
              как ещё две кнопки. Та же форма, что у этих строк в карточке. */}
          {!HAS_REQUISITES && (
            <div className="mt-7 flex flex-wrap items-center gap-x-7 gap-y-2.5">
              <span className="inline-flex items-center gap-2 text-sm text-neutral-700">
                <Globe className="h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                Все регионы России, дистанционно
              </span>
              <span className="inline-flex items-center gap-2 text-sm text-neutral-700">
                <FileCheck className="h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                Работаю по договору
              </span>
            </div>
          )}
          <ButtonLink href="#quiz" variant="secondary" size="lg" className="mt-8">
            Обсудить задачу
          </ButtonLink>
        </Reveal>

        {HAS_REQUISITES && (
          <Reveal delay={100}>
            <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-card">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-600">
                Реквизиты
              </p>
              <dl className="mt-4 space-y-3 text-sm">
                {REQUISITE_ROWS.map((row) => (
                  <div key={row.label} className="flex justify-between gap-4 border-b border-neutral-200 pb-3 last:border-0 last:pb-0">
                    <dt className="text-neutral-600">{row.label}</dt>
                    <dd className="text-right font-medium text-neutral-900">{row.value}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-5 flex items-center gap-2 text-sm text-neutral-700">
                <Globe className="h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                Все регионы России, дистанционно
              </p>
              <p className="mt-3 flex items-center gap-2 text-sm text-neutral-700">
                <FileCheck className="h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                Работаю по договору
              </p>
            </div>
          </Reveal>
        )}
      </div>
    </Section>
  )
}
