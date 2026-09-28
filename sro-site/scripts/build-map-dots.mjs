// Точечная карта России для раздела «География» (с 28.09.2026).
//
// Берёт настоящие границы субъектов из src/content/mapData.ts (их готовит
// scripts/build-map.py) и раскладывает по стране шестиугольную сетку точек:
// каждая точка знает, в каком выделенном регионе она стоит, или стоит в
// остальной стране. Пишет src/content/mapDots.ts — руками его не править.
//
// Почему точки, а не заливка контуров. Заливкой большие регионы (Красноярский
// край, Якутия) ложились сплошными пятнами и перетягивали на себя весь раздел,
// а карта выглядела картинкой из справочника. Точечная сетка — приём
// дорогих сайтов: та же география, но лёгкая, и выделение читается цветом
// точек, а не массой.
//
// Маленькому региону (Москва, Крым) может не достаться ни одной точки сетки —
// тогда ему ставится одна точка в его метке (MAP_ANCHORS): регион из списка
// не должен пропасть с карты.
//
//   node scripts/build-map-dots.mjs      # из sro-site/
import { readFileSync, writeFileSync } from 'node:fs'

const SRC = 'src/content/mapData.ts'
const OUT = 'src/content/mapDots.ts'
const STEP = 11 // шаг сетки в единицах viewBox (1000 × 544)

const text = readFileSync(SRC, 'utf8')
const base = text.match(/export const MAP_BASE = '([^']+)'/)[1]
const activeBlock = text.match(/export const MAP_ACTIVE[^{]*\{([\s\S]*?)\n\}/)[1]
const active = Object.fromEntries([...activeBlock.matchAll(/(\w+):\s*'([^']+)'/g)].map((m) => [m[1], m[2]]))
const anchorBlock = text.match(/export const MAP_ANCHORS[^{]*\{([\s\S]*?)\n\}/)[1]
const anchors = Object.fromEntries(
  [...anchorBlock.matchAll(/(\w+):\s*\{\s*x:\s*([\d.]+),\s*y:\s*([\d.]+)\s*\}/g)].map((m) => [m[1], [+m[2], +m[3]]]),
)
const [, , width, height] = text.match(/VIEW_BOX = '([^']+)'/)[1].split(' ').map(Number)

// Контур — только M, L и Z (так пишет build-map.py): разбираем в кольца.
function rings(d) {
  const out = []
  let ring = null
  for (const [, cmd, args] of d.matchAll(/([MLZ])([^MLZ]*)/g)) {
    if (cmd === 'Z') {
      if (ring) out.push(ring)
      ring = null
      continue
    }
    const nums = args.trim().split(/[\s,]+/).filter(Boolean).map(Number)
    if (cmd === 'M') {
      if (ring) out.push(ring)
      ring = []
    }
    for (let i = 0; i < nums.length; i += 2) ring.push([nums[i], nums[i + 1]])
  }
  if (ring) out.push(ring)
  return out
}

// Чёт-нечет, как у fill-rule="evenodd" на карте: анклавы остаются дырами.
function inside(pt, rs) {
  let hit = false
  for (const r of rs) {
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const [xi, yi] = r[i]
      const [xj, yj] = r[j]
      if (yi > pt[1] !== yj > pt[1] && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) hit = !hit
    }
  }
  return hit
}

const baseRings = rings(base)
const activeRings = Object.fromEntries(Object.entries(active).map(([k, d]) => [k, rings(d)]))

const baseDots = []
const activeDots = Object.fromEntries(Object.keys(active).map((k) => [k, []]))
const rowH = (STEP * Math.sqrt(3)) / 2
for (let row = 0, y = STEP / 2; y < height; row++, y += rowH) {
  for (let x = STEP / 2 + (row % 2 ? STEP / 2 : 0); x < width; x += STEP) {
    const pt = [x, y]
    const key = Object.keys(activeRings).find((k) => inside(pt, activeRings[k]))
    if (key) activeDots[key].push(pt)
    else if (inside(pt, baseRings)) baseDots.push(pt)
  }
}
for (const [key, dots] of Object.entries(activeDots)) {
  if (!dots.length && anchors[key]) dots.push(anchors[key])
}

const fmt = (dots) => dots.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
const total = baseDots.length + Object.values(activeDots).reduce((n, d) => n + d.length, 0)
writeFileSync(
  OUT,
  `// Сгенерировано scripts/build-map-dots.mjs из mapData.ts — руками не править.
// Точки шестиугольной сетки с шагом ${STEP} в координатах VIEW_BOX: «x,y x,y …».

export const DOT_STEP = ${STEP}

// Остальная страна.
export const DOTS_BASE = '${fmt(baseDots)}'

// Выделенные регионы: ключ — тот же, что в MAP_ACTIVE и regions.ts.
export const DOTS_ACTIVE: Record<string, string> = {
${Object.entries(activeDots).map(([k, d]) => `  ${k}: '${fmt(d)}',`).join('\n')}
}
`,
)
console.log(`${OUT}: ${total} точек, из них в регионах ${total - baseDots.length}`)
for (const [k, d] of Object.entries(activeDots)) console.log(`  ${k}: ${d.length}`)
