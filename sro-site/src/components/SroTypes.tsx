import { ArrowRight } from 'lucide-react'
import { SRO_DETAILS } from '../content/sroDetails'
import { page } from '../lib/site'
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

// Карточки берутся из данных страниц видов СРО (content/sroDetails.ts):
// заголовок, описание и кадр карточки — те же строки, что и на самой
// странице. Раньше состав жил здесь отдельным массивом, и после появления
// страниц он стал бы вторым источником правды: переименовали вид на странице
// — на главной он остался старым, и никто бы не заметил.
//
// Формулировки состава работ — из градостроительного законодательства
// (виды СРО и области их деятельности), а не наши: придумывать их нельзя.

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
        {SRO_DETAILS.map((type, index) => (
          <Reveal key={type.slug} delay={index * 80} className="h-full">
            <article
              className={`group relative flex h-full flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-card ${cardHover}`}
            >
              {/* Кадр слегка наезжает при наведении: карточка с фотографией
                  должна отзываться самой фотографией, а не только рамкой.
                  scale-[1.03] — предел, за которым видно потерю резкости. */}
              <div className="overflow-hidden">
                <div className="transition-transform duration-300 group-hover:scale-[1.03]">
                  <Figure {...type.card.image} frame={false} />
                </div>
              </div>
              <div className="flex flex-1 flex-col p-6">
                <h3 className="text-lg font-semibold text-neutral-950 transition-colors group-hover:text-accent-700">
                  {type.card.title}
                </h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-neutral-600">
                  {type.card.text}
                </p>
                {/* Ссылка растянута псевдоэлементом на всю карточку: кликается
                    она целиком, но доступное имя остаётся у одной ссылки, а не
                    размазывается по картинке и заголовку.

                    Видимая подпись стоит в начале доступного имени, а не в
                    конце: WCAG 2.5.3 требует, чтобы имя начиналось с того, что
                    написано на кнопке, — иначе голосовое управление на команду
                    «нажми Подробнее» ссылку не найдёт. Хвост с названием вида
                    нужен, чтобы три одинаковые ссылки различались на слух.

                    Плашка, а не голая строка: на макете, который прислал
                    заказчик, «Подробнее» — именно кнопка, и в ряду из трёх
                    карточек она сразу говорит, что карточка ведёт дальше. */}
                <a
                  href={page(type.path)}
                  aria-label={`Подробнее: ${type.card.title}`}
                  className="mt-5 inline-flex items-center gap-2 self-start rounded-xl border border-accent-200 bg-accent-50 px-4 py-2 text-sm font-semibold text-accent-700 transition-colors group-hover:border-accent-600 group-hover:bg-accent-600 group-hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 after:absolute after:inset-0 after:rounded-2xl"
                >
                  Подробнее
                  <ArrowRight className="h-4 w-4 shrink-0" aria-hidden="true" />
                </a>
              </div>
            </article>
          </Reveal>
        ))}
      </div>
      <Reveal className="mt-7 text-center text-sm text-neutral-600">
        Не нашли свою область?{' '}
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
