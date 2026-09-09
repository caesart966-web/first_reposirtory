// Запускает все браузерные проверки сайта.
//
// Зачем отдельный запускатель. Проверки открывают собранный сайт по адресу
// http://127.0.0.1:4321 — и раньше этот адрес нужно было поднять руками.
// Кто не знал (а знать неоткуда), получал на ровном месте
// «page.goto: net::ERR_CONNECTION_REFUSED» и решал, что сломан сайт.
// Теперь сервер поднимается сам и гасится после проверок.
//
// Если на 4321 уже кто-то отвечает — берём его и ничего не трогаем:
// у разработчика может быть открыт свой предпросмотр.

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'

const PORT = 4321
const BASE = `http://127.0.0.1:${PORT}`

const TESTS = [
  ['test-calc.mjs', 'калькулятор «нужна ли СРО»'],
  ['test-form.mjs', 'форма заявки'],
  ['test-cost.mjs', 'калькулятор взносов'],
  ['test-a11y.mjs', 'клавиатура, меню и работа без скриптов'],
  ['test-contrast.mjs', 'контраст надписей'],
  ['test-widths.mjs', 'вёрстка на всех ширинах'],
  ['test-tables.mjs', 'таблицы'],
  ['test-hero-photo.mjs', 'текст поверх фотографий'],
  ['test-search.mjs', 'поиск по сайту'],
  ['test-pages.mjs', 'страницы в браузере'],
]

if (!existsSync('dist/index.html')) {
  console.error('✗ Сайт не собран. Сначала: npm run build')
  process.exit(1)
}

const alive = async () => {
  try {
    const res = await fetch(BASE + '/', { signal: AbortSignal.timeout(1500) })
    return res.ok
  } catch {
    return false
  }
}

let server = null
if (await alive()) {
  console.log(`Сайт уже отдаётся на ${BASE} — беру его.`)
} else {
  server = spawn(process.execPath, ['scripts/serve-subpath.mjs', '/', String(PORT)], {
    stdio: 'ignore',
  })
  const until = Date.now() + 15000
  while (Date.now() < until && !(await alive())) {
    await new Promise((r) => setTimeout(r, 200))
  }
  if (!(await alive())) {
    server.kill()
    console.error(`✗ Не удалось поднять сайт на ${BASE}`)
    process.exit(1)
  }
  console.log(`Сайт поднят на ${BASE}`)
}

const stop = () => {
  if (server && !server.killed) server.kill()
}
process.on('exit', stop)
process.on('SIGINT', () => {
  stop()
  process.exit(130)
})

const run = (file) =>
  new Promise((resolve) => {
    const child = spawn(process.execPath, ['scripts/' + file], { stdio: 'inherit' })
    child.on('close', (code) => resolve(code ?? 1))
  })

let failed = null
for (const [file, what] of TESTS) {
  const code = await run(file)
  if (code !== 0) {
    failed = what
    break
  }
}

stop()

if (failed) {
  console.error(`\n✗ Проверка не прошла: ${failed}`)
  process.exit(1)
}
console.log('\n✓ Все проверки пройдены.')
