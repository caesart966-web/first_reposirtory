import { BadgeCheck, ChevronRight, FileSignature, Phone, ShieldCheck } from 'lucide-react'
import { LINKS } from '../content/contacts'
import { anchor, asset } from '../lib/site'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'

// Первый экран, дневной вариант: фотография на всю ширину, текст тёмный.
//
// Кадр — hero-day.*: ясный день, краны и стеклянные корпуса справа, слева
// чистое небо. Сгенерирован заказчиком по промпту сайта 17.09.2026 (учёт —
// public/img/CREDITS.md). Заказчик просил «не сумрачно, а нормально и
// профессионально», поэтому кадр оставлен в цвете, без фирменного дуотона:
// небо, бетон и стекло и так в палитре сайта, а дуотон вернул бы сумрак.
//
// Текст стоит на левой трети, где в кадре одно небо. Плёнка всё равно есть:
// на компьютере — белый градиент слева, чтобы стрелы кранов, заходящие в
// середину, не резали подзаголовок; на телефоне текст занимает всю ширину,
// плёнка ровная. Обе подобраны замером контраста по каждой надписи
// (hero-contrast.mjs) — с тёмным текстом ищется самый тёмный пиксель под ним.
//
// Секция намеренно невысокая (отступы 56px сверху и снизу на компьютере):
// первый экран 1440×900 должен показывать верх карточек «Видов СРО» — они
// точка входа, ради которой из героя убрали дубль квиза (проверка T7).
// С отступами 96/112 карточки начинались на 986px и уходили за экран.
//
// object-top: секция ниже кадра, и при обрезке уходит площадка с перилами
// внизу, а не оголовки кранов сверху. На телефоне кадр сдвинут вправо
// (70%): там корпуса и краны, а не пустое небо.
const BG = './img/hero-day.webp'
const BG_AVIF = './img/hero-day.avif'

const POINTS = [
  { icon: BadgeCheck, text: 'Консультация бесплатная' },
  { icon: FileSignature, text: 'Работаю по договору' },
  { icon: ShieldCheck, text: 'Конфиденциально' },
]

export function HeroPhoto() {
  return (
    <section className="relative overflow-hidden">
      <picture>
        <source srcSet={asset(BG_AVIF)} type="image/avif" />
        <img
          src={asset(BG)}
          alt=""
          aria-hidden="true"
          width={1672}
          height={941}
          loading="eager"
          decoding="async"
          className="pointer-events-none absolute inset-0 h-full w-full select-none object-cover object-[70%_0%] lg:object-[50%_0%]"
        />
      </picture>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-white/75 lg:hidden"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 hidden bg-[linear-gradient(90deg,rgba(255,255,255,0.92)_0%,rgba(255,255,255,0.82)_45%,rgba(255,255,255,0)_72%)] lg:block"
      />

      <div className="relative mx-auto w-full max-w-6xl px-4 pb-14 pt-14 sm:px-6 sm:pb-16 sm:pt-16 lg:px-8 lg:pb-14 lg:pt-14">
        <Reveal className="max-w-2xl">
          {/* Метка замера стоит на строчных элементах, а не на блоках:
              рамка блока тянется на всю ширину колонки, и замер контраста
              ловил бы стрелу крана под пустым правым краем, где букв нет. */}
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-accent-700 sm:text-xs sm:tracking-[0.18em]">
            <span data-hero-text>Строители · Проектировщики · Изыскатели</span>
          </p>
          <h1 className="mt-5 text-4xl font-bold leading-[1.08] tracking-tight text-neutral-950 sm:text-5xl lg:text-[3.4rem]">
            <span data-hero-text>
              Вступление в <span className="text-accent-600">СРО</span> под&nbsp;ключ
            </span>
          </h1>
          <p className="mt-6 max-w-xl text-lg text-neutral-700">
            <span data-hero-text>
              Для строительных, проектных и изыскательских организаций. Подберу подходящую
              СРО, подготовлю документы и сопровожу до внесения в реестр членов.
            </span>
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <ButtonLink href={anchor('#types')} size="lg">
              Подобрать СРО за 1 минуту
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </ButtonLink>
            <ButtonLink href={LINKS.tel} variant="secondary" size="lg">
              <Phone className="h-4 w-4" aria-hidden="true" />
              Позвонить
            </ButtonLink>
          </div>
          <ul className="mt-8 flex flex-wrap gap-2.5">
            {POINTS.map((point) => (
              <li
                key={point.text}
                className="inline-flex items-center gap-2 rounded-xl border border-neutral-200 bg-white/85 px-3.5 py-2 text-sm font-medium text-neutral-800 backdrop-blur-sm"
              >
                <point.icon className="h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                <span data-hero-text>{point.text}</span>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  )
}
