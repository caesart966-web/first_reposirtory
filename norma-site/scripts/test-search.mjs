// Проверка поиска по сайту: морфология, порядок выдачи и работа в браузере.
//
// Запуск: node scripts/test-search.mjs   (входит в npm test)
//
// Поиск — единственная часть сайта, которая может «работать» и при этом
// быть бесполезной: строка есть, результаты появляются, а нужной страницы
// среди них нет. Поэтому здесь проверяется не «поиск отвечает»,
// а «поиск отвечает правильно»: у каждого запроса записана страница,
// которая обязана стоять первой.

import { readFileSync } from 'node:fs'
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { extname, join } from 'node:path'
import { chromium } from 'playwright'
import { stem, same, prepare, search, foundLabel } from '../src/lib/search.ts'

const problems = []
const bad = (m) => problems.push(m)
let checks = 0

// ── 1. Морфология ─────────────────────────────────────────────────────────
//
// Пары, которые обязаны считаться одним словом. Половина запросов приходит
// в форме, отличной от той, что написана на странице.
const SAME = [
  ['вступить', 'вступление'],
  ['вступление', 'вступления'],
  ['взнос', 'взносы'],
  ['взносы', 'взносов'],
  ['документ', 'документы'],
  ['документы', 'документов'],
  ['специалист', 'специалистов'],
  ['проектировщик', 'проектировщиков'],
  ['ответственность', 'ответственности'],
  ['членство', 'членства'],
  ['проверить', 'проверка'],
  ['страхование', 'страхования'],
  ['договор', 'договора'],
  ['подрядчик', 'подрядчика'],
  ['сро', 'СРО'],
  ['нрс', 'НРС'],
]

// Пары, которые сливаться НЕ должны: иначе поиск перестанет различать
// что угодно от чего угодно.
const DIFFERENT = [
  ['проект', 'проверка'],
  ['взнос', 'внос'],
  ['член', 'чек'],
  ['суд', 'судно'],
  ['лицензия', 'лицо'],
]

for (const [a, b] of SAME) {
  checks++
  if (!same(stem(a), stem(b))) bad(`«${a}» и «${b}» должны находиться друг по другу (${stem(a)} / ${stem(b)})`)
}
for (const [a, b] of DIFFERENT) {
  checks++
  if (same(stem(a), stem(b))) bad(`«${a}» и «${b}» — разные слова, а поиск считает их одним (${stem(a)} / ${stem(b)})`)
}

// Склонение числа найденного.
for (const [n, want] of [[1, '1 страница'], [2, '2 страницы'], [5, '5 страниц'], [11, '11 страниц'], [21, '21 страница'], [104, '104 страницы']]) {
  checks++
  if (foundLabel(n) !== want) bad(`число найденного: ${foundLabel(n)} вместо «${want}»`)
}

// ── 2. Порядок выдачи по настоящему индексу ───────────────────────────────
const docs = prepare(JSON.parse(readFileSync('dist/search-index.json', 'utf8')))

const QUERIES = [
  ['взносы', '/stoimost/'],
  ['вступление ООО', '/baza-znaniy/vstuplenie-ooo-i-ip/'],
  ['порог 10 млн', '/baza-znaniy/porog-10-mln/'],
  ['документы для вступления', '/dokumenty/'],
  ['НРС', '/uslugi/nrs/'],
  ['допуск СРО', '/baza-znaniy/dopuskov-sro-ne-sushchestvuet/'],
  ['субподряд', '/baza-znaniy/nuzhna-li-sro-subpodryadchiku/'],
  ['как проверить сро', '/proverit-sro/'],
  ['страхование', '/baza-znaniy/strahovanie-otvetstvennosti/'],
  ['выход из сро', '/baza-znaniy/vyhod-iz-sro/'],
  ['арбитраж', '/uslugi/yuridicheskie-uslugi/'],
  ['расчётный счёт', '/uslugi/yuridicheskie-uslugi/'],
  ['охрана труда', '/uslugi/ohrana-truda/'],
  ['лицензия МЧС', '/uslugi/licenzii/'],
]

for (const [q, want] of QUERIES) {
  checks++
  const hits = search(docs, q, 5)
  if (hits.length === 0) {
    bad(`запрос «${q}»: ничего не нашлось, а должна быть ${want}`)
    continue
  }
  if (hits[0].doc.u !== want) {
    bad(`запрос «${q}»: первой стоит ${hits[0].doc.u}, а должна ${want} (весь список: ${hits.map((h) => h.doc.u).join(', ')})`)
  }
  if (!hits[0].snippet.includes('<mark>')) bad(`запрос «${q}»: в отрывке нет подсветки`)
}

// Запрос, которого на сайте нет, обязан давать пусто, а не «что-нибудь».
checks++
if (search(docs, 'бетономешалка напрокат', 5).length > 0) {
  bad('поиск находит страницы по запросу, которого на сайте нет')
}
// Все слова запроса обязаны найтись: два слова — это уточнение.
checks++
if (search(docs, 'субподряд бетономешалка', 5).length > 0) {
  bad('поиск возвращает страницы, где найдено только одно слово из двух')
}

// ── 3. Работа в браузере ──────────────────────────────────────────────────
const types = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
}

const server = createServer(async (req, res) => {
  let path = decodeURIComponent((req.url || '/').split('?')[0])
  if (path.endsWith('/')) path += 'index.html'
  try {
    const body = await readFile(join('dist', path))
    res.writeHead(200, { 'Content-Type': types[extname(path)] || 'application/octet-stream' })
    res.end(body)
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' })
    res.end('нет')
  }
})
await new Promise((r) => server.listen(0, r))
const BASE = `http://127.0.0.1:${server.address().port}`

const browser = await chromium.launch()

// На узком телефоне поиск живёт полем в меню, а не кнопкой в шапке:
// четыре элемента в ряд при 320 px не помещаются. Проверяем этот путь
// отдельно — он единственный, каким туда можно попасть.
{
  const page = await browser.newPage({ viewport: { width: 360, height: 720 } })
  await page.goto(`${BASE}/`, { waitUntil: 'networkidle' })

  checks++
  if (await page.locator('.icon-search').isVisible()) {
    bad('телефон 360: кнопка поиска в шапке видна — ряд шапки от неё вылезает за край')
  }
  await page.locator('.burger').click()
  checks++
  const field = page.locator('.mm-search input')
  if (!(await field.isVisible())) bad('телефон 360: в меню нет поля поиска — искать неоткуда')
  else {
    await field.fill('субподряд')
    await page.locator('.mm-search button[type="submit"]').click()
    await page.waitForLoadState('networkidle')
    checks++
    if (!page.url().includes('/poisk/')) bad(`телефон 360: поиск из меню увёл на ${page.url()}`)
    await page.waitForSelector('.ps-out .s-hit', { timeout: 5000 }).catch(() => {})
    checks++
    if ((await page.locator('.ps-out .s-hit').count()) === 0) {
      bad('телефон 360: поиск из меню ничего не нашёл')
    }
  }
  await page.close()
}

for (const [screen, width] of [['планшет', 768], ['компьютер', 1280]]) {
  const page = await browser.newPage({ viewport: { width, height: 800 } })
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto(`${BASE}/`, { waitUntil: 'networkidle' })

  // Кнопка поиска есть на любой ширине.
  checks++
  const btn = page.locator('.icon-search')
  if (!(await btn.isVisible())) {
    bad(`${screen}: кнопки поиска нет в шапке`)
    await page.close()
    continue
  }

  await btn.click()
  checks++
  if (!(await page.locator('.sp-input').isVisible())) bad(`${screen}: строка поиска не открылась`)

  // Поле должно получить курсор: иначе придётся ещё раз тыкать пальцем.
  checks++
  if (!(await page.evaluate(() => document.activeElement?.classList.contains('sp-input')))) {
    bad(`${screen}: курсор не встал в строку поиска`)
  }

  await page.locator('.sp-input').fill('субподряд')
  await page.waitForSelector('.sp-out .s-hit', { timeout: 5000 }).catch(() => {})
  const hits = await page.locator('.sp-out .s-hit').count()
  checks++
  if (hits === 0) bad(`${screen}: по запросу «субподряд» ничего не показано`)

  // Подсветка и стили обязаны доехать до вставленной скриптом разметки:
  // Астро своим правилам туда дорогу не даёт, и без :global() список
  // остался бы без оформления.
  checks++
  const marked = await page.locator('.sp-out mark').count()
  if (marked === 0) bad(`${screen}: найденные слова не подсвечены`)
  checks++
  const styled = await page.evaluate(() => {
    const el = document.querySelector('.sp-out .s-title')
    if (!el) return false
    const f = getComputedStyle(el).fontFamily
    return f.includes('Literata')
  })
  if (!styled) bad(`${screen}: список найденного остался без оформления (правила не достали до вставленной разметки)`)

  // Первая ссылка ведёт на настоящую страницу.
  checks++
  const firstHref = await page.locator('.sp-out .s-hit').first().getAttribute('href')
  const resp = await page.request.get(BASE + firstHref)
  if (!resp.ok()) bad(`${screen}: первая ссылка из поиска ведёт на ${firstHref} — ответ ${resp.status()}`)

  // Esc закрывает и возвращает курсор на кнопку.
  await page.keyboard.press('Escape')
  checks++
  if (await page.locator('.sp-input').isVisible()) bad(`${screen}: строка поиска не закрылась по Esc`)
  checks++
  if (!(await page.evaluate(() => document.activeElement?.classList.contains('icon-search')))) {
    bad(`${screen}: после закрытия курсор не вернулся на кнопку поиска`)
  }

  checks++
  if (errors.length > 0) bad(`${screen}: ошибки в скриптах — ${errors.join('; ')}`)
  await page.close()
}

// Страница результатов принимает запрос из адреса.
{
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto(`${BASE}/poisk/?q=${encodeURIComponent('порог 10 млн')}`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.ps-out .s-hit', { timeout: 5000 }).catch(() => {})

  checks++
  const first = await page.locator('.ps-out .s-hit').first().getAttribute('href')
  if (!first || !first.endsWith('/baza-znaniy/porog-10-mln/')) {
    bad(`страница результатов: первой стоит ${first}, а должна статья о пороге 10 млн`)
  }
  checks++
  if (!(await page.locator('.ps-input').inputValue()).includes('порог')) {
    bad('страница результатов: запрос из адреса не подставился в поле')
  }
  checks++
  if ((await page.locator('.ps-status').textContent())?.trim() === '') {
    bad('страница результатов: не сказано, сколько найдено')
  }

  // Запрос, которого нет: человек должен получить ответ, а не пустоту.
  await page.locator('.ps-input').fill('бетономешалка напрокат')
  await page.waitForTimeout(500)
  checks++
  const status = (await page.locator('.ps-status').textContent()) ?? ''
  if (!status.includes('ничего не нашлось')) {
    bad(`страница результатов: по несуществующему запросу сказано «${status.trim()}»`)
  }
  checks++
  if ((await page.locator('.ps-out .s-hit').count()) > 0) {
    bad('страница результатов: по несуществующему запросу остались старые результаты')
  }

  // Подсказки под полем подставляют запрос.
  await page.locator('.ps-hints button').first().click()
  await page.waitForTimeout(400)
  checks++
  if ((await page.locator('.ps-out .s-hit').count()) === 0) bad('страница результатов: подсказка под полем ничего не находит')

  checks++
  if (errors.length > 0) bad(`страница результатов: ошибки в скриптах — ${errors.join('; ')}`)
  await page.close()
}

// ── Меню: подсветка раздела и отсутствие «дыры» на планшетах ──────────────
for (const width of [360, 768, 820, 900, 999, 1000, 1280]) {
  const page = await browser.newPage({ viewport: { width, height: 800 } })
  await page.goto(`${BASE}/uslugi/nrs/`, { waitUntil: 'domcontentloaded' })
  checks++
  const canNavigate = await page.evaluate(() => {
    const visible = (s) => {
      const el = document.querySelector(s)
      if (!el) return false
      const r = el.getBoundingClientRect()
      return r.width > 0 && r.height > 0
    }
    return visible('.nav') || visible('.burger')
  })
  if (!canNavigate) bad(`ширина ${width}: на странице нет ни меню, ни кнопки меню — уйти с неё некуда`)
  await page.close()
}

{
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  await page.goto(`${BASE}/baza-znaniy/porog-10-mln/`, { waitUntil: 'domcontentloaded' })
  checks++
  const current = await page.locator('.nav a[aria-current="page"]').allTextContents()
  if (current.length !== 1 || current[0] !== 'База знаний') {
    bad(`подсветка раздела на статье: отмечено ${JSON.stringify(current)}, а должна «База знаний»`)
  }
  await page.close()
}

await browser.close()
server.close()

if (problems.length > 0) {
  console.error(`✗ Поиск и меню (${problems.length}):`)
  problems.forEach((p) => console.error(`  · ${p}`))
  process.exit(1)
}
console.log(`✓ Поиск находит нужное и работает в браузере: ${checks} проверок.`)
