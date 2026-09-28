// Метрика — только после согласия, и именно тот счётчик.
//
// Запуск:  npm test   (или node scripts/test-metrika.mjs [адрес сайта])
//
// Зачем. Счётчик подключается из полосы про cookie, а не стоит в разметке,
// и это обещание политики: до «Принять» к Яндексу не уходит ни одного
// запроса. Пока номер счётчика был пуст, полосы не было вовсе, и стеречь
// было нечего — поведение проверили один раз руками. С вписанным номером
// ошибка здесь уже не косметика: Метрика, загруженная до согласия, — это
// обработка данных без согласия, на каждом заходе.
//
// Запросы к mc.yandex.ru перехватываются и получают пустую заглушку: слать
// заходы проверки в настоящий счётчик нельзя, да и Яндекс из среды проверки
// недоступен. Вызовы ym() копятся в очереди загрузчика (ym.a) — по ней
// и видно, с каким номером счётчик инициализирован и куда ушла цель.
//
// Настоящий playwright, а не scripts/lib/browser.mjs: обёртка отвечает
// за посетителя «только необходимые» ещё до загрузки страницы, и полосы
// эта проверка бы не увидела.

import { chromium } from 'playwright'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const { SITE } = await import('../src/config/site.ts')

let problems = 0
const ok = (m) => console.log(`  ✓ ${m}`)
const fail = (m) => { console.log(`  ✗ ${m}`); problems++ }

console.log('\nЯндекс.Метрика и согласие на cookie\n')

if (!SITE.metrikaId) {
  console.log('  · счётчик не подключён (SITE.metrikaId пуст) — полосы нет, проверять нечего')
  process.exit(0)
}
const ID = Number(SITE.metrikaId)
const TAG = `https://mc.yandex.ru/metrika/tag.js?id=${ID}`

const browser = await chromium.launch()

async function visitor() {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
  const hits = []
  await context.route(/mc\.yandex\.ru/, (route) => {
    hits.push(route.request().url())
    route.fulfill({ status: 200, contentType: 'application/javascript', body: '/* заглушка */' })
  })
  const page = await context.newPage()
  return { context, page, hits }
}

const queue = (page) => page.evaluate(() => (window.ym && window.ym.a ? window.ym.a.map((a) => Array.from(a)) : []))

// ── Первый заход и отказ ──────────────────────────────────────────────────
{
  const { context, page, hits } = await visitor()
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })

  // На превью счётчика нет нарочно (CookieBanner.astro): заходы на черновик
  // смешались бы с настоящими. Такая сборка — не повод падать.
  const robots = await page.locator('meta[name="robots"]').getAttribute('content').catch(() => null)
  if (robots && /noindex/i.test(robots)) {
    console.log('  · сборка превью (noindex): счётчика здесь нет нарочно — проверять нечего')
    await browser.close()
    process.exit(0)
  }

  const note = page.locator('#cookie-note')
  if (await note.isVisible()) ok('при первом заходе видна полоса с выбором')
  else fail('при первом заходе полоса про cookie не показалась')
  if (hits.length === 0 && (await page.evaluate(() => typeof window.ym)) === 'undefined') {
    ok('до выбора к Метрике не ушло ни одного запроса')
  } else {
    fail(`до выбора Метрика уже подключена: запросов ${hits.length}`)
  }

  await page.click('[data-cookie="need"]')
  await page.reload({ waitUntil: 'networkidle' })
  if (hits.length === 0 && !(await note.isVisible())) {
    ok('«Только необходимые»: ни одного запроса и после перезагрузки, полоса больше не показывается')
  } else {
    fail(`после «Только необходимые»: запросов ${hits.length}, полоса ${(await note.isVisible()) ? 'видна' : 'скрыта'}`)
  }
  await context.close()
}

// ── Согласие ──────────────────────────────────────────────────────────────
{
  const { context, page, hits } = await visitor()
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })
  await page.click('[data-cookie="all"]')
  await page.waitForFunction(() => typeof window.ym === 'function')
  await page.waitForLoadState('networkidle')

  if (hits.length === 1 && hits[0] === TAG) ok(`«Принять»: один запрос — ${TAG}`)
  else fail(`«Принять»: ожидался один запрос ${TAG}, ушло: ${hits.join(', ') || 'ничего'}`)

  const init = (await queue(page)).find((c) => c[1] === 'init')
  if (!init) {
    fail('счётчик не инициализирован')
  } else {
    if (init[0] === ID) ok(`счётчик ${ID} инициализирован номером-числом, как в коде Метрики`)
    else fail(`init с номером ${JSON.stringify(init[0])}, а нужен ${ID} числом`)
    if (init[2]?.webvisor === true && init[2]?.clickmap === true) ok('вебвизор и карта кликов включены')
    else fail('в init нет вебвизора или карты кликов')
  }

  // Цель с кликом по телефону. Переход по tel: гасится, чтобы браузер
  // не пытался звонить, — обработчик цели при этом срабатывает как обычно.
  await page.evaluate(() => {
    window.addEventListener('click', (e) => { if (e.target.closest?.('a')) e.preventDefault() }, true)
    document.querySelector('[data-goal="click_phone"]').click()
  })
  const goal = (await queue(page)).find((c) => c[1] === 'reachGoal' && c[2] === 'click_phone')
  if (!goal) fail('цель click_phone не ушла')
  else if (goal[0] !== ID) fail(`цель ушла в счётчик ${JSON.stringify(goal[0])}, а не в ${ID}`)
  else ok('цель click_phone уходит в тот же счётчик')

  hits.length = 0
  await page.reload({ waitUntil: 'networkidle' })
  if (!(await page.locator('#cookie-note').isVisible()) && hits.length === 1) {
    ok('согласие помнится: полосы нет, счётчик грузится сам')
  } else {
    fail(`после согласия и перезагрузки: запросов ${hits.length}, полоса ${(await page.locator('#cookie-note').isVisible()) ? 'видна' : 'скрыта'}`)
  }
  await context.close()
}

await browser.close()
console.log(problems ? `\n✗ Проверка не прошла: ${problems}\n` : '\n✓ Метрика подключается только после согласия и считает в свой счётчик.\n')
process.exit(problems ? 1 : 0)
