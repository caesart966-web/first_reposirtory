// Лента логотипов СРО-партнёров на главной (PartnerLogos.astro).
//
// Запуск: npm test   (или node scripts/test-logos.mjs [адрес сайта])
//
// Зачем. Лента держится на нескольких условиях, которые ломаются молча:
// сайт собирается, лента едет, а на деле —
//   • знак без подписи: диктор читает «изображение», поисковик не знает, чьё;
//   • повтор набора (он нужен для бесконечной ленты) читается диктором
//     второй раз, если снять с него aria-hidden;
//   • на стыке знаки дёргаются: половина ленты должна быть ровно одним
//     набором с промежутками — так её и сдвигает анимация;
//   • знаки за краем ленты не грузятся (отложенная загрузка считает их
//     невидимыми) и появляются посреди движения;
//   • кнопка «остановить» не останавливает, а при «уменьшить движение»
//     лента всё равно едет.
// Всё это меряется в браузере поведением, а не наличием классов.

import { chromium } from './lib/browser.mjs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
let fails = 0
const ok = (m) => console.log(`  ✓ ${m}`)
const fail = (m) => { fails++; console.log(`  ✗ ${m}`) }
const check = (cond, m, why = '') => (cond ? ok(m) : fail(why ? `${m} — ${why}` : m))

// Сколько знаков должно быть — из partners.ts: номер в реестре и логотип.
const { PARTNERS } = await import('../src/config/partners.ts')
const expected = PARTNERS.filter((p) => p.reg && p.logo).length

console.log('\nЛента логотипов партнёров\n')
const browser = await chromium.launch()

for (const vp of [{ width: 390, height: 844 }, { width: 1440, height: 900 }]) {
  const tag = vp.width < 600 ? 'телефон' : 'компьютер'
  const page = await browser.newPage({ viewport: vp })
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })
  await page.locator('.plogos').scrollIntoViewIfNeeded()
  await page.waitForFunction(() => [...document.querySelectorAll('.plogos img')].every((i) => i.complete), null, { timeout: 10000 }).catch(() => {})

  const r = await page.evaluate(() => {
    const track = document.querySelector('.pl-track')
    const first = [...track.querySelectorAll('li:not(.dup)')]
    const dups = [...track.querySelectorAll('li.dup')]
    const setW = first.reduce((s, li) => s + li.getBoundingClientRect().width, 0)
    const imgs = [...track.querySelectorAll('img')]
    return {
      n: first.length,
      nDup: dups.length,
      alts: first.map((li) => li.querySelector('img')?.getAttribute('alt') || ''),
      dupHidden: dups.every((li) => li.getAttribute('aria-hidden') === 'true' && li.querySelector('img')?.getAttribute('alt') === ''),
      half: track.scrollWidth / 2,
      setW,
      notLoaded: imgs.filter((i) => !(i.complete && i.naturalWidth > 0)).map((i) => i.getAttribute('src')),
      anim: getComputedStyle(track).animationName,
      overflow: document.documentElement.scrollWidth - innerWidth,
    }
  })
  if (tag === 'телефон') {
    check(r.n === expected, `Знаков столько, сколько партнёров с номером и логотипом (${expected})`, `в ленте ${r.n}`)
    check(r.alts.every((a) => a.length > 3), 'У каждого знака подпись — название организации', r.alts.filter((a) => a.length <= 3).length + ' без подписи')
    check(r.nDup === r.n && r.dupHidden, 'Повтор набора скрыт от диктора (aria-hidden, пустые подписи)')
  }
  check(Math.abs(r.half - r.setW) <= 1, `${tag}: половина ленты — ровно один набор, стык без рывка`, `половина ${r.half.toFixed(1)}, набор ${r.setW.toFixed(1)}`)
  check(!r.notLoaded.length, `${tag}: загружены все знаки, и те, что за краем ленты`, r.notLoaded.join(', '))
  check(r.anim === 'pl-run', `${tag}: лента движется`, `animation-name: ${r.anim}`)
  check(r.overflow <= 0, `${tag}: страница не шире экрана`, `шире на ${r.overflow} px`)

  // Кнопка останавливает и запускает снова.
  const state = () => page.evaluate(() => ({
    play: getComputedStyle(document.querySelector('.pl-track')).animationPlayState,
    pressed: document.querySelector('.pl-btn').getAttribute('aria-pressed'),
  }))
  await page.locator('.pl-btn').click()
  const s1 = await state()
  await page.locator('.pl-btn').click()
  const s2 = await state()
  check(s1.play === 'paused' && s1.pressed === 'true' && s2.play === 'running' && s2.pressed === 'false',
    `${tag}: кнопка останавливает ленту и запускает снова`, `после нажатия ${s1.play}/${s1.pressed}, после второго ${s2.play}/${s2.pressed}`)

  // На телефоне кнопка не под столбиком кнопок связи.
  if (tag === 'телефон') {
    const geo = await page.evaluate(() => {
      const b = document.querySelector('.pl-btn').getBoundingClientRect()
      const rail = document.querySelector('.contact-rail')
      return { right: b.right, railLeft: rail ? rail.getBoundingClientRect().left : Infinity }
    })
    check(geo.right < geo.railLeft, 'Кнопка остановки левее столбика кнопок связи', `${Math.round(geo.right)} > ${Math.round(geo.railLeft)}`)
  }
  await page.close()
}

// «Уменьшить движение»: лента стоит, повтора нет, ряд листается.
{
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })
  const r = await page.evaluate(() => {
    const track = document.querySelector('.pl-track')
    const view = document.querySelector('.pl-view')
    return {
      anim: getComputedStyle(track).animationName,
      dupShown: [...track.querySelectorAll('li.dup')].some((li) => getComputedStyle(li).display !== 'none'),
      btn: getComputedStyle(document.querySelector('.pl-btn')).display,
      scrollable: view.scrollWidth > view.clientWidth && getComputedStyle(view).overflowX === 'auto',
    }
  })
  check(r.anim === 'none' && !r.dupShown && r.btn === 'none', 'При «уменьшить движение» лента стоит, повтора и кнопки нет', JSON.stringify(r))
  check(r.scrollable, 'При «уменьшить движение» ряд листается — все знаки достижимы')
  await ctx.close()
}

await browser.close()
if (fails) {
  console.log(`\n✗ Лента логотипов: ${fails}.`)
  process.exit(1)
}
console.log('\n✓ Лента логотипов в порядке.')
