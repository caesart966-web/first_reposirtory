// Воздух вокруг текста: строки соседних блоков не наезжают друг на друга,
// текст не прижат к линейкам.
//
// ЗАЧЕМ. 15.10.2026 заказчик прислал снимок «Обо мне»: хвост курсивного «р»
// в заголовке шапки лёг на абзац под ним, а цифры «112+» и «10» стояли
// вплотную к вертикальной линейке соседней колонки. Ни одна проверка этого
// не видела: test-widths ищет вылезший текст и наезд блоков, но абзац под
// заголовком не вылезает и не наезжает — между блоками ноль, а буквы
// при этом сцепились. Контраст, ширины, таблицы — всё было зелёным.
//
// ЧТО МЕРЯЕТСЯ — сами буквы, а не рамки блоков. Браузер отдаёт прямоугольник
// каждой строки (Range.getClientRects) по высоте шрифта, а в нём буквы
// занимают разное место: у «НОРМА» капсом низ пустой, у «работаю» там висит
// хвост «р». Поэтому для близких пар знаки строки меряются на холсте тем же
// шрифтом (measureText), и сравниваются низ букв верхней строки и верх букв
// нижней.
//
// 1. Строки двух РАЗНЫХ блоков друг над другом (заголовок и абзац, подпись
//    и значение) расходятся хотя бы на MIN_INK_GAP px и не меньше MIN_INK_EM
//    от кегля крупной из двух: подписи «Телефон» над номером хватает 4 px,
//    под заголовком в 52 px нужно 6. Строки одного абзаца не сравниваются.
// 2. Текст рядом с вертикальной линейкой (рамкой в 1–3 px, своей или соседа)
//    стоит от неё не ближе MIN_RULE_GAP. Круги и пилюли — не линейки.
//
// Порог проверен на сборке v51: она падает на «Обо мне» (заголовок и цифры),
// на карточках городов главной на телефоне и на шапках городов, партнёров,
// словаря и поиска; нынешняя проходит.
//
// Запуск: node scripts/test-spacing.mjs [адрес]   (сайт — npm run build)

import { readFileSync } from 'node:fs'
import { chromium } from './lib/browser.mjs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const MIN_INK_GAP = 4
const MIN_INK_EM = 0.12
const MIN_RULE_GAP = 8
const WIDTHS = [390, 768, 1280, 1440]

// Все страницы из карты сайта плюс две, которых в ней нет нарочно.
const map = readFileSync('dist/sitemap-0.xml', 'utf8')
const PAGES = [
  ...[...map.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => new URL(m[1]).pathname),
  '/poisk/',
  '/404.html',
]

/** Выполняется на странице: возвращает найденные места. */
function measure({ MIN_INK_GAP, MIN_INK_EM, MIN_RULE_GAP }) {
  const shown = (el) =>
    el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }) &&
    !el.closest('svg, [hidden], .contact-rail, .cookie, .vh, .hp-field')
  const blockOf = (el) => {
    while (el && getComputedStyle(el).display.startsWith('inline') && el.parentElement) el = el.parentElement
    return el
  }
  const name = (s) => s.replace(/\s+/g, ' ').trim().slice(0, 40)

  // Строки текста
  const lines = []
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  const range = document.createRange()
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (!n.data.trim()) continue
    const el = n.parentElement
    if (!el || !shown(el)) continue
    const cs = getComputedStyle(el)
    if (cs.position === 'fixed') continue
    // Текст, срезанный до пикселя (visually-hidden), — для голоса, не для глаз.
    const r0 = el.getBoundingClientRect()
    if (r0.width <= 2 || r0.height <= 2) continue
    range.selectNodeContents(n)
    const block = blockOf(el)
    for (const r of range.getClientRects()) {
      if (r.width < 2 || r.height < 2) continue
      lines.push({
        l: r.left, r: r.right, t: r.top + scrollY, b: r.bottom + scrollY,
        block, node: n, text: n.data, fs: parseFloat(cs.fontSize),
      })
    }
  }

  // Очертания букв строки. Прямоугольник строки — высота шрифта целиком:
  // у «НОРМА» капсом под ним пусто там, где у «работаю» висит хвост «р».
  // Поэтому для пар-кандидатов знаки строки меряются на холсте тем же
  // шрифтом (measureText: actualBoundingBox — сами буквы, fontBoundingBox —
  // высота шрифта), и верх с низом букв ставятся от линии шрифта.
  const ctx = document.createElement('canvas').getContext('2d')
  const ink = (ln) => {
    if (ln.ink) return ln.ink
    const n = ln.node
    let s = ''
    for (let i = 0; i < n.data.length; i++) {
      range.setStart(n, i)
      range.setEnd(n, i + 1)
      for (const r of range.getClientRects()) {
        if (Math.abs(r.top + scrollY - ln.t) < 1 && r.left >= ln.l - 1 && r.right <= ln.r + 1) {
          s += n.data[i]
          break
        }
      }
    }
    const cs = getComputedStyle(n.parentElement)
    if (cs.textTransform === 'uppercase') s = s.toUpperCase()
    ctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`
    const m = ctx.measureText(s.trim() || n.data.trim())
    const A = m.fontBoundingBoxAscent
    const D = m.fontBoundingBoxDescent
    const base = ln.t + ((ln.b - ln.t) * A) / (A + D)
    ln.ink = { t: base - m.actualBoundingBoxAscent, b: base + m.actualBoundingBoxDescent, s: s.trim() }
    return ln.ink
  }

  const found = []

  // 1. Наезд строк разных блоков
  lines.sort((a, b) => a.t - b.t)
  for (let i = 0; i < lines.length; i++) {
    const a = lines[i]
    for (let j = i + 1; j < lines.length && lines[j].t < a.b + 12; j++) {
      const b = lines[j]
      if (a.block === b.block || a.block.contains(b.block) || b.block.contains(a.block)) continue
      const hOverlap = Math.min(a.r, b.r) - Math.max(a.l, b.l)
      if (hOverlap < 4) continue
      // Друг над другом, а не в одной строке: верх нижней ниже верха верхней
      // хотя бы на треть её высоты. Иначе это соседи по строке (значок
      // и подпись в одном ряду), и их разводит не межстрочный воздух.
      const upper = a.t <= b.t ? a : b
      const lower = upper === a ? b : a
      if (lower.t - upper.t < (upper.b - upper.t) / 3) continue
      // Сколько воздуха нужно — от кегля: подписи «Телефон» над номером
      // хватает 4 px, а под заголовком в 52 px те же 4 px — уже наезд.
      const need = Math.max(MIN_INK_GAP, MIN_INK_EM * Math.max(upper.fs, lower.fs))
      if (lower.t - upper.b >= need) continue
      const gap = ink(lower).t - ink(upper).b
      if (gap < need) {
        found.push({
          kind: 'строки сцепились',
          gap: Math.round(gap),
          a: name(ink(upper).s),
          b: name(ink(lower).s),
          y: Math.round(upper.b),
        })
      }
    }
  }

  // 2. Текст у вертикальной линейки
  const rules = []
  for (const el of document.body.querySelectorAll('*')) {
    if (el.closest('svg') || !shown(el)) continue
    const cs = getComputedStyle(el)
    if (cs.position === 'fixed') continue
    const r = el.getBoundingClientRect()
    if (r.height < 16) continue
    // Круг и пилюля — не стенка: «или» в кружке стоит у его края по дуге.
    if (parseFloat(cs.borderTopLeftRadius) >= Math.min(r.width, r.height) * 0.4) continue
    for (const side of ['left', 'right']) {
      const w = parseFloat(cs[`border-${side}-width`])
      if (!w || w > 3 || cs[`border-${side}-style`] === 'none') continue
      if (/rgba\([^)]*,\s*0\)|transparent/.test(cs[`border-${side}-color`])) continue
      const x0 = side === 'left' ? r.left : r.right - w
      rules.push({ el, x0, x1: x0 + w, t: r.top + scrollY, b: r.bottom + scrollY })
    }
  }
  for (const rule of rules) {
    for (const ln of lines) {
      const vOverlap = Math.min(rule.b, ln.b) - Math.max(rule.t, ln.t)
      if (vOverlap < (ln.b - ln.t) / 2) continue
      let gap
      if (ln.l >= rule.x1) gap = ln.l - rule.x1
      else if (ln.r <= rule.x0) gap = rule.x0 - ln.r
      else continue // линейка под текстом насквозь — это подчёркивание или рамка поля, не стенка
      if (gap < MIN_RULE_GAP) {
        found.push({
          kind: 'текст у линейки',
          gap: Math.round(gap),
          a: name(ln.text),
          b: `${rule.el.tagName.toLowerCase()}.${[...rule.el.classList].join('.')}`,
          y: Math.round(ln.t),
        })
      }
    }
  }
  return found
}

const browser = await chromium.launch()
let failed = 0
let checked = 0
for (const width of WIDTHS) {
  const ctx = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  for (const path of PAGES) {
    await page.goto(BASE + path, { waitUntil: 'networkidle' })
    await page.evaluate(() => document.fonts.ready)
    const found = await page.evaluate(measure, { MIN_INK_GAP, MIN_INK_EM, MIN_RULE_GAP })
    checked++
    const seen = new Set()
    for (const f of found) {
      const key = `${f.kind}|${f.a}|${f.b}`
      if (seen.has(key)) continue
      seen.add(key)
      failed++
      console.log(`✗ ${path} при ${width}px — ${f.kind} (${f.gap} px): «${f.a}» / «${f.b}», y=${f.y}`)
    }
  }
  await ctx.close()
}
await browser.close()

if (failed) {
  console.log(`\n✗ Тесно в ${failed} местах.`)
  process.exit(1)
}
console.log(`✓ Строки не сцепляются, текст не прижат к линейкам: ${PAGES.length} страниц на ${WIDTHS.length} ширинах (${checked} замеров).`)
