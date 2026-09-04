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

  const point = active ? POINTS[active as keyof typeof POINTS] : null
  const ACTIVE_LABEL = point && {
    text: point.label,
    // Ширина плашки на глаз по числу букв: измерить текст в SVG нечем.
    w: point.label.length * 10.5 + 28,
    // У верхней кромки подпись уходит под точку, иначе её срежет.
    y: point.y < 70 ? point.y + 26 : point.y - 56,
    // Прижимаем к краям карты, чтобы длинное имя не вылезло за границу.
    x: Math.min(Math.max(point.x, point.label.length * 5.25 + 16), 1000 - (point.label.length * 5.25 + 16)),
  }

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
            className="w-full overflow-visible"
            role="img"
            aria-label="Карта России с отмеченными регионами работы"
          >
            <defs>
              {/* Градиент и мягкая тень: плоская заливка одним тоном читалась
                  вырезанной из бумаги наклейкой. С лёгким объёмом силуэт
                  выглядит подложкой, на которой стоят точки. */}
              <linearGradient id="ru-fill" x1="0" y1="0" x2="0.4" y2="1">
                <stop offset="0%" stopColor="#DDE3FB" />
                <stop offset="100%" stopColor="#EFF2FE" />
              </linearGradient>
              <filter id="ru-shadow" x="-10%" y="-20%" width="120%" height="150%">
                <feDropShadow dx="0" dy="8" stdDeviation="10" floodColor="#2439B8" floodOpacity="0.13" />
              </filter>
            </defs>
            <g filter="url(#ru-shadow)">
              {[MAP.main, MAP.crimea, MAP.kaliningrad].map((d) => (
                <path key={d.slice(0, 24)} d={d} fill="url(#ru-fill)" stroke="#C3CDF7" strokeWidth="2" />
              ))}
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
                  {/* Ореол только у активной точки: пятнадцать постоянных
                      ореолов слились бы в облако. */}
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r="30"
                    className={`fill-accent-500 transition-opacity duration-200 ${on ? 'opacity-20' : 'opacity-0'}`}
                  />
                  {/* Прозрачный круг пошире — чтобы курсор ловил точку,
                      а не приходилось попадать в десять пикселей. */}
                  <circle cx={p.x} cy={p.y} r="26" fill="transparent" />
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={on ? 14 : 10}
                    className={`transition-all duration-200 ${on ? 'fill-accent-700' : 'fill-accent-600'}`}
                  />
                  {/* Белая сердцевина: сплошной кружок читался кляксой, кольцо
                      — меткой. */}
                  <circle cx={p.x} cy={p.y} r={on ? 5 : 3.5} className="fill-white transition-all duration-200" />
                </g>
              )
            })}
            {/* Подпись рисуется последней, поверх всех точек: иначе соседняя
                точка накрывала бы её край. Плашка не мерится по тексту —
                в SVG это стоило бы отдельного прохода вёрстки, — а считается
                по числу букв; для одного слова в две-три строки этого хватает.

                По вертикали подпись уходит вниз, если точка у верхней кромки,
                по горизонтали прижимается к краям карты: у Петербурга и
                Якутска она иначе вылезала за границу и обрезалась. */}
            {ACTIVE_LABEL && (
              <g className="pointer-events-none">
                <rect
                  x={ACTIVE_LABEL.x - ACTIVE_LABEL.w / 2}
                  y={ACTIVE_LABEL.y}
                  width={ACTIVE_LABEL.w}
                  height="38"
                  rx="12"
                  className="fill-accent-800"
                />
                <text
                  x={ACTIVE_LABEL.x}
                  y={ACTIVE_LABEL.y + 25}
                  textAnchor="middle"
                  className="fill-white text-[19px] font-semibold"
                >
                  {ACTIVE_LABEL.text}
                </text>
              </g>
            )}
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
