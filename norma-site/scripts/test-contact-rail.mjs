// Кнопки связи на телефоне: столбик значков у правого края.
//
// Запуск:  npm test   (или node scripts/test-contact-rail.mjs [адрес сайта])
//
// Зачем. Столбик лежит ПОВЕРХ страницы, и всё, что делает его терпимым,
// держится на условиях, которые ломаются молча: он поднимается над полосой
// про cookie (высоту сообщает скрипт полосы), прячется при открытом меню,
// при наборе текста в форме и в конце страницы. Сломайся любое — сайт
// соберётся и будет выглядеть рабочим, а на телефоне значки лягут поверх
// кнопок полосы, пунктов меню или поля, в которое человек печатает.
//
// Полосу про cookie проверка открывает настоящим playwright, а не обёрткой
// из lib/browser.mjs: обёртка отвечает за посетителя заранее, и полосы
// здесь было бы не увидеть. Где полосы нет вовсе (сборка без счётчика
// Метрики), эта часть пропускается с пометкой.

import { chromium as bare } from 'playwright'
import { readFileSync } from 'node:fs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const PHONE = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' }

let problems = 0
const ok = (m) => console.log(`  ✓ ${m}`)
const fail = (m) => { console.log(`  ✗ ${m}`); problems++ }
const check = (cond, m, why = '') => (cond ? ok(m) : fail(why ? `${m} — ${why}` : m))

// Каналов столько, сколько ссылок в site.ts: без MAX их три.
const site = readFileSync(new URL('../src/config/site.ts', import.meta.url), 'utf8')
const channels = /maxLink:\s*'[^']+'/.test(site) ? 4 : 3

const rail = (page) =>
  page.evaluate(() => {
    const el = document.querySelector('.contact-rail')
    if (!el) return null
    const cs = getComputedStyle(el)
    const r = el.getBoundingClientRect()
    const links = [...el.querySelectorAll('a')].map((a) => {
      const b = a.getBoundingClientRect()
      return { w: b.width, h: b.height, top: b.top, label: a.getAttribute('aria-label') || a.textContent.trim(), tel: a.href.startsWith('tel:') }
    })
    return { shown: cs.display !== 'none' && cs.visibility !== 'hidden' && cs.opacity !== '0', top: r.top, bottom: r.bottom, left: r.left, right: r.right, links }
  })

console.log('\nКнопки связи на телефоне\n')

const browser = await bare.launch()

// ── Полоса про cookie: столбик над ней, а не под ней ─────────────────────
{
  const ctx = await browser.newContext(PHONE)
  const page = await ctx.newPage()
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })
  const note = page.locator('#cookie-note')
  if (!(await note.count()) || !(await note.isVisible())) {
    console.log('  · полосы про cookie в этой сборке нет (нет счётчика Метрики) — часть про неё пропущена')
  } else {
    await page.waitForTimeout(200)
    const r = await rail(page)
    const noteTop = (await note.boundingBox()).y
    check(r && r.shown && r.bottom <= noteTop, 'Над полосой про cookie', r ? `низ столбика ${Math.round(r.bottom)} px, верх полосы ${Math.round(noteTop)} px` : 'столбика нет')
    await page.click('[data-cookie="need"]')
    await page.waitForTimeout(300)
    const after = await rail(page)
    check(after && after.bottom >= PHONE.viewport.height - 40, 'После ответа опускается к низу экрана', after ? `низ на ${Math.round(after.bottom)} px из ${PHONE.viewport.height}` : '')
  }
  await ctx.close()
}

// Дальше — посетитель, который уже ответил про cookie.
const ctx = await browser.newContext(PHONE)
await ctx.addInitScript(() => { try { localStorage.setItem('norma-cookie', 'need') } catch {} })
const page = await ctx.newPage()
await page.goto(BASE + '/', { waitUntil: 'networkidle' })

// ── Первый экран: видно, всё на месте ────────────────────────────────────
{
  const r = await rail(page)
  check(r && r.shown, 'Виден с первого экрана')
  if (r) {
    check(r.links.length === channels, `Каналов ${channels}, как в site.ts`, `в столбике ${r.links.length}`)
    check(r.top >= 0 && r.bottom <= PHONE.viewport.height && r.right <= PHONE.viewport.width, 'Целиком в пределах экрана')
    const small = r.links.filter((l) => l.w < 44 || l.h < 44)
    check(!small.length, 'Значки не меньше 44 px — по ним попадают пальцем', small.map((l) => `${l.label}: ${Math.round(l.w)}×${Math.round(l.h)}`).join(', '))
    const unnamed = r.links.filter((l) => !l.label.trim())
    check(!unnamed.length, 'У каждой ссылки есть название для экранного диктора и поисковика', `без названия: ${unnamed.length}`)
    const lowest = r.links.reduce((a, b) => (b.top > a.top ? b : a))
    check(lowest.tel, 'Телефон внизу, ближе всего к большому пальцу')
  }
}

// ── Поле формы в фокусе — прячется; флажок — нет ─────────────────────────
{
  await page.locator('#zayavka input[type="tel"]').first().focus()
  check(!(await rail(page)).shown, 'Прячется, пока человек печатает в поле формы')
  await page.locator('#zayavka input[type="checkbox"]').first().focus()
  check((await rail(page)).shown, 'Не прячется от флажка согласия — иначе мигал бы при каждом нажатии')
  await page.evaluate(() => document.activeElement?.blur())
}

// ── Меню открыто — прячется ──────────────────────────────────────────────
{
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
  await page.locator('[aria-controls="mobile-menu"]').first().click()
  await page.waitForTimeout(200)
  check(!(await rail(page)).shown, 'Прячется при открытом меню')
  await page.keyboard.press('Escape')
  await page.waitForTimeout(200)
  check((await rail(page)).shown, 'Возвращается, когда меню закрыли')
}

// ── Конец страницы — прячется, подвал виден целиком ──────────────────────
{
  await page.evaluate(() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' }))
  await page.waitForTimeout(300)
  check(!(await rail(page)).shown, 'Уходит в конце страницы — не закрывает последние строки подвала')
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
  await page.waitForTimeout(300)
  check((await rail(page)).shown, 'Возвращается, когда страницу прокрутили назад')
}
await ctx.close()

// ── На компьютере столбика нет: там телефон и заявка в шапке ─────────────
{
  const wide = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  await wide.addInitScript(() => { try { localStorage.setItem('norma-cookie', 'need') } catch {} })
  const p = await wide.newPage()
  await p.goto(BASE + '/', { waitUntil: 'networkidle' })
  check(!(await rail(p)).shown, 'На ширине 1280 столбика нет')
  await wide.close()
}

await browser.close()
console.log(problems ? `\n✗ Проверка не прошла: ${problems}.\n` : '\n✓ Кнопки связи на месте и не мешают.\n')
process.exit(problems ? 1 : 0)
