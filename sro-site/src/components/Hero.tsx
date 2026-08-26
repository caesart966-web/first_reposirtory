import { BadgeCheck, FileText, Handshake, Phone, Search, ShieldCheck } from 'lucide-react'
import { LINKS } from '../content/contacts'
import { BlueprintGrid, Themis } from './illustrations'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'

const STEPS = [
  { icon: Search, title: 'Подбор СРО', text: 'Под задачу, регион и виды работ' },
  { icon: ShieldCheck, title: 'Проверка', text: 'Статус СРО и требования к членам' },
  { icon: FileText, title: 'Документы', text: 'Полный пакет под требования СРО' },
  { icon: Handshake, title: 'Сопровождение', text: 'Лично веду процесс до результата' },
]

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
        <div className="absolute -top-32 right-[-10%] h-[420px] w-[420px] rounded-full bg-accent-100/60 blur-3xl" />
        <div className="absolute bottom-[-30%] left-[-10%] h-[360px] w-[360px] rounded-full bg-accent-50 blur-3xl" />
        <BlueprintGrid className="absolute inset-0 h-full w-full text-accent-400/25" />
        {/* Фемида — фирменный мотив с визитки, крупным водяным знаком */}
        {/* Фемида — фоновый водяной знак во всю высоту первого экрана */}
        <Themis className="absolute bottom-0 left-[42%] hidden h-full w-auto text-accent-600/[0.07] sm:block lg:left-[38%]" />
      </div>

      <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-4 pb-14 pt-12 sm:px-6 sm:pb-20 sm:pt-16 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:px-8">
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-600">
            СРО · НРС · НОК · Документы · Сопровождение
          </p>
          <h1 className="mt-5 text-4xl font-bold leading-[1.08] tracking-tight text-neutral-950 sm:text-5xl lg:text-[3.3rem]">
            Помогу вступить в{' '}
            <span className="text-accent-600">СРО</span> без лишней переписки и&nbsp;ошибок
            в&nbsp;документах
          </h1>
          <p className="mt-6 max-w-xl text-lg text-neutral-600">
            Подберу СРО, проверю документы, подготовлю необходимые материалы и лично сопровожу
            процесс.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <ButtonLink href="#quiz" size="lg">
              Получить консультацию
            </ButtonLink>
            <ButtonLink href={LINKS.tel} variant="secondary" size="lg">
              <Phone className="h-4 w-4" aria-hidden="true" />
              Позвонить
            </ButtonLink>
          </div>
          <p className="mt-6 text-sm text-neutral-500">
            Работаю по договору · Стоимость обсуждаем до начала работы · Конфиденциально
          </p>
        </Reveal>

        <Reveal delay={120}>
          <div className="relative lg:ml-auto lg:w-full lg:max-w-[480px]">
            <div className="relative overflow-hidden rounded-3xl border border-neutral-200/90 bg-gradient-to-br from-white via-accent-50/40 to-accent-100/50 p-5 shadow-card sm:p-7">
              <svg className="absolute inset-0 h-full w-full text-accent-300/25" aria-hidden="true">
                <defs>
                  <pattern id="hero-dots" width="22" height="22" patternUnits="userSpaceOnUse">
                    <circle cx="1.5" cy="1.5" r="1.5" fill="currentColor" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#hero-dots)" />
              </svg>
              <div
                className="absolute bottom-14 left-[2.55rem] top-14 hidden w-px border-l-2 border-dashed border-accent-300/70 sm:block"
                aria-hidden="true"
              />
              <div className="relative space-y-3.5">
                {STEPS.map((step, index) => (
                  <div
                    key={step.title}
                    className="group flex items-center gap-4 rounded-2xl border border-neutral-200/90 bg-white/95 px-4 py-3.5 shadow-card backdrop-blur transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover sm:px-5 sm:py-4"
                  >
                    <span className="w-7 shrink-0 text-sm font-bold tabular-nums text-accent-600">
                      0{index + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="font-semibold text-neutral-950">{step.title}</p>
                      <p className="text-sm text-neutral-500">{step.text}</p>
                    </div>
                    <step.icon
                      className="ml-auto h-5 w-5 shrink-0 text-accent-500 transition-transform duration-200 group-hover:scale-110"
                      aria-hidden="true"
                    />
                  </div>
                ))}
              </div>
            </div>
            <div className="absolute -top-4 right-4 hidden items-center gap-2 rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-800 shadow-card sm:flex">
              <BadgeCheck className="h-4 w-4 text-accent-600" aria-hidden="true" />
              Лично веду каждый проект
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
