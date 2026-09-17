// Проверка карты России в разделе «География».
//
// Карта — единственное место на сайте, где утверждение делается не словами,
// а геометрией: «вот субъект вашего города». Ошибиться тут легко и незаметно.
// Поэтому проверяется не то, что карта нарисовалась, а то, что она говорит
// правду и не ломает страницу.
//
// ЧТО ИМЕННО.
//
// 1. Метка каждого города лежит ВНУТРИ своего субъекта. Это ловит настоящую
//    ошибку: перепутанные координаты или неверную строку в GEO_NAME
//    (scripts/build-map.py). Нарисованная карта при этом выглядит
//    безупречно — точка просто стоит не там, и глазами на 33 городах
//    этого не увидеть.
//
// 2. Высота раздела не меняется ни при каком наведении. Поле показаний
//    держит высоту структурой (подпись и показания в одной ячейке сетки),
//    а не записанным числом, и эта проверка — то, что не даёт структуре
//    развалиться при следующей правке текста.
//
// 3. У каждого города из regions.ts есть контур субъекта и метка. Новый
//    город не может тихо пропасть с карты. И координаты, по которым карта
//    построена, совпадают с теми, что в regions.ts сейчас: метки в
//    mapdata.ts уже спроецированы, поправку координат без пересборки
//    карты глазами не увидеть вовсе.
//
// 4. Карта не берёт фокус. Она помечена aria-hidden — фокусируемый элемент
//    внутри такой ветки клавиатура находит, а озвучить нечем.
//
// 5. Наведение действительно работает: субъект подсвечивается, перекрестье
//    появляется, в показаниях оказывается тот город, на который навели,
//    и у трёх городов с партнёрами — их настоящие номера из partners.ts.
//
// 6. Ничего не вылезает за края пластины ни на одной из трёх ширин.
//
// Запуск: node scripts/test-geomap.mjs [адрес]
import { chromium } from './lib/browser.mjs'
import { REGIONS } from '../src/config/regions.ts'
import { partnersOf } from '../src/config/partners.ts'
import { MAP_SOURCE } from '../src/config/mapdata.ts'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const WIDTHS = [
  { w: 1440, h: 1000, name: 'компьютер' },
  { w: 1024, h: 900, name: 'планшет' },
  { w: 390, h: 844, name: 'телефон' },
]

const fail = []
const ok = (m) => console.log('✓ ' + m)
const bad = (m) => {
  fail.push(m)
  console.log('✗ ' + m)
}

const browser = await chromium.launch()

// ── 1–5: всё, что требует мыши, — на широком экране ───────────────────
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  await page.goto(`${BASE}/`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(400)

  // 3. Все города на месте.
  const drawn = await page.$$eval('.gmap-pin', (els) => els.map((e) => e.dataset.city))
  const missing = REGIONS.filter((r) => !drawn.includes(r.slug)).map((r) => r.slug)
  const extra = drawn.filter((s) => !REGIONS.some((r) => r.slug === s))
  if (missing.length) bad(`нет метки на карте: ${missing.join(', ')}`)
  else if (extra.length) bad(`метка без города в regions.ts: ${extra.join(', ')}`)
  else ok(`все ${REGIONS.length} городов есть на карте`)

  // Карта не устарела: координаты, по которым её строили, — те же самые.
  const stale = REGIONS.filter((r) => {
    const src = MAP_SOURCE[r.slug]
    return !src || src.lon !== r.lon || src.lat !== r.lat
  }).map((r) => r.slug)
  if (stale.length)
    bad(
      `координаты в regions.ts разошлись с картой (${stale.join(', ')}) — ` +
        'пересоберите: см. шапку scripts/build-map.py',
    )
  else ok('карта построена по тем же координатам, что записаны в regions.ts')

  const emptyPaths = await page.$$eval('.gmap-reg', (els) =>
    els.filter((e) => (e.getAttribute('d') || '').length < 20).map((e) => e.dataset.city),
  )
  if (emptyPaths.length) bad(`пустой контур субъекта: ${emptyPaths.join(', ')}`)
  else ok('у каждого города нарисован контур его субъекта')

  // 1. Метка внутри своего субъекта.
  //
  // Допуск нужен: контуры упрощены Дугласом–Пейкером до 1.4 px, и город
  // у самой границы (Петербург, Москва) законно оказывается снаружи
  // на доли пикселя. Он маленький нарочно — ошибка «не тот субъект»
  // промахивается на десятки пикселей, а не на два.
  const TOL = 3
  const outside = await page.evaluate((tol) => {
    const svg = document.querySelector('.gmap-svg')
    const out = []
    for (const pin of document.querySelectorAll('.gmap-pin')) {
      const slug = pin.dataset.city
      const dot = pin.querySelector('.gmap-dot')
      const path = document.querySelector(`.gmap-reg[data-city="${slug}"]`)
      if (!path) continue
      const x = Number(dot.getAttribute('cx'))
      const y = Number(dot.getAttribute('cy'))
      const pt = svg.createSVGPoint()
      let hit = false
      for (let dx = -tol; dx <= tol && !hit; dx += tol) {
        for (let dy = -tol; dy <= tol && !hit; dy += tol) {
          pt.x = x + dx
          pt.y = y + dy
          if (path.isPointInFill(pt)) hit = true
        }
      }
      if (!hit) out.push(slug)
    }
    return out
  }, TOL)
  if (outside.length) bad(`метка города вне своего субъекта: ${outside.join(', ')}`)
  else ok(`метка каждого города лежит внутри своего субъекта (допуск ${TOL} px)`)

  // 4. Фокус внутрь карты не заходит.
  const focusable = await page.$$eval('.gmap-svg', (els) =>
    els.flatMap((e) =>
      Array.from(e.querySelectorAll('a, button, [tabindex], input, select, textarea')).map(
        (n) => n.tagName,
      ),
    ),
  )
  if (focusable.length) bad(`внутри aria-hidden карты есть фокусируемое: ${focusable.join(', ')}`)
  else ok('карта не берёт фокус: ходят по городам списком под ней')

  // 2 + 5. Наведение: высота, подсветка, показания.
  const height = () => page.$eval('#goroda', (e) => Math.round(e.getBoundingClientRect().height))
  const idleH = await height()
  const jumped = []
  const wrong = []
  for (const r of REGIONS) {
    await page.hover(`.gmap-pin[data-city="${r.slug}"] .gmap-hit`)
    await page.waitForTimeout(30)
    const h = await height()
    if (h !== idleH) jumped.push(`${r.slug} ${idleH}→${h}`)
    const state = await page.evaluate((slug) => {
      const live = document.querySelector('[data-read]').classList.contains('is-live')
      const on = document.querySelector('.gmap-reg.is-on')?.dataset.city
      const cross = document.querySelector('.gmap-cross').classList.contains('is-on')
      const sro = document.querySelector('[data-sro].is-on, [data-sro-none].is-on')
      return {
        live,
        on,
        cross,
        city: document.querySelector('[data-f="city"]').textContent,
        code: document.querySelector('[data-f="code"]').textContent,
        subject: document.querySelector('[data-f="subject"]').textContent,
        href: document.querySelector('[data-f="href"]').getAttribute('href'),
        regs: sro ? Array.from(sro.querySelectorAll('li span')).map((n) => n.textContent) : null,
        none: !!sro?.hasAttribute('data-sro-none'),
      }
    }, r.slug)
    const want = partnersOf(r.slug).map((p) => p.reg)
    if (!state.live) wrong.push(`${r.slug}: показания не включились`)
    else if (state.on !== r.slug) wrong.push(`${r.slug}: подсветился субъект ${state.on}`)
    else if (!state.cross) wrong.push(`${r.slug}: нет перекрестья`)
    else if (state.city !== r.city) wrong.push(`${r.slug}: в показаниях «${state.city}»`)
    else if (state.code !== r.code) wrong.push(`${r.slug}: код «${state.code}» вместо «${r.code}»`)
    else if (state.subject !== r.subject) wrong.push(`${r.slug}: субъект «${state.subject}»`)
    else if (!state.href?.includes(`/sro/${r.slug}/`)) wrong.push(`${r.slug}: ссылка ${state.href}`)
    else if (want.length && String(state.regs) !== String(want))
      wrong.push(`${r.slug}: номера СРО ${state.regs} вместо ${want}`)
    else if (!want.length && !state.none)
      wrong.push(`${r.slug}: партнёров нет, а запасной блок не показан`)
  }
  if (jumped.length) bad(`высота раздела прыгает при наведении: ${jumped.slice(0, 4).join('; ')}`)
  else ok(`высота раздела не меняется ни на одном из ${REGIONS.length} городов`)
  if (wrong.length) wrong.slice(0, 6).forEach(bad)
  else ok(`показания верны на всех ${REGIONS.length} городах, включая номера СРО в реестре`)

  await page.mouse.move(5, 5)
  await page.waitForTimeout(80)
  const back = await page.evaluate(() => ({
    live: document.querySelector('[data-read]').classList.contains('is-live'),
    on: document.querySelectorAll('.is-on').length,
  }))
  if (back.live || back.on) bad('после ухода курсора показания и подсветка остались')
  else ok('курсор ушёл — карта вернулась в покой')

  await page.close()
}

// ── 6. Ничего не вылезает за края пластины ────────────────────────────
for (const { w, h, name } of WIDTHS) {
  const page = await browser.newPage({ viewport: { width: w, height: h } })
  await page.goto(`${BASE}/`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(300)
  const over = await page.evaluate(() => {
    const root = document.querySelector('.gmap')
    const box = root.getBoundingClientRect()
    const out = []
    for (const el of root.querySelectorAll('.gmap-plate, .gmap-read *')) {
      const s = getComputedStyle(el)
      if (s.display === 'none' || s.visibility === 'hidden') continue
      const r = el.getBoundingClientRect()
      if (!r.width) continue
      if (r.right > box.right + 1 || r.left < box.left - 1) {
        out.push(`${el.className || el.tagName}: ${Math.round(r.left - box.left)}..${Math.round(r.right - box.right)}`)
      }
    }
    return out
  })
  if (over.length) bad(`${name}: за края блока вылезает ${over.slice(0, 3).join('; ')}`)
  else ok(`${name}: ничего не вылезает за края`)
  await page.close()
}

await browser.close()

console.log('')
if (fail.length) {
  console.log(`✗ Карта: ${fail.length} замечаний.`)
  process.exit(1)
}
console.log(`✓ Карта в порядке: ${REGIONS.length} городов, метки внутри своих субъектов,`)
console.log('  показания не двигают страницу, наведение показывает верные номера СРО.')
