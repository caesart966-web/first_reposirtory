import { Check, FileCheck, Globe, type LucideIcon } from 'lucide-react'
import { FACTS, REQUISITES, isPlaceholder } from '../content/facts'
import { REGIONS } from '../content/regions'
import { SRO_DETAILS } from '../content/sroDetails'
import { anchor } from '../lib/site'
import { ScalesMark } from './illustrations'
import { ButtonLink } from './ui/Button'
import { cardHover } from './ui/card'
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
  { label: 'ИНН', value: REQUISITES.inn },
  { label: 'КПП', value: REQUISITES.kpp },
  { label: 'ОГРН', value: REQUISITES.ogrn },
  { label: 'Адрес', value: REQUISITES.address },
].filter((row) => !isPlaceholder(row.value))

// Пока цифр практики нет, во вводном абзаце их не упоминаем вовсе —
// плейсхолдеры в прозе выглядят ещё хуже, чем в полосе фактов.
const FACTS_READY = !isPlaceholder(FACTS.yearsOfPractice) && !isPlaceholder(FACTS.companies)

// Полоса цифр. У конкурентов здесь «15 лет», «1 день», «100%» — цифры
// продавца, проверить их нельзя. Здесь только то, что на сайте уже есть и
// что посетитель может пересчитать сам: страницы видов, список регионов,
// обещание одного исполнителя и бесплатного разбора из «Стоимости».
// Поэтому две цифры считаются из данных, а не набраны руками.
//
// Годы практики и число компаний сюда не входят: заказчик их не назвал,
// а придумать цифру — то же самое, что придумать закон.
const NUMBERS: { value: string; label: string; href: string }[] = [
  {
    value: String(SRO_DETAILS.length),
    label: 'вида СРО: строители, проектировщики, изыскатели',
    href: '#types',
  },
  {
    value: String(REGIONS.length),
    label: 'регионов, где помогаю вступить — дистанционно',
    href: '#regions',
  },
  {
    value: '1',
    label: 'исполнитель на всю задачу: от первого звонка до выписки из реестра',
    href: '#faq',
  },
  {
    value: '0 ₽',
    label: 'за разбор задачи и консультацию — платите только за работу',
    href: '#pricing',
  },
]

function Chip({ icon: Icon, children }: { icon: LucideIcon; children: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-neutral-700">
      <Icon className="h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
      {children}
    </span>
  )
}

export function AboutExpert() {
  return (
    <Section id="about" className="bg-neutral-50/55">
      <div className="grid items-center gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:gap-16">
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent-600">О нас</p>
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
                Помогаю строительным, проектным и изыскательским компаниям вступать в СРО и решать
                связанные с этим задачи.
              </>
            )}
          </p>
          <p className="mt-4 text-neutral-600">
            Каждый проект веду самостоятельно: отвечаю на вопросы, готовлю документы и общаюсь с СРО
            — лично, без менеджеров и посредников. Вы всегда знаете, кто занимается вашей задачей и
            на каком она этапе.
          </p>
          <ul className="mt-7 space-y-3">
            {ADVANTAGES.map((advantage) => (
              <li key={advantage} className="flex items-start gap-3 text-neutral-700">
                <Check className="mt-1 h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                {advantage}
              </li>
            ))}
          </ul>
          <ButtonLink href={anchor('#quiz')} variant="secondary" size="lg" className="mt-8">
            Обсудить задачу
          </ButtonLink>
        </Reveal>

        {/* Карточка компании — на месте фотографии у конкурентов. Фотографии
            нет и не будет: сайт представляет компанию, а не лицо. Вместо неё
            знак, юридическое имя и реквизиты — то, что действительно
            подтверждает, с кем вы имеете дело. */}
        <Reveal delay={100}>
          <div className="relative overflow-hidden rounded-3xl border border-neutral-200 bg-white p-6 shadow-card sm:p-8">
            {/* Крупный знак в углу, полупрозрачный: узнаваемость шапки, а не
                логотип на всю карточку. Уходит за край намеренно. */}
            <ScalesMark
              className="pointer-events-none absolute -right-8 -top-6 h-40 w-auto text-accent-100"
              aria-hidden="true"
            />
            <div className="relative">
              <div className="flex items-center gap-3">
                <ScalesMark className="h-7 w-auto shrink-0 text-accent-600" aria-hidden="true" />
                <div className="leading-tight">
                  <p className="font-bold tracking-tight text-neutral-950">{REQUISITES.legalName}</p>
                  <p className="text-sm text-neutral-600">Вступление в СРО</p>
                </div>
              </div>
              {REQUISITE_ROWS.length > 0 && (
                <dl className="mt-6 space-y-3 text-sm">
                  {REQUISITE_ROWS.map((row) => (
                    <div
                      key={row.label}
                      className="flex justify-between gap-4 border-b border-neutral-200 pb-3 last:border-0 last:pb-0"
                    >
                      <dt className="shrink-0 text-neutral-600">{row.label}</dt>
                      <dd className="text-right font-medium text-neutral-900">{row.value}</dd>
                    </div>
                  ))}
                </dl>
              )}
              <div className="mt-6 flex flex-col gap-2.5">
                <Chip icon={Globe}>Дистанционно, приезжать не нужно</Chip>
                <Chip icon={FileCheck}>Работаю по договору</Chip>
              </div>
            </div>
          </div>
        </Reveal>
      </div>

      {/* Полоса цифр под текстом, во всю ширину. Каждая плитка ведёт туда,
          где цифру можно проверить: к страницам видов, к карте, к ответу
          про одного исполнителя, к разделу о стоимости. Поэтому плитки и
          приподнимаются при наведении — это обещание клика, и оно честное. */}
      <Reveal delay={140} className="mt-12">
        <ul className="grid grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-5">
          {NUMBERS.map((item) => (
            <li key={item.href}>
              <a
                href={anchor(item.href)}
                className={`flex h-full flex-col rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6 ${cardHover}`}
              >
                <span className="text-4xl font-bold tabular-nums tracking-tight text-accent-700 sm:text-5xl">
                  {item.value}
                </span>
                <span className="mt-3 text-sm leading-snug text-neutral-600">{item.label}</span>
              </a>
            </li>
          ))}
        </ul>
      </Reveal>
    </Section>
  )
}
