// Считает, насколько запасной системный шрифт отличается по размеру от нашего.
// Полученные числа подставляются в @font-face запасных шрифтов (size-adjust,
// ascent-override), чтобы при подмене шрифта страница не дёргалась.
//
// Запуск: node scripts/font-metrics.mjs   (сайт должен быть запущен на :4321)

import { chromium } from 'playwright'

const browser = await chromium.launch()
const page = await browser.newPage()
await page.goto('http://127.0.0.1:4321/', { waitUntil: 'networkidle' })

const result = await page.evaluate(async () => {
  await document.fonts.ready
  const sample =
    'Вступление в СРО с выпиской из реестра за 24 часа. Компенсационный фонд обеспечения договорных обязательств.'

  const measure = (family) => {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    ctx.font = `100px ${family}`
    const m = ctx.measureText(sample)
    return {
      width: m.width,
      ascent: m.fontBoundingBoxAscent,
      descent: m.fontBoundingBoxDescent,
    }
  }

  const pairs = [
    ['Onest Variable', 'Arial'],
    ['Golos Text Variable', 'Arial'],
    ['JetBrains Mono Variable', 'monospace'],
  ]

  return pairs.map(([real, fallback]) => {
    const r = measure(`"${real}"`)
    const f = measure(fallback)
    const sizeAdjust = r.width / f.width
    return {
      real,
      fallback,
      sizeAdjust: +(sizeAdjust * 100).toFixed(2),
      // Метрики запасного шрифта пересчитываем под новый размер,
      // иначе высота строки всё равно разойдётся.
      ascent: +((r.ascent / 100 / sizeAdjust) * 100).toFixed(2),
      descent: +((r.descent / 100 / sizeAdjust) * 100).toFixed(2),
    }
  })
})

console.log(JSON.stringify(result, null, 1))
await browser.close()
