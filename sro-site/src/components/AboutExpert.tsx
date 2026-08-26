import {
  FileCog,
  LifeBuoy,
  MessagesSquare,
  Receipt,
  Route,
  SlidersHorizontal,
} from 'lucide-react'
import { CONTACTS } from '../content/contacts'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'

const ADVANTAGES = [
  {
    icon: MessagesSquare,
    title: 'Личная коммуникация',
    text: 'Вы общаетесь напрямую со мной — без колл-центра и передачи задачи «по цепочке».',
  },
  {
    icon: Route,
    title: 'Без лишних посредников',
    text: 'Один человек ведёт вашу задачу от первого вопроса до результата.',
  },
  {
    icon: Receipt,
    title: 'Прозрачная стоимость',
    text: 'Стоимость обсуждаем и фиксируем до начала работы, без скрытых платежей.',
  },
  {
    icon: SlidersHorizontal,
    title: 'Индивидуальная работа',
    text: 'Никаких шаблонных решений «для всех» — только то, что нужно вашей компании.',
  },
  {
    icon: LifeBuoy,
    title: 'Сопровождение',
    text: 'Остаюсь на связи на каждом этапе — и после подачи документов.',
  },
  {
    icon: FileCog,
    title: 'Документы под ситуацию',
    text: 'Пакет готовится под конкретную СРО, ваши виды работ и ваших специалистов.',
  },
]

export function AboutExpert() {
  return (
    <Section id="about">
      <div className="grid items-start gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-14">
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent-600">
            О специалисте
          </p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
            Вы работаете непосредственно со специалистом, а не с отделом продаж
          </h2>
          <p className="mt-5 text-lg text-neutral-600">
            Меня зовут {CONTACTS.name}. Я самостоятельно веду каждый проект: отвечаю на вопросы,
            готовлю документы и общаюсь с СРО — лично, без менеджеров и посредников.
          </p>
          <p className="mt-4 text-neutral-600">
            Вы всегда знаете, кто занимается вашей задачей и на каком она этапе.
          </p>
          <ButtonLink href="#quiz" variant="secondary" className="mt-7">
            Обсудить задачу
          </ButtonLink>
        </Reveal>
        <div className="grid gap-4 sm:grid-cols-2">
          {ADVANTAGES.map((advantage, index) => (
            <Reveal key={advantage.title} delay={(index % 2) * 80} className="h-full">
              <div className="h-full rounded-2xl border border-neutral-200 bg-white p-5 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-accent-200 hover:shadow-card-hover">
                <advantage.icon className="h-5 w-5 text-accent-600" aria-hidden="true" />
                <h3 className="mt-3 font-semibold text-neutral-950">{advantage.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-neutral-600">{advantage.text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </Section>
  )
}
