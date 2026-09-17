import { BadgeCheck, ChevronRight, FileSignature, Phone, ShieldCheck } from 'lucide-react'
import { LINKS } from '../content/contacts'
import { anchor, asset } from '../lib/site'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'

// Первый экран, тёмный вариант: кадр заказчика на всю ширину под плёнкой.
//
// Кадр тот же, что под квизом (quiz-bg.*): каска «СРО», кодексы, чертежи,
// стройка с краном за окном. Если заказчик выберет этот вариант, под квиз
// вернётся кадр стола (desk.*) — одна сцена не должна открывать и закрывать
// страницу, на это заказчик уже указывал.
//
// Плёнка на компьютере — градиент слева направо: под текстом плотная, справа
// прозрачнее, чтобы кран и кодексы читались. На телефоне текст занимает всю
// ширину, поэтому там плёнка ровная и плотная. Обе подобраны замером
// контраста по каждой надписи (набор hero-contrast), а не на глаз.
//
// Три довода под кнопками — те же, что были строкой в светлом варианте:
// консультация бесплатная, договор, конфиденциальность. Ничего нового не
// обещаем, только показываем заметнее.
const BG = './img/quiz-bg.webp'
const BG_AVIF = './img/quiz-bg.avif'

const POINTS = [
  { icon: BadgeCheck, text: 'Консультация бесплатная' },
  { icon: FileSignature, text: 'Работаю по договору' },
  { icon: ShieldCheck, text: 'Конфиденциально' },
]

export function HeroDark() {
  return (
    <section className="relative overflow-hidden bg-accent-950 text-white">
      <picture>
        <source srcSet={asset(BG_AVIF)} type="image/avif" />
        <img
          src={asset(BG)}
          alt=""
          aria-hidden="true"
          loading="eager"
          decoding="async"
          className="pointer-events-none absolute inset-0 h-full w-full select-none object-cover"
        />
      </picture>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-accent-950/70 lg:hidden"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 hidden bg-gradient-to-r from-accent-950 via-accent-950/85 to-accent-950/35 lg:block"
      />
      {/* Низ уходит в цвет секции: без этого кадр обрывался бы ровной
          линией по кромке и читался вставкой, а не фоном. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-accent-950 to-transparent"
      />

      <div className="relative mx-auto w-full max-w-6xl px-4 pb-16 pt-14 sm:px-6 sm:pb-24 sm:pt-20 lg:px-8 lg:pb-28 lg:pt-24">
        <Reveal className="max-w-2xl">
          <p data-hero-text className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-200">
            Строители · Проектировщики · Изыскатели
          </p>
          <h1
            data-hero-text
            className="mt-5 text-4xl font-bold leading-[1.08] tracking-tight text-white sm:text-5xl lg:text-[3.4rem]"
          >
            Вступление в СРО под&nbsp;ключ
          </h1>
          <p data-hero-text className="mt-6 max-w-xl text-lg text-neutral-200">
            Подберу подходящую СРО, подготовлю документы и сопровожу до внесения в реестр
            членов. Дистанционно, по всей России.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <ButtonLink href={anchor('#types')} variant="inverse" size="lg">
              Подобрать СРО за 1 минуту
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </ButtonLink>
            <ButtonLink href={LINKS.tel} variant="outlineInverse" size="lg">
              <Phone className="h-4 w-4" aria-hidden="true" />
              Позвонить
            </ButtonLink>
          </div>
          <ul className="mt-10 flex flex-wrap gap-2.5">
            {POINTS.map((point) => (
              <li
                key={point.text}
                data-hero-text
                className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-3.5 py-2 text-sm font-medium text-white"
              >
                <point.icon className="h-4 w-4 shrink-0 text-accent-300" aria-hidden="true" />
                {point.text}
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  )
}
