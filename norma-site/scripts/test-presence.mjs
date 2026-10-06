// «На связи» рядом с фотографией владельца: первый экран, форма, «Контакты».
//
// Запуск:  npm test   (или node scripts/test-presence.mjs [адрес сайта])
//
// Зачем. Строка говорит, что сейчас быстрее — позвонить или написать,
// по московскому времени. Решает одна функция (src/lib/presence.ts), а мест
// три: под кнопками первого экрана, над формой заявки и «Сейчас на связи»
// на «Контактах». Ошибка здесь была бы тихой и жила бы по часам: днём всё
// верно, а ночью первый экран говорит «на связи», а «Контакты» — «пишите».
// Поэтому часы браузера подменяются (page.clock), и проверяются три
// состояния: будний день, ночь, выходной.
//
// Ещё одна проверка — без скрипта: строка не должна оставаться пустой,
// в разметке стоит режим из бланка контактов.

import { chromium } from './lib/browser.mjs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'

let problems = 0
const ok = (m) => console.log(`  ✓ ${m}`)
const fail = (m) => { console.log(`  ✗ ${m}`); problems++ }

console.log('\nСтрока «на связи» по московскому времени\n')

// Время задаётся в UTC: Москва — UTC+3 круглый год, Иркутск — UTC+8.
// Часы выбраны так, чтобы Москва и Иркутск расходились в «день/ночь»:
// в 19:00 по Москве в Иркутске полночь, в 5:00 по Москве там 10 утра.
// Строка, посчитанная по часам посетителя, здесь ошиблась бы.
const CASES = [
  { name: 'будний день, 19:00 по Москве', at: '2026-10-06T16:00:00Z', state: 'on', short: 'Сейчас на связи', long: 'Сейчас на связи, отвечу сразу' },
  { name: 'ночь, 5:00 по Москве', at: '2026-10-07T02:00:00Z', state: 'night', short: 'Ночь в Москве — быстрее написать', long: 'Ночь в Москве — быстрее всего написать в мессенджер' },
  { name: 'суббота, 12:00 по Москве', at: '2026-10-10T09:00:00Z', state: 'on', short: 'Выходной, но на связи', long: 'Выходной, но на связи — звоните или пишите' },
]

const browser = await chromium.launch()

for (const c of CASES) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, timezoneId: 'Asia/Irkutsk' })
  const page = await context.newPage()
  // Часовой пояс браузера — иркутский нарочно: строка обязана считать
  // по Москве, а не по часам посетителя.
  await page.clock.setFixedTime(new Date(c.at))

  await page.goto(BASE + '/', { waitUntil: 'networkidle' })
  const rows = await page.locator('[data-presence]').evaluateAll((els) =>
    els.map((el) => ({ state: el.dataset.state, text: el.querySelector('.pr-state-text')?.textContent?.trim() })),
  )
  if (rows.length !== 2) fail(`${c.name}: на главной строк «на связи» ${rows.length}, ожидалось 2 (первый экран и форма)`)
  else if (rows.every((r) => r.state === c.state && r.text === c.short)) ok(`${c.name}: главная — «${c.short}» в обоих местах`)
  else fail(`${c.name}: главная показывает ${JSON.stringify(rows)}, ожидалось «${c.short}» (${c.state})`)

  await page.goto(BASE + '/kontakty/', { waitUntil: 'networkidle' })
  const k = await page.evaluate(() => {
    const box = document.getElementById('k-status')
    return { state: box?.dataset.state, text: box?.querySelector('.k-status-text')?.textContent?.trim(), hidden: box?.hidden }
  })
  if (k.state === c.state && k.text === c.long && !k.hidden) ok(`${c.name}: «Контакты» — «${c.long}»`)
  else fail(`${c.name}: на «Контактах» ${JSON.stringify(k)}, ожидалось «${c.long}» (${c.state})`)
  await context.close()
}

// Без скрипта — режим из бланка, а не пустая строка.
{
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, javaScriptEnabled: false })
  const page = await context.newPage()
  await page.goto(BASE + '/', { waitUntil: 'load' })
  const text = (await page.locator('.presence .pr-state-text').textContent())?.trim()
  if (text === 'Круглосуточно, без выходных') ok('без скрипта: «Круглосуточно, без выходных»')
  else fail(`без скрипта строка «${text}», ожидалось «Круглосуточно, без выходных»`)
  await context.close()
}

await browser.close()
console.log(problems ? `\n✗ Проверка не прошла: ${problems}\n` : '\n✓ Первый экран, форма и «Контакты» говорят одно и то же в любое время суток.\n')
process.exit(problems ? 1 : 0)
