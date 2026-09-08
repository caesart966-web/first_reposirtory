// Подстановка реального домена во все служебные адреса сайта.
//
// До покупки домена везде стоит плейсхолдер https://example.com — в canonical
// и og:url одиннадцати страниц, в адресе картинки для мессенджеров, в карте
// сайта и в robots.txt. Мест много, и пропустить одно легко: страница с чужим
// canonical выпадает из поиска молча, без единой ошибки в консоли.
//
// Поэтому подстановка — одна команда, а не ручной поиск по файлам:
//
//   node scripts/set-domain.mjs sro-rostov.ru
//   node scripts/set-domain.mjs https://sro-rostov.ru
//
// Скрипт заодно убирает пометку TODO про домен: она нужна была ровно до
// этого момента. Проверку, что плейсхолдеров не осталось, делает набор
// og-sitemap.mjs.
import { readFileSync, writeFileSync } from 'node:fs'
import { readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const PLACEHOLDER = 'https://example.com'
const TODO = /^[ \t]*<!-- TODO: замените example\.com на реальный домен сайта -->\n/gm
const SKIP = new Set(['node_modules', 'dist', 'src', 'scripts', 'assets-src', '.git'])

const raw = process.argv[2]
if (!raw) {
  console.error('Укажите домен: node scripts/set-domain.mjs вашдомен.ру')
  process.exit(1)
}
// Принимаем и «сайт.ру», и «https://сайт.ру/», приводим к одному виду.
const host = raw.replace(/^https?:\/\//, '').replace(/\/+$/, '')
if (!/^[a-zа-я0-9.-]+\.[a-zа-я]{2,}$/i.test(host)) {
  console.error(`Не похоже на домен: «${raw}»`)
  process.exit(1)
}
const origin = `https://${host}`

/** Файлы, где может встретиться плейсхолдер: страницы и файлы для поисковика. */
function targets(dir = root, prefix = '') {
  const out = []
  for (const entry of readdirSync(dir)) {
    if (SKIP.has(entry) || entry.startsWith('.')) continue
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) out.push(...targets(full, `${prefix}${entry}/`))
    else if (entry === 'index.html' || entry === 'robots.txt' || entry === 'sitemap.xml') {
      out.push({ path: full, name: `${prefix}${entry}` })
    }
  }
  return out
}

let changed = 0
let left = 0
for (const file of targets()) {
  const before = readFileSync(file.path, 'utf8')
  const after = before.split(PLACEHOLDER).join(origin).replace(TODO, '')
  if (after !== before) {
    writeFileSync(file.path, after)
    const n = before.split(PLACEHOLDER).length - 1
    console.log(`${file.name}: заменено ${n}`)
    changed += 1
  }
  if (after.includes('example.com')) left += 1
}

console.log(`\nДомен: ${origin}`)
console.log(`Файлов изменено: ${changed}`)
if (left) {
  console.error(`ВНИМАНИЕ: в ${left} файлах ещё остался example.com — проверьте вручную`)
  process.exit(1)
}
console.log('Плейсхолдеров не осталось. Пересоберите сайт: npm run build')
