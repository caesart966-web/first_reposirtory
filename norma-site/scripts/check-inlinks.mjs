// Перелинковка: на каждую статью и каждую страницу услуги ведут ссылки
// из ТЕКСТА других страниц.
//
// ЗАЧЕМ. Меню, подвал и оглавление базы знаний ссылаются на всё подряд,
// и для поисковика такая ссылка значит мало: она стоит на каждой странице.
// Вес и повод обойти страницу дают ссылки из текста — там, где о ней
// заходит речь. 15.10.2026 подсчёт показал: на три статьи («Что даёт
// членство», «Смена уровня ответственности», «СРО по видам работ»)
// и четыре услуги (лицензии, охрана труда, промбезопасность, юридические)
// из текста не вело ни одной ссылки, ещё на семь статей — по одной.
// Новый сайт, 20 страниц в Search Console «не проиндексированы» — сироты
// обходятся последними. Ссылки расставлены по смыслу; проверка держит
// порог, чтобы новая статья не вышла сиротой снова.
//
// ЧТО СЧИТАЕТСЯ. Ссылки внутри <main>, кроме header, footer, nav (крошки)
// и блоков data-nosearch («Читайте дальше», «Другие услуги», форма) —
// той же обвязки, которую не берёт поиск по сайту. Ссылки с оглавлений
// /baza-znaniy/ и /uslugi/ не в счёт: они есть у всех.
//
// ПОРОГ. Статья — не меньше двух страниц-источников, услуга — не меньше
// одной. Упало — впишите ссылку на страницу в текст близких по теме
// статей: там, где о ней действительно заходит речь.
//
// Запуск: node scripts/check-inlinks.mjs [папка_сборки]

import { readdir, readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

const DIST = resolve(process.argv[2] || 'dist')
const NEED = { article: 2, service: 1 }
const INDEXES = new Set(['/baza-znaniy/', '/uslugi/'])
const VOID = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'])

// Подпапка сборки — из canonical главной, как в check-links.mjs.
async function detectBase() {
  const home = join(DIST, 'index.html')
  if (!existsSync(home)) return '/'
  const html = await readFile(home, 'utf8')
  const m = html.match(/<link rel="canonical" href="([^"]+)"/)
  return m ? new URL(m[1]).pathname : '/'
}

async function walk(dir) {
  const out = []
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) out.push(...(await walk(p)))
    else if (e.name === 'index.html') out.push(p)
  }
  return out
}

/** Ссылки из текста страницы: внутри <main>, вне обвязки. */
function contentLinks(html) {
  const clean = html.replace(/<(script|style|svg)\b[\s\S]*?<\/\1>/gi, '').replace(/<!--[\s\S]*?-->/g, '')
  const tag = /<(\/?)([a-zA-Z][\w-]*)([^>]*)>/g
  const stack = []
  let skip = 0
  let inMain = 0
  const links = []
  for (let m = tag.exec(clean); m; m = tag.exec(clean)) {
    const [, close, rawName, attrs] = m
    const name = rawName.toLowerCase()
    if (VOID.has(name)) continue
    if (close) {
      while (stack.length) {
        const top = stack.pop()
        if (top.skip) skip--
        if (top.main) inMain--
        if (top.name === name) break
      }
      continue
    }
    if (attrs.trimEnd().endsWith('/')) continue
    const isSkip = /\sdata-nosearch(?=[\s=>]|$)/.test(attrs) || ['header', 'footer', 'nav'].includes(name)
    const isMain = name === 'main'
    stack.push({ name, skip: isSkip, main: isMain })
    if (isSkip) skip++
    if (isMain) inMain++
    if (name === 'a' && inMain && !skip) {
      const href = attrs.match(/\shref="([^"]*)"/)?.[1]
      if (href && href.startsWith('/')) links.push(href.split('#')[0].split('?')[0])
    }
  }
  return links
}

const base = await detectBase()
const files = await walk(DIST)
const pages = new Map()
for (const f of files) {
  const rel = '/' + relative(DIST, f).replace(/\\/g, '/').replace(/index\.html$/, '')
  if (rel.startsWith('/poisk/') || rel.startsWith('/404')) continue
  pages.set(rel, await readFile(f, 'utf8'))
}

const inbound = new Map([...pages.keys()].map((p) => [p, new Set()]))
for (const [src, html] of pages) {
  for (let href of contentLinks(html)) {
    if (!href.startsWith(base)) continue
    href = '/' + href.slice(base.length)
    if (!href.endsWith('/')) href += '/'
    if (href !== src && inbound.has(href) && !INDEXES.has(src)) inbound.get(href).add(src)
  }
}

const kindOf = (p) =>
  /^\/baza-znaniy\/[^/]+\/$/.test(p) ? 'article' : /^\/uslugi\/[^/]+\/$/.test(p) ? 'service' : null

const weak = []
let checked = 0
for (const [p, from] of inbound) {
  const kind = kindOf(p)
  if (!kind) continue
  checked++
  if (from.size < NEED[kind]) weak.push({ p, kind, n: from.size, from: [...from] })
}

if (weak.length) {
  console.error('✗ Страницы, на которые почти не ведут ссылки из текста сайта:')
  for (const w of weak.sort((a, b) => a.n - b.n)) {
    const what = w.kind === 'article' ? 'статья' : 'услуга'
    console.error(`  ${w.p} (${what}) — ${w.n} из ${NEED[w.kind]}${w.from.length ? ': ' + w.from.join(', ') : ''}`)
  }
  console.error('  Впишите ссылку на эти страницы в текст близких по теме статей — там, где о них заходит речь.')
  process.exit(1)
}
console.log(`✓ Перелинковка: на каждую из ${checked} статей и услуг ведут ссылки из текста (статья — от ${NEED.article}, услуга — от ${NEED.service}).`)
