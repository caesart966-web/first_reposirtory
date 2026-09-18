// Проверка формы заявки: валидация, маска телефона, защита от ботов,
// честное сообщение об ошибке вместо ложного «отправлено».
//
// Запуск: node scripts/test-form.mjs [адрес]

import { chromium } from './lib/browser.mjs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1200, height: 900 } })

let failed = 0
const check = (ok, name, detail = '') => {
  console.log(ok ? `✓ ${name}` : `✗ ${name}${detail ? ' — ' + detail : ''}`)
  if (!ok) failed++
}

await page.goto(BASE + '/kontakty/', { waitUntil: 'networkidle' })

// 1. Пустая форма не отправляется, показывает ошибки
await page.click('#lf-submit')
await page.waitForTimeout(200)
check(
  await page.locator('[data-field="name"].field--error').count() > 0,
  'Пустое имя помечается ошибкой',
)
check(
  await page.locator('[data-field="phone"].field--error').count() > 0,
  'Пустой телефон помечается ошибкой',
)
check(await page.locator('#err-agree.show').count() > 0, 'Без согласия отправить нельзя')

// 2. Маска телефона приводит ввод к единому виду
await page.fill('#lf-phone', '')
await page.type('#lf-phone', '89319698664')
const masked = await page.inputValue('#lf-phone')
check(masked === '+7 931 969-86-64', 'Телефон форматируется', `получили «${masked}»`)

// 3. Неверная почта не пропускается
await page.fill('#lf-name', 'Иван')
await page.fill('#lf-email', 'не-почта')
await page.check('#lf-agree')
await page.click('#lf-submit')
await page.waitForTimeout(200)
check(await page.locator('[data-field="email"].field--error').count() > 0, 'Неверная почта не проходит')

// 4. Корректные данные: приёмник не настроен — должен быть честный экран ошибки,
//    а не ложное «заявка отправлена»
await page.fill('#lf-email', 'test@example.ru')
await page.waitForTimeout(2600) // ловушка по времени: боты отправляют мгновенно
await page.click('#lf-submit')
await page.waitForTimeout(600)
const okShown = await page.locator('#lf-ok').isVisible()
const errShown = await page.locator('#lf-err').isVisible()
check(!okShown && errShown, 'Без настроенной почты показывается ошибка, а не ложный успех')

const errText = await page.locator('#lf-err').textContent()
check(/\+7 931/.test(errText || ''), 'В экране ошибки есть рабочий телефон')
check(
  (await page.inputValue('#lf-name')) === 'Иван',
  'Введённые данные не потеряны после ошибки',
)

// 5. Черновик сохраняется в браузере — заявка не пропадёт при закрытии вкладки
const draft = await page.evaluate(() => localStorage.getItem('norma-lead-draft'))
check(!!draft && draft.includes('Иван'), 'Черновик заявки сохранён в браузере')

// 6. Ловушка для ботов: заполненное скрытое поле не отправляет заявку
await page.goto(BASE + '/kontakty/', { waitUntil: 'networkidle' })
await page.evaluate(() => localStorage.removeItem('norma-lead-draft'))
await page.reload({ waitUntil: 'networkidle' })
await page.fill('#lf-name', 'Бот')
await page.fill('#lf-phone', '9001234567')
await page.check('#lf-agree')
await page.fill('#lf-company-site', 'https://spam.example')
await page.waitForTimeout(2600)
await page.click('#lf-submit')
await page.waitForTimeout(400)
check(await page.locator('#lf-ok').isVisible(), 'Боту показывается обычный экран успеха (заявка не уходит)')

// 7. Клавиатура: по форме можно пройти табом
await page.goto(BASE + '/kontakty/', { waitUntil: 'networkidle' })
// Обход табом идёт до кнопки, а не ровно восемь раз: полей в форме
// стало больше, и записанное число молча превратило бы проверку
// в проверку длины формы вместо достижимости кнопки.
await page.focus('#lf-name')
const reachable = []
for (let i = 0; i < 20 && !reachable.includes('lf-submit'); i++) {
  await page.keyboard.press('Tab')
  reachable.push(await page.evaluate(() => document.activeElement?.id || document.activeElement?.tagName))
}
check(reachable.includes('lf-submit'), 'Кнопка отправки достижима с клавиатуры', reachable.join(','))

// ── Связка калькуляторов с заявкой ─────────────────────────────────────
//
// Человек отвечает на вопросы калькулятора, нажимает «получить расчёт»
// и попадает на форму — пересказывать те же ответы заново ему незачем.
// Ломается эта связка молча: форма просто остаётся пустой, а понять,
// что так и было задумано, нельзя. Поэтому проверяется весь путь.
{
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 900 } })
  const q = await ctx.newPage()

  await q.goto(BASE + '/#calc', { waitUntil: 'networkidle' })
  await q.waitForTimeout(300)
  const pick = async (n) => {
    const btns = await q.$$('#calc button[data-id]')
    if (!btns[n]) throw new Error('в калькуляторе нет кнопки ответа №' + n)
    await btns[n].click()
    await q.waitForTimeout(200)
  }
  await pick(0) // строительство
  await pick(0) // с застройщиком
  await pick(1) // свыше 10 млн
  await pick(0) // торги
  await q.waitForTimeout(300)

  const snap = await q.evaluate(() => {
    try {
      return JSON.parse(sessionStorage.getItem('norma-calc') || 'null')
    } catch {
      return null
    }
  })
  check(!!snap?.summary, 'Калькулятор «нужна ли СРО» сохраняет ответы для заявки')
  check(snap?.kind === 'build', 'В снимке верный вид работ', String(snap?.kind))

  await q.goto(BASE + '/kontakty/#form', { waitUntil: 'networkidle' })
  await q.waitForTimeout(400)
  const state = await q.evaluate(() => ({
    shown: !document.querySelector('[data-calc-note]')?.hasAttribute('hidden'),
    text: document.querySelector('[data-calc-text]')?.textContent || '',
    kind: document.querySelector('#lf-kind')?.value,
    hidden: document.querySelector('[data-calc-value]')?.value || '',
  }))
  check(state.shown, 'Расчёт показан в заявке видимой строкой, а не только скрытым полем')
  check(state.kind === 'build', 'Вид работ подставлен из калькулятора', String(state.kind))
  check(
    state.hidden === state.text && state.hidden.length > 20,
    'Что показано, то и уйдёт: видимый текст совпадает со скрытым полем',
  )

  // Кнопка «Убрать» должна убирать всё: и строку, и поле, и снимок.
  await q.click('[data-calc-drop]')
  await q.waitForTimeout(200)
  const after = await q.evaluate(() => ({
    shown: !document.querySelector('[data-calc-note]')?.hasAttribute('hidden'),
    hidden: document.querySelector('[data-calc-value]')?.value || '',
    stored: sessionStorage.getItem('norma-calc'),
  }))
  check(!after.shown && !after.hidden && !after.stored, 'Кнопка «Убрать» снимает расчёт целиком')

  // Просроченный расчёт не подставляется: назавтра человек уже не помнит,
  // что он отвечал, и приложенный разбор стал бы для него сюрпризом.
  await q.evaluate(() => {
    localStorage.removeItem('norma-lead-draft')
    sessionStorage.setItem(
      'norma-calc',
      JSON.stringify({ at: Date.now() - 60 * 60 * 1000, kind: 'design', summary: 'Старый расчёт' }),
    )
  })
  // reload, а не goto на тот же адрес с якорем: смена якоря — навигация
  // внутри документа, страница не перезагружается и скрипт формы
  // не запускается заново. На этом тест уже один раз соврал.
  await q.reload({ waitUntil: 'networkidle' })
  await q.waitForTimeout(400)
  const stale = await q.evaluate(() => ({
    shown: !document.querySelector('[data-calc-note]')?.hasAttribute('hidden'),
    kind: document.querySelector('#lf-kind')?.value,
  }))
  check(!stale.shown && !stale.kind, 'Просроченный расчёт не подставляется')

  // Список видов работ в форме обязан совпадать с ответами калькулятора,
  // иначе подстановка промахнётся, а увидеть это без проверки нельзя.
  const opts = await q.$$eval('#lf-kind option', (els) => els.map((e) => e.value).filter(Boolean))
  for (const id of ['build', 'design', 'survey', 'demolition']) {
    check(opts.includes(id), `В форме есть вид работ «${id}»`)
  }

  await ctx.close()
}

await browser.close()

if (failed) {
  console.log(`\nОШИБОК: ${failed}`)
  process.exit(1)
}
console.log('\n✓ Форма работает правильно, заявки не теряются.')
