// Чертёж фасада для раздела «Как проходит работа» (Process.tsx).
//
// 19.10.2026 — первая версия (коробка с окнами и кран); 20.10.2026 заказчик:
// «чуть красивее и профессиональнее». Теперь это лист рабочего чертежа:
// рамка листа, оси с кружками-марками, отметки уровней слева, размерная
// линия, штамп в правом нижнем углу (номер листа и стадия меняются вместе
// с шагом), а фасад — с цоколем, карнизом, переплётами окон, входом под
// козырьком и фронтоном с круглым окном (фронтон — как в знаке компании).
// На последнем шаге кран уезжает, в окнах загорается свет, а на лист ложится
// печать со знаком весов.
//
// Стадии: 0 — пустой лист (земля и рамка), 1 — разбивка осей и фундамент,
// 2 — каркас и отметки, 3 — стены, окна, кран, 4 — фронтон, вход, печать.
// Линии прорисовываются (stroke-dashoffset по pathLength = 1), подписи
// и заливки проявляются. Подписи мельче 6 px на телефоне не читаются, поэтому
// до 640 px их нет вовсе (max-sm:hidden): там остаются линии и печать.
//
// Все цифры на листе — условные, как на любом учебном чертеже: размер «18 000»
// и отметки уровней ничего о реальном объекте не утверждают.

const BRASS = '#C09A68'
const BRASS_LIGHT = '#D2B186'
const GRAY = '#A79D91'
const DRAW = 'stroke-dashoffset 1.1s cubic-bezier(0.22, 1, 0.36, 1)'
const FADE = 'opacity 0.8s ease'

// Сетка листа. Земля на y = 330, фасад от x = 120 до 320: три пролёта
// и четыре этажа по 42.
const GROUND = 330
const AXES = [120, 186.7, 253.3, 320]
const LEVELS = [330, 288, 246, 204, 162]
const LEVEL_TEXT = ['±0,000', '+3,300', '+6,600', '+9,900', '+13,200']
const BAYS = [153.3, 220, 286.7]

type Stroke = { s: number; d: string; w?: number; c?: string; dash?: boolean }

const win = (cx: number, top: number) => {
  const x = cx - 15
  const y = top + 9
  return `M${x} ${y}h30v24h-30Z M${cx} ${y}v24 M${x} ${y + 9}h30 M${x - 3} ${y + 26}h36`
}

// Окна: три верхних этажа целиком, на первом — без среднего пролёта (там вход).
const WINDOWS = LEVELS.slice(1).flatMap((top, floor) =>
  BAYS.filter((_, bay) => !(floor === 0 && bay === 1)).map((cx) => win(cx, top)),
)

const LINES: Stroke[] = [
  // 1 — разбивка осей и фундамент
  ...AXES.map((x) => ({ s: 1, d: `M${x} 96V372`, w: 0.5, c: GRAY, dash: true })),
  { s: 1, d: 'M116 330v14h-6v6h220v-6h-6v-14', w: 1.3 },
  { s: 1, d: 'M120 366v-8M320 366v-8M120 362h200M116 366l8-8M316 366l8-8', w: 0.7, c: GRAY },
  // 2 — каркас: колонны по осям и перекрытия
  ...AXES.map((x) => ({ s: 2, d: `M${x} ${GROUND}V162`, w: 1.4 })),
  ...LEVELS.slice(1).map((y) => ({ s: 2, d: `M112 ${y}h216`, w: 1.4 })),
  ...LEVELS.map((y) => ({ s: 2, d: `M58 ${y}h46M98 ${y - 6}l6 6l6-6`, w: 0.7, c: GRAY })),
  // 3 — цоколь, карниз и окна с переплётами
  { s: 3, d: 'M116 318h208', w: 1 },
  { s: 3, d: 'M110 162h220v-6h-220Z', w: 1.2 },
  ...WINDOWS.map((d) => ({ s: 3, d, w: 0.9 })),
]

// 3 — башенный кран: ствол решёткой, стрела и противовес, кабина, крюк.
const CRANE: Stroke[] = [
  { s: 3, d: 'M374 330V66M386 330V66', w: 1.1 },
  {
    s: 3,
    d: 'M374 330L386 312L374 294L386 276L374 258L386 240L374 222L386 204L374 186L386 168L374 150L386 132L374 114L386 96L374 78',
    w: 0.6,
  },
  { s: 3, d: 'M196 60H444M196 66H444', w: 1 },
  { s: 3, d: 'M196 66L206 60L216 66L226 60L236 66L246 60L256 66L266 60L276 66L286 60L296 66L306 60L316 66L326 60L336 66L346 60L356 66L366 60', w: 0.5 },
  { s: 3, d: 'M380 60V34M380 34L200 60M380 34L444 60', w: 0.7 },
  { s: 3, d: 'M426 66h16v12h-16Z M362 70h12v10h-12Z', w: 0.9 },
  { s: 3, d: 'M250 66v40M244 106h12v7h-12Z', w: 0.8 },
]

// 4 — фронтон с круглым окном, вход под козырьком.
const FINISH: Stroke[] = [
  { s: 4, d: 'M106 156L220 114L334 156', w: 1.6 },
  { s: 4, d: 'M220 133a8 8 0 1 0 0.01 0', w: 1 },
  { s: 4, d: 'M206 330v-32h28v32M220 298v32', w: 1.2 },
  { s: 4, d: 'M198 294h44M202 294l-4 -6M238 294l4-6', w: 1.1 },
]

// Порядок линии внутри стадии — для задержки: линии ложатся по очереди.
const orderOf = (list: Stroke[]) => list.map((l, i) => list.slice(0, i).filter((x) => x.s === l.s).length)
const LINE_ORDER = orderOf(LINES)
const CRANE_ORDER = orderOf(CRANE)
const FINISH_ORDER = orderOf(FINISH)

// «Реестр», а не «Выписка» (22.10.2026) — как четвёртый шаг в Process.tsx.
export const STAGE_NAMES = ['Заявка', 'Разбор', 'Документы', 'Реестр']

export function Blueprint({ stage, animate }: { stage: number; animate: boolean }) {
  const drawn = (s: number, order: number, slow = 1) => ({
    strokeDasharray: 1,
    strokeDashoffset: stage >= s ? 0 : 1,
    transition: animate ? `${DRAW} ${order * 0.06 * slow}s` : 'none',
  })
  const shown = (on: boolean, delay = 0) => ({
    opacity: on ? 1 : 0,
    transition: animate ? `${FADE} ${delay}s` : 'none',
  })
  // Оси — штрихпунктиром: такую линию не прочертишь через dashoffset,
  // поэтому она проявляется, а остальные линии прорисовываются.
  const path = (l: Stroke, order: number, key: string) =>
    l.dash ? (
      <path
        key={key}
        d={l.d}
        stroke={l.c ?? BRASS}
        strokeOpacity={0.55}
        strokeWidth={l.w ?? 1}
        strokeDasharray="10 3 1.5 3"
        style={shown(stage >= l.s, order * 0.06)}
      />
    ) : (
      <path
        key={key}
        d={l.d}
        pathLength={1}
        stroke={l.c ?? BRASS}
        strokeWidth={l.w ?? 1}
        strokeLinecap="round"
        strokeLinejoin="round"
        style={drawn(l.s, order)}
      />
    )

  return (
    <svg viewBox="0 0 480 420" className="h-full w-full" fill="none" aria-hidden="true">
      <defs>
        <pattern id="bp-grid" width="16" height="16" patternUnits="userSpaceOnUse">
          <path d="M16 0H0V16" stroke="#FBF9F5" strokeOpacity="0.045" strokeWidth="1" />
        </pattern>
      </defs>

      {/* Лист: сетка, внешняя рамка и рамка поля с отступом под подшивку. */}
      <rect x="8" y="8" width="464" height="404" fill="url(#bp-grid)" stroke="#FBF9F5" strokeOpacity="0.08" />
      <rect x="22" y="14" width="444" height="392" stroke="#FBF9F5" strokeOpacity="0.14" strokeWidth="0.8" />

      {/* Земля — всегда: чертёж начинается с неё. */}
      <path d="M36 330h408" stroke={GRAY} strokeWidth="1" />
      <path
        d="M44 336l-6 6M56 336l-6 6M68 336l-6 6M80 336l-6 6M92 336l-6 6M346 336l-6 6M358 336l-6 6M370 336l-6 6M382 336l-6 6M394 336l-6 6M406 336l-6 6M418 336l-6 6M430 336l-6 6"
        stroke={GRAY}
        strokeOpacity="0.55"
        strokeWidth="0.7"
      />

      {LINES.map((l, i) => path(l, LINE_ORDER[i], `l${i}`))}

      {/* Свет в окнах — на последнем шаге. */}
      {WINDOWS.map((d, i) => (
        <path
          key={`glow-${i}`}
          d={d.split(' M')[0]}
          fill={BRASS}
          style={{
            fillOpacity: stage >= 4 ? 0.3 : 0,
            transition: animate ? `fill-opacity 0.9s ease ${0.25 + (i % 5) * 0.1}s` : 'none',
          }}
        />
      ))}

      {/* Кран уходит, когда дом сдан. */}
      <g style={shown(stage < 4)}>
        {CRANE.map((l, i) => (
          <path
            key={`crane-${i}`}
            d={l.d}
            pathLength={1}
            stroke={BRASS_LIGHT}
            strokeWidth={l.w}
            strokeLinejoin="round"
            strokeLinecap="round"
            style={drawn(l.s, CRANE_ORDER[i] + 2, 1.5)}
          />
        ))}
      </g>

      {FINISH.map((l, i) => path(l, FINISH_ORDER[i] + 1, `f${i}`))}

      {/* Подписи: марки осей, отметки уровней, размер. */}
      <g className="max-sm:hidden" fill={GRAY} fontSize="8.5" style={{ fontVariantNumeric: 'tabular-nums' }}>
        <g style={shown(stage >= 1, 0.3)}>
          {AXES.map((x, i) => (
            <g key={x}>
              <circle cx={x} cy={380} r={8} fill="none" stroke={GRAY} strokeWidth="0.7" />
              <text x={x} y={383} textAnchor="middle">
                {i + 1}
              </text>
            </g>
          ))}
          <text x={220} y={357} textAnchor="middle">
            18 000
          </text>
        </g>
        <g style={shown(stage >= 2, 0.4)}>
          {LEVELS.map((y, i) => (
            <text key={y} x={58} y={y - 3}>
              {LEVEL_TEXT[i]}
            </text>
          ))}
        </g>
      </g>

      {/* Штамп листа: номер листа и стадия — вместе с шагом. */}
      <g className="max-sm:hidden">
        <path d="M336 370h130v36H336ZM376 370v36M336 388h130" stroke="#FBF9F5" strokeOpacity="0.22" strokeWidth="0.7" />
        <g fontSize="7.5" fill={GRAY}>
          <text x={341} y={382}>
            Лист
          </text>
          <text x={341} y={400}>
            Стадия
          </text>
        </g>
        <g fontSize="9" fill={BRASS_LIGHT}>
          <text x={382} y={382}>
            {stage > 0 ? `${stage} из 4` : '—'}
          </text>
          <text x={382} y={400}>
            {stage > 0 ? STAGE_NAMES[stage - 1] : '—'}
          </text>
        </g>
      </g>

      {/* Печать со знаком весов — когда дом сдан. */}
      <g
        style={{
          opacity: stage >= 4 ? 1 : 0,
          transform: `rotate(-12deg) scale(${stage >= 4 ? 1 : 1.35})`,
          transformBox: 'fill-box',
          transformOrigin: 'center',
          transition: animate ? 'opacity 0.5s ease 0.9s, transform 0.6s cubic-bezier(0.22, 1, 0.36, 1) 0.9s' : 'none',
        }}
      >
        <circle cx={410} cy={292} r={27} stroke={BRASS} strokeWidth="1.4" />
        <circle cx={410} cy={292} r={22.5} stroke={BRASS} strokeWidth="0.7" />
        <g transform="translate(395.1 279.2) scale(0.62)" fill={BRASS} stroke={BRASS} strokeLinecap="round" strokeLinejoin="round">
          <path d="M3.2 12.6 24 3.6l20.8 9Z" fill="none" strokeWidth="2" />
          <path d="M24 12.6v20" fill="none" strokeWidth="2.2" />
          <path d="M5.2 13.4.6 25.2m4.6-11.8 4.6 11.8m33-11.8-4.6 11.8m4.6-11.8 4.6 11.8" fill="none" strokeWidth="1.2" />
          <path d="M-.4 25.2h11.2q-5.6 7.2-11.2 0Zm37.6 0h11.2q-5.6 7.2-11.2 0Z" stroke="none" />
          <path d="M20.4 32.4h7.2l2.2 4.2H18.2Z" stroke="none" />
          <path d="M16.2 37.9h15.6" fill="none" strokeWidth="1.5" />
        </g>
      </g>
    </svg>
  )
}
