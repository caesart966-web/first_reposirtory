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
const ON_DARK = val(css, '--on-dark', /--on-dark:\s*(#[0-9A-Fa-f]{6})/)
const MUTED = val(css, '--muted', /--muted:\s*(#[0-9A-Fa-f]{6})/)
const ON_DARK_MUTED = val(css, '--on-dark-muted', /--on-dark-muted:\s*(#[0-9A-Fa-f]{6})/)
const DOMAIN = 'norma-sro.ru'

// ── Строка услуг в шапке письма ───────────────────────────────────────────
//
// Подписи написаны здесь, а НЕ взяты из services.ts дословно: в конфиге
// они для меню сайта («Лицензии»), а в письме важно назвать то, за чем
// приходят («лицензии МЧС и Ростехнадзора» — и то и другое на странице
// услуги действительно есть).
//
// Но привязка к конфигурации всё равно нужна, поэтому у каждой подписи
// стоит slug, и скрипт ПРОВЕРЯЕТ, что такая услуга на сайте есть. Уберут
// услугу со страницы — сборка шапки упадёт с её именем, а не будет молча
// обещать в письмах то, чего сайт уже не делает.
const services = readFileSync(join(root, 'src/config/services.ts'), 'utf8')
const SERVICE_ROWS = [
  ['nrs', 'НРС и НОК'],
  ['ohrana-truda', 'охрана труда'],
  ['promyshlennaya-bezopasnost', 'промбезопасность'],
  ['licenzii', 'лицензии МЧС'],
  ['yuridicheskie-uslugi', 'юридические услуги'],
]
const missing = SERVICE_ROWS.filter(([slug]) => !services.includes(`slug: '${slug}'`)).map(([s]) => s)
if (missing.length) throw new Error(`в шапке письма обещаны услуги, которых нет в services.ts: ${missing.join(', ')}`)
// Список нарочно неполный: строка одна, в неё влезает пять пунктов,
// и проверка ниже это стережёт. Полный перечень — на сайте, в «Услугах»:
// у лицензий там не только МЧС, но и Ростехнадзор, Минкультуры и отходы.
const SERVICE_LINE = SERVICE_ROWS.map(([, label]) => label).join(' · ')

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
// Доля радиуса вписанного круга, за которую содержимое квадратных картинок
// не должно выходить. Не 100 %: часть мест рисует поверх круга ещё и рамку
// изнутри, и знак, упёртый в край, теряет засечки.
const CIRCLE_SAFE = 0.85

const shot = async (name, w, h, body, { bg = 'transparent', scale = 2, pdf = false, pad = 0, fits = null, circle = null, safe = null, jpeg = false } = {}) => {
  const ctx = await browser.newContext({ viewport: { width: w + pad * 2, height: h + pad * 2 }, deviceScaleFactor: scale })
  const p = await ctx.newPage()
  await p.setContent(page(w + pad * 2, h + pad * 2, `<div id="a" style="padding:${pad}px;display:inline-block">${body}</div>`, bg), { waitUntil: 'load' })
  await p.evaluate(() => document.fonts.ready)
  const el = p.locator('#a')
  const file = join(out, `${name}.${jpeg ? 'jpg' : 'png'}`)
  // Строка услуг набрана в одну линию и обрезается молча: браузер просто
  // уводит хвост за край, и в письме «юридические услуги» превратятся
  // в «юридичес». Меряем настоящие пиксели.
  if (fits) {
    const over = await p.locator(fits).evaluate((n) => n.scrollWidth - n.clientWidth)
    if (over > 0) throw new Error(`строка услуг шире поля на ${over} px — сократите подписи в SERVICE_ROWS`)
  }
  // Квадратные картинки почти везде обрезают в круг. Проверяем по настоящим
  // прямоугольникам элементов, что каждый их угол лежит внутри круга
  // с запасом, — а не надеемся, что подпись «вроде бы влезла».
  if (circle) {
    const far = await p.evaluate((sels) => {
      const box = document.querySelector('#a').getBoundingClientRect()
      const cx = box.left + box.width / 2
      const cy = box.top + box.height / 2
      const r = Math.min(box.width, box.height) / 2
      let worst = 0
      for (const s of sels) for (const n of document.querySelectorAll(s)) {
        const b = n.getBoundingClientRect()
        for (const [x, y] of [[b.left, b.top], [b.right, b.top], [b.left, b.bottom], [b.right, b.bottom]]) {
          worst = Math.max(worst, Math.hypot(x - cx, y - cy) / r)
        }
      }
      return worst
    }, circle)
    if (far > CIRCLE_SAFE) {
      throw new Error(`${name}: содержимое доходит до ${Math.round(far * 100)} % радиуса при допустимых ${Math.round(CIRCLE_SAFE * 100)} % — при обрезке в круг его срежет`)
    }
  }
  // Широкие картинки обрезают не в круг, а в кадр другой пропорции.
  // Зона, которая переживает обрезку, задаётся прямоугольником в координатах
  // полотна, и каждый элемент из списка обязан лежать в ней целиком.
  if (safe) {
    const outside = await p.evaluate(({ sels, x0, y0, x1, y1 }) => {
      const box = document.querySelector('#a').getBoundingClientRect()
      const bad = []
      for (const s of sels) for (const n of document.querySelectorAll(s)) {
        const b = n.getBoundingClientRect()
        const l = b.left - box.left
        const t = b.top - box.top
        const r = b.right - box.left
        const d = b.bottom - box.top
        if (l < x0 || t < y0 || r > x1 || d > y1) bad.push(`${s}: ${Math.round(l)}–${Math.round(r)} × ${Math.round(t)}–${Math.round(d)}`)
      }
      return bad
    }, safe)
    if (outside.length) {
      throw new Error(`${name}: выходит из зоны ${Math.round(safe.x0)}–${Math.round(safe.x1)} × ${Math.round(safe.y0)}–${Math.round(safe.y1)}, которую не срежет обрезка: ${outside.join('; ')}`)
    }
  }
  await el.screenshot({
    path: file,
    omitBackground: !jpeg && bg === 'transparent',
    ...(jpeg ? { type: 'jpeg', quality: 92 } : {}),
  })
  if (pdf) {
    const box = await el.boundingBox()
    await p.pdf({ path: join(out, `${name}.pdf`), width: `${box.width}px`, height: `${box.height}px`, printBackground: bg !== 'transparent', pageRanges: '1' })
  }
  await ctx.close()
  return file
}

// 1. Знак отдельно — для аватарок и мест, где нужен только символ.
await shot('znak', 512, 512, `<svg style="display:block" viewBox="-6 -6 112 112" width="512" height="512" fill="${ACC}">${PATHS.map((d) => `<path d="${d}"/>`).join('')}</svg>`)

// 2. Горизонтальный логотип на прозрачном — тёмный и светлый.
await shot('logotip', 460, 110, lockup(INK, ACC, MUTED), { pdf: true, pad: 14 })
await shot('logotip-belyy', 460, 110, lockup('#FFFFFF', ACC_BRIGHT, ON_DARK_MUTED), { pad: 14 })

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

// 3а. Квадратный логотип с подписью — для каталогов организаций
//     (Яндекс Бизнес и подобные), где картинка стоит рядом с названием.
//
// Подписать знак попросил заказчик (27.09.2026): в каталоге рядом стоит
// название «Норма», а слово «норма» само по себе о предмете не говорит —
// разбор имени в README. Подпись та же, что у горизонтального логотипа
// (SITE.brandTag), но с заглавной: здесь она стоит отдельной строкой.
//
// Такие картинки тоже обрезают в круг, поэтому знак меньше, чем у аватара
// (150 против 172), а вписанность в круг меряет shot(): подпись шире знака,
// и её углы уходят к краю первыми. Снимается в 1024 px — каталоги
// принимают крупные файлы и сами уменьшают их под свои размеры.
const TAG_LINE = TAG[0].toUpperCase() + TAG.slice(1)
const stack = (w, h, bg, fill, ink, { mark, gap, size }) =>
  `<div style="width:${w}px;height:${h}px;background:${bg};display:grid;place-content:center;justify-items:center;gap:${gap}px">
     <svg style="display:block" viewBox="0 0 100 100" width="${mark}" height="${mark}" fill="${fill}">${PATHS.map((d) => `<path d="${d}"/>`).join('')}</svg>
     <div id="tag" style="font-family:G;font-weight:600;font-size:${size}px;letter-spacing:.01em;line-height:1;white-space:nowrap;color:${ink}">${TAG_LINE}</div>
   </div>`
const square = (bg, fill, ink) => stack(512, 512, bg, fill, ink, { mark: 150, gap: 24, size: 38 })
await shot('logotip-kvadrat', 512, 512, square(DARK, ACC_BRIGHT, ON_DARK), { bg: DARK, circle: ['#a svg', '#tag'] })
await shot('logotip-kvadrat-svetlyy', 512, 512, square(PAPER, ACC, INK), { bg: PAPER, circle: ['#a svg', '#tag'] })

// 3б. Обложка — тот же знак с подписью на широком полотне (просьба
//     заказчика, 27.09.2026: «такой же логотип для обложки»).
//
// Справку Яндекса из среды сборки не открыть (yandex.ru закрыт сетевой
// политикой), а вторичные источники называют разные пропорции: 2,5 : 1
// (400×160) и 4 : 1 (1440×360). Поэтому полотно — 2,5 : 1, 2000×800,
// а знак с подписью стоят в зоне, которая переживает обе обрезки: по высоте —
// полоса 4 : 1 из середины, по ширине — кадр 16 : 9 на случай, если узкий
// экран подрежет обложку с боков. Проверяет это shot(), по настоящим
// прямоугольникам. Текста, кроме подписи, нет нарочно: контакты на обложке
// каталоги не любят, и у них для этого есть свои поля.
const COVER_W = 1000
const COVER_H = 400
const band = COVER_W / 4
const frame = (COVER_H * 16) / 9
const COVER_SAFE = {
  sels: ['#a svg', '#tag'],
  x0: (COVER_W - frame) / 2 + 24,
  x1: (COVER_W + frame) / 2 - 24,
  y0: (COVER_H - band) / 2 + 16,
  y1: (COVER_H + band) / 2 - 16,
}
const cover = (bg, fill, ink) => stack(COVER_W, COVER_H, bg, fill, ink, { mark: 140, gap: 22, size: 36 })
await shot('oblozhka', COVER_W, COVER_H, cover(DARK, ACC_BRIGHT, ON_DARK), { bg: DARK, safe: COVER_SAFE })
await shot('oblozhka-svetlaya', COVER_W, COVER_H, cover(PAPER, ACC, INK), { bg: PAPER, safe: COVER_SAFE })

// 4. Шапка письма. 600×140 в пересчёте на экран — стандартная ширина письма;
//    снимается в двойном размере, чтобы не мылилась на телефоне.
//    Сургучный отрезок на линейке — та же размерная линия, что делит
//    секции на сайте: единственное яркое пятно, всё остальное бумага.
// Раскладка потоком, а не абсолютом: высота получается из содержимого,
// и между логотипом и линейкой не остаётся лишнего белого поля.
// Первая версия была прибита к 162 px, и под подписью зияло 40 px пустоты.
const header = `
  <div style="width:600px;background:${PAPER};padding:20px 34px 13px;font-synthesis:none">
    <div style="display:flex;align-items:center;justify-content:space-between">
      ${lockup(INK, ACC, MUTED, 0.78)}
      <div style="text-align:right;display:grid;gap:5px">
        <div style="font-family:G;font-weight:700;font-size:20px;color:${INK};
                    font-variant-numeric:lining-nums tabular-nums;white-space:nowrap">${PHONE}</div>
        <div style="font-family:G;font-size:13.5px;color:${ACC}">${DOMAIN}</div>
      </div>
    </div>
    <div style="position:relative;margin-top:17px;height:1px;background:${LINE}">
      <div style="position:absolute;left:0;top:-1px;width:46px;height:3px;background:${ACC}"></div>
    </div>
    <div id="uslugi" style="margin-top:11px;font-family:G;font-size:11.5px;
                letter-spacing:.01em;color:${MUTED};white-space:nowrap">${SERVICE_LINE}</div>
  </div>`
await shot('pochta-shapka', 600, 200, header, { bg: PAPER, fits: '#uslugi' })

// Запасные варианты шапки. Почтовые сервисы капризны к вложениям в подпись:
// Mail.ru отказался грузить файл с пробелом и скобками в имени, а некоторые
// режут по ширине или не принимают PNG. Поэтому рядом лежат тот же рисунок
// в одинарном масштабе (600 px по ширине) и в JPEG. Картинка одна и та же,
// разница только в размере файла и формате.
await shot('pochta-shapka-600', 600, 200, header, { bg: PAPER, scale: 1 })
await shot('pochta-shapka', 600, 200, header, { bg: PAPER, jpeg: true })

// ── Шапка едет вместе с сайтом ────────────────────────────────────────────
//
// Mail.ru отказался принимать файл в подпись — и с исходным именем,
// и с переименованным. Обходной путь надёжнее самой загрузки: картинка
// лежит на своём сайте, а в подпись вставляется ССЫЛКОЙ. Тогда её
// не нужно никуда загружать, а поменяется шапка — обновится у всех
// писем разом, без правки подписи.
//
// Поэтому файл копируется в public/img/ и уезжает в сборку сайта.
// Ни одна страница его не показывает, и это не мусор: потребитель
// у него есть — подпись в почте, адрес записан в brand/README.md.
const { copyFileSync } = await import('node:fs')
copyFileSync(join(out, 'pochta-shapka.png'), join(root, 'public/img/pochta-shapka.png'))

// ── Подпись без картинки ──────────────────────────────────────────────────
//
// Запасной путь, и местами он лучше основного: почтовые клиенты часто
// блокируют картинки в письмах, пока получатель не нажмёт «показать
// изображения», — текст виден всегда.
//
// Шрифты сайта здесь не годятся: в письме их нет и подставить неоткуда.
// Берём то, что есть у всех: Georgia под антикву (она и рисовалась как
// антиква для экрана, то есть говорит о том же, что Literata) и Arial
// под остальное. Стили — строчные: почтовые сервисы вырезают <style>.
// Вёрстка таблицами и атрибутами, а не современным CSS: редактор подписи —
// это WYSIWYG, он режет всё, чего не понимает, а почтовые клиенты
// не знают ни flex, ни grid. Сургучная линейка слева — отдельная ячейка
// с bgcolor, а не border: атрибут bgcolor понимают вообще все, включая
// Outlook, а border-left у ячейки он местами теряет. Высоту эта ячейка
// берёт от соседней сама — на то и таблица.
//
// Приём взят с сайта: поле бланка, отчёркнутое красным. Это единственное
// украшение здесь, всё остальное делает типографика и воздух.
const cell = 'font-size:0;line-height:0'
const sig = `<!doctype html><meta charset="utf-8">
<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse">
<tr>
  <td width="3" bgcolor="${ACC}" style="${cell};width:3px">&nbsp;</td>
  <td width="18" style="${cell}">&nbsp;</td>
  <td style="font-family:Arial,Helvetica,sans-serif;padding:2px 0 3px">

    <table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse"><tr>
      <td style="font-family:Georgia,'Times New Roman',serif;font-weight:bold;
                 font-size:23px;letter-spacing:2px;color:${INK};line-height:1.1">${BRAND}</td>
      <td width="14" style="${cell}">&nbsp;</td>
      <td valign="bottom" style="font-size:10.5px;letter-spacing:1.2px;text-transform:uppercase;
                 padding-bottom:3px;
                 color:${ACC};white-space:nowrap">${TAG}</td>
    </tr></table>

    <div style="height:14px;${cell}">&nbsp;</div>

    <div style="font-size:15px;font-weight:bold;color:${INK};line-height:1.3">Алихан Багишев</div>

    <div style="height:6px;${cell}">&nbsp;</div>

    <div style="font-size:15px;color:${INK};line-height:1.4">
      <a href="tel:${PHONE.replace(/[^+\d]/g, '')}" style="color:${INK};text-decoration:none">${PHONE}</a>
      <span style="color:${LINE}">&nbsp; · &nbsp;</span>
      <a href="https://${DOMAIN}/" style="color:${ACC};text-decoration:none;font-weight:bold">${DOMAIN}</a>
    </div>

    <div style="height:14px;${cell}">&nbsp;</div>

    <table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse"><tr>
      <td width="46" height="3" bgcolor="${ACC}" style="${cell}">&nbsp;</td>
      <td width="413" height="1" bgcolor="${LINE}" style="${cell}">&nbsp;</td>
    </tr></table>

    <div style="height:9px;${cell}">&nbsp;</div>

    <div style="font-size:11.5px;color:${MUTED};line-height:1.5">${SERVICE_LINE}</div>

  </td>
</tr>
</table>
`
writeFileSync(join(out, 'podpis.html'), sig)

// ── Подпись совсем без разметки ───────────────────────────────────────────
//
// Mail.ru не принял ни картинку, ни html-файл: его редактор подписи
// не умеет загружать файлы вообще, он умеет только то, что в него
// вставили или набрали. Поэтому третий вариант — голый текст, который
// копируется и вставляется, и загружать нечего в принципе.
//
// Разделители — средняя точка и длинное тире: они есть в любом шрифте
// и в любой кодировке. Рамок из псевдографики здесь нет нарочно: в моно-
// ширинном шрифте они сойдутся, а в пропорциональном (а подпись показывают
// именно им) развалятся в кривую лесенку.
const plain = [
  `${BRAND} — ${TAG}`,
  'Алихан Багишев',
  '',
  PHONE,
  DOMAIN,
  '',
  SERVICE_LINE,
  '',
].join('\n')
writeFileSync(join(out, 'podpis.txt'), plain)

await browser.close()

// Размеры читаем из самих файлов: записанные руками расходятся с делом
// при первой же правке раскладки, а проверить их некому.
const png = (f) => {
  const b = readFileSync(join(out, f))
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), kb: (b.length / 1024).toFixed(0) }
}
const row = (f, what) => {
  const { w, h, kb } = png(f)
  return `  ${f.padEnd(28)} ${String(w + '×' + h).padEnd(12)} ${what.padEnd(30)} ${kb} КБ`
}
console.log(`
Фирменные файлы собраны в norma-site/brand/

  znak.svg, znak-belyy.svg     вектор       только монограмма
${row('znak.png', 'прозрачный фон')}
${row('logotip.png', 'прозрачный фон')}
${row('logotip-belyy.png', 'для тёмного фона')}
${row('avatar.png', 'аватар, тёмный')}
${row('avatar-svetlyy.png', 'аватар, светлый')}
${row('logotip-kvadrat.png', 'знак с подписью, тёмный')}
${row('logotip-kvadrat-svetlyy.png', 'знак с подписью, светлый')}
${row('oblozhka.png', 'обложка каталога, тёмная')}
${row('oblozhka-svetlaya.png', 'обложка каталога, светлая')}
${row('pochta-shapka.png', 'шапка письма, 600 px по ширине')}
${row('pochta-shapka-600.png', 'она же в одинарном масштабе')}
  logotip.pdf                  вектор       для печати
  podpis.html                  текст        подпись с оформлением: открыть, Ctrl+A, Ctrl+C
  podpis.txt                   текст        подпись совсем без разметки

Шапка скопирована в public/img/ — после заливки сайта она будет доступна
по адресу https://${DOMAIN}/img/pochta-shapka.png и вставляется в подпись
ссылкой, без загрузки файла в почту.

Цвета и контакты взяты из site.ts и global.css — руками здесь не вписано ничего.
`)
