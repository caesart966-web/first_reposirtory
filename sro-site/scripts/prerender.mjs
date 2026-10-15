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
const { render } = await import(pathToFileURL(join(ssrDir, 'entry-server.js')).href)

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
  // Глубина по умолчанию — та же, что в detail.tsx и service.tsx.
  const root = attr(attrs, 'data-root') ?? (sro !== undefined ? '../' : service !== undefined ? '../../' : '')
  const body = render({ root, sro, service })
  if (!/<h1[\s>]/.test(body)) throw new Error(`${name}: в собранной странице нет <h1>`)

  const viewport = html.match(/<meta name="viewport"[^>]*>/)
  if (!viewport) throw new Error(`${name}: нет <meta name="viewport">`)
  html = html.replace(viewport[0], `${viewport[0]}\n    ${HEAD}`)
  html = html.replace(whole, `<div id="root"${attrs}>${body}</div>`)
  writeFileSync(file, html)
  done++
  console.log(`  ${name.padEnd(48)} ${(body.length / 1024).toFixed(0).padStart(4)} КБ текста`)
}

if (done !== 11) throw new Error(`Страниц ${done}, ожидалось 11 — новая страница? Поправьте число здесь.`)
rmSync(ssrDir, { recursive: true, force: true })
console.log(`prerender: текст вписан в ${done} страниц`)
