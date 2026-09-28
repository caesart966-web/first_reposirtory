// Якоря не прячутся под липкой шапкой.
//
// Шапка сайта липкая: 79 px на компьютере, 69 на телефоне. Ссылка вида
// «/страница/#раздел» ставит цель к верхнему краю окна — то есть ПОД шапку,
// если у цели нет scroll-margin-top (правило в global.css, рядом с `.wrap`).
// Так и вышло 28.09.2026: окошко «Сайт компании — бесплатно» на главной
// вело на заголовок /uslugi/marketing/#besplatno, и заголовок вставал ровно
// под шапку — человек попадал на страницу, не видя, куда попал.
// check-links.mjs этого не видит и не может: якорь есть, ссылка рабочая.
//
// Что делается: из готового сайта собираются все внутренние ССЫЛКИ с якорем
// (только <a>: у печати в SVG тоже есть href="#…", но это путь для текста,
// а не переход), каждая цель открывается на телефоне и на компьютере,
// и верх цели должен оказаться не выше низа шапки. Цель у самого низа
// страницы, до которой прокрутка не достаёт, встаёт ниже — это не ошибка.
// Цель, скрытая на этой ширине (display: none), пропускается.
//
// Запуск: node scripts/test-anchors.mjs [адрес]
import { chromium } from './lib/browser.mjs'
import { readFileSync, readdirSync } from 'node:fs'
import { join, relative } from 'node:path'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'

const walk = (d) =>
  readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(join(d, e.name)) : join(d, e.name)))

// цель «/путь/#id» → страница, где на неё впервые сослались (для сообщения)
const targets = new Map()
for (const file of walk('dist').filter((f) => f.endsWith('.html'))) {
  const page = '/' + relative('dist', file).replace(/index\.html$/, '').replace(/\\/g, '/')
  const html = readFileSync(file, 'utf8')
  for (const m of html.matchAll(/<a\b[^>]*?\shref="([^"]*#[^"]+)"/g)) {
    const raw = m[1].replace(/&amp;/g, '&')
    if (/^[a-z][a-z0-9+.-]*:/i.test(raw) || raw.startsWith('//')) continue
    const [path, id] = raw.split('#')
    const key = `${path || page}#${decodeURIComponent(id)}`
    // «Перейти к содержанию» (#main) стоит на каждой странице и собран
    // одним шаблоном (Base.astro): мерить его полсотни раз — это полсотни
    // одинаковых замеров. Берётся главная.
    if (id === 'main' && key !== '/#main') continue
    if (!targets.has(key)) targets.set(key, page)
  }
}

const browser = await chromium.launch()
const problems = []
let checked = 0

for (const [screen, width, height] of [['телефон', 390, 844], ['компьютер', 1280, 900]]) {
  const ctx = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  for (const [target, from] of targets) {
    await page.goto(BASE + target, { waitUntil: 'networkidle' })
    await page.waitForTimeout(150)
    const r = await page.evaluate((id) => {
      const el = document.getElementById(id)
      if (!el) return { missing: true }
      const box = el.getBoundingClientRect()
      if (box.width === 0 && box.height === 0) return { hidden: true }
      const header = document.querySelector('.site-header')
      return { top: Math.round(box.top), header: header ? Math.round(header.getBoundingClientRect().bottom) : 0 }
    }, decodeURIComponent(target.split('#')[1]))
    if (r.missing) problems.push(`${target} (${screen}): цели нет на странице — ссылка с ${from}`)
    else if (!r.hidden) {
      checked++
      if (r.top < r.header - 1) {
        problems.push(`${target} (${screen}): верх цели на ${r.top} px, шапка кончается на ${r.header} — цель под шапкой (ссылка с ${from})`)
      }
    }
  }
  await ctx.close()
}
await browser.close()

if (problems.length) {
  console.log('✗ Якоря под шапкой:')
  problems.forEach((p) => console.log('   ' + p))
  console.log('  Цели нужен scroll-margin-top — общее правило в src/styles/global.css.')
  process.exit(1)
}
console.log(`✓ Якоря: ${targets.size} целей, ${checked} замеров на телефоне и компьютере — ни одна не уходит под шапку.`)
