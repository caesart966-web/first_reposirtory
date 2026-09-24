import type { ReactNode } from 'react'
import { Reveal, RevealText } from './Reveal'

// Ритм страницы: ключевые секции дышат шире, вторичные — компактнее.
// Отступы крупнее прежних: в новом оформлении воздух — главный инструмент,
// как у Apple, а не рамки и тени.
const PADDING = {
  key: 'py-24 sm:py-32',
  default: 'py-20 sm:py-28',
  compact: 'py-16 sm:py-20',
}

export function Section({
  id,
  className = '',
  size = 'default',
  children,
}: {
  id?: string
  className?: string
  size?: keyof typeof PADDING
  children: ReactNode
}) {
  return (
    <section id={id} className={`${PADDING[size]} ${className}`}>
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">{children}</div>
    </section>
  )
}

// Заголовок раздела.
//
// Раньше: подпись капсом с разрядкой, заголовок и подзаголовок — всё по
// центру. Именно этот набор читается «сделано нейросетью»: он стоял над
// каждым из двенадцати разделов одинаково. Теперь заголовок антиквой по
// левому краю, крупно, поднимается по словам; подпись над ним — обычным
// регистром с короткой латунной чертой, как рубрика в журнале.
//
// Подзаголовок на широком экране уходит вправо от заголовка, в свою
// колонку: так раздел начинается одной строкой, а не столбиком из трёх.
export function SectionHeading({
  eyebrow,
  title,
  subtitle,
  dark = false,
}: {
  eyebrow?: string
  title: string
  subtitle?: string
  dark?: boolean
}) {
  // Без подзаголовка колонок нет: иначе заголовок в узкой колонке раздела
  // (документы, «О нас») делил её ещё раз и рассыпался на шесть строк.
  return (
    <div
      className={
        subtitle ? 'grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)] lg:items-end lg:gap-16' : ''
      }
    >
      <div>
        {eyebrow && (
          <Reveal>
            <p
              className={`flex items-center gap-3 text-sm ${
                dark ? 'text-neutral-300' : 'text-neutral-600'
              }`}
            >
              <span
                className={`h-px w-8 ${dark ? 'bg-accent-300' : 'bg-accent-500'}`}
                aria-hidden="true"
              />
              {eyebrow}
            </p>
          </Reveal>
        )}
        <RevealText
          text={title}
          className={`mt-4 font-display text-[2.6rem] font-medium leading-[1.02] tracking-[-0.01em] sm:text-5xl lg:text-[3.6rem] ${
            dark ? 'text-neutral-50' : 'text-neutral-950'
          }`}
        />
      </div>
      {subtitle && (
        <Reveal delay={150}>
          <p className={`text-base leading-relaxed sm:text-lg ${dark ? 'text-neutral-300' : 'text-neutral-600'}`}>
            {subtitle}
          </p>
        </Reveal>
      )}
    </div>
  )
}
