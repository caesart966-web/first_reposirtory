import { ArrowUpRight, Phone } from 'lucide-react'
import { useEffect, useState, type CSSProperties } from 'react'
import { LINKS } from '../content/contacts'
import { IMAGES } from '../content/images'
import { TYPES_GROUP } from '../content/nav'
import { SRO_DETAILS } from '../content/sroDetails'
import { asset, page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { ButtonLink } from './ui/Button'
import { RevealText } from './ui/Reveal'

// Первый экран — «лист и окно» (с 26.09.2026): слева светлая бумага
// с заголовком, кнопками и тремя видами СРО, справа кадр с краном во всю
// высоту раздела.
//
// До этого здесь стоял слайдер: три кадра по семь секунд, и в каждый момент
// видна была треть предложения — на телефоне только «СРО строителей».
// Теперь все три вида стоят списком сразу, а кадр нужен один. Списком,
// а не карточками, и без номеров: номера на сайте остались там, где есть
// порядок (шаги работы, опись документов), а три вида СРО — не очередь.
// Название и подсказка — тот же набор данных, что выпадающее меню «Виды СРО»
// (TYPES_GROUP): разойтись с шапкой они не могут.
//
// Кадр — в тёплом монохроме, как все фотографии сайта, и снят «светлым
// ключом»: небо уходит в бумагу, поэтому кадр растворяется в листе без рамки
// и без серой полосы (маска .hero-photo в index.css). При загрузке он
// «проявляется», как отпечаток, текст выплывает ступенькой (.hero-rise, --d).
// У каждого вида СРО в списке — миниатюра своего кадра из той же серии
// (sro-thumb-*, 160 px, 2–5 КБ). У миниатюры и шапки страницы вида одно имя
// перехода, «sro-<вид>»: нажали вид — миниатюра разворачивается в шапку.
// При наведении строка ложится на лист, миниатюра чуть приближается,
// кружок со стрелкой темнеет и поворачивается.
//
// СМЕНА КАДРА (с 28.09.2026). Наведение на вид СРО (или фокус с клавиатуры)
// меняет кадр в окне на кадр этого вида: план этажа для проектировщиков,
// изыскатели с прибором для изыскателей; ушёл курсор со списка — вернулся кран.
// Кадр меняется в том же окне, а не разворачивается на весь фон: текст
// остаётся на бумаге, и контраст не зависит от того, какой кадр сейчас
// под ним (на весь фон понадобилось бы затемнение и белый текст — это уже
// другой первый экран). Новый кадр проступает поверх крана (opacity) и чуть
// оседает из приближения, как при загрузке; уходящий гаснет вдвое медленнее. Два дополнительных кадра —
// около 200 КБ, поэтому грузятся после загрузки страницы, когда браузер
// свободен, и только там, где есть наведение и окно шире телефона:
// на телефоне кадр — узкая полоса, а наведения нет вовсе.
//
// ТЕЛЕФОН. Первый экран обязан показать, что это, для кого и как связаться:
// заголовок, обе кнопки и все три вида — без прокрутки при видимой высоте
// окна 780 px (стережёт test-site.mjs). Поэтому там кадр — невысокая полоса
// сверху, подзаголовок «Для строительных, проектных…» снят (его повторяет
// список видов прямо под кнопками), а у видов — только названия: подсказки
// в две строки растягивали список за край экрана.

// Ступенька появления: задержка анимации .hero-rise.
const delay = (ms: number) => ({ '--d': `${ms}ms` }) as CSSProperties

const TYPES = SRO_DETAILS.map((detail) => ({
  slug: detail.slug,
  title: detail.card.title,
  hint: TYPES_GROUP.items.find((item) => item.href === detail.path)?.hint,
  href: page(detail.path),
  image: detail.card.image,
}))

// Какую часть кадра показывать в окне первого экрана. Окно на компьютере
// почти квадратное, панорама изыскателей широкая — из неё берутся люди
// с прибором, а не мачта с левого края. Классы записаны целиком: Tailwind
// собирает только те, что видит в исходнике.
const FRAME: Record<string, string> = {
  construction: 'object-[50%_30%] lg:object-[50%_18%]',
  design: 'object-[50%_50%] lg:object-[45%_50%]',
  survey: 'object-[70%_40%] lg:object-[80%_45%]',
}

// Кадр, который сейчас на экране, и загружены ли остальные. Смена кадра —
// только там, где есть наведение: на телефоне касание строки сразу ведёт
// на страницу вида, и грузить ради него два кадра незачем.
const canHover = () => matchMedia('(hover: hover) and (min-width: 640px)').matches
const idle = 'requestIdleCallback' in window

function useHoverFrame() {
  const [shown, setShown] = useState<string | null>(null)
  const [ready, setReady] = useState(false)
  useEffect(() => {
    if (!canHover()) return
    let handle = 0
    const start = () => {
      handle = idle
        ? requestIdleCallback(() => setReady(true), { timeout: 3000 })
        : window.setTimeout(() => setReady(true), 1200)
    }
    if (document.readyState === 'complete') start()
    else addEventListener('load', start, { once: true })
    return () => {
      removeEventListener('load', start)
      if (idle) cancelIdleCallback(handle)
      else clearTimeout(handle)
    }
  }, [])
  const show = (slug: string | null) => {
    if (!canHover()) return
    // Курсор пришёл раньше, чем браузер освободился, — грузим сразу.
    if (slug) setReady(true)
    setShown(slug)
  }
  return { shown, ready, show }
}

export function Hero() {
  const image = IMAGES.construction
  const frame = useHoverFrame()
  return (
    <section className="relative isolate overflow-hidden bg-neutral-50 text-neutral-950" aria-labelledby="hero-title">
      {/* Кадр: на телефоне и планшете — полоса над текстом, с 1024px — правая
          часть раздела во всю высоту, край к краю экрана; растворяется
          к тексту. Лист поверх (.hero-develop) — для «проявления». */}
      <div
        className="hero-photo relative h-28 overflow-hidden min-[380px]:h-32 sm:h-72 lg:absolute lg:inset-y-0 lg:left-[46%] lg:right-0 lg:h-auto min-[1800px]:left-[calc(50%-90px)] min-[1800px]:right-[max(0px,calc(50%-900px))]"
        aria-hidden="true"
      >
        <picture className="hero-print block h-full w-full">
          {image.srcAvif && <source type="image/avif" srcSet={asset(image.srcAvif)} />}
          <img
            src={asset(image.src)}
            alt=""
            width={image.width}
            height={image.height}
            loading="eager"
            decoding="async"
            className={`scroll-drift h-full w-full object-cover ${FRAME.construction}`}
          />
        </picture>
        {frame.ready &&
          TYPES.filter((type) => type.image !== image).map((type) => (
            <picture
              key={type.slug}
              // Приходящий кадр проступает быстрее, чем гаснет уходящий:
              // при переходе с вида на вид иначе на середине сквозь оба
              // просвечивал кран — двойная экспозиция.
              className={`absolute inset-0 transition-[opacity,transform] ease-silk ${
                frame.shown === type.slug ? 'opacity-100 duration-700' : 'opacity-0 duration-[1400ms] motion-safe:scale-[1.04]'
              }`}
            >
              {type.image.srcAvif && <source type="image/avif" srcSet={asset(type.image.srcAvif)} />}
              <img
                src={asset(type.image.src)}
                alt=""
                width={type.image.width}
                height={type.image.height}
                decoding="async"
                className={`scroll-drift h-full w-full object-cover ${FRAME[type.slug] ?? ''}`}
              />
            </picture>
          ))}
        <span className="hero-develop absolute inset-0 bg-neutral-50" aria-hidden="true" />
      </div>

      <div className="mx-auto flex w-full max-w-6xl flex-col px-4 pb-10 pt-5 sm:px-6 sm:pb-14 sm:pt-10 lg:min-h-[min(860px,calc(100svh-64px))] lg:px-8 lg:pb-12 lg:pt-12">
        <div className="lg:w-[56%]">
          <p data-hero-text className="hero-rise hidden items-center gap-3 text-sm text-neutral-600 sm:flex" style={delay(0)}>
            <span className="h-px w-8 bg-accent-500" aria-hidden="true" />
            Для строительных, проектных и изыскательских организаций
          </p>
          <RevealText
            as="h1"
            id="hero-title"
            text={'Вступление в СРО под\u00a0ключ'}
            className="font-display text-[2.9rem] font-medium leading-[0.95] tracking-[-0.015em] min-[380px]:text-[3.2rem] sm:mt-6 sm:text-7xl lg:text-[4.75rem] xl:text-[5.25rem]"
          />
          <p className="hero-rise mt-4 max-w-xl text-[17px] leading-relaxed text-neutral-600 sm:mt-7 sm:text-lg lg:mt-6" style={delay(380)}>
            <span data-hero-text>
              {nbsp('Подберу подходящую СРО, подготовлю документы и сопровожу до внесения в реестр членов.')}
            </span>
          </p>
          {/* На телефоне кнопки делят строку поровну: две кнопки разной
              ширины у левого края выглядели случайно брошенными. */}
          <div className="hero-rise mt-6 flex gap-3 sm:mt-9 sm:flex-wrap lg:mt-8" style={delay(480)}>
            <ButtonLink href="#contacts" size="lg" arrow className="flex-1 sm:flex-none">
              Связаться
            </ButtonLink>
            <ButtonLink href={LINKS.tel} variant="secondary" size="lg" className="flex-1 px-5 sm:flex-none sm:px-7">
              <Phone className="h-4 w-4" aria-hidden="true" />
              Позвонить
            </ButtonLink>
          </div>
        </div>

        <div className="hero-rise mt-6 sm:mt-12 lg:mt-auto lg:w-[56%] lg:pt-8 xl:w-[62%]" style={delay(600)}>
          <p id="hero-types" data-hero-text className="text-sm font-medium text-neutral-600">
            Выберите вид СРО
          </p>
          <ul
            aria-labelledby="hero-types"
            className="mt-2 border-b border-neutral-300 sm:mt-3"
            onMouseLeave={() => frame.show(null)}
          >
            {TYPES.map((type) => (
              <li key={type.href} className="border-t border-neutral-300">
                <a
                  href={type.href}
                  onMouseEnter={() => frame.show(type.slug)}
                  onFocus={() => frame.show(type.slug)}
                  onBlur={() => frame.show(null)}
                  className="group -mx-2 flex min-h-14 items-center gap-3 rounded-2xl px-2 py-1.5 transition-colors duration-500 ease-silk hover:bg-neutral-100 sm:gap-5 sm:py-3 lg:gap-4 lg:py-2.5"
                >
                  {type.image.thumb && (
                    <span
                      className="block h-11 w-11 shrink-0 overflow-hidden rounded-xl bg-neutral-200 sm:h-14 sm:w-14 lg:h-12 lg:w-12"
                      style={{ viewTransitionName: `sro-${type.slug}` } as CSSProperties}
                    >
                      <picture>
                        {type.image.thumbAvif && <source type="image/avif" srcSet={asset(type.image.thumbAvif)} />}
                        <img
                          src={asset(type.image.thumb)}
                          alt=""
                          width={160}
                          height={160}
                          loading="eager"
                          decoding="async"
                          className="h-full w-full object-cover transition-transform duration-700 ease-silk group-hover:scale-110"
                        />
                      </picture>
                    </span>
                  )}
                  <span className="min-w-0 flex-1">
                    <span data-hero-text className="block font-display text-[1.2rem] font-medium leading-tight min-[380px]:text-[1.3rem] sm:text-2xl">
                      {type.title}
                    </span>
                    {type.hint && (
                      <span data-hero-text className="mt-1 hidden text-sm leading-snug text-neutral-600 sm:block">
                        {type.hint}
                      </span>
                    )}
                  </span>
                  <span
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-neutral-300 text-neutral-950 transition-all duration-700 ease-silk group-hover:rotate-45 group-hover:border-neutral-950 group-hover:bg-neutral-950 group-hover:text-neutral-50 sm:h-11 sm:w-11"
                    aria-hidden="true"
                  >
                    <ArrowUpRight className="h-5 w-5" />
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
