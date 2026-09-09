// Проверка городских страниц — защита от дорвеев.
//
// Запуск: node scripts/test-regions.mjs   (входит в npm test)
//
// ЧТО ТАКОЕ ДОРВЕЙ И ПОЧЕМУ ЭТО ОПАСНО. Самый простой способ «покрыть города» —
// сделать одну страницу и размножить её, подменив название. Яндекс и Google
// такое распознают и наказывают не отдельную страницу, а сайт целиком:
// в правилах Яндекса это прямо названо «дорвеями». То есть попытка занять
// городские запросы дёшево стоит всех остальных запросов разом.
//
// Поэтому здесь меряется не «есть ли страница», а сколько на ней текста,
// которого нет ни на одной другой городской странице. Порог намеренно
// с запасом: сегодня страницы дают 22–25 %, порог стоит на 18 %.
// Клон свалится сразу и заметно.
//
// Заодно проверяется, что страница не тупик: с неё есть ходы в разбор
// регионального принципа, в стоимость и в проверку реестров.

import { readFileSync, readdirSync, existsSync } from 'node:fs'
import { join } from 'node:path'
import { REGIONS } from '../src/config/regions.ts'

const DIST = 'dist'
const problems = []
const bad = (m) => problems.push(m)
let checks = 0

const MIN_UNIQUE_SHARE = 0.18
const MIN_UNIQUE_CHARS = 900

if (!existsSync(join(DIST, 'sro'))) {
  console.error('✗ Нет собранных городских страниц. Сначала: npm run build')
  process.exit(1)
}

const textOf = (html) =>
  (html.match(/<main[^>]*>([\s\S]*)<\/main>/) || ['', ''])[1]
    .replace(/<(script|style|svg)[\s\S]*?<\/\1>/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&[a-z]+;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const pages = REGIONS.map((r) => {
  const file = join(DIST, 'sro', r.slug, 'index.html')
  if (!existsSync(file)) {
    bad(`нет страницы города ${r.city} (${file})`)
    return null
  }
  const html = readFileSync(file, 'utf8')
  return { r, html, text: textOf(html) }
}).filter(Boolean)

// ── Содержимое: город назван, субъект назван, ходы дальше есть ────────────
for (const { r, html, text } of pages) {
  const url = `/sro/${r.slug}/`

  checks++
  const h1 = (html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/) || ['', ''])[1].replace(/<[^>]+>/g, '')
  if (!h1.includes(r.inCity)) bad(`${url}: в заголовке H1 нет «${r.inCity}» — страница не отвечает на запрос с городом`)

  checks++
  if (!text.includes(r.subject)) bad(`${url}: не назван субъект РФ «${r.subject}»`)

  checks++
  if (!text.includes(r.trap.slice(0, 40))) bad(`${url}: нет разбора ошибки, который написан для этого города`)

  checks++
  for (const n of r.neighbours) {
    if (!text.includes(n.name.split(' —')[0])) {
      bad(`${url}: в списке соседних субъектов нет «${n.name}»`)
      break
    }
  }

  // Страница не должна быть тупиком: с неё ведут в разбор нормы,
  // в стоимость и в проверку реестров.
  checks++
  for (const target of ['/baza-znaniy/regionalnyy-princip/', '/stoimost/', '/proverit-sro/']) {
    if (!html.includes(`href="${target}"`) && !html.includes(target)) {
      bad(`${url}: нет ссылки на ${target} — страница получается тупиком`)
    }
  }

  checks++
  const title = (html.match(/<title>([^<]*)<\/title>/) || ['', ''])[1]
  if (!title.includes(r.inCity)) bad(`${url}: в заголовке вкладки нет «${r.inCity}»`)
}

// ── Уникальность: сколько текста есть ТОЛЬКО здесь ───────────────────────
const shingles = (t) => {
  const w = t.split(' ')
  const s = new Set()
  for (let i = 0; i + 6 <= w.length; i++) s.add(w.slice(i, i + 6).join(' '))
  return s
}

const sets = pages.map((p) => ({ ...p, s: shingles(p.text) }))
const seen = new Map()
for (const p of sets) for (const x of p.s) seen.set(x, (seen.get(x) || 0) + 1)

for (const p of sets) {
  let uniqueCount = 0
  let uniqueChars = 0
  for (const x of p.s) {
    if (seen.get(x) === 1) {
      uniqueCount++
      uniqueChars += x.length
    }
  }
  const share = uniqueCount / p.s.size
  // Знаки в шинглах пересекаются между собой, поэтому делим на длину окна:
  // получается честная оценка объёма собственного текста.
  const ownChars = Math.round(uniqueChars / 6)

  checks++
  if (share < MIN_UNIQUE_SHARE) {
    bad(
      `/sro/${p.r.slug}/: только ${(share * 100).toFixed(1)}% текста не встречается на других городских страницах ` +
        `(нужно ${(MIN_UNIQUE_SHARE * 100).toFixed(0)}%). Это признак дорвея — напишите городу свой разбор в src/config/regions.ts`,
    )
  }
  checks++
  if (ownChars < MIN_UNIQUE_CHARS) {
    bad(
      `/sro/${p.r.slug}/: собственного текста примерно ${ownChars} знаков, нужно от ${MIN_UNIQUE_CHARS}`,
    )
  }
}

// ── Оглавление ведёт на каждый город ─────────────────────────────────────
const indexFile = join(DIST, 'sro', 'index.html')
if (!existsSync(indexFile)) bad('нет оглавления /sro/')
else {
  const index = readFileSync(indexFile, 'utf8')
  for (const r of REGIONS) {
    checks++
    if (!index.includes(`/sro/${r.slug}/`)) bad(`оглавление /sro/ не ведёт на ${r.city}`)
  }
}

// ── Города в карте сайта ─────────────────────────────────────────────────
const maps = readdirSync(DIST).filter((f) => /^sitemap-\d+\.xml$/.test(f))
const sitemap = maps.map((f) => readFileSync(join(DIST, f), 'utf8')).join('')
for (const r of REGIONS) {
  checks++
  if (!sitemap.includes(`/sro/${r.slug}/`)) bad(`города ${r.city} нет в карте сайта`)
}

if (problems.length > 0) {
  console.error(`✗ Городские страницы (${problems.length}):`)
  problems.forEach((p) => console.error(`  · ${p}`))
  process.exit(1)
}

const shares = sets.map((p) => {
  let u = 0
  for (const x of p.s) if (seen.get(x) === 1) u++
  return u / p.s.size
})
const min = Math.min(...shares) * 100
const max = Math.max(...shares) * 100
console.log(
  `✓ Городские страницы в порядке: ${pages.length} городов, ${checks} проверок. ` +
    `Собственного текста на странице ${min.toFixed(0)}–${max.toFixed(0)}% при пороге ${MIN_UNIQUE_SHARE * 100}%.`,
)
