// Собирает индекс для поиска по сайту из готовой сборки.
//
// Запускается сразу после astro build (см. npm run build) и кладёт
// dist/search-index.json. Читает именно собранные страницы, а не исходники:
// так в индекс попадает ровно то, что видит посетитель, включая тексты,
// которые страницы собирают из конфигов на лету.
//
// Индекс не грузится вместе со страницей — строка поиска забирает его
// при первом обращении к поиску. Поэтому его вес не влияет на скорость
// открытия сайта.

import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const root = process.argv[2] || 'dist'

const walk = (dir) =>
  readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(join(dir, e.name)) : join(dir, e.name),
  )

// Что не индексируем: страницу «не найдено» и саму страницу результатов.
const SKIP = [/^\/404\.html$/, /^\/poisk\/$/]

/**
 * Убирает куски, помеченные data-nosearch, вместе с содержимым.
 *
 * Это обвязка страницы: форма заявки, хлебные крошки, карточки «другие
 * услуги» и «читайте дальше». Они одинаковы на двадцати страницах,
 * и без этого поиск по слову «заявка» находил бы весь сайт разом,
 * а индекс весил вдвое больше нужного.
 *
 * Считаем вложенность одноимённых тегов, а не ищем первый закрывающий:
 * внутри отмеченного <section> лежат другие <section>.
 */
const stripMarked = (html) => {
  let out = html
  for (let guard = 0; guard < 200; guard++) {
    const open = out.match(/<([a-z]+)[^>]*\sdata-nosearch[\s>]/i)
    if (!open) break
    const tag = open[1]
    const start = open.index
    const re = new RegExp(`<${tag}\\b[^>]*>|</${tag}\\s*>`, 'gi')
    re.lastIndex = start + open[0].length - 1
    let depth = 1
    let end = out.length
    let m
    while ((m = re.exec(out))) {
      depth += m[0][1] === '/' ? -1 : 1
      if (depth === 0) {
        end = m.index + m[0].length
        break
      }
    }
    out = out.slice(0, start) + ' ' + out.slice(end)
  }
  return out
}

const text = (html) =>
  html
    // Служебное содержимое: скрипты, стили и рисунки. В svg лежат подписи
    // к иконкам — в поиске они дали бы «стрелка» и «конверт» на каждой странице.
    .replace(/<(script|style|svg)[\s\S]*?<\/\1>/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&mdash;/g, '—')
    .replace(/&laquo;/g, '«')
    .replace(/&raquo;/g, '»')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    // Мягкий перенос: он стоит внутри слов в шапках таблиц и разорвал бы их.
    .replace(/­/g, '')
    .replace(/\s+/g, ' ')
    .trim()

const docs = []

for (const file of walk(root).filter((f) => f.endsWith('.html'))) {
  const html = readFileSync(file, 'utf8')
  const url = '/' + relative(root, file).replace(/index\.html$/, '').replace(/\\/g, '/')
  if (SKIP.some((re) => re.test(url))) continue

  const raw = html.match(/<main[^>]*>([\s\S]*)<\/main>/)?.[1]
  const main = raw ? stripMarked(raw) : raw
  if (!main) {
    console.warn(`  ! ${url}: нет <main>, страница в поиск не попала`)
    continue
  }

  const h1 = text(main.match(/<h1[^>]*>([\s\S]*?)<\/h1>/)?.[1] ?? '')
  const headings = [...main.matchAll(/<h[23][^>]*>([\s\S]*?)<\/h[23]>/g)]
    .map((m) => text(m[1]))
    .filter(Boolean)
  const description = html.match(/<meta name="description" content="([^"]*)"/)?.[1] ?? ''

  const body = text(main)
  if (!h1 || !body) {
    console.warn(`  ! ${url}: пустой заголовок или текст`)
    continue
  }

  docs.push({ u: url, t: h1, d: text(description), h: headings, b: body })
}

docs.sort((a, b) => a.u.localeCompare(b.u))

const out = join(root, 'search-index.json')
writeFileSync(out, JSON.stringify(docs))
const kb = (statSync(out).size / 1024).toFixed(0)
console.log(`✓ Индекс поиска: ${docs.length} страниц, ${kb} КБ`)
