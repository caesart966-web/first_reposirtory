import {
  AlertCircle,
  Check,
  CheckCircle2,
  ChevronLeft,
  Loader2,
  Phone,
  RotateCcw,
} from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { CONFIGURED, CONTACTS, LINKS, externalLinkProps } from '../content/contacts'
import { buildLeadMessage, sendLead } from '../lib/lead'
import { TelegramIcon, WhatsAppIcon } from './icons'
import { CitySkyline } from './illustrations'
import { useLegalDocs } from './LegalDocs'
import { QUESTIONS, TOTAL_STEPS, useQuiz } from './QuizContext'
import { Button, ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

const inputClasses =
  'mt-1.5 w-full rounded-xl border border-neutral-300 bg-white px-4 py-3 text-neutral-900 placeholder:text-neutral-500 focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-500/30'

export function Quiz() {
  // Шаг, ответы и статус общие с героем (см. QuizContext): первый вопрос
  // задаётся на первом экране, а продолжается квиз уже здесь.
  const { step, setStep, answers, setAnswers, status, setStatus } = useQuiz()
  const [form, setForm] = useState({ name: '', phone: '', email: '' })
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Honeypot: человек поле не видит и не может сфокусировать, боты заполняют.
  const [botField, setBotField] = useState('')
  const advanceTimer = useRef<number | null>(null)
  const openLegal = useLegalDocs()

  // Доступность: при смене шага переводим фокус на заголовок нового шага,
  // чтобы клавиатура и скринридер не «теряли» квиз.
  const stepHeadingRef = useRef<HTMLElement | null>(null)
  const focusPending = useRef(false)

  useEffect(() => {
    if (focusPending.current) {
      focusPending.current = false
      stepHeadingRef.current?.focus()
    }
  }, [step, status])

  useEffect(
    () => () => {
      if (advanceTimer.current !== null) window.clearTimeout(advanceTimer.current)
    },
    [],
  )

  function pickOption(questionId: string, option: string) {
    if (advanceTimer.current !== null) return
    setAnswers((prev) => ({ ...prev, [questionId]: option }))
    advanceTimer.current = window.setTimeout(() => {
      advanceTimer.current = null
      focusPending.current = true
      setStep((prev) => Math.min(prev + 1, TOTAL_STEPS - 1))
    }, 280)
  }

  function goBack() {
    if (advanceTimer.current !== null) return
    setError(null)
    focusPending.current = true
    setStep((prev) => Math.max(prev - 1, 0))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const name = form.name.trim()
    const phone = form.phone.trim()
    const email = form.email.trim()

    if (!name) {
      setError('Пожалуйста, укажите имя.')
      return
    }
    if (phone.replace(/\D/g, '').length < 6) {
      setError('Пожалуйста, укажите корректный номер телефона.')
      return
    }
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setError('Пожалуйста, укажите корректный e-mail.')
      return
    }
    if (!consent) {
      setError('Для отправки заявки нужно согласие на обработку персональных данных.')
      return
    }

    setError(null)

    // Заполненный honeypot — это бот: показываем обычный экран успеха,
    // но заявку никуда не отправляем.
    if (botField.trim()) {
      focusPending.current = true
      setStatus('done')
      return
    }

    setStatus('sending')
    try {
      await sendLead({ name, phone, email, answers })
      focusPending.current = true
      setStatus('done')
    } catch {
      // Введённые данные не сбрасываем: с экрана ошибки можно повторить отправку.
      focusPending.current = true
      setStatus('failed')
    }
  }

  const question = step < QUESTIONS.length ? QUESTIONS[step] : null

  // Готовые ссылки «отправить заявку в один клик» для экрана успеха.
  const leadMessage = buildLeadMessage({
    name: form.name.trim(),
    phone: form.phone.trim(),
    email: form.email.trim(),
    answers,
  })
  // WhatsApp умеет принимать текст сообщения в ссылке, Telegram — нет,
  // поэтому там просто открывается диалог.
  const whatsappSendHref = CONFIGURED.whatsapp
    ? `${CONTACTS.whatsapp}${CONTACTS.whatsapp.includes('?') ? '&' : '?'}text=${encodeURIComponent(leadMessage)}`
    : LINKS.whatsapp
  const telegramSendHref = LINKS.telegram

  return (
    // Тёмная закрывающая секция: квиз поглотил отдельный финальный призыв,
    // чтобы на странице не было двух блоков «оставьте заявку» подряд.
    <Section id="quiz" className="relative overflow-hidden bg-accent-950">
      <CitySkyline className="pointer-events-none absolute inset-x-0 bottom-0 h-20 w-full text-white/[0.09] sm:h-28" />
      <div className="relative">
        <SectionHeading
          dark
          eyebrow="Заявка"
          title="Расскажите, какая задача стоит перед вашей компанией"
          subtitle="4 вопроса меньше чем за минуту — отвечу лично и предложу план действий."
        />
      </div>
      <Reveal className="relative mt-10">
        <div className="mx-auto max-w-2xl rounded-3xl border border-neutral-200 bg-white p-6 shadow-card sm:p-10">
          {status === 'done' ? (
            <div className="text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-accent-50 text-accent-600">
                <CheckCircle2 className="h-8 w-8" aria-hidden="true" />
              </div>
              <h3
                ref={(el) => {
                  stepHeadingRef.current = el
                }}
                tabIndex={-1}
                className="mt-5 text-2xl font-semibold text-neutral-950 focus:outline-none"
              >
                Заявка отправлена{form.name.trim() ? `, ${form.name.trim()}` : ''}
              </h3>
              <p className="mt-3 text-neutral-600">Отвечу лично.</p>
              <div className="mt-6 rounded-2xl bg-neutral-50 p-5 text-left text-sm">
                <p className="font-semibold text-neutral-900">Ваши ответы</p>
                <ul className="mt-3 space-y-2 text-neutral-600">
                  {QUESTIONS.filter((q) => answers[q.id]).map((q) => (
                    <li key={q.id} className="flex justify-between gap-4">
                      <span className="text-neutral-500">{q.id}</span>
                      <span className="text-right font-medium text-neutral-800">
                        {answers[q.id]}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              <p className="mt-6 text-sm text-neutral-500">
                Если удобнее в мессенджере — напишите напрямую.
              </p>
              <div className="mt-3 flex flex-wrap justify-center gap-3">
                <ButtonLink
                  href={whatsappSendHref}
                  variant="secondary"
                  {...externalLinkProps(CONFIGURED.whatsapp)}
                >
                  <WhatsAppIcon className="h-4 w-4" />
                  WhatsApp
                </ButtonLink>
                <ButtonLink
                  href={telegramSendHref}
                  variant="secondary"
                  {...externalLinkProps(CONFIGURED.telegram)}
                >
                  <TelegramIcon className="h-4 w-4" />
                  Telegram
                </ButtonLink>
              </div>
            </div>
          ) : status === 'failed' ? (
            <div className="text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-red-50 text-red-600">
                <AlertCircle className="h-8 w-8" aria-hidden="true" />
              </div>
              <h3
                ref={(el) => {
                  stepHeadingRef.current = el
                }}
                tabIndex={-1}
                className="mt-5 text-2xl font-semibold text-neutral-950 focus:outline-none"
              >
                Не удалось отправить заявку
              </h3>
              <p className="mt-3 text-neutral-600">
                Ваши ответы сохранены — попробуйте отправить ещё раз или свяжитесь со мной
                напрямую.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-3">
                <Button
                  onClick={() => {
                    focusPending.current = true
                    setStatus('idle')
                  }}
                >
                  <RotateCcw className="h-4 w-4" aria-hidden="true" />
                  Попробовать снова
                </Button>
                <ButtonLink href={LINKS.tel} variant="secondary">
                  <Phone className="h-4 w-4" aria-hidden="true" />
                  Позвонить
                </ButtonLink>
                <ButtonLink
                  href={whatsappSendHref}
                  variant="secondary"
                  {...externalLinkProps(CONFIGURED.whatsapp)}
                >
                  <WhatsAppIcon className="h-4 w-4" />
                  WhatsApp
                </ButtonLink>
                <ButtonLink
                  href={telegramSendHref}
                  variant="secondary"
                  {...externalLinkProps(CONFIGURED.telegram)}
                >
                  <TelegramIcon className="h-4 w-4" />
                  Telegram
                </ButtonLink>
              </div>
            </div>
          ) : (
            <>
              <div className="mb-5 flex items-center justify-between text-sm text-neutral-500">
                <span>
                  Шаг {step + 1} из {TOTAL_STEPS}
                </span>
                {step > 0 && (
                  <button
                    type="button"
                    onClick={goBack}
                    className="-my-2 inline-flex items-center gap-1 rounded-lg px-2 py-2.5 font-medium text-accent-600 transition hover:text-accent-700"
                  >
                    <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                    Назад
                  </button>
                )}
              </div>
              <div className="mb-7 h-1.5 overflow-hidden rounded-full bg-neutral-100">
                <div
                  className="h-full rounded-full bg-accent-600 transition-all duration-300"
                  style={{ width: `${((step + 1) / TOTAL_STEPS) * 100}%` }}
                />
              </div>

              {question ? (
                <fieldset>
                  <legend
                    ref={(el) => {
                      stepHeadingRef.current = el
                    }}
                    tabIndex={-1}
                    className="text-xl font-semibold text-neutral-950 focus:outline-none sm:text-2xl"
                  >
                    {question.question}
                  </legend>
                  <div className="mt-6 grid gap-3">
                    {question.options.map((option) => {
                      const selected = answers[question.id] === option
                      return (
                        <button
                          key={option}
                          type="button"
                          onClick={() => pickOption(question.id, option)}
                          aria-pressed={selected}
                          className={`flex items-center justify-between gap-3 rounded-xl border px-5 py-4 text-left font-medium transition-all duration-150 ${
                            selected
                              ? 'border-accent-600 bg-accent-50 text-accent-800'
                              : 'border-neutral-200 bg-white text-neutral-800 hover:border-accent-300 hover:bg-accent-50/50'
                          }`}
                        >
                          {option}
                          <span
                            className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                              selected
                                ? 'border-accent-600 bg-accent-600 text-white'
                                : 'border-neutral-300 text-transparent'
                            }`}
                            aria-hidden="true"
                          >
                            <Check className="h-3 w-3" />
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </fieldset>
              ) : (
                <form onSubmit={handleSubmit} noValidate>
                  <h3
                    ref={(el) => {
                      stepHeadingRef.current = el
                    }}
                    tabIndex={-1}
                    className="text-xl font-semibold text-neutral-950 focus:outline-none sm:text-2xl"
                  >
                    Куда прислать ответ по вашей задаче?
                  </h3>
                  <p className="mt-2 text-neutral-600">
                    Оставьте контакты — свяжусь, уточню детали и предложу план действий.
                  </p>
                  {/* Ловушка для ботов: скрыта визуально, вне таб-порядка,
                      не читается скринридером. Заполнена — заявка не отправляется. */}
                  <div aria-hidden="true">
                    <label className="pointer-events-none absolute -left-[9999px] top-0 h-px w-px overflow-hidden opacity-0">
                      Не заполняйте это поле
                      <input
                        type="text"
                        name="company_website"
                        tabIndex={-1}
                        autoComplete="off"
                        className="pointer-events-none absolute -left-[9999px] top-0 h-px w-px opacity-0"
                        value={botField}
                        onChange={(e) => setBotField(e.target.value)}
                      />
                    </label>
                  </div>
                  <div className="mt-6 grid gap-4">
                    <label className="text-sm font-medium text-neutral-700">
                      Имя
                      <input
                        type="text"
                        name="name"
                        autoComplete="name"
                        placeholder="Как к вам обращаться"
                        value={form.name}
                        onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                        className={inputClasses}
                        required
                      />
                    </label>
                    <label className="text-sm font-medium text-neutral-700">
                      Телефон
                      <input
                        type="tel"
                        name="phone"
                        autoComplete="tel"
                        inputMode="tel"
                        placeholder="+7 ___ ___-__-__"
                        value={form.phone}
                        onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                        className={inputClasses}
                        required
                      />
                    </label>
                    <label className="text-sm font-medium text-neutral-700">
                      E-mail
                      <input
                        type="email"
                        name="email"
                        autoComplete="email"
                        placeholder="name@company.ru"
                        value={form.email}
                        onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                        className={inputClasses}
                        required
                      />
                    </label>
                    <label className="flex items-start gap-3 text-sm text-neutral-600">
                      <input
                        type="checkbox"
                        checked={consent}
                        onChange={(e) => setConsent(e.target.checked)}
                        className="mt-0.5 h-4 w-4 shrink-0 accent-accent-600"
                      />
                      <span>
                        Соглашаюсь на{' '}
                        <button
                          type="button"
                          onClick={(event) => {
                            // preventDefault — чтобы клик по ссылке не переключал чекбокс
                            event.preventDefault()
                            openLegal('consent')
                          }}
                          className="font-medium text-accent-700 underline underline-offset-2 transition hover:text-accent-800"
                        >
                          обработку персональных данных
                        </button>
                      </span>
                    </label>
                  </div>
                  <div aria-live="polite">
                    {error && (
                      <p className="mt-4 flex items-start gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                        {error}
                      </p>
                    )}
                  </div>
                  <Button
                    type="submit"
                    size="lg"
                    className="mt-6 w-full"
                    disabled={status === 'sending'}
                  >
                    {status === 'sending' && (
                      <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                    )}
                    Отправить заявку
                  </Button>
                </form>
              )}
            </>
          )}
        </div>
      </Reveal>
    </Section>
  )
}
