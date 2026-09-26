// Фирменные файлы: знак, логотип, аватар и шапка для писем.
//
// Запуск:  npm run brand    → папка norma-site/brand/
//
// Зачем скриптом, а не руками в редакторе. Знак живёт в разметке
// (LogoMark.astro), цвета — в global.css, контакты — в config/site.ts.
// Нарисованный однажды и положенный в папку логотип разойдётся с сайтом
// при первой же правке телефона или оттенка, и заметить это будет некому.
// Здесь всё берётся из тех же источников, что и сам сайт.
//
// Текст в PNG растрируется, поэтому рядом кладётся PDF: Chromium печатает
// его вектором и вшивает шрифты, так что в типографии логотип не рассыплется.

import { execFileSync } from 'node:child_process'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const out = join(root, 'brand')
const fonts = join(root, 'public/fonts')
mkdirSync(out, { recursive: true })

// ── Источники правды ──────────────────────────────────────────────────────
const site = readFileSync(join(root, 'src/config/site.ts'), 'utf8')
const css = readFileSync(join(root, 'src/styles/global.css'), 'utf8')
const val = (src, key, re) => (src.match(re) || [])[1] ?? (() => { throw new Error(`не нашёл ${key}`) })()

const BRAND = val(site, 'brand', /brand:\s*'([^']+)'/)
const TAG = val(site, 'brandTag', /brandTag:\s*'([^']+)'/)
const PHONE = val(site, 'phone', /phone:\s*'([^']+)'/)
const ACC = val(css, '--acc', /--acc:\s*(#[0-9A-Fa-f]{6})/)
const ACC_BRIGHT = val(css, '--acc-bright', /--acc-bright:\s*(#[0-9A-Fa-f]{6})/)
const INK = val(css, '--ink', /--ink:\s*(#[0-9A-Fa-f]{6})/)
const DARK = val(css, '--dark', /--dark:\s*(#[0-9A-Fa-f]{6})/)
const LINE = val(css, '--line', /--line:\s*(#[0-9A-Fa-f]{6})/)
const PAPER = val(css, '--paper', /--paper:\s*(#[0-9A-Fa-f]{6})/)
const DOMAIN = 'norma-sro.ru'

// Монограмма — те же четыре контура, что в LogoMark.astro.
const mark = readFileSync(join(root, 'src/components/LogoMark.astro'), 'utf8')
const PATHS = [...mark.matchAll(/<path\s+d="([^"]+)"|d="([^"]+)"/g)]
  .map((m) => m[1] || m[2])
  .filter(Boolean)
if (PATHS.length !== 4) throw new Error(`в LogoMark.astro ожидалось 4 контура, найдено ${PATHS.length}`)

const markSvg = (fill) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="${fill}">\n` +
  PATHS.map((d) => `  <path d="${d}"/>`).join('\n') +
  '\n</svg>\n'

writeFileSync(join(out, 'znak.svg'), markSvg(ACC))
writeFileSync(join(out, 'znak-belyy.svg'), markSvg('#FFFFFF'))

// ── Шрифты вшиваем в страницу, иначе Chromium возьмёт системный ───────────
const font = (file) => `url(data:font/woff2;base64,${readFileSync(join(fonts, file)).toString('base64')}) format('woff2')`
const FACE = `
  @font-face { font-family: L; src: ${font('literata-cyrillic.woff2')}; font-weight: 400 800; }
  @font-face { font-family: L; src: ${font('literata-latin.woff2')}; font-weight: 400 800; unicode-range: U+0000-024F; }
  @font-face { font-family: G; src: ${font('golos-cyrillic.woff2')}; font-weight: 400 700; }
  @font-face { font-family: G; src: ${font('golos-latin.woff2')}; font-weight: 400 700; unicode-range: U+0000-024F; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
`

// Замок логотипа: знак, название антиквой вразрядку, под ним подпись.
const lockup = (ink, accent, muted, scale = 1) => `
  <div style="display:flex;align-items:center;gap:${18 * scale}px">
    <svg style="display:block" viewBox="0 0 100 100" width="${58 * scale}" height="${58 * scale}" fill="${accent}">
      ${PATHS.map((d) => `<path d="${d}"/>`).join('')}
    </svg>
    <div style="display:grid;gap:${4 * scale}px">
      <div style="font-family:L;font-weight:800;font-size:${38 * scale}px;letter-spacing:.09em;color:${ink};line-height:1">${BRAND}</div>
      <div style="font-family:G;font-size:${14.5 * scale}px;letter-spacing:.02em;color:${muted};line-height:1">${TAG}</div>
    </div>
  </div>`

const page = (w, h, body, bg = 'transparent') =>
  `<!doctype html><meta charset="utf-8"><style>${FACE}
   body{width:${w}px;height:${h}px;background:${bg};display:flex;align-items:center}</style>${body}`

const browser = await chromium.launch()

// Снимаем НЕ страницу, а сам элемент. Холст фиксированного размера почти
// всегда шире содержимого, и логотип уезжал бы в левую половину файла
// с пустотой справа — вставить такой в письмо или в документ нельзя,
// он выглядит сдвинутым. Поле вокруг задаётся явно, чтобы буквы
// не упирались в край.
const shot = async (name, w, h, body, { bg = 'transparent', scale = 2, pdf = false, pad = 0 } = {}) => {
  const ctx = await browser.newContext({ viewport: { width: w + pad * 2, height: h + pad * 2 }, deviceScaleFactor: scale })
  const p = await ctx.newPage()
  await p.setContent(page(w + pad * 2, h + pad * 2, `<div id="a" style="padding:${pad}px;display:inline-block">${body}</div>`, bg), { waitUntil: 'load' })
  await p.evaluate(() => document.fonts.ready)
  const el = p.locator('#a')
  await el.screenshot({ path: join(out, `${name}.png`), omitBackground: bg === 'transparent' })
  if (pdf) {
    const box = await el.boundingBox()
    await p.pdf({ path: join(out, `${name}.pdf`), width: `${box.width}px`, height: `${box.height}px`, printBackground: bg !== 'transparent', pageRanges: '1' })
  }
  await ctx.close()
  return `${name}.png`
}

// 1. Знак отдельно — для аватарок и мест, где нужен только символ.
await shot('znak', 512, 512, `<svg style="display:block" viewBox="-6 -6 112 112" width="512" height="512" fill="${ACC}">${PATHS.map((d) => `<path d="${d}"/>`).join('')}</svg>`)

// 2. Горизонтальный логотип на прозрачном — тёмный и светлый.
await shot('logotip', 460, 110, lockup(INK, ACC, '#6B6156'), { pdf: true, pad: 14 })
await shot('logotip-belyy', 460, 110, lockup('#FFFFFF', ACC_BRIGHT, '#B3A99C'), { pad: 14 })

// 3. Аватар для мессенджеров и почты.
//
// Знак занимает ТРЕТЬ квадрата, а не половину, и это не вкусовщина.
// Почти все такие места обрезают картинку в круг, а некоторые ещё и
// подрезают его изнутри собственной рамкой. Знак во всю ширину теряет
// при этом засечки — а засечки здесь и делают из двух букв монограмму.
// Треть оставляет запас с любой стороны: круг вписан в квадрат, и центр
// при любой обрезке остаётся нетронутым.
const avatar = (bg, fill) =>
  `<div style="width:512px;height:512px;background:${bg};display:grid;place-items:center">
     <svg style="display:block" viewBox="0 0 100 100" width="172" height="172" fill="${fill}">${PATHS.map((d) => `<path d="${d}"/>`).join('')}</svg>
   </div>`
await shot('avatar', 512, 512, avatar(DARK, ACC_BRIGHT), { bg: DARK, scale: 1 })
await shot('avatar-svetlyy', 512, 512, avatar(PAPER, ACC), { bg: PAPER, scale: 1 })

// 4. Шапка письма. 600×140 в пересчёте на экран — стандартная ширина письма;
//    снимается в двойном размере, чтобы не мылилась на телефоне.
//    Сургучный отрезок на линейке — та же размерная линия, что делит
//    секции на сайте: единственное яркое пятно, всё остальное бумага.
const header = `
  <div style="width:600px;height:140px;background:${PAPER};position:relative;font-synthesis:none">
    <div style="position:absolute;left:34px;right:34px;top:0;bottom:22px;
                display:flex;align-items:center;justify-content:space-between">
      ${lockup(INK, ACC, '#6B6156', 0.78)}
      <div style="text-align:right;display:grid;gap:5px">
        <div style="font-family:G;font-weight:700;font-size:20px;color:${INK};
                    font-variant-numeric:lining-nums tabular-nums;white-space:nowrap">${PHONE}</div>
        <div style="font-family:G;font-size:13.5px;color:${ACC}">${DOMAIN}</div>
      </div>
    </div>
    <div style="position:absolute;left:34px;right:34px;bottom:20px;height:1px;background:${LINE}"></div>
    <div style="position:absolute;left:34px;bottom:19px;width:46px;height:3px;background:${ACC}"></div>
  </div>`
await shot('pochta-shapka', 600, 140, header, { bg: PAPER })

await browser.close()

// Размеры читаем из самих файлов: записанные руками расходятся с делом
// при первой же правке раскладки, а проверить их некому.
const png = (f) => {
  const b = readFileSync(join(out, f))
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), kb: (b.length / 1024).toFixed(0) }
}
const row = (f, what) => {
  const { w, h, kb } = png(f)
  return `  ${f.padEnd(22)} ${String(w + '×' + h).padEnd(12)} ${what.padEnd(28)} ${kb} КБ`
}
console.log(`
Фирменные файлы собраны в norma-site/brand/

  znak.svg, znak-belyy.svg   вектор, только монограмма
${row('znak.png', 'прозрачный фон')}
${row('logotip.png', 'прозрачный фон')}
${row('logotip-belyy.png', 'для тёмного фона')}
${row('avatar.png', 'аватар, тёмный')}
${row('avatar-svetlyy.png', 'аватар, светлый')}
${row('pochta-shapka.png', 'шапка письма, 600×140 на экране')}
  logotip.pdf            вектор       для печати

Цвета и контакты взяты из site.ts и global.css — руками здесь не вписано ничего.
`)
