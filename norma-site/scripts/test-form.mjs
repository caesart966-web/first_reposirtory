// Проверка формы заявки: валидация, маска телефона, защита от ботов,
// честное сообщение об ошибке вместо ложного «отправлено».
//
// Запуск: node scripts/test-form.mjs [адрес]

import { chromium } from 'playwright'

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
await page.focus('#lf-name')
const reachable = []
for (let i = 0; i < 8; i++) {
  await page.keyboard.press('Tab')
  reachable.push(await page.evaluate(() => document.activeElement?.id || document.activeElement?.tagName))
}
check(reachable.includes('lf-submit'), 'Кнопка отправки достижима с клавиатуры', reachable.join(','))

await browser.close()

if (failed) {
  console.log(`\nОШИБОК: ${failed}`)
  process.exit(1)
}
console.log('\n✓ Форма работает правильно, заявки не теряются.')
