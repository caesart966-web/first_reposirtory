import { BadgeCheck, ChevronRight, FileSignature, Phone, ShieldCheck } from 'lucide-react'
import { LINKS } from '../content/contacts'
import { anchor, asset } from '../lib/site'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'

// Первый экран, тёмный вариант: стройка в стиле чертежа на всю ширину.
//
// Фон — собственный рисунок (public/img/skyline.svg, собирается
// scripts/make-skyline.py): силуэты зданий, башенные краны, каркас
// недостроя тонкими светлыми линиями на фирменном синем. Сначала здесь
// стоял кадр заказчика с каской и кодексами — тот же, что под квизом, — и
// заказчик попросил другую картинку, чтобы сцена не повторялась. Новую
// фотографию взять неоткуда (сеть закрыта, выдумывать источник нельзя),
// поэтому рисунок: он только наш, и вопрос прав не возникает.
//
// Рисунок 1920×1000 и прижат к низу (object-bottom): при обрезке под высоту
// секции уходит небо, а не здания с землёй. Плёнка на компьютере — градиент
// слева направо, под текстом плотная, справа почти нет — там краны и
// недострой видны целиком. На телефоне текст на всю ширину, плёнка ровная.
// Обе подобраны замером контраста по каждой надписи (hero-contrast.mjs).
//
// Три довода под кнопками — те же, что были строкой в светлом варианте:
// консультация бесплатная, договор, конфиденциальность. Ничего нового не
// обещаем, только показываем заметнее.
const BG = './img/skyline.svg'

const POINTS = [
  { icon: BadgeCheck, text: 'Консультация бесплатная' },
  { icon: FileSignature, text: 'Работаю по договору' },
  { icon: ShieldCheck, text: 'Конфиденциально' },
]

export function HeroDark() {
  return (
    <section className="relative overflow-hidden bg-accent-950 text-white">
      <img
        src={asset(BG)}
        alt=""
        aria-hidden="true"
        width={1920}
        height={1000}
        loading="eager"
        decoding="async"
        className="pointer-events-none absolute inset-0 h-full w-full select-none object-cover object-bottom"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-accent-950/70 lg:hidden"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 hidden bg-[linear-gradient(90deg,#141A45_0%,rgba(20,26,69,0.86)_45%,rgba(20,26,69,0)_100%)] lg:block"
      />

      <div className="relative mx-auto w-full max-w-6xl px-4 pb-14 pt-14 sm:px-6 sm:pb-20 sm:pt-20 lg:px-8 lg:pb-24 lg:pt-24">
        <Reveal className="max-w-2xl">
          <p data-hero-text className="text-[11px] font-semibold uppercase tracking-[0.12em] text-accent-200 sm:text-xs sm:tracking-[0.18em]">
            Строители · Проектировщики · Изыскатели
          </p>
          <h1
            data-hero-text
            className="mt-5 text-4xl font-bold leading-[1.08] tracking-tight text-white sm:text-5xl lg:text-[3.4rem]"
          >
            Вступление в СРО под&nbsp;ключ
          </h1>
          <p data-hero-text className="mt-6 max-w-xl text-lg text-neutral-200">
            Для строительных, проектных и изыскательских организаций. Подберу подходящую СРО,
            подготовлю документы и сопровожу до внесения в реестр членов.
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
