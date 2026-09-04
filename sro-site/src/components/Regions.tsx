import { MapPin } from 'lucide-react'
import { useEffect, useState } from 'react'
import { LABELS, REGIONS, type RegionKey } from '../content/regions'
import { anchor } from '../lib/site'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

const KEYS = Object.keys(LABELS) as RegionKey[]

type MapData = typeof import('../content/mapData')

// Карта охвата: где заказчик помогает вступить в СРО.
//
// Границы субъектов настоящие (см. scripts/build-map.py), поэтому регион
// закрашивается целиком, а не отмечается булавкой. Разница не косметическая:
// закрашенная Якутия сразу показывает масштаб работы, точка на её месте
// говорила ровно столько же, сколько точка на Костроме.
//
// Почему карта И список, а не что-то одно. Карта одним взглядом показывает
// главное — работа идёт от Петербурга до Якутска, а не «по Ростову». Но на
// телефоне карта России шириной 360 пикселей превращает Кострому в пиксель:
// ни прочитать, ни попасть пальцем. Поэтому работает всегда список, а карта
// показывает охват.
//
// Связь в обе стороны: наводите на строку — загорается регион, наводите
// на регион — подсвечивается строка. Это и есть смысл интерактивности здесь:
// человек ищет свой регион, а не разглядывает картинку.
export function Regions() {
  const [active, setActive] = useState<RegionKey | null>(null)

  // Контуры 83 субъектов — это 24 КБ после сжатия, больше половины скрипта
  // главной страницы. Блок стоит перед подвалом, до него ещё надо долистать,
  // поэтому карта грузится отдельным файлом после первой отрисовки: на
  // скорость открытия сайта она больше не влияет. Место под неё держится
  // заранее, чтобы страница не дёргалась, когда файл придёт.
  const [map, setMap] = useState<MapData | null>(null)
  useEffect(() => {
    let alive = true
    import('../content/mapData').then((data) => {
      if (alive) setMap(data)
    })
    return () => {
      alive = false
    }
  }, [])

  const point = active && map ? map.MAP_ANCHORS[active] : null
  // Плашку не измерить: ширину текста в SVG без отдельного прохода вёрстки
  // не узнать, поэтому считаем по числу букв — для одного-двух слов хватает.
  const text = active ? LABELS[active] : null
  const w = text ? text.length * 10 + 30 : 0
  const box = point &&
    text && {
      text,
      w,
      // У верхней кромки подпись уходит под метку, иначе её срежет.
      y: point.y < 70 ? point.y + 22 : point.y - 54,
      // Прижимаем к краям карты, чтобы длинное имя не вылезло за границу.
      x: Math.min(Math.max(point.x, w / 2 + 4), 1000 - w / 2 - 4),
    }

  return (
    <Section id="regions" className="bg-neutral-50/55">
      <SectionHeading
        eyebrow="География"
        title="Регионы, где помогу вступить"
        subtitle="Работа идёт дистанционно, приезжать не нужно. Для строителей регион важен: закон разрешает вступать только в СРО своего субъекта."
      />

      {/* Карта во всю ширину, список под ней. В две колонки рядом карта
          ужималась до трети экрана — ради неё блок и делался. */}
      <Reveal className="mt-10">
        {/* Скринридеру карта объявляется одной короткой подписью, а не
            пятнадцатью контурами: полный перечень регионов он всё равно
            прочитает из списка ниже, и дублировать его голосом незачем. */}
        {!map ? (
          <div className="w-full rounded-2xl bg-accent-50" style={{ aspectRatio: '1000 / 544' }} />
        ) : (
          <svg
            viewBox={map.VIEW_BOX}
            className="w-full overflow-visible"
            role="img"
            aria-label="Карта России: регионы, где помогаю вступить в СРО, выделены цветом"
          >
            <defs>
              {/* Лёгкий градиент вместо плоской заливки: с ним выделенные
                  регионы выглядят подсвеченными, а не закрашенными маркером. */}
              <linearGradient id="ru-on" x1="0" y1="0" x2="0.3" y2="1">
                <stop offset="0%" stopColor="#4A66EF" />
                <stop offset="100%" stopColor="#2F4BDE" />
              </linearGradient>
              <linearGradient id="ru-hot" x1="0" y1="0" x2="0.3" y2="1">
                <stop offset="0%" stopColor="#2F4BDE" />
                <stop offset="100%" stopColor="#202F93" />
              </linearGradient>
              <filter id="ru-shadow" x="-6%" y="-12%" width="112%" height="130%">
                <feDropShadow dx="0" dy="7" stdDeviation="9" floodColor="#141A45" floodOpacity="0.14" />
              </filter>
            </defs>

            <g filter="url(#ru-shadow)">
              {/* Остальная страна — только фон. Правило evenodd нужно из-за
                  анклавов: Адыгея внутри Краснодарского края, Ненецкий округ
                  внутри Архангельской области. Без него дырки бы залились. */}
              <path
                d={map.MAP_BASE}
                fillRule="evenodd"
                className="pointer-events-none fill-accent-100 stroke-white"
                strokeWidth="1.1"
              />
              {KEYS.map((key) => {
                const on = active === key
                return (
                  // onClick — ради телефона: наведения там нет, а тап по
                  // региону подпись показывает.
                  <path
                    key={key}
                    d={map.MAP_ACTIVE[key]}
                    fillRule="evenodd"
                    fill={on ? 'url(#ru-hot)' : 'url(#ru-on)'}
                    className="cursor-default stroke-white transition-[fill] duration-200"
                    strokeWidth="1.1"
                    onMouseEnter={() => setActive(key)}
                    onMouseLeave={() => setActive(null)}
                    onClick={() => setActive(key)}
                  />
                )
              })}
            </g>

            {/* Метка города и подпись рисуются последними, поверх контуров:
                иначе соседний регион накрыл бы им край. По вертикали подпись
                уходит вниз, если город у верхней кромки, по горизонтали
                прижимается к краям карты — иначе у Крыма и Якутска её
                обрезало бы границей viewBox. */}
            {point && box && (
              <g className="pointer-events-none">
                <circle cx={point.x} cy={point.y} r="13" className="fill-white opacity-70" />
                <circle cx={point.x} cy={point.y} r="6" className="fill-accent-800" />
                <rect
                  x={box.x - box.w / 2}
                  y={box.y}
                  width={box.w}
                  height="38"
                  rx="12"
                  className="fill-accent-800"
                />
                <text
                  x={box.x}
                  y={box.y + 25}
                  textAnchor="middle"
                  className="fill-white text-[19px] font-semibold"
                >
                  {box.text}
                </text>
              </g>
            )}
          </svg>
        )}
      </Reveal>

      <Reveal delay={80} className="mt-8">
        {/* Три колонки на десктопе, одна на телефоне: пятнадцать строк в три
            колонки на узком экране дают нечитаемые обрезки названий. */}
        <ul className="mx-auto grid max-w-4xl gap-1 sm:grid-cols-2 lg:grid-cols-3">
          {REGIONS.map((region) => {
            const on = active === region.point
            return (
              <li key={region.name}>
                {/* Строка не кликается — это перечень, а не меню. Отклик
                    всё равно нужен: он связывает строку с регионом на карте. */}
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
        <p className="mx-auto mt-6 max-w-2xl px-3 text-center text-sm text-neutral-600">
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
    </Section>
  )
}
