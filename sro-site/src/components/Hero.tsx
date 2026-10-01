import { ArrowRight, DraftingCompass, HardHat, Mountain } from 'lucide-react'
import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { IMAGES } from '../content/images'
import { SRO_DETAILS } from '../content/sroDetails'
import { fadeIn } from '../lib/fade'
import { asset, page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { ButtonLink } from './ui/Button'
import { GoTo } from './ui/GoTo'
import { RevealText } from './ui/Reveal'

// Первый экран — «лист и окно» (с 26.09.2026): слева светлая бумага
// с заголовком, кнопками и тремя видами СРО, справа кадр с краном во всю
// высоту раздела.
//
// До этого здесь стоял слайдер: три кадра по семь секунд, и в каждый момент
// видна была треть предложения — на телефоне только «СРО строителей».
// Теперь все три вида стоят списком сразу, а кадр нужен один. Без номеров:
// номера на сайте остались там, где есть порядок (шаги работы, опись
// документов), а три вида СРО — не очередь. На компьютере — строками,
// на телефоне и планшете с 01.10.2026 — карточками (см. «Телефон и планшет»).
// Название вида и адрес — из SRO_DETAILS, тех же данных, что страницы видов
// и меню «Виды СРО»: разойтись с шапкой они не могут.
//
// Кадр — в тёплом монохроме, как все фотографии сайта, и снят «светлым
// ключом»: небо уходит в бумагу, поэтому кадр растворяется в листе без рамки
// и без серой полосы (маска .hero-photo в index.css). При загрузке он
// «проявляется», как отпечаток, текст выплывает ступенькой (.hero-rise, --d).
//
// ВЫБОР ВИДА — «от задачи клиента» (01.10.2026, вариант В из трёх, выбор
// заказчика). Над списком вопрос «Чем занимается ваша компания?», строка —
// занятие словами клиента («Строительство, капремонт, снос»), вид СРО —
// подписью справа со стрелкой. Человек знает, чем занимается, но не всегда
// знает, какая СРО ему нужна: переводить «я строю» в «СРО строителей» ему
// больше не надо. «Капремонт», а не «ремонт»: для текущего ремонта членство
// не требуется, и слово «ремонт» обещало бы лишнее.
// До этого у строки были миниатюра кадра 48 px и кружок со стрелкой:
// миниатюра в монохроме не читалась, а три кружка спорили с кружком
// кнопки «Связаться» (правило кружков — ui/GoTo.tsx).
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
// ТЕЛЕФОН И ПЛАНШЕТ (до 1024 px) — «обложка» (01.10.2026, заказчик: «красивее
// и профессиональнее», из трёх вариантов выбран этот). Заголовок стоит белым
// на кадре, под ним — затемнение снизу вверх (COVER_SHADE), ниже на бумаге
// строка, кнопки и три вида СРО карточками (TypeCards): значок, занятие,
// вид СРО мелко. Нажатие на карточку меняет кадр обложки на кадр этого вида
// (заказчик: «чтобы и там картинка менялась, когда кликаешь на тип СРО»),
// выбранная карточка выделена и показывает «Открыть →» — второе нажатие
// ведёт на страницу вида. Сразу выбрано строительство: на первом кадре кран.
// Списком строками остаётся компьютер — там кадр меняется наведением.
// Первый экран обязан показать, что это, для кого и как связаться:
// заголовок, обе кнопки и все три вида — без прокрутки при видимой высоте
// окна 780 px (стережёт test-site.mjs). Поэтому подзаголовок «Для
// строительных, проектных…» на телефоне снят (его повторяют карточки видов),
// а высота обложки подобрана под это окно.
// Строки компьютера (с 1024 px): подпись вида СРО у всех трёх справа
// и не переносится (whitespace-nowrap). Раньше строка переносилась сама
// (flex-wrap), и подпись стояла то справа, то снизу (01.10.2026, снимок
// заказчика). С 1024 до 1279 px занятие мельче (1,375rem) — колонка там
// узкая, и «Строительство, капремонт, снос» иначе уходило на две строки.

// Ступенька появления: задержка анимации .hero-rise.
const delay = (ms: number) => ({ '--d': `${ms}ms` }) as CSSProperties

// Занятие словами клиента — по виду СРО. Короче подсказки из меню
// «Виды СРО»: строка первого экрана должна уложиться в одну строку
// на телефоне.
const ACTIVITY: Record<string, string> = {
  construction: 'Строительство, капремонт, снос',
  design: 'Проектирование',
  survey: 'Инженерные изыскания',
}

const TYPES = SRO_DETAILS.map((detail) => ({
  slug: detail.slug,
  title: detail.card.title,
  activity: ACTIVITY[detail.slug] ?? detail.card.title,
  href: page(detail.path),
  image: detail.card.image,
}))

// Какую часть кадра показывать в окне первого экрана. Окно на компьютере
// почти квадратное, все три кадра вертикальные: у крана — башня, у плана —
// середина листа, у геодезиста — прибор и руки, а не земля под штативом. Классы записаны целиком: Tailwind
// собирает только те, что видит в исходнике.
const FRAME: Record<string, string> = {
  construction: 'object-[50%_30%] lg:object-[50%_18%]',
  design: 'object-[50%_45%] lg:object-[50%_40%]',
  survey: 'object-[50%_30%] lg:object-[50%_28%]',
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

// Значки видов СРО в карточках телефона.
const TYPE_ICON: Record<string, typeof HardHat> = {
  construction: HardHat,
  design: DraftingCompass,
  survey: Mountain,
}

// Какую часть кадра показывать в обложке телефона: она широкая и невысокая.
const COVER_FRAME: Record<string, string> = {
  construction: 'object-[60%_30%]',
  design: 'object-[50%_45%]',
  survey: 'object-[50%_30%]',
}

// Затемнение обложки снизу вверх. Белый заголовок обязан держать 4,5:1
// над самым светлым местом кадра (кадры сняты светлым ключом, у плана
// этажа светлый почти весь лист), поэтому под строками заголовка тон
// не светлее ~55 %. Меряет по пикселям scripts/test-hero-contrast.mjs.
const COVER_SHADE =
  'bg-[linear-gradient(to_top,rgba(20,17,15,0.94)_0%,rgba(20,17,15,0.82)_38%,rgba(20,17,15,0.5)_66%,rgba(20,17,15,0.08)_100%)]'

// Кадры обложки. Кран — сразу; два других кадра телефон грузит после
// загрузки страницы, когда браузер свободен, чтобы смена по нажатию шла
// без ожидания; нажали раньше — грузится сразу. На компьютере обложки нет,
// и лишние кадры туда не грузятся.
//
// Смена кадра без рывка (01.10.2026, заказчик: «немного подёргивает»):
// 1) новый кадр проступает ПОВЕРХ прежнего, а прежний держится под ним
//    до конца и гаснет уже невидимо. Раньше гасли оба сразу: на середине
//    оба были полупрозрачны, сквозь них проступал тёмный фон — мигание;
// 2) смена начинается, только когда кадр раскодирован (img.decode()) —
//    иначе он проявлялся рывком посреди перехода;
// 3) слои кадров заведены заранее (will-change), а не в первый кадр смены.
const COVER_FADE = '[transition:opacity_0.9s_cubic-bezier(0.22,1,0.36,1),transform_1.6s_cubic-bezier(0.22,1,0.36,1)]'

function CoverPhotos({ active }: { active: string }) {
  const [all, setAll] = useState(false)
  const [shown, setShown] = useState(active)
  const [under, setUnder] = useState<string | null>(null)
  const shownRef = useRef(active)
  const imgs = useRef<Record<string, HTMLImageElement | null>>({})
  useEffect(() => {
    if (!matchMedia('(max-width: 1023px)').matches) return
    let handle = 0
    const start = () => {
      handle = idle
        ? requestIdleCallback(() => setAll(true), { timeout: 3000 })
        : window.setTimeout(() => setAll(true), 1200)
    }
    if (document.readyState === 'complete') start()
    else addEventListener('load', start, { once: true })
    return () => {
      removeEventListener('load', start)
      if (idle) cancelIdleCallback(handle)
      else clearTimeout(handle)
    }
  }, [])
  useEffect(() => {
    if (active === shownRef.current) return
    let cancelled = false
    const img = imgs.current[active]
    const loaded = !img
      ? Promise.resolve()
      : img.complete
        ? Promise.resolve()
        : new Promise((done) => {
            img.addEventListener('load', done, { once: true })
            img.addEventListener('error', done, { once: true })
          })
    loaded
      .then(() => img?.decode())
      .catch(() => {})
      .then(() => {
        if (cancelled) return
        setUnder(shownRef.current)
        shownRef.current = active
        setShown(active)
      })
    return () => {
      cancelled = true
    }
  }, [active])
  // Прежний кадр убирается из-под нового, когда тот проступил целиком.
  useEffect(() => {
    if (!under) return
    const t = window.setTimeout(() => setUnder(null), 1000)
    return () => clearTimeout(t)
  }, [under, shown])
  return (
    // isolate — порядок слоёв (z-[1], z-[2]) живёт внутри обложки: без него
    // при «уменьшить движение» (нет анимации .hero-print, нет и своего
    // контекста наложения) кадр ложился поверх затемнения и заголовка.
    // Фон под кадрами тёмный: пока кадр грузится, белый заголовок стоит
    // на графите, а не на бумаге (lib/fade.ts — кадр проступает поверх).
    <div className="hero-print absolute inset-0 isolate bg-neutral-900 lg:hidden" aria-hidden="true">
      {TYPES.map((type) =>
        type.slug === 'construction' || all || active === type.slug ? (
          <picture
            key={type.slug}
            data-shown={shown === type.slug ? '' : undefined}
            className={`absolute inset-0 [will-change:opacity,transform] ${COVER_FADE} ${
              shown === type.slug
                ? 'z-[2] opacity-100'
                : under === type.slug
                  ? 'z-[1] opacity-100'
                  : 'z-0 opacity-0 motion-safe:scale-[1.05]'
            }`}
          >
            {type.image.srcAvif && <source type="image/avif" srcSet={asset(type.image.srcAvif)} />}
            <img
              ref={(el) => {
                imgs.current[type.slug] = el
                fadeIn(el)
              }}
              src={asset(type.image.src)}
              alt=""
              width={type.image.width}
              height={type.image.height}
              loading="eager"
              decoding="async"
              className={`h-full w-full object-cover ${COVER_FRAME[type.slug] ?? ''}`}
            />
          </picture>
        ) : null,
      )}
    </div>
  )
}

// Три вида СРО карточками — телефон и планшет. Кружка со стрелкой
// здесь нет нарочно: он только у кнопок «Связаться» (ui/GoTo.tsx).
//
// Каждая карточка — ссылка на страницу своего вида, и элемент не меняется
// при выборе. До 01.10.2026 выбранная была ссылкой, остальные — кнопками,
// и при нажатии React пересоздавал обе карточки: рамка, тень и «Открыть»
// возникали скачком, без перехода (заказчик: «подёргивает»). Теперь
// касание невыбранной карточки меняет кадр (переход отменяется), касание
// выбранной ведёт на страницу. Enter с клавиатуры (detail 0) и щелчок
// с Ctrl/Shift ведут сразу: кадр — украшение (aria-hidden), экранному
// диктору и клавиатуре показывать нечего.
function TypeCards({ active, onSelect }: { active: string; onSelect: (slug: string) => void }) {
  return (
    <ul aria-labelledby="hero-types" data-hero-cards className="mt-2.5 grid gap-2 sm:max-w-xl lg:hidden">
      {TYPES.map((type) => {
        const Icon = TYPE_ICON[type.slug] ?? HardHat
        const on = active === type.slug
        return (
          <li key={type.href}>
            <a
              href={type.href}
              data-selected={on ? '' : undefined}
              onClick={(e) => {
                if (on || e.detail === 0 || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
                e.preventDefault()
                onSelect(type.slug)
              }}
              className={`flex w-full touch-manipulation select-none items-center gap-3 rounded-2xl border py-2.5 pl-2.5 pr-3 text-left [-webkit-tap-highlight-color:transparent] max-[359px]:gap-2.5 max-[359px]:pl-2 max-[359px]:pr-2.5 transition-[border-color,box-shadow,background-color,transform] duration-500 ease-silk motion-safe:active:scale-[0.985] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-50 ${
                on
                  ? 'border-accent-500 bg-white shadow-[0_6px_18px_-8px_rgba(107,76,38,0.35),0_0_0_1px_theme(colors.accent.500)]'
                  : 'border-neutral-200 bg-white/80 shadow-[0_1px_2px_rgba(20,17,15,0.05),0_0_0_1px_transparent]'
              }`}
            >
              <span
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ring-1 ring-inset transition-[background-color,color,box-shadow] duration-500 ease-silk max-[359px]:h-9 max-[359px]:w-9 ${
                  on ? 'bg-accent-600 text-neutral-50 ring-accent-600' : 'bg-accent-50 text-accent-700 ring-accent-200/70'
                }`}
              >
                <Icon className="h-5 w-5" strokeWidth={1.6} aria-hidden="true" />
              </span>
              {/* «Открыть →» — во второй строке, рядом с видом СРО: справа
                  от занятия оно отнимало ширину, и «Строительство, капремонт,
                  снос» у выбранной карточки уходило на две строки. Оно стоит
                  у каждой карточки и проступает у выбранной: место под него
                  занято всегда, строки при выборе не сдвигаются. Стрелки «>»
                  у невыбранных карточек нет: первое касание не ведёт на
                  страницу, а меняет кадр. Уже 360 px значок и поля карточки
                  чуть меньше, занятие 13,5 px, вторая строка 12 px — иначе
                  на 320 px строки не помещались. */}
              <span className="min-w-0 flex-1">
                <span className="block text-[0.9375rem] font-semibold leading-snug text-neutral-950 max-[359px]:text-[0.84375rem] min-[380px]:text-base">
                  {type.activity}
                </span>
                <span className="flex items-center justify-between gap-3 text-[0.8125rem] leading-snug max-[359px]:gap-2 max-[359px]:text-xs">
                  <span className="text-neutral-600">{type.title}</span>
                  <span
                    className={`flex shrink-0 items-center gap-1 font-semibold text-accent-700 transition-[opacity,transform] duration-500 ease-silk ${
                      on ? 'opacity-100' : 'opacity-0 motion-safe:-translate-x-1.5'
                    }`}
                    aria-hidden="true"
                  >
                    Открыть
                    <ArrowRight className="h-4 w-4" />
                  </span>
                </span>
              </span>
            </a>
          </li>
        )
      })}
    </ul>
  )
}

export function Hero() {
  const image = IMAGES.construction
  const frame = useHoverFrame()
  const [active, setActive] = useState('construction')
  return (
    <section className="relative isolate overflow-hidden bg-neutral-50 text-neutral-950" aria-labelledby="hero-title">
      {/* Кадр компьютера (с 1024 px): правая часть раздела во всю высоту,
          край к краю экрана; растворяется к тексту. Лист поверх
          (.hero-develop) — для «проявления». На телефоне и планшете кадр —
          обложка под заголовком (CoverPhotos ниже). */}
      <div
        className="hero-photo relative hidden overflow-hidden lg:absolute lg:block lg:inset-y-0 lg:left-[46%] lg:right-0 lg:h-auto min-[1800px]:left-[calc(50%-5.625rem)] min-[1800px]:right-[max(0px,calc(50%-56.25rem))]"
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
            ref={fadeIn}
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

      <div className="mx-auto flex w-full max-w-6xl min-[1800px]:max-w-7xl flex-col px-4 pb-10 pt-5 sm:px-6 sm:pb-14 sm:pt-10 lg:min-h-[min(53.75rem,calc(100svh-4rem))] lg:px-8 lg:pb-12 lg:pt-12">
        <div className="lg:w-[56%]">
          <p data-hero-text className="hero-rise hidden items-center gap-3 text-sm text-neutral-600 lg:flex" style={delay(0)}>
            <span className="h-px w-8 bg-accent-500" aria-hidden="true" />
            Для строительных, проектных и изыскательских организаций
          </p>
          {/* Обложка телефона и планшета: кадр во всю ширину, затемнение
              и заголовок белым поверх. С 1024 px обёртка исчезает
              (lg:contents) — заголовок снова обычный, на бумаге. */}
          <div className="relative -mx-4 -mt-5 overflow-hidden px-4 pb-6 pt-[8rem] text-neutral-50 min-[380px]:pt-[9rem] sm:-mx-6 sm:-mt-10 sm:px-6 sm:pb-8 sm:pt-[15rem] lg:contents lg:text-neutral-950">
            <CoverPhotos active={active} />
            <span className={`absolute inset-0 lg:hidden ${COVER_SHADE}`} aria-hidden="true" />
            <span className="hero-develop absolute inset-0 bg-neutral-950 lg:hidden" aria-hidden="true" />
            <RevealText
              as="h1"
              id="hero-title"
              text={'Вступление в СРО под\u00a0ключ'}
              className="relative font-display text-[2.6rem] font-medium leading-[0.95] tracking-[-0.015em] min-[380px]:text-[2.85rem] sm:text-7xl lg:mt-6 lg:text-[4.75rem] xl:text-[5.25rem]"
            />
          </div>
          <p className="hero-rise mt-5 max-w-xl text-[1.0625rem] leading-relaxed text-neutral-600 sm:mt-7 sm:text-lg lg:mt-6" style={delay(380)}>
            <span data-hero-text>
              {nbsp('Подберу подходящую СРО, подготовлю документы и сопровожу до внесения в реестр членов.')}
            </span>
          </p>
          {/* Кнопка одна — «Связаться» (01.10.2026, заказчик: «лишние,
              повторяющиеся элементы»). «Позвонить» повторяла значок телефона
              в шапке, который виден на любой ширине, а «Связаться» ведёт
              ко всем способам сразу: номер, мессенджеры, почта. На телефоне
              кнопка во всю строку — под большой палец. */}
          <div className="hero-rise mt-6 flex sm:mt-9 lg:mt-8" style={delay(480)}>
            <ButtonLink href="#contacts" size="lg" arrow className="flex-1 sm:flex-none">
              Связаться
            </ButtonLink>
          </div>
        </div>

        <div className="hero-rise mt-6 sm:mt-12 lg:mt-auto lg:w-[56%] lg:pt-8 xl:w-[60%]" style={delay(600)}>
          <p id="hero-types" data-hero-text className="text-sm font-medium text-neutral-600">
            Чем занимается ваша компания?
          </p>
          <ul
            aria-labelledby="hero-types"
            className="mt-3 hidden border-b border-neutral-300 lg:block"
            onMouseLeave={() => frame.show(null)}
          >
            {TYPES.map((type) => (
              <li key={type.href} className="border-t border-neutral-300">
                <a
                  href={type.href}
                  onMouseEnter={() => frame.show(type.slug)}
                  onFocus={() => frame.show(type.slug)}
                  onBlur={() => frame.show(null)}
                  className="group flex min-h-14 flex-col justify-center gap-0.5 py-1.5 focus-visible:outline-none sm:py-4 md:flex-row md:items-baseline md:justify-between md:gap-6"
                >
                  <span
                    data-hero-text
                    className="min-w-0 font-display text-[1.1rem] font-medium leading-tight min-[380px]:text-[1.25rem] sm:text-[1.75rem] lg:text-[1.375rem] xl:text-[1.75rem]"
                  >
                    {type.activity}
                  </span>
                  <GoTo tone="muted" className="shrink-0 whitespace-nowrap text-[0.8125rem] leading-snug sm:text-[0.9375rem] sm:leading-normal">
                    <span data-hero-text>{type.title}</span>
                  </GoTo>
                </a>
              </li>
            ))}
          </ul>
          <TypeCards active={active} onSelect={setActive} />
        </div>
      </div>
    </section>
  )
}
