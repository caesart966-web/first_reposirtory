#!/usr/bin/env node
// PDF брендбуков: node brandbooks/make-pdf.mjs → brandbooks/pdf/*.pdf
//
// Запускать после node brandbooks/build.mjs: печатаются готовые файлы.
//
// Страница режется по разделам: каждый раздел — отдельная страница своей
// высоты, ширина у всех 1440 px. На листах A4 раздел рвался бы посередине,
// а тёмный фон обрывался бы белой полосой внизу листа. Короткие блоки
// (оглавление-полоса, выходные данные) уходят на страницу к соседу:
// страница высотой в триста пикселей читается обрывком.
//
// Шрифты Google Fonts браузер получает через Node: за прокси со своим
// сертификатом браузер их не загрузит, а PDF молча уйдёт запасной Georgia.
// Поэтому перед печатью проверяется, что фирменные шрифты действительно
// загружены, и после — что страниц ровно столько, сколько разделов: лишняя
// страница значит, что раздел не поместился и на новую страницу ушла
// полоска.

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { execSync } from 'node:child_process'

const HERE = dirname(fileURLToPath(import.meta.url))
const OUT = join(HERE, 'pdf')
const WIDTH = 1440
const MERGE_BELOW = 520 // px: блок ниже этого уходит на страницу к соседу

const BOOKS = [
  { id: 'norma', fonts: ['Literata', 'Golos Text'] },
  { id: 'biznes-grupp', fonts: ['Brygada 1918', 'Onest'] },
  { id: 'x-pto', fonts: ['Geologica', 'Inter', 'JetBrains Mono'] },
]

async function loadPlaywright() {
  try {
    return await import('playwright')
  } catch {}
  try {
    const root = execSync('npm root -g', { encoding: 'utf8' }).trim()
    return await import(pathToFileURL(join(root, 'playwright', 'index.mjs')).href)
  } catch {}
  console.error('Нужен playwright: npm i -g playwright && npx playwright install chromium')
  process.exit(1)
}

const { chromium } = await loadPlaywright()
const browser = await chromium.launch()
mkdirSync(OUT, { recursive: true })
let failed = 0

for (const book of BOOKS) {
  const ctx = await browser.newContext({ viewport: { width: WIDTH, height: 1000 }, colorScheme: 'light', reducedMotion: 'reduce' })
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, async (route) => {
    const req = route.request()
    const res = await fetch(req.url(), { headers: { 'user-agent': req.headers()['user-agent'] } })
    await route.fulfill({
      status: res.status,
      body: Buffer.from(await res.arrayBuffer()),
      headers: { 'content-type': res.headers.get('content-type') || 'application/octet-stream', 'access-control-allow-origin': '*' },
    })
  })
  const page = await ctx.newPage()
  await page.goto(pathToFileURL(join(HERE, `${book.id}.html`)).href, { waitUntil: 'networkidle' })
  await page.evaluate(() => document.fonts.ready)

  const loaded = await page.evaluate(() => [...new Set([...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family.replace(/"/g, '')))])
  const missing = book.fonts.filter((f) => !loaded.includes(f))
  if (missing.length) {
    console.error(`✗ ${book.id}: не загрузились шрифты ${missing.join(', ')} — PDF ушёл бы с запасными`)
    failed++
    await ctx.close()
    continue
  }

  // В PDF не нужны подсказки и кнопки, которые работают только на экране.
  await page.addStyleTag({ content: '.pdf-hide, [data-play], .toast, .dim { display: none !important; }' })
  await page.waitForTimeout(300)

  // Разделы по порядку и их высоты; короткие — к соседу.
  const pages = await page.evaluate(({ width, mergeBelow }) => {
    const els = [...document.querySelectorAll('body > header, body > nav, body > section, body > main > section, body > footer')]
    const chunks = []
    for (const el of els) {
      const h = el.getBoundingClientRect().height
      if (h < mergeBelow && chunks.length) chunks[chunks.length - 1].push(el)
      else chunks.push([el])
    }
    // Ширина по умолчанию — та же: по ней браузер считает медиазапросы,
    // и без неё печать собиралась мобильной вёрсткой (лист Letter, 816 px).
    const css = [`@page { size: ${width}px 1000px; margin: 0; }`]
    chunks.forEach((group, i) => {
      const top = group[0].getBoundingClientRect().top
      const bottom = group[group.length - 1].getBoundingClientRect().bottom
      const h = Math.ceil(bottom - top)
      css.push(`@page c${i} { size: ${width}px ${h}px; margin: 0; }`)
      group.forEach((el) => { el.style.page = `c${i}` })
    })
    const style = document.createElement('style')
    style.textContent = css.join('\n')
    document.head.appendChild(style)
    return chunks.length
  }, { width: WIDTH, mergeBelow: MERGE_BELOW })

  await page.emulateMedia({ media: 'screen' })
  const file = join(OUT, `${book.id}.pdf`)
  writeFileSync(file, await page.pdf({ width: `${WIDTH}px`, height: '1000px', printBackground: true, preferCSSPageSize: true }))

  const got = (readFileSync(file, 'latin1').match(/\/Type\s*\/Page[^s]/g) || []).length
  if (got !== pages) {
    console.error(`✗ ${book.id}: страниц ${got}, разделов ${pages} — раздел не поместился на свою страницу`)
    failed++
  } else {
    const kb = (readFileSync(file).length / 1024).toFixed(0)
    console.log(`✓ ${book.id}.pdf: ${pages} страниц, ${kb} КБ`)
  }
  await ctx.close()
}

await browser.close()
if (failed) process.exit(1)
