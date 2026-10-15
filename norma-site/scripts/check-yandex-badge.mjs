// Что сейчас отдаёт Яндекс в рамке значка рейтинга — для робота GitHub
// «НОРМА: проверить значок рейтинга Яндекса».
//
// Зачем. Значок — чужая страница в рамке 150×50 (YandexRating.astro). Если
// Яндекс поменяет её содержимое, на сайте вместо рейтинга появится обрезок
// чужой страницы с полосами прокрутки — так и случилось 15.10.2026 (снимок
// заказчика: «Бизне…» и полосы прокрутки в подвале). Из среды, где
// собирается сайт, yandex.ru закрыт, а у GitHub доступ есть.
//
// Скрипт открывает адрес значка в браузере ровно 150×50 и пишет: куда
// привели переходы, заголовок страницы, текст и помещается ли содержимое
// в рамку. Карточку организации проверяет обычным запросом: жив ли номер.
//
// Запуск: node scripts/check-yandex-badge.mjs   (нужен playwright с chromium)

import { readFileSync } from 'node:fs'
import { chromium } from 'playwright'

const site = readFileSync(new URL('../src/config/site.ts', import.meta.url), 'utf8')
const id = site.match(/yandexOrgId:\s*'(\d+)'/)?.[1]
if (!id) {
  console.error('✗ В site.ts нет yandexOrgId')
  process.exit(1)
}
const badge = `https://yandex.ru/sprav/widget/rating-badge/${id}?type=rating`
const card = `https://yandex.ru/maps/org/${id}/`
const UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'

// Цепочка переходов обычными запросами — видно, не ведёт ли адрес
// значка куда-то ещё (страница Бизнеса, капча, «не найдено»).
async function chain(url) {
  const steps = []
  let u = url
  for (let i = 0; i < 8; i++) {
    const res = await fetch(u, { redirect: 'manual', headers: { 'User-Agent': UA, 'Accept-Language': 'ru' } })
    steps.push(`${res.status} ${u}`)
    const loc = res.headers.get('location')
    if (res.status >= 300 && res.status < 400 && loc) {
      u = new URL(loc, u).toString()
      continue
    }
    const body = await res.text()
    const title = body.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]?.trim() ?? '—'
    return { steps, title, size: body.length }
  }
  return { steps, title: '(слишком много переходов)', size: 0 }
}

for (const [name, url] of [['Значок', badge], ['Карточка', card]]) {
  try {
    const r = await chain(url)
    console.log(`\n${name}:`)
    for (const s of r.steps) console.log(`  ${s}`)
    console.log(`  заголовок: ${r.title} · ${r.size} байт`)
  } catch (e) {
    console.log(`\n${name}: запрос не прошёл — ${e.message}`)
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 150, height: 50 }, userAgent: UA, locale: 'ru-RU' })
await page.goto(badge, { waitUntil: 'networkidle', timeout: 45000 }).catch((e) => console.log(`goto: ${e.message}`))
await page.waitForTimeout(1500)
const view = await page.evaluate(() => ({
  href: location.href,
  title: document.title,
  text: document.body?.innerText.replace(/\s+/g, ' ').trim().slice(0, 400),
  w: document.documentElement.scrollWidth,
  h: document.documentElement.scrollHeight,
}))
await page.screenshot({ path: 'badge-150x50.png' })
await page.setViewportSize({ width: 900, height: 600 })
await page.waitForTimeout(500)
await page.screenshot({ path: 'badge-900x600.png', fullPage: true })
await browser.close()

console.log('\nВ рамке 150×50:')
console.log(`  адрес: ${view.href}`)
console.log(`  заголовок: ${view.title || '—'}`)
console.log(`  текст: ${view.text || '—'}`)
console.log(`  содержимое: ${view.w}×${view.h} px`)
if (view.href.startsWith('chrome-error:')) {
  console.log('✗ Страница значка не открылась — смотрите ошибку выше.')
  process.exit(1)
}
const fits = view.w <= 152 && view.h <= 52
console.log(fits ? '✓ Помещается в 150×50 — значок цел.' : '✗ Не помещается в 150×50 — в подвале будут полосы прокрутки.')
process.exit(fits ? 0 : 1)
