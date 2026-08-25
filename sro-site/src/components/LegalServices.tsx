import { Award, Briefcase, FilePen, Gavel } from 'lucide-react'
import { JusticeScales, SurveyLegal } from './illustrations'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'

// Смежные юридические услуги с визитки — помимо основного профиля СРО.
const SERVICES = [
  {
    icon: Briefcase,
    title: 'Регистрация и ликвидация',
    text: 'Юридических лиц и предпринимателей — от подачи до внесения записи.',
  },
  {
    icon: FilePen,
    title: 'Изменения в учредительных документах',
    text: 'Подготовлю пакет и сопровожу внесение изменений в ЕГРЮЛ.',
  },
  {
    icon: Gavel,
    title: 'Представление интересов в судах',
    text: 'Досудебная работа и защита позиции компании в судебных спорах.',
  },
  {
    icon: Award,
    title: 'Повышение квалификации и аттестации',
    text: 'Помогу организовать обучение и аттестацию специалистов для СРО и НРС.',
  },
]

export function LegalServices() {
  return (
    <Section id="legal-services" className="relative overflow-hidden">
      <JusticeScales className="pointer-events-none absolute right-2 top-1/2 hidden h-[320px] w-auto -translate-y-1/2 text-accent-500/[0.10] xl:block" />
      <div className="relative grid items-start gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:gap-14">
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent-600">
            Юридическая практика
          </p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
            Смежные юридические услуги
          </h2>
          <p className="mt-4 text-lg text-neutral-600">
            Вопросы, которые часто идут в связке со вступлением в СРО, — решаю их в рамках
            одной задачи, без привлечения сторонних юристов.
          </p>
          <SurveyLegal className="mt-8 hidden h-auto w-full max-w-sm text-accent-500/40 lg:block" />
        </Reveal>
        <div className="grid gap-4 sm:grid-cols-2">
          {SERVICES.map((service, index) => (
            <Reveal key={service.title} delay={(index % 2) * 80} className="h-full">
              <article className="flex h-full items-start gap-4 rounded-2xl border border-neutral-200 bg-white p-5 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-accent-200 hover:shadow-card-hover">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-50 text-accent-600">
                  <service.icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="font-semibold text-neutral-950">{service.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-neutral-600">{service.text}</p>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </Section>
  )
}
