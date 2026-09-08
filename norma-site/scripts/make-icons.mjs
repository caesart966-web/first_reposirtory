// Собирает растровые значки сайта из public/favicon.svg.
//
// Запуск:  node scripts/make-icons.mjs   (или npm run icons)
// Повторять нужно, только если поменялся сам знак.
//
// Зачем растр, когда есть SVG. Браузеры SVG понимают, а вот значок сайта
// в выдаче Яндекса, иконка на домашнем экране телефона и знак организации
// в микроразметке — это растровые картинки. Без них в выдаче на месте
// значка пустой лист.
//
// Углы. У квадратных значков (apple-touch-icon и знак для микроразметки)
// скругления нет нарочно: iOS и поисковики скругляют картинку сами,
// и уже скруглённый файл даёт двойную рамку с прозрачными уголками,
// которые телефон дорисовывает чёрным.

import { chromium } from 'playwright'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const pub = resolve(here, '../public')

const svg = await readFile(resolve(pub, 'favicon.svg'), 'utf8')
const square = svg.replace(/ rx="\d+"/, '') // тот же знак, но без скруглений

const ICONS = [
  { file: 'favicon-32.png', size: 32, art: svg },
  { file: 'favicon-192.png', size: 192, art: svg },
  { file: 'apple-touch-icon.png', size: 180, art: square },
  { file: 'logo-512.png', size: 512, art: square },
]

const browser = await chromium.launch()
try {
  for (const { file, size, art } of ICONS) {
    const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 })
    await page.setContent(
      `<style>html,body{margin:0;padding:0;background:transparent}svg{display:block;width:${size}px;height:${size}px}</style>${art}`,
    )
    const shot = await page.screenshot({ omitBackground: true, type: 'png' })
    await writeFile(resolve(pub, file), shot)
    await page.close()
    console.log(`  ${file}  ${size}×${size}`)
  }
} finally {
  await browser.close()
}
console.log('✓ Значки собраны из favicon.svg')
