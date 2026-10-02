import type { ReactNode } from 'react'
import { nbsp } from '../../lib/typo'
import { Reveal, RevealText } from './Reveal'

// Ритм страницы: ключевые секции дышат шире, вторичные — компактнее.
// Отступы крупнее прежних: в новом оформлении воздух — главный инструмент,
// как у Apple, а не рамки и тени.
// На телефоне на ступень плотнее (30.09.2026): 80 px сверху и снизу
// у каждого раздела давали 160 px пустоты на каждом стыке, и главная
// тянулась почти на девятнадцать экранов.
const PADDING = {
  key: 'py-20 sm:py-32',
  default: 'py-16 sm:py-28',
  compact: 'py-12 sm:py-20',
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
      <div className="mx-auto w-full max-w-6xl min-[1800px]:max-w-7xl px-4 sm:px-6 lg:px-8">{children}</div>
    </section>
  )
}

// Заголовок раздела.
//
// Раньше: подпись капсом с разрядкой, заголовок и подзаголовок — всё по
// центру. Именно этот набор читается «сделано нейросетью»: он стоял над
// каждым из двенадцати разделов одинаково. Теперь заголовок антиквой по
// левому краю, крупно, поднимается по словам.
//
// Надзаголовка («— Документы» над «Подготовлю пакет документов…») больше нет
// (28.09.2026): короткая латунная черта с подписью стояла над каждым
// разделом и почти везде повторяла заголовок — «Вопросы» над «Частыми
// вопросами», «География» над «Географией работы». Одинаковая рубрика над
// всеми разделами — примета шаблонной страницы, сделанной нейросетью,
// а заказчик попросил таких примет не оставлять.
//
// Подзаголовок на широком экране уходит вправо от заголовка, в свою
// колонку: так раздел начинается одной строкой, а не столбиком из трёх.
// titleClassName — поправка кегля для одного раздела: «и сертификация»
// склеено неразрывным пробелом и на 320 px шире колонки (02.10.2026).
export function SectionHeading({
  title,
  subtitle,
  dark = false,
  titleClassName = '',
}: {
  title: string
  subtitle?: string
  dark?: boolean
  titleClassName?: string
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
        <RevealText
          text={title}
          className={`font-display text-[2.6rem] font-medium leading-[1.02] tracking-[-0.01em] sm:text-5xl lg:text-[3.6rem] ${
            dark ? 'text-neutral-50' : 'text-neutral-950'
          } ${titleClassName}`}
        />
      </div>
      {subtitle && (
        <Reveal delay={150}>
          <p className={`text-base leading-relaxed sm:text-lg ${dark ? 'text-neutral-300' : 'text-neutral-600'}`}>
            {nbsp(subtitle)}
          </p>
        </Reveal>
      )}
    </div>
  )
}
