import { ChevronRight, Phone } from 'lucide-react'
import { LINKS } from '../content/contacts'
import { BlueprintGrid } from './illustrations'
import { QUESTIONS, useQuiz, useStartQuiz } from './QuizContext'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'

// Первый вопрос квиза стоит прямо на первом экране: точка конверсии
// не должна быть в середине страницы.
const FIRST_QUESTION = QUESTIONS[0]

export function Hero() {
  const startQuiz = useStartQuiz()
  const { answers } = useQuiz()

  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
        {/* Белая вуаль поверх фоновой гравюры: на первом экране уже работают
            сетка чертежа и два размытых пятна, третий фоновый мотив под ними
            даёт грязь. Ниже первого экрана Фемида проступает в полную силу. */}
        <div className="absolute inset-0 bg-white/75" />
        <div className="absolute -top-32 right-[-10%] h-[420px] w-[420px] rounded-full bg-accent-100/60 blur-3xl" />
        <div className="absolute bottom-[-30%] left-[-10%] h-[360px] w-[360px] rounded-full bg-accent-50 blur-3xl" />
        <BlueprintGrid className="absolute inset-0 h-full w-full text-accent-400/25" />
      </div>

      <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-4 pb-14 pt-12 sm:px-6 sm:pb-20 sm:pt-16 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:px-8">
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-600">
            СРО · НРС · НОК · Документы · Сопровождение
          </p>
          <h1 className="mt-5 text-4xl font-bold leading-[1.08] tracking-tight text-neutral-950 sm:text-5xl lg:text-[3.3rem]">
            Помогу вступить в <span className="text-accent-600">СРО</span> без лишней переписки
            и&nbsp;ошибок в&nbsp;документах
          </h1>
          <p className="mt-6 max-w-xl text-lg text-neutral-600">
            Подберу СРО, проверю документы, подготовлю необходимые материалы и лично сопровожу
            процесс.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            {/* На телефоне кнопка спрятана: карточка с тем же первым вопросом
                стоит сразу под ней, и кнопка лишь прокручивала мимо неё. */}
            <ButtonLink href="#quiz" size="lg" className="hidden sm:inline-flex">
              Подобрать СРО за 1 минуту
            </ButtonLink>
            <ButtonLink href={LINKS.tel} variant="secondary" size="lg">
              <Phone className="h-4 w-4" aria-hidden="true" />
              Позвонить
            </ButtonLink>
          </div>
          <p className="mt-6 text-sm text-neutral-600">
            Работаю по договору · Стоимость обсуждаем до начала работы · Конфиденциально
          </p>
        </Reveal>

        <Reveal delay={120}>
          <div className="relative lg:ml-auto lg:w-full lg:max-w-[480px]">
            <div className="rounded-3xl border border-neutral-200/90 bg-white/95 p-5 shadow-card backdrop-blur sm:p-7">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-600">
                Вопрос 1 из {QUESTIONS.length}
              </p>
              <h2 className="mt-3 text-xl font-semibold text-neutral-950 sm:text-2xl">
                {FIRST_QUESTION.question}
              </h2>
              <div className="mt-5 grid gap-2.5">
                {FIRST_QUESTION.options.map((option) => {
                  const selected = answers[FIRST_QUESTION.id] === option
                  return (
                    <button
                      key={option}
                      type="button"
                      onClick={() => startQuiz(FIRST_QUESTION.id, option)}
                      className={`flex items-center justify-between gap-3 rounded-xl border px-4 py-3.5 text-left font-medium transition-all duration-150 sm:px-5 ${
                        selected
                          ? 'border-accent-600 bg-accent-50 text-accent-800'
                          : 'border-neutral-200 bg-white text-neutral-800 hover:border-accent-300 hover:bg-accent-50/50'
                      }`}
                    >
                      {option}
                      <ChevronRight
                        className="h-4 w-4 shrink-0 text-accent-500"
                        aria-hidden="true"
                      />
                    </button>
                  )
                })}
              </div>
              <p className="mt-4 text-sm text-neutral-500">
                1 минута, {QUESTIONS.length} вопроса. Отвечу лично.
              </p>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
