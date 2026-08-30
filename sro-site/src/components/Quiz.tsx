import {
  AlertCircle,
  Check,
  CheckCircle2,
  ChevronLeft,
  Loader2,
  Pencil,
  Phone,
  RotateCcw,
} from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { CONFIGURED, CONTACTS, LINKS, externalLinkProps } from '../content/contacts'
import { buildLeadMessage, sendLead } from '../lib/lead'
import { TelegramIcon, WhatsAppIcon } from './icons'
import { CitySkyline } from './illustrations'
import { useLegalDocs } from './LegalDocs'
import { plural } from '../lib/plural'
import { QUESTIONS, TOTAL_STEPS, useQuiz } from './QuizContext'
import { Button, ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

const inputClasses =
  'mt-1.5 w-full rounded-xl border border-neutral-300 bg-white px-4 py-3 text-neutral-900 placeholder:text-neutral-500 focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-500/30'

// Куда идти после ответа: к первому вопросу НИЖЕ текущего, на который ещё
// не отвечали, а если таких нет — на экран контактов.
//
// Просто «шаг + 1» здесь не годится. Часть ответов приходит с самой страницы:
// вид СРО выбирают карточкой в секции «Виды СРО», сценарий — строкой в
// «Типовых ситуациях». Со сдвигом на единицу квиз показывал такой вопрос
// второй раз, уже с подсвеченным ответом, — то есть заставлял отвечать на то,
// на что человек только что ответил кликом по фотографии.
//
// Назад (goBack) при этом ходит ровно на шаг: там посетитель правит ответ
// осознанно, и перепрыгивать через вопросы нельзя.
function nextStep(from: number, answers: Record<string, string>): number {
  const index = QUESTIONS.findIndex((q, i) => i > from && !answers[q.id])
  return index === -1 ? Math.min(QUESTIONS.length, TOTAL_STEPS - 1) : index
}

// Маска телефона без библиотек (T15): из любого ввода — «+7 900 000-00-00».
// Ведущие 7/8 считаем кодом страны и съедаем; всё, кроме цифр, отбрасываем.
// Если цифр не осталось (стёрли всё) — поле пустеет целиком, чтобы «+7 »
// не застревал при удалении.
function formatPhone(raw: string): string {
  let digits = raw.replace(/\D/g, '')
  if (digits.startsWith('7') || digits.startsWith('8')) digits = digits.slice(1)
  digits = digits.slice(0, 10)
  if (!digits) return ''
  let out = `+7 ${digits.slice(0, 3)}`
  if (digits.length > 3) out += ` ${digits.slice(3, 6)}`
  if (digits.length > 6) out += `-${digits.slice(6, 8)}`
  if (digits.length > 8) out += `-${digits.slice(8, 10)}`
  return out
}

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
    const next = { ...answers, [questionId]: option }
    setAnswers(next)
    // 400 мс вместо 280 (T16): выбранный вариант успевает подсветиться,
    // и уход на следующий вопрос не ощущается рывком.
    advanceTimer.current = window.setTimeout(() => {
      advanceTimer.current = null
      focusPending.current = true
      setStep(nextStep(step, next))
    }, 400)
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
    // Маска гарантирует формат «+7 …», здесь проверяем только полноту номера.
    if (phone.replace(/\D/g, '').length < 11) {
      setError('Пожалуйста, укажите номер телефона полностью.')
      return
    }
    // E-mail опционален (T14): валидируем только непустое значение.
    if (email && !/^\S+@\S+\.\S+$/.test(email)) {
      setError('Пожалуйста, укажите корректный e-mail — или оставьте поле пустым.')
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
    <Section id="quiz" size="key" className="relative overflow-hidden bg-accent-950">
      {/* Фон секции: план этажа языком рабочего чертежа, нарисованный нами
          (scripts/make-floorplan.py). Не фотография намеренно — все три
          снимка сайта заняты карточками видов СРО, и любой из них здесь
          повторял бы карточку, стоящую выше по странице.

          Мотив выбран так, чтобы не совпасть ни с одним уже занятым: разрез
          здания стоит в карточке проектировщиков, сетка чертежа — в герое,
          силуэт города — внизу этой же секции, весы — фоном всей страницы.
          План этажа узнаётся всеми тремя аудиториями сразу.

          Линии в файле белые, плотность задаётся здесь: так один файл годится
          под любую тёмную подложку. Маска гасит края — без неё чертёж
          обрывается ровной линией и читается вставкой, а не фоном. */}
      <img
        src="./img/floorplan.svg"
        alt=""
        aria-hidden="true"
        loading="lazy"
        decoding="async"
        className="pointer-events-none absolute inset-0 h-full w-full select-none object-cover opacity-[0.13] [mask-image:radial-gradient(120%_95%_at_50%_50%,#000_0%,#000_45%,transparent_100%)] [-webkit-mask-image:radial-gradient(120%_95%_at_50%_50%,#000_0%,#000_45%,transparent_100%)]"
      />
      <CitySkyline className="pointer-events-none absolute inset-x-0 bottom-0 h-20 w-full text-white/[0.09] sm:h-28" />
      <div className="relative">
        <SectionHeading
          dark
          eyebrow="Заявка"
          title="Расскажите, какая задача стоит перед вашей компанией"
          subtitle={`${QUESTIONS.length} ${plural(
            QUESTIONS.length,
            'вопрос',
            'вопроса',
            'вопросов',
          )} меньше чем за минуту. Отвечу лично, консультация бесплатная.`}
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
                  {question ? `Вопрос ${step + 1} из ${QUESTIONS.length}` : 'Последний шаг'}
                </span>
                {step > 0 && (
                  <button
                    type="button"
                    onClick={goBack}
                    className="-my-2 inline-flex items-center gap-1 rounded-xl px-2 py-2.5 font-medium text-accent-600 transition hover:text-accent-700"
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
                  {/* Свод ответов (T16): последний шанс поправить ответ до
                      отправки. Клик по строке возвращает на тот вопрос; после
                      нового выбора квиз сам дойдёт обратно до контактов. */}
                  <div className="mt-5 rounded-2xl bg-neutral-50 p-4">
                    <p className="text-sm font-semibold text-neutral-900">Ваши ответы</p>
                    <ul className="mt-2 divide-y divide-neutral-200/70">
                      {QUESTIONS.filter((q) => answers[q.id]).map((q) => (
                        <li key={q.id}>
                          <button
                            type="button"
                            onClick={() => {
                              focusPending.current = true
                              setStep(QUESTIONS.findIndex((item) => item.id === q.id))
                            }}
                            className="group flex w-full items-center justify-between gap-4 py-2.5 text-left text-sm transition hover:text-accent-700"
                            aria-label={`Изменить ответ: ${q.id}`}
                          >
                            <span className="text-neutral-500">{q.id}</span>
                            <span className="flex min-w-0 items-center gap-2 text-right font-medium text-neutral-800 group-hover:text-accent-700">
                              <span className="truncate">{answers[q.id]}</span>
                              <Pencil
                                className="h-3.5 w-3.5 shrink-0 text-neutral-400 transition group-hover:text-accent-600"
                                aria-hidden="true"
                              />
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
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
                        onChange={(e) => {
                          const phone = formatPhone(e.target.value)
                          setForm((f) => ({ ...f, phone }))
                        }}
                        maxLength={16}
                        className={inputClasses}
                        required
                      />
                    </label>
                    <label className="text-sm font-medium text-neutral-700">
                      E-mail{' '}
                      <span className="font-normal text-neutral-500">— если удобнее письмом</span>
                      <input
                        type="email"
                        name="email"
                        autoComplete="email"
                        placeholder="name@company.ru"
                        value={form.email}
                        onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                        className={inputClasses}
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
                      <p className="mt-4 flex items-start gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
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
