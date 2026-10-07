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
import { chromium } from './lib/browser.mjs'
import { readFileSync } from 'fs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const sitemap = readFileSync('dist/sitemap-0.xml', 'utf8')
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => new URL(m[1]).pathname)
urls.push('/404.html')
// Страницы, закрытой от индексации, в карте сайта нет — а проверять её надо.
urls.push('/poisk/')

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
      // Лента логотипов партнёров (PartnerLogos.astro) шире экрана нарочно:
      // она едет и обрезана своим контейнером .pl-view. Исключение узкое,
      // по одному классу, а не «всё внутри overflow: hidden» — общее правило
      // пропустило бы настоящий обрезанный текст. Ленту меряет test-logos.
      const marquee = (el) => el.closest('.pl-view') !== null
      for (const el of document.querySelectorAll('body *')) {
        const cs = getComputedStyle(el)
        if (cs.display === 'none' || cs.visibility === 'hidden' || cs.position === 'fixed') continue
        if (decorative(el) || clipped(el) || marquee(el)) continue
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
        // У растянутой ссылки (.stretch-link, global.css) цель — вся карточка:
        // невидимый слой ::after накрывает её целиком, и нажимается именно она.
        const card = el.classList.contains('stretch-link') ? el.closest('.stretch, .card--link') : null
        const r = (card || el).getBoundingClientRect()
        // Ссылка внутри строки текста — не тап-цель: она и не должна быть
        // 44 px высотой, иначе абзац развалится. Считаем только те,
        // что стоят отдельно: кнопки и ссылки-блоки.
        const inline = !card && getComputedStyle(el).display === 'inline'
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

// ── Предзагрузка по наведению ──
// Хостинг отвечает на запрос страницы 1,5–4,4 с (29.09.2026). Правила
// speculationrules в Base.astro запрашивают страницу, пока курсор идёт
// к клику. Проверяется поведение: наведение на ссылку даёт запрос
// с Sec-Purpose: prefetch, а не просто наличие тега в разметке.
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } })
  const page = await ctx.newPage()
  let prefetched = false
  page.on('request', (r) => {
    if (/prefetch/.test(r.headers()['sec-purpose'] || '') && new URL(r.url()).pathname.endsWith('/stoimost/')) prefetched = true
  })
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })
  await page.hover('header a[href$="/stoimost/"]')
  for (let i = 0; i < 20 && !prefetched; i++) await page.waitForTimeout(100)
  if (!prefetched) problems.push('наведение на «Стоимость» в шапке не запросило страницу заранее (speculationrules в Base.astro)')
  else console.log('✓ Наведение на ссылку запрашивает страницу заранее (Sec-Purpose: prefetch)')
  await ctx.close()
}
// ── Первый экран не ждёт анимации ──
// До 30.09.2026 .rv прятал блоки до скрипта: список статей в базе знаний,
// разбивка на «Стоимости» и карточки городов появлялись примерно через
// секунду после первой отрисовки (телефон, медленный 4G, сервер 1,5 с).
// Теперь прячется только то, что ниже экрана. Проверяется сразу после
// загрузки, до прокрутки: в кадре нет ни одного спрятанного блока,
// а ниже кадра они есть, то есть появление при прокрутке не отключено.
{
  let below = 0
  for (const [screen, width, height] of [['телефон', 390, 844], ['компьютер', 1280, 900]]) {
    const ctx = await browser.newContext({ viewport: { width, height } })
    const page = await ctx.newPage()
    for (const url of ['/', '/baza-znaniy/', '/stoimost/', '/sro/moskva/', '/uslugi/sro-stroiteley/', '/baza-znaniy/kak-vstupit-v-sro/']) {
      await page.goto(BASE + url, { waitUntil: 'domcontentloaded' })
      await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))))
      const r = await page.evaluate(() => {
        const vh = innerHeight
        const rv = [...document.querySelectorAll('.rv')]
        const inView = rv.filter((e) => { const b = e.getBoundingClientRect(); return b.height > 0 && b.top < vh && b.bottom > 0 })
        return {
          hidden: inView.filter((e) => e.classList.contains('rv-wait') || getComputedStyle(e).opacity !== '1').map((e) => e.className.slice(0, 40)),
          below: rv.filter((e) => e.getBoundingClientRect().top >= vh && e.classList.contains('rv-wait')).length,
        }
      })
      below += r.below
      for (const h of r.hidden) problems.push(`${url} ${screen}: на первом экране блок спрятан до анимации → ${h}`)
    }
    await ctx.close()
  }
  if (below === 0) problems.push('ни одного блока ниже экрана не ждёт прокрутки — появление при прокрутке отключилось')
  else console.log(`✓ Первый экран виден сразу, появление при прокрутке — только ниже экрана (${below} блоков ждут)`)
}
// ── После прокрутки не осталось невидимок ──
// До 07.10.2026 печать «Сверено» под .js ждала класса .in на себе, а его
// вешает наблюдатель прокрутки только блокам .rv — и без «уменьшить
// движение» печать не видел никто: ни на главной, ни на «Контактах».
// Снимки и проверки шли с уменьшенным движением, у которого в стилях свой
// путь, и пропускали это месяц; нашёл заказчик по пустому месту рядом
// с ИНН. Здесь движение обычное: страница проматывается до конца, и после
// этого прозрачным не должно остаться ничего, в чём есть текст или
// картинка. Чистая декорация без текста (гильош первого экрана, 7 %
// непрозрачности нарочно) помечена aria-hidden и в счёт не идёт.
// Отдельно печать: видна и стоит на месте, а не висит крупной.
{
  const before = problems.length
  let pages = 0
  let seals = 0
  for (const [screen, width, height] of [['телефон', 390, 844], ['компьютер', 1280, 900]]) {
    const ctx = await browser.newContext({ viewport: { width, height } })
    const page = await ctx.newPage()
    for (const url of ['/', '/kontakty/', '/stoimost/', '/obo-mne/', '/uslugi/sro-stroiteley/', '/baza-znaniy/kak-vstupit-v-sro/']) {
      await page.goto(BASE + url, { waitUntil: 'networkidle' })
      const H = await page.evaluate(() => document.documentElement.scrollHeight)
      for (let y = 0; y < H; y += Math.round(height * 0.6)) {
        await page.evaluate((y) => window.scrollTo({ top: y, behavior: 'instant' }), y)
        await page.waitForTimeout(100)
      }
      await page.waitForTimeout(1200)
      const r = await page.evaluate(() => {
        const faint = (e) => Number(getComputedStyle(e).opacity) <= 0.1
        const ghosts = []
        for (const el of document.querySelectorAll('body *')) {
          const cs = getComputedStyle(el)
          if (cs.display === 'none' || cs.visibility === 'hidden' || !faint(el)) continue
          const b = el.getBoundingClientRect()
          if (b.width < 8 || b.height < 8) continue
          let up = el.parentElement
          while (up && !faint(up) && getComputedStyle(up).visibility !== 'hidden') up = up.parentElement
          if (up) continue
          const text = (el.textContent || '').replace(/\s+/g, ' ').trim()
          const pic = el.matches('img, svg') || el.querySelector('img, svg')
          if (!text && (!pic || el.closest('[aria-hidden="true"]'))) continue
          ghosts.push(`${el.tagName.toLowerCase()}.${String(el.className?.baseVal ?? el.className).split(' ')[0]} «${text.slice(0, 30)}»`)
        }
        const seals = [...document.querySelectorAll('.seal')].map((e) => {
          const cs = getComputedStyle(e)
          const m = cs.transform.match(/matrix\(([^)]+)\)/)
          const [a, b] = m ? m[1].split(',').map(Number) : [1, 0]
          return { op: Number(cs.opacity), scale: Math.hypot(a, b) }
        })
        return { ghosts, seals }
      })
      pages++
      for (const g of r.ghosts) problems.push(`${url} ${screen}: после прокрутки до конца осталось невидимым → ${g}`)
      if (['/', '/kontakty/'].includes(url) && r.seals.length === 0) problems.push(`${url} ${screen}: печати «Сверено» на странице нет`)
      for (const s of r.seals) {
        seals++
        if (s.op < 0.85 || Math.abs(s.scale - 1) > 0.02) {
          problems.push(`${url} ${screen}: печать «Сверено» не видна (непрозрачность ${s.op}, масштаб ${s.scale.toFixed(2)})`)
        }
      }
    }
    await ctx.close()
  }
  if (problems.length === before) {
    console.log(`✓ С обычным движением после прокрутки видно всё: ${pages} страниц, печать «Сверено» — ${seals} замера`)
  }
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
