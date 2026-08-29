// Скриншоты собранного сайта — для быстрой визуальной проверки.
// Запуск: node scripts/screenshots.mjs [адрес] [папка_для_картинок]

import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const OUT = process.argv[3] || 'screenshots'

const pages = [
  { name: 'main', path: '/' },
  { name: 'stoimost', path: '/stoimost/' },
  { name: 'komu', path: '/komu-nuzhna-sro/' },
  { name: 'usluga', path: '/uslugi/sro-stroiteley/' },
  { name: 'statya', path: '/baza-znaniy/porog-10-mln/' },
  { name: 'kontakty', path: '/kontakty/' },
]

await mkdir(OUT, { recursive: true })
const browser = await chromium.launch()

for (const device of [
  { key: 'desktop', width: 1360, height: 900 },
  { key: 'mobile', width: 390, height: 844 },
]) {
  const context = await browser.newContext({
    viewport: { width: device.width, height: device.height },
    deviceScaleFactor: 1,
    isMobile: device.key === 'mobile',
    hasTouch: device.key === 'mobile',
  })
  const page = await context.newPage()

  for (const p of pages) {
    await page.goto(BASE + p.path, { waitUntil: 'networkidle' })
    // Прокрутить страницу, чтобы сработали анимации появления
    await page.evaluate(async () => {
      await new Promise((done) => {
        let y = 0
        const step = () => {
          y += window.innerHeight
          window.scrollTo(0, y)
          if (y < document.body.scrollHeight) setTimeout(step, 120)
          else { window.scrollTo(0, 0); setTimeout(done, 500) }
        }
        step()
      })
    })
    // Дождаться, пока все блоки проявятся, иначе на снимке будут пустые места
    await page.waitForFunction(() => !document.querySelector('.rv:not(.in)'), { timeout: 8000 }).catch(() => {})
    await page.waitForTimeout(400)
    await page.screenshot({ path: `${OUT}/${p.name}-${device.key}.png`, fullPage: true })

    // Проверка на горизонтальный скролл — частая беда мобильной вёрстки
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    if (overflow > 1) console.log(`! ${p.path} (${device.key}): горизонтальный скролл ${overflow}px`)
  }
  await context.close()
}

await browser.close()
console.log(`Скриншоты в папке ${OUT}/`)
