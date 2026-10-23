// Сквозная проверка сайта: все страницы (одиннадцать и статьи) на шести ширинах, плюс
// первый экран главной, меню и нижняя панель на телефоне.
//
// Живёт в репозитории, а не в рабочей папке сессии: 24.09.2026 рабочая
// папка пропала вместе с контейнером, и с ней — все наборы проверок.
//
//   npm run build && npx vite preview --port 4181 &
//   node scripts/test-site.mjs                       # по умолчанию http://localhost:4181/
//   BASE=http://localhost:4190/first_reposirtory/sro/ node scripts/test-site.mjs
//
// Playwright в зависимостях сайта не нужен (см. build-og.mjs): модуль берётся
// из переменной PLAYWRIGHT, если он лежит не рядом.
import { existsSync, readdirSync } from 'node:fs'
const pw = await import(process.env.PLAYWRIGHT || 'playwright-core')
const { chromium } = pw.default ?? pw

const BASE = process.env.BASE || 'http://localhost:4181/'
// Статьи (15.10.2026) — обходом папки stati/: их число растёт каждую неделю,
// и список, записанный руками, отстал бы от сайта.
const STATI = new URL('../stati/', import.meta.url)
const ARTICLE_PAGES = existsSync(STATI)
  ? ['stati/', ...readdirSync(STATI, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => `stati/${d.name}/`)]
  : []
const PAGES = ['', 'sro-stroiteley/', 'sro-proektirovshchikov/', 'sro-izyskateley/',
  'uslugi/vstuplenie-v-sro/', 'uslugi/podbor-i-proverka-sro/', 'uslugi/dokumenty/',
  'uslugi/specialisty-nrs/', 'uslugi/nok/', 'uslugi/uroven-otvetstvennosti/',
  'uslugi/soprovozhdenie-proverok/', ...ARTICLE_PAGES]
// 1920 — колонка текста шире (80rem с 1800 px, index.css).
const WIDTHS = [320, 390, 768, 1024, 1440, 1920]

const ok = []
const bad = []
const check = (n, c, d = '') => (c ? ok : bad).push(`${c ? 'ok' : 'FAIL'}: ${n}${d ? ' — ' + d : ''}`)

const b = await chromium.launch({ executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium' })

// Прокрутка до низа шагами — чтобы сработали появления и ленивые картинки.
async function scrollThrough(p) {
  await p.evaluate(async () => {
    const step = Math.round(innerHeight * 0.6)
    for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
      scrollTo({ top: y, behavior: 'instant' })
      await new Promise((r) => setTimeout(r, 90))
    }
    scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' })
  })
  await p.waitForTimeout(1500)
}

const linkTargets = new Set()

for (const path of PAGES) {
  for (const W of WIDTHS) {
    const mobile = W < 768
    const ctx = await b.newContext({ viewport: { width: W, height: mobile ? 780 : 900 }, isMobile: mobile, hasTouch: mobile })
    const p = await ctx.newPage()
    const errs = []
    const failed = []
    p.on('console', (m) => m.type() === 'error' && errs.push(m.text()))
    p.on('pageerror', (e) => errs.push(String(e)))
    p.on('response', (r) => { if (r.url().startsWith(BASE) && r.status() >= 400) failed.push(`${r.status()} ${r.url()}`) })
    const tag = `${path || '/'} @${W}`
    const res = await p.goto(BASE + path, { waitUntil: 'networkidle' })
    check(`${tag}: 200`, res.status() === 200, String(res.status()))
    await scrollThrough(p)

    const r = await p.evaluate(() => {
      const text = document.body.innerText
      const vis = (el) => {
        const s = getComputedStyle(el)
        return s.visibility !== 'hidden' && s.display !== 'none' && el.getClientRects().length > 0
      }
      const anchors = [...document.querySelectorAll('a[href]')]
      return {
        hscroll: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        h1: document.querySelectorAll('h1').length,
        placeholder: (text.match(/\[[А-ЯЁA-Z_ ]{2,}\]/) ?? [null])[0],
        banned: ['квиз', 'Оставить заявку', 'политик', 'конфиденциальн', 'Отправить заявку', 'Согласие на обработку']
          .filter((w) => text.toLowerCase().includes(w.toLowerCase())),
        forms: document.querySelectorAll('form, input, textarea, select').length,
        brokenHash: anchors
          .map((a) => a.getAttribute('href'))
          .filter((h) => h.startsWith('#') && h.length > 1 && !document.getElementById(h.slice(1))),
        hrefs: anchors.map((a) => a.href).filter((h) => h.startsWith(location.origin)),
        // Мессенджеры исключены: на телефоне они открывают приложение в той же
        // вкладке, на компьютере — новую; это задумано (README, «Ссылки
        // мессенджеров»).
        externalBad: anchors
          .filter((a) => /^https?:/.test(a.getAttribute('href')) && !a.href.startsWith(location.origin) && !a.dataset.channel)
          .filter((a) => a.target !== '_blank' || !/noopener/.test(a.rel))
          .map((a) => a.href),
        contacts: !!document.getElementById('contacts'),
        tel: document.querySelectorAll('#contacts a[href^="tel:"]').length,
        messengers: document.querySelectorAll('#contacts [data-channel]:not([href^="tel"])').length,
        imgs: [...document.images].filter((i) => !i.complete || i.naturalWidth === 0).map((i) => i.src),
        noAlt: [...document.images].filter((i) => !i.hasAttribute('alt')).map((i) => i.src),
        hiddenReveal: [...document.querySelectorAll('.reveal, .reveal-words, .reveal-image')]
          .filter((el) => vis(el) && !el.classList.contains('is-visible')).length,
        oldDomain: document.documentElement.outerHTML.includes('example.com'),
        // Заголовок, из которого длинное слово вылезает за его колонку:
        // горизонтальной прокрутки при этом нет, слово просто ложится
        // на соседний текст («компенсационные» в узкой колонке раздела).
        // Меряется сам текст (прямоугольники строк), а не scrollWidth:
        // у вопросов FAQ повёрнутый значок «+» выступает на 4 px, букв это
        // не касается.
        wideHeads: [...document.querySelectorAll('h1, h2, h3')]
          .filter((h) => vis(h))
          .filter((h) => {
            const box = h.getBoundingClientRect()
            const walk = document.createTreeWalker(h, NodeFilter.SHOW_TEXT)
            const range = document.createRange()
            for (let t = walk.nextNode(); t; t = walk.nextNode()) {
              range.selectNodeContents(t)
              if ([...range.getClientRects()].some((r) => r.width > 0 && (r.right > box.right + 1 || r.left < box.left - 1))) return true
            }
            return false
          })
          .map((h) => h.textContent.trim().slice(0, 40)),
        // Крупные цифры под шапкой страниц видов СРО стоят без переноса
        // (whitespace-nowrap) — значит, обязаны помещаться в свою плитку.
        wideFacts: [...document.querySelectorAll('section[aria-label="Коротко"] dd')]
          .filter((dd) => {
            const cell = dd.parentElement
            const box = cell.getBoundingClientRect()
            const range = document.createRange()
            range.selectNodeContents(dd)
            return range.getBoundingClientRect().right > box.right - parseFloat(getComputedStyle(cell).paddingRight) + 1
          })
          .map((dd) => dd.textContent),
        // Шрифт заголовков действительно загрузился, а не подменился Georgia.
        displayFont: document.fonts.check('500 40px "Brygada 1918 Variable"', 'Вступление'),
        // Кружок со стрелкой (↗) — только в кнопках «Связаться» (01.10.2026,
        // ui/GoTo.tsx): переход на другую страницу показывает простая
        // стрелка →. Кружок, ведущий не в «Связаться», — вернувшаяся
        // примета шаблона.
        strayCircles: [...document.querySelectorAll('svg.lucide-arrow-up-right')]
          .map((svg) => svg.closest('a, button'))
          .filter((el) => !el || el.getAttribute('href') !== '#contacts')
          .map((el) => (el ? el.getAttribute('href') ?? el.textContent.trim() : 'без ссылки')),
      }
    })
    check(`${tag}: без горизонтальной прокрутки`, r.hscroll <= 1, `${r.hscroll}px`)
    check(`${tag}: один h1`, r.h1 === 1, String(r.h1))
    check(`${tag}: без плейсхолдеров`, !r.placeholder, r.placeholder ?? '')
    check(`${tag}: без следов квиза и политики`, r.banned.length === 0, r.banned.join(', '))
    check(`${tag}: форм и полей ввода нет`, r.forms === 0, String(r.forms))
    check(`${tag}: якоря ведут на существующие id`, r.brokenHash.length === 0, r.brokenHash.join(' '))
    check(`${tag}: внешние ссылки — новая вкладка с noopener`, r.externalBad.length === 0, r.externalBad.join(' '))
    check(`${tag}: раздел «Связаться» на месте`, r.contacts && r.tel >= 1 && r.messengers === 3, `tel ${r.tel}, мессенджеров ${r.messengers}`)
    check(`${tag}: все картинки загрузились`, r.imgs.length === 0, r.imgs.join(' '))
    check(`${tag}: у каждой картинки есть alt`, r.noAlt.length === 0, r.noAlt.join(' '))
    check(`${tag}: после прокрутки всё проявилось`, r.hiddenReveal === 0, `${r.hiddenReveal} блоков остались скрытыми`)
    check(`${tag}: без example.com`, !r.oldDomain)
    check(`${tag}: заголовки не шире своей колонки`, r.wideHeads.length === 0, r.wideHeads.join(' | '))
    check(`${tag}: ключевые цифры помещаются в плитки`, r.wideFacts.length === 0, r.wideFacts.join(' | '))
    check(`${tag}: шрифт заголовков загружен`, r.displayFont)
    check(`${tag}: кружок со стрелкой только у «Связаться»`, r.strayCircles.length === 0, r.strayCircles.join(' '))
    check(`${tag}: без ошибок в консоли`, errs.length === 0, errs[0]?.slice(0, 140) ?? '')
    check(`${tag}: без битых запросов`, failed.length === 0, failed.join(' '))
    if (W === 1440) r.hrefs.forEach((h) => linkTargets.add(h.split('#')[0]))
    await ctx.close()
  }
}

// Каждая внутренняя ссылка открывается.
{
  const ctx = await b.newContext()
  for (const url of linkTargets) {
    const res = await ctx.request.get(url)
    check(`ссылка ${url.replace(BASE, '/')} открывается`, res.status() === 200, String(res.status()))
  }
  check('внутренних адресов не больше страниц сайта', linkTargets.size <= PAGES.length, [...linkTargets].join(' '))
  await ctx.close()
}

// Текст страниц в самом HTML (scripts/prerender.mjs, 15.10.2026): поисковик,
// который не выполняет JavaScript, видит страницу целиком, а не пустой
// <div id="root">. Без скрипта: текст на месте, h1 тот же, что собирает
// браузер, и блоки, которые выплывают по прокрутке, видны (noscript в <head>).
// Со скриптом (с 20.10.2026): скрипт подхватил готовую разметку (класс
// mounted, lib/mounted.ts), а запасной pre-late (скрипт не пришёл за 4 с)
// не включился; класса pre-wait, прятавшего текст до скрипта, нет вовсе.
{
  const off = await b.newContext({ javaScriptEnabled: false, viewport: { width: 1280, height: 900 } })
  const on = await b.newContext({ viewport: { width: 1280, height: 900 } })
  const heading = () => {
    const h1 = document.querySelector('#root h1')
    return h1?.getAttribute('aria-label') ?? h1?.textContent ?? ''
  }
  for (const path of PAGES) {
    const tag = `${path || '/'} без JavaScript`
    const p = await off.newPage()
    await p.goto(BASE + path, { waitUntil: 'load' })
    const raw = await p.evaluate(() => {
      const root = document.getElementById('root')
      const h1 = root.querySelector('h1')
      return {
        h1: h1?.getAttribute('aria-label') ?? h1?.textContent ?? '',
        words: root.innerText.split(/\s+/).filter(Boolean).length,
        hidden: [...root.querySelectorAll('.reveal')].filter((el) => getComputedStyle(el).opacity === '0').length,
        opacity: getComputedStyle(root).opacity,
      }
    })
    await p.close()
    const q = await on.newPage()
    await q.goto(BASE + path, { waitUntil: 'networkidle' })
    const live = { h1: await q.evaluate(heading), cls: await q.evaluate(() => document.documentElement.className) }
    await q.close()
    // Список статей — оглавление: на нём заголовки и строки о сути, а не
    // текст, поэтому порог ниже.
    const minWords = path === 'stati/' ? 150 : 300
    check(`${tag}: текст страницы в HTML`, raw.words >= minWords, `${raw.words} слов`)
    check(`${tag}: h1 тот же, что в браузере`, raw.h1 !== '' && raw.h1 === live.h1, `«${raw.h1}» / «${live.h1}»`)
    check(`${tag}: ничего не спрятано`, raw.hidden === 0 && raw.opacity === '1', `скрытых блоков ${raw.hidden}, прозрачность корня ${raw.opacity}`)
    check(`${path || '/'}: после отрисовки готовый текст не спрятан`, !/\bpre-(wait|late)\b/.test(live.cls), live.cls)
    check(`${path || '/'}: скрипт подхватил готовую страницу`, /\bmounted\b/.test(live.cls), live.cls)
  }
  await off.close()
  await on.close()
}

// Первый экран главной: три вида СРО списком, кадр справа.
//
// Главное, что здесь стережётся, — что видно БЕЗ прокрутки: заголовок,
// кнопка «Связаться» и все три вида. До 26.09.2026 тут стоял слайдер, и в каждый
// момент на экране была треть предложения. Высоты телефона взяты не по
// размеру экрана, а по видимой части окна браузера: адресная строка
// и панель вкладок съедают 60–180 px, и 390 × 844 на деле — 390 × 664…780.
const HERO = 'section[aria-labelledby="hero-title"]'
// Меряется ПОСЛЕ появления: текст первого экрана выплывает снизу на 18 px,
// и замер посреди анимации принимал сдвиг за вёрстку (список «уезжал» за край
// экрана на ровно 18 px). Ждутся только анимации по времени — привязанные
// к прокрутке (.scroll-drift) не кончаются никогда.
const heroGeometry = (p) => p.evaluate(async (sel) => {
  await Promise.all(document.getAnimations()
    .filter((a) => a.timeline === document.timeline)
    .map((a) => a.finished.catch(() => {})))
  const hero = document.querySelector(sel)
  const rect = (el) => el.getBoundingClientRect()
  // Видимый список видов: с 1024 px — строками, на телефоне и планшете —
  // карточками (каждая карточка — ссылка на страницу своего вида).
  const list = [...hero.querySelectorAll('ul[aria-labelledby="hero-types"]')].find((u) => u.getClientRects().length)
  const links = [...list.querySelectorAll('a, button')]
  const buttons = [...hero.querySelectorAll('a[href="#contacts"], a[href^="tel:"]')]
  const photo = hero.querySelector('img')
  return {
    hrefs: links.map((a) => a.getAttribute('href')).filter(Boolean),
    rows: links.map((a) => Math.round(rect(a).height)),
    lastLink: Math.round(Math.max(...links.map((a) => rect(a).bottom))),
    buttonsBottom: Math.round(Math.max(...buttons.map((a) => rect(a).bottom))),
    buttons: buttons.length,
    photoLoaded: photo.complete && photo.naturalWidth > 0,
  }
}, HERO)
{
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.evaluate(() => document.fonts.ready)
  const g = await heroGeometry(p)
  check('первый экран: у каждого вида ссылка на свою страницу',
    g.hrefs.length === 3 && ['sro-stroiteley/', 'sro-proektirovshchikov/', 'sro-izyskateley/'].every((x) => g.hrefs.some((l) => l.endsWith(x))), g.hrefs.join(' '))
  check('первый экран: кадр загрузился', g.photoLoaded)
  check('первый экран 1440 × 900: все три вида видны без прокрутки', g.lastLink <= 900, `низ списка ${g.lastLink}`)
  check('первый экран 1440: подсказки видов в одну строку', g.rows.every((h) => h === g.rows[0]), g.rows.join(','))
  await ctx.close()

  // Проверки «текст не заходит на кадр» здесь больше нет (26.09.2026): кадр
  // растворяется в бумаге и заходит под текст нарочно. Что под буквами он
  // прозрачен, меряет по пикселям scripts/test-hero-contrast.mjs — вместе
  // с заголовком.

  // prefers-reduced-motion: всё видно сразу.
  const rctx = await b.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' })
  const rp = await rctx.newPage()
  await rp.goto(BASE, { waitUntil: 'networkidle' })
  await rp.waitForTimeout(1500)
  const hidden = await rp.evaluate(() => [...document.querySelectorAll('.reveal')].filter((e) => getComputedStyle(e).opacity !== '1').length)
  check('reduced motion: все блоки видны без прокрутки', hidden === 0, String(hidden))
  await rctx.close()
}

// Широкий экран, 01.10.2026. Корневой кегль — обычные 16 px на любой ширине:
// днём макет рос вместе с окном, и заказчик вернул обратно («даже отдаляя —
// не отдаляется»): рост от ширины окна отменяет уменьшение браузера.
// 5760 × 3200 — это 1440 × 800 при масштабе 25 %: там кегль тоже 16 px,
// то есть уменьшение работает. С 1800 px колонка текста 80rem вместо 72rem.
for (const [W, H] of [[1440, 900], [1920, 1000], [2560, 1300], [5760, 3200]]) {
  const colPx = W >= 1800 ? 1280 : 1152
  const ctx = await b.newContext({ viewport: { width: W, height: H } })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  const r = await p.evaluate(() => ({
    root: parseFloat(getComputedStyle(document.documentElement).fontSize),
    col: document.querySelector('header .max-w-6xl').getBoundingClientRect().width,
    hscroll: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }))
  const tag = `широкий экран ${W}×${H}`
  check(`${tag}: корневой кегль 16 px`, r.root === 16, `${r.root} px`)
  check(`${tag}: колонка ${colPx} px`, Math.abs(r.col - colPx) < 1, `${Math.round(r.col)} px`)
  check(`${tag}: без горизонтальной прокрутки`, r.hscroll <= 1, `${r.hscroll}px`)
  await ctx.close()
}

// Шире 1800 px кадры первого экрана, «Документов» и «О нас» держатся
// у колонки текста — не дальше 900 px от центра. Без этого кадр уезжал
// к краю окна и отрывался от текста. Проверяется поведение, а не классы:
// правила Tailwind для ширин идут в конце файла стилей и уже один раз
// молча перебили такую привязку.
{
  const W = 2560
  const reach = 900
  const ctx = await b.newContext({ viewport: { width: W, height: 1300 } })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  // По раскладке (offset*), а не по getBoundingClientRect: у кадров есть
  // движение по прокрутке (scale), и увеличенный на 12 % кадр выглядел бы
  // вылезшим за границу, хотя стоит на месте. Родитель у всех трёх — раздел
  // во всю ширину окна, поэтому offsetLeft — это и есть координата в окне.
  const edges = await p.evaluate(() => {
    const el = (sel) => document.querySelector(sel)
    const right = (e) => e.offsetLeft + e.offsetWidth
    return { hero: right(el('.hero-photo')), docs: el('.docs-photo').offsetLeft, about: right(el('.about-photo')) }
  })
  check(`широкий экран ${W}: кадр первого экрана у колонки текста`, edges.hero <= W / 2 + reach + 1, `правый край ${Math.round(edges.hero)}`)
  check(`широкий экран ${W}: кадр «Документов» у колонки текста`, edges.docs >= W / 2 - reach - 1, `левый край ${Math.round(edges.docs)}`)
  check(`широкий экран ${W}: кадр «О нас» у колонки текста`, edges.about <= W / 2 + reach + 1, `правый край ${Math.round(edges.about)}`)

  // Карта: у каждого выделенного региона есть контур, и наведение на строку
  // списка зажигает его регион (связь списка и карты в обе стороны).
  await p.locator('#regions').scrollIntoViewIfNeeded()
  await p.waitForFunction(() => document.querySelectorAll('#regions svg path[fill^="url(#ru-"]').length > 0)
  const shapes = await p.evaluate(() => {
    const all = [...document.querySelectorAll('#regions svg path[fill^="url(#ru-"]')]
    return { count: all.length, empty: all.filter((el) => !el.getAttribute('d')).length }
  })
  check('карта: у каждого выделенного региона есть контур', shapes.count >= 13 && shapes.empty === 0, `регионов ${shapes.count}, пустых ${shapes.empty}`)
  await p.locator('#regions li div').first().hover()
  const hot = await p.evaluate(() => document.querySelectorAll('#regions svg path[fill="url(#ru-hot)"]').length)
  check('карта: строка списка зажигает свой регион', hot === 1, `подсвечено ${hot}`)
  await ctx.close()
}

// Переход между страницами (@view-transition в index.css). Проверяется, что
// он срабатывает и что первый кадр новой страницы — тот, что снимает смена, —
// уже полный. С 20.10.2026 скрипт отрисовку не блокирует: первый кадр — это
// готовая разметка до скрипта. На нём заголовок обязан стоять на месте
// (без вступления — html.arrived из строчки в <head>, prerender.mjs), а блоки
// в кадре — быть видимыми (html.arrived-settling:not(.mounted) в index.css),
// иначе смена «проявляла» бы страницу без них, и они возникали бы рывком.
// При «уменьшить движение» перехода нет вовсе.
for (const motion of ['no-preference', 'reduce']) {
  const ctx = await b.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: motion })
  await ctx.addInitScript(() => {
    addEventListener('pagereveal', (e) => {
      window.__vt = Boolean(e.viewTransition)
      const h1 = document.querySelector('#root h1')
      const word = h1?.querySelector('.w > span')
      // Блоки в кадре, которые на первом кадре прозрачны или сдвинуты.
      const hiddenInView = [...document.querySelectorAll('#root .reveal, #root .reveal-words .w > span')].filter((el) => {
        const r = el.getBoundingClientRect()
        if (r.bottom <= 0 || r.top >= innerHeight || r.width === 0) return false
        const cs = getComputedStyle(el)
        return cs.opacity === '0' || (cs.transform !== 'none' && cs.transform !== 'matrix(1, 0, 0, 1, 0, 0)')
      }).length
      window.__first = {
        empty: !document.getElementById('root')?.children.length,
        title: !!h1 && !!word && ['none', 'matrix(1, 0, 0, 1, 0, 0)'].includes(getComputedStyle(word).transform) && getComputedStyle(h1).opacity === '1',
        hiddenInView,
      }
    })
  })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  // Скрипты новой страницы — с задержкой, как на медленной сети. Без неё
  // проверка не ловит ничего: с локального сервера скрипт приходит раньше
  // первого кадра, и пустой лист не получается даже без защиты (проверено:
  // blocking="render" убран из сборки — без задержки проверка проходила).
  await p.route(/\/assets\/.+\.js$/, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 700))
    await route.continue()
  })
  await p.locator('#hero-types + ul a').first().click()
  await p.waitForLoadState('networkidle')
  const [vt, first] = await p.evaluate(() => [window.__vt, window.__first])
  if (motion === 'reduce') {
    check('переход между страницами: при «уменьшить движение» его нет', vt === false, String(vt))
  } else {
    check('переход между страницами: срабатывает', vt === true, String(vt))
    check('переход между страницами: новая страница в момент показа не пустая', first?.empty === false, JSON.stringify(first))
    check('переход между страницами: на первом кадре заголовок на месте, блоки в кадре видны',
      first?.title === true && first?.hiddenInView === 0, JSON.stringify(first))
  }
  await ctx.close()
}

// Первый экран не ждёт скрипта (20.10.2026). Готовая разметка видна сразу,
// а скрипт её подхватывает (lib/start.tsx). Скрипты здесь приходят на 5 с
// позже: к 2,8 с вступление первого экрана (CSS) уже отыграло, и заголовок,
// подзаголовок и кнопка обязаны стоять на месте, хотя скрипта ещё нет.
// До 20.10.2026 скрипт блокировал отрисовку, и на телефоне с медленным
// интернетом первый экран появлялся только с ним — через ~1,9 с.
for (const path of ['', 'sro-stroiteley/', 'stati/kak-proverit-sro/']) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  await p.route(/\/assets\/.+\.js$/, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 5000))
    await route.continue().catch(() => {})
  })
  await p.goto(BASE + path, { waitUntil: 'commit' })
  await p.waitForTimeout(2800)
  const r = await p.evaluate(() => {
    const h1 = document.querySelector('#root h1')
    const words = [...(h1?.querySelectorAll('.w > span') ?? [])]
    const box = h1?.getBoundingClientRect()
    // Кнопка первого экрана — в <main>, не в меню шапки; видимость — по её
    // обёртке с анимацией появления (.hero-rise), а не по самой ссылке.
    const button = [...document.querySelectorAll('main a[href="#contacts"]')].find((a) => {
      const rr = a.getBoundingClientRect()
      return rr.width > 0 && rr.top < innerHeight
    })
    return {
      mounted: document.documentElement.classList.contains('mounted'),
      // После анимации браузер отдаёт либо none, либо единичную матрицу.
      h1: !!h1 && box.top < innerHeight && words.length > 0 && words.every((w) => ['none', 'matrix(1, 0, 0, 1, 0, 0)'].includes(getComputedStyle(w).transform)),
      button: !!button && getComputedStyle(button.closest('.hero-rise') ?? button).opacity === '1',
    }
  })
  check(`/${path} до скрипта: скрипт ещё не пришёл`, r.mounted === false, JSON.stringify(r))
  check(`/${path} до скрипта: заголовок первого экрана на месте`, r.h1, JSON.stringify(r))
  check(`/${path} до скрипта: кнопка «Связаться»/«Обсудить задачу» видна`, r.button, JSON.stringify(r))
  await ctx.close()
}

// Подхват готовой разметки (20.10.2026): то, что зависит от адреса и от
// устройства, после подхвата верное. React при подхвате не исправляет
// атрибуты, разошедшиеся с готовой разметкой, — поэтому подсветка открытой
// страницы в меню считается одинаково при сборке и в браузере
// (lib/site.ts, isCurrentPage), а «мышь или палец» решается после подхвата
// (lib/useDesktopPointer.ts).
{
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
  const p = await ctx.newPage()
  await p.goto(BASE + 'sro-stroiteley/', { waitUntil: 'networkidle' })
  const r = await p.evaluate(() => ({
    current: [...document.querySelectorAll('header a[aria-current="page"]')].map((a) => a.getAttribute('href')),
    blank: [...document.querySelectorAll('#contacts [data-channel]:not([href^="tel"])')].map((a) => a.target),
  }))
  check('подхват: в меню подсвечена открытая страница вида', r.current.length >= 1 && r.current.every((h) => h.includes('sro-stroiteley')), JSON.stringify(r.current))
  check('подхват: мессенджеры на компьютере — в новой вкладке', r.blank.length === 3 && r.blank.every((t) => t === '_blank'), JSON.stringify(r.blank))
  await ctx.close()
}

// Телефон: первый экран на разной высоте видимой части окна. На 664
// (iPhone с развёрнутыми панелями Safari) все три вида уже не помещаются —
// там требуются заголовок и кнопки связи, а список начинается у края.
for (const [width, height, need] of [[390, 780, 'all'], [360, 740, 'all'], [390, 664, 'buttons']]) {
  const ctx = await b.newContext({ viewport: { width, height }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.evaluate(() => document.fonts.ready)
  const g = await heroGeometry(p)
  // Кнопка одна (01.10.2026): «Позвонить» повторяла значок телефона в шапке.
  check(`телефон ${width} × ${height}: «Связаться» видна без прокрутки, «Позвонить» не повторяет шапку`, g.buttons === 1 && g.buttonsBottom <= height, `кнопок ${g.buttons}, низ ${g.buttonsBottom}`)
  if (need === 'all') check(`телефон ${width} × ${height}: все три вида видны без прокрутки`, g.lastLink <= height, `низ списка ${g.lastLink}`)
  check(`телефон ${width}: строки видов не ниже 44px и в одну строку`, g.rows.every((h) => h >= 44 && h < 70), g.rows.join(','))
  await ctx.close()
}

// Телефон: меню и нижняя панель.
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  const bar = p.locator('nav[aria-label="Быстрая связь"]')
  check('телефон: нижняя панель скрыта на первом экране', (await bar.getAttribute('aria-hidden')) === 'true')
  // Скрытая панель недоступна и с клавиатуры (22.10.2026, пункт 7):
  // aria-hidden прятал её от диктора, а Tab доходил до невидимых ссылок.
  check('телефон: скрытая нижняя панель недоступна с клавиатуры (inert)', await bar.evaluate((n) => n.inert))
  await p.evaluate(() => scrollTo({ top: 2000, behavior: 'instant' }))
  await p.waitForTimeout(700)
  check('телефон: нижняя панель появилась после прокрутки', (await bar.getAttribute('aria-hidden')) === 'false')
  check('телефон: появившаяся нижняя панель доступна', !(await bar.evaluate((n) => n.inert)))
  // У «Связаться» панель уходит: там те же номер и мессенджеры крупно.
  await p.evaluate(() => document.getElementById('contacts').scrollIntoView({ block: 'start', behavior: 'instant' }))
  await p.waitForTimeout(700)
  check('телефон: у «Связаться» нижняя панель уходит', (await bar.getAttribute('aria-hidden')) === 'true')
  await p.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }))
  await p.locator('header button[aria-label="Открыть меню"]').click()
  await p.waitForTimeout(600)
  const menuLinks = await p.locator('nav[aria-label="Мобильная навигация"] a:visible').count()
  check('телефон: меню открывается', menuLinks > 5, String(menuLinks))
  // «Контакты» в меню ведут к разделу (data-direct), «Связаться» в меню —
  // открывает панель связи поверх страницы, как кнопки «Связаться» везде
  // на телефоне (22.10.2026, пункт 2).
  await p.locator('nav[aria-label="Мобильная навигация"] a:visible', { hasText: 'Контакты' }).first().click()
  await p.waitForTimeout(1500)
  const top = await p.evaluate(() => document.getElementById('contacts').getBoundingClientRect().top)
  check('телефон: «Контакты» из меню приводят к разделу «Связаться»', Math.abs(top) < 200, String(Math.round(top)))
  await p.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }))
  await p.locator('header button[aria-label="Открыть меню"]').click()
  await p.waitForTimeout(600)
  await p.locator('header a:visible', { hasText: 'Связаться' }).last().click()
  await p.waitForTimeout(900)
  const m = await p.evaluate(() => ({
    sheet: document.querySelector('dialog[data-contact-sheet]').open,
    menu: getComputedStyle(document.getElementById('mobile-menu')).visibility,
    y: Math.round(scrollY),
  }))
  check('телефон: «Связаться» из меню открывает панель связи, меню закрыто', m.sheet && m.menu === 'hidden' && m.y === 0, JSON.stringify(m))
  await ctx.close()
}

// Меню телефона: открытая страница отмечена (22.10.2026, пункт 6) — как
// в меню компьютера: фоном и цветом пункта, для диктора — aria-current.
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  for (const [path, href] of [['sro-stroiteley/', 'sro-stroiteley/'], ['uslugi/dokumenty/', 'uslugi/dokumenty/']]) {
    await p.goto(BASE + path, { waitUntil: 'networkidle' })
    await p.locator('header button[aria-label="Открыть меню"]').click()
    await p.waitForTimeout(600)
    const cur = await p.evaluate(() => [...document.querySelectorAll('#mobile-menu a[aria-current="page"]')].map((a) => ({
      href: a.getAttribute('href'),
      bg: getComputedStyle(a).backgroundColor,
      visible: a.checkVisibility(),
    })))
    check(`меню телефона на ${path}: открытая страница отмечена`,
      cur.length === 1 && cur[0].href.endsWith(href) && cur[0].visible && cur[0].bg !== 'rgba(0, 0, 0, 0)', JSON.stringify(cur))
  }
  await ctx.close()
}

// Панель «Связаться» на телефоне (22.10.2026, пункт 2): кнопки «Связаться»,
// «Обсудить задачу», «Проверить мои документы» открывают способы связи
// поверх страницы, а не уводят к разделу в конце (на главной — прыжок
// на 18 экранов). Страница стоит на месте. В WhatsApp — начало сообщения
// по теме кнопки, у письма — тема.
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  const errs = []
  p.on('pageerror', (e) => errs.push(String(e)))
  await p.goto(BASE, { waitUntil: 'networkidle' })
  const sheet = () => p.evaluate(() => {
    const d = document.querySelector('dialog[data-contact-sheet]')
    const wa = d.querySelector('[data-channel="WhatsApp"]')
    const mail = d.querySelector('[data-channel="Почта"]')
    const box = d.querySelector('.sheet-panel').getBoundingClientRect()
    return {
      open: d.open,
      y: Math.round(scrollY),
      wa: wa ? new URL(wa.href).searchParams.get('text') : null,
      subject: mail ? decodeURIComponent(mail.getAttribute('href').split('subject=')[1] ?? '') : null,
      bottom: Math.round(box.bottom),
      focus: d.contains(document.activeElement),
    }
  })
  // Касание по координатам: tap() Playwright прокручивает к элементу сам
  // (плавно — у страницы scroll-behavior: smooth), и проверка «страница
  // на месте» мерила бы его прокрутку, а не панель.
  const tapAt = async (loc) => {
    const box = await loc.boundingBox()
    await p.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2)
  }
  const toCenter = (loc) => loc.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }))
  await tapAt(p.locator('section[aria-labelledby="hero-title"] a[href="#contacts"]:visible').first())
  await p.waitForTimeout(800)
  let s = await sheet()
  check('панель связи: «Связаться» на первом экране открывает её, страница на месте', s.open && s.y === 0, JSON.stringify(s))
  check('панель связи: стоит у нижнего края, фокус в ней', Math.abs(s.bottom - 780) <= 1 && s.focus, JSON.stringify(s))
  check('панель связи: в WhatsApp набрано начало сообщения', /консультация по вступлению в СРО/.test(s.wa ?? ''), s.wa ?? '')
  await p.locator('dialog[data-contact-sheet] button[aria-label="Закрыть"]').tap()
  await p.waitForTimeout(800)
  check('панель связи: крестик закрывает', !(await sheet()).open)

  const docs = p.locator('a[data-topic="documents"]')
  await toCenter(docs)
  await p.waitForTimeout(400)
  const y0 = await p.evaluate(() => Math.round(scrollY))
  await tapAt(docs)
  await p.waitForTimeout(800)
  s = await sheet()
  check('панель связи: «Проверить мои документы» — на месте прокрутки, тема о документах',
    s.open && Math.abs(s.y - y0) <= 2 && /проверить документы/.test(s.wa ?? '') && /Проверка документов/.test(s.subject ?? ''), JSON.stringify({ y0, ...s }))
  await p.keyboard.press('Escape')
  await p.waitForTimeout(800)
  s = await sheet()
  check('панель связи: Esc закрывает, страница на месте', !s.open && Math.abs(s.y - y0) <= 2, JSON.stringify(s))
  await tapAt(docs)
  await p.waitForTimeout(800)
  await p.touchscreen.tap(195, 30)
  await p.waitForTimeout(800)
  check('панель связи: касание затемнения закрывает', !(await sheet()).open)
  await tapAt(docs)
  await p.waitForTimeout(800)
  await p.locator('dialog[data-contact-sheet] a', { hasText: 'Адрес и карта' }).tap()
  await p.waitForTimeout(1500)
  const end = await p.evaluate(() => ({
    open: document.querySelector('dialog[data-contact-sheet]').open,
    top: Math.round(document.getElementById('contacts').getBoundingClientRect().top),
  }))
  check('панель связи: «Адрес и карта» ведёт к разделу «Связаться»', !end.open && Math.abs(end.top) < 200, JSON.stringify(end))
  check('панель связи: без ошибок', errs.length === 0, errs[0] ?? '')

  // Тема страницы: у вида СРО — его название, и в нижней панели тоже.
  await p.goto(BASE + 'sro-stroiteley/', { waitUntil: 'networkidle' })
  const discuss = p.locator('main a[href="#contacts"]:visible', { hasText: 'Обсудить задачу' }).first()
  await toCenter(discuss)
  await p.waitForTimeout(400)
  await tapAt(discuss)
  await p.waitForTimeout(800)
  s = await sheet()
  const barWa = await p.evaluate(() => new URL(document.querySelector('nav[aria-label="Быстрая связь"] [data-channel="WhatsApp"]').href).searchParams.get('text'))
  check('панель связи: на странице вида тема — вид СРО', s.open && /СРО строителей/.test(s.wa ?? '') && /СРО строителей/.test(s.subject ?? ''), JSON.stringify(s))
  check('нижняя панель: WhatsApp с темой страницы', /СРО строителей/.test(barWa ?? ''), barWa ?? '')
  await ctx.close()
}

// Компьютер: панели нет — «Связаться» ведёт к разделу, как раньше; номер
// и «Связаться» всегда в шапке.
{
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.locator('section[aria-labelledby="hero-title"] a[href="#contacts"]:visible').first().click()
  await p.waitForTimeout(1500)
  const r = await p.evaluate(() => ({
    open: document.querySelector('dialog[data-contact-sheet]').open,
    top: Math.round(document.getElementById('contacts').getBoundingClientRect().top),
  }))
  check('компьютер: «Связаться» ведёт к разделу, панели нет', !r.open && Math.abs(r.top) < 200, JSON.stringify(r))
  await ctx.close()
}

// Клавиатура (22.10.2026, пункт 7): первая ссылка страницы — «Перейти
// к содержанию», видна в фокусе и уводит фокус в main; следующий Tab —
// к первой ссылке содержания, а не обратно в шапку.
{
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
  const p = await ctx.newPage()
  await p.goto(BASE + 'sro-stroiteley/', { waitUntil: 'networkidle' })
  await p.keyboard.press('Tab')
  const first = await p.evaluate(() => {
    const a = document.activeElement
    const r = a.getBoundingClientRect()
    return { text: a.textContent.trim(), w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top) }
  })
  check('клавиатура: первая ссылка — «Перейти к содержанию», видна в фокусе',
    first.text === 'Перейти к содержанию' && first.w > 100 && first.h >= 36 && first.top >= 0, JSON.stringify(first))
  await p.keyboard.press('Enter')
  await p.waitForTimeout(300)
  const main = await p.evaluate(() => document.activeElement?.id)
  await p.keyboard.press('Tab')
  const next = await p.evaluate(() => ({
    inMain: !!document.activeElement?.closest('main'),
    text: document.activeElement?.textContent.trim().slice(0, 30),
    tabindex: document.getElementById('main').getAttribute('tabindex'),
  }))
  check('клавиатура: «Перейти к содержанию» ведёт в main, дальше — содержание страницы',
    main === 'main' && next.inMain && next.tabindex === null, JSON.stringify({ main, ...next }))
  await ctx.close()
}

// Области нажатия не меньше 44 px (22.10.2026, пункт 5): «Назад» в шапке
// страниц, знак в шапке, номер телефона в «Связаться»; у вкладок ООО / ИП
// кнопка 36 px, но нажатие ловится и на 4 px выше и ниже (::after).
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  await p.goto(BASE + 'sro-stroiteley/', { waitUntil: 'networkidle' })
  await scrollThrough(p)
  const r = await p.evaluate(() => {
    const h = (el) => (el ? Math.round(el.getBoundingClientRect().height) : 0)
    const tabs = [...document.querySelectorAll('[role="tab"]')].filter((t) => t.checkVisibility()).map((t) => {
      t.scrollIntoView({ block: 'center', behavior: 'instant' })
      const box = t.getBoundingClientRect()
      const x = box.left + box.width / 2
      const hit = (y) => {
        const el = document.elementFromPoint(x, y)
        return el === t || t.contains(el)
      }
      return { h: Math.round(box.height), above: hit(box.top - 3), below: hit(box.bottom + 3) }
    })
    return {
      back: h(document.querySelector('main section .hero-rise a')),
      logo: h(document.querySelector('header a[href]:not([href="#main"])')),
      tel: h(document.querySelector('#contacts a[href^="tel"]')),
      tabs,
    }
  })
  check('нажатие: «Назад» в шапке страницы — не меньше 44 px', r.back >= 44, String(r.back))
  check('нажатие: знак в шапке — не меньше 44 px', r.logo >= 44, String(r.logo))
  check('нажатие: номер телефона в «Связаться» — не меньше 44 px', r.tel >= 44, String(r.tel))
  check('нажатие: вкладки ООО / ИП ловят нажатие и чуть выше, и чуть ниже',
    r.tabs.length >= 2 && r.tabs.every((t) => t.above && t.below), JSON.stringify(r.tabs))
  await ctx.close()
}

// Вкладки документов (22.10.2026, пункт 7): роль tabpanel — у обёртки,
// а не у самого списка: у ul с ролью tabpanel пункты списка теряли
// родителя-список для диктора (axe: listitem, aria-allowed-role).
{
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
  const p = await ctx.newPage()
  for (const path of ['sro-stroiteley/', 'uslugi/dokumenty/']) {
    await p.goto(BASE + path, { waitUntil: 'networkidle' })
    const r = await p.evaluate(() => [...document.querySelectorAll('[role="tabpanel"]')].map((el) => ({
      tag: el.tagName,
      list: !!el.querySelector('ul, ol'),
      label: !!document.getElementById(el.getAttribute('aria-labelledby') ?? ''),
    })))
    check(`${path}: панели вкладок — обёртки вокруг списков`, r.length > 0 && r.every((x) => x.tag === 'DIV' && x.list && x.label), JSON.stringify(r))
  }
  await ctx.close()
}

// Порядок разделов главной (22.10.2026, разбор главной): цена и «О компании»
// выше, «Лицензии» — перед «О компании». Светлые и тёмные разделы
// чередуются: соседи с одним фоном слились бы в один раздел.
{
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  const r = await p.evaluate(() => {
    const kids = [...document.querySelector('main').children].filter((el) => el.tagName === 'SECTION')
    return {
      ids: kids.map((el) => el.id || el.getAttribute('aria-labelledby')),
      bgs: kids.map((el) => getComputedStyle(el).backgroundColor),
      lead: [...document.querySelectorAll('section[aria-labelledby="hero-title"] p')].map((el) => el.textContent).find((t) => /Подберу/.test(t)) ?? '',
    }
  })
  const want = ['hero-title', 'services', 'process', 'pricing', 'nrs', 'documents', 'licenzii', 'about', 'articles', 'faq', 'regions', 'contacts']
  check('главная: порядок разделов', JSON.stringify(r.ids) === JSON.stringify(want), r.ids.join(' → '))
  const same = r.bgs.map((bg, i) => (i && bg === r.bgs[i - 1] && bg !== 'rgba(0, 0, 0, 0)' ? `${r.ids[i - 1]}/${r.ids[i]}` : null)).filter(Boolean)
  check('главная: у соседних разделов разный фон', same.length === 0, same.join(' '))
  check('главная: на первом экране «Консультация бесплатная»', /Консультация\s+бесплатная/.test(r.lead), r.lead)
  await ctx.close()
}

// «Лицензии» до 1024 px свёрнуты (22.10.2026): название и перечень строкой,
// нажатие раскрывает описание и пункты с нормами. С 1024 px открыты всегда,
// кнопок там нет.
for (const [w, h, mobile] of [[390, 844, true], [820, 1180, true], [1440, 900, false]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mobile, hasTouch: mobile })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.evaluate(() => document.getElementById('licenzii').scrollIntoView({ block: 'start', behavior: 'instant' }))
  await p.waitForTimeout(1200)
  const state = () => p.evaluate(() => [...document.querySelectorAll('#licenzii article')].map((a) => ({
    button: a.querySelector('button[aria-expanded]')?.checkVisibility() ?? false,
    expanded: a.querySelector('button[aria-expanded]')?.getAttribute('aria-expanded'),
    items: [...a.querySelectorAll('li h4')].filter((h4) => h4.checkVisibility({ visibilityProperty: true }) && h4.getBoundingClientRect().height > 0).length,
  })))
  const s0 = await state()
  if (w < 1024) {
    check(`«Лицензии» ${w}: листы свёрнуты, видны названия и перечни`, s0.length === 3 && s0.every((x) => x.button && x.expanded === 'false' && x.items === 0), JSON.stringify(s0))
    const btn = p.locator('#licenzii article').nth(1).locator('button[aria-expanded]')
    const box = await btn.boundingBox()
    if (mobile) await p.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2)
    else await btn.click()
    await p.waitForTimeout(900)
    const s1 = await state()
    check(`«Лицензии» ${w}: нажатие раскрывает лист с пунктами`, s1[1].expanded === 'true' && s1[1].items === 4 && s1[0].items === 0, JSON.stringify(s1))
  } else {
    check(`«Лицензии» ${w}: листы открыты, кнопок нет`, s0.length === 3 && s0.every((x) => !x.button && x.items > 0), JSON.stringify(s0))
  }
  await ctx.close()
}

// «Как проверить СРО»: кнопки официальных реестров (22.10.2026) — в новой
// вкладке, с noopener, только сайты Ростехнадзора, НОСТРОЙ и НОПРИЗ.
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  await p.goto(BASE + 'stati/kak-proverit-sro/', { waitUntil: 'networkidle' })
  const links = await p.evaluate(() => [...document.querySelectorAll('main a[target="_blank"]')]
    .filter((a) => /gosnadzor|nostroy|nopriz/.test(a.href))
    .map((a) => ({ href: a.getAttribute('href'), rel: a.rel, h: Math.round(a.getBoundingClientRect().height) })))
  check('«Как проверить СРО»: три кнопки реестров', links.length === 3 && links.every((l) => /noopener/.test(l.rel) && l.h >= 44), JSON.stringify(links))
  await ctx.close()
}

// «Сколько стоит вступление в СРО» (22.10.2026): суммы фондов в статье
// записаны руками (articles.ts читает Node, импортировать таблицы нельзя) —
// поэтому они обязаны совпасть с суммами на страницах видов СРО.
{
  const ctx = await b.newContext()
  const sums = async (path) => {
    const html = await (await ctx.request.get(BASE + path)).text()
    const main = html.slice(html.indexOf('<main'), html.indexOf('</main>'))
    return new Set([...main.matchAll(/(?<![\d\s\u00a0])(\d{1,3}(?:[\s\u00a0\u202f]\d{3})*)[\s\u00a0\u202f]₽/g)]
      .map((m) => m[1].replace(/\D/g, '')))
  }
  const art = await sums('stati/skolko-stoit-vstuplenie-v-sro/')
  const types = new Set([...(await sums('sro-stroiteley/')), ...(await sums('sro-proektirovshchikov/'))])
  const diff = [...art].filter((x) => !types.has(x)).concat([...types].filter((x) => !art.has(x)))
  check('«Сколько стоит»: суммы фондов совпадают со страницами видов СРО', art.size >= 14 && diff.length === 0, `${art.size} сумм; расхождения: ${diff.join(', ') || 'нет'}`)
  await ctx.close()
}

// Разбор Replica (23.10.2026), bugs.md. B01: рамка фокуса у строк услуг
// на светлом фоне — не ниже 3:1 (WCAG 1.4.11); светлая латунь accent-400
// давала 2,3–2,5:1. B02: о цене работы на странице статьи — один раздел
// «Сколько стоит…», а не свой раздел статьи плюс общий блок под ним.
{
  const lum = (rgb) => { const c = rgb.map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 }); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] }
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05) }
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.locator('#services').scrollIntoViewIfNeeded()
  const rows = await p.locator('#services a').count()
  const found = []
  for (let i = 0; i < rows; i++) {
    const a = p.locator('#services a').nth(i)
    await a.evaluate((e) => e.focus({ focusVisible: true }))
    await p.waitForTimeout(80)
    found.push(await a.evaluate((e) => {
      const nums = (s) => (s.match(/rgba?\(([^)]+)\)/)?.[1] || '').split(',').slice(0, 3).map(Number)
      // Кольцо Tailwind — тень с растяжкой больше нуля и непрозрачным цветом;
      // тень отступа (растяжка 0) и прозрачные заглушки рядом не в счёт.
      const shadow = getComputedStyle(e).boxShadow
      const part = shadow === 'none' ? null : shadow.split(/,(?![^(]*\))/)
        .find((x) => !/rgba\([^)]*,\s*0\)/.test(x) && parseFloat((x.match(/(-?[\d.]+)px\s*$/) || [])[1] || '0') > 0)
      const ring = part ? nums(part) : null
      let bg = null
      for (let el = e.parentElement; el; el = el.parentElement) { const c = getComputedStyle(el).backgroundColor; if (c !== 'rgba(0, 0, 0, 0)') { bg = nums(c); break } }
      return { text: e.textContent.trim().slice(0, 24), ring, bg }
    }))
  }
  const bad = found.filter((f) => f.ring && f.ring.length === 3 && ratio(f.ring, f.bg) < 3).map((f) => `${f.text}: ${ratio(f.ring, f.bg).toFixed(2)}:1`)
  check('рамка фокуса у строк услуг на светлом — от 3:1', found.some((f) => f.ring) && bad.length === 0, bad.join('; ') || `${found.filter((f) => f.ring).length} рамок`)
  await ctx.close()
  const c2 = await b.newContext()
  for (const path of ARTICLE_PAGES.filter((x) => x !== 'stati/')) {
    const html = await (await c2.request.get(BASE + path)).text()
    const n = [...html.matchAll(/<h2[^>]*>([^<]*)<\/h2>/g)].filter((m) => m[1].trim().startsWith('Сколько стоит')).length
    check(`${path}: «Сколько стоит» — один раздел`, n === 1, `${n}`)
  }
  await c2.close()
}

// Картинки для мессенджеров (22.10.2026): у каждой страницы, кроме главной,
// своя картинка с её заголовком; файл на месте, 1200 × 630.
{
  const ctx = await b.newContext()
  const seen = new Set()
  for (const path of PAGES) {
    const html = await (await ctx.request.get(BASE + path)).text()
    const og = html.match(/<meta property="og:image" content="([^"]+)"/)?.[1] ?? ''
    const file = og.replace(/^https?:\/\/[^/]+\//, '')
    const res = await ctx.request.get(BASE + file)
    const ok = res.status() === 200 && /^image\//.test(res.headers()['content-type'] ?? '')
    check(`${path || '/'}: картинка для мессенджеров ${file}`, ok && (path === '' ? file === 'og.png' : file === `og/${path.replace(/\/$/, '').replace(/\//g, '-')}.jpg`), `${res.status()} ${og}`)
    seen.add(file)
  }
  check('картинки для мессенджеров у страниц разные', seen.size === PAGES.length, `${seen.size} из ${PAGES.length}`)
  await ctx.close()
}

// Список видов на первом экране. С 1024 px — строками, подпись вида СРО
// у всех трёх строк справа, занятие в одну строку (01.10.2026: строки
// переносились сами, и подпись стояла то справа, то снизу). До 1024 px —
// карточками одной высоты, занятие в одну строку.
{
  const ctx = await b.newContext()
  const p = await ctx.newPage()
  for (const w of [320, 375, 412, 480, 640, 768, 1023, 1024, 1100, 1280, 1440]) {
    await p.setViewportSize({ width: w, height: 900 })
    await p.goto(BASE, { waitUntil: 'networkidle' })
    await p.evaluate(() => document.fonts.ready)
    const r = await p.evaluate(() => {
      const list = [...document.querySelectorAll('ul[aria-labelledby="hero-types"]')].find((u) => u.getClientRects().length)
      const cards = list.hasAttribute('data-hero-cards')
      const items = [...list.querySelectorAll(':scope > li > a, :scope > li > button')]
      return {
        cards,
        rows: items.map((a) => {
          const title = cards ? a.querySelector('.font-semibold') : a.children[0]
          const t = title.getBoundingClientRect()
          const lines = Math.round(t.height / parseFloat(getComputedStyle(title).lineHeight))
          const h = cards ? null : a.children[1].getBoundingClientRect()
          // Подпись вида под занятием (карточки) — тоже в одну строку.
          const sub = cards ? title.nextElementSibling : null
          const subTwo = sub ? sub.getBoundingClientRect().height > parseFloat(getComputedStyle(sub).lineHeight) * 1.5 : null
          return { lines, subTwo, height: Math.round(a.getBoundingClientRect().height), right: h ? h.top < t.bottom - 2 : null }
        }),
      }
    })
    const ok3 = r.rows.length === 3
    if (w < 1024) {
      check(`первый экран ${w}: виды СРО — карточками`, r.cards && ok3)
      check(`первый экран ${w}: карточки одной высоты`, ok3 && r.rows.every((x) => Math.abs(x.height - r.rows[0].height) <= 1), r.rows.map((x) => x.height).join(' / '))
      check(`первый экран ${w}: подпись вида СРО в карточке в одну строку`, ok3 && r.rows.every((x) => x.subTwo === false), r.rows.map((x) => (x.subTwo ? '2' : '1')).join(' / '))
    } else {
      check(`первый экран ${w}: подпись вида СРО у всех строк справа`, !r.cards && ok3 && r.rows.every((x) => x.right), r.rows.map((x) => (x.right ? 'справа' : 'под')).join(' / '))
    }
    check(`первый экран ${w}: занятие в одну строку`, ok3 && r.rows.every((x) => x.lines === 1), r.rows.map((x) => x.lines).join(' / '))
  }
  await ctx.close()
}

// Телефон: карточка вида открывает свою страницу с одного нажатия
// (22.10.2026, разбор удобства, пункт 1). До того первое нажатие только
// выбирало вид и меняло кадр обложки, страница открывалась вторым — а его
// не угадывали: нажал, ничего не открылось. Выбранной карточки больше нет.
// На обложке кран, и кадры двух других видов на телефоне не грузятся:
// показывать их некому — смена кадра осталась только для мыши.
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  const frames = []
  p.on('request', (r) => /slide-(design|survey)/.test(r.url()) && frames.push(r.url().split('/').pop()))
  await p.goto(BASE, { waitUntil: 'networkidle' })
  // Раньше кадры видов грузились, когда браузер освободится, — подождать
  // с запасом, чтобы проверка видела и отложенную загрузку.
  await p.waitForTimeout(3500)
  const s0 = await p.evaluate(() => {
    const items = [...document.querySelectorAll('[data-hero-cards] > li > *')]
    const pics = [...document.querySelectorAll('section[aria-labelledby="hero-title"] .lg\\:hidden picture img')]
    return {
      tags: items.map((el) => el.tagName).join(','),
      selected: items.filter((el) => el.hasAttribute('data-selected') || el.hasAttribute('aria-pressed')).length,
      pics: pics.map((img) => img.getAttribute('src').replace(/\?.*$/, '').split('/').pop()),
    }
  })
  check('телефон: каждая карточка вида — ссылка', s0.tags === 'A,A,A', s0.tags)
  check('телефон: «выбранной» карточки нет', s0.selected === 0, String(s0.selected))
  check('телефон: на обложке кран, кадры других видов не грузятся', s0.pics.length === 1 && /hero-day/.test(s0.pics[0]) && frames.length === 0, `${s0.pics.join(' ')} | ${frames.join(' ')}`)
  await p.locator('[data-hero-cards] > li').nth(1).locator('a').tap()
  await p.waitForURL(/sro-proektirovshchikov\/$/, { timeout: 5000 }).catch(() => {})
  check('телефон: одно нажатие на карточку открывает страницу вида', /sro-proektirovshchikov\/$/.test(p.url()), p.url())
  await ctx.close()
}

// Планшет с мышью: наведение на карточку меняет кадр обложки на кадр вида,
// мышь ушла с карточек — снова кран. Смена без рывка (01.10.2026): карточки
// при смене не пересоздаются, а прежний кадр держится под новым, пока тот
// проступает (иначе на середине смены сквозь оба полупрозрачных кадра мигал
// тёмный фон).
{
  const ctx = await b.newContext({ viewport: { width: 800, height: 1000 } })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  // Кадры других видов грузятся, когда браузер свободен, — дождаться их.
  await p.waitForFunction(() => document.querySelectorAll('section[aria-labelledby="hero-title"] .lg\\:hidden picture img').length === 3)
  await p.evaluate(() => document.querySelectorAll('[data-hero-cards] > li > a').forEach((a, i) => { a.dataset.mark = String(i) }))
  const pictures = 'section[aria-labelledby="hero-title"] .lg\\:hidden picture'
  const state = () => p.evaluate((sel) => {
    const file = (el) => el.querySelector('img').getAttribute('src').replace(/\?.*$/, '').split('/').pop()
    return {
      marks: [...document.querySelectorAll('[data-hero-cards] > li > *')].map((el) => el.dataset.mark).join(','),
      shown: [...document.querySelectorAll(sel)].filter((el) => getComputedStyle(el).opacity === '1').map(file),
      top: [...document.querySelectorAll(sel)].filter((el) => el.hasAttribute('data-shown')).map(file),
    }
  }, pictures)
  // Мышь ставится по координатам: hover() Playwright сначала прокручивает
  // к карточке, и при плавной прокрутке страницы (scroll-behavior: smooth)
  // карточка уезжала из-под неподвижной мыши — кадр возвращался к крану.
  // На 800 × 1000 все три карточки в окне и без прокрутки.
  const point = async (i) => {
    const box = await p.locator('[data-hero-cards] > li').nth(i).locator('a').boundingBox()
    await p.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
  }
  const inView = await p.evaluate(() => [...document.querySelectorAll('[data-hero-cards] a')].every((a) => a.getBoundingClientRect().bottom <= innerHeight))
  check('планшет 800 × 1000: карточки видов в окне без прокрутки', inView)
  for (const [i, file] of [[1, 'slide-design'], [2, 'slide-survey']]) {
    await point(i)
    // Середина смены: новый кадр сверху проступает, прежний под ним целиком.
    await p.waitForTimeout(250)
    const mid = await p.evaluate((sel) => [...document.querySelectorAll(sel)].map((el) => ({ top: el.hasAttribute('data-shown'), o: Number(getComputedStyle(el).opacity) })), pictures)
    const rising = mid.find((x) => x.top)
    check(`планшет: смена на «${file}» без мигания — прежний кадр держится под новым`,
      rising && rising.o > 0 && rising.o < 1 && mid.some((x) => !x.top && x.o === 1), JSON.stringify(mid))
    await p.waitForTimeout(1300)
    const st = await state()
    check(`планшет: наведение на вид ${i + 1} меняет кадр обложки, страница та же`, p.url() === BASE && st.top[0]?.startsWith(file) && st.shown.length === 1 && st.shown[0].startsWith(file), `${p.url()} ${st.shown.join(' ')}`)
    check('планшет: карточки при смене кадра не пересоздаются', st.marks === '0,1,2', st.marks)
  }
  await p.mouse.move(780, 990)
  await p.waitForTimeout(1600)
  const back = await state()
  check('планшет: мышь ушла с карточек — на обложке снова кран', /hero-day/.test(back.top[0] || '') && back.shown.length === 1, back.shown.join(' '))
  await ctx.close()
}

// Заголовок обложки — поверх кадра при любой настройке движения и после
// смены кадра: при «уменьшить движение» у обложки нет анимации, а с ней
// и своего контекста наложения, и кадр со z-index ложился на заголовок.
for (const motion of ['no-preference', 'reduce']) {
  // Кадр меняет наведение мыши (с 22.10.2026 касание открывает страницу),
  // поэтому окно телефонной ширины — без касаний.
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, reducedMotion: motion })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.waitForFunction(() => document.querySelectorAll('section[aria-labelledby="hero-title"] .lg\\:hidden picture img').length === 3)
  // Мышь — по координатам (см. проверку планшета выше): вторая карточка
  // на 390 × 780 в окне, страница не прокручивается.
  const box = await p.locator('[data-hero-cards] > li').nth(1).locator('a').boundingBox()
  await p.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
  await p.waitForTimeout(1600)
  const top = await p.evaluate(() => {
    const shown = document.querySelector('section[aria-labelledby="hero-title"] .lg\\:hidden picture[data-shown] img')?.getAttribute('src') ?? ''
    const h = document.getElementById('hero-title')
    const r = h.getBoundingClientRect()
    const el = document.elementFromPoint(r.left + 20, r.top + r.height / 2)
    return { who: h.contains(el) ? 'заголовок' : `${el?.tagName}.${el?.className}`.slice(0, 80), shown: shown.replace(/\?.*$/, '').split('/').pop() }
  })
  check(`телефон (${motion}): после смены кадра заголовок обложки поверх кадра`, top.who === 'заголовок' && /slide-design/.test(top.shown), JSON.stringify(top))
  await ctx.close()
}

// Переход между страницами без рывка (01.10.2026, заказчик: «дёргается,
// когда открываю раздел и когда выхожу»). Первый заход — со вступлением
// (кадр проявляется, заголовок поднимается); страница, открытая со своей
// страницы или кнопкой «Назад», стоит на месте сразу — её показывает смена
// страниц, и вступление поверх смены читалось подёргиванием. Смена — новая
// страница проступает поверх неподвижной прежней, без сдвига.
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  const intro = () => p.evaluate(() => ({
    arrived: document.documentElement.classList.contains('arrived'),
    running: document.getAnimations()
      .filter((a) => a.timeline === document.timeline && a.playState === 'running')
      .map((a) => a.animationName || a.transitionProperty || '?')
      .filter((n) => ['develop', 'print-settle', 'rise', 'transform', 'opacity'].includes(n)).length,
  }))
  await p.goto(BASE, { waitUntil: 'domcontentloaded' })
  const first = await intro()
  check('первый заход: вступление первого экрана играет', !first.arrived && first.running > 0, JSON.stringify(first))
  await p.waitForTimeout(1500)
  await p.locator('[data-hero-cards] > li').nth(2).locator('a').tap()
  await p.waitForURL(/sro-izyskateley\/$/)
  await p.waitForLoadState('domcontentloaded')
  const inner = await intro()
  check('переход внутри сайта: страница вида без вступления', inner.arrived && inner.running === 0, JSON.stringify(inner))
  await p.goBack()
  await p.waitForLoadState('domcontentloaded')
  const back = await intro()
  check('«Назад» на главную: обложка не проявляется заново', back.arrived && back.running === 0, JSON.stringify(back))
  const vt = await p.evaluate(() => {
    const rules = [...document.styleSheets].flatMap((sh) => { try { return [...sh.cssRules] } catch { return [] } })
    const flat = (list) => list.flatMap((r) => (r.cssRules ? [r, ...flat([...r.cssRules])] : [r]))
    const all = flat(rules)
    const old = all.find((r) => r.selectorText === '::view-transition-old(root)')
    const nw = all.find((r) => r.selectorText === '::view-transition-new(root)')
    const kf = all.find((r) => r.type === CSSRule.KEYFRAMES_RULE && r.name === 'vt-in')
    return {
      old: old && `${old.style.animationName || old.style.animation}|${old.style.mixBlendMode}`,
      nw: nw && nw.style.mixBlendMode,
      slide: kf ? /transform/.test(kf.cssText) : null,
    }
  })
  check('смена страниц: прежняя стоит под новой, без вспышки и без сдвига',
    vt.old === 'none|normal' && vt.nw === 'normal' && vt.slide === false, JSON.stringify(vt))
  await ctx.close()
}

// Меню телефона и группы подвала — плавно, без рывка (01.10.2026, заказчик:
// «чтобы всё плавно открывалось и закрывалось»). Меню — лист поверх
// страницы: страница под ним не сдвигается (раньше меню стояло в потоке
// липкой шапки и сталкивало её вниз), закрытое — недоступно, касание
// по тени закрывает. Группа подвала раскрывается по высоте, а не скачком.
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  await p.goto(BASE + 'sro-izyskateley/', { waitUntil: 'networkidle' })
  const h1 = () => p.evaluate(() => Math.round(document.querySelector('h1').getBoundingClientRect().top))
  const closedLinks = await p.locator('#mobile-menu a:visible').count()
  check('телефон: закрытое меню недоступно', closedLinks === 0, String(closedLinks))
  const y0 = await h1()
  await p.locator('header button[aria-label="Открыть меню"]').tap()
  const mid = await p.evaluate(() => Number(getComputedStyle(document.getElementById('mobile-menu')).opacity))
  await p.waitForTimeout(600)
  const y1 = await h1()
  check('телефон: меню проступает плавно, страница под ним не сдвигается', mid < 1 && y0 === y1, `прозрачность в начале ${mid}, заголовок ${y0} → ${y1}`)
  await p.mouse.click(195, 770)
  await p.waitForTimeout(600)
  check('телефон: касание мимо меню закрывает его', !(await p.locator('#mobile-menu').isVisible()))
  await p.evaluate(() => document.querySelector('footer').scrollIntoView({ behavior: 'instant' }))
  const group = p.locator('footer button[aria-expanded]').first()
  await group.tap()
  await p.waitForTimeout(150)
  const half = await p.evaluate((id) => document.getElementById(id).parentElement.getBoundingClientRect().height, await group.getAttribute('aria-controls'))
  await p.waitForTimeout(800)
  const full = await p.evaluate((id) => document.getElementById(id).parentElement.getBoundingClientRect().height, await group.getAttribute('aria-controls'))
  check('телефон: группа подвала раскрывается плавно', half > 0 && half < full - 1 && full > 40, `${Math.round(half)} → ${Math.round(full)}`)
  await ctx.close()
}

// Фотография, которая ещё грузится, проступает, а не возникает рывком
// (lib/fade.ts); пришедшая быстро — сразу. Кадр шапки
// страницы вида отдаётся с задержкой, как на медленной связи.
// Три пути (20.10.2026, fadeInFirstScreen):
// - первый заход: кадр шапки «проявляется» из-под гаснущего листа
//   (.hero-develop), и прятать его до загрузки нельзя — проявление и есть
//   плавное появление, а прятанье откладывало главную картинку;
// - кадр не успел к концу проявления (очень медленная сеть) — проступает сам;
// - пришли со своей страницы (проявления нет) — обычный fadeIn.
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  const slowImage = async (ms) => {
    await p.unroute(/\/img\//)
    await p.route(/\/img\/.*slide-survey/, async (route) => { await new Promise((r) => setTimeout(r, ms)); await route.continue().catch(() => {}) })
  }
  const state = () => p.locator('main img').first().evaluate((el) => ({ fade: el.dataset.fade, o: getComputedStyle(el).opacity, t: el.style.transition }))

  await slowImage(900)
  await p.goto(BASE + 'sro-izyskateley/', { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(300)
  const develop = await state()
  await p.waitForLoadState('networkidle')
  await p.waitForTimeout(300)
  const developed = await state()
  check('первый заход: кадр, который ещё грузится, не прячется под проявлением',
    develop.fade === 'develop' && develop.o === '1' && developed.o === '1', JSON.stringify({ develop, developed }))

  await slowImage(4200)
  await p.goto(BASE + 'sro-izyskateley/', { waitUntil: 'domcontentloaded' })
  await p.waitForLoadState('networkidle')
  await p.waitForTimeout(900)
  const late = await state()
  check('первый заход: кадр, опоздавший к концу проявления, проступает', late.fade === 'develop' && late.o === '1' && /opacity/.test(late.t), JSON.stringify(late))

  await slowImage(900)
  await p.goto(BASE + 'stati/', { waitUntil: 'networkidle' })
  await p.evaluate(() => { location.href = '../sro-izyskateley/' })
  await p.waitForURL(/sro-izyskateley/, { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(300)
  const before = await state()
  await p.waitForLoadState('networkidle')
  await p.waitForTimeout(900)
  const after = await state()
  check('со своей страницы: кадр, который ещё грузится, проступает плавно', before.fade === 'wait' && before.o === '0' && after.fade === 'done' && after.o === '1', JSON.stringify({ before, after }))
  const img = p.locator('main img').first()
  await p.unroute(/\/img\//)
  await p.reload({ waitUntil: 'networkidle' })
  await p.waitForTimeout(900)
  const again = await img.evaluate((el) => getComputedStyle(el).opacity)
  check('повторный заход: кадр виден', again === '1', again)
  // Обложка главной на телефоне: пока кадр грузится и проступает, под ним
  // графит, а не бумага — иначе обложка на миг светлела бы (вспышка).
  await p.goto(BASE, { waitUntil: 'domcontentloaded' })
  const under = await p.evaluate(() => {
    const box = document.querySelector('section[aria-labelledby="hero-title"] .lg\\:hidden picture')?.parentElement
    const [r, g, bl] = (box ? getComputedStyle(box).backgroundColor : '').match(/\d+/g)?.map(Number) ?? [255, 255, 255]
    return Math.round(0.2126 * r + 0.7152 * g + 0.0722 * bl)
  })
  check('обложка телефона: под кадром тёмный фон, без вспышки при загрузке', under < 60, String(under))
  await ctx.close()
}

// Почта в «Связаться» (01.10.2026, вечер): нажатие на адрес открывает
// почту (mailto), рядом значок копирования — слова «Скопировать» на экране
// нет, после нажатия на значок адрес лежит в буфере и видна бирка
// «Скопировано». На компьютере — щелчок, на телефоне — касание.
for (const [label, opts] of [
  ['компьютер', { viewport: { width: 1440, height: 900 } }],
  ['телефон', { viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true }],
]) {
  const ctx = await b.newContext({ ...opts, permissions: ['clipboard-read', 'clipboard-write'] })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  const link = p.locator('#contacts [data-email="link"]')
  const btn = p.locator('#contacts [data-copy="email"]')
  await link.scrollIntoViewIfNeeded()
  await p.waitForTimeout(500)
  const before = await p.evaluate(() => /Скопировать/.test(document.getElementById('contacts').innerText))
  check(`${label}: в «Связаться» нет слова «Скопировать»`, !before)
  const email = (await link.innerText()).trim()
  const href = await link.getAttribute('href')
  check(`${label}: адрес почты открывает почту`, /@/.test(email) && href === `mailto:${email}`, `${href}`)
  const box = await btn.boundingBox()
  // До сотых: при дробном положении блока браузер отдаёт 43,99997 вместо 44.
  const px = (v) => Math.round(v * 100) / 100
  check(`${label}: значок копирования не меньше 44 px`, box && px(box.width) >= 44 && px(box.height) >= 44, box ? `${box.width}×${box.height}` : 'нет')
  if (opts.isMobile) await btn.tap()
  else await btn.click()
  await p.waitForTimeout(600)
  const clip = await p.evaluate(() => navigator.clipboard.readText())
  check(`${label}: значок копирует почту`, clip === email, `в буфере «${clip}», на экране «${email}»`)
  const tag = await p.evaluate(() => {
    const el = [...document.querySelectorAll('#contacts span')].find((s) => s.textContent === 'Скопировано')
    return el ? Number(getComputedStyle(el).opacity) : -1
  })
  check(`${label}: после нажатия видно «Скопировано»`, tag > 0.9, String(tag))
  await ctx.close()
}

await b.close()
console.log(bad.join('\n'))
console.log(`\n${ok.length} ок, ${bad.length} не прошло`)
console.log(bad.length ? 'ЕСТЬ ПАДЕНИЯ' : 'САЙТ ЦЕЛИКОМ В ПОРЯДКЕ')
process.exit(bad.length ? 1 : 0)
