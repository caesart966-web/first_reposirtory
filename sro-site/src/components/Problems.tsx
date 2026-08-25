import { ClipboardList, Clock, Compass, FileSearch } from 'lucide-react'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

const SCENARIOS = [
  {
    icon: Clock,
    title: 'Нужно срочно вступить в СРО',
    text: 'Контракт уже близко, а членства ещё нет. Выстроим самый короткий реалистичный путь.',
  },
  {
    icon: Compass,
    title: 'Не знаете, какая СРО подходит',
    text: 'Организаций много, условия заметно отличаются. Сравню варианты и объясню разницу простым языком.',
  },
  {
    icon: FileSearch,
    title: 'Не уверены в документах',
    text: 'Проверю комплект до подачи, покажу слабые места и помогу закрыть их заранее.',
  },
  {
    icon: ClipboardList,
    title: 'Есть вопрос по НРС',
    text: 'Разберём требования к специалистам, стажу и документам — составим понятный план действий.',
  },
]

export function Problems() {
  return (
    <Section id="problems">
      <SectionHeading
        eyebrow="Типовые ситуации"
        title="Не знаете, с чего начать?"
        subtitle="Начните с той точки, где вы сейчас, — дальше я подскажу."
      />
      <div className="mt-10 grid gap-4 sm:grid-cols-2 sm:gap-5">
        {SCENARIOS.map((scenario, index) => (
          <Reveal key={scenario.title} delay={(index % 2) * 80} className="h-full">
            <article className="flex h-full items-start gap-4 rounded-2xl border border-neutral-200 bg-white p-6 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-accent-200 hover:shadow-card-hover">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-50 text-accent-600">
                <scenario.icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h3 className="font-semibold text-neutral-950">{scenario.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-neutral-600">{scenario.text}</p>
              </div>
            </article>
          </Reveal>
        ))}
      </div>
      <Reveal className="mt-9 text-center">
        <ButtonLink href="#quiz" size="lg">
          Разобрать мою ситуацию
        </ButtonLink>
      </Reveal>
    </Section>
  )
}
