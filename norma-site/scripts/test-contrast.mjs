// Проверяет контраст текста к фону на всех страницах сайта.
//
// Зачем отдельно от test-video-contrast.mjs: тот смотрит настоящие пиксели,
// но только на первом экране, где под текстом видео. Этот проверяет всё
// остальное — обычный текст на обычном фоне, зато на всех страницах разом.
//
// Что он поймал при написании: в новой тёмной секции выделенное слово
// в заголовке осталось тёмно-синим на тёмно-синем — 3.3:1 при норме 4.5.
// Глазами это выглядит как «просто синее слово», а на телефоне при ярком
// свете не читается вовсе. Правило, которое красит такие слова в светлый
// оттенок, перечисляло секции поимённо и новую не знало.
//
// Запуск: node scripts/test-contrast.mjs [адрес]

import { chromium } from 'playwright'
import { readdir } from 'node:fs/promises'
import { join } from 'node:path'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const DIST = 'dist'

// Первый экран проверяется по настоящим кадрам видео в test-video-contrast.mjs:
// под текстом там движущаяся картинка, и статический расчёт по цвету фона
// дал бы неверный ответ в обе стороны.
const SKIP_INSIDE = ['.hero']

/** Собираем список страниц из сборки, чтобы новая страница попадала под проверку сама. */
async function pages(dir = DIST, prefix = '/') {
  const out = []
  for (const e of await readdir(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      if (['_astro', 'fonts', 'video', 'api'].includes(e.name)) continue
      out.push(...(await pages(join(dir, e.name), prefix + e.name + '/')))
    } else if (e.name === 'index.html') {
      out.push(prefix)
    }
  }
  return out.sort()
}

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } })
const page = await ctx.newPage()

const list = await pages()
let failed = 0
let checked = 0
const unknown = new Map()

for (const path of list) {
  await page.goto(BASE + path, { waitUntil: 'domcontentloaded' })

  const found = await page.evaluate((skipInside) => {
    const lum = (css) => {
      const m = css.match(/[\d.]+/g)
      if (!m) return null
      const [r, g, b, a = '1'] = m.map(Number)
      if (a < 1) return null // полупрозрачный — эффективный цвет не вычислить
      const f = (v) => {
        v /= 255
        return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
      }
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    }

    const results = []
    const unsure = []

    for (const el of document.querySelectorAll('body *')) {
      if (skipInside.some((sel) => el.closest(sel))) continue

      // Только элементы с собственным текстом: иначе один и тот же текст
      // проверялся бы столько раз, сколько над ним обёрток.
      const own = [...el.childNodes]
        .filter((n) => n.nodeType === 3 && n.textContent.trim().length > 1)
        .map((n) => n.textContent.trim())
        .join(' ')
      if (!own) continue

      const cs = getComputedStyle(el)
      if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') continue
      if (!el.getClientRects().length) continue

      const fg = lum(cs.color)
      if (fg === null) continue

      // Фон ищем вверх по дереву до первого непрозрачного цвета.
      // Картинка или градиент по дороге означают, что цвет фона неизвестен:
      // такие места отмечаем отдельно, а не выдаём ложный вердикт.
      let node = el
      let bg = null
      let blocked = null
      while (node && node !== document.documentElement.parentNode) {
        const s = getComputedStyle(node)
        if (s.backgroundImage && s.backgroundImage !== 'none') {
          blocked = node.className?.toString().split(' ')[0] || node.tagName.toLowerCase()
          break
        }
        const l = lum(s.backgroundColor)
        if (l !== null) { bg = l; break }
        node = node.parentElement
      }

      const label = (el.className?.toString().split(' ')[0] || el.tagName.toLowerCase())
      if (blocked !== null) { unsure.push(`${el.tagName.toLowerCase()}.${label} (в ${blocked})`); continue }
      if (bg === null) continue

      const ratio = (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05)

      // Крупный текст по стандарту: от 24px, либо от 18.66px полужирным.
      const size = parseFloat(cs.fontSize)
      const bold = parseInt(cs.fontWeight, 10) >= 700
      const big = size >= 24 || (bold && size >= 18.66)
      const need = big ? 3 : 4.5

      results.push({ ok: ratio >= need, ratio: +ratio.toFixed(2), need, label, tag: el.tagName.toLowerCase(), text: own.slice(0, 40) })
    }
    return { results, unsure }
  }, SKIP_INSIDE)

  checked += found.results.length
  const bad = found.results.filter((r) => !r.ok)
  for (const u of found.unsure) unknown.set(u, (unknown.get(u) || 0) + 1)

  if (bad.length) {
    failed += bad.length
    console.log(`✗ ${path}`)
    // Одинаковые места на странице повторяются — показываем каждое один раз.
    const seen = new Set()
    for (const r of bad) {
      const key = `${r.tag}.${r.label}:${r.ratio}`
      if (seen.has(key)) continue
      seen.add(key)
      console.log(`    ${r.tag}.${r.label} — ${r.ratio}:1 при норме ${r.need} · «${r.text}»`)
    }
  } else {
    console.log(`✓ ${path.padEnd(42)} ${found.results.length} надписей`)
  }
}

await browser.close()

if (unknown.size) {
  console.log(`\nНе проверено автоматически (под картинкой или градиентом — цвет фона не вычислить):`)
  for (const [k, n] of [...unknown].sort((a, b) => b[1] - a[1]).slice(0, 8)) {
    console.log(`  · ${k} — ${n} шт.`)
  }
  console.log('  Первый экран проверяется по настоящим кадрам: scripts/test-video-contrast.mjs')
}

if (failed) {
  console.log(`\nОШИБОК: ${failed}. Текст читается хуже нормы.
Частая причина: тёмная секция без класса section--dark — тогда выделенное
слово в заголовке остаётся тёмно-синим на тёмно-синем.`)
  process.exit(1)
}
console.log(`\n✓ Контраст в норме: ${checked} надписей на ${list.length} страницах.`)
