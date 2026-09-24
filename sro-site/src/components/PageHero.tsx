import { ArrowLeft } from 'lucide-react'
import type { PageImage } from '../content/images'
import { asset } from '../lib/site'
import { ButtonLink } from './ui/Button'
import { Reveal, RevealText } from './ui/Reveal'

// Первый экран внутренних страниц — видов СРО и услуг.
//
// Тот же язык, что у слайдера на главной: тёмный графит, заголовок антиквой,
// кнопка-пилюля со стрелкой. У страниц видов под плёнкой лежит кадр своего
// вида — тот же, что на слайде главной, откуда человек сюда пришёл. У услуг
// кадра нет: их семь, а кадров по теме нет, и выдумывать иллюстрацию к
// «уровню ответственности» значило бы ставить случайную картинку.
export function PageHero({
  backHref,
  backLabel,
  title,
  lead,
  image,
}: {
  backHref: string
  backLabel: string
  title: string
  lead: string
  image?: PageImage
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
              decoding="async"
              className="h-full w-full object-cover"
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
          <RevealText
            as="h1"
            text={title}
            className="mt-10 font-display text-[2.9rem] font-medium leading-[1] tracking-[-0.01em] sm:text-6xl lg:text-[4.6rem]"
          />
          <Reveal delay={200}>
            <p className="mt-7 max-w-2xl text-lg leading-relaxed text-neutral-200">
              <span data-hero-text>{lead}</span>
            </p>
            <ButtonLink href="#contacts" variant="inverse" size="lg" arrow className="mt-9">
              Обсудить задачу
            </ButtonLink>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
