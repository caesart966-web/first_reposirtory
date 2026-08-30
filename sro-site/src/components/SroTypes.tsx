import { ArrowRight } from 'lucide-react'
import { IMAGES, type PageImage } from '../content/images'
import { QUESTIONS, QUESTION_IDS, SRO_TYPES, useStartQuiz } from './QuizContext'
import { cardHover } from './ui/card'
import { Figure } from './ui/Figure'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Секция — это вопрос квиза «какой вид СРО нужен», показанный картинками:
// посетитель узнаёт себя по кадру и заголовку и входит в квиз с уже выбранным
// ответом. Вопрос ищем по имени, варианты берём из общих констант — так
// карточка и вариант квиза physically одна и та же строка.
const TYPE_QUESTION = QUESTIONS.find((q) => q.id === QUESTION_IDS.type)

// Три карточки — три варианта ответа. Порядок и состав заданы здесь, а не
// выводятся из options фильтрацией: раньше карточка, чей вариант переименовали,
// просто исчезала из сетки, и никто бы этого не заметил.
//
// Формулировки состава работ — из градостроительного законодательства (виды
// СРО и области их деятельности), а не наши: придумывать их нельзя. Область
// строителей и проектировщиков — по ГрК РФ (ст. 55.8), пять видов изысканий —
// по постановлению Правительства РФ № 402. Перечень изысканий полный: четыре
// пункта без геотехнических читались бы как исчерпывающий список, которым
// они не являются.
type TypeCard = { answer: string; title: string; text: string; image: PageImage }

const TYPES: TypeCard[] = [
  {
    answer: SRO_TYPES.construction,
    title: 'СРО строителей',
    text: 'Строительство, реконструкция, капитальный ремонт и снос объектов капитального строительства.',
    image: IMAGES.construction,
  },
  {
    answer: SRO_TYPES.design,
    title: 'СРО проектировщиков',
    text: 'Подготовка проектной документации — архитектурно-строительное проектирование объектов капитального строительства.',
    image: IMAGES.design,
  },
  {
    answer: SRO_TYPES.survey,
    title: 'СРО изыскателей',
    text: 'Инженерные изыскания: геодезические, геологические, гидрометеорологические, экологические, геотехнические.',
    image: IMAGES.survey,
  },
]

export function SroTypes() {
  const startQuiz = useStartQuiz()

  // Вопроса нет — показывать нечего. Раньше здесь стоял `!`, и пропавший
  // вопрос ронял вычисление модуля, то есть белый экран всего сайта вместо
  // одной недостающей секции.
  if (!TYPE_QUESTION) return null

  return (
    <Section id="types" size="compact">
      <SectionHeading
        eyebrow="Виды СРО"
        title="Строительство, проектирование, изыскания"
        subtitle="Работаю со всеми тремя видами саморегулируемых организаций. Выберите свой — уточню детали и назову порядок действий."
      />
      <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {TYPES.map((type, index) => (
          <Reveal key={type.answer} delay={index * 80} className="h-full">
            {/* Карточка кликается целиком: псевдоэлемент кнопки растянут по
                article. Доступное имя при этом остаётся у одной кнопки, а не
                размазывается по картинке и заголовку. */}
            <article
              className={`group relative flex h-full flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-card ${cardHover}`}
            >
              {/* Кадр слегка наезжает при наведении: карточка с фотографией
                  должна отзываться самой фотографией, а не только рамкой.
                  scale-[1.03] — предел, за которым видно потерю резкости. */}
              <div className="overflow-hidden">
                <div className="transition-transform duration-300 group-hover:scale-[1.03]">
                  <Figure {...type.image} frame={false} />
                </div>
              </div>
              <div className="flex flex-1 flex-col p-6">
                <h3 className="text-lg font-semibold text-neutral-950">{type.title}</h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-neutral-600">{type.text}</p>
                {/* Видимая подпись стоит в начале доступного имени, а не в
                    конце: WCAG 2.5.3 требует, чтобы имя начиналось с того, что
                    написано на кнопке, — иначе голосовое управление на команду
                    «нажми Подобрать СРО» кнопку не найдёт. Хвост с названием
                    вида нужен, чтобы три одинаковые кнопки различались на слух. */}
                <button
                  type="button"
                  onClick={() => startQuiz(TYPE_QUESTION.id, type.answer)}
                  aria-label={`Подобрать СРО: ${type.title}`}
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
      <Reveal className="mt-7 text-center text-sm text-neutral-600">
        Ваша область не назвалась?{' '}
        <button
          type="button"
          onClick={() => startQuiz(TYPE_QUESTION.id, SRO_TYPES.unsure)}
          className="font-semibold text-accent-700 underline underline-offset-2 transition hover:text-accent-800"
        >
          Помогу определить
        </button>
      </Reveal>
    </Section>
  )
}
