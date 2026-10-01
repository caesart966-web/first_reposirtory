import { useEffect, useState } from 'react'
import { LABELS, REGIONS, type RegionKey } from '../content/regions'
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
// Цвет подбирался трижды. Насыщенная латунь — Красноярский край и Якутия
// огромными пятнами перетягивали на себя весь раздел. Тёплый серый
// (26.09.2026) — карта потухла, заказчик попросил ярче. Точечная сетка
// (28.09.2026) — заказчику не понравилась, вернули заливку. Сейчас —
// светлая латунь (accent-200 → 300 с лёгким переходом): регионы читаются
// цветом, но не спорят с заголовком; регион под курсором — густая латунь.
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
              {/* Лёгкий переход вместо плоской заливки: с ним регионы
                  выглядят подсвеченными, а не закрашенными маркером. */}
              <linearGradient id="ru-on" x1="0" y1="0" x2="0.3" y2="1">
                <stop offset="0%" stopColor="#E0C49A" />
                <stop offset="100%" stopColor="#CBA671" />
              </linearGradient>
              <linearGradient id="ru-hot" x1="0" y1="0" x2="0.3" y2="1">
                <stop offset="0%" stopColor="#A57B47" />
                <stop offset="100%" stopColor="#86602F" />
              </linearGradient>
              <filter id="ru-shadow" x="-6%" y="-12%" width="112%" height="130%">
                <feDropShadow dx="0" dy="7" stdDeviation="9" floodColor="#1C1815" floodOpacity="0.12" />
              </filter>
            </defs>

            <g filter="url(#ru-shadow)">
              {/* Остальная страна — только фон. Правило evenodd нужно из-за
                  анклавов: Адыгея внутри Краснодарского края, Ненецкий округ
                  внутри Архангельской области. Без него дырки бы залились. */}
              <path
                d={map.MAP_BASE}
                fillRule="evenodd"
                className="pointer-events-none fill-neutral-200 stroke-neutral-100"
                strokeWidth="1.1"
              />
              {KEYS.map((key) => (
                // onClick — ради телефона: наведения там нет, а касание
                // региона показывает подпись.
                <path
                  key={key}
                  d={map.MAP_ACTIVE[key]}
                  fillRule="evenodd"
                  fill={active === key ? 'url(#ru-hot)' : 'url(#ru-on)'}
                  className="cursor-default stroke-neutral-100 transition-[fill] duration-500"
                  strokeWidth="1.1"
                  onMouseEnter={() => setActive(key)}
                  onMouseLeave={() => setActive(null)}
                  onClick={() => setActive(key)}
                />
              ))}
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
        {/* Строка — субъект, справа серым — город, если заказчик его назвал
            (content/regions.ts). На линейках, как перечни на всём сайте:
            на телефоне — столбцом, с 640 px — в две колонки, с 1024 — в три.
            До 01.10.2026 названия шли в поток, как слова в строке, — так
            помещалось больше, но вразнобой записанный список читался
            сплошной кашей. */}
        <ul className="grid border-t border-neutral-300 sm:grid-cols-2 sm:gap-x-10 lg:grid-cols-3">
          {REGIONS.map((region) => {
            const on = active === region.point
            return (
              <li key={region.name} className="border-b border-neutral-300">
                {/* Строка не кликается — это перечень, а не меню. Отклик
                    всё равно нужен: он связывает строку с регионом на карте. */}
                <div
                  onMouseEnter={() => setActive(region.point)}
                  onMouseLeave={() => setActive(null)}
                  className={`flex items-baseline gap-2.5 py-3 text-[15px] transition-colors duration-150 ${
                    on ? 'text-accent-800' : 'text-neutral-900'
                  }`}
                >
                  {/* Кружок цвета региона на карте — та же латунь. */}
                  <span
                    className={`h-2 w-2 shrink-0 -translate-y-px rounded-full transition-colors duration-150 ${
                      on ? 'bg-accent-800' : 'bg-accent-500'
                    }`}
                    aria-hidden="true"
                  />
                  <span className="min-w-0 flex-1">{region.name}</span>
                  {region.city && (
                    <span className="shrink-0 text-sm text-neutral-600">{region.city}</span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
        {/* По левому краю, как весь текст сайта: по центру под списком
            на линейках приписка выглядела отдельной плашкой. */}
        <p className="mt-6 max-w-2xl text-sm leading-relaxed text-neutral-600">
          Вашего региона нет в списке?{' '}
          <a
            href="#contacts"
            className="font-semibold text-accent-700 underline underline-offset-2 transition hover:text-accent-800"
          >
            Напишите — скажу, смогу ли помочь
          </a>
          . Перечень пополняется, а для проектировщиков и изыскателей региональных ограничений
          нет.
        </p>
      </Reveal>
    </Section>
  )
}
