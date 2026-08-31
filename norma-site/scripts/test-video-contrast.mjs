// Проверяет, что текст поверх фоновых роликов читается.
//
// Зачем отдельная проверка: обычные инструменты доступности считают контраст
// по цвету фона в стилях. Под текстом здесь не цвет, а движущаяся картинка,
// и на светлом кадре надпись может пропасть, хотя в стилях всё формально
// в порядке. Поэтому смотрим настоящие пиксели на разных секундах ролика
// и берём самый светлый — худший — случай.
//
// Цвет самого текста берётся из браузера, а не считается «белым»: приглушённый
// подзаголовок требует фона вдвое темнее, чем белый заголовок, и разница
// решает, пройдёт страница или нет.
//
// Запуск: node scripts/test-video-contrast.mjs [адрес]

import { chromium } from 'playwright'
import { PNG } from 'pngjs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const MOMENTS = [0.2, 2.5, 5, 7.5, 9.5] // секунды ролика
const MIN = 4.5 // требование стандарта для обычного текста

// Страницы с фоновым роликом. Добавили ролик на новую страницу —
// допишите её сюда, иначе проверка её просто не увидит.
const PAGES = [
  {
    url: '/',
    section: '.hero',
    texts: ['.geo', '.page-title', '.tagline', '.promises'],
    // Значки и белая карточка предложения — у них своя подложка,
    // мерить по ним фон бессмысленно.
    hide: '.hero .wrap svg, .hero .hero-offer',
  },
]

const SCREENS = [
  [1280, 900, 'компьютер'],
  [390, 800, 'телефон'],
]

const lum = (r, g, b) => {
  const f = (v) => {
    v /= 255
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}

// Контраст по стандарту: (светлее + 0.05) / (темнее + 0.05).
const contrast = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)

const browser = await chromium.launch()
let failed = 0
let checked = 0

for (const page_ of PAGES) {
  for (const [width, height, screen] of SCREENS) {
    const ctx = await browser.newContext({ viewport: { width, height } })
    const page = await ctx.newPage()
    await page.goto(BASE + page_.url, { waitUntil: 'networkidle' })

    // Ролик грузится лениво, после полной загрузки страницы.
    await page.waitForFunction(() => {
      const v = document.querySelector('video')
      return v && v.readyState >= 2
    }, { timeout: 20000 })

    // Где лежит текст и какого он цвета.
    const areas = await page.evaluate(({ section, texts }) => {
      const toL = (css) => {
        const [r, g, b] = css.match(/\d+(\.\d+)?/g).map(Number)
        const f = (v) => {
          v /= 255
          return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
        }
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
      }
      return texts
        .map((sel) => {
          const el = document.querySelector(`${section} ${sel}`)
          if (!el) return null
          const r = el.getBoundingClientRect()
          return {
            sel,
            x: Math.round(r.x),
            y: Math.round(r.y),
            w: Math.round(r.width),
            h: Math.round(r.height),
            textL: toL(getComputedStyle(el).color),
          }
        })
        .filter(Boolean)
    }, page_)

    // Делаем буквы прозрачными, но НЕ прячем их. Тень под текстом рисуется
    // по контуру глифа и остаётся на месте — значит в замер попадает ровно
    // то, на чём буква лежит на самом деле: кадр плюс её собственная тень.
    //
    // Прятать текст через visibility было бы неверно: тень исчезла бы вместе
    // с ним, и замер показал бы фон светлее, чем видит посетитель. А не прятать
    // вовсе нельзя — сами буквы дали бы контраст 1:1.
    await page.addStyleTag({
      content: `${page_.section} .wrap, ${page_.section} .wrap * {
        color: transparent !important;
        -webkit-text-fill-color: transparent !important;
      }
      ${page_.hide} { visibility: hidden !important }`,
    })

    const worst = new Map()
    const skipped = new Set()

    for (const t of MOMENTS) {
      await page.evaluate((sec) => {
        const v = document.querySelector('video')
        v.pause()
        v.currentTime = sec
      }, t)
      await page.waitForFunction(() => {
        const v = document.querySelector('video')
        return v.readyState >= 2 && !v.seeking
      }, { timeout: 8000 }).catch(() => {})
      await page.waitForTimeout(250)

      for (const a of areas) {
        // Замерить можно только то, что попало в окно: снимок берётся
        // с видимой области. Пропуски не проглатываем — о них сказано ниже,
        // иначе перестановка блока молча снимает проверку с текста.
        if (a.y < 0 || a.y + a.h > height || a.w < 4) {
          skipped.add(a.sel)
          continue
        }
        const buf = await page.screenshot({ clip: { x: a.x, y: a.y, width: a.w, height: a.h } })
        const png = PNG.sync.read(buf)
        // Берём 5% самых светлых пикселей: одиночная светлая точка погоды
        // не делает, а вот светлое пятно под строкой — делает.
        const ls = []
        for (let i = 0; i < png.data.length; i += 4) {
          ls.push(lum(png.data[i], png.data[i + 1], png.data[i + 2]))
        }
        ls.sort((x, y) => y - x)
        const bright = ls[Math.floor(ls.length * 0.05)]
        const c = contrast(a.textL, bright)
        const prev = worst.get(a.sel)
        if (!prev || c < prev.c) worst.set(a.sel, { c, t })
      }
    }

    for (const [sel, { c, t }] of worst) {
      const ok = c >= MIN
      if (!ok) failed++
      checked++
      const where = `${page_.url} · ${screen}`
      console.log(`${ok ? '✓' : '✗'} ${where.padEnd(30)} ${sel.padEnd(13)} ${c.toFixed(2)}:1 (на ${t} с)`)
    }
    // Скрытый от замера текст — не ошибка, но и не тишина: чаще всего он
    // просто ушёл ниже сгиба, и видео под ним уже нет.
    for (const sel of skipped) {
      if (!worst.has(sel)) {
        console.log(`· ${`${page_.url} · ${screen}`.padEnd(30)} ${sel.padEnd(13)} не замерен: не попал в окно`)
      }
    }
    await ctx.close()
  }
}

await browser.close()

if (failed) {
  console.log(`\nОШИБОК: ${failed} из ${checked}. Текст на видео читается хуже нормы ${MIN}:1.
Пелена лежит в .veil, src/components/Hero.astro.`)
  process.exit(1)
}
const word = PAGES.length === 1 ? 'странице' : 'страницах'
console.log(`\n✓ Текст читается поверх видео: ${checked} замеров на ${PAGES.length} ${word}.`)
