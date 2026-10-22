import { ArrowLeft } from 'lucide-react'
import type { CSSProperties } from 'react'
import type { PageImage } from '../content/images'
import { fadeInFirstScreen } from '../lib/fade'
import { asset } from '../lib/site'
import { nbsp } from '../lib/typo'
import { ButtonLink } from './ui/Button'
import { RevealText } from './ui/Reveal'

// Первый экран внутренних страниц — видов СРО и услуг.
//
// Тёмный графит, заголовок антиквой, кнопка-пилюля со стрелкой. У страниц
// видов под плёнкой лежит кадр своего вида (у строителей — тот же кран, что
// на первом экране главной). До 01.10.2026 сюда при переходе с главной
// перетекала миниатюра вида из списка первого экрана; миниатюр там больше
// нет, и имя перехода снято. С 29.09.2026 кадр есть и у каждой услуги (заказчик:
// «там чёрный фон — надо фотографии»): снимки заказчика из assets-src,
// каждый под смысл страницы — scripts/prepare-service-photos.py. До того
// кадр был только у «Подготовки документов» (папки).
//
// Строка «На этой странице» (toc) — оглавление разделами-пилюлями: человек
// пришёл по стрелке с главной и сразу видит, что здесь есть и куда нажать,
// не пролистывая всю страницу. Текст пилюль помечен data-hero-text: на
// страницах видов они лежат поверх кадра, и их контраст меряет
// scripts/test-hero-contrast.mjs.
// На телефоне (до 640 px) с 01.10.2026 пилюли идут одним рядом и листаются
// вбок: в три ряда они занимали 210 px, и первый экран кончался шапкой,
// не дойдя до содержания. Ряд выходит к краям экрана — срезанная крайняя
// пилюля сама показывает, что дальше есть ещё. «Что делаю я» и «Сколько
// стоит» в оглавление не входят: эти разделы есть на каждой странице.
//
// meta — строка над заголовком у статей (15.10.2026): дата и время чтения.
// Дата стоит до заголовка нарочно: у статьи о законе первым делом важно,
// насколько она свежая.
//
// bright — плёнка тоньше (статьи, 16.10.2026, заказчик: «картинки видно
// плохо, чуть ярче»): на телефоне 0.7 вместо 0.78, на компьютере справа
// кадр открыт целиком. Контраст перемерен test-hero-contrast.mjs.
//
// Появление (20.10.2026) — CSS-анимацией при загрузке (.hero-rise и
// заголовок по словам, .hero-words), а не по прокрутке через скрипт:
// готовая разметка страницы видна раньше, чем скрипт её подхватит
// (lib/start.tsx), и шапка, ждущая скрипта, стояла бы пустой над уже
// показанным кадром. Пришли со своей страницы — без анимации (html.arrived).
export type TocItem = { id: string; title: string }

// Ступенька появления: задержка анимации .hero-rise.
const rise = (ms: number) => ({ '--d': `${ms}ms` }) as CSSProperties

export function PageHero({
  backHref,
  backLabel,
  title,
  lead,
  image,
  toc = [],
  meta,
  bright = false,
}: {
  backHref: string
  backLabel: string
  title: string
  lead: string
  image?: PageImage
  toc?: TocItem[]
  meta?: string
  bright?: boolean
}) {
  return (
    <section className="relative isolate overflow-hidden bg-accent-950 text-neutral-50">
      {image && (
        <div className="absolute inset-0 -z-10" aria-hidden="true">
          <picture>
            {image.srcAvif && <source type="image/avif" srcSet={asset(image.srcAvif)} />}
            <img
              src={asset(image.src)}
              alt=""
              width={image.width}
              height={image.height}
              loading="eager"
              // Кадр шапки — раньше скрипта и шрифтов (см. Hero.tsx, HIGH).
              {...({ fetchpriority: 'high' } as Record<string, string>)}
              decoding="async"
              ref={fadeInFirstScreen}
              className="scroll-drift h-full w-full object-cover"
              style={{ objectPosition: image.position }}
            />
          </picture>
          {/* На телефоне текст идёт во всю ширину, и плёнка ровная и плотная;
              с 1024px — сходит на нет к правому краю, где текста нет.
              Подобрано замером контраста по каждой надписи. */}
          {/* 29.09.2026 справа плёнка светлее (0.25 → 0.1): кадры услуг
              полутоновые и под прежней читались тёмным пятном. Текст стоит
              левее середины, над ним плотность прежняя; перемерено
              test-hero-contrast.mjs. */}
          {/* Классы целиком, а не склейкой: Tailwind ищет их в исходнике строкой. */}
          <div
            className={
              bright
                ? 'absolute inset-0 bg-[rgba(20,17,15,0.7)] lg:bg-[linear-gradient(90deg,rgba(20,17,15,0.88)_0%,rgba(20,17,15,0.6)_48%,rgba(20,17,15,0)_85%)]'
                : 'absolute inset-0 bg-[rgba(20,17,15,0.78)] lg:bg-[linear-gradient(90deg,rgba(20,17,15,0.9)_0%,rgba(20,17,15,0.7)_48%,rgba(20,17,15,0.1)_85%)]'
            }
          />
          <div
            className={
              bright
                ? 'absolute inset-x-0 bottom-0 h-1/2 bg-[linear-gradient(0deg,rgba(20,17,15,0.75)_0%,rgba(20,17,15,0)_100%)]'
                : 'absolute inset-x-0 bottom-0 h-1/2 bg-[linear-gradient(0deg,rgba(20,17,15,0.85)_0%,rgba(20,17,15,0)_100%)]'
            }
          />
          {/* Проявление кадра (20.10.2026), как на главной: на первом заходе
              кадр проступает из графита раздела, пока поднимается заголовок.
              Пришли со своей страницы или «уменьшить движение» — листа нет
              (index.css, .hero-develop). Кадр под ним показывается сам, как
              только загрузится (lib/fade.ts, fadeInFirstScreen). */}
          <span className="hero-develop absolute inset-0 bg-accent-950" aria-hidden="true" />
        </div>
      )}
      <div className="mx-auto w-full max-w-6xl min-[1800px]:max-w-7xl px-4 pb-20 pt-14 sm:px-6 sm:pb-28 sm:pt-20 lg:px-8">
        <div className="hero-rise" style={rise(0)}>
          {/* Высота ссылки 44 px — под палец (22.10.2026: было 20 px), а место
              в шапке прежнее: отрицательные поля сверху и снизу съедают прибавку. */}
          <a
            href={backHref}
            className="-my-3 inline-flex min-h-11 items-center gap-2 text-sm text-neutral-300 transition-colors duration-500 hover:text-neutral-50"
          >
            <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden="true" />
            {backLabel}
          </a>
        </div>
        <div className="max-w-3xl">
          {/* Кегль на телефоне — по самому длинному слову заголовков:
              «проектировщиков», «ответственности». На 2,9rem они были шире
              экрана и обрезались краем шапки (до 28.09.2026 — незаметно:
              горизонтальной прокрутки при этом нет). */}
          {meta && (
            <div className="hero-rise" style={rise(60)}>
              <p className="mt-10 text-sm text-neutral-200">
                <span data-hero-text>{meta}</span>
              </p>
            </div>
          )}
          <RevealText
            as="h1"
            intro
            delay={80}
            text={title}
            className={`font-display text-[1.95rem] font-medium tracking-[-0.01em] ${
              // Заголовок статьи — вопрос в пять-восемь слов: кеглем страниц
              // услуг он вставал в четыре строки на полэкрана.
              meta
                ? 'mt-4 leading-[1.06] min-[380px]:text-[2.15rem] sm:text-5xl lg:text-[3.6rem]'
                : 'mt-10 leading-[1.02] min-[380px]:text-[2.35rem] sm:text-6xl lg:text-[4.6rem]'
            }`}
          />
          <div className="hero-rise" style={rise(200)}>
            <p className="mt-7 max-w-2xl text-lg leading-relaxed text-neutral-200">
              <span data-hero-text>{nbsp(lead)}</span>
            </p>
            <ButtonLink href="#contacts" variant="inverse" size="lg" arrow className="mt-9">
              Обсудить задачу
            </ButtonLink>
          </div>
        </div>
        {toc.length > 0 && (
          <div className="hero-rise" style={rise(320)}>
            <nav aria-label="На этой странице" className="mt-10 border-t border-white/15 pt-6 sm:mt-14">
              <p className="text-sm text-neutral-300">
                <span data-hero-text>На этой странице</span>
              </p>
              <ul className="-mx-4 mt-4 flex gap-2 overflow-x-auto px-4 [scrollbar-width:none] sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0 [&::-webkit-scrollbar]:hidden">
                {toc.map((item) => (
                  <li key={item.id} className="shrink-0">
                    <a
                      href={`#${item.id}`}
                      className="inline-flex min-h-11 items-center whitespace-nowrap rounded-full border border-white/25 bg-accent-950/40 px-4 text-sm text-neutral-100 transition-colors duration-500 ease-silk hover:border-white/70 hover:text-neutral-50"
                    >
                      <span data-hero-text>{item.title}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
        )}
      </div>
    </section>
  )
}
