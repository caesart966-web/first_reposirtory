// Проверки, которые не ловит Lighthouse: работа с клавиатуры, читаемость
// страницы без JavaScript, мобильное меню, размеры кнопок под палец.
//
// Запуск: node scripts/test-a11y.mjs [адрес]

import { chromium } from 'playwright'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const browser = await chromium.launch()

let failed = 0
const check = (ok, name, detail = '') => {
  console.log(ok ? `✓ ${name}` : `✗ ${name}${detail ? ' — ' + detail : ''}`)
  if (!ok) failed++
}

// ── 1. Страница читается без JavaScript ──────────────────────────────────
{
  const ctx = await browser.newContext({ javaScriptEnabled: false })
  const page = await ctx.newPage()
  for (const path of ['/', '/stoimost/', '/uslugi/sro-stroiteley/']) {
    await page.goto(BASE + path, { waitUntil: 'domcontentloaded' })
    const text = (await page.locator('body').innerText()).trim()
    const visible = await page.evaluate(
      () => [...document.querySelectorAll('.rv')].filter((el) => getComputedStyle(el).opacity === '0').length,
    )
    check(text.length > 2000, `Без JavaScript текст ${path} читается`, `${text.length} знаков`)
    check(visible === 0, `Без JavaScript ничего не спрятано на ${path}`, `${visible} невидимых блоков`)
  }
  await ctx.close()
}

// ── 2. Клавиатура: фокус виден, по сайту можно пройти ────────────────────
{
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })

  // Первая же табуляция должна давать ссылку «Перейти к содержанию»
  await page.keyboard.press('Tab')
  const first = await page.evaluate(() => document.activeElement?.textContent?.trim())
  check(first === 'Перейти к содержанию', 'Первый Tab — ссылка «Перейти к содержанию»', String(first))

  // Рамку фокуса проверяем настоящими нажатиями Tab: браузер показывает её
  // только при переходе с клавиатуры, программный focus() её не включает.
  const noRing = []
  for (let i = 0; i < 30; i++) {
    await page.keyboard.press('Tab')
    const info = await page.evaluate(() => {
      const el = document.activeElement
      if (!el || el === document.body) return null
      const s = getComputedStyle(el)
      const ring =
        (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none'
      return { ring, name: (el.textContent || el.getAttribute('aria-label') || el.tagName).trim().slice(0, 30) }
    })
    if (info && !info.ring) noRing.push(info.name)
  }
  check(noRing.length === 0, 'При ходьбе по Tab рамка фокуса видна всегда', noRing.join(' | '))

  // Калькулятор проходится с клавиатуры
  await page.locator('#calc-body .opt').first().focus()
  await page.keyboard.press('Enter')
  await page.waitForTimeout(300)
  const advanced = await page.locator('#calc-step-label').textContent()
  check(/Вопрос 2/.test(advanced || ''), 'Калькулятор отвечает на Enter', String(advanced))

  await page.close()
}

// ── 3. Мобильное меню: открывается, закрывается по Esc ───────────────────
{
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })

  const menuHiddenAtStart = await page.locator('#mobile-menu').isHidden()
  check(menuHiddenAtStart, 'Мобильное меню закрыто при загрузке')

  await page.locator('.burger').click()
  await page.waitForTimeout(200)
  check(await page.locator('#mobile-menu').isVisible(), 'Меню открывается по кнопке')

  const scrollLocked = await page.evaluate(() => document.body.style.overflow === 'hidden')
  check(scrollLocked, 'При открытом меню страница за ним не прокручивается')

  await page.keyboard.press('Escape')
  await page.waitForTimeout(200)
  check(await page.locator('#mobile-menu').isHidden(), 'Меню закрывается по Esc')

  // Телефон виден на первом экране, без прокрутки
  check(await page.locator('.icon-phone').isVisible(), 'Кнопка звонка видна на первом экране')

  // Размеры тап-целей: минимум 24 px по стандарту доступности.
  // Ссылки внутри абзацев не считаем — для них стандарт делает исключение,
  // иначе строки текста пришлось бы разгонять до нечитаемого межстрочья.
  const small = await page.evaluate(() => {
    const inParagraph = (el) => !!el.closest('p, li:not(:has(> a:only-child)), .prose, .doc, summary')
    const bad = []
    document.querySelectorAll('a[href], button').forEach((el) => {
      const r = el.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) return
      if (inParagraph(el)) return
      if (r.height < 24) bad.push((el.textContent || el.getAttribute('aria-label') || '?').trim().slice(0, 30))
    })
    return bad
  })
  check(small.length === 0, 'Тап-цели не меньше 24 px', small.join(' | '))

  await page.close()
}

await browser.close()

if (failed) {
  console.log(`\nОШИБОК: ${failed}`)
  process.exit(1)
}
console.log('\n✓ Клавиатура, мобильное меню и работа без JavaScript — в порядке.')
