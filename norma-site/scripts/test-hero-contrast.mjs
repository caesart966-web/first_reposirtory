// Проверяет, что текст на первом экране читается поверх видео.
//
// Зачем отдельная проверка: обычные инструменты доступности считают контраст
// по цвету фона в стилях. Под текстом здесь не цвет, а движущаяся картинка,
// и на светлом кадре белый заголовок может пропасть, хотя в стилях всё
// формально в порядке. Поэтому смотрим настоящие пиксели на разных секундах
// ролика и берём самый светлый — худший — случай.
//
// Запуск: node scripts/test-hero-contrast.mjs [адрес]

import { chromium } from 'playwright'
import { PNG } from 'pngjs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const MOMENTS = [0.2, 2.5, 5, 7.5, 9.5] // секунды ролика
const MIN = 4.5 // требование стандарта для обычного текста

const lum = (r, g, b) => {
  const f = (v) => {
    v /= 255
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}
// Белый текст: контраст = 1.05 / (яркость фона + 0.05)
const contrastToWhite = (L) => 1.05 / (L + 0.05)

const browser = await chromium.launch()
let failed = 0

for (const [width, height, name] of [[1280, 900, 'компьютер'], [390, 800, 'телефон']]) {
  const ctx = await browser.newContext({ viewport: { width, height } })
  const page = await ctx.newPage()
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })
  await page.waitForFunction(() => {
    const v = document.querySelector('video')
    return v && v.readyState >= 2
  }, { timeout: 20000 })

  // Прямоугольники, за которыми лежит видео и по которым идёт текст
  const areas = await page.evaluate(() =>
    ['.page-title', '.tagline', '.promises', '.geo'].map((sel) => {
      const el = document.querySelector(sel)
      if (!el) return null
      const r = el.getBoundingClientRect()
      return { sel, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }
    }).filter(Boolean),
  )

  // Делаем буквы прозрачными, но НЕ прячем их. Тень под текстом рисуется
  // по контуру глифа и остаётся на месте — значит в замер попадает ровно
  // то, на чём буква лежит на самом деле: кадр плюс её собственная тень.
  //
  // Прятать текст через visibility было бы неверно: тень исчезла бы вместе
  // с ним, и замер показал бы фон светлее, чем видит посетитель. А не прятать
  // вовсе нельзя — сами белые буквы дали бы контраст 1:1.
  await page.addStyleTag({
    content: `.hero .wrap, .hero .wrap * {
      color: transparent !important;
      -webkit-text-fill-color: transparent !important;
    }
    .hero .wrap svg, .hero .hero-offer { visibility: hidden !important }`,
  })

  const worst = new Map()

  for (const t of MOMENTS) {
    await page.evaluate((sec) => {
      const v = document.querySelector('video')
      v.pause()
      v.currentTime = sec
    }, t)
    await page.waitForFunction(() => {
      const v = document.querySelector('video')
      return v.readyState >= 2 && !v.seeking
    }, { timeout: 8000 }).catch(() => {})
    await page.waitForTimeout(250)

    for (const a of areas) {
      if (a.y < 0 || a.y + a.h > height || a.w < 4) continue
      const buf = await page.screenshot({ clip: { x: a.x, y: a.y, width: a.w, height: a.h } })
      const png = PNG.sync.read(buf)
      // Берём 5% самых светлых пикселей: одиночная светлая точка погоды
      // не делает, а вот светлое пятно под строкой — делает.
      const ls = []
      for (let i = 0; i < png.data.length; i += 4) {
        ls.push(lum(png.data[i], png.data[i + 1], png.data[i + 2]))
      }
      ls.sort((x, y) => y - x)
      const bright = ls[Math.floor(ls.length * 0.05)]
      const c = contrastToWhite(bright)
      const prev = worst.get(a.sel)
      if (!prev || c < prev.c) worst.set(a.sel, { c, t })
    }
  }

  for (const [sel, { c, t }] of worst) {
    const ok = c >= MIN
    if (!ok) failed++
    console.log(`${ok ? '✓' : '✗'} ${name}: ${sel.padEnd(14)} худший контраст ${c.toFixed(2)}:1 (на ${t} с)`)
  }
  await ctx.close()
}

await browser.close()

if (failed) {
  console.log(`\nОШИБОК: ${failed}. Текст на видео читается хуже нормы ${MIN}:1 — сделайте пелену плотнее в Hero.astro.`)
  process.exit(1)
}
console.log(`\n✓ Текст первого экрана читается поверх видео на всех проверенных кадрах.`)
