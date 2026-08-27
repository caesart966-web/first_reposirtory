import { ArrowRight } from 'lucide-react'
import { QUESTIONS, useStartQuiz } from './QuizContext'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Каждый сценарий — это уже готовый ответ на один из вопросов квиза:
// клик по строке не просто ведёт вниз, а записывает то, что посетитель
// про себя уже сформулировал.
const SCENARIOS = [
  {
    tag: 'Срочно',
    title: 'Нужно срочно вступить в СРО',
    text: 'Контракт уже близко, а членства ещё нет. Выстроим самый короткий реалистичный путь.',
    questionId: QUESTIONS[1].id,
    answer: 'Максимально срочно',
  },
  {
    tag: 'Выбор СРО',
    title: 'Не знаете, какая СРО подходит',
    text: 'Организаций много, условия заметно отличаются. Сравню варианты и объясню разницу простым языком.',
    questionId: QUESTIONS[0].id,
    answer: 'Пока не знаю — нужна помощь с выбором',
  },
  {
    tag: 'Документы',
    title: 'Не уверены в документах',
    text: 'Проверю комплект до подачи, покажу слабые места и помогу закрыть их заранее.',
    questionId: QUESTIONS[3].id,
    answer: 'Подготовка документов',
  },
  {
    tag: 'НРС',
    title: 'Есть вопрос по НРС',
    text: 'Разберём требования к специалистам, стажу и документам — составим понятный план действий.',
    questionId: QUESTIONS[2].id,
    answer: 'Не знаю, нужна проверка',
  },
]

export function Problems() {
  const startQuiz = useStartQuiz()

  return (
    <Section id="problems">
      <SectionHeading
        eyebrow="Типовые ситуации"
        title="Не знаете, с чего начать?"
        subtitle="Выберите то, что ближе к вашей ситуации, — продолжим с этого места."
      />
      {/* Не карточки, а крупные строки: секция должна читаться иначе,
          чем сетки услуг и контактов. */}
      <Reveal className="mx-auto mt-10 max-w-4xl divide-y divide-neutral-200 border-y border-neutral-200">
        {SCENARIOS.map((scenario) => (
          <button
            key={scenario.title}
            type="button"
            onClick={() => startQuiz(scenario.questionId, scenario.answer)}
            className="group flex w-full items-center gap-5 py-6 text-left transition-colors duration-200 hover:bg-accent-50/40 sm:gap-8"
          >
            <span className="w-28 shrink-0 text-xs font-semibold uppercase tracking-[0.14em] text-accent-600 sm:w-32">
              {scenario.tag}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block font-semibold text-neutral-950 sm:text-lg">
                {scenario.title}
              </span>
              <span className="mt-1 block text-sm leading-relaxed text-neutral-600">
                {scenario.text}
              </span>
            </span>
            <ArrowRight
              className="h-5 w-5 shrink-0 text-neutral-400 transition-all duration-200 group-hover:translate-x-1 group-hover:text-accent-600"
              aria-hidden="true"
            />
          </button>
        ))}
      </Reveal>
    </Section>
  )
}
