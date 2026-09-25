// Проверка боевого пути заявки: форма в браузере → PHP → письмо.
//
// Запуск:  npm run test:lead     (после npm run release -- ваш-домен.ru)
//
// Зачем отдельно от npm test. Остальные проверки гоняются на превью, где PHP
// нет вовсе: там форма честно показывает телефон вместо отправки, и весь
// обработчик остаётся непроверенным до самого хостинга. А ломается в нём
// ровно то, что не видно глазами: заявка уходит, посетитель видит «отправлено»,
// а письмо не доходит — или доходит пустым.
//
// Здесь поднимается настоящий PHP (php -S) на боевой сборке, браузер
// заполняет настоящую форму и нажимает настоящую кнопку, а письмо вместо
// отправки пишется в файл (NORMA_MAIL_DRY_RUN). Дальше проверяется, что
// в письме есть всё, что человек ввёл, — и что журнал заявок не отдаётся
// по прямой ссылке.
//
// Единственное, что подменяется на время проверки, — ALLOWED_HOST: браузер
// приходит с 127.0.0.1, а в боевой сборке там ваш домен. Файл возвращается
// на место в любом случае, даже если проверка упала.

import { execFileSync, spawn } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dist = join(root, 'dist')
const phpFile = join(dist, 'api/submit.php')
const logFile = join(dist, 'api/leads.log.php')
const PORT = 8123

const red = (s) => `\x1b[31m${s}\x1b[0m`
const green = (s) => `\x1b[32m${s}\x1b[0m`
let problems = 0
const ok = (m) => console.log(`  ${green('✓')} ${m}`)
const fail = (m) => { console.log(`  ${red('✗')} ${m}`); problems++ }

if (!existsSync(phpFile)) {
  console.log(red('Сначала соберите сайт: npm run release -- ваш-домен.ru'))
  process.exit(1)
}
try {
  execFileSync('php', ['-v'], { stdio: 'ignore' })
} catch {
  console.log(red('Нужен PHP в системе: без него боевой путь заявки не проверить.'))
  process.exit(1)
}

const original = readFileSync(phpFile, 'utf8')
const tmp = mkdtempSync(join(tmpdir(), 'norma-lead-'))
const mailFile = join(tmp, 'lead.eml')
let server

const cleanup = () => {
  writeFileSync(phpFile, original)
  if (existsSync(logFile)) rmSync(logFile)
  if (server) server.kill()
  rmSync(tmp, { recursive: true, force: true })
}
process.on('exit', cleanup)

// Заявка, которую «оставляет» проверка. Каждое значение потом ищется
// в письме: если форма перестанет класть в него город или вид работ,
// проверка упадёт с именем пропавшего поля, а не общим «что-то не так».
const LEAD = {
  name: 'Иван Петров',
  phone: '+7 900 123-45-67',
  email: 'ivan@example.com',
  city: 'Ростов-на-Дону',
  kind: 'build',
  kindLabel: 'Строительство',
  nrs: 'no',
  message: 'Нужна СРО, договор на 14 млн с застройщиком.',
}

console.log('\nБоевой путь заявки: форма → PHP → письмо\n')

writeFileSync(phpFile, original.replace(/const ALLOWED_HOST = '[^']*';/, "const ALLOWED_HOST = '127.0.0.1';"))
if (existsSync(logFile)) rmSync(logFile)

server = spawn('php', ['-S', `127.0.0.1:${PORT}`, '-t', dist], {
  env: { ...process.env, NORMA_MAIL_DRY_RUN: mailFile },
  stdio: 'ignore',
})

const base = `http://127.0.0.1:${PORT}`
let up = false
for (let i = 0; i < 40 && !up; i++) {
  try {
    const r = await fetch(`${base}/kontakty/`)
    up = r.ok
  } catch { await new Promise((r) => setTimeout(r, 250)) }
}
if (!up) { fail('PHP-сервер не поднялся'); process.exit(1) }

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } })
const page = await ctx.newPage()
await page.addInitScript(() => { try { localStorage.setItem('norma-cookie', 'necessary') } catch {} })
await page.goto(`${base}/kontakty/`, { waitUntil: 'networkidle' })

const form = page.locator('#form')
await form.locator('input[name=name]').fill(LEAD.name)
await form.locator('input[name=phone]').fill(LEAD.phone)
await form.locator('input[name=email]').fill(LEAD.email)
await form.locator('input[name=city]').fill(LEAD.city)
await form.locator('select[name=kind]').selectOption(LEAD.kind)
await form.locator('select[name=nrs]').selectOption(LEAD.nrs)
await form.locator('textarea[name=message]').fill(LEAD.message)
if (await form.locator('input[name=agree]').count()) await form.locator('input[name=agree]').check()
await form.locator('button[type=submit]').click()
await page.waitForTimeout(3000)

const shown = (await form.innerText()).replace(/\s+/g, ' ')
if (/Заявка отправлена/i.test(shown)) ok('посетитель видит «Заявка отправлена»')
else fail(`посетитель не увидел подтверждения: …${shown.slice(-140)}`)

await browser.close()

// ── Письмо ────────────────────────────────────────────────────────────────
if (!existsSync(mailFile)) {
  fail('письмо не сформировано — заявка до почты не дошла')
} else {
  const mail = readFileSync(mailFile, 'utf8')
  const mustHave = [
    ['имя', LEAD.name],
    ['телефон', LEAD.phone],
    ['e-mail для ответа', LEAD.email],
    ['город', LEAD.city],
    ['вид работ', LEAD.kindLabel],
    ['текст обращения', LEAD.message],
  ]
  const lost = mustHave.filter(([, v]) => !mail.includes(v)).map(([k]) => k)
  if (lost.length) fail(`в письме нет: ${lost.join(', ')}`)
  else ok('в письме всё, что ввёл человек')

  // Адрес отправителя обязан быть на домене сайта: с чужого домена письмо
  // не пройдёт SPF и уляжется в спам — молча, без единой ошибки на сайте.
  const from = (mail.match(/^From:.*<([^>]+)>/m) || [])[1] || ''
  const host = (readFileSync(phpFile, 'utf8').match(/const MAIL_FROM = '[^@]+@([^']+)'/) || [])[1] || ''
  if (from.endsWith(`@${host}`) && host && !host.includes('example')) ok(`письмо уходит от ${from}`)
  else fail(`отправитель ${from || '(пусто)'} — нужен ящик на домене сайта, иначе письма уйдут в спам`)

  if (mail.includes(`Reply-To: ${LEAD.email}`)) ok('на письмо можно ответить прямо из почты')
  else fail('нет заголовка Reply-To — ответить на заявку одной кнопкой не выйдет')
}

// ── Журнал ────────────────────────────────────────────────────────────────
if (!existsSync(logFile)) {
  fail('заявка не записалась в журнал — при сбое почты она потеряется')
} else {
  const log = readFileSync(logFile, 'utf8')
  if (log.startsWith('<?php exit;')) ok('журнал начинается с команды PHP «остановись»')
  else fail('журнал не защищён первой строкой — его отдаст любой nginx')
  if (log.includes(LEAD.phone)) ok('заявка записана в журнал до отправки письма')
  else fail('в журнале нет заявки')

  const direct = await fetch(`${base}/api/leads.log.php`)
  const body = await direct.text()
  if (body.trim() === '') ok('по прямой ссылке журнал не отдаёт ни байта')
  else fail(`журнал открывается в браузере — там персональные данные: ${body.slice(0, 80)}`)
}

// ── Чужой сайт ────────────────────────────────────────────────────────────
const foreign = await fetch(`${base}/api/submit.php`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Origin: 'https://chuzhoy-sayt.ru' },
  body: JSON.stringify({ access_key: 'x', message: 'подделка' }),
})
const foreignBody = await foreign.json().catch(() => ({}))
if (foreignBody.success === false) ok('заявку с чужого сайта обработчик не принимает')
else fail('чужой сайт может слать заявки от вашего имени')

console.log(
  problems
    ? `\n${red(`Путь заявки сломан: ${problems} проблем${problems === 1 ? 'а' : ''}. На хостинг в таком виде нельзя.`)}\n`
    : `\n${green('✓ Заявка доходит: форма, письмо, журнал и защита от чужих сайтов в порядке.')}\n`,
)
process.exit(problems ? 1 : 0)
