// Сквозная проверка сайта: все одиннадцать страниц на пяти ширинах, плюс
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
const pw = await import(process.env.PLAYWRIGHT || 'playwright-core')
const { chromium } = pw.default ?? pw

const BASE = process.env.BASE || 'http://localhost:4181/'
const PAGES = ['', 'sro-stroiteley/', 'sro-proektirovshchikov/', 'sro-izyskateley/',
  'uslugi/vstuplenie-v-sro/', 'uslugi/podbor-i-proverka-sro/', 'uslugi/dokumenty/',
  'uslugi/specialisty-nrs/', 'uslugi/nok/', 'uslugi/uroven-otvetstvennosti/',
  'uslugi/soprovozhdenie-proverok/']
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

// Первый экран главной: три вида СРО списком, кадр справа.
//
// Главное, что здесь стережётся, — что видно БЕЗ прокрутки: заголовок,
// обе кнопки и все три вида. До 26.09.2026 тут стоял слайдер, и в каждый
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
  const links = [...hero.querySelectorAll('#hero-types + ul a')]
  const buttons = [...hero.querySelectorAll('a[href="#contacts"], a[href^="tel:"]')]
  const photo = hero.querySelector('img')
  return {
    hrefs: links.map((a) => a.getAttribute('href')),
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
// он срабатывает и что новая страница в момент показа уже собрана: корень
// у страниц заполняет скрипт, и без blocking="render" у него (плагин
// в vite.config.ts) и синхронной первой отрисовки (flushSync в main.tsx,
// detail.tsx, service.tsx) переход «проявлял» бы пустой лист. При «уменьшить
// движение» перехода нет вовсе.
for (const motion of ['no-preference', 'reduce']) {
  const ctx = await b.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: motion })
  await ctx.addInitScript(() => {
    addEventListener('pagereveal', (e) => {
      window.__vt = Boolean(e.viewTransition)
      window.__rootEmpty = !document.getElementById('root')?.children.length
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
  const [vt, empty] = await p.evaluate(() => [window.__vt, window.__rootEmpty])
  if (motion === 'reduce') {
    check('переход между страницами: при «уменьшить движение» его нет', vt === false, String(vt))
  } else {
    check('переход между страницами: срабатывает', vt === true, String(vt))
    check('переход между страницами: новая страница в момент показа не пустая', empty === false, String(empty))
  }
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
  check(`телефон ${width} × ${height}: обе кнопки связи видны без прокрутки`, g.buttons === 2 && g.buttonsBottom <= height, `низ кнопок ${g.buttonsBottom}`)
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
  await p.evaluate(() => scrollTo({ top: 2000, behavior: 'instant' }))
  await p.waitForTimeout(700)
  check('телефон: нижняя панель появилась после прокрутки', (await bar.getAttribute('aria-hidden')) === 'false')
  // У «Связаться» панель уходит: там те же номер и мессенджеры крупно.
  await p.evaluate(() => document.getElementById('contacts').scrollIntoView({ block: 'start', behavior: 'instant' }))
  await p.waitForTimeout(700)
  check('телефон: у «Связаться» нижняя панель уходит', (await bar.getAttribute('aria-hidden')) === 'true')
  await p.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }))
  await p.locator('header button[aria-label="Открыть меню"]').click()
  await p.waitForTimeout(600)
  const menuLinks = await p.locator('nav[aria-label="Мобильная навигация"] a:visible').count()
  check('телефон: меню открывается', menuLinks > 5, String(menuLinks))
  await p.locator('header a:visible', { hasText: 'Связаться' }).last().click()
  await p.waitForTimeout(1500)
  const top = await p.evaluate(() => document.getElementById('contacts').getBoundingClientRect().top)
  check('телефон: «Связаться» из меню приводит к контактам', Math.abs(top) < 200, String(Math.round(top)))
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
  check(`${label}: значок копирования не меньше 44 px`, box && box.width >= 44 && box.height >= 44, box ? `${box.width}×${box.height}` : 'нет')
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
