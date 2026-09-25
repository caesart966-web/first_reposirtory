import { ArrowUpRight, Phone } from 'lucide-react'
import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { LINKS } from '../content/contacts'
import { SRO_DETAILS } from '../content/sroDetails'
import { asset, page } from '../lib/site'
import { ButtonLink } from './ui/Button'

// Первый экран — слайдер из трёх видов СРО.
//
// Приём из ролика, который прислал заказчик (сайт «woodland»): кадры
// сменяются шторкой, новый входит справа, старый под ним уезжает влево.
// Здесь у приёма есть смысл, а не только красота: три слайда — три вида
// СРО, и каждая вкладка внизу ведёт на страницу своего вида. Отдельная
// сетка карточек «Виды СРО» под первым экраном поэтому снята — она
// повторяла бы то же самое второй раз подряд.
//
// Заголовок один на все слайды и не меняется: «Вступление в СРО под ключ» —
// это h1 страницы, по нему её находит поиск, и прыгать он не должен.
// Меняются кадр и подсвеченная вкладка.
//
// Смена — по окончании полосы прогресса у активной вкладки (CSS-анимация,
// 7 с). Наведение на вкладки ставит полосу на паузу: человек читает —
// слайд не уезжает из-под глаз. При prefers-reduced-motion автосмены нет
// вовсе: глобальное правило сжимает анимации до 0.01 мс, и без этой
// проверки слайды пролистывались бы мгновенно по кругу.

const SLIDE_MS = 7000

const SLIDES = SRO_DETAILS.map((detail) => ({
  slug: detail.slug,
  href: page(detail.path),
  title: detail.card.title,
  text: detail.card.text,
  image: detail.card.image,
}))

function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = () => setReduced(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])
  return reduced
}

export function Hero() {
  const [current, setCurrent] = useState(0)
  const [prev, setPrev] = useState<number | null>(null)
  const [paused, setPaused] = useState(false)
  const reduced = useReducedMotion()
  // Первый кадр стоит сразу, без шторки: прятать то, что уже на экране,
  // незачем, а шторка на загрузке страницы выглядела бы как мигание.
  const started = useRef(false)

  const goTo = (index: number) => {
    if (index === current) return
    started.current = true
    setPrev(current)
    setCurrent(index)
  }

  const next = () => goTo((current + 1) % SLIDES.length)

  // Вкладка ушла из фокуса окна — пауза, иначе, вернувшись, человек видит
  // уже третий слайд и не понимает, куда делся первый.
  useEffect(() => {
    const onVisibility = () => setPaused(document.hidden)
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [])

  return (
    <section
      className={`relative isolate overflow-hidden bg-neutral-950 text-neutral-50 ${paused ? 'progress-paused' : ''}`}
      aria-roledescription="слайдер"
      aria-label="Виды СРО"
    >
      {/* Слои кадров. Все три лежат друг на друге с самого начала — так
          браузер загружает их заранее, и шторка не упирается в пустоту. */}
      <div className="scroll-drift absolute inset-0 -z-10" aria-hidden="true">
        {SLIDES.map((slide, index) => {
          const role =
            index === current ? 'active' : index === prev ? 'prev' : 'idle'
          return (
            <div
              key={slide.slug}
              className={`absolute inset-0 overflow-hidden ${
                role === 'active'
                  ? `z-20 ${started.current && !reduced ? 'slide-in' : ''}`
                  : role === 'prev'
                    ? `z-10 ${reduced ? 'opacity-0' : 'slide-out'}`
                    : 'z-0 opacity-0'
              }`}
            >
              <picture>
                {slide.image.srcAvif && <source type="image/avif" srcSet={asset(slide.image.srcAvif)} />}
                <img
                  src={asset(slide.image.src)}
                  alt=""
                  width={slide.image.width}
                  height={slide.image.height}
                  loading={index === 0 ? 'eager' : 'lazy'}
                  decoding="async"
                  className="h-full w-full object-cover"
                />
              </picture>
            </div>
          )
        })}
        {/* Плёнка под текстом, три слоя: ровный по всему кадру; с 1280px
            добавочный слева, сходящий на нет к правому краю (текст там только
            в левой колонке); снизу — под вкладками. До 1280px ровный слой
            плотнее: на телефоне и планшете текст идёт во всю ширину, а на
            1024–1279 заголовок доходит до трёх четвертей экрана, где левый
            слой уже сходит на нет, — замер давал там 3,6:1.
            Подобрано замером контраста по каждой надписи на всех трёх
            слайдах (hero-contrast2.mjs), а не на глаз: худший пиксель под
            подписью давал 1.2:1 — кадры дневные, и белый текст ложился
            на небо. */}
        <div className="absolute inset-0 z-30 bg-[rgba(20,17,15,0.62)] xl:bg-[rgba(20,17,15,0.4)]" />
        <div className="absolute inset-0 z-30 hidden bg-[linear-gradient(90deg,rgba(20,17,15,0.8)_0%,rgba(20,17,15,0.6)_48%,rgba(20,17,15,0)_82%)] xl:block" />
        <div className="absolute inset-x-0 bottom-0 z-30 h-2/3 bg-[linear-gradient(0deg,rgba(20,17,15,0.92)_0%,rgba(20,17,15,0.5)_45%,rgba(20,17,15,0)_100%)]" />
      </div>

      <div className="mx-auto flex min-h-[min(860px,calc(100svh-64px))] w-full max-w-6xl flex-col px-4 pb-8 pt-16 sm:px-6 sm:pt-24 lg:px-8">
        <div className="max-w-3xl">
          <p data-hero-text className="flex items-center gap-3 text-sm text-neutral-200">
            <span className="h-px w-8 bg-accent-300" aria-hidden="true" />
            Для строительных, проектных и изыскательских организаций
          </p>
          <h1 className="mt-6 font-display text-[3.4rem] font-medium leading-[0.95] tracking-[-0.015em] sm:text-7xl lg:text-[6.2rem]">
            <span data-hero-text>Вступление в&nbsp;СРО под&nbsp;ключ</span>
          </h1>
          <p className="mt-7 max-w-xl text-lg leading-relaxed text-neutral-200">
            <span data-hero-text>
              Подберу подходящую СРО, подготовлю документы и сопровожу до внесения в реестр
              членов.
            </span>
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <ButtonLink href="#contacts" variant="inverse" size="lg" arrow>
              Связаться
            </ButtonLink>
            <ButtonLink href={LINKS.tel} variant="outlineInverse" size="lg">
              <Phone className="h-4 w-4" aria-hidden="true" />
              Позвонить
            </ButtonLink>
          </div>
        </div>

        {/* Вкладки видов СРО. Полоса сверху у активной — таймер слайда.

            На телефоне три подписи в ряд не помещаются: «Проектировщики»
            наезжало на «Изыскатели». Поэтому там вкладки — только полосы,
            а под ними название и ссылка активного слайда. Сама полоса в 1px,
            но нажимается вся ячейка высотой 44px — меньше пальцу мало. С 640px —
            три колонки с подписями. */}
        <div
          className="mt-auto pt-14"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(document.hidden)}
          onFocusCapture={() => setPaused(true)}
          onBlurCapture={() => setPaused(document.hidden)}
        >
          <div className="grid grid-cols-3 gap-3 sm:gap-6">
            {SLIDES.map((slide, index) => {
              const active = index === current
              return (
                <div key={slide.slug} className="min-w-0">
                  <button
                    type="button"
                    onClick={() => goTo(index)}
                    aria-pressed={active}
                    aria-label={slide.title}
                    className={`group flex min-h-11 w-full flex-col justify-center text-left transition-colors duration-500 ease-silk sm:block sm:min-h-0 ${
                      active ? 'text-neutral-50' : 'text-neutral-300 hover:text-neutral-100'
                    }`}
                  >
                    <span className="relative block h-px bg-white/25">
                      {active && (
                        <span
                          // key перезапускает полосу при каждом возврате на слайд
                          key={`${slide.slug}-${current}-${prev}`}
                          className={`absolute inset-0 bg-neutral-50 ${reduced ? '' : 'progress-run'}`}
                          style={{ '--slide-ms': `${SLIDE_MS}ms` } as CSSProperties}
                          onAnimationEnd={reduced ? undefined : next}
                        />
                      )}
                    </span>
                    <span
                      data-hero-text
                      className="mt-4 hidden font-display text-[1.7rem] font-medium leading-tight sm:block"
                    >
                      {slide.title}
                    </span>
                    <span className="mt-2 hidden text-sm leading-snug text-neutral-300 md:line-clamp-2">
                      {slide.text}
                    </span>
                  </button>
                  <a
                    href={slide.href}
                    className={`mt-3 hidden items-center gap-1.5 text-sm font-medium transition-colors duration-500 ease-silk sm:inline-flex ${
                      active ? 'text-accent-200 hover:text-neutral-50' : 'text-neutral-400 hover:text-neutral-200'
                    }`}
                    aria-label={`Подробнее: ${slide.title}`}
                  >
                    Подробнее
                    <ArrowUpRight className="h-4 w-4 shrink-0" aria-hidden="true" />
                  </a>
                </div>
              )
            })}
          </div>
          {/* Телефон: подпись активного слайда под полосами. */}
          <div className="mt-2 sm:hidden" aria-live="polite">
            <p data-hero-text className="font-display text-[1.7rem] font-medium leading-tight">
              {SLIDES[current].title}
            </p>
            <a
              href={SLIDES[current].href}
              className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-accent-200"
              aria-label={`Подробнее: ${SLIDES[current].title}`}
            >
              Подробнее
              <ArrowUpRight className="h-4 w-4 shrink-0" aria-hidden="true" />
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
