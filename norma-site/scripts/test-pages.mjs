// Обход всех страниц сайта настоящим браузером.
//
// Остальные проверки берут по 5–8 страниц: так быстрее, и на них ловится
// почти всё. Но «почти» здесь стоит дорого — ошибка в скрипте на одной
// статье из двадцати шести не всплывёт нигде, а посетитель получит
// страницу, на которой не работает меню.
//
// Что проверяется на каждом адресе, включая 404:
//   · ошибки в консоли и необработанные исключения;
//   · запросы, не получившие ответа (битая картинка, шрифт, скрипт);
//   · горизонтальная прокрутка на 320 px — это самый узкий телефон,
//     который ещё встречается, и на нём ломается то, что держится
//     на 360;
//   · элементы, вылезающие за правый край;
//   · ссылки и кнопки без доступного имени — их не прочитает диктор
//     и не поймёт поисковик;
//   · размер тап-целей. Порог провала — 24 px: это минимум WCAG 2.2 AA,
//     и меньше него быть не должно нигде. Всё, что меньше 44 px, идёт
//     в замечания, а не в провалы: 44 — это уровень AAA, и гнать под него
//     каждую ссылку в подвале значило бы разнести вёрстку ради цифры.
//     Правило простое: попасть пальцем можно всегда, крупные цели —
//     у того, чем пользуются с телефона на ходу.
//
// Запуск: node scripts/test-pages.mjs [адрес]
import { chromium } from 'playwright'
import { readFileSync } from 'fs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const sitemap = readFileSync('dist/sitemap-0.xml', 'utf8')
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => new URL(m[1]).pathname)
urls.push('/404.html')

const browser = await chromium.launch()
const problems = []
const tight = new Set()
let checked = 0

for (const [screen, width, height] of [['телефон', 320, 720], ['компьютер', 1280, 900]]) {
  const ctx = await browser.newContext({ viewport: { width, height } })
  for (const url of urls) {
    const page = await ctx.newPage()
    const errors = []
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
    page.on('pageerror', (e) => errors.push(`исключение: ${e.message}`))
    page.on('requestfailed', (r) => {
      // Счётчик Метрики на превью не подключён, его отсутствие — не ошибка.
      if (!r.url().includes('mc.yandex.ru')) errors.push(`не загрузилось: ${r.url()}`)
    })

    const res = await page.goto(BASE + url, { waitUntil: 'networkidle' })
    if (!res || res.status() >= 400) problems.push(`${url} ${screen}: ответ ${res ? res.status() : 'нет'}`)

    // Прокручиваем до низа: часть скриптов просыпается только там.
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += innerHeight) {
        window.scrollTo(0, y)
        await new Promise((r) => setTimeout(r, 40))
      }
      window.scrollTo(0, 0)
    })
    await page.waitForTimeout(200)

    const found = await page.evaluate((vw) => {
      const out = { scroll: 0, wide: [], nameless: [], small: [], tight: [] }
      // Меряем не scrollWidth, а то, что видит посетитель: уедет ли
      // страница вбок, если её потянуть. У html стоит overflow-x: clip,
      // и scrollWidth продолжает показывать вылет декоративной печати,
      // хотя пальцем страницу уже не сдвинуть.
      window.scrollTo(vw, 0)
      out.scroll = Math.round(window.scrollX)
      window.scrollTo(0, 0)

      // Скрытое от диктора — украшение: фон первого экрана, гильош, печать.
      // Оно живёт под clip у html и страницу не двигает, мерить его нечего.
      const decorative = (el) => el.closest('[aria-hidden="true"]') !== null
      // Спрятанная приёмом «видно только голосом» шапка таблицы сохраняет
      // размеры, но её нет на экране.
      const clipped = (el) => {
        for (let n = el.parentElement; n; n = n.parentElement) {
          const c = getComputedStyle(n)
          if (c.clip === 'rect(0px, 0px, 0px, 0px)') return true
          const r = n.getBoundingClientRect()
          if (c.overflow === 'hidden' && r.width <= 1 && r.height <= 1) return true
        }
        return false
      }
      for (const el of document.querySelectorAll('body *')) {
        const cs = getComputedStyle(el)
        if (cs.display === 'none' || cs.visibility === 'hidden' || cs.position === 'fixed') continue
        if (decorative(el) || clipped(el)) continue
        const r = el.getBoundingClientRect()
        if (r.width === 0 || r.height === 0) continue
        if (r.right > vw + 1 && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll') {
          const tag = el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/)[0] : '')
          if (!out.wide.includes(tag)) out.wide.push(tag)
        }
      }

      const visible = (el) => {
        const r = el.getBoundingClientRect()
        const cs = getComputedStyle(el)
        return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden'
      }
      for (const el of document.querySelectorAll('a, button')) {
        if (!visible(el)) continue
        const name = (el.getAttribute('aria-label') || el.textContent || '').trim() ||
          (el.querySelector('img')?.getAttribute('alt') || '').trim() ||
          (el.querySelector('title')?.textContent || '').trim()
        if (!name) out.nameless.push(el.outerHTML.slice(0, 70))
        const r = el.getBoundingClientRect()
        // Ссылка внутри строки текста — не тап-цель: она и не должна быть
        // 44 px высотой, иначе абзац развалится. Считаем только те,
        // что стоят отдельно: кнопки и ссылки-блоки.
        const inline = getComputedStyle(el).display === 'inline'
        if (!inline && (r.width < 24 || r.height < 24)) {
          out.small.push(`${el.tagName.toLowerCase()} «${name.slice(0, 24)}» ${Math.round(r.width)}×${Math.round(r.height)}`)
        } else if (!inline && (r.width < 44 || r.height < 44)) {
          out.tight.push(`${el.tagName.toLowerCase()} «${name.slice(0, 24)}» ${Math.round(r.width)}×${Math.round(r.height)}`)
        }
      }
      return out
    }, width)

    if (found.scroll > 0) problems.push(`${url} ${screen}: страница уезжает вбок на ${found.scroll} px`)
    for (const t of found.wide) problems.push(`${url} ${screen}: за правый край вылезает ${t}`)
    for (const t of found.nameless) problems.push(`${url} ${screen}: ссылка или кнопка без имени → ${t}`)
    for (const t of [...new Set(found.small)]) problems.push(`${url} ${screen}: тап-цель меньше 24 px → ${t}`)
    for (const t of [...new Set(found.tight)]) tight.add(t)
    for (const e of [...new Set(errors)]) problems.push(`${url} ${screen}: ${e}`)

    checked++
    await page.close()
  }
  await ctx.close()
}
await browser.close()

if (tight.size) {
  const list = [...tight]
  console.log(`Целей от 24 до 44 px: ${list.length} видов — это допустимо (AA), но пальцем в них попадают хуже.`)
  for (const x of list.slice(0, 8)) console.log('  · ' + x)
  if (list.length > 8) console.log(`  · …и ещё ${list.length - 8}`)
  console.log()
}
if (problems.length) {
  console.log('ПРОБЛЕМЫ:')
  for (const x of problems) console.log('  ✗ ' + x)
  process.exit(1)
}
console.log(`✓ Все страницы чистые: ${checked} проверок (${urls.length} адресов × 2 экрана).`)
