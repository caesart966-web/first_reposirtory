import {
  createContext,
  useContext,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from 'react'

export type Question = {
  id: string
  question: string
  options: string[]
}

// Единственный источник вопросов: их показывают и герой, и секция квиза.
export const QUESTIONS: Question[] = [
  {
    id: 'Вид СРО',
    question: 'Какой вид СРО нужен?',
    options: [
      'Строительство',
      'Проектирование',
      'Инженерные изыскания',
      'Пока не знаю — нужна помощь с выбором',
    ],
  },
  {
    id: 'Срочность',
    question: 'Насколько срочно нужно решить задачу?',
    options: ['Максимально срочно', 'В ближайшее время', 'Пока изучаю вопрос'],
  },
  {
    id: 'Специалисты НРС',
    question: 'Есть ли специалисты, включённые в НРС?',
    options: ['Да, есть', 'Нет', 'Не знаю, нужна проверка'],
  },
  {
    id: 'Какая помощь',
    question: 'Какая помощь нужна?',
    options: [
      'Вступление в СРО под ключ',
      'Подбор и проверка СРО',
      'Подготовка документов',
      'Консультация по НРС / НОК',
    ],
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

export function QuizProvider({ children }: { children: ReactNode }) {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
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

// Ответ на вопрос из героя: сохраняем выбор, открываем квиз на следующем
// вопросе и прокручиваем к нему. Статус сбрасываем, иначе после отправленной
// заявки посетитель увидит старый экран успеха вместо вопроса.
export function useStartQuizFromHero() {
  const { setAnswers, setStep, setStatus } = useQuiz()

  return (questionId: string, option: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: option }))
    setStatus('idle')
    setStep(1)

    const target = document.getElementById('quiz')
    if (!target) return
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
  }
}
