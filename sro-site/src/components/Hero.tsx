import { ArrowUpRight, Phone } from 'lucide-react'
import { LINKS } from '../content/contacts'
import { IMAGES } from '../content/images'
import { TYPES_GROUP } from '../content/nav'
import { asset, page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { ButtonLink } from './ui/Button'

// Первый экран — «лист и окно» (с 26.09.2026): слева светлая бумага
// с заголовком, кнопками и тремя видами СРО, справа фотография во всю высоту.
//
// До этого здесь стоял слайдер: три кадра по семь секунд, и в каждый момент
// видна была треть предложения — на телефоне только «СРО строителей».
// Теперь все три вида стоят списком сразу, а кадр нужен один. Списком,
// а не карточками: тот же приём, что строки в «Документах», и тот же набор
// данных, что выпадающее меню «Виды СРО» (TYPES_GROUP) — название и подсказка
// не могут разойтись с шапкой.
//
// Рамка кадра вертикальная, как и сам снимок: он встаёт почти в родном
// размере, поэтому резче, чем был во всю ширину экрана, где из вертикального
// кадра вырезалась узкая полоса и растягивалась втрое.
//
// ТЕЛЕФОН. Первый экран обязан показать, что это, для кого и как связаться:
// заголовок, обе кнопки и все три вида — без прокрутки на 390 × 844
// (стережёт test-site.mjs). Поэтому там кадр — невысокая полоса сверху,
// подзаголовок «Для строительных, проектных…» снят (его повторяет список
// видов прямо под кнопками), а у видов — только названия: подсказки
// в две строки растягивали список за край экрана.

const TYPES = TYPES_GROUP.items.map((item, index) => ({
  number: String(index + 1).padStart(2, '0'),
  title: item.label,
  hint: item.hint,
  href: page(item.href),
}))

export function Hero() {
  const image = IMAGES.construction
  return (
    <section className="relative isolate overflow-hidden bg-neutral-50 text-neutral-950" aria-labelledby="hero-title">
      {/* Кадр: на телефоне и планшете — полоса над текстом, с 1024px — правая
          колонка во всю высоту раздела, край к краю экрана. Край жёсткий:
          растушёвка в бумагу давала серую полосу там, где тёмный кадр
          смешивался со светлым листом. */}
      <div
        className="relative h-28 overflow-hidden min-[380px]:h-32 sm:h-72 lg:absolute lg:inset-y-0 lg:left-[60%] lg:right-0 lg:h-auto"
        aria-hidden="true"
      >
        <picture>
          {image.srcAvif && <source type="image/avif" srcSet={asset(image.srcAvif)} />}
          <img
            src={asset(image.src)}
            alt=""
            width={image.width}
            height={image.height}
            loading="eager"
            decoding="async"
            className="scroll-drift h-full w-full object-cover object-[50%_30%] lg:object-[50%_18%]"
          />
        </picture>
      </div>

      <div className="mx-auto flex w-full max-w-6xl flex-col px-4 pb-10 pt-5 sm:px-6 sm:pb-14 sm:pt-10 lg:min-h-[min(860px,calc(100svh-64px))] lg:px-8 lg:pb-12 lg:pt-12">
        <div className="lg:w-[56%]">
          <p data-hero-text className="hidden items-center gap-3 text-sm text-neutral-600 sm:flex">
            <span className="h-px w-8 bg-accent-500" aria-hidden="true" />
            Для строительных, проектных и изыскательских организаций
          </p>
          <h1
            id="hero-title"
            className="font-display text-[2.9rem] font-medium leading-[0.95] tracking-[-0.015em] min-[380px]:text-[3.2rem] sm:mt-6 sm:text-7xl lg:text-[4.75rem] xl:text-[5.25rem]"
          >
            <span data-hero-text>Вступление в&nbsp;СРО под&nbsp;ключ</span>
          </h1>
          <p className="mt-4 max-w-xl text-[17px] leading-relaxed text-neutral-600 sm:mt-7 sm:text-lg lg:mt-6">
            <span data-hero-text>
              {nbsp('Подберу подходящую СРО, подготовлю документы и сопровожу до внесения в реестр членов.')}
            </span>
          </p>
          {/* На телефоне кнопки делят строку поровну: две кнопки разной
              ширины у левого края выглядели случайно брошенными. */}
          <div className="mt-6 flex gap-3 sm:mt-9 sm:flex-wrap lg:mt-8">
            <ButtonLink href="#contacts" size="lg" arrow className="flex-1 sm:flex-none">
              Связаться
            </ButtonLink>
            <ButtonLink href={LINKS.tel} variant="secondary" size="lg" className="flex-1 px-5 sm:flex-none sm:px-7">
              <Phone className="h-4 w-4" aria-hidden="true" />
              Позвонить
            </ButtonLink>
          </div>
        </div>

        <div className="mt-8 sm:mt-12 lg:mt-auto lg:w-[56%] lg:pt-8 xl:w-[58%]">
          <p id="hero-types" data-hero-text className="text-sm font-medium text-neutral-600">
            Выберите вид СРО
          </p>
          <ul aria-labelledby="hero-types" className="mt-3 border-b border-neutral-300">
            {TYPES.map((type) => (
              <li key={type.href}>
                <a
                  href={type.href}
                  className="group flex min-h-14 items-center gap-4 border-t border-neutral-300 py-3 transition-colors duration-500 ease-silk hover:border-accent-500 sm:gap-5 sm:py-4 lg:gap-4 lg:py-3.5"
                >
                  <span className="w-6 shrink-0 text-xs font-medium tabular-nums tracking-[0.16em] text-accent-600" aria-hidden="true">
                    {type.number}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span data-hero-text className="block font-display text-[1.3rem] font-medium min-[380px]:text-[1.45rem] leading-tight sm:text-2xl">
                      {type.title}
                    </span>
                    {type.hint && (
                      <span data-hero-text className="mt-1 hidden text-sm leading-snug text-neutral-600 sm:block">
                        {type.hint}
                      </span>
                    )}
                  </span>
                  <ArrowUpRight
                    className="h-5 w-5 shrink-0 text-accent-600 transition-transform duration-500 ease-silk group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                    aria-hidden="true"
                  />
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
