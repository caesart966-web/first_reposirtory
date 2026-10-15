// Собирает картинку-превью (og-image) для мессенджеров и соцсетей.
// Рисуется в браузере из HTML и сохраняется в public/og.jpg — 1200×630.
//
// Запуск (после npm install):  node scripts/make-og.mjs
// Повторять нужно, только если поменялись название, телефон или оформление.

import { chromium } from 'playwright'
import { writeFile, readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const out = resolve(here, '../public/og.jpg')

// Данные берём из того же конфига, что и сайт, — чтобы картинка не разошлась с текстом.
const site = await import(resolve(here, '../src/config/site.ts')).catch(() => null)
const PHONE = site?.SITE?.phone ?? '+7 931 969-86-64'

// Фирменный знак берём из того же файла, что и сайт, — чтобы картинка-превью
// не разошлась с логотипом в шапке.
const markFile = await readFile(resolve(here, '../src/components/LogoMark.astro'), 'utf8')

// Цвета — из global.css, как у npm run brand: превью в мессенджерах
// обязано быть того же цвета, что сайт (с 07.10.2026 — синего).
const css = await readFile(resolve(here, '../src/styles/global.css'), 'utf8')
const token = (name) => {
  const m = css.match(new RegExp(`${name}:\\s*(#[0-9A-Fa-f]{6})`))
  if (!m) throw new Error(`не нашёл ${name} в global.css`)
  return m[1]
}
const DARK = token('--dark')
const ACC = token('--acc')
const ACC_BRIGHT = token('--acc-bright')
const ON_DARK_MUTED = token('--on-dark-muted')
const rgba = (hex, a) => `rgba(${[1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(',')},${a})`
const MARK = markFile.slice(markFile.indexOf('<svg'), markFile.lastIndexOf('</svg>') + 6)
  .replace(/height=\{[^}]+\}/, 'height="58"')
  .replace(/width=\{[^}]+\}/, 'width="58"')
  .replace(/class=\{[^}]+\}/, '')

// Шрифты — свои, из public/fonts, вписанные в страницу (data:). Раньше
// здесь стояла ссылка на Google Fonts, и превью годами рисовалось запасными
// Times и Arial: страница открывается через setContent как about:blank,
// и до шрифтов она не доходила (замечено 07.10.2026 при смене цвета).
const font = async (file) =>
  `url(data:font/woff2;base64,${(await readFile(resolve(here, '../public/fonts', file))).toString('base64')}) format('woff2')`
const FONTS = `
  @font-face { font-family: 'Literata'; font-weight: 200 900; src: ${await font('literata-cyrillic.woff2')}; unicode-range: U+0400-045F, U+2116; }
  @font-face { font-family: 'Literata'; font-weight: 200 900; src: ${await font('literata-latin.woff2')}; unicode-range: U+0000-00FF, U+2010-2027; }
  @font-face { font-family: 'Golos Text'; font-weight: 400 900; src: ${await font('golos-cyrillic.woff2')}; unicode-range: U+0400-045F, U+2116; }
  @font-face { font-family: 'Golos Text'; font-weight: 400 900; src: ${await font('golos-latin.woff2')}; unicode-range: U+0000-00FF, U+2010-2027; }
  @font-face { font-family: 'Golos Text'; font-weight: 400 900; src: ${await font('golos-rub.woff2')}; unicode-range: U+20BD; }`

const html = `<!doctype html>
<html><head><meta charset="utf-8">
<style>
  ${FONTS}
  * { box-sizing: border-box; margin: 0; }
  body {
    width: 1200px; height: 630px;
    background: ${DARK};
    color: #fff;
    font-family: 'Golos Text', sans-serif;
    padding: 72px 80px;
    display: flex; flex-direction: column; justify-content: space-between;
    position: relative; overflow: hidden;
  }
  /* Клетка отсюда убрана: заказчик просил убрать её с первого экрана сайта
     («читается школьной тетрадью»), а на картинке-превью она оставалась —
     то есть в мессенджерах сайт представлялся тем оформлением, от которого
     на нём самом отказались. Вместо неё — свет из угла в цвет акцента
     и вторая, слабая подсветка снизу слева, чтобы низ не был плоским.
     Картинка сохраняется в JPEG, а не PNG. Проверено на этом же файле:
     PNG с клеткой весил 144 КБ, PNG с гладкими градиентами — 165, то есть
     стал хуже. Плавные переходы для PNG тяжелее тонких линий: он хранит
     каждый оттенок, а их тут тысячи. JPEG для такой картинки — 47 КБ
     при неотличимом качестве, и og:image его принимает наравне с PNG. */
  .glow {
    position: absolute; inset: 0;
    background:
      radial-gradient(760px 440px at 84% 10%, ${rgba(ACC, 0.34)}, transparent 70%),
      radial-gradient(620px 380px at 6% 96%, ${rgba(ACC_BRIGHT, 0.1)}, transparent 72%);
  }
  .row { position: relative; display: flex; align-items: center; gap: 16px; }
  .mark { display: grid; place-items: center; color: ${ACC_BRIGHT}; }
  .brand b { font-size: 26px; font-weight: 800; letter-spacing: .07em; display: block; line-height: 1.1; }
  .brand span { font-size: 15px; color: ${ON_DARK_MUTED}; }
  h1 { position: relative; font-family: 'Literata', Georgia, serif; font-size: 60px; font-weight: 700; line-height: 1.1; letter-spacing: -.02em; max-width: 17ch; }
  h1 em { font-style: normal; color: ${ACC_BRIGHT}; }
  .foot { position: relative; display: flex; align-items: flex-end; justify-content: space-between; gap: 40px; }
  .facts { display: flex; gap: 40px; }
  .fact b { display: block; font-size: 30px; font-weight: 800; color: #fff; line-height: 1.1; }
  .fact span { font-size: 15px; color: ${ON_DARK_MUTED}; }
  .phone { font-family: 'Golos Text', sans-serif; font-size: 26px; color: ${ACC_BRIGHT}; white-space: nowrap; }
</style></head>
<body>
  <div class="glow"></div>
  <div class="row">
    <div class="mark">${MARK}</div>
    <div class="brand"><b>НОРМА</b><span>вступление в СРО · НРС · НОК · лицензии</span></div>
  </div>
  <h1>Вступление в СРО <em>без устаревших норм</em></h1>
  <div class="foot">
    <div class="facts">
      <div class="fact"><b>2–3 дня</b><span>выписка из реестра</span></div>
      <div class="fact"><b>0 ₽</b><span>подготовка документов</span></div>
      <div class="fact"><b>10 млн ₽</b><span>актуальный порог</span></div>
    </div>
    <div class="phone">${PHONE}</div>
  </div>
</body></html>`

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } })
await page.setContent(html, { waitUntil: 'networkidle' })
await page.evaluate(() => document.fonts.ready)
// Шрифт обязан быть своим: запасной Times — та самая ошибка, что жила здесь годами.
const fams = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family))
if (!fams.some((f) => f.includes('Literata')) || !fams.some((f) => f.includes('Golos'))) {
  throw new Error(`шрифты превью не загрузились: ${fams.join(', ') || 'ни одного'}`)
}
const buffer = await page.screenshot({ type: 'jpeg', quality: 90 })
await writeFile(out, buffer)
await browser.close()

console.log(`Картинка-превью сохранена: ${out}`)
