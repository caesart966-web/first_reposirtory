// Картинка для мессенджеров (og:image), 1200×630.
//
// Собирается из фирменных элементов сайта, а не рисуется отдельно: тот же
// знак весов из illustrations.tsx, тот же тёмный фон accent-950, что у блока
// заявки и подвала, тот же Inter. Фотографий нет намеренно — карточка в
// мессенджере показывается размером с ноготь, и любой кадр там превращается
// в кашу, а знак и имя читаются.
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

// Тот же Inter, что на сайте, и берём его из node_modules, а не из сети:
// среда сборки может быть без интернета, и тогда картинка молча уехала бы
// системным шрифтом — на глаз почти незаметно, а фирменный вид уже не тот.
const FONTS = resolve(root, 'node_modules/@fontsource-variable/inter/files')
const face = (subset) =>
  `@font-face{font-family:Inter;font-style:normal;font-weight:100 900;src:url(data:font/woff2;base64,` +
  readFileSync(resolve(FONTS, `inter-${subset}-wght-normal.woff2`)).toString('base64') +
  `) format('woff2-variations')}`

// Знак весов — те же координаты, что в ScalesMark: viewBox 0 0 46 26.
const SCALES = `<svg viewBox="0 0 46 26" fill="none" stroke="#A3B8FC" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round" style="width:150px;height:auto">
  <path d="M23 1.8V5"/><path d="M8.98 7 23 5l14.04 2"/>
  <path d="M8.98 7 1.99 21M8.98 7l6.99 14"/><path d="M1.99 21a8.9 8.9 0 0 0 13.98 0"/>
  <path d="M1.99 21h13.98"/><path d="M37.02 7 30.03 21M37.02 7l6.99 14"/>
  <path d="M30.03 21a8.9 8.9 0 0 0 13.98 0"/><path d="M30.03 21h13.98"/></svg>`

const html = `<!doctype html><html lang="ru"><head><meta charset="utf-8">
<style>
  ${face('cyrillic')}
  ${face('latin')}
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:1200px;height:630px;background:#141A45;overflow:hidden;
    font-family:Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
  /* Чертёжная сетка — тот же приём, что на первом экране сайта: едва заметная,
     она даёт фону строительный характер и не спорит с текстом. */
  .grid{position:absolute;inset:0;
    background-image:linear-gradient(#A3B8FC14 1px,transparent 1px),
                     linear-gradient(90deg,#A3B8FC14 1px,transparent 1px);
    background-size:60px 60px}
  .glow{position:absolute;right:-140px;top:-160px;width:620px;height:620px;border-radius:50%;
    background:radial-gradient(circle,#2F4BDE55 0%,#2F4BDE00 68%)}
  .wrap{position:relative;height:100%;display:flex;flex-direction:column;
    justify-content:center;padding:0 86px}
  .name{margin-top:38px;font-size:64px;font-weight:700;color:#fff;letter-spacing:-.02em}
  .role{margin-top:14px;font-size:34px;font-weight:600;color:#A3B8FC}
  .lead{margin-top:30px;font-size:27px;line-height:1.35;color:#D8D3CC;max-width:900px}
  .rule{margin-top:38px;width:104px;height:5px;border-radius:3px;background:#2F4BDE}
  .tags{margin-top:26px;font-size:23px;color:#A9A29A;letter-spacing:.02em}
</style></head><body>
  <div class="grid"></div><div class="glow"></div>
  <div class="wrap">
    ${SCALES}
    <div class="name">ООО «БИЗНЕС-ГРУПП»</div>
    <div class="role">Вступление в СРО</div>
    <div class="lead">Строители, проектировщики, изыскатели. Подбор СРО, подготовка
      документов, специалисты НРС — до внесения в реестр членов.</div>
    <div class="rule"></div>
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
