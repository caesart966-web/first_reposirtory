// Текст страниц прямо в HTML (15.10.2026).
//
// Запускается сам после `npm run build` (postbuild в package.json): берёт
// серверную сборку src/entry-server.tsx из dist-ssr/ и вписывает готовую
// разметку в <div id="root"> каждой страницы в dist/. До этого корень был
// пустым, и поисковик без JavaScript видел страницу без единого слова
// (Search Console: пять страниц услуг «Обнаружена, не проиндексирована»).
//
// Какая страница какая — читается из самого HTML, как в точках входа:
// data-sro (вид СРО), data-service (услуга), data-root (глубина).
//
// Посетитель видит сайт как раньше. Скрипт страницы собирает её заново
// (createRoot), а готовый текст до этого спрятан: в <head> встаёт строчка,
// которая ставит <html> класс pre-wait (#root прозрачен), точка входа снимает
// его сразу после первой отрисовки (lib/mounted.ts). Без скрипта класса нет —
// текст виден, как и нужно поисковику. Если скрипт не пришёл за 4 секунды
// (очень медленная сеть, старый браузер), готовый текст показывается сам:
// pre-late открывает блоки, которые иначе выплывают по прокрутке, arrived
// снимает вступление первого экрана, чтобы пересборка его не повторила.
//
// Строчка стоит сразу после viewport, до стилей: встроенный скрипт после
// <link rel="stylesheet"> ждал бы загрузки стилей и задерживал разбор страницы.
import { readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const site = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dist = join(site, 'dist')
const ssrDir = join(site, 'dist-ssr')
const { render, ARTICLE_SLUGS } = await import(pathToFileURL(join(ssrDir, 'entry-server.js')).href)

const HEAD =
  '<style>html.pre-wait #root{opacity:0}' +
  'html.pre-late .reveal,html.pre-late .reveal-words .w>span{opacity:1!important;transform:none!important}</style>' +
  '<script>(function(h){h.classList.add("pre-wait");setTimeout(function(){' +
  'if(h.classList.contains("pre-wait")){h.classList.remove("pre-wait");h.classList.add("pre-late","arrived")}' +
  '},4000)})(document.documentElement)</script>'

const pages = []
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) walk(path)
    else if (name === 'index.html') pages.push(path)
  }
}
walk(dist)

const attr = (attrs, name) => attrs.match(new RegExp(`\\b${name}="([^"]*)"`))?.[1]

// Сколько страниц ожидать — столько же index.html, сколько в исходниках
// (каталоги, как в build-sitemap.mjs): пропавшая при сборке страница
// роняет сборку, а не уходит на хостинг молча.
const SKIP = new Set(['node_modules', 'dist', 'dist-ssr', 'public', 'src', 'scripts', 'assets-src'])
const sources = []
const walkSources = (dir) => {
  for (const name of readdirSync(dir)) {
    if (SKIP.has(name) || name.startsWith('.')) continue
    const path = join(dir, name)
    if (statSync(path).isDirectory()) walkSources(path)
    else if (name === 'index.html') sources.push(path)
  }
}
walkSources(site)

const articlesSeen = new Set()
let done = 0
for (const file of pages) {
  const name = relative(dist, file)
  let html = readFileSync(file, 'utf8')
  const roots = [...html.matchAll(/<div id="root"([^>]*)>([\s\S]*?)<\/div>/g)]
  if (roots.length !== 1) throw new Error(`${name}: ожидался один <div id="root">, найдено ${roots.length}`)
  const [whole, attrs, inner] = roots[0]
  if (inner.trim()) throw new Error(`${name}: корень уже заполнен — prerender запущен второй раз?`)

  const sro = attr(attrs, 'data-sro')
  const service = attr(attrs, 'data-service')
  const pageKind = attr(attrs, 'data-page')
  const article = attr(attrs, 'data-article')
  // Глубина по умолчанию — та же, что в detail.tsx, service.tsx и stati.tsx.
  const root =
    attr(attrs, 'data-root') ??
    (sro !== undefined || pageKind !== undefined ? '../' : service !== undefined || article !== undefined ? '../../' : '')
  const body = render({ root, sro, service, page: pageKind, article })
  if (article !== undefined) articlesSeen.add(article)
  if (!/<h1[\s>]/.test(body)) throw new Error(`${name}: в собранной странице нет <h1>`)

  const viewport = html.match(/<meta name="viewport"[^>]*>/)
  if (!viewport) throw new Error(`${name}: нет <meta name="viewport">`)
  html = html.replace(viewport[0], `${viewport[0]}\n    ${HEAD}`)
  html = html.replace(whole, `<div id="root"${attrs}>${body}</div>`)
  writeFileSync(file, html)
  done++
  console.log(`  ${name.padEnd(48)} ${(body.length / 1024).toFixed(0).padStart(4)} КБ текста`)
}

if (done !== sources.length) throw new Error(`Страниц в сборке ${done}, в исходниках ${sources.length}`)
// Каждая статья из content/articles.ts должна иметь страницу, и наоборот:
// иначе забыли `npm run articles` после правки списка.
const missing = ARTICLE_SLUGS.filter((slug) => !articlesSeen.has(slug))
const extra = [...articlesSeen].filter((slug) => !ARTICLE_SLUGS.includes(slug))
if (missing.length || extra.length) {
  throw new Error(
    `Статьи и страницы разошлись (запустите npm run articles): без страницы — ${missing.join(', ') || 'нет'}; ` +
      `страница без статьи — ${extra.join(', ') || 'нет'}`,
  )
}
rmSync(ssrDir, { recursive: true, force: true })
console.log(`prerender: текст вписан в ${done} страниц`)
