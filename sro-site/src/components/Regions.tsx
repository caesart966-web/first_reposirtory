import { useEffect, useMemo, useState } from 'react'
import { LABELS, REGIONS, type RegionKey } from '../content/regions'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

const KEYS = Object.keys(LABELS) as RegionKey[]

type MapData = typeof import('../content/mapData') & typeof import('../content/mapDots')

// Точки сетки одной строкой «x,y x,y …» → один путь из кружков. Один путь
// на группу, а не две с лишним тысячи элементов <circle>: страница остаётся
// лёгкой, а браузер рисует карту одним вызовом на регион.
function dotsPath(dots: string, r: number): string {
  let d = ''
  for (const pair of dots.split(' ')) {
    const [x, y] = pair.split(',').map(Number)
    d += `M${(x - r).toFixed(1)} ${y}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`
  }
  return d
}

// Карта охвата: где заказчик помогает вступить в СРО.
//
// Границы субъектов настоящие (см. scripts/build-map.py), поэтому регион
// выделяется целиком, а не отмечается булавкой: выделенная Якутия сразу
// показывает масштаб работы, одна точка на её месте говорила бы ровно
// столько же, сколько точка на Костроме.
//
// С 28.09.2026 карта точечная (scripts/build-map-dots.mjs): страна разложена
// шестиугольной сеткой точек, точки выделенных регионов — латунью и чуть
// крупнее. Заливкой контуров огромные регионы ложились сплошными пятнами
// и перетягивали на себя весь раздел (сначала латунными, потом серыми), а
// карта выглядела картинкой из справочника. Контуры регионов остались
// невидимыми — по ним ловится наведение, иначе курсор проваливался бы
// в промежутки между точками.
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
    Promise.all([import('../content/mapData'), import('../content/mapDots')]).then(([shapes, dots]) => {
      if (alive) setMap({ ...shapes, ...dots })
    })
    return () => {
      alive = false
    }
  }, [])

  // Пути из точек считаются один раз, когда карта пришла.
  const dots = useMemo(() => {
    if (!map) return null
    const step = map.DOT_STEP
    return {
      base: dotsPath(map.DOTS_BASE, step * 0.28),
      active: Object.fromEntries(KEYS.map((key) => [key, dotsPath(map.DOTS_ACTIVE[key] ?? '', step * 0.36)])),
    }
  }, [map])

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
    <Section id="regions" className="bg-neutral-100">
      <SectionHeading
        title="География работы"
        // Неразрывный пробел держит «субъекта РФ» вместе: без него «РФ»
        // срывалось на отдельную строку и висело там одно.
        subtitle={
          'Работаю дистанционно, личный визит не нужен. Для строительных компаний регион важен: по закону вступить можно только в СРО своего субъекта\u00A0РФ.'
        }
      />

      {/* Карта во всю ширину, список под ней. В две колонки рядом карта
          ужималась до трети экрана — ради неё блок и делался. */}
      <Reveal className="mt-10">
        {/* Скринридеру карта объявляется одной короткой подписью, а не
            пятнадцатью контурами: полный перечень регионов он всё равно
            прочитает из списка ниже, и дублировать его голосом незачем. */}
        {!map ? (
          <div className="w-full rounded-3xl bg-neutral-200/60" style={{ aspectRatio: '1000 / 544' }} />
        ) : (
          <svg
            viewBox={map.VIEW_BOX}
            className="w-full overflow-visible"
            role="img"
            aria-label="Карта России: регионы, где помогаю вступить в СРО, выделены цветом"
          >
            <defs>
              {/* Латунь с лёгким переходом по всей карте, а не плоская заливка:
                  точки на западе светлее, на востоке глубже — карта читается
                  освещённой, как лист, а не залитой маркером. */}
              <linearGradient id="ru-dot" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1000" y2="544">
                <stop offset="0%" stopColor="#C9A370" />
                <stop offset="100%" stopColor="#9A6F3E" />
              </linearGradient>
            </defs>

            {dots && (
              <>
                {/* Остальная страна — светлые точки, только фон. */}
                <path d={dots.base} className="pointer-events-none fill-neutral-300" />
                {KEYS.map((key) => (
                  <path
                    key={key}
                    d={dots.active[key]}
                    fill={active === key ? '#4D3A26' : 'url(#ru-dot)'}
                    className="pointer-events-none transition-[fill] duration-500"
                  />
                ))}
              </>
            )}

            {/* Невидимые контуры выделенных регионов — поверхность для
                наведения и касания. onClick — ради телефона: наведения там
                нет, а касание региона показывает подпись. evenodd — из-за
                анклавов: Адыгея внутри Краснодарского края. */}
            {KEYS.map((key) => (
              <path
                key={key}
                d={map.MAP_ACTIVE[key]}
                fillRule="evenodd"
                fill="transparent"
                className="cursor-default"
                onMouseEnter={() => setActive(key)}
                onMouseLeave={() => setActive(null)}
                onClick={() => setActive(key)}
              />
            ))}

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
        {/* Три колонки на компьютере, две на планшете. На телефоне — в поток,
            как слова в строке: в один столбик пятнадцать строк тянулись
            на полтора экрана, а в колонки длинные названия («Свердловская
            область, Екатеринбург») рвались на обрезки. */}
        <ul className="mx-auto flex max-w-4xl flex-wrap gap-x-1 gap-y-0 sm:grid sm:grid-cols-2 sm:gap-1 lg:grid-cols-3">
          {REGIONS.map((region) => {
            const on = active === region.point
            return (
              <li key={region.name}>
                {/* Строка не кликается — это перечень, а не меню. Отклик
                    всё равно нужен: он связывает строку с регионом на карте. */}
                <div
                  onMouseEnter={() => setActive(region.point)}
                  onMouseLeave={() => setActive(null)}
                  className={`flex items-center gap-2 rounded-xl px-2 py-1.5 text-sm transition-colors duration-150 sm:gap-2.5 sm:px-3 sm:py-2 ${
                    on ? 'bg-accent-50 text-accent-800' : 'text-neutral-700'
                  }`}
                >
                  {/* Точка вместо булавки — та же, что на карте. */}
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full transition-colors duration-150 ${
                      on ? 'bg-accent-800' : 'bg-accent-500'
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
          Вашего региона нет в списке?{' '}
          <a
            href="#contacts"
            className="font-semibold text-accent-700 underline underline-offset-2 transition hover:text-accent-800"
          >
            Напишите, уточню возможность работы
          </a>
          . Перечень пополняется, а для проектировщиков и изыскателей региональных ограничений
          нет.
        </p>
      </Reveal>
    </Section>
  )
}
