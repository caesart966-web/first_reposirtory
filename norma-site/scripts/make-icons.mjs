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
// favicon.ico. На странице его не объявляет ни одна ссылка, и всё же он
// нужен: /favicon.ico спрашивают вслепую, без разметки, — закладки
// и ярлыки Windows, читалки RSS, часть роботов. Без файла каждый такой
// запрос получал 404, а Вебмастер писал «Файл favicon не найден»
// (29.09.2026, у http-копии сайта). Внутри три PNG — 16, 32 и 48 px:
// PNG внутри ICO понимают все браузеры с 2007 года, и файл собирается
// без отдельной библиотеки.
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

/** Размеры внутри favicon.ico. */
const ICO_SIZES = [16, 32, 48]

/**
 * ICO — заголовок, по записи на картинку и сами картинки подряд.
 * Картинки здесь PNG: ширина и высота в записи — байт (0 значит 256),
 * 32 бита на точку, дальше длина PNG и смещение от начала файла.
 */
function ico(pngs) {
  const head = Buffer.alloc(6)
  head.writeUInt16LE(0, 0) // зарезервировано
  head.writeUInt16LE(1, 2) // 1 — значок (2 было бы курсором)
  head.writeUInt16LE(pngs.length, 4)
  const dir = Buffer.alloc(16 * pngs.length)
  let offset = head.length + dir.length
  pngs.forEach(({ size, data }, i) => {
    const at = i * 16
    dir.writeUInt8(size >= 256 ? 0 : size, at)
    dir.writeUInt8(size >= 256 ? 0 : size, at + 1)
    dir.writeUInt8(0, at + 2) // палитры нет
    dir.writeUInt8(0, at + 3)
    dir.writeUInt16LE(1, at + 4) // плоскостей
    dir.writeUInt16LE(32, at + 6) // бит на точку
    dir.writeUInt32LE(data.length, at + 8)
    dir.writeUInt32LE(offset, at + 12)
    offset += data.length
  })
  return Buffer.concat([head, dir, ...pngs.map((p) => p.data)])
}

const browser = await chromium.launch()
async function render(art, size) {
  const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 })
  await page.setContent(
    `<style>html,body{margin:0;padding:0;background:transparent}svg{display:block;width:${size}px;height:${size}px}</style>${art}`,
  )
  const shot = await page.screenshot({ omitBackground: true, type: 'png' })
  await page.close()
  return shot
}
try {
  for (const { file, size, art } of ICONS) {
    await writeFile(resolve(pub, file), await render(art, size))
    console.log(`  ${file}  ${size}×${size}`)
  }
  const pngs = []
  for (const size of ICO_SIZES) pngs.push({ size, data: await render(svg, size) })
  await writeFile(resolve(pub, 'favicon.ico'), ico(pngs))
  console.log(`  favicon.ico  ${ICO_SIZES.join(', ')} px`)
} finally {
  await browser.close()
}
console.log('✓ Значки собраны из favicon.svg')
