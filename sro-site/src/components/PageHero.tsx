import { ArrowLeft } from 'lucide-react'
import type { CSSProperties } from 'react'
import type { PageImage } from '../content/images'
import { asset } from '../lib/site'
import { nbsp } from '../lib/typo'
import { ButtonLink } from './ui/Button'
import { Reveal, RevealText } from './ui/Reveal'

// Первый экран внутренних страниц — видов СРО и услуг.
//
// Тёмный графит, заголовок антиквой, кнопка-пилюля со стрелкой. У страниц
// видов под плёнкой лежит кадр своего вида (у строителей — тот же кран, что
// на первом экране главной). При переходе с главной сюда перетекает миниатюра
// вида из списка первого экрана: у обоих одно имя перехода (transitionName,
// «sro-<вид>»). У услуг кадр только там, где есть предмет, который
// можно снять: папки у «Подготовки документов». Выдумывать иллюстрацию
// к «уровню ответственности» значило бы ставить случайную картинку.
//
// Строка «На этой странице» (toc) — оглавление разделами-пилюлями: человек
// пришёл по стрелке с главной и сразу видит, что здесь есть и куда нажать,
// не пролистывая всю страницу. Текст пилюль помечен data-hero-text: на
// страницах видов они лежат поверх кадра, и их контраст меряет
// scripts/test-hero-contrast.mjs.
export type TocItem = { id: string; title: string }

export function PageHero({
  backHref,
  backLabel,
  title,
  lead,
  image,
  transitionName,
  toc = [],
}: {
  backHref: string
  backLabel: string
  title: string
  lead: string
  image?: PageImage
  /** Имя для плавного перехода между страницами (view-transition-name). */
  transitionName?: string
  toc?: TocItem[]
}) {
  return (
    <section className="relative isolate overflow-hidden bg-accent-950 text-neutral-50">
      {image && (
        <div
          className="absolute inset-0 -z-10"
          style={transitionName ? ({ viewTransitionName: transitionName } as CSSProperties) : undefined}
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
              className="scroll-drift h-full w-full object-cover"
              style={{ objectPosition: image.position }}
            />
          </picture>
          {/* На телефоне текст идёт во всю ширину, и плёнка ровная и плотная;
              с 1024px — сходит на нет к правому краю, где текста нет.
              Подобрано замером контраста по каждой надписи. */}
          <div className="absolute inset-0 bg-[rgba(20,17,15,0.78)] lg:bg-[linear-gradient(90deg,rgba(20,17,15,0.9)_0%,rgba(20,17,15,0.7)_48%,rgba(20,17,15,0.25)_85%)]" />
          <div className="absolute inset-x-0 bottom-0 h-1/2 bg-[linear-gradient(0deg,rgba(20,17,15,0.85)_0%,rgba(20,17,15,0)_100%)]" />
        </div>
      )}
      <div className="mx-auto w-full max-w-6xl px-4 pb-20 pt-14 sm:px-6 sm:pb-28 sm:pt-20 lg:px-8">
        <Reveal>
          <a
            href={backHref}
            className="inline-flex items-center gap-2 text-sm text-neutral-300 transition-colors duration-500 hover:text-neutral-50"
          >
            <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden="true" />
            {backLabel}
          </a>
        </Reveal>
        <div className="max-w-3xl">
          {/* Кегль на телефоне — по самому длинному слову заголовков:
              «проектировщиков», «ответственности». На 2,9rem они были шире
              экрана и обрезались краем шапки (до 28.09.2026 — незаметно:
              горизонтальной прокрутки при этом нет). */}
          <RevealText
            as="h1"
            text={title}
            className="mt-10 font-display text-[1.95rem] font-medium leading-[1.02] tracking-[-0.01em] min-[380px]:text-[2.35rem] sm:text-6xl lg:text-[4.6rem]"
          />
          <Reveal delay={200}>
            <p className="mt-7 max-w-2xl text-lg leading-relaxed text-neutral-200">
              <span data-hero-text>{nbsp(lead)}</span>
            </p>
            <ButtonLink href="#contacts" variant="inverse" size="lg" arrow className="mt-9">
              Обсудить задачу
            </ButtonLink>
          </Reveal>
        </div>
        {toc.length > 0 && (
          <Reveal delay={320}>
            <nav aria-label="На этой странице" className="mt-14 border-t border-white/15 pt-6">
              <p className="text-sm text-neutral-300">
                <span data-hero-text>На этой странице</span>
              </p>
              <ul className="mt-4 flex flex-wrap gap-2">
                {toc.map((item) => (
                  <li key={item.id}>
                    <a
                      href={`#${item.id}`}
                      className="inline-flex min-h-11 items-center rounded-full border border-white/25 bg-accent-950/40 px-4 text-sm text-neutral-100 transition-colors duration-500 ease-silk hover:border-white/70 hover:text-neutral-50"
                    >
                      <span data-hero-text>{item.title}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </Reveal>
        )}
      </div>
    </section>
  )
}
