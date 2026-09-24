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
// Кладёт public/og.png. Размеры и вес сторожит набор og-sitemap.mjs.
const pw = await import(process.env.PLAYWRIGHT || 'playwright-core')
const { chromium } = pw.default ?? pw
import { readFileSync } from 'node:fs'
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

// Знак весов — те же координаты, что в ScalesMark: viewBox 0 0 46 26.
const SCALES = `<svg viewBox="0 0 46 26" fill="none" stroke="#C09A68" stroke-width="1.6"
  stroke-linecap="round" stroke-linejoin="round" style="width:120px;height:auto">
  <path d="M23 1.8V5"/><path d="M8.98 7 23 5l14.04 2"/>
  <path d="M8.98 7 1.99 21M8.98 7l6.99 14"/><path d="M1.99 21a8.9 8.9 0 0 0 13.98 0"/>
  <path d="M1.99 21h13.98"/><path d="M37.02 7 30.03 21M37.02 7l6.99 14"/>
  <path d="M30.03 21a8.9 8.9 0 0 0 13.98 0"/><path d="M30.03 21h13.98"/></svg>`

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

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' })
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 })
await page.setContent(html, { waitUntil: 'load' })
// Шрифт может не приехать (сеть закрыта) — тогда рисуем системным, но ждём попытку.
await page.evaluate(() => document.fonts.ready).catch(() => {})
await page.waitForTimeout(600)
await page.screenshot({ path: OUT, type: 'png' })
await browser.close()
console.log('og.png готов:', OUT)
