// Кнопки связи на телефоне: столбик значков у правого края.
//
// Запуск:  npm test   (или node scripts/test-contact-rail.mjs [адрес сайта])
//
// Зачем. Столбик лежит ПОВЕРХ страницы, и всё, что делает его терпимым,
// держится на условиях, которые ломаются молча: он поднимается над полосой
// про cookie (высоту сообщает скрипт полосы), прячется при открытом меню,
// при наборе текста в форме, в конце страницы и пока человек листает вниз
// (с 30.09.2026), а суммы карточки условий, суммы компфонда в карточках
// направлений и плюсы вопросов отодвинуты из-под него. Сломайся любое — сайт
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

// Прокрутка шагами, как пальцем: каждый шаг короче экрана.
const step = (dy, n) => page.evaluate(async ([dy, n]) => {
  for (let i = 0; i < n; i++) {
    window.scrollBy({ top: dy, behavior: 'instant' })
    await new Promise((r) => setTimeout(r, 60))
  }
}, [dy, n])

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

    // Суммы в карточке условий — главное на первом экране. До 30.09.2026
    // столбик ложился ровно на них: «0 ₽» и «5 000 ₽ в месяц» читались
    // наполовину. Меряется правый край каждой суммы против левого края
    // столбика — на тех строках, мимо которых он проходит по высоте.
    const covered = await page.evaluate((rl) => {
      const out = []
      for (const dd of document.querySelectorAll('.ho-row dd')) {
        const b = dd.getBoundingClientRect()
        if (b.bottom > rl.top && b.top < rl.bottom && b.right > rl.left) out.push(`${dd.textContent.trim()} (${Math.round(b.right)} > ${Math.round(rl.left)})`)
      }
      return out
    }, { top: r.top, bottom: r.bottom, left: r.left })
    check(!covered.length, 'Суммы в карточке условий не под значками', covered.join(', '))
  }
}

// ── Листает вниз — уходит, листает вверх — возвращается ──────────────────
// Человек, листающий вниз, читает, и столбик закрывал бы концы строк.
// Листнул вверх — ищет, где написать: значки на месте. Шаги короче экрана:
// скачок больше экрана — это переход по ссылке, а не чтение.
{
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
  await page.waitForTimeout(150)
  await step(160, 8)
  await page.waitForTimeout(200)
  check(!(await rail(page)).shown, 'Уходит, пока человек листает вниз, — не закрывает текст')
  await step(-60, 2)
  await page.waitForTimeout(200)
  check((await rail(page)).shown, 'Возвращается, как только листнули вверх')

  // «Плюс» у вопросов: по нему нажимают, и под столбиком палец попадал
  // в мессенджер вместо ответа. Правый край плюса — левее столбика.
  await page.evaluate(() => document.querySelector('#faq').scrollIntoView({ behavior: 'instant' }))
  await step(-60, 2)
  await page.waitForTimeout(200)
  const r = await rail(page)
  const plus = await page.evaluate(() => [...document.querySelectorAll('#faq summary')].map((s) => {
    const b = s.getBoundingClientRect()
    return { top: b.top, bottom: b.bottom, right: b.right - parseFloat(getComputedStyle(s).paddingRight) }
  }))
  const under = plus.filter((p) => p.bottom > r.top && p.top < r.bottom && p.right > r.left)
  check(r.shown && !under.length, 'Плюсы у вопросов не под значками', under.length ? `под столбиком ${under.length} из ${plus.length}` : r.shown ? '' : 'столбик не показался')

  // Суммы компенсационного фонда в карточках трёх направлений (с 30.09.2026)
  // стоят у правого края, как суммы первого экрана. Пока карточки листают,
  // мимо столбика по высоте проходит каждая строка, поэтому меряется правый
  // край всех сумм, а не только тех, что сейчас на уровне значков.
  const funds = await page.evaluate(() => [...document.querySelectorAll('.df-row dd')].map((d) => ({ t: d.textContent.trim(), right: d.getBoundingClientRect().right })))
  const fundsUnder = funds.filter((f) => f.right > r.left)
  check(
    r.shown && funds.length > 0 && !fundsUnder.length,
    'Суммы компфонда в карточках направлений не под значками',
    !funds.length ? 'строк с суммами нет' : fundsUnder.map((f) => `${f.t} (${Math.round(f.right)} > ${Math.round(r.left)})`).join(', '),
  )
}

// ── Поле формы в фокусе — прячется; флажок — нет ─────────────────────────
{
  await page.locator('#zayavka input[type="tel"]').first().focus()
  check(!(await rail(page)).shown, 'Прячется, пока человек печатает в поле формы')
  await page.evaluate(() => document.activeElement?.blur())
  // Флажок нажимают, когда он уже на экране: ставим его в середину экрана
  // и листаем чуть вверх, чтобы столбик показался, — и только потом фокус.
  // Иначе фокус сам прокрутил бы страницу вниз, и столбик ушёл бы от этого.
  await page.evaluate(() => document.querySelector('#zayavka input[type="checkbox"]').scrollIntoView({ block: 'center', behavior: 'instant' }))
  await step(-60, 2)
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
