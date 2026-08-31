// Проверка вёрстки на «неудобных» ширинах и при раздутых шрифтах.
//
// Зачем: Android в режиме «версия для ПК» показывает страницу в широкой
// раскладке и при этом сам увеличивает шрифты. Ширины блоков остаются
// прежними — текст перестаёт помещаться, слова рвутся посередине, колонки
// налезают друг на друга. Обычные проверки этого не ловят, потому что
// в них шрифт нормального размера.
//
// Здесь мы искусственно раздуваем шрифты и смотрим, переживёт ли вёрстка.
//
// Запуск: node scripts/test-widths.mjs [адрес]

import { chromium } from 'playwright'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const PAGES = ['/', '/stoimost/', '/komu-nuzhna-sro/', '/kontakty/', '/uslugi/sro-stroiteley/', '/dokumenty/', '/proverit-sro/']

// Ширины, на которых чаще всего ломается: край брейкпоинтов и режим «для ПК».
const WIDTHS = [360, 390, 480, 640, 767, 768, 899, 900, 980, 1024, 1279, 1360]

const browser = await chromium.launch()
let failed = 0

const report = (ok, name, detail = '') => {
  if (!ok) {
    failed++
    console.log(`✗ ${name}${detail ? ' — ' + detail : ''}`)
  }
}

// ── 1. Горизонтальная прокрутка на всех ширинах ──────────────────────────
for (const width of WIDTHS) {
  const ctx = await browser.newContext({ viewport: { width, height: 900 } })
  const page = await ctx.newPage()
  for (const path of PAGES) {
    await page.goto(BASE + path, { waitUntil: 'networkidle' })
    await page.waitForTimeout(150)
    const over = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    report(over <= 1, `${path} при ${width}px — горизонтальная прокрутка`, `${over}px`)
  }
  await ctx.close()
}
console.log(`✓ Нет горизонтальной прокрутки: ${PAGES.length} страниц × ${WIDTHS.length} ширин`)

// ── 2. Раздутые шрифты: имитируем режим «версия для ПК» на телефоне ──────
{
  const ctx = await browser.newContext({ viewport: { width: 980, height: 900 } })
  const page = await ctx.newPage()
  for (const path of PAGES) {
    await page.goto(BASE + path, { waitUntil: 'networkidle' })
    // Раздуваем шрифты так же, как это делает браузер: множитель к уже
    // посчитанному размеру каждого элемента. Через CSS с em так нельзя —
    // размеры перемножались бы по всей вложенности и выросли бы в тысячи раз.
    await page.evaluate(() => {
      const sizes = new Map()
      document.querySelectorAll('body *').forEach((el) => {
        sizes.set(el, parseFloat(getComputedStyle(el).fontSize))
      })
      sizes.forEach((px, el) => {
        el.style.fontSize = `${(px * 1.5).toFixed(2)}px`
      })
    })
    await page.waitForTimeout(300)

    const over = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    report(over <= 1, `${path} с раздутым шрифтом — страницу распирает`, `${over}px`)

    // Слова, разорванные посередине: признак того, что текст не помещается
    const broken = await page.evaluate(() => {
      const bad = []
      document.querySelectorAll('p, li, dd, b, span, h1, h2, h3').forEach((el) => {
        if (el.children.length) return
        const s = getComputedStyle(el)
        if (s.overflowWrap === 'anywhere' || s.wordBreak === 'break-all') return
        // Элементы, которые по замыслу свёрнуты и раскрываются при наведении
        // (подпись у круглой кнопки связи), обрезаны намеренно — это не поломка.
        if (parseFloat(s.maxWidth) === 0) return
        // Если элемент шире своего контейнера — текст вылезает
        if (el.scrollWidth > el.clientWidth + 2) {
          bad.push((el.textContent || '').trim().slice(0, 40))
        }
      })
      return bad.slice(0, 5)
    })
    report(broken.length === 0, `${path} с раздутым шрифтом — текст вылезает`, broken.join(' | '))
  }
  await ctx.close()
}

await browser.close()

if (failed) {
  console.log(`\nОШИБОК: ${failed}`)
  process.exit(1)
}
console.log('✓ Раздутые шрифты вёрстку не ломают.')
