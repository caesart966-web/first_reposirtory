// Сквозная проверка сайта: все одиннадцать страниц на пяти ширинах, плюс
// слайдер первого экрана, меню и нижняя панель на телефоне.
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

// Слайдер первого экрана.
{
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  const hero = p.locator('section[aria-roledescription="слайдер"]')
  const pressed = () => hero.locator('button[aria-pressed="true"]').getAttribute('aria-label')
  check('слайдер: стартует с первого вида', (await pressed()) === 'СРО строителей', await pressed())
  await p.waitForTimeout(7600)
  check('слайдер: сам переходит ко второму через ~7 с', (await pressed()) === 'СРО проектировщиков', await pressed())
  await hero.locator('button[aria-label="СРО изыскателей"]').click()
  await p.waitForTimeout(300)
  check('слайдер: вкладка переключает слайд', (await pressed()) === 'СРО изыскателей', await pressed())
  check('слайдер: при наведении на вкладки — пауза', /progress-paused/.test(await hero.getAttribute('class')))
  await p.waitForTimeout(8000)
  check('слайдер: на паузе не уезжает', (await pressed()) === 'СРО изыскателей', await pressed())
  await p.mouse.move(700, 150)
  check('слайдер: увёл мышь — пауза снята', !/progress-paused/.test(await hero.getAttribute('class')))
  const links = await hero.locator('a[href*="sro-"]').evaluateAll((els) => els.map((a) => a.getAttribute('href')))
  check('слайдер: у каждого вида ссылка на свою страницу', ['sro-stroiteley/', 'sro-proektirovshchikov/', 'sro-izyskateley/'].every((x) => links.some((l) => l.endsWith(x))), links.join(' '))
  await ctx.close()

  // prefers-reduced-motion: автосмены нет, всё видно сразу.
  const rctx = await b.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' })
  const rp = await rctx.newPage()
  await rp.goto(BASE, { waitUntil: 'networkidle' })
  await rp.waitForTimeout(8000)
  const rh = rp.locator('section[aria-roledescription="слайдер"]')
  check('reduced motion: слайдер не листается сам', (await rh.locator('button[aria-pressed="true"]').getAttribute('aria-label')) === 'СРО строителей')
  const hidden = await rp.evaluate(() => [...document.querySelectorAll('.reveal')].filter((e) => getComputedStyle(e).opacity !== '1').length)
  check('reduced motion: все блоки видны без прокрутки', hidden === 0, String(hidden))
  await rctx.close()
}

// Телефон: слайдер, меню, нижняя панель.
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  await p.goto(BASE, { waitUntil: 'networkidle' })
  const tabs = await p.locator('section[aria-roledescription="слайдер"] button[aria-pressed]').evaluateAll((els) =>
    els.map((e) => { const r = e.getBoundingClientRect(); return [r.left, r.right, r.height] }))
  const overlapTabs = tabs.some((t, i) => i && t[0] < tabs[i - 1][1] - 1)
  check('телефон: вкладки слайдера не наезжают', !overlapTabs, JSON.stringify(tabs))
  check('телефон: вкладки не ниже 44px', tabs.every((t) => t[2] >= 44), tabs.map((t) => Math.round(t[2])).join(','))
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
