// Проверка доступности axe-core (WCAG 2.0–2.2 A/AA и best practice) на всех
// страницах сайта при 390 и 1440 px.
//
// До 23.10.2026 она жила только в рабочей папке сессии, а в отчётах стояло
// «axe — 0 нарушений»; повторить это было нечем (нашла экскурсия diff-tour).
// axe-core в зависимостях сайта нет: файл берётся из пакета npm.
//
//   npm pack axe-core@4.10.2 && tar xzf axe-core-4.10.2.tgz   # → package/axe.min.js
//   npm run build && npx vite preview --port 4181 &
//   AXE=package/axe.min.js node scripts/test-axe.mjs
//
// Playwright — как в test-site.mjs: из переменной PLAYWRIGHT, если лежит не рядом.
// Страницы — те же, что у test-site.mjs: одиннадцать и статьи обходом папки stati/.
import { existsSync, readdirSync, readFileSync } from 'node:fs'
const pw = await import(process.env.PLAYWRIGHT || 'playwright-core')
const { chromium } = pw.default ?? pw

const BASE = process.env.BASE || 'http://localhost:4181/'
if (!process.env.AXE || !existsSync(process.env.AXE)) {
  console.error('Нужен путь к axe.min.js в переменной AXE (см. начало файла).')
  process.exit(2)
}
const axeSrc = readFileSync(process.env.AXE, 'utf8')
const STATI = new URL('../stati/', import.meta.url)
const PAGES = ['', 'sro-stroiteley/', 'sro-proektirovshchikov/', 'sro-izyskateley/',
  'uslugi/vstuplenie-v-sro/', 'uslugi/podbor-i-proverka-sro/', 'uslugi/dokumenty/',
  'uslugi/specialisty-nrs/', 'uslugi/nok/', 'uslugi/uroven-otvetstvennosti/',
  'uslugi/soprovozhdenie-proverok/',
  ...(existsSync(STATI)
    ? ['stati/', ...readdirSync(STATI, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => `stati/${d.name}/`)]
    : []),
  '404.html']

const b = await chromium.launch({ executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium' })
const found = {}
for (const [W, H, mobile] of [[390, 844, true], [1440, 900, false]]) {
  for (const path of PAGES) {
    const ctx = await b.newContext({ viewport: { width: W, height: H }, isMobile: mobile, hasTouch: mobile, reducedMotion: 'reduce' })
    const p = await ctx.newPage()
    await p.goto(BASE + path, { waitUntil: 'networkidle' })
    // Прокрутка до конца — чтобы проявились блоки и подгрузились картинки.
    await p.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 600) {
        scrollTo(0, y)
        await new Promise((r) => setTimeout(r, 30))
      }
      scrollTo(0, 0)
    })
    await p.waitForTimeout(400)
    await p.addScriptTag({ content: axeSrc })
    const violations = await p.evaluate(async () => {
      const res = await window.axe.run(document, {
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'] },
      })
      return res.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, n: v.nodes.length, first: v.nodes[0]?.target.join(' ') }))
    })
    for (const v of violations) {
      found[v.id] ??= { ...v, n: 0, where: [] }
      found[v.id].n += v.n
      found[v.id].where.push(`${W}:/${path} → ${v.first}`)
    }
    await ctx.close()
  }
}
await b.close()

for (const [id, v] of Object.entries(found)) {
  console.log(`\n[${v.impact}] ${id} — ${v.help} — узлов ${v.n}`)
  for (const w of v.where.slice(0, 6)) console.log('   ', w)
}
const rules = Object.keys(found).length
console.log(`\n${PAGES.length} страниц × 2 ширины, правил с нарушениями: ${rules}`)
process.exit(rules ? 1 : 0)
