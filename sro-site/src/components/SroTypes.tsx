import { ArrowRight } from 'lucide-react'
import { IMAGES, type PageImage } from '../content/images'
import { QUESTIONS, QUESTION_IDS, useStartQuiz } from './QuizContext'
import { Figure } from './ui/Figure'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Секция — это вопрос квиза «какой вид СРО нужен», показанный картинками:
// посетитель узнаёт себя по кадру и заголовку и входит в квиз с уже выбранным
// ответом. Вопрос берётся по имени, а варианты — прямо из него: разъехаться
// подписи карточек и варианты квиза не могут.
const TYPE_QUESTION = QUESTIONS.find((q) => q.id === QUESTION_IDS.type)!

// Карточки описаны по вариантам ответа, а не списком рядом с ними: ключ здесь —
// та же строка, что уходит в квиз и в письмо с заявкой. Разъехаться подписи
// и варианты не могут, а лишний или переименованный вариант виден сразу.
//
// Формулировки состава работ — из градостроительного законодательства (виды
// СРО и области их деятельности), а не наши: придумывать их нельзя.
const CARDS: Record<string, { title: string; text: string; image: PageImage }> = {
  Строительство: {
    title: 'СРО строителей',
    text: 'Строительство, реконструкция, капитальный ремонт и снос объектов капитального строительства.',
    image: IMAGES.construction,
  },
  Проектирование: {
    title: 'СРО проектировщиков',
    text: 'Подготовка проектной документации — архитектурно-строительное проектирование объектов.',
    image: IMAGES.design,
  },
  'Инженерные изыскания': {
    title: 'СРО изыскателей',
    text: 'Инженерные изыскания: геодезические, геологические, гидрометеорологические, экологические.',
    image: IMAGES.survey,
  },
}

const TYPES = TYPE_QUESTION.options
  .map((answer) => ({ answer, card: CARDS[answer] }))
  .filter((item): item is { answer: string; card: (typeof CARDS)[string] } => Boolean(item.card))

// Оставшийся вариант того же вопроса («пока не знаю») — для тех, кто пришёл
// без готового ответа. Отдельной карточкой он был бы четвёртым в ряду из трёх
// и ломал бы сетку, поэтому стоит строкой под ней.
const UNSURE = TYPE_QUESTION.options.find((option) => !CARDS[option])

export function SroTypes() {
  const startQuiz = useStartQuiz()

  return (
    <Section id="types">
      <SectionHeading
        eyebrow="Виды СРО"
        title="Строительство, проектирование, изыскания"
        subtitle="Работаю со всеми тремя видами саморегулируемых организаций. Выберите свой — уточню детали и назову порядок действий."
      />
      <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {TYPES.map(({ answer, card }, index) => (
          <Reveal key={answer} delay={index * 80} className="h-full">
            {/* Карточка кликается целиком: псевдоэлемент кнопки растянут по
                article. Доступное имя при этом остаётся у одной кнопки, а не
                размазывается по картинке и заголовку. */}
            <article className="relative flex h-full flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-card transition-colors duration-200 hover:border-accent-300">
              <Figure {...card.image} frame={false} />
              <div className="flex flex-1 flex-col p-6">
                <h3 className="text-lg font-semibold text-neutral-950">{card.title}</h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-neutral-600">{card.text}</p>
                <button
                  type="button"
                  onClick={() => startQuiz(TYPE_QUESTION.id, answer)}
                  aria-label={`${card.title}: подобрать и обсудить задачу`}
                  className="mt-5 inline-flex items-center gap-2 self-start rounded-xl text-sm font-semibold text-accent-700 transition hover:text-accent-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 after:absolute after:inset-0 after:rounded-2xl"
                >
                  Подобрать СРО
                  <ArrowRight className="h-4 w-4 shrink-0" aria-hidden="true" />
                </button>
              </div>
            </article>
          </Reveal>
        ))}
      </div>
      {UNSURE && (
        <Reveal className="mt-7 text-center text-sm text-neutral-600">
          Не знаете, какой вид нужен?{' '}
          <button
            type="button"
            onClick={() => startQuiz(TYPE_QUESTION.id, UNSURE)}
            className="font-semibold text-accent-700 underline underline-offset-2 transition hover:text-accent-800"
          >
            Помогу определить
          </button>
        </Reveal>
      )}
    </Section>
  )
}
