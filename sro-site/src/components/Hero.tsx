import { Phone } from 'lucide-react'
import { useEffect, useState, type CSSProperties } from 'react'
import { LINKS } from '../content/contacts'
import { IMAGES } from '../content/images'
import { SRO_DETAILS } from '../content/sroDetails'
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
// Теперь все три вида стоят списком сразу, а кадр нужен один. Списком,
// а не карточками, и без номеров: номера на сайте остались там, где есть
// порядок (шаги работы, опись документов), а три вида СРО — не очередь.
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
// ТЕЛЕФОН. Первый экран обязан показать, что это, для кого и как связаться:
// заголовок, обе кнопки и все три вида — без прокрутки при видимой высоте
// окна 780 px (стережёт test-site.mjs). Поэтому там кадр — невысокая полоса
// сверху, подзаголовок «Для строительных, проектных…» снят (его повторяет
// список видов прямо под кнопками), а строки плотнее: занятие и под ним
// вид СРО мелко.
// Расположение подписи одно на весь список (01.10.2026, снимок заказчика
// с телефона): до 768 px вид СРО всегда под занятием, шире — всегда справа.
// Раньше строка переносилась сама (flex-wrap), и где короткое
// «Проектирование» влезало в строку с подписью, а длинные — нет, подпись
// стояла то справа, то снизу: на 375, 412–480, 640 и 1024–1100 px.
// Справа подпись не переносится (whitespace-nowrap), переносится само
// занятие; с 1024 до 1279 px оно мельче (1,375rem) — колонка там узкая,
// и «Строительство, капремонт, снос» иначе уходило на две строки.

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

export function Hero() {
  const image = IMAGES.construction
  const frame = useHoverFrame()
  return (
    <section className="relative isolate overflow-hidden bg-neutral-50 text-neutral-950" aria-labelledby="hero-title">
      {/* Кадр: на телефоне и планшете — полоса над текстом, с 1024px — правая
          часть раздела во всю высоту, край к краю экрана; растворяется
          к тексту. Лист поверх (.hero-develop) — для «проявления». */}
      <div
        className="hero-photo relative h-28 overflow-hidden min-[380px]:h-32 sm:h-72 lg:absolute lg:inset-y-0 lg:left-[46%] lg:right-0 lg:h-auto min-[1800px]:left-[calc(50%-5.625rem)] min-[1800px]:right-[max(0px,calc(50%-56.25rem))]"
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

      <div className="mx-auto flex w-full max-w-6xl min-[1800px]:max-w-7xl flex-col px-4 pb-10 pt-5 sm:px-6 sm:pb-14 sm:pt-10 lg:min-h-[min(53.75rem,calc(100svh-4rem))] lg:px-8 lg:pb-12 lg:pt-12">
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
          <p className="hero-rise mt-4 max-w-xl text-[1.0625rem] leading-relaxed text-neutral-600 sm:mt-7 sm:text-lg lg:mt-6" style={delay(380)}>
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

        <div className="hero-rise mt-6 sm:mt-12 lg:mt-auto lg:w-[56%] lg:pt-8 xl:w-[60%]" style={delay(600)}>
          <p id="hero-types" data-hero-text className="text-sm font-medium text-neutral-600">
            Чем занимается ваша компания?
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
        </div>
      </div>
    </section>
  )
}
