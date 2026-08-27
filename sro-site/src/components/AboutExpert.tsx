import { Check } from 'lucide-react'
import { CONTACTS } from '../content/contacts'
import { FACTS, REQUISITES } from '../content/facts'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'

// Максимум три и строками, а не карточками: карточки уже заняты услугами.
const ADVANTAGES = [
  'Вы общаетесь напрямую со мной — без колл-центра и передачи задачи «по цепочке»',
  'Стоимость обсуждаем и фиксируем до начала работы, без скрытых платежей',
  'Пакет документов готовится под конкретную СРО, ваши виды работ и ваших специалистов',
]

const REQUISITE_ROWS = [
  { label: 'Статус', value: REQUISITES.legalStatus },
  { label: 'ИНН', value: REQUISITES.inn },
  { label: 'ОГРНИП', value: REQUISITES.ogrnip },
]

export function AboutExpert() {
  return (
    <Section id="about">
      <div className="mx-auto grid max-w-5xl items-start gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:gap-16">
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent-600">
            О специалисте
          </p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
            Вы работаете непосредственно со специалистом, а не с отделом продаж
          </h2>
          <p className="mt-5 text-lg text-neutral-600">
            Меня зовут {CONTACTS.name}. Занимаюсь вопросами СРО {FACTS.yearsOfPractice} лет, за это
            время сопровождал {FACTS.companies} компаний из {FACTS.regions} регионов.
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
          <ButtonLink href="#quiz" variant="secondary" className="mt-8">
            Обсудить задачу
          </ButtonLink>
        </Reveal>

        <Reveal delay={100}>
          <div className="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-6">
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
            <p className="mt-5 text-sm text-neutral-600">
              Работаю по договору. Все договорённости — письменно, до начала работы.
            </p>
          </div>
        </Reveal>
      </div>
    </Section>
  )
}
