import { MapPin } from 'lucide-react'
import { useState } from 'react'
import { MAP, POINTS, REGIONS } from '../content/regions'
import { anchor } from '../lib/site'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Карта охвата: где заказчик помогает вступить в СРО.
//
// Почему карта И список, а не что-то одно. Карта одним взглядом показывает
// главное — работа идёт от Петербурга до Якутска, а не «по Ростову». Но на
// телефоне карта России шириной 360 пикселей превращает пятнадцать точек в
// россыпь булавочных головок: ни прочитать, ни попасть пальцем. Поэтому
// работает всегда список, а карта показывает охват.
//
// Связь в обе стороны: наводите на строку — загорается её точка, наводите
// на точку — подсвечивается строка. Это и есть смысл интерактивности здесь:
// человек ищет свой регион, а не разглядывает картинку.
export function Regions() {
  const [active, setActive] = useState<string | null>(null)

  return (
    <Section id="regions" className="bg-neutral-50/55">
      <SectionHeading
        eyebrow="География"
        title="Регионы, где помогу вступить"
        subtitle="Работа идёт дистанционно, приезжать не нужно. Для строителей регион важен: закон разрешает вступать только в СРО своего субъекта."
      />

      <div className="mt-10 grid gap-8 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] lg:items-center lg:gap-12">
        <Reveal>
          {/* Скринридеру карта объявляется одной короткой подписью, а не
              пятнадцатью точками: полный перечень регионов он всё равно
              прочитает из списка рядом, и дублировать его голосом незачем. */}
          <svg
            viewBox="0 0 1000 520"
            className="w-full"
            role="img"
            aria-label="Карта России с отмеченными регионами работы"
          >
            {/* Заливка и контур разной насыщенности: на одном тоне силуэт
                расплывался пятном и терялся на светлой подложке секции. */}
            <g className="text-accent-300">
              <path d={MAP.main} fill="currentColor" className="text-accent-100" />
              <path d={MAP.main} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
              <path d={MAP.crimea} fill="currentColor" className="text-accent-100" />
              <path d={MAP.crimea} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
              <path d={MAP.kaliningrad} fill="currentColor" className="text-accent-100" />
              <path d={MAP.kaliningrad} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
            </g>
            {Object.entries(POINTS).map(([key, p]) => {
              const on = active === key
              return (
                <g
                  key={key}
                  onMouseEnter={() => setActive(key)}
                  onMouseLeave={() => setActive(null)}
                  className="cursor-default"
                >
                  {/* Ореол появляется только у активной точки: пятнадцать
                      постоянных ореолов слились бы в облако. */}
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r="30"
                    className={`fill-accent-500 transition-opacity duration-200 ${
                      on ? 'opacity-20' : 'opacity-0'
                    }`}
                  />
                  {/* Прозрачный круг пошире — чтобы курсор ловил точку,
                      а не приходилось попадать в семь пикселей. */}
                  <circle cx={p.x} cy={p.y} r="26" fill="transparent" />
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={on ? 15 : 10}
                    className={`transition-all duration-200 ${
                      on ? 'fill-accent-700' : 'fill-accent-600'
                    }`}
                  />
                  <circle cx={p.x} cy={p.y} r={on ? 5.5 : 3.5} className="fill-white transition-all duration-200" />
                </g>
              )
            })}
          </svg>
        </Reveal>

        <Reveal delay={80}>
          {/* Две колонки на десктопе, одна на телефоне: пятнадцать строк в две
              колонки на узком экране дают нечитаемые обрезки названий. */}
          <ul className="grid gap-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            {REGIONS.map((region) => {
              const on = active === region.point
              return (
                <li key={region.name}>
                  {/* Строка не кликается — это перечень, а не меню. Отклик
                      всё равно нужен: он связывает строку с точкой на карте. */}
                  <div
                    onMouseEnter={() => setActive(region.point)}
                    onMouseLeave={() => setActive(null)}
                    className={`flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition-colors duration-150 ${
                      on ? 'bg-accent-50 text-accent-800' : 'text-neutral-700'
                    }`}
                  >
                    <MapPin
                      className={`h-4 w-4 shrink-0 transition-colors duration-150 ${
                        on ? 'text-accent-600' : 'text-accent-500/60'
                      }`}
                      aria-hidden="true"
                    />
                    <span className="min-w-0">{region.name}</span>
                  </div>
                </li>
              )
            })}
          </ul>
          <p className="mt-5 px-3 text-sm text-neutral-600">
            Не нашли свой регион?{' '}
            <a
              href={anchor('#quiz')}
              className="font-semibold text-accent-700 underline underline-offset-2 transition hover:text-accent-800"
            >
              Напишите — проверю
            </a>
            : список пополняется, а для проектировщиков и изыскателей региональных
            ограничений нет вовсе.
          </p>
        </Reveal>
      </div>
    </Section>
  )
}
