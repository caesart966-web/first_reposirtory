// Шрифты не только загружены, но и применены.
//
// Запуск:  npm test   (или node scripts/test-fonts.mjs [адрес сайта])
//
// Зачем. Шрифты на сайте разрезаны на кириллическую и латинскую части,
// и в латинской — не одна латиница: цифры, пробел, знаки препинания.
// Какое-то время заранее грузилась только кириллица, а латиница — «когда
// встретится». При font-display: optional браузер такой шрифт не берёт
// никогда: он загружался (в списке шрифтов страницы значился «loaded»),
// но телефон, суммы, «WhatsApp» и «Telegram» рисовались запасным
// Helvetica/Arial. Ни одна проверка этого не видела, увидел заказчик —
// на нижней панели связи (её потом сменили значки без подписей)
// «Позвонить» было одним шрифтом, а «WhatsApp» другим.
//
// Поэтому здесь спрашивается не «загружен ли файл», а каким шрифтом
// браузер на самом деле нарисовал текст (CSS.getPlatformFontsForNode).
// Страница открывается в чистом контексте, без кеша — как у посетителя,
// который пришёл впервые.

import { chromium } from './lib/browser.mjs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'

// Что проверяем. Суммы со знаком «₽» — отдельными пунктами: знака нет
// ни в латинской, ни в кириллической части, он лежит в своих файлах
// (golos-rub, literata-rub), и до 27.09.2026 рисовался системным шрифтом.
const CASES = [
  { path: '/', sel: '.apply-direct a', font: 'Golos Text', what: 'телефон и «WhatsApp», «Telegram», «MAX» под формой' },
  { path: '/', sel: '.apply-direct .ad-phone', font: 'Golos Text', what: 'телефон под формой заявки' },
  { path: '/', sel: '.hero .page-title', font: 'Literata', what: 'заголовок первого экрана (пробелы — из латинской части)' },
  { path: '/', sel: '.steps4 .s4-num', font: 'Literata', what: 'номера шагов' },
  { path: '/kontakty/', sel: '.k-phone', font: 'Golos Text', what: 'номер телефона на «Контактах»' },
  { path: '/', sel: '.ho-list dd', font: 'Golos Text', what: 'условия на первом экране — цифры и «₽»' },
  // «₽» в антикве. Здесь стояли суммы первого года на главной (.pt-sum) —
  // блок убран 28.09.2026, и ближайшие цифры с «₽» антиквой — в шапке услуги.
  { path: '/uslugi/sro-stroiteley/', sel: '.fv', font: 'Literata', what: 'цифры в шапке услуги — «₽» в антикве' },
]

let problems = 0
const ok = (m) => console.log(`  ✓ ${m}`)
const fail = (m) => { console.log(`  ✗ ${m}`); problems++ }

console.log('\nШрифты применены, а не только загружены\n')

// Предзагрузка всех четырёх прямых начертаний — отдельным требованием.
// Замер шрифта по отрисовке ловит поломку не всегда: без предзагрузки
// латиница Literata иногда успевает к первой отрисовке, иногда нет, —
// гонка. А разметку можно проверить без гонок.
{
  const html = await (await fetch(BASE + '/')).text()
  const preloaded = [...html.matchAll(/<link[^>]+rel="preload"[^>]+as="font"[^>]*>/g)]
    .map((m) => (m[0].match(/href="([^"]+)"/) || [])[1] || '')
  for (const file of ['golos-cyrillic', 'golos-latin', 'golos-rub', 'literata-cyrillic', 'literata-latin', 'literata-rub']) {
    if (preloaded.some((h) => h.endsWith(`/fonts/${file}.woff2`))) ok(`${file}.woff2 загружается заранее`)
    else fail(`${file}.woff2 не загружается заранее — при font-display: optional браузер его не применит`)
  }
}

const browser = await chromium.launch()
const byPath = Map.groupBy(CASES, (c) => c.path)

for (const [path, cases] of byPath) {
  // Телефонная ширина: нижняя панель связи есть только на ней.
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } })
  const page = await ctx.newPage()
  const cdp = await ctx.newCDPSession(page)
  await cdp.send('Network.enable')
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
  await page.goto(BASE + path, { waitUntil: 'networkidle' })
  await cdp.send('DOM.enable')
  await cdp.send('CSS.enable')
  const { root } = await cdp.send('DOM.getDocument', { depth: -1 })

  for (const c of cases) {
    const { nodeIds } = await cdp.send('DOM.querySelectorAll', { nodeId: root.nodeId, selector: c.sel })
    if (!nodeIds.length) { fail(`${path} — не нашлось «${c.sel}» (${c.what})`); continue }
    const wrong = []
    for (const nodeId of nodeIds) {
      const { fonts } = await cdp.send('CSS.getPlatformFontsForNode', { nodeId })
      const other = fonts.filter((f) => f.familyName !== c.font && f.glyphCount > 0)
      if (other.length) wrong.push(other.map((f) => `${f.familyName} (${f.glyphCount} зн.)`).join(', '))
    }
    if (wrong.length) fail(`${path} — ${c.what}: кроме ${c.font} нарисовано шрифтом ${wrong[0]}`)
    else ok(`${path} — ${c.what}: ${c.font}${nodeIds.length > 1 ? `, все ${nodeIds.length}` : ''}`)
  }
  await ctx.close()
}

await browser.close()
console.log(problems
  ? `\n✗ Проверка не прошла: ${problems}. Если латиница рисуется запасным шрифтом — проверьте предзагрузку\n  латинских файлов в Base.astro: при font-display: optional без неё шрифт не применяется.\n`
  : '\n✓ Цифры, латиница и пробелы нарисованы фирменными шрифтами.\n')
process.exit(problems ? 1 : 0)
