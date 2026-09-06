// Проверяет, что текст первого экрана читается поверх фоновой фотографии.
//
// Зачем отдельная проверка. Обычные инструменты доступности — и наш
// scripts/test-contrast.mjs тоже — считают контраст по цвету фона из стилей.
// Под текстом первого экрана не цвет, а фотография: в стилях там белая
// бумага, а на экране бронзовая статуя. Расчёт даёт «всё отлично», а на
// телефоне абзац лежит на бронзе и не читается.
//
// Такая проверка на этом сайте уже была — когда на первом экране стояло
// видео с картой. Она поймала строку «2 минуты · 4 вопроса» с контрастом
// 3.38:1 при норме 4.5. Видео убрали, проверку удалили; появилась
// фотография — проверка вернулась.
//
// Как работает: делает буквы прозрачными (но НЕ прячет их — иначе исчезла
// бы и тень, если её когда-нибудь добавят), снимает пиксели ровно под
// каждой строкой, берёт 5% самых светлых и самых тёмных и считает контраст
// к настоящему цвету текста. Худший случай и есть ответ.
//
// Запуск: node scripts/test-hero-photo.mjs [адрес]

import { chromium } from 'playwright'
import { PNG } from 'pngjs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const MIN = 4.5
const MIN_BIG = 3 // крупный текст: от 24px, либо от 18.66px полужирным

const TEXTS = ['.geo', '.page-title', '.hero-lead', '.note', '.verify p', '.stat .v', '.stat .d']

const SCREENS = [
  [1280, 1400, 'компьютер'],
  [820, 1500, 'планшет'],
  [390, 1600, 'телефон'],
]

const lum = (r, g, b) => {
  const f = (v) => {
    v /= 255
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}
const contrast = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)

const browser = await chromium.launch()
let failed = 0
let checked = 0
let hasPhoto = true

for (const [width, height, screen] of SCREENS) {
  const ctx = await browser.newContext({ viewport: { width, height } })
  const page = await ctx.newPage()
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })

  if (!(await page.$('.hero .photo'))) {
    hasPhoto = false
    await ctx.close()
    break
  }

  // Где лежит текст, какого он цвета и насколько крупный.
  const areas = await page.evaluate((sels) => {
    const toL = (css) => {
      const [r, g, b] = css.match(/\d+(\.\d+)?/g).map(Number)
      const f = (v) => {
        v /= 255
        return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
      }
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    }
    const out = []
    for (const sel of sels) {
      const el = document.querySelector(`.hero ${sel}`)
      if (!el) continue
      const r = el.getBoundingClientRect()
      const cs = getComputedStyle(el)
      const size = parseFloat(cs.fontSize)
      const bold = parseInt(cs.fontWeight, 10) >= 700
      out.push({
        sel,
        x: Math.round(r.x),
        y: Math.round(r.y),
        w: Math.round(r.width),
        h: Math.round(r.height),
        textL: toL(cs.color),
        big: size >= 24 || (bold && size >= 18.66),
      })
    }
    return out
  }, TEXTS)

  // Буквы делаем прозрачными, но не прячем: если под текстом появится тень,
  // она рисуется по контуру глифа и должна попасть в замер.
  await page.addStyleTag({
    content: `.hero, .hero * { color: transparent !important; -webkit-text-fill-color: transparent !important; }
              .hero .hero-offer, .hero .cta, .hero svg, .hero .law { visibility: hidden !important }`,
  })

  for (const a of areas) {
    if (a.y < 0 || a.y + a.h > height || a.w < 4 || a.h < 4) {
      console.log(`· ${`${screen}`.padEnd(11)} ${a.sel.padEnd(13)} не замерен: не попал в окно`)
      continue
    }
    // Рамку и скруглённые углы в замер не берём: у чипа с географией
    // собственная непрозрачная подложка, а по краям его прямоугольника
    // видна фотография — из-за неё честный замер показывал провал там,
    // где текст на самом деле лежит на белом.
    const inset = 3
    const clip = {
      x: a.x + inset,
      y: a.y + inset,
      width: Math.max(1, a.w - inset * 2),
      height: Math.max(1, a.h - inset * 2),
    }
    const buf = await page.screenshot({ clip })
    const png = PNG.sync.read(buf)

    // Считаем контраст для каждой точки фона и берём тот, что хуже
    // у 5% площади. Так проверка ловит и тёмный фон под тёмным текстом,
    // и светлый под светлым, и не срывается на одиночной точке.
    const cs = []
    for (let i = 0; i < png.data.length; i += 4) {
      cs.push(contrast(a.textL, lum(png.data[i], png.data[i + 1], png.data[i + 2])))
    }
    cs.sort((x, y) => x - y)
    const c = cs[Math.floor(cs.length * 0.05)]
    const need = a.big ? MIN_BIG : MIN
    const ok = c >= need
    if (!ok) failed++
    checked++
    console.log(`${ok ? '✓' : '✗'} ${screen.padEnd(11)} ${a.sel.padEnd(13)} ${c.toFixed(2)}:1 при норме ${need}`)
  }

  await ctx.close()
}

await browser.close()

if (!hasPhoto) {
  console.log('· Фотографии на первом экране нет (site.ts → heroPhoto пустой) — проверять нечего.')
  process.exit(0)
}
if (failed) {
  console.log(`\nОШИБОК: ${failed} из ${checked}. Текст поверх фотографии читается хуже нормы.
Что делать: в src/components/Hero.astro у слоя .photo убавить opacity либо
сдвинуть маску так, чтобы кадр гас раньше, чем начинается эта строка.`)
  process.exit(1)
}
console.log(`\n✓ Текст читается поверх фотографии: ${checked} замеров на ${SCREENS.length} ширинах.`)
