// Отправка изменённых страниц в IndexNow ПОСЛЕ заливки архива на хостинг.
//
// Запускает его робот GitHub Actions «НОРМА: отправить изменённые страницы
// в IndexNow» — кнопкой Run workflow. Из среды, где собирается сайт, адрес
// IndexNow закрыт сетевой политикой (30.09.2026), а у GitHub доступ есть.
//
//   node scripts/indexnow-live.mjs                 — список из indexnow.txt
//   node scripts/indexnow-live.mjs /stoimost/ …    — только эти адреса
//   node scripts/indexnow-live.mjs --all           — все страницы сайта
//   … --no-check                                   — без сверки версии
//
// В отличие от npm run indexnow, здесь ничего не собирается: адреса берутся
// с живого сайта, из его карты, — проверяется ровно то, что там лежит.
//
// Порядок проверок и почему он такой:
// 1. Карта сайта на хостинге должна совпасть до байта с картой архива,
//    из которого составлен indexnow.txt (отпечаток записан в файле).
//    Не совпала — архив ещё не залит или залит не тот; позвать робота
//    на старые страницы значит потратить переобход впустую, а повторно
//    он придёт не скоро.
// 2. Файл ключа <ключ>.txt должен открываться на сайте и содержать ключ:
//    иначе IndexNow отвергнет отправку ответом 403.
// 3. Каждый адрес из списка должен быть в карте сайта — опечатка в ручном
//    списке иначе ушла бы роботу как адрес несуществующей страницы.

import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const fail = (msg) => {
  console.error(`✗ ${msg}`)
  process.exit(1)
}

const args = process.argv.slice(2)
const all = args.includes('--all')
const noCheck = args.includes('--no-check')
const given = args.filter((a) => a.startsWith('/'))

const seo = readFileSync(resolve(here, '../src/config/seo.ts'), 'utf8')
const key = seo.match(/indexNowKey:\s*'([^']*)'/)?.[1] ?? ''
if (!/^[0-9a-zA-Z-]{8,128}$/.test(key)) fail('в src/config/seo.ts нет ключа IndexNow')

const list = readFileSync(resolve(here, '../indexnow.txt'), 'utf8')
const meta = (name) => list.match(new RegExp(`^# ${name}: (.+)$`, 'm'))?.[1]?.trim()
const host = meta('host')
const wantHash = meta('sitemap-sha256')
const archive = meta('archive') || 'последний архив'
if (!host) fail('в indexnow.txt нет строки «# host: …» — пересоберите список командой npm run changed')

// Только для проверки самого скрипта: локальная копия сайта и заглушка
// IndexNow вместо настоящих адресов. В роботе GitHub эти переменные не заданы.
const SITE_BASE = process.env.INDEXNOW_SITE_BASE || `https://${host}`
const API = process.env.INDEXNOW_API || 'https://api.indexnow.org/indexnow'

const get = async (path) => {
  const res = await fetch(`${SITE_BASE}${path}`, {
    headers: { 'User-Agent': 'Mozilla/5.0 (compatible; norma-site indexnow)' },
    signal: AbortSignal.timeout(25000),
  })
  if (!res.ok) throw new Error(`${path} — ответ ${res.status}`)
  return res.text()
}

// 1. Та ли версия на сайте
const liveMap = await get('/sitemap-0.xml').catch((e) => fail(`карта сайта не открылась: ${e.message}`))
if (!noCheck) {
  const liveHash = createHash('sha256').update(liveMap).digest('hex')
  if (!wantHash) fail('в indexnow.txt нет отпечатка карты сайта — пересоберите список командой npm run changed')
  if (liveHash !== wantHash) {
    fail(
      `на сайте не та версия: карта сайта не совпадает с архивом ${archive}.\n` +
        '  Залейте архив в ~/norma-sro.ru/public_html/, откройте сайт в инкогнито\n' +
        '  и запустите робота снова. Отправить без сверки — галочка «без проверки версии».',
    )
  }
  console.log(`✓ На сайте ${archive}: карта сайта совпадает.`)
}

// 2. Ключ на сайте
const keyText = await get(`/${key}.txt`).catch((e) => fail(`файл ключа не открылся: ${e.message}`))
if (keyText.trim() !== key) fail(`файл ${key}.txt на сайте есть, но в нём не ключ`)
console.log('✓ Файл ключа на месте.')

// 3. Адреса
const live = [...liveMap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1])
const livePaths = new Set(live.map((u) => new URL(u).pathname))
let paths
if (all) paths = [...livePaths]
else if (given.length) paths = given
else paths = list.split('\n').map((l) => l.trim()).filter((l) => l.startsWith('/'))
if (!paths.length) fail('список адресов пуст')
const missing = paths.filter((p) => !livePaths.has(p))
if (missing.length) fail(`этих адресов нет в карте сайта: ${missing.join(' ')}`)

const urlList = paths.map((p) => `https://${host}${p}`)
console.log(`Отправляю ${urlList.length} адрес(ов) в IndexNow…`)
const res = await fetch(API, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json; charset=utf-8' },
  body: JSON.stringify({ host, key, keyLocation: `https://${host}/${key}.txt`, urlList }),
})
const hints = {
  403: 'ключ не подтверждён — файл ключа на сайте не тот',
  422: 'адреса не совпадают с доменом',
  429: 'слишком частая отправка — попробуйте завтра',
}
if (res.ok || res.status === 202) {
  console.log(`✓ Принято (${res.status}). Яндекс придёт за страницами в ближайшие часы.`)
  for (const u of urlList) console.log(`  ${u}`)
} else {
  fail(`отказ ${res.status}${hints[res.status] ? ': ' + hints[res.status] : ''}`)
}
