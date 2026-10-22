// Картинка для мессенджеров (og:image), 1200×630.
//
// Собирается из фирменных элементов сайта, а не рисуется отдельно: тот же
// знак весов из illustrations.tsx, тот же тёплый графит accent-950, что у
// раздела «Связаться», те же шрифты — Brygada 1918 в имени, Onest в тексте.
// Фотографий нет намеренно — карточка в мессенджере показывается размером
// с ноготь, и любой кадр там превращается в кашу, а знак и имя читаются.
//
// С 24.09.2026 — в новой палитре: графит и латунь вместо синего. Сетка
// чертежа и синее свечение сняты вместе с прежним оформлением.
//
// Playwright в зависимостях сайта не нужен: картинка пересобирается редко,
// а тащить браузер в прод-сборку ради неё незачем. Скрипт берёт модуль из
// переменной окружения, если он лежит не рядом:
//
//   npx playwright-core --version           # если модуль уже есть
//   node scripts/build-og.mjs
//   PLAYWRIGHT=/путь/к/node_modules/playwright-core node scripts/build-og.mjs
//
// Кладёт public/og.png — картинку главной и запасную для всех страниц.
//
// С 22.10.2026 у остальных страниц своя картинка, public/og/<адрес>.jpg
// (разбор удобства: когда ссылку на услугу или статью пересылают клиенту,
// по картинке сразу видно, о чём она). Тот же вид — графит, весы, имя
// компании, — а вместо «Вступление в СРО под ключ» заголовок страницы
// и строка под ним. Текст берётся из ГОТОВОЙ страницы (dist, <h1> и первая
// строка шапки), а не пишется здесь: так картинка не разойдётся со
// страницей. Поэтому сначала сборка, потом картинки, потом сборка ещё раз:
//
//   npm run build && node scripts/build-og.mjs --pages && npm run articles && npm run build
//
// --pages — только картинки страниц, og.png не пересобирается (главную
// картинку заказчик видел и одобрил, лишний раз её не трогаем).
// JPEG, а не PNG: на тексте и мягком свете разницы не видно, а вес втрое
// меньше — 14 картинок едут в каждом архиве.
const pw = await import(process.env.PLAYWRIGHT || 'playwright-core')
const { chromium } = pw.default ?? pw
import { existsSync, mkdirSync, readdirSync, readFileSync } from 'node:fs'
import { ogName } from './og-name.mjs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const OUT = resolve(root, 'public/og.png')

// Шрифты сайта берём из node_modules, а не из сети: среда сборки может быть
// без интернета, и тогда картинка молча уехала бы системным шрифтом — на глаз
// почти незаметно, а фирменный вид уже не тот.
const face = (family, pkg, file) =>
  `@font-face{font-family:${family};font-style:normal;font-weight:100 900;src:url(data:font/woff2;base64,` +
  readFileSync(resolve(root, `node_modules/@fontsource-variable/${pkg}/files/${file}`)).toString('base64') +
  `) format('woff2-variations')}`

// Знак — те же координаты, что в ScalesMark (весы под фронтоном).
const SCALES = `<svg viewBox="-1 2 50 37.4" fill="#C09A68" stroke="#C09A68"
  stroke-linecap="round" stroke-linejoin="round" style="width:104px;height:auto">
  <path d="M3.2 12.6 24 3.6l20.8 9Z" fill="none" stroke-width="2"/>
  <path d="M24 12.6v20" fill="none" stroke-width="2.2"/>
  <path d="M5.2 13.4.6 25.2m4.6-11.8 4.6 11.8m33-11.8-4.6 11.8m4.6-11.8 4.6 11.8" fill="none" stroke-width="1.2"/>
  <path d="M-.4 25.2h11.2q-5.6 7.2-11.2 0Zm37.6 0h11.2q-5.6 7.2-11.2 0Z" stroke="none"/>
  <path d="M20.4 32.4h7.2l2.2 4.2H18.2Z" stroke="none"/>
  <path d="M16.2 37.9h15.6" fill="none" stroke-width="1.5"/></svg>`

const html = `<!doctype html><html lang="ru"><head><meta charset="utf-8">
<style>
  ${face('Onest', 'onest', 'onest-cyrillic-wght-normal.woff2')}
  ${face('Onest', 'onest', 'onest-latin-wght-normal.woff2')}
  ${face('Brygada', 'brygada-1918', 'brygada-1918-cyrillic-wght-normal.woff2')}
  ${face('Brygada', 'brygada-1918', 'brygada-1918-latin-wght-normal.woff2')}
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:1200px;height:630px;background:#1C1815;overflow:hidden;
    font-family:Onest,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
  /* Мягкий тёплый свет из правого верхнего угла — как на тёмных разделах
     сайта: плоский графит в ленте мессенджера читается провалом. */
  .light{position:absolute;right:-180px;top:-220px;width:720px;height:720px;border-radius:50%;
    background:radial-gradient(circle,#9D744333 0%,#9D744300 70%)}
  .wrap{position:relative;height:100%;display:flex;flex-direction:column;
    justify-content:center;padding:0 90px}
  .eyebrow{margin-top:44px;display:flex;align-items:center;gap:16px;font-size:24px;color:#D6CDC1}
  .eyebrow i{display:block;width:44px;height:1px;background:#C09A68}
  .name{margin-top:18px;font-family:Brygada,Georgia,serif;font-size:84px;font-weight:500;
    line-height:1;color:#FBF9F5;letter-spacing:-.01em;font-variant-numeric:lining-nums}
  .lead{margin-top:30px;font-size:27px;line-height:1.4;color:#D6CDC1;max-width:920px}
  .tags{margin-top:40px;padding-top:26px;border-top:1px solid #FFFFFF26;
    font-size:22px;color:#A79D91;letter-spacing:.01em}
</style></head><body>
  <div class="light"></div>
  <div class="wrap">
    ${SCALES}
    <div class="eyebrow"><i></i>ООО «БИЗНЕС-ГРУПП»</div>
    <div class="name">Вступление в&nbsp;СРО<br>под&nbsp;ключ</div>
    <div class="lead">Строители, проектировщики, изыскатели. Подбор СРО, подготовка
      документов, специалисты НРС — до внесения в реестр членов.</div>
    <div class="tags">СРО · НРС · НОК · Документы · Сопровождение</div>
  </div>
</body></html>`

const PAGES_ONLY = process.argv.includes('--pages')
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium' })
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 })
if (!PAGES_ONLY) {
  await page.setContent(html, { waitUntil: 'load' })
  // Шрифт может не приехать (сеть закрыта) — тогда рисуем системным, но ждём попытку.
  await page.evaluate(() => document.fonts.ready).catch(() => {})
  await page.waitForTimeout(600)
  await page.screenshot({ path: OUT, type: 'png' })
  console.log('og.png готов:', OUT)
}

// ——— Картинки страниц ————————————————————————————————————————————————
const DIST = resolve(root, 'dist')
const OG_DIR = resolve(root, 'public/og')
if (!existsSync(resolve(DIST, 'index.html'))) throw new Error('Нет dist: сначала npm run build — текст картинок берётся из готовых страниц')
mkdirSync(OG_DIR, { recursive: true })

const textOf = (fragment) =>
  fragment
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;|&#160;/g, '\u00a0')
    .replace(/&quot;/g, '"')
    .replace(/&laquo;/g, '«')
    .replace(/&raquo;/g, '»')
    .replace(/&amp;/g, '&')
    .replace(/[ \t\n]+/g, ' ')
    .trim()
const escHtml = (text) => text.replace(/&/g, '&amp;').replace(/</g, '&lt;')

// Все страницы, кроме главной (у неё og.png) и 404.
const pages = []
const walk = (dir, rel) => {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isDirectory() || ['assets', 'img', 'og', 'fonts'].includes(entry.name)) continue
    const at = resolve(dir, entry.name)
    if (existsSync(resolve(at, 'index.html'))) pages.push(`${rel}${entry.name}/`)
    walk(at, `${rel}${entry.name}/`)
  }
}
walk(DIST, '')

// Подпись над заголовком — раздел меню, как крошка: «Виды СРО», «Услуги».
const KICKER = (url) =>
  url.startsWith('uslugi/') ? 'Услуги' : url.startsWith('sro-') ? 'Виды СРО' : 'Со\u00a0ссылками на\u00a0Градостроительный кодекс'

for (const url of pages.sort()) {
  const source = readFileSync(resolve(DIST, url, 'index.html'), 'utf8')
  const h1 = source.match(/<h1[^>]*>([\s\S]*?)<\/h1>/)
  if (!h1) throw new Error(`Нет <h1> на странице ${url}`)
  let name = textOf(h1[1])
  // Строка шапки: первая подпись data-hero-text после заголовка; у статьи
  // перед заголовком — дата и время чтения.
  const before = source.slice(0, h1.index)
  const after = source.slice(h1.index + h1[0].length)
  const lead = textOf(after.match(/data-hero-text[^>]*>([\s\S]*?)<\/span>/)?.[1] ?? '')
  const meta = textOf([...before.matchAll(/data-hero-text[^>]*>([\s\S]*?)<\/span>/g)].pop()?.[1] ?? '')
  let kicker = KICKER(url)
  if (url.startsWith('stati/') && url !== 'stati/') kicker = `Статья${meta ? ' · ' + meta.split(' · ')[0] : ''}`
  // Список статей: «Статьи» в заголовке ничего не скажет в ленте мессенджера.
  if (url === 'stati/') name = 'Статьи о\u00a0вступлении в\u00a0СРО'
  if (!lead) throw new Error(`Нет строки под заголовком на странице ${url}`)

  const card = html
    .replace(/<div class="wrap">[\s\S]*<\/div>\s*<\/body>/, `<div class="wrap page">
    <div class="top">${SCALES.replace('width:104px', 'width:64px')}<span>ООО «БИЗНЕС-ГРУПП»</span></div>
    <div class="body">
      <div class="eyebrow"><i></i>${escHtml(kicker)}</div>
      <div class="name">${escHtml(name)}</div>
      <div class="lead">${escHtml(lead)}</div>
    </div>
    <div class="foot"><span>biznesgrp.ru</span><span>Консультация бесплатная</span></div>
  </div>
</body>`)
    .replace('</style>', `
  .page{justify-content:flex-start;padding:56px 90px 50px}
  .top{display:flex;align-items:center;gap:22px;font-size:24px;color:#D6CDC1;letter-spacing:.01em}
  .body{flex:1;display:flex;flex-direction:column;justify-content:center}
  .page .eyebrow{margin-top:0}
  .page .name{font-size:72px;line-height:1.04}
  .page .lead{font-size:28px;max-width:960px}
  .foot{display:flex;justify-content:space-between;padding-top:24px;border-top:1px solid #FFFFFF26;
    font-size:22px;color:#A79D91;letter-spacing:.01em}
</style>`)
  await page.setContent(card, { waitUntil: 'load' })
  await page.evaluate(() => document.fonts.ready).catch(() => {})
  // Заголовок и строка ужимаются, пока всё не встанет в 630 px: заголовки
  // от «Статей» до «Независимой оценки квалификации (НОК)».
  const fit = await page.evaluate(() => {
    const name = document.querySelector('.name')
    const lead = document.querySelector('.lead')
    const body = document.querySelector('.body')
    let n = 72
    let l = 28
    const over = () => body.scrollHeight > body.clientHeight || document.body.scrollHeight > 630
    while (over() && n > 48) {
      n -= 2
      l = Math.max(23, l - 0.5)
      name.style.fontSize = `${n}px`
      lead.style.fontSize = `${l}px`
    }
    return { n, l, ok: !over() }
  })
  if (!fit.ok) throw new Error(`Текст не помещается в картинку: ${url}`)
  await page.waitForTimeout(150)
  const file = ogName(url)
  await page.screenshot({ path: resolve(OG_DIR, file), type: 'jpeg', quality: 90 })
  console.log(`  og/${file} — «${name.replace(/\u00a0/g, ' ')}» (${fit.n}/${fit.l} px)`)
}
await browser.close()
