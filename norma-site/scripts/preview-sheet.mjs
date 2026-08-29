// Собирает обзорные снимки сайта для показа заказчику:
// первые экраны ключевых страниц на компьютере и на телефоне.
//
// Запуск: node scripts/preview-sheet.mjs [адрес] [папка]

import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const OUT = process.argv[3] || 'screenshots'

await mkdir(OUT, { recursive: true })
const browser = await chromium.launch()

// Прокрутить страницу до нужного места и дождаться появления блоков
const settle = async (page, selector) => {
  await page.evaluate(async () => {
    await new Promise((done) => {
      let y = 0
      const step = () => {
        y += window.innerHeight
        window.scrollTo(0, y)
        y < document.body.scrollHeight ? setTimeout(step, 110) : (window.scrollTo(0, 0), setTimeout(done, 400))
      }
      step()
    })
  })
  await page.waitForFunction(() => !document.querySelector('.rv:not(.in)'), { timeout: 8000 }).catch(() => {})
  if (selector) {
    await page.locator(selector).first().scrollIntoViewIfNeeded()
    await page.waitForTimeout(400)
  }
}

const shots = [
  { name: '1-главная-первый-экран', path: '/', w: 1360, h: 860 },
  { name: '2-калькулятор', path: '/', w: 1360, h: 860, to: '#calc' },
  { name: '3-калькулятор-ответ-не-нужна', path: '/', w: 1360, h: 900, to: '#calc', act: 'no' },
  { name: '4-отказы-на-торгах', path: '/', w: 1360, h: 860, to: '#torgi' },
  { name: '5-кому-нужна-кому-нет', path: '/', w: 1360, h: 900, to: '#komu' },
  { name: '6-стоимость-таблицы', path: '/stoimost/', w: 1360, h: 900, to: '#tablicy' },
  { name: '7-проверка-в-госреестре', path: '/', w: 1360, h: 800, to: '#proverka' },
  { name: '8-страница-услуги', path: '/uslugi/sro-stroiteley/', w: 1360, h: 900 },
  { name: '9-статья-с-датами', path: '/baza-znaniy/porog-10-mln/', w: 1360, h: 900 },
  { name: '10-мобильный-первый-экран', path: '/', w: 390, h: 844 },
  { name: '11-мобильный-калькулятор', path: '/', w: 390, h: 844, to: '#calc' },
  { name: '12-мобильная-форма', path: '/kontakty/', w: 390, h: 844, to: '#form' },
]

for (const s of shots) {
  const ctx = await browser.newContext({
    viewport: { width: s.w, height: s.h },
    isMobile: s.w < 500,
    hasTouch: s.w < 500,
    deviceScaleFactor: 2,
  })
  const page = await ctx.newPage()
  await page.goto(BASE + s.path, { waitUntil: 'networkidle' })
  await settle(page, s.to)

  // Показать честный ответ калькулятора «СРО не нужна»
  if (s.act === 'no') {
    for (const t of ['Строительство, реконструкция', 'С генподрядчиком']) {
      await page.locator('#calc-body .opt', { hasText: t }).first().click()
      await page.waitForTimeout(200)
    }
    await page.waitForSelector('.verdict')
    await page.locator('#calc').scrollIntoViewIfNeeded()
    await page.waitForTimeout(400)
  }

  await page.screenshot({ path: `${OUT}/${s.name}.png` })
  await ctx.close()
}

await browser.close()
console.log(`Снимки готовы: ${OUT}/ (${shots.length} шт.)`)
