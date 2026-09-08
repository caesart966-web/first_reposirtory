// Глубокая проверка собранной разметки. Без браузера — по файлам в dist/.
//
// check-links.mjs смотрит ссылки, мета-теги и заголовки. Здесь то, что
// он не трогает и что ломается тихо:
//
//   1. Картинки: пустой alt у смысловой, отсутствие width/height (браузеру
//      нечем зарезервировать место — вёрстка прыгает при загрузке),
//      ссылка на несуществующий файл.
//   2. Якоря: ссылка вида /uslugi/#nrs, где на целевой странице такого id нет.
//      Внешне работает — просто открывает начало страницы, и никто не замечает.
//   3. Ресурсы: og-картинка, значок, шрифты — то, что подключено, но могло
//      не попасть в сборку.
//   4. Мета: canonical совпадает с адресом страницы, og:url — с canonical,
//      есть lang, charset и viewport.
//   5. Внешние ссылки в новой вкладке без rel="noopener" — чужая страница
//      получает доступ к window.opener.
//   6. Порядок заголовков: h2 сразу после h1, без пропуска уровней —
//      по ним ходят с экранным диктором.
//   7. Поля формы без подписи.
//   8. Микроразметка: JSON-LD должен разбираться и содержать @context.
//   9. Косые в конце внутренних адресов: сайт собран с trailingSlash: always,
//      и ссылка без косой уедет на редирект, которого на статике нет.
//
// Запуск: node scripts/check-html.mjs [папка_сборки]
import { readFileSync, existsSync } from 'fs'
import { readdir } from 'fs/promises'
import { join, dirname } from 'path'

const DIST = process.argv[2] || 'dist'

const htmlFiles = async (dir) => {
  const out = []
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, e.name)
    if (e.isDirectory()) out.push(...(await htmlFiles(full)))
    else if (e.name.endsWith('.html')) out.push(full)
  }
  return out
}

const files = (await htmlFiles(DIST)).sort()
const home = readFileSync(join(DIST, 'index.html'), 'utf8')
const canonicalHome = home.match(/<link rel="canonical" href="([^"]+)"/)?.[1] || 'https://example.ru/'
const BASE = new URL(canonicalHome).pathname.replace(/\/$/, '')

const urlOf = (f) => '/' + f.slice(DIST.length + 1).replace(/index\.html$/, '').replace(/\\/g, '/')
const strip = (p) => (BASE && p.startsWith(BASE + '/') ? p.slice(BASE.length) : p)

// Собираем все id на каждой странице — понадобятся для проверки якорей.
const idsByUrl = new Map()
for (const f of files) {
  const html = readFileSync(f, 'utf8')
  idsByUrl.set(urlOf(f), new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1])))
}

const problems = []
const warnings = []

for (const f of files) {
  const html = readFileSync(f, 'utf8')
  const url = urlOf(f)
  const p = (m) => problems.push(`${url}: ${m}`)
  const w = (m) => warnings.push(`${url}: ${m}`)

  // ── Каркас документа ──
  if (!/<html[^>]+lang="ru"/.test(html)) p('нет lang="ru" у <html>')
  if (!/<meta charset="utf-8"/i.test(html)) p('нет <meta charset>')
  if (!/name="viewport"/.test(html)) p('нет <meta viewport>')

  // ── Canonical и Open Graph ──
  //
  // У страницы, закрытой от поиска, canonical не требуется: 404 отдаётся
  // по любому несуществующему адресу, и указывать ей не на что.
  const noindex = /content="noindex/.test(html)
  const canonical = html.match(/<link rel="canonical" href="([^"]+)"/)?.[1]
  if (!canonical && !noindex) p('нет canonical')
  else if (canonical && new URL(canonical).pathname !== url) p(`canonical указывает на ${new URL(canonical).pathname}, а страница — ${url}`)
  const ogUrl = html.match(/property="og:url" content="([^"]+)"/)?.[1]
  if (canonical && ogUrl && ogUrl !== canonical) p('og:url не совпадает с canonical')

  // ── Картинки ──
  for (const m of html.matchAll(/<img\b[^>]*>/g)) {
    const tag = m[0]
    const src = tag.match(/\ssrc="([^"]+)"/)?.[1] || ''
    const alt = tag.match(/\salt="([^"]*)"/)
    const short = src.split('/').pop() || tag.slice(0, 40)
    if (!alt) p(`<img> без alt → ${short}`)
    if (!/\swidth="/.test(tag) || !/\sheight="/.test(tag)) {
      // Пиксель счётчика Метрики размерам не подлежит — он невидимый.
      if (!src.includes('mc.yandex.ru')) w(`<img> без width/height → ${short}`)
    }
    if (src.startsWith('/') && !src.startsWith('//')) {
      const file = join(DIST, strip(src))
      if (!existsSync(file)) p(`картинки нет в сборке → ${src}`)
    }
  }

  // ── Ресурсы: значок, og-картинка, шрифты, стили, скрипты ──
  for (const m of html.matchAll(/(?:href|src|content)="(\/[^"]+\.(?:svg|png|jpe?g|webp|woff2?|css|js))"/g)) {
    const file = join(DIST, strip(m[1]))
    if (!existsSync(file)) p(`файла нет в сборке → ${m[1]}`)
  }
  const og = html.match(/property="og:image" content="([^"]+)"/)?.[1]
  if (og) {
    const file = join(DIST, strip(new URL(og).pathname))
    if (!existsSync(file)) p(`og:image не собрана → ${og}`)
  }

  // ── Якоря ──
  for (const m of html.matchAll(/href="([^"]*#[^"]+)"/g)) {
    const raw = m[1]
    if (/^(https?:|mailto:|tel:)/.test(raw)) continue
    const [path, hash] = raw.split('#')
    const target = path === '' ? url : strip(path)
    const ids = idsByUrl.get(target)
    if (!ids) { p(`якорь ведёт на несуществующую страницу → ${raw}`); continue }
    if (!ids.has(hash)) p(`якорь #${hash} не найден на ${target} → ${raw}`)
  }

  // ── Косая в конце ──
  for (const m of html.matchAll(/href="(\/[^"#?]*)"/g)) {
    const href = m[1]
    // Файл, а не страница: у файла косой в конце не бывает.
    // Двенадцать знаков, а не пять: .webmanifest длиннее привычных .png и .xml.
    if (/\.[a-z0-9]{2,12}$/i.test(href)) continue
    if (!href.endsWith('/')) p(`адрес без косой в конце → ${href}`)
  }

  // ── Новая вкладка ──
  for (const m of html.matchAll(/<a\b[^>]*target="_blank"[^>]*>/g)) {
    if (!/rel="[^"]*noopener/.test(m[0])) p(`target="_blank" без rel="noopener" → ${m[0].slice(0, 70)}`)
  }

  // ── Порядок заголовков ──
  const levels = [...html.matchAll(/<h([1-6])\b/g)].map((m) => Number(m[1]))
  for (let i = 1; i < levels.length; i++) {
    if (levels[i] - levels[i - 1] > 1) w(`пропуск уровня заголовка: h${levels[i - 1]} → h${levels[i]}`)
  }

  // ── Поля формы ──
  //
  // Подписать поле можно тремя способами, и все три законные: label с for,
  // aria-label и — самый частый на этом сайте — поле, вложенное внутрь
  // самого label. Третий способ проверка сперва не знала и объявила
  // «без подписи» тридцать полей калькулятора и все галочки согласия.
  for (const m of html.matchAll(/<(input|textarea|select)\b[^>]*>/g)) {
    const tag = m[0]
    if (/type="(hidden|submit|button)"/.test(tag)) continue
    const id = tag.match(/\sid="([^"]+)"/)?.[1]
    // Вложено ли поле в label: смотрим назад от него до ближайшего
    // открывающего или закрывающего тега label.
    const before = html.slice(0, m.index)
    const openAt = before.lastIndexOf('<label')
    const closeAt = before.lastIndexOf('</label>')
    const insideLabel = openAt > closeAt
    const labelled =
      insideLabel ||
      /aria-label(?:ledby)?="/.test(tag) ||
      (id && new RegExp(`<label[^>]*for="${id}"`).test(html))
    if (!labelled) p(`поле формы без подписи → ${tag.slice(0, 60)}`)
  }

  // ── Микроразметка ──
  for (const m of html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
    try {
      const data = JSON.parse(m[1])
      if (!data['@context']) p('в JSON-LD нет @context')
    } catch (e) {
      p(`JSON-LD не разбирается: ${e.message}`)
    }
  }
}

// ── Карта сайта ──
const sitemap = existsSync(join(DIST, 'sitemap-0.xml')) ? readFileSync(join(DIST, 'sitemap-0.xml'), 'utf8') : ''
const inSitemap = new Set([...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => new URL(m[1]).pathname))
for (const f of files) {
  const url = urlOf(f)
  if (url === '/404.html' || url.endsWith('404.html')) continue
  if (!inSitemap.has(url)) warnings.push(`${url}: страницы нет в карте сайта`)
}

console.log(`Проверено страниц: ${files.length}\n`)
if (warnings.length) {
  console.log('ЗАМЕЧАНИЯ:')
  for (const x of warnings) console.log('  · ' + x)
  console.log()
}
if (problems.length) {
  console.log('ПРОБЛЕМЫ:')
  for (const x of problems) console.log('  ✗ ' + x)
  process.exit(1)
}
console.log('✓ Разметка, картинки, якоря, ресурсы и микроразметка в порядке.')
