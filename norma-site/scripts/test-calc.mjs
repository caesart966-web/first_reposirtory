// Проверка калькулятора «Нужна ли вам СРО»: прогоняем все ветки и смотрим,
// что вердикт совпадает с ожидаемым. Так ошибка в логике не уедет на сайт.
//
// Запуск: node scripts/test-calc.mjs [адрес]

import { chromium } from 'playwright'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'

// [что выбираем по шагам] → чего ждём в вердикте
const cases = [
  {
    name: 'Субподрядчик-строитель: СРО не нужна',
    picks: ['Строительство, реконструкция, капитальный ремонт', 'С генподрядчиком'],
    expectKind: 'v-no',
    expectText: 'СРО вам не нужна',
    expectLaw: 'ч. 2.1 ст. 52',
  },
  {
    name: 'ИЖС: СРО не нужна',
    picks: ['Строительство, реконструкция, капитальный ремонт', 'С физлицом'],
    expectKind: 'v-no',
    expectText: 'СРО вам не нужна',
  },
  {
    name: 'Строитель до 10 млн: СРО не нужна',
    picks: ['Строительство, реконструкция, капитальный ремонт', 'С застройщиком', 'До 10 млн'],
    expectKind: 'v-no',
    expectText: 'СРО вам не нужна',
  },
  {
    name: 'Строитель свыше 10 млн без торгов: нужна',
    picks: ['Строительство, реконструкция, капитальный ремонт', 'С застройщиком', 'Свыше 10 млн', 'Нет, работаем'],
    expectKind: 'v-yes',
    expectText: 'нужна СРО строителей',
  },
  {
    name: 'Строитель свыше 10 млн + торги: нужна и КФ ОДО',
    picks: ['Строительство, реконструкция, капитальный ремонт', 'С застройщиком', 'Свыше 10 млн', 'Да, планируем'],
    expectKind: 'v-cond',
    expectText: 'для торгов — второй взнос',
  },
  {
    name: 'Проектировщик, малая сумма: всё равно нужна',
    picks: ['Подготовка проектной документации', 'С застройщиком', 'До 25 млн', 'Нет, работаем'],
    expectKind: 'v-yes',
    expectText: 'нужна СРО проектировщиков',
  },
  {
    name: 'Проектировщик-субподрядчик: не нужна',
    picks: ['Подготовка проектной документации', 'С генподрядчиком'],
    expectKind: 'v-no',
    expectText: 'СРО вам не нужна',
  },
  {
    name: 'Изыскатель по прямому договору: нужна',
    picks: ['Инженерные изыскания', 'С застройщиком', 'До 25 млн', 'Нет, работаем'],
    expectKind: 'v-yes',
    expectText: 'нужна СРО изыскателей',
  },
  {
    name: 'Снос до 1 млн: не нужна',
    picks: ['Снос объектов', 'С застройщиком', 'До 1 млн'],
    expectKind: 'v-no',
    expectLaw: 'ст. 55.31',
  },
  {
    name: 'Снос от 1 млн + торги: нужна и КФ ОДО',
    picks: ['Снос объектов', 'С застройщиком', '1 млн ₽ и более', 'Да, планируем'],
    expectKind: 'v-cond',
  },
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1200, height: 900 } })

let failed = 0

for (const c of cases) {
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('#calc-body .opt')

  const steps = []
  for (const pick of c.picks) {
    const btn = page.locator('#calc-body .opt', { hasText: pick }).first()
    await btn.waitFor({ timeout: 5000 })
    steps.push((await page.locator('#calc-step-label').textContent())?.trim())
    await btn.click()
    await page.waitForTimeout(120)
  }

  await page.waitForSelector('.verdict', { timeout: 5000 })
  const kind = await page.evaluate(() => document.querySelector('.verdict')?.className || '')
  const text = await page.evaluate(() => document.querySelector('.verdict')?.textContent || '')

  const problems = []
  if (c.expectKind && !kind.includes(c.expectKind)) problems.push(`вердикт ${kind}, ждали ${c.expectKind}`)
  if (c.expectText && !text.includes(c.expectText)) problems.push(`нет текста «${c.expectText}»`)
  if (c.expectLaw && !text.includes(c.expectLaw)) problems.push(`нет нормы «${c.expectLaw}»`)

  // Счётчик шагов должен быть согласован: «Вопрос N из M», N ≤ M
  steps.forEach((s) => {
    const m = s?.match(/Вопрос (\d+) из (\d+)/)
    if (m && Number(m[1]) > Number(m[2])) problems.push(`счётчик «${s}»`)
  })

  if (problems.length) {
    failed++
    console.log(`✗ ${c.name}\n    ${problems.join('\n    ')}\n    шаги: ${steps.join(' → ')}`)
  } else {
    console.log(`✓ ${c.name}  (${steps.join(' → ')})`)
  }
}

await browser.close()

if (failed) {
  console.log(`\nОШИБОК: ${failed} из ${cases.length}`)
  process.exit(1)
}
console.log(`\n✓ Все ${cases.length} сценариев калькулятора дают верный ответ.`)
