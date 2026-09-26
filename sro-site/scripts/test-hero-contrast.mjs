// Контраст надписей поверх фотографий — замером пикселей, а не на глаз.
//
// Для каждой надписи (заголовок h1 и всё, что помечено [data-hero-text]):
// её цвет и прямоугольник; затем все
// надписи прячутся, экран снимается без них, и под каждой ищется худший
// (самый близкий к ней по яркости) пиксель фона. Норма — 4,5:1 для любой
// надписи, в том числе крупной: запас на смену кадров.
//
// Меряются первый экран главной (с 26.09.2026 кадр растворяется в бумаге
// и заходит под текст — замер и есть та проверка, что под буквами он
// прозрачен), шапки страниц видов СРО и услуги «Подготовка документов»
// (у неё в шапке папки), раздел «О нас» с фотографией Фемиды и раздел
// «Документы» с фотографией папок (подпись, заголовок и абзац ложатся
// на растворённый край кадра) на 1440, 1024, 820 и 390 px.
// Первая версия плёнки давала 1,2:1 — кадры дневные, белая подпись ложилась
// на небо; статический расчёт по стилям этого не видит принципиально.
//
//   node scripts/test-hero-contrast.mjs     # BASE, PLAYWRIGHT, CHROMIUM — как в test-site.mjs
const pw = await import(process.env.PLAYWRIGHT || 'playwright-core')
const { chromium } = pw.default ?? pw

const BASE = process.env.BASE || 'http://localhost:4181/'
const NORM = 4.5
const SHOTS = [
  { path: '' },
  { path: 'sro-stroiteley/' }, { path: 'sro-proektirovshchikov/' }, { path: 'sro-izyskateley/' }, { path: 'uslugi/nok/' },
  { path: 'uslugi/dokumenty/' },
  { path: '', section: 'about', selector: '#about h2, #about p, #about li span:last-child' },
  { path: '', section: 'documents', selector: '#documents h2, #documents p' },
]
const DEVICES = [
  ['1440', { width: 1440, height: 900 }, false],
  ['1024', { width: 1024, height: 900 }, false],
  ['820', { width: 820, height: 1180 }, true],
  ['390', { width: 390, height: 844 }, true],
]

const b = await chromium.launch({ executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium' })
// Отдельная страница-вычислитель: снимок разбирается в canvas, пиксели
// читаются getImageData — так проверка не тянет за собой ни Python, ни пакетов.
const calc = await b.newPage()
await calc.setContent('<canvas id="c"></canvas>')

const rows = []
for (const [dev, vp, mob] of DEVICES) {
  for (const s of SHOTS) {
    const ctx = await b.newContext({ viewport: vp, hasTouch: mob, isMobile: mob, reducedMotion: 'reduce', deviceScaleFactor: 1 })
    const p = await ctx.newPage()
    await p.goto(BASE + s.path, { waitUntil: 'networkidle' })
    const selector = s.selector || 'h1, [data-hero-text]'
    if (s.section) {
      // Шапка и нижняя панель — поверх раздела, их прячем и в обоих снимках:
      // иначе под надписью оказалась бы шапка, а не фотография.
      await p.addStyleTag({ content: 'header, nav[aria-label="Быстрая связь"]{visibility:hidden !important}' })
      await p.evaluate((id) => document.getElementById(id).scrollIntoView({ behavior: 'instant' }), s.section)
    }
    await p.evaluate(() => document.fonts.ready)
    await p.waitForTimeout(900)
    // Меряется не прямоугольник элемента, а строки самого текста (прямоугольники
    // диапазона): абзац-блок тянется на всю ширину колонки, и его правый край
    // ложился на мраморную статую там, где букв нет, — замер давал 1:1.
    const boxes = await p.$$eval(selector, (els) => els
      .filter((e) => e.getClientRects().length && e.textContent.trim())
      .flatMap((e) => {
        const range = document.createRange()
        range.selectNodeContents(e)
        const color = getComputedStyle(e).color
        const text = e.textContent.trim().slice(0, 32)
        return [...range.getClientRects()]
          .filter((r) => r.width > 2 && r.height > 2)
          .map((r) => ({ text, x: r.x, y: r.y, w: r.width, h: r.height, color }))
      })
      .filter((x) => x.y < innerHeight && x.y + x.h > 0))
    await p.addStyleTag({ content: `${selector}{visibility:hidden !important}` })
    await p.waitForTimeout(200)
    const png = (await p.screenshot()).toString('base64')
    await ctx.close()

    const worst = await calc.evaluate(async ({ png, boxes }) => {
      const img = new Image()
      img.src = 'data:image/png;base64,' + png
      await img.decode()
      const c = document.getElementById('c')
      c.width = img.width
      c.height = img.height
      const g = c.getContext('2d', { willReadFrequently: true })
      g.drawImage(img, 0, 0)
      const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 }
      const lum = (r, gg, bb) => 0.2126 * lin(r) + 0.7152 * lin(gg) + 0.0722 * lin(bb)
      return boxes.map((bx) => {
        const [tr, tg, tb] = bx.color.match(/\d+/g).map(Number)
        const tl = lum(tr, tg, tb)
        const x0 = Math.max(0, Math.floor(bx.x)), y0 = Math.max(0, Math.floor(bx.y))
        const w = Math.min(img.width - x0, Math.ceil(bx.w)), h = Math.min(img.height - y0, Math.ceil(bx.h))
        if (w <= 0 || h <= 0) return { ...bx, worst: Infinity }
        const d = g.getImageData(x0, y0, w, h).data
        let min = Infinity
        for (let i = 0; i < d.length; i += 4) {
          const bl = lum(d[i], d[i + 1], d[i + 2])
          const cr = (Math.max(tl, bl) + 0.05) / (Math.min(tl, bl) + 0.05)
          if (cr < min) min = cr
        }
        return { text: bx.text, worst: min }
      })
    }, { png, boxes })
    const name = `${s.path || '/'}${s.section ? ` #${s.section}` : ''} @${dev}`
    // Надпись в несколько строк даёт несколько прямоугольников — в отчёт идёт худший.
    const byText = new Map()
    for (const r of worst) if (!byText.has(r.text) || r.worst < byText.get(r.text).worst) byText.set(r.text, r)
    for (const r of byText.values()) rows.push({ name, ...r })
  }
}
await b.close()

rows.sort((a, b) => a.worst - b.worst)
const bad = rows.filter((r) => r.worst < NORM)
for (const r of rows.slice(0, 8)) console.log(`${r.worst.toFixed(2)}:1  ${r.worst < NORM ? 'FAIL' : 'ok  '}  ${r.name}  «${r.text}»`)
console.log(`\nзамеров: ${rows.length}, ниже ${NORM}:1 — ${bad.length}`)
for (const r of bad) console.log(`FAIL: ${r.name} «${r.text}» — ${r.worst.toFixed(2)}:1`)
console.log(bad.length ? 'КОНТРАСТ НИЖЕ НОРМЫ' : 'КОНТРАСТ НАДПИСЕЙ НА ФОТОГРАФИЯХ В НОРМЕ')
process.exit(bad.length ? 1 : 0)
