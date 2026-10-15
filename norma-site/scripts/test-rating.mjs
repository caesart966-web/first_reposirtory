// Значок рейтинга Яндекса — только после согласия; QR и ссылки — в одно место.
//
// Запуск:  npm test   (или node scripts/test-rating.mjs [адрес сайта])
//
// Зачем. Значок — рамка с yandex.ru, и Яндекс при её загрузке ставит свои
// cookie. Политика обещает, что до «Принять» к Яндексу не уходит ни одного
// запроса, поэтому рамки в разметке нет: её вставляет скрипт после согласия
// (YandexRating.astro). Ошибка здесь была бы тихой: рамка, вписанная
// в разметку «для простоты», выглядит так же, только грузится у всех —
// и узнать об этом было бы неоткуда.
//
// Запросы к Яндексу перехватываются: значок получает заглушку, Метрика —
// пустой скрипт. Настоящий playwright, а не scripts/lib/browser.mjs:
// обёртка заранее отвечает «только необходимые», и согласия не было бы.

import { chromium } from 'playwright'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const { SITE, YANDEX_ORG } = await import('../src/config/site.ts')
const PAGE = '/kontakty/'

let problems = 0
const ok = (m) => console.log(`  ✓ ${m}`)
const fail = (m) => { console.log(`  ✗ ${m}`); problems++ }

console.log('\nЗначок рейтинга Яндекса и QR для отзыва\n')

if (!YANDEX_ORG) {
  console.log('  · номер организации не вписан (SITE.yandexOrgId пуст) — значка нет, проверять нечего')
  process.exit(0)
}

const STUB = '<!doctype html><meta charset="utf-8"><body style="margin:0;background:#fff">рейтинг</body>'
const browser = await chromium.launch()

async function visitor(width = 1280, height = 900) {
  const context = await browser.newContext({ viewport: { width, height } })
  const hits = []
  await context.route(/(^https?:\/\/([a-z0-9-]+\.)*(yandex\.ru|ya\.cc)\/)/, (route) => {
    const url = route.request().url()
    if (!/mc\.yandex\.ru/.test(url)) hits.push(url)
    route.fulfill(/sprav\/widget/.test(url)
      ? { status: 200, contentType: 'text/html', body: STUB }
      : { status: 200, contentType: 'application/javascript', body: '/* заглушка */' })
  })
  const page = await context.newPage()
  return { context, page, hits }
}

const frames = (page) => page.locator('[data-yr] iframe')

// ── Разметка: рамки нет, ссылки ведут куда надо ──────────────────────────
{
  const { context, page, hits } = await visitor()
  const res = await page.goto(BASE + PAGE, { waitUntil: 'networkidle' })
  const html = await res.text()

  const robots = await page.locator('meta[name="robots"]').getAttribute('content').catch(() => null)
  const preview = Boolean(robots && /noindex/i.test(robots))

  if (!/<iframe/i.test(html)) ok('в разметке страницы рамки нет — её вставляет только скрипт')
  else fail('в разметке страницы есть <iframe>: значок грузился бы без согласия')

  const boxes = await page.locator('[data-yr]').count()
  if (boxes === 2) ok('значок стоит в двух местах: «Отзывы» на контактах и подвал')
  else fail(`мест под значок ${boxes}, ожидалось 2 (раздел «Отзывы» и подвал)`)

  const cards = await page.locator('[data-yr] .yr-link').evaluateAll((a) => a.map((x) => x.getAttribute('href')))
  if (cards.length && cards.every((h) => h === YANDEX_ORG.card)) ok(`до согласия на месте значка ссылка на карточку ${YANDEX_ORG.card}`)
  else fail(`ссылки на месте значка: ${cards.join(', ') || 'нет'} — ожидалась ${YANDEX_ORG.card}`)

  const asks = await page.locator('[data-goal="click_review"]').evaluateAll((a) => a.map((x) => x.getAttribute('href')))
  if (asks.length === 2 && asks.every((h) => h === SITE.reviewLink)) ok(`«Оставить отзыв» (раздел и подвал) ведёт на ${SITE.reviewLink}`)
  else fail(`ссылки «Оставить отзыв»: ${asks.join(', ') || 'нет'} — ожидались две на ${SITE.reviewLink}`)

  const qr = page.locator('.k-rev-qr svg')
  if ((await qr.getAttribute('data-qr-text')) === SITE.reviewLink && (await qr.isVisible())) {
    ok('QR на компьютере виден и несёт ту же ссылку, что «Оставить отзыв»')
  } else {
    fail('QR не виден на 1280 px или ведёт не туда, куда ссылка рядом')
  }

  await page.locator('.site-footer').scrollIntoViewIfNeeded()
  await page.waitForTimeout(300)
  if (hits.length === 0 && (await frames(page).count()) === 0) ok('до выбора к Яндексу не ушло ни одного запроса, даже у подвала')
  else fail(`до выбора: запросов к Яндексу ${hits.length}, рамок ${await frames(page).count()}`)

  if (preview) {
    console.log('  · сборка превью (noindex): полосы и согласия здесь нет нарочно — дальше проверять нечего')
    await context.close()
    await browser.close()
    console.log(problems ? `\n✗ Проверка не прошла: ${problems}\n` : '\n✓ Значок рейтинга без согласия не грузится.\n')
    process.exit(problems ? 1 : 0)
  }

  await page.click('[data-cookie="need"]')
  await page.waitForTimeout(300)
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.site-footer').scrollIntoViewIfNeeded()
  await page.waitForTimeout(300)
  if (hits.length === 0 && (await frames(page).count()) === 0) ok('«Только необходимые»: значка нет и после перезагрузки, запросов ноль')
  else fail(`после «Только необходимые»: запросов ${hits.length}, рамок ${await frames(page).count()}`)
  await context.close()
}

// ── Согласие на этой же странице ─────────────────────────────────────────
{
  const { context, page, hits } = await visitor()
  await page.goto(BASE + PAGE, { waitUntil: 'networkidle' })
  const rev = page.locator('.k-rev')
  await rev.scrollIntoViewIfNeeded()
  const before = await rev.boundingBox()

  await page.click('[data-cookie="all"]')
  await page.locator('.k-rev [data-yr][data-on]').waitFor({ timeout: 5000 }).catch(() => {})

  const srcs = await frames(page).evaluateAll((f) => f.map((x) => ({ src: x.getAttribute('src'), w: x.width, h: x.height, title: x.title })))
  if (srcs.length === 2 && srcs.every((f) => f.src === YANDEX_ORG.badge)) ok(`«Принять»: значок вставлен без перезагрузки — ${YANDEX_ORG.badge}`)
  else fail(`после «Принять» рамки: ${JSON.stringify(srcs)}`)
  if (srcs.every((f) => f.w === '150' && f.h === '50' && f.title)) ok('рамка 150×50 и с названием для экранного диктора')
  else fail('у рамки не тот размер или нет title')

  if (await page.locator('.k-rev [data-yr][data-on]').count()) ok('значок в «Отзывах» загрузился и встал поверх ссылки')
  else fail('значок в «Отзывах» не загрузился')
  const after = await rev.boundingBox()
  if (before && after && Math.abs(before.height - after.height) < 0.5) ok('раздел не сдвинулся: значок занял место ссылки')
  else fail(`раздел «Отзывы» изменил высоту: ${before?.height} → ${after?.height}`)

  if (hits.length >= 1 && hits.every((u) => u === YANDEX_ORG.badge)) ok('к Яндексу уходит только запрос значка')
  else fail(`запросы к Яндексу: ${hits.join(', ')}`)

  hits.length = 0
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.k-rev').scrollIntoViewIfNeeded()
  await page.locator('.k-rev [data-yr][data-on]').waitFor({ timeout: 5000 }).catch(() => {})
  if ((await frames(page).count()) === 2 && hits.length >= 1) ok('согласие помнится: после перезагрузки значок грузится сам')
  else fail(`после перезагрузки: рамок ${await frames(page).count()}, запросов ${hits.length}`)
  await context.close()
}

// ── Телефон: QR не нужен, ссылка на месте ────────────────────────────────
{
  const { context, page } = await visitor(390, 844)
  await page.goto(BASE + PAGE, { waitUntil: 'networkidle' })
  const qrShown = await page.locator('.k-rev-qr').isVisible()
  const go = page.locator('.k-rev-go')
  const goBox = await go.boundingBox()
  if (!qrShown && (await go.isVisible()) && goBox && goBox.height >= 44) ok('на телефоне QR скрыт, «Оставить отзыв» — ссылкой высотой от 44 px')
  else fail(`на 390 px: QR ${qrShown ? 'виден' : 'скрыт'}, ссылка ${goBox ? Math.round(goBox.height) + ' px' : 'не видна'}`)
  await context.close()
}

await browser.close()
console.log(problems ? `\n✗ Проверка не прошла: ${problems}\n` : '\n✓ Значок рейтинга грузится только после согласия, QR и ссылки ведут в одно место.\n')
process.exit(problems ? 1 : 0)
