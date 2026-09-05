import {
  createContext,
  useContext,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from 'react'
import { serviceBySlug } from '../content/services'
import { SRO_TYPES } from '../content/sroTypes'

export type Question = {
  id: string
  question: string
  options: string[]
}

// SRO_TYPES живут в content/sroTypes.ts: их импортируют и данные страниц
// видов, а те нужны здесь — без отдельного файла получался круг импортов.
// Реэкспорт оставлен, чтобы секции продолжали брать варианты из квиза.
export { SRO_TYPES } from '../content/sroTypes'

// Идентификаторы вопросов вынесены отдельно, потому что на них ссылаются
// три секции. Раньше они брали вопрос по номеру в массиве (QUESTIONS[0]),
// и перестановка вопросов молча перевесила бы ответы на чужие: сценарий
// «нужно срочно» записался бы в «вид СРО». По имени такое невозможно.
export const QUESTION_IDS = {
  help: 'Какая помощь',
  type: 'Вид СРО',
  urgency: 'Срочность',
  nrs: 'Специалисты НРС',
} as const

// Единственный источник вопросов: их показывают и герой, и секция квиза.
//
// Первым идёт вопрос о задаче, а не о виде СРО: вид посетитель выбирает выше
// по странице, в секции «Виды СРО», — карточкой с фотографией, а не строкой
// списка. Спрашивать одно и то же дважды на расстоянии одного экрана нельзя.
export const QUESTIONS: Question[] = [
  {
    id: QUESTION_IDS.help,
    question: 'Какая помощь нужна?',
    options: [
      'Вступление в СРО под ключ',
      'Подбор и проверка СРО',
      'Подготовка документов',
      'Консультация по НРС / НОК',
    ],
  },
  {
    id: QUESTION_IDS.type,
    question: 'Какой вид СРО нужен?',
    options: [SRO_TYPES.construction, SRO_TYPES.design, SRO_TYPES.survey, SRO_TYPES.unsure],
  },
  {
    id: QUESTION_IDS.urgency,
    question: 'Насколько срочно нужно решить задачу?',
    options: ['Максимально срочно', 'В ближайшее время', 'Пока изучаю вопрос'],
  },
  {
    id: QUESTION_IDS.nrs,
    question: 'Есть ли специалисты, включённые в НРС?',
    options: ['Да, есть', 'Нет', 'Не знаю, нужна проверка'],
  },
]

// Вопросы плюс экран контактов.
export const TOTAL_STEPS = QUESTIONS.length + 1

export type QuizStatus = 'idle' | 'sending' | 'done' | 'failed'

// В контексте только то, что нужно обеим секциям. Данные формы, согласие,
// ошибки валидации и honeypot живут внутри Quiz — герой их не касается.
type QuizContextValue = {
  step: number
  setStep: Dispatch<SetStateAction<number>>
  answers: Record<string, string>
  setAnswers: Dispatch<SetStateAction<Record<string, string>>>
  status: QuizStatus
  setStatus: Dispatch<SetStateAction<QuizStatus>>
}

const QuizContext = createContext<QuizContextValue | null>(null)

// Вид СРО, выбранный на отдельной странице, приезжает в адресе: '?sro=design'.
// Со страницы вида человек уже сказал, куда вступает, — спрашивать его об этом
// ещё раз значит не услышать первый ответ.
//
// Ключи те же, что и в data-sro у страниц (content/sroDetails.ts, поле slug),
// поэтому карта одна и живёт рядом с самими вариантами.
const SRO_BY_SLUG: Record<string, string> = {
  construction: SRO_TYPES.construction,
  design: SRO_TYPES.design,
  survey: SRO_TYPES.survey,
}

// Читаем один раз при старте. Неизвестный ключ игнорируем молча: подставлять
// вместо него «пока не знаю» было бы ответом за посетителя.
function answerFromUrl(): Record<string, string> {
  if (typeof window === 'undefined') return {}
  const params = new URLSearchParams(window.location.search)
  const preset: Record<string, string> = {}
  const slug = params.get('sro')
  const answer = slug ? SRO_BY_SLUG[slug] : undefined
  if (answer) preset[QUESTION_IDS.type] = answer
  // Услуга со страницы /uslugi/…: '?help=nrs'. Тот же принцип — человек уже
  // сказал, какая помощь нужна, кликнув по карточке; второй раз не спрашиваем.
  const help = params.get('help')
  const helpAnswer = help ? serviceBySlug(help)?.help : undefined
  if (helpAnswer) preset[QUESTION_IDS.help] = helpAnswer
  return preset
}

// Считано один раз на загрузку модуля: адрес за время жизни страницы
// не меняется, а вызов на каждый рендер провайдера — лишняя работа.
const URL_ANSWERS = answerFromUrl()

export function QuizProvider({ children }: { children: ReactNode }) {
  const [step, setStep] = useState(() => {
    const first = QUESTIONS.findIndex((q) => !URL_ANSWERS[q.id])
    return first === -1 ? QUESTIONS.length : first
  })
  const [answers, setAnswers] = useState<Record<string, string>>(URL_ANSWERS)
  const [status, setStatus] = useState<QuizStatus>('idle')

  const value = useMemo(
    () => ({ step, setStep, answers, setAnswers, status, setStatus }),
    [step, answers, status],
  )

  return <QuizContext.Provider value={value}>{children}</QuizContext.Provider>
}

export function useQuiz(): QuizContextValue {
  const value = useContext(QuizContext)
  if (!value) throw new Error('useQuiz используется вне QuizProvider')
  return value
}

// Вход в квиз из другой секции: сохраняем готовый ответ, открываем квиз на
// первом вопросе, который ещё без ответа, и прокручиваем к нему. Статус
// сбрасываем, иначе после отправленной заявки посетитель увидит старый экран
// успеха вместо вопроса.
//
// Так работают и первый вопрос в герое (ответ на первый — откроется второй),
// и сценарии в секции «Типовые ситуации» (ответ на любой вопрос — квиз
// начнётся с того, что осталось выяснить).
export function useStartQuiz() {
  const { setAnswers, setStep, setStatus, status } = useQuiz()

  return (questionId: string, option: string) => {
    setAnswers((prev) => {
      // Заявка уже отправлена — значит это новая история: старые ответы
      // не тащим, иначе посетитель попадёт сразу на форму контактов.
      const base = status === 'done' ? {} : prev
      const next = { ...base, [questionId]: option }
      const firstUnanswered = QUESTIONS.findIndex((q) => !next[q.id])
      setStep(firstUnanswered === -1 ? QUESTIONS.length : firstUnanswered)
      return next
    })
    setStatus('idle')

    const target = document.getElementById('quiz')
    if (!target) return
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
  }
}
