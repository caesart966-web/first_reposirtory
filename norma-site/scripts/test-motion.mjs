// Плавность: переходы между страницами и прокрутка без рывков.
//
// ЧТО СТЕРЕЖЁТ.
// 1. Переход между страницами (23.10.2026). Новая страница проступает
//    поверх прежней (@view-transition в global.css), шапка стоит на месте
//    отдельным слоем. Проверяется поведением: после щелчка по ссылке
//    в меню новая страница получает событие pagereveal с переходом,
//    а при «уменьшить движение» — без него.
// 2. Слой фотографии в шапке «в два этажа». Снаружи (.head-photo) —
//    масштаб «дыхания» и непрозрачность, внутри (::before) — снимок
//    с фильтром и маской. Пока фильтр стоял на анимируемом слое, браузер
//    пересчитывал его каждый кадр: на «Стоимости» при прокрутке терялось
//    6–22 кадра из ~110 на 1280 px, в два этажа — 0–1. Проверка смотрит
//    на устройство слоя (фильтр не на том элементе, что движется) и меряет
//    потерянные кадры при прокрутке шагами по трети экрана.
//
// Запуск: node scripts/test-motion.mjs [адрес]

import { chromium } from './lib/browser.mjs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const MAX_DROPPED = 4
let failed = 0
const ok = (m) => console.log(`  ✓ ${m}`)
const fail = (m) => { failed++; console.log(`  ✗ ${m}`) }
const check = (cond, m, why = '') => (cond ? ok(m) : fail(why ? `${m} — ${why}` : m))

const browser = await chromium.launch()

console.log('Переход между страницами')
for (const motion of ['no-preference', 'reduce']) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: motion })
  await ctx.addInitScript(() => {
    addEventListener('pagereveal', (e) => { window.__vt = Boolean(e.viewTransition) })
  })
  const page = await ctx.newPage()
  await page.goto(BASE + '/stoimost/', { waitUntil: 'networkidle' })
  const names = await page.evaluate(() =>
    [...document.querySelectorAll('*')].map((el) => getComputedStyle(el).viewTransitionName).filter((n) => n && n !== 'none' && n !== 'root'), // root — у самого html, он есть всегда
  )
  await page.click('.site-header .nav a[href$="/kontakty/"]')
  await page.waitForURL('**/kontakty/')
  await page.waitForTimeout(600)
  const vt = await page.evaluate(() => window.__vt)
  if (motion === 'no-preference') {
    check(vt === true, 'новая страница проступает поверх прежней (view transition)', `pagereveal: ${vt}`)
    check(names.length === 1 && names[0] === 'site-header', 'отдельный слой при переходе — только шапка', JSON.stringify(names))
  } else {
    check(vt === false, 'при «уменьшить движение» перехода нет', `pagereveal: ${vt}`)
  }
  await ctx.close()
}

console.log('Фотография в шапке')
for (const path of ['/stoimost/', '/uslugi/nrs/']) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } })
  const page = await ctx.newPage()
  await page.goto(BASE + path, { waitUntil: 'networkidle' })
  const layer = await page.evaluate(() => {
    const el = document.querySelector('.page-head .head-photo')
    if (!el) return null
    const out = getComputedStyle(el)
    const inn = getComputedStyle(el, '::before')
    return {
      animated: out.animationName !== 'none',
      outerFilter: out.filter,
      outerMask: out.maskImage || out.webkitMaskImage,
      innerFilter: inn.filter,
      innerImage: inn.backgroundImage,
    }
  })
  if (!layer) { fail(`${path}: слоя .head-photo нет`); await ctx.close(); continue }
  check(
    layer.animated && layer.outerFilter === 'none' && (!layer.outerMask || layer.outerMask === 'none'),
    `${path}: движется внешний слой, фильтра и маски на нём нет`,
    JSON.stringify(layer),
  )
  check(layer.innerFilter !== 'none' && layer.innerImage.includes('url('), `${path}: снимок с фильтром — во внутреннем слое`, JSON.stringify(layer))

  await page.waitForTimeout(400)
  const dropped = await page.evaluate(async () => {
    const times = []
    let stop = false
    const tick = (t) => { times.push(t); if (!stop) requestAnimationFrame(tick) }
    requestAnimationFrame(tick)
    const step = Math.round(innerHeight / 3)
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      scrollTo(0, y)
      await new Promise((r) => setTimeout(r, 60))
    }
    stop = true
    let n = 0
    for (let i = 1; i < times.length; i++) if (times[i] - times[i - 1] > 24) n++
    return n
  })
  check(dropped <= MAX_DROPPED, `${path}: прокрутка без рывков (потеряно кадров: ${dropped}, допуск ${MAX_DROPPED})`)
  await ctx.close()
}

await browser.close()
if (failed) {
  console.log(`\n✗ Плавность: ${failed} замечаний.`)
  process.exit(1)
}
console.log('\n✓ Переходы между страницами и прокрутка без рывков.')
