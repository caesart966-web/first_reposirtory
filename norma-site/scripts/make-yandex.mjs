// МАТЕРИАЛЫ ДЛЯ ЯНДЕКС БИЗНЕСА: ролик для раздела «Видео» и картинки
// к услугам — для раздела «Фото → Услуги» и к позициям в «Товарах и услугах».
//
// Запуск: npm run yandex        → release/yandex/ (в git не попадает)
//
// ЗАЧЕМ СКРИПТ, А НЕ ГОТОВЫЕ ФАЙЛЫ. В ролике и на картинках — условия
// вступления, подарки, срок выписки, пороги и статьи закона. Всё это
// берётся из тех же конфигов, что и сайт (offer.ts, facts.ts, services.ts),
// поэтому поменялось условие — пересобрали, и Яндекс показывает то же, что
// сайт. Нарисованный руками ролик разошёлся бы с сайтом при первой правке,
// и заметить это было бы некому — ровно как с логотипом (make-brand.mjs).
//
// ЧТО ТРЕБУЕТ ЯНДЕКС (сентябрь 2026; справку Яндекса из среды сборки
// не открыть, взято из поиска). Видео: MP4, 5–60 секунд, до 100 МБ, от 360p,
// лучше 1080p. Фото: JPG или PNG, до 10 МБ, от 320×240 до 5000×5000.
// Модерация отклоняет стоковые снимки, картинки из интернета, коллажи,
// водяные знаки и рекламные баннеры; в публикациях — телефоны, ссылки
// и слова ЦЕЛИКОМ ПРОПИСНЫМИ. Отсюда правила:
//   · ни одной фотографии с сайта: кадры с Фемидой и подписанием похожи
//     на сток (README, раздел 9), модерация их и отклонит — всё нарисовано
//     из фирменного оформления: бумага, антиква, сургуч, значки заказчика;
//   · ни телефона, ни адреса сайта, ни логотипа поверх картинок услуг
//     (знак в углу модерация сочтёт водяным знаком) — всё это в профиле есть;
//   · подписи — обычным регистром, капс только у аббревиатур (СРО, НРС);
//   · печати «Сверено» нет: она значит «сверено с законом», а в ролике
//     рядом стоят условия СРО и подарки — не нормы закона (CLAUDE.md).
//
// ffmpeg: берётся из переменной FFMPEG или из PATH. Без него картинки
// собираются, а ролик — нет (скрипт скажет об этом и завершится с ошибкой).
// Если ffmpeg не установлен: pip install imageio-ffmpeg, затем
// FFMPEG=$(python3 -c "import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())").
//
// Нужен Node 22.6+: конфиги сайта — TypeScript и подключаются напрямую
// (--experimental-strip-types, флаг стоит в package.json).

import { spawn, spawnSync } from 'node:child_process'
import { mkdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const out = join(root, 'release/yandex')
mkdirSync(out, { recursive: true })

const { OFFER, GIFTS, GIFT_TAG } = await import('../src/config/offer.ts')
const { TERMS, LAW, THRESHOLD_BUILD } = await import('../src/config/facts.ts')
const { SERVICES } = await import('../src/config/services.ts')

// ── Цвета и шрифты — из стилей сайта ──────────────────────────────────────
const css = readFileSync(join(root, 'src/styles/global.css'), 'utf8')
const color = (name) => {
  const m = css.match(new RegExp(`${name}:\\s*(#[0-9A-Fa-f]{6})`))
  if (!m) throw new Error(`в global.css нет ${name}`)
  return m[1]
}
const C = {
  paper: color('--paper-2'),
  card: color('--card'),
  ink: color('--ink'),
  muted: color('--muted'),
  line: color('--line'),
  acc: color('--acc'),
  accDeep: color('--acc-deep'),
  accSoft: color('--acc-soft'),
  good: color('--good'),
}

// Те же @font-face, что у сайта (fonts.css), с теми же диапазонами —
// иначе «₽» и цифры взялись бы из запасного шрифта, как уже было на сайте.
const fontsCss = readFileSync(join(root, 'src/styles/fonts.css'), 'utf8')
const FACES = [...fontsCss.matchAll(/@font-face\s*{([^}]+)}/g)]
  .map((m) => m[1])
  .map((b) =>
    b.replace(/url\('\/fonts\/([^']+)'\)/g, (_, f) =>
      `url(data:font/woff2;base64,${readFileSync(join(root, 'public/fonts', f)).toString('base64')})`,
    ),
  )
  // На сайте стоит font-display: optional — страница не ждёт шрифт. Здесь
  // наоборот: кадр снимается один раз, и запасной шрифт в нём остался бы
  // навсегда (так и вышло в первой сборке: Georgia и DejaVu вместо своих).
  .map((b) => b.replace(/font-display:\s*\w+/, 'font-display: block'))
  .map((b) => `@font-face {${b}}`)
  .join('\n')
if (!FACES.includes('U+20BD')) throw new Error('в fonts.css не нашёлся шрифт со знаком ₽')

const HEAD = "'Literata Variable', Georgia, serif"
const BODY = "'Golos Text Variable', system-ui, sans-serif"

// ── Значки — те же контуры, что на сайте ──────────────────────────────────
const dirSrc = readFileSync(join(root, 'src/components/DirIcon.astro'), 'utf8')
const DIR = Object.fromEntries([...dirSrc.matchAll(/"(builder|design|survey)":\s*"([^"]+)"/g)].map((m) => [m[1], m[2]]))
if (Object.keys(DIR).length !== 3) throw new Error('в DirIcon.astro ожидалось три контура')

const giftSrc = readFileSync(join(root, 'src/components/GiftIcon.astro'), 'utf8')
const GIFT_ICON = Object.fromEntries(
  [...giftSrc.matchAll(/\b(site|year|cashback):\s*((?:'[^']*'\s*\+?\s*)+)/g)].map((m) => [
    m[1],
    [...m[2].matchAll(/'([^']*)'/g)].map((q) => q[1]).join(''),
  ]),
)
if (Object.keys(GIFT_ICON).length !== 3) throw new Error('в GiftIcon.astro ожидалось три значка')

const iconSrc = readFileSync(join(root, 'src/components/Icon.astro'), 'utf8')
const ICON = (name) => {
  const m = iconSrc.match(new RegExp(`\\b${name}:\\s*'([^']+)'`))
  if (!m) throw new Error(`в Icon.astro нет значка ${name}`)
  return m[1]
}

const markSrc = readFileSync(join(root, 'src/components/LogoMark.astro'), 'utf8')
const MARK = [...markSrc.matchAll(/<path\s+d="([^"]+)"|d="([^"]+)"/g)].map((m) => m[1] || m[2]).filter(Boolean)
if (MARK.length !== 4) throw new Error(`в LogoMark.astro ожидалось 4 контура, найдено ${MARK.length}`)
const siteSrc = readFileSync(join(root, 'src/config/site.ts'), 'utf8')
const BRAND = (siteSrc.match(/brand:\s*'([^']+)'/) || [])[1]
const TAG = (siteSrc.match(/brandTag:\s*'([^']+)'/) || [])[1]
if (!BRAND || !TAG) throw new Error('в site.ts не нашлись brand и brandTag')

const svgDir = (name, size) =>
  `<svg viewBox="0 0 200 200" width="${size}" height="${size}" fill="currentColor"><path d="${DIR[name]}"/></svg>`
const svgGift = (name, size) =>
  `<svg viewBox="29 13 264 244" width="${size}" height="${Math.round((size * 244) / 264)}" fill="none" stroke="currentColor" stroke-width="8" stroke-linecap="round" stroke-linejoin="round">${GIFT_ICON[name]}</svg>`
// Значки из Icon.astro нарисованы для 20 px; на большой картинке линию
// тоньше, чтобы вес совпадал со значками заказчика.
const svgLine = (name, size) =>
  `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round">${ICON(name)}</svg>`
const svgMark = (size, fill = C.acc) =>
  `<svg viewBox="0 0 100 100" width="${size}" height="${size}" fill="${fill}">${MARK.map((d) => `<path d="${d}"/>`).join('')}</svg>`
const check = (size) =>
  `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="${C.good}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.5l5 5L20 6.5"/></svg>`

// Гильош — та же розетка, что на первом экране сайта (Hero.astro): окружности,
// расставленные по кругу. Фактура листа вместо фотографии.
const rosette = (size, opacity) => {
  const rings = []
  for (let i = 0; i < 36; i++) {
    const a = (i / 36) * Math.PI * 2
    rings.push(`<circle cx="${(Math.cos(a) * 92).toFixed(2)}" cy="${(Math.sin(a) * 92).toFixed(2)}" r="150"/>`)
  }
  return `<svg viewBox="-260 -260 520 520" width="${size}" height="${size}" style="opacity:${opacity}" fill="none" stroke="${C.acc}" stroke-width="0.7">${rings.join('')}</svg>`
}

// Чип со статьёй — как на сайте: только у того, что написано в законе.
const chip = (text, fs) =>
  `<span style="display:inline-flex;align-items:center;gap:.45em;white-space:nowrap;border:1.5px solid ${C.acc};color:${C.accDeep};border-radius:6px;padding:.28em .6em;font:600 ${fs}px/1 ${BODY}">§ ${text}</span>`

const page = (w, h, style, body) => `<!doctype html><html lang="ru"><meta charset="utf-8"><style>
${FACES}
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: ${w}px; height: ${h}px; overflow: hidden; }
body { background: ${C.paper}; color: ${C.ink}; font-family: ${BODY}; -webkit-font-smoothing: antialiased; }
.grain { position: absolute; inset: 0; opacity: .5; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 .45 0 0 0 0 .38 0 0 0 0 .28 0 0 0 .06 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }
.light { position: absolute; inset: 0; background: radial-gradient(120% 90% at 85% 0%, rgba(255,255,255,.85), rgba(255,255,255,0) 60%), linear-gradient(180deg, rgba(0,0,0,0) 70%, rgba(80,60,30,.05)); }
${style}
</style><body>${body}</body></html>`

const browser = await chromium.launch()
const made = []

// Все начертания загружаются до первого кадра: иначе браузер нарисует
// запасным шрифтом то, что успеет, и снимок это запомнит.
const fontsLoaded = (p) =>
  p.evaluate(async () => {
    await Promise.all([...document.fonts].map((f) => f.load().catch(() => null)))
    await document.fonts.ready
    return [...document.fonts].filter((f) => f.status !== 'loaded').length
  })

// Короткие слова не остаются в конце строки: «в / СРО» читается плохо.
// И тире не начинает строку: оно держится за слово перед ним.
const nbsp = (t) =>
  t.replace(/(^|[\s(«])(в|и|с|к|о|у|а|на|по|за|из|от|до|для|не|ни|без|при)\s/gi, '$1$2\u00a0').replace(/ —/g, '\u00a0—')

// ═════════════════════════ КАРТИНКИ К УСЛУГАМ ══════════════════════════════
// 1600 × 1200 (4:3). Содержимое держится в средней полосе 1200 × 900: так
// оно переживает и обрезку в квадрат в списке услуг, и в 16:9 в галерее.
const W = 1600
const H = 1200

// Статьи — только у утверждений о законе, как на сайте.
const LAW_OF = {
  'sro-stroiteley': LAW.build,
  'sro-proektirovshchikov': LAW.design,
  'sro-izyskateley': LAW.design,
  nrs: LAW.twoSpecialists,
}

const serviceIcon = (s) =>
  s.dirIcon ? svgDir(s.dirIcon, 230) : s.slug === 'marketing' ? svgGift('site', 230) : svgLine(s.icon, 210)

// Первая фраза описания услуги из services.ts: целиком описание на картинке
// мельчит, а в миниатюре Яндекса и вовсе превращается в серую полосу.
const firstSentence = (t) => t.split(/(?<=[.!?])\s+/)[0]

const cardStyle = `
.rose { position: absolute; }
.rose.a { left: -330px; top: -360px; }
.rose.b { right: -330px; bottom: -380px; transform: rotate(12deg); }
.box { position: absolute; left: 200px; top: 150px; width: 1200px; height: 900px; display: grid; justify-items: center; align-content: center; gap: 40px; text-align: center; }
.ic { color: ${C.acc}; display: grid; place-items: center; width: 280px; height: 280px; border-radius: 24px; background: ${C.card}; box-shadow: 0 34px 70px -44px rgba(22,19,15,.5); border: 1px solid ${C.line}; }
.tx { display: grid; gap: 24px; justify-items: center; }
h1 { font: 700 84px/1.06 ${HEAD}; letter-spacing: -.015em; text-wrap: balance; max-width: 1150px; }
p { font: 400 40px/1.4 ${BODY}; color: ${C.muted}; text-wrap: balance; max-width: 1060px; }
`

for (const s of SERVICES) {
  const law = LAW_OF[s.slug]
  const html = page(
    W,
    H,
    cardStyle,
    `<div class="light"></div><div class="grain"></div>
     <div class="rose a">${rosette(760, 0.12)}</div>
     <div class="rose b">${rosette(760, 0.12)}</div>
     <div class="box">
       <div class="ic">${serviceIcon(s)}</div>
       <div class="tx">
         <h1>${nbsp(s.title)}</h1>
         <p>${nbsp(firstSentence(s.excerpt))}</p>
         ${law ? chip(law, 30) : ''}
       </div>
     </div>`,
  )
  const p = await browser.newPage({ viewport: { width: W, height: H } })
  await p.setContent(html, { waitUntil: 'load' })
  const missed = await fontsLoaded(p)
  if (missed) throw new Error(`«${s.title}»: не загрузилось начертаний — ${missed}`)
  // Текст не имеет права вылезти из средней полосы: иначе его срежет
  // квадратная миниатюра в списке услуг.
  const over = await p.evaluate(() => {
    const b = document.querySelector('.box').getBoundingClientRect()
    const kids = [...document.querySelectorAll('.box > *')].map((e) => e.getBoundingClientRect())
    return kids.some((k) => k.top < b.top || k.bottom > b.bottom)
  })
  if (over) throw new Error(`«${s.title}»: текст не помещается в безопасную полосу 1200×900`)
  const file = join(out, `usluga-${s.slug}.jpg`)
  await p.screenshot({ path: file, type: 'jpeg', quality: 92 })
  await p.close()
  made.push(file)
}

// ═════════════════════════════ РОЛИК ═══════════════════════════════════════
// 1920 × 1080, 30 кадров в секунду, ~42 секунды. Сцены — HTML с CSS-анимацией;
// кадр снимается после того, как все анимации поставлены на нужное время
// (document.getAnimations → currentTime): так ролик собирается одинаково
// при любой скорости машины, без пропущенных кадров.
const VW = 1920
const VH = 1080
const FPS = 30

// [начало, конец] каждой сцены в секундах. Сцены идут встык, а не внахлёст:
// уходящая гаснет за полсекунды до своего конца, новая проявляется после.
// Внахлёст первая сборка давала двойную экспозицию — на переходе читались
// два заголовка сразу, один сквозь другой.
const T = {
  logo: [0, 4.4],
  head: [4.4, 10.2],
  dirs: [10.2, 17.6],
  offer: [17.6, 25],
  gift: [25, 32.2],
  term: [32.2, 37.4],
  end: [37.4, 42.5],
}
const DURATION = 42.5

const scene = (id, inner) => {
  const [a, b] = T[id]
  const last = id === 'end'
  return `<section class="scene" style="animation: ${last ? `in .6s ${a}s both` : `in .6s ${a}s both, out .5s ${b - 0.5}s forwards`}">${inner}</section>`
}
// Появление элемента внутри сцены: задержка от начала сцены.
const at = (id, d, anim = 'up', dur = 0.7) => `animation: ${anim} ${dur}s ${(T[id][0] + d).toFixed(2)}s both`

const videoStyle = `
@keyframes in { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }
@keyframes out { from { opacity: 1; } to { opacity: 0; transform: translateY(-14px); } }
@keyframes up { from { opacity: 0; transform: translateY(28px); } to { opacity: 1; transform: none; } }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes pop { 0% { opacity: 0; transform: scale(.82); } 70% { opacity: 1; transform: scale(1.03); } 100% { opacity: 1; transform: scale(1); } }
@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(14deg); } }
.rose { position: absolute; left: -330px; top: 120px; animation: spin ${DURATION}s linear both; }
.scene { position: absolute; inset: 0; display: grid; place-items: center; }
.wrap { width: 1560px; }
.lbl { font: 600 30px/1 ${BODY}; color: ${C.accDeep}; letter-spacing: .01em; }
.lbl::before { content: ''; display: inline-block; width: 44px; height: 3px; background: ${C.acc}; vertical-align: middle; margin: -4px 18px 0 0; }
em { font-style: normal; color: ${C.accDeep}; }
/* сцена 1 — знак */
.logo { display: grid; justify-items: center; gap: 30px; }
.logo .name { font: 800 132px/1 ${HEAD}; letter-spacing: .09em; }
.logo .tag { font: 400 46px/1 ${BODY}; color: ${C.muted}; }
.logo .bar { width: 420px; height: 3px; background: ${C.acc}; transform-origin: left; }
/* сцена 2 — заголовок */
.h { font: 700 132px/1.04 ${HEAD}; letter-spacing: -.02em; }
.lead { margin-top: 44px; font: 400 46px/1.4 ${BODY}; color: ${C.muted}; max-width: 1400px; }
/* сцена 3 — направления */
.dirs { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 36px; margin-top: 48px; }
.dir { background: ${C.card}; border: 1px solid ${C.line}; border-radius: 14px; padding: 44px 38px 40px; display: grid; gap: 22px; align-content: start; box-shadow: 0 30px 60px -44px rgba(22,19,15,.45); }
.dir .i { color: ${C.acc}; }
.dir h3 { font: 700 42px/1.12 ${HEAD}; }
.dir p { font: 400 30px/1.45 ${BODY}; color: ${C.muted}; }
.st { font: 700 84px/1.08 ${HEAD}; letter-spacing: -.015em; margin-top: 26px; }
/* сцена 4 — условия */
.offer { display: grid; gap: 0; }
/* по столбцам: условия читаются сверху вниз, как в карточке на сайте */
.card ul.two { grid-template-columns: 1fr 1fr; grid-template-rows: repeat(3, auto); grid-auto-flow: column; column-gap: 60px; row-gap: 28px; }
.card { background: ${C.card}; border: 1px solid ${C.line}; border-radius: 14px; padding: 48px 50px; box-shadow: 0 30px 70px -44px rgba(22,19,15,.5); position: relative; }
.card::before { content: ''; position: absolute; left: -1px; right: -1px; top: -1px; height: 6px; background: ${C.acc}; border-radius: 14px 14px 0 0; }
.card ul { list-style: none; display: grid; gap: 26px; }
.offer .card { margin-top: 44px; }
.card li { display: grid; grid-template-columns: auto 1fr; gap: 20px; align-items: center; font: 500 40px/1.2 ${BODY}; }
.note { margin-top: 34px; font: 400 28px/1.4 ${BODY}; color: ${C.muted}; }
/* сцена 5 — подарок */
.gift { position: relative; background: ${C.card}; border: 1.5px solid ${C.line}; border-radius: 16px; padding: 70px 60px 34px; box-shadow: 0 30px 70px -44px rgba(22,19,15,.5); width: 1280px; justify-self: center; }
.gift::before { content: ''; position: absolute; inset: 9px; border: 1.5px solid color-mix(in srgb, ${C.acc} 26%, transparent); border-radius: 10px; }
.gtag { position: absolute; top: 0; left: 48px; transform: translateY(-50%); background: ${C.acc}; color: #fff; font: 600 30px/1 ${BODY}; padding: 14px 26px; border-radius: 999px; }
.grow { display: grid; grid-template-columns: 150px 1fr; gap: 40px; align-items: center; padding: 12px 0; }
.grow .i { color: ${C.acc}; display: grid; place-items: center; }
.grow b { display: block; font: 700 56px/1.15 ${BODY}; }
.grow span { display: block; font: 400 32px/1.4 ${BODY}; color: ${C.muted}; margin-top: 6px; }
.or { text-align: center; font: italic 400 36px/1 ${HEAD}; color: ${C.muted}; padding: 6px 0;
  background: linear-gradient(${C.line}, ${C.line}) left center / calc(50% - 50px) 2px no-repeat, linear-gradient(${C.line}, ${C.line}) right center / calc(50% - 50px) 2px no-repeat; }
/* сцена 6 — срок */
.term { display: grid; grid-template-columns: auto 1fr; gap: 70px; align-items: center; }
.big { font: 700 220px/1 ${HEAD}; color: ${C.accDeep}; letter-spacing: -.03em; white-space: nowrap; }
.term h3 { font: 700 48px/1.15 ${HEAD}; text-wrap: balance; }
.term p { font: 400 34px/1.45 ${BODY}; color: ${C.muted}; margin-top: 22px; }
/* сцена 7 — финал */
.fin { display: grid; justify-items: center; gap: 26px; text-align: center; }
.fin .row { display: flex; align-items: center; gap: 30px; }
.fin .name { font: 800 96px/1 ${HEAD}; letter-spacing: .09em; }
.fin .tag { font: 400 38px/1 ${BODY}; color: ${C.muted}; margin-top: 12px; }
.fin .say { margin-top: 44px; font: 700 70px/1.1 ${HEAD}; }
.fin .sub { font: 400 38px/1.4 ${BODY}; color: ${C.muted}; }
`

const [build, design, survey] = ['sro-stroiteley', 'sro-proektirovshchikov', 'sro-izyskateley'].map((slug) =>
  SERVICES.find((s) => s.slug === slug),
)
if (!build || !design || !survey) throw new Error('в services.ts нет одной из трёх услуг СРО')

const videoBody = `
<div class="light"></div><div class="grain"></div>
<div class="rose">${rosette(1300, 0.1)}</div>

${scene(
  'logo',
  `<div class="logo">
    <div style="${at('logo', 0.1, 'pop', 0.8)}">${svgMark(210)}</div>
    <div class="name" style="${at('logo', 0.6)}">${BRAND}</div>
    <div class="bar" style="${at('logo', 1.0, 'grow', 0.8)}"></div>
    <div class="tag" style="${at('logo', 1.2)}">${TAG}</div>
  </div>`,
)}

${scene(
  'head',
  `<div class="wrap">
    <div class="lbl" style="${at('head', 0.1, 'fade', 0.6)}">по всей России</div>
    <div class="h" style="margin-top:40px;${at('head', 0.25)}">Вступление в <em>СРО</em></div>
    <div class="h" style="${at('head', 0.5)}">без устаревших норм</div>
    <p class="lead" style="${at('head', 1.1)}">${nbsp('Строителям, проектировщикам и изыскателям.')}<br>${nbsp('Если членство вам не нужно, скажу об этом до оплаты и покажу норму.')}</p>
  </div>`,
)}

${scene(
  'dirs',
  `<div class="wrap">
    <div class="lbl" style="${at('dirs', 0.1, 'fade', 0.6)}">Три направления</div>
    <div class="st" style="margin-top:22px;${at('dirs', 0.2)}">Кому нужна <em>СРО</em></div>
    <div class="dirs">
      ${[
        [build, 'builder', `Если обязательства по прямому договору больше ${THRESHOLD_BUILD}. СРО — вашего субъекта РФ.`, LAW.build],
        [design, 'design', 'При любой сумме прямого договора. Регион не важен: СРО — любого субъекта.', LAW.design],
        [survey, 'survey', 'При любой сумме прямого договора. Регион не важен: СРО — любого субъекта.', LAW.design],
      ]
        .map(
          ([s, icon, note, law], i) => `<div class="dir" style="${at('dirs', 0.45 + i * 0.35)}">
            <div class="i">${svgDir(icon, 140)}</div>
            <h3>${s.short}</h3>
            <p>${nbsp(note)}</p>
            <div>${chip(law, 22)}</div>
          </div>`,
        )
        .join('')}
    </div>
  </div>`,
)}

${scene(
  'offer',
  `<div class="wrap offer">
    <div class="lbl" style="${at('offer', 0.1, 'fade', 0.6)}">Условия вступления</div>
    <div class="st" style="margin-top:22px;${at('offer', 0.3)}">Первый год — <em>только обязательные взносы</em></div>
    <div class="card" style="${at('offer', 0.5)}">
      <ul class="two">
        ${OFFER.map((o, i) => `<li style="${at('offer', 0.8 + i * 0.3)}">${check(40)}<span>${o.short}</span></li>`).join('')}
      </ul>
    </div>
    <p class="note" style="${at('offer', 2.4, 'fade', 0.8)}">${nbsp('Точный набор условий зависит от подобранной СРО — назову его до подачи документов.')}</p>
  </div>`,
)}

${scene(
  'gift',
  `<div class="wrap" style="display:grid">
    <div class="gift" style="${at('gift', 0.1)}">
      <span class="gtag" style="${at('gift', 0.4, 'pop', 0.6)}">${GIFT_TAG}</span>
      ${GIFTS.map(
        (g, i) => `${i ? `<div class="or" style="${at('gift', 0.55 + i * 0.55, 'fade', 0.5)}">или</div>` : ''}
        <div class="grow" style="${at('gift', 0.6 + i * 0.55)}">
          <div class="i">${svgGift(g.id, 130)}</div>
          <div><b>${g.t}</b>${g.d ? `<span>${nbsp(g.d)}</span>` : ''}</div>
        </div>`,
      ).join('')}
    </div>
  </div>`,
)}

${scene(
  'term',
  `<div class="wrap term">
    <div class="big" style="${at('term', 0.15, 'pop', 0.8)}">${TERMS.extract}</div>
    <div>
      <h3 style="${at('term', 0.5)}">${nbsp('обычно от подачи до выписки из реестра')}</h3>
      <p style="${at('term', 0.9)}">${nbsp(`Решение о приёме принимает СРО: по закону у неё на это ${TERMS.law}.`)}</p>
      <div style="margin-top:26px;${at('term', 1.2, 'fade', 0.6)}">${chip(LAW.term, 26)}</div>
    </div>
  </div>`,
)}

${scene(
  'end',
  `<div class="fin">
    <div class="row" style="${at('end', 0.1, 'pop', 0.8)}">
      ${svgMark(150)}
      <div style="text-align:left"><div class="name">${BRAND}</div><div class="tag">${TAG}</div></div>
    </div>
    <div class="say" style="${at('end', 0.7)}">Консультация — бесплатно</div>
    <div class="sub" style="${at('end', 1.0)}">Если СРО вам не нужна, так и скажу.</div>
  </div>`,
)}
`

{
  const p = await browser.newPage({ viewport: { width: VW, height: VH } })
  await p.setContent(page(VW, VH, videoStyle, videoBody), { waitUntil: 'load' })
  const missed = await fontsLoaded(p)
  if (missed) throw new Error(`ролик: не загрузилось начертаний — ${missed}`)
  await p.evaluate(() => document.getAnimations().forEach((a) => a.pause()))
  const seek = (ms) => p.evaluate((t) => document.getAnimations().forEach((a) => (a.currentTime = t)), ms)

  // Проверка отдельных кадров без сборки ролика: YX_FRAMES="2.5,7,13".
  if (process.env.YX_FRAMES) {
    for (const sec of process.env.YX_FRAMES.split(',').map(Number)) {
      await seek(sec * 1000)
      const f = join(out, `kadr-${String(sec).replace('.', '_')}.jpg`)
      await p.screenshot({ path: f, type: 'jpeg', quality: 90 })
      made.push(f)
    }
    await browser.close()
    console.log(made.filter((f) => f.includes('kadr-')).map((f) => '  ' + f.replace(root + '/', '')).join('\n'))
    process.exit(0)
  }

  // Обложка ролика: Яндекс даёт заменить её после модерации.
  await seek(7000)
  const cover = join(out, 'video-oblozhka.jpg')
  await p.screenshot({ path: cover, type: 'jpeg', quality: 92 })
  made.push(cover)

  const ffmpeg = process.env.FFMPEG || 'ffmpeg'
  const probe = spawnSync(ffmpeg, ['-version'], { stdio: 'ignore' })
  if (probe.error || probe.status !== 0) {
    await browser.close()
    console.log(made.map((f) => '  ' + f.replace(root + '/', '')).join('\n'))
    console.error('✗ Ролик не собран: нет ffmpeg (см. шапку скрипта). Картинки готовы.')
    process.exit(1)
  }

  const video = join(out, 'video-norma.mp4')
  const enc = spawn(
    ffmpeg,
    ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', video],
    { stdio: ['pipe', 'inherit', 'inherit'] },
  )
  const frames = Math.round(DURATION * FPS)
  for (let i = 0; i < frames; i++) {
    await seek((i / FPS) * 1000)
    const buf = await p.screenshot({ type: 'png' })
    if (!enc.stdin.write(buf)) await new Promise((r) => enc.stdin.once('drain', r))
  }
  enc.stdin.end()
  const code = await new Promise((r) => enc.on('close', r))
  if (code !== 0) throw new Error(`ffmpeg завершился с кодом ${code}`)
  const mb = statSync(video).size / 1024 / 1024
  if (mb > 100) throw new Error(`ролик ${mb.toFixed(1)} МБ — Яндекс принимает до 100 МБ`)
  made.push(video)
  console.log(`✓ Ролик: ${DURATION} с, ${VW}×${VH}, ${FPS} к/с, ${mb.toFixed(1)} МБ`)
}

await browser.close()
console.log(`✓ Готово, ${made.length} файлов в release/yandex/:`)
console.log(made.map((f) => '  ' + f.replace(root + '/', '')).join('\n'))
