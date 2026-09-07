// Технический аудит: настоящие метрики загрузки, а не ощущения.
//
// Что меряет: вес переданного по сети, время до первой отрисовки и до
// самого крупного элемента (LCP), сдвиг вёрстки при загрузке (CLS),
// ошибки в консоли и число блокирующих отрисовку файлов.
//
// Запуск: node scripts/audit.mjs [адрес]
import { chromium } from 'playwright'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const PAGES = ['/', '/stoimost/', '/uslugi/nrs/', '/kontakty/', '/baza-znaniy/porog-10-mln/']
const SCREENS = [
  ['компьютер', 1280, 900],
  ['телефон', 390, 844],
]

const browser = await chromium.launch()
const rows = []
const errors = []

for (const [screen, width, height] of SCREENS) {
  for (const url of PAGES) {
    const ctx = await browser.newContext({ viewport: { width, height } })
    const page = await ctx.newPage()
    let bytes = 0
    const byType = {}
    page.on('response', async (r) => {
      try {
        const h = await r.allHeaders()
        const n = Number(h['content-length'] || 0)
        bytes += n
        const t = (h['content-type'] || '').split(';')[0]
        byType[t] = (byType[t] || 0) + n
      } catch {}
    })
    page.on('console', (m) => { if (m.type() === 'error') errors.push(`${url} ${screen}: ${m.text()}`) })
    page.on('pageerror', (e) => errors.push(`${url} ${screen}: ${e.message}`))

    // LCP отдаётся только наблюдателю: getEntriesByType после загрузки
    // возвращает пусто. Наблюдатель ставится ДО перехода на страницу.
    await page.addInitScript(() => {
      window.__lcp = 0
      new PerformanceObserver((l) => {
        for (const e of l.getEntries()) window.__lcp = e.startTime
      }).observe({ type: 'largest-contentful-paint', buffered: true })
    })
    await page.goto(BASE + url, { waitUntil: 'networkidle' })

    // Прокручиваем как человек — шагами по трети экрана — и считаем кадры.
    // Разом до низа браузер долистывает одним движением, и рывки, которые
    // чувствуются при обычной прокрутке, в такой замер не попадают.
    const frames = await page.evaluate(async () => {
      const times = []
      let stop = false
      const tick = (t) => { times.push(t); if (!stop) requestAnimationFrame(tick) }
      requestAnimationFrame(tick)
      const step = Math.round(window.innerHeight / 3)
      for (let y = 0; y < document.body.scrollHeight; y += step) {
        window.scrollTo(0, y)
        await new Promise((r) => setTimeout(r, 60))
      }
      stop = true
      await new Promise((r) => setTimeout(r, 120))
      // Кадр пропущен, если от предыдущего прошло больше полутора обычных
      // кадров: 24 мс при 60 Гц.
      let dropped = 0
      for (let i = 1; i < times.length; i++) if (times[i] - times[i - 1] > 24) dropped++
      return { total: times.length, dropped }
    })
    await page.evaluate(() => window.scrollTo(0, 0))
    await page.waitForTimeout(400)

    const m = await page.evaluate(() => {
      const nav = performance.getEntriesByType('navigation')[0]
      const paint = Object.fromEntries(performance.getEntriesByType('paint').map((p) => [p.name, p.startTime]))
      const shifts = performance.getEntriesByType('layout-shift') || []
      const cls = shifts.filter((s) => !s.hadRecentInput).reduce((a, s) => a + s.value, 0)
      const blocking = [...document.querySelectorAll('link[rel=stylesheet]')].length
      return {
        dcl: Math.round(nav.domContentLoadedEventEnd),
        fcp: Math.round(paint['first-contentful-paint'] || 0),
        lcp: Math.round(window.__lcp || 0),
        cls: Number(cls.toFixed(4)),
        blocking,
        nodes: document.querySelectorAll('*').length,
      }
    })
    rows.push({ screen, url, kb: Math.round(bytes / 1024), ...m, ...frames })
    await ctx.close()
  }
}
await browser.close()

const pad = (v, n) => String(v).padEnd(n)
console.log(
  pad('экран', 11) + pad('страница', 30) + pad('вес', 8) + pad('FCP', 8) +
  pad('LCP', 8) + pad('CLS', 7) + pad('кадров', 8) + pad('рывков', 8) + 'узлов',
)
for (const r of rows) {
  console.log(
    pad(r.screen, 11) + pad(r.url, 30) + pad(r.kb + ' КБ', 8) +
    pad(r.fcp + ' мс', 8) + pad(r.lcp + ' мс', 8) + pad(r.cls, 7) +
    pad(r.total, 8) + pad(r.dropped, 8) + r.nodes,
  )
}
console.log()
if (errors.length) {
  console.log('ОШИБКИ В КОНСОЛИ:')
  for (const e of [...new Set(errors)]) console.log('  ✗ ' + e)
} else {
  console.log('✓ Ошибок в консоли нет')
}
const worstCls = Math.max(...rows.map((r) => r.cls))
const worstLcp = Math.max(...rows.map((r) => r.lcp))
const worstDrop = Math.max(...rows.map((r) => r.dropped))
console.log(
  `\nХудший CLS ${worstCls} (норма до 0.1), худший LCP ${worstLcp} мс (норма до 2500), ` +
  `рывков при прокрутке не больше ${worstDrop}`,
)
