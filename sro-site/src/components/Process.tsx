import { useEffect, useRef, useState } from 'react'
import { nbsp } from '../lib/typo'
import { Reveal } from './ui/Reveal'
import { SectionHeading } from './ui/Section'

// Четыре шага работы — тёмный раздел посреди страницы, пауза между
// светлыми блоками.
//
// С 26.09.2026 без фотографии. Здесь стояла Фемида (до того — гравюра), но
// раздел рассказывает про шаги, а символ правосудия ни один шаг не объясняет:
// она переехала в «О нас», где сайт говорит, на чём держится работа.
// Номера здесь по делу: это последовательность.
//
// С 19.10.2026 — чертёж, который достраивается по шагам (заказчик прислал
// шаблон Ora со scrolltide.co: часы разбираются и собираются, пока страницу
// листают). Здесь тот же приём «главами», но своим рисунком: шаги идут
// столбиком, рядом стоит чертёж дома латунными линиями, и с каждым шагом
// на нём прибавляется стадия — разметка и фундамент, каркас, стены
// и кран, готовый дом под фронтоном (фронтон — как в знаке компании).
// Не 240 кадров, а один SVG в несколько килобайт: на телефоне ни ожидания,
// ни лишнего трафика. Шаг, который сейчас читают, — тот, чей верх прошёл
// 55 % высоты окна; остальные чуть приглушены (не ниже 0,6: текст
// остаётся читаемым, 5:1 и выше).
//
// Без скрипта (готовый HTML для поисковика) и при «уменьшить движение»
// чертёж стоит готовым и все шаги видны одинаково.
//
// «Через форму на сайте» из первого шага убрано вместе с формой.
const STEPS = [
  {
    number: '01',
    title: 'Заявка',
    text: 'Позвоните или напишите: какие работы и по какому договору планируете.',
  },
  {
    number: '02',
    title: 'Разбор',
    text: 'Смотрю договор и документы и говорю, нужна ли СРО и какая.',
  },
  {
    number: '03',
    title: 'Документы',
    // До 01.10.2026 — «Собираю комплект под требования выбранной СРО»:
    // слово в слово первая фраза раздела «Документы» сразу ниже. Здесь —
    // кто что делает на шаге, как в шагах вступления (StepsGrid).
    text: 'Готовлю комплект, вы подписываете и подаёте его в СРО.',
  },
  {
    number: '04',
    title: 'Выписка',
    text: 'Веду переписку с СРО до решения о приёме и выписки из реестра.',
  },
]

// Чертёж. Сетка viewBox — 400 × 340, земля на y = 290, дом от x = 100
// до 300: три пролёта по 66,7 и четыре этажа по 40. У каждой линии своя
// стадия (s): линия прорисовывается, когда стадия дошла до неё.
const BAYS = [133.3, 200, 266.7] // середины пролётов
const FLOORS = [130, 170, 210, 250] // верх каждого этажа
const windowPath = (cx: number, top: number) => `M${cx - 14} ${top + 10}h28v22h-28Z`

type Line = { s: number; d: string; thin?: boolean }
const LINES: Line[] = [
  // 1 — разметка и фундамент
  { s: 1, d: 'M100 290v16h200v-16' },
  { s: 1, d: 'M100 316v12M300 316v12M100 322h200M96 326l8-8M296 326l8-8', thin: true },
  // 2 — каркас: колонны и перекрытия
  { s: 2, d: 'M100 290V130' },
  { s: 2, d: 'M166.7 290V130' },
  { s: 2, d: 'M233.3 290V130' },
  { s: 2, d: 'M300 290V130' },
  { s: 2, d: 'M94 250h212' },
  { s: 2, d: 'M94 210h212' },
  { s: 2, d: 'M94 170h212' },
  { s: 2, d: 'M94 130h212' },
]

// Порядковый номер линии внутри своей стадии — для задержки.
const LINE_ORDER = LINES.map((line, i) => LINES.slice(0, i).filter((x) => x.s === line.s).length)

// 3 — окна (на 4-й стадии в них загорается свет), дверь — на 4-й.
const WINDOWS = FLOORS.flatMap((top, floor) =>
  BAYS.filter((_, bay) => !(floor === FLOORS.length - 1 && bay === 1)).map((cx) => windowPath(cx, top)),
)

// 3 — кран; на 4-й стадии он уходит: дом достроен.
const CRANE = [
  'M334 290V52M346 290V52',
  'M334 290L346 270L334 250L346 230L334 210L346 190L334 170L346 150L334 130L346 110L334 90L346 70L334 52',
  'M168 52H392M340 52V30M340 30L178 52M340 30L392 52',
  'M330 58h20v12h-20Z',
  'M214 52v44M208 96h12v8h-12Z',
]

// 4 — фронтон и дверь.
const FINISH = ['M92 130L200 92L308 130', 'M188 290v-28h24v28']

const DRAW = 'stroke-dashoffset 1.1s cubic-bezier(0.22, 1, 0.36, 1)'

function Blueprint({ stage, animate }: { stage: number; animate: boolean }) {
  // Задержки внутри стадии — линии ложатся по очереди, как их чертят.
  const stroke = (s: number, order: number) => ({
    strokeDasharray: 1,
    strokeDashoffset: stage >= s ? 0 : 1,
    transition: animate ? `${DRAW} ${order * 0.08}s` : 'none',
  })
  return (
    <svg viewBox="70 20 340 320" className="h-full w-full" fill="none" aria-hidden="true">
      <defs>
        <pattern id="bp-grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M20 0H0V20" stroke="#FBF9F5" strokeOpacity="0.05" strokeWidth="1" />
        </pattern>
      </defs>
      <rect x="70" y="20" width="340" height="320" fill="url(#bp-grid)" />
      {/* Земля — всегда: чертёж начинается с неё. */}
      <path d="M76 290h328" stroke="#A79D91" strokeWidth="1.2" />
      <path d="M86 296l-6 6M106 296l-6 6M126 296l-6 6M326 296l-6 6M346 296l-6 6M366 296l-6 6M386 296l-6 6" stroke="#A79D91" strokeOpacity="0.6" strokeWidth="1" />

      {LINES.map((line, i) => (
        <path
          key={line.d}
          d={line.d}
          pathLength={1}
          stroke={line.thin ? '#A79D91' : '#C09A68'}
          strokeWidth={line.thin ? 1 : 1.6}
          strokeLinecap="round"
          style={stroke(line.s, LINE_ORDER[i])}
        />
      ))}

      {WINDOWS.map((d, i) => (
        <path
          key={d}
          d={d}
          pathLength={1}
          stroke="#C09A68"
          strokeWidth="1.2"
          fill="#C09A68"
          style={{
            ...stroke(3, i % 6),
            fillOpacity: stage >= 4 ? 0.32 : 0,
            transition: animate
              ? `${DRAW} ${(i % 6) * 0.08}s, fill-opacity 0.9s ease ${0.3 + (i % 5) * 0.12}s`
              : 'none',
          }}
        />
      ))}

      <g style={{ opacity: stage >= 4 ? 0 : 1, transition: animate ? 'opacity 0.9s ease' : 'none' }}>
        {CRANE.map((d, i) => (
          <path
            key={d}
            d={d}
            pathLength={1}
            stroke="#D2B186"
            strokeWidth={i === 1 ? 0.9 : 1.3}
            strokeLinejoin="round"
            style={stroke(3, i + 2)}
          />
        ))}
      </g>

      {FINISH.map((d, i) => (
        <path
          key={d}
          d={d}
          pathLength={1}
          stroke="#C09A68"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={stroke(4, i + 1)}
        />
      ))}
    </svg>
  )
}

export function Process() {
  // null — скрипт ещё не считал прокрутку (готовый HTML) или движение
  // уменьшено: дом достроен, все шаги видны одинаково. -1 — раздел ещё
  // не дошёл до середины экрана: на чертеже только земля.
  const [active, setActive] = useState<number | null>(null)
  const [animate, setAnimate] = useState(false)
  const listRef = useRef<HTMLOListElement>(null)

  useEffect(() => {
    const list = listRef.current
    if (!list || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const items = [...list.children] as HTMLElement[]
    let frame = 0
    const measure = () => {
      frame = 0
      const line = window.innerHeight * 0.55
      let index = -1
      items.forEach((el, i) => {
        if (el.getBoundingClientRect().top <= line) index = i
      })
      setActive(index)
    }
    measure()
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(measure)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      cancelAnimationFrame(frame)
    }
  }, [])

  // Переходы включаются только после того, как первая расстановка по месту
  // прокрутки уже на экране (два кадра после неё): иначе готовый дом
  // «стирался» бы на глазах, а при «Назад» на главную под обложкой шло бы
  // движение, которого там быть не должно (test-site.mjs, «Назад» на главную).
  const measured = active !== null
  useEffect(() => {
    if (!measured) return
    let second = 0
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => setAnimate(true))
    })
    return () => {
      cancelAnimationFrame(first)
      cancelAnimationFrame(second)
    }
  }, [measured])

  return (
    <section id="process" className="relative isolate bg-accent-950 py-20 text-neutral-50 sm:py-32">
      <div className="mx-auto w-full max-w-6xl min-[1800px]:max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading dark title="Как проходит работа" />
        {/* До 1024 px чертёж липнет под шапкой сверху, шаги проезжают под ним
            (у него свой графитовый фон и растушёвка снизу); с 1024 px —
            справа, по середине экрана, шаги слева. */}
        <div className="mt-10 sm:mt-14 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-20">
          <div className="sticky top-16 z-10 -mx-4 bg-accent-950 px-4 pb-2 pt-3 after:pointer-events-none after:absolute after:inset-x-0 after:top-full after:h-10 after:bg-gradient-to-b after:from-accent-950 after:to-transparent sm:-mx-6 sm:px-6 lg:order-2 lg:top-[max(5rem,calc(50vh-15rem))] lg:mx-0 lg:self-start lg:bg-transparent lg:p-0 lg:after:hidden">
            <div className="mx-auto h-[min(30vh,15rem)] max-w-full sm:h-[min(34vh,19rem)] lg:h-[30rem]">
              <Blueprint stage={active === null ? STEPS.length : active + 1} animate={animate} />
            </div>
          </div>

          <ol ref={listRef} className="relative mt-6 border-t border-white/15 lg:order-1 lg:mt-0">
            {STEPS.map((step, index) => {
              const dim = active !== null && active >= 0 && index !== active
              return (
                <li
                  key={step.number}
                  className="min-h-[34vh] border-b border-white/15 py-7 last:min-h-0 sm:py-9 lg:min-h-[42vh] lg:py-10 lg:last:min-h-0"
                >
                  <Reveal delay={index * 120}>
                    <div
                      className={`grid grid-cols-[3.5rem_minmax(0,1fr)] sm:grid-cols-[5rem_minmax(0,1fr)] ${
                        animate ? 'transition-opacity duration-700 ease-silk' : ''
                      }`}
                      style={{ opacity: dim ? 0.6 : 1 }}
                    >
                      <p className="font-display text-[2rem] font-medium leading-none tabular-nums text-accent-300 sm:text-[2.6rem]">
                        {step.number}
                      </p>
                      <div>
                        <h3 className="font-display text-[1.6rem] font-medium leading-none sm:text-[1.9rem] sm:leading-tight">
                          {step.title}
                        </h3>
                        <p className="mt-2.5 max-w-md leading-relaxed text-neutral-300 sm:mt-3">{nbsp(step.text)}</p>
                      </div>
                    </div>
                  </Reveal>
                </li>
              )
            })}
          </ol>
        </div>
      </div>
    </section>
  )
}
