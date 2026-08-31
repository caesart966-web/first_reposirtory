// Проверяет калькулятор взносов на странице стоимости.
//
// Зачем: калькулятор называет посетителю сумму в миллионах рублей. Ошибка
// здесь — не съехавшая вёрстка, а неверная цифра в бюджете компании,
// и заметить её на глаз невозможно: числа выглядят правдоподобно любые.
//
// Ожидаемые суммы не вписаны в проверку, а берутся из src/config/facts.ts —
// того же файла, из которого их берёт сайт. Поэтому проверка следит не за
// «теми же числами, что вчера», а за тем, что калькулятор считает именно по
// таблицам закона: сложение, переключение направления, включение и выключение
// второго фонда.
//
// Запуск: node scripts/test-cost.mjs [адрес]

import { chromium } from 'playwright'
import { FUNDS } from '../src/config/facts.ts'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'

// Тот же формат, что и на странице: разряды неразрывными пробелами.
const money = (n) => n.toLocaleString('ru-RU').replace(/\s/g, ' ') + ' ₽'

const at = (rows, level) => rows.find((r) => r.level === level).amountNum

// Случаи покрывают всё, что калькулятор умеет менять:
// направление (две разные таблицы), уровень, наличие и отсутствие торгов.
const CASES = [
  {
    name: 'строитель, 1 уровень, без торгов',
    dir: 'build', table: 'build', harm: 1, tender: false,
    expect: at(FUNDS.buildHarm, 1),
  },
  {
    name: 'строитель, 3 уровень, без торгов',
    dir: 'build', table: 'build', harm: 3, tender: false,
    expect: at(FUNDS.buildHarm, 3),
  },
  {
    name: 'строитель, 3 уровень + торги по 2 уровню',
    dir: 'build', table: 'build', harm: 3, tender: true, contract: 2,
    expect: at(FUNDS.buildHarm, 3) + at(FUNDS.buildContract, 2),
  },
  {
    name: 'строитель, максимальные уровни',
    dir: 'build', table: 'build', harm: 5, tender: true, contract: 5,
    expect: at(FUNDS.buildHarm, 5) + at(FUNDS.buildContract, 5),
  },
  {
    name: 'проектировщик, 1 уровень, без торгов',
    dir: 'design', table: 'design', harm: 1, tender: false,
    expect: at(FUNDS.designHarm, 1),
  },
  {
    name: 'проектировщик, 4 уровень + торги по 4 уровню',
    dir: 'design', table: 'design', harm: 4, tender: true, contract: 4,
    expect: at(FUNDS.designHarm, 4) + at(FUNDS.designContract, 4),
  },
  {
    // Изыскатели платят по той же таблице, что и проектировщики
    // (ч. 10 и ч. 11 ст. 55.16) — проверяем, что калькулятор их не путает
    // со строителями.
    name: 'изыскатель платит по таблице проектировщиков',
    dir: 'survey', table: 'design', harm: 2, tender: false,
    expect: at(FUNDS.designHarm, 2),
  },
]

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 } })
const page = await ctx.newPage()

const errors = []
page.on('pageerror', (e) => errors.push(e.message))

await page.goto(BASE + '/stoimost/', { waitUntil: 'domcontentloaded' })

let failed = 0

for (const c of CASES) {
  await page.check(`input[name="cost-dir"][value="${c.dir}"]`)
  await page.check(`input[name="cost-harm-${c.table}"][value="${c.harm}"]`)
  await page.check(`input[name="cost-odo"][value="${c.tender ? 'yes' : 'no'}"]`)
  if (c.tender) await page.check(`input[name="cost-contract-${c.table}"][value="${c.contract}"]`)

  const got = await page.evaluate(() => ({
    total: document.getElementById('out-total').textContent,
    odoShown: !document.getElementById('out-odo-row').hidden,
  }))

  const want = money(c.expect)
  const ok = got.total === want && got.odoShown === c.tender
  if (!ok) failed++
  console.log(
    `${ok ? '✓' : '✗'} ${c.name.padEnd(46)} ${got.total}` +
      (ok ? '' : `  ← ожидалось ${want}${got.odoShown !== c.tender ? ', строка ОДО показана неверно' : ''}`),
  )
}

// Уровни чужого направления должны быть спрятаны и выключены: иначе
// посетитель может оставить выбранным уровень из другой таблицы.
await page.check('input[name="cost-dir"][value="design"]')
const hidden = await page.evaluate(() => {
  const other = document.querySelector('.lvls[data-for="build"]')
  const mine = document.querySelector('.lvls[data-for="design"]')
  return {
    otherHidden: other.hidden,
    otherDisabled: [...other.querySelectorAll('input')].every((i) => i.disabled),
    mineShown: !mine.hidden,
  }
})
const swapOk = hidden.otherHidden && hidden.otherDisabled && hidden.mineShown
if (!swapOk) failed++
console.log(`${swapOk ? '✓' : '✗'} уровни чужого направления спрятаны и выключены`)

// Сумма не должна называться «стоимостью вступления»: в неё не входят
// взносы самой СРО, и подменять одно другим — ровно та ошибка, за которую
// сайт критикует конкурентов.
//
// Проверяем именно подписи над числами, а не наличие слов где-то в блоке:
// ниже фраза «стоимость под ключ» стоит законно — в объяснении, почему
// такую цифру здесь не называют.
const honest = await page.evaluate(() => {
  const box = document.getElementById('cost-out')
  const cap = box.querySelector('.out-cap')?.textContent || ''
  const totalLabel = box.querySelector('.out-total span')?.textContent || ''
  return {
    capIsAboutLaw: /установленные законом/i.test(cap),
    totalIsAboutLaw: /по закону/i.test(totalLabel),
    listsMissing: /Чего в этой сумме нет/i.test(box.textContent || ''),
  }
})
const honestOk = honest.capIsAboutLaw && honest.totalIsAboutLaw && honest.listsMissing
if (!honestOk) failed++
console.log(
  `${honestOk ? '✓' : '✗'} итог подписан как взносы по закону и перечисляет, чего в нём нет` +
    (honestOk ? '' : `  ← ${JSON.stringify(honest)}`),
)

if (errors.length) {
  failed++
  console.log(`✗ ошибки в консоли: ${errors.join('; ')}`)
}

await browser.close()

if (failed) {
  console.log(`\nОШИБОК: ${failed}. Калькулятор в src/components/CostCalculator.astro,
суммы — в src/config/facts.ts.`)
  process.exit(1)
}
console.log(`\n✓ Калькулятор взносов считает по таблицам закона: ${CASES.length} случаев.`)
