// Стережёт правило первого экрана: на полосе с картой не должно быть текста.
//
// История этой проверки. Сначала ролик лежал фоном под всем первым экраном,
// а поверх шёл белый текст. Читаемость приходилось держать двумя подпорками:
// плотной пеленой поверх кадра и тенью у каждой буквы. Проверка тогда
// снимала настоящие пиксели видео и считала контраст по худшему кадру —
// и правильно делала: однажды она поймала две строки, которые на телефоне
// давали 4.22:1 и 4.35:1 при норме 4.5, а глазами это выглядело нормально.
//
// Потом карта переехала в собственную полосу, где не написано ничего:
// ролик стало видно целиком и в полную силу, а текст лёг на сплошной цвет
// с контрастом 15:1 — считать там нечего, это делает test-contrast.mjs
// вместе со всеми остальными надписями сайта.
//
// Но само правило нужно стеречь. Стоит однажды поставить на карту подпись
// или кнопку — и вернётся ровно та задача, ради которой писалась старая
// проверка, только подпорок в стилях уже не будет. Поэтому здесь осталось
// одно утверждение: над видео нет ни одной надписи. Если появится —
// проверка упадёт и напомнит, чем это кончилось в прошлый раз.
//
// Запуск: node scripts/test-video-contrast.mjs [адрес]

import { chromium } from 'playwright'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const SIZES = [
  { name: 'компьютер', width: 1440, height: 900 },
  { name: 'планшет', width: 820, height: 1100 },
  { name: 'телефон', width: 390, height: 844 },
]

const browser = await chromium.launch()
let failed = 0

for (const size of SIZES) {
  const ctx = await browser.newContext({ viewport: { width: size.width, height: size.height } })
  const page = await ctx.newPage()
  await page.goto(BASE + '/', { waitUntil: 'load' })

  // Ролик подключается после загрузки страницы и свободной минуты у браузера,
  // поэтому ждём, пока у него появятся собственные размеры. Не дождались —
  // не беда: проверка на текст поверх карты от этого не зависит.
  await page
    .waitForFunction(() => {
      const v = document.querySelector('.plate video')
      return v && v.videoWidth > 0
    }, { timeout: 6000 })
    .catch(() => {})

  const found = await page.evaluate(() => {
    const plate = document.querySelector('.plate')
    if (!plate) return { missing: true }
    const box = plate.getBoundingClientRect()

    const over = []
    for (const el of document.querySelectorAll('body *')) {
      if (plate.contains(el)) continue
      const text = [...el.childNodes]
        .filter((n) => n.nodeType === 3 && n.textContent.trim().length > 0)
        .map((n) => n.textContent.trim())
        .join(' ')
      if (!text) continue
      const cs = getComputedStyle(el)
      if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') continue
      const r = el.getBoundingClientRect()
      if (!r.width || !r.height) continue
      // Пересечение с полосой карты по обеим осям.
      const hit = r.left < box.right && r.right > box.left && r.top < box.bottom && r.bottom > box.top
      if (hit) over.push(`${el.tagName.toLowerCase()}.${el.className?.toString().split(' ')[0] || ''} — «${text.slice(0, 40)}»`)
    }

    // Уперлась ли полоса в ограничение высоты. Если да, поля по бокам
    // карты — так и задумано: на широком мониторе карта не растягивается,
    // а встаёт по центру тёмного поля.
    const cap = parseFloat(getComputedStyle(plate).maxHeight)
    return {
      plate: { width: Math.round(box.width), height: Math.round(box.height) },
      capped: Number.isFinite(cap) && box.height >= cap - 1,
      video: (() => {
        const v = plate.querySelector('video')
        if (!v) return null
        // Насколько карта заполняет полосу. При object-fit: contain пустые
        // поля по краям означают, что пропорция полосы разошлась с файлом.
        const vb = v.getBoundingClientRect()
        const nat = v.videoWidth && v.videoHeight ? v.videoWidth / v.videoHeight : null
        const shown = nat
          ? (nat > vb.width / vb.height
              ? { w: vb.width, h: vb.width / nat }
              : { w: vb.height * nat, h: vb.height })
          : null
        return shown && { fillX: +(shown.w / vb.width).toFixed(3), fillY: +(shown.h / vb.height).toFixed(3) }
      })(),
      over,
    }
  })

  if (found.missing) {
    console.log(`✗ ${size.name}: полосы с картой на странице нет вовсе`)
    failed++
    await ctx.close()
    continue
  }

  const fill = found.video
  const fillNote = fill
    ? found.capped && fill.fillY >= 0.99
      ? ` · карта по центру, ширина ${Math.round(fill.fillX * 100)}% полосы`
      : ` · карта заполняет полосу на ${Math.round(fill.fillX * 100)}%×${Math.round(fill.fillY * 100)}%`
    : ''

  if (found.over.length) {
    failed++
    console.log(`✗ ${size.name} ${found.plate.width}×${found.plate.height}: на карте оказался текст`)
    for (const o of found.over.slice(0, 6)) console.log(`    ${o}`)
  } else {
    console.log(`✓ ${size.name.padEnd(10)} полоса ${found.plate.width}×${found.plate.height}${fillNote}`)
  }

  // Пустое поле по краям карты бывает двух видов. По бокам на широком
  // экране — так и задумано: полоса упёрлась в ограничение высоты, и карта
  // встала по центру. Всё остальное — признак того, что пропорцию полосы
  // забыли поменять вслед за файлом.
  const gapExplained = found.capped && fill && fill.fillY >= 0.99
  if (fill && (fill.fillX < 0.99 || fill.fillY < 0.99) && !gapExplained) {
    console.log(`    ⚠ по краям карты остаётся пустое поле. Пропорция .plate в MapPlate.astro`)
    console.log(`      должна совпадать с размером файла public/video/hero.webm.`)
  }

  await ctx.close()
}

await browser.close()

if (failed) {
  console.log(`\nОШИБОК: ${failed}.
На полосе с картой не должно быть надписей. Текст поверх видео читается
хуже, чем кажется на светлом мониторе: чтобы вернуть его туда, пришлось бы
снова гасить ролик пеленой и подкладывать тень под каждую букву — и мерить
контраст по настоящим кадрам, как делалось до переделки первого экрана.`)
  process.exit(1)
}
console.log('\n✓ Карта чистая: текста поверх видео нет ни на одной ширине экрана.')
