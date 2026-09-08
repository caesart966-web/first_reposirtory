// Проверяет таблицы на всех страницах сайта.
//
// Зачем отдельная проверка. Таблиц на сайте девять, и живут они по-разному:
// на страницах услуг и стоимости они написаны руками, в статьях базы знаний
// приходят из markdown. Проверка ширин (test-widths.mjs) их не ловит:
// таблица в контейнере с горизонтальной прокруткой не тянет страницу вбок,
// формально всё в порядке — а на телефоне правую половину таблицы просто
// не видно, и ничто не сообщает, что её надо листать.
//
// Что проверяем на каждой таблице и каждой ширине:
//   · не шире экрана;
//   · не требует горизонтальной прокрутки внутри своего контейнера;
//   · текст не вылезает из ячеек;
//   · ячейки не наезжают друг на друга.
//
// Скрытые элементы в замер не берём: шапка таблицы на телефоне спрятана
// приёмом «видно только голосом» — она сохраняет размеры и лежит поверх
// первой строки, и без этой оговорки проверка ругалась бы всегда.
//
// Запуск: node scripts/test-tables.mjs [адрес]
import { chromium } from 'playwright'
import { readFileSync } from 'fs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const WIDTHS = [390, 768, 1280]

const sitemap = readFileSync('dist/sitemap-0.xml', 'utf8')
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => new URL(m[1]).pathname)

const browser = await chromium.launch()
let checked = 0
let failed = 0

for (const width of WIDTHS) {
  const page = await browser.newPage({ viewport: { width, height: 900 } })
  for (const url of urls) {
    await page.goto(BASE + url, { waitUntil: 'domcontentloaded' })
    const found = await page.evaluate((vw) => {
      // Видимой считаем ячейку, которая действительно отдаётся в точке
      // своего центра: спрятанная шапка сохраняет размеры, но там её нет.
      //
      // Одной этой проверки не хватило. Шапка прячется приёмом «видно только
      // голосом»: сама она сжата до 1×1 с clip и overflow, а ячейки внутри
      // сохраняют настоящие размеры и торчат наружу. Если в точке центра
      // такой ячейки сверху оказывается общий предок (сама таблица),
      // то hit.contains(el) верно — и ячейка засчитывалась видимой.
      // Ветка hit.contains(el) нужна для пустых ячеек, где в центре нет
      // ни текста, ни фона, поэтому убирать её нельзя. Вместо этого
      // отдельно отсекаем всё, что лежит внутри спрятанного контейнера.
      const inClipped = (el) => {
        for (let n = el.parentElement; n; n = n.parentElement) {
          const cs = getComputedStyle(n)
          if (cs.clip === 'rect(0px, 0px, 0px, 0px)') return true
          const r = n.getBoundingClientRect()
          if (cs.overflow === 'hidden' && r.width <= 1 && r.height <= 1) return true
        }
        return false
      }
      const visible = (el) => {
        const r = el.getBoundingClientRect()
        if (r.width < 3 || r.height < 3) return false
        if (inClipped(el)) return false
        const hit = document.elementFromPoint(r.left + r.width / 2, Math.min(r.top + r.height / 2, innerHeight - 1))
        return !!hit && (hit === el || el.contains(hit) || hit.contains(el))
      }
      const out = []
      document.querySelectorAll('table').forEach((t) => {
        const box = t.getBoundingClientRect()
        if (!box.height) return
        t.scrollIntoView({ block: 'center' })
        const rect = t.getBoundingClientRect()
        const wrap = t.parentElement
        const cells = [...t.querySelectorAll('td, th')].filter(visible)
        const spill = cells.filter((c) => c.scrollWidth > c.clientWidth + 1).map((c) => c.textContent.trim().slice(0, 24))
        let overlap = 0
        for (const c of cells) {
          const a = c.getBoundingClientRect()
          for (const o of cells) {
            if (o === c) continue
            const q = o.getBoundingClientRect()
            if (a.left < q.right - 2 && a.right > q.left + 2 && a.top < q.bottom - 2 && a.bottom > q.top + 2) overlap++
          }
        }
        out.push({
          wide: rect.width > vw + 1,
          scroll: wrap ? wrap.scrollWidth > wrap.clientWidth + 1 : false,
          spill,
          overlap,
          w: Math.round(rect.width),
        })
      })
      return out
    }, width)

    for (const t of found) {
      checked++
      const problems = []
      if (t.wide) problems.push(`шире экрана (${t.w} px)`)
      if (t.scroll) problems.push('требует прокрутки вбок')
      if (t.spill.length) problems.push(`текст вылезает из ячеек: ${t.spill.join(', ')}`)
      if (t.overlap) problems.push(`ячейки наезжают друг на друга (${t.overlap})`)
      if (problems.length) {
        failed++
        console.log(`✗ ${String(width).padEnd(5)} ${url.padEnd(40)} ${problems.join('; ')}`)
      }
    }
  }
  await page.close()
}
await browser.close()

if (failed) {
  console.log(`\nОШИБОК: ${failed} из ${checked}. Таблицы ломаются.`)
  console.log('Что делать: на узком экране таблица должна разворачиваться')
  console.log('в карточки — см. @media (max-width: 599px) у table.data')
  console.log('в src/styles/global.css. Каждой ячейке нужен data-label.')
  process.exit(1)
}
console.log(`✓ Таблицы в порядке: ${checked} замеров на ${WIDTHS.length} ширинах.`)
