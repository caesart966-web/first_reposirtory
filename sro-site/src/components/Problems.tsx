import { ArrowRight } from 'lucide-react'
import { QUESTION_IDS, useStartQuiz } from './QuizContext'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Каждый сценарий — это уже готовый ответ на один из вопросов квиза:
// клик по строке не просто ведёт вниз, а записывает то, что посетитель
// про себя уже сформулировал.
//
// Строки «не знаете, какая СРО подходит» здесь больше нет: ровно это
// предлагает секция «Виды СРО» ссылкой «Помогу определить», тем же ответом
// на тот же вопрос и через один экран — это читалось как один и тот же
// вопрос, заданный дважды.
//
// Оставшийся «Документы» пишет тот же ответ, что и вариант в карточке героя,
// и это осознанно: там строка списка вариантов, здесь описанная ситуация,
// между ними два экрана, и повторно отвечать никого не заставляют — квиз
// пропускает вопрос, на который ответ уже есть (см. nextStep в Quiz.tsx).
const SCENARIOS = [
  {
    tag: 'Срочно',
    title: 'Нужно срочно вступить в СРО',
    text: 'Контракт уже близко, а членства ещё нет. Выстроим самый короткий реалистичный путь.',
    questionId: QUESTION_IDS.urgency,
    answer: 'Максимально срочно',
  },
  {
    tag: 'Документы',
    title: 'Не уверены в документах',
    text: 'Проверю комплект до подачи, покажу слабые места и помогу закрыть их заранее.',
    questionId: QUESTION_IDS.help,
    answer: 'Подготовка документов',
  },
  {
    tag: 'НРС',
    title: 'Есть вопрос по НРС',
    text: 'Разберём требования к специалистам, стажу и документам — составим понятный план действий.',
    questionId: QUESTION_IDS.nrs,
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
            className="group flex w-full flex-col gap-2 py-6 text-left transition-colors duration-200 hover:bg-accent-50/40 sm:flex-row sm:items-center sm:gap-8"
          >
            {/* До sm строка вертикальная: колонка тега шириной 112px оставляла
                тексту ~190px из 358 — описания рвались на 5-7 коротких строк. */}
            <span className="shrink-0 text-xs font-semibold uppercase tracking-[0.14em] text-accent-600 sm:w-32">
              {scenario.tag}
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-2 font-semibold text-neutral-950 sm:text-lg">
                {scenario.title}
                <ArrowRight
                  className="h-4 w-4 shrink-0 text-neutral-400 transition-all duration-200 group-hover:translate-x-1 group-hover:text-accent-600 sm:hidden"
                  aria-hidden="true"
                />
              </span>
              <span className="mt-1 block text-sm leading-relaxed text-neutral-600">
                {scenario.text}
              </span>
            </span>
            <ArrowRight
              className="hidden h-5 w-5 shrink-0 text-neutral-400 transition-all duration-200 group-hover:translate-x-1 group-hover:text-accent-600 sm:block"
              aria-hidden="true"
            />
          </button>
        ))}
      </Reveal>
    </Section>
  )
}
