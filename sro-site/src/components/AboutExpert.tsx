import { Check, FileCheck, Globe, MapPin, type LucideIcon } from 'lucide-react'
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
const ADVANTAGES = [
  'Прямая связь со специалистом, без колл-центра и передачи задачи между отделами',
  'Три вида СРО: строительство, проектирование, инженерные изыскания',
  'Сопровождение после вступления: проверки СРО, изменение видов работ, вопросы НРС',
]

// Пока цифр практики нет, во вводном абзаце их не упоминаем вовсе —
// плейсхолдеры в прозе выглядят ещё хуже, чем в полосе фактов.
const FACTS_READY = !isPlaceholder(FACTS.yearsOfPractice) && !isPlaceholder(FACTS.companies)

// Город из адреса реквизитов: полный адрес в визитке не нужен, он в подвале.
const CITY = 'Ростов-на-Дону'

// Полоса цифр. У конкурентов здесь «15 лет», «1 день», «100%» — цифры
// продавца, проверить их нельзя. Здесь только то, что на сайте уже есть и
// что посетитель может пересчитать сам: страницы видов, список регионов,
// обещание одного исполнителя и бесплатной консультации из «Стоимости».
// Поэтому две цифры считаются из данных, а не набраны руками.
//
// Годы практики и число компаний сюда не входят: заказчик их не назвал,
// а придумать цифру — то же самое, что придумать закон.
const NUMBERS: { value: string; label: string; href: string }[] = [
  {
    value: String(SRO_DETAILS.length),
    label: 'вида СРО: строительство, проектирование, инженерные изыскания',
    href: '#types',
  },
  {
    value: String(REGIONS.length),
    label: 'регионов, в которых помогаю вступить в СРО',
    href: '#regions',
  },
  {
    value: '1',
    label: 'специалист ведёт задачу от обращения до выписки из реестра',
    href: '#faq',
  },
  {
    value: '0 ₽',
    label: 'консультация на любом этапе; оплачивается только работа',
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
            Один специалист ведёт вашу задачу от обращения до выписки из реестра
          </h2>
          <p className="mt-5 text-lg text-neutral-600">
            {FACTS_READY ? (
              <>
                {REQUISITES.legalName} занимается вступлением в СРО {FACTS.yearsOfPractice} лет;
                за это время сопровождение прошли {FACTS.companies} компаний из {FACTS.regions}{' '}
                регионов.
              </>
            ) : (
              <>
                {REQUISITES.legalName} занимается вступлением в СРО строителей, проектировщиков
                и изыскателей, а также вопросами специалистов НРС и независимой оценки
                квалификации.
              </>
            )}
          </p>
          <p className="mt-4 text-neutral-600">
            Каждую задачу от начала до конца ведёт один специалист: он отвечает на вопросы,
            готовит документы и взаимодействует с саморегулируемой организацией. Вы всегда
            знаете, кто занимается вашим вопросом и на каком он этапе.
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

        {/* Визитка компании — на месте фотографии у конкурентов. Фотографии
            нет: сайт представляет компанию, а не лицо. Реквизитов здесь тоже
            нет — они в подвале, где их ищут; тут только знак, имя, город и
            условия работы. */}
        <Reveal delay={100}>
          <div className="relative overflow-hidden rounded-3xl border border-neutral-200 bg-white p-6 shadow-card sm:p-8">
            {/* Крупный знак в углу, полупрозрачный и за краем: узнаваемость
                шапки, а не логотип во всю карточку. Текст лежит поверх него
                только в правом верхнем углу, где строки короткие. */}
            <ScalesMark
              className="pointer-events-none absolute -right-10 -top-8 h-44 w-auto text-accent-50"
              aria-hidden="true"
            />
            <div className="relative">
              <div className="flex items-center gap-3">
                <ScalesMark className="h-8 w-auto shrink-0 text-accent-600" aria-hidden="true" />
                <div className="leading-tight">
                  <p className="text-lg font-bold tracking-tight text-neutral-950">{REQUISITES.legalName}</p>
                  <p className="text-sm text-neutral-600">Вступление в СРО</p>
                </div>
              </div>
              <div className="mt-7 flex flex-col gap-3 border-t border-neutral-200 pt-6">
                <Chip icon={MapPin}>{CITY}</Chip>
                <Chip icon={Globe}>Дистанционно, личный визит не требуется</Chip>
                <Chip icon={FileCheck}>Работаю по договору</Chip>
              </div>
              <a
                href={anchor('#contacts')}
                className="mt-6 inline-block text-sm font-medium text-accent-700 underline underline-offset-2 transition hover:text-accent-800"
              >
                Реквизиты и контакты
              </a>
            </div>
          </div>
        </Reveal>
      </div>

      {/* Полоса цифр под текстом, во всю ширину. Каждая плитка ведёт туда,
          где цифру можно проверить: к страницам видов, к карте, к ответу
          про одного специалиста, к разделу о стоимости. Поэтому плитки и
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
