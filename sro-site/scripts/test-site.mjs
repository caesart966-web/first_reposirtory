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
const WIDTHS = [320, 390, 768, 1024, 1440]

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
        // Шрифт заголовков действительно загрузился, а не подменился Georgia.
        displayFont: document.fonts.check('500 40px "Brygada 1918 Variable"', 'Вступление'),
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
    check(`${tag}: шрифт заголовков загружен`, r.displayFont)
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

await b.close()
console.log(bad.join('\n'))
console.log(`\n${ok.length} ок, ${bad.length} не прошло`)
console.log(bad.length ? 'ЕСТЬ ПАДЕНИЯ' : 'САЙТ ЦЕЛИКОМ В ПОРЯДКЕ')
process.exit(bad.length ? 1 : 0)
