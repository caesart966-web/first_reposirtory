// Проверка всего, что сайт говорит поисковым системам.
//
// Запуск:  node scripts/check-seo.mjs dist   (входит в npm run check)
//
// Что стережёт эта проверка и чего НЕ делает соседняя. check-links.mjs
// смотрит на страницу глазами человека: битые ссылки, пустые заголовки,
// одинаковые описания. Здесь — то, что человек не видит вовсе и что
// ломается молча: canonical, ссылающийся не на себя; Open Graph без
// картинки; микроразметка, у которой узел ссылается на несуществующий
// @id; карта сайта, потерявшая страницу; лента, ведущая на удалённую
// статью. Ошибки этого класса не проявляются ни в браузере, ни в тестах —
// они проявляются через месяц отсутствием страницы в выдаче.
//
// Проверка знает про два режима сборки. Черновик (PUBLIC_NOINDEX=1)
// закрыт от поиска целиком, и требовать от него canonical бессмысленно —
// режим определяется по robots.txt.

import { readFileSync, existsSync, readdirSync } from 'node:fs'
import { join, relative, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = process.argv[2] || 'dist'
const here = dirname(fileURLToPath(import.meta.url))
const pub = join(here, '../public')

const problems = []
const warnings = []
const bad = (m) => problems.push(m)
const warn = (m) => warnings.push(m)

const walk = (dir) =>
  readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(join(dir, e.name)) : join(dir, e.name),
  )

const files = walk(root).filter((f) => f.endsWith('.html'))
if (files.length === 0) {
  console.error(`✗ В ${root} нет собранных страниц. Сначала: npm run build`)
  process.exit(1)
}

// ── Режим сборки ──────────────────────────────────────────────────────────
const robotsPath = join(root, 'robots.txt')
if (!existsSync(robotsPath)) bad('нет robots.txt')
const robots = existsSync(robotsPath) ? readFileSync(robotsPath, 'utf8') : ''
const draft = /Disallow:\s*\/\s*$/m.test(robots)

// ── Разбор страниц ────────────────────────────────────────────────────────
const attr = (html, re) => html.match(re)?.[1]
const meta = (html, name) =>
  attr(html, new RegExp(`<meta\\s+name="${name}"\\s+content="([^"]*)"`)) ??
  attr(html, new RegExp(`<meta\\s+property="${name}"\\s+content="([^"]*)"`))

const pages = []
for (const file of files) {
  const html = readFileSync(file, 'utf8')
  const url = '/' + relative(root, file).replace(/index\.html$/, '').replace(/\\/g, '/')
  pages.push({ file, url, html, is404: url === '/404.html' })
}

const indexable = pages.filter((p) => !p.is404)

// Подпапка, в которую собран сайт. На своём домене это «/», на превью —
// «/first_reposirtory/norma/». Берём её из canonical главной страницы:
// адреса в разметке записаны с подпапкой, а файлы в сборке лежат без неё,
// и без этой поправки проверка искала бы og-картинку не там.
const basePath = (() => {
  const home = pages.find((p) => p.url === '/')
  const canonical = home && home.html.match(/<link rel="canonical" href="([^"]*)"/)?.[1]
  return canonical ? new URL(canonical).pathname : '/'
})()

// Адрес из разметки → файл в сборке.
const localFile = (pathname) => join(root, pathname.slice(basePath.length))

for (const p of pages) {
  const { html, url } = p

  if (!/<html[^>]+lang="ru"/.test(html)) bad(`${url}: у <html> нет lang="ru"`)

  const robotsMeta = meta(html, 'robots')
  if (!robotsMeta) bad(`${url}: нет мета-тега robots`)

  // Страница 404 обязана быть закрыта в любом режиме сборки: она отдаётся
  // по любому несуществующему адресу.
  if (p.is404 && !/noindex/.test(robotsMeta ?? '')) bad('/404.html: страница не закрыта от индексации')

  const canonical = attr(html, /<link rel="canonical" href="([^"]*)"/)
  if (p.is404) {
    if (canonical) bad('/404.html: у страницы 404 не должно быть canonical')
  } else if (!canonical) {
    bad(`${url}: нет canonical`)
  }

  // ── Open Graph и Twitter ────────────────────────────────────────────────
  const need = [
    'og:type', 'og:site_name', 'og:title', 'og:description', 'og:url', 'og:locale',
    'og:image', 'og:image:width', 'og:image:height', 'og:image:alt',
    'twitter:card', 'twitter:title', 'twitter:description', 'twitter:image',
  ]
  for (const tag of need) if (!meta(html, tag)) bad(`${url}: нет ${tag}`)

  // og:url и canonical обязаны совпадать: расхождение — прямое указание
  // поисковику, что настоящий адрес страницы другой.
  const ogUrl = meta(html, 'og:url')
  if (canonical && ogUrl && canonical !== ogUrl) bad(`${url}: og:url (${ogUrl}) не совпадает с canonical (${canonical})`)

  // Картинка-превью должна существовать. Ссылка на несуществующий файл
  // даёт пустую карточку во всех мессенджерах сразу.
  const ogImage = meta(html, 'og:image')
  if (ogImage) {
    const path = new URL(ogImage).pathname
    if (!existsSync(localFile(path))) bad(`${url}: og:image ведёт на ${path} — такого файла в сборке нет`)
  }

  // ── Микроразметка ───────────────────────────────────────────────────────
  const ld = attr(html, /<script type="application\/ld\+json">([\s\S]*?)<\/script>/)
  if (!ld) {
    bad(`${url}: нет микроразметки JSON-LD`)
    continue
  }
  let graph
  try {
    graph = JSON.parse(ld)
  } catch (e) {
    bad(`${url}: микроразметка не разбирается как JSON (${e.message})`)
    continue
  }
  const nodes = graph['@graph'] ?? []
  const types = nodes.map((n) => n['@type'])

  // Объявленные узлы ищем по всему дереву, а не только на верхнем уровне:
  // вложенный объект с @id и содержимым — такое же объявление
  // (так объявлен знак организации внутри узла ProfessionalService).
  const ids = new Set()
  const declare = (v) => {
    if (Array.isArray(v)) return v.forEach(declare)
    if (!v || typeof v !== 'object') return
    if (typeof v['@id'] === 'string' && Object.keys(v).length > 1) ids.add(v['@id'])
    Object.values(v).forEach(declare)
  }
  declare(nodes)

  for (const t of ['ProfessionalService', 'WebSite']) {
    if (!types.includes(t)) bad(`${url}: в микроразметке нет узла ${t}`)
  }
  const page = nodes.find((n) => String(n['@id'] ?? '').endsWith('#webpage'))
  if (!page) bad(`${url}: в микроразметке нет узла страницы (#webpage)`)
  else if (canonical && page.url !== canonical) bad(`${url}: узел страницы указывает на ${page.url}, а canonical — на ${canonical}`)

  // Ссылки внутри страницы должны разрешаться. На чужие узлы (#org, #website
  // с главной) ссылаться можно — они объявлены здесь же.
  const refs = []
  const collect = (v) => {
    if (Array.isArray(v)) v.forEach(collect)
    else if (v && typeof v === 'object') {
      if (typeof v['@id'] === 'string' && Object.keys(v).length === 1) refs.push(v['@id'])
      Object.values(v).forEach(collect)
    }
  }
  collect(nodes)
  for (const ref of new Set(refs)) {
    if (!ids.has(ref)) bad(`${url}: микроразметка ссылается на несуществующий узел ${ref}`)
  }

  // Крошки: есть на каждой странице, кроме главной и 404.
  const isHome = url === '/'
  if (!isHome && !p.is404 && !types.includes('BreadcrumbList')) {
    bad(`${url}: нет хлебных крошек в микроразметке`)
  }

  // ── Статьи ──────────────────────────────────────────────────────────────
  const isArticle = /^\/baza-znaniy\/.+\//.test(url)
  if (isArticle) {
    if (meta(html, 'og:type') !== 'article') bad(`${url}: og:type должен быть article`)
    for (const tag of ['article:published_time', 'article:modified_time', 'article:author']) {
      if (!meta(html, tag)) bad(`${url}: нет ${tag}`)
    }
    const art = nodes.find((n) => n['@type'] === 'Article')
    if (!art) bad(`${url}: нет узла Article`)
    else {
      for (const field of ['headline', 'datePublished', 'dateModified', 'author', 'publisher', 'image']) {
        if (!art[field]) bad(`${url}: в узле Article нет поля ${field}`)
      }
      // Дата в разметке и дата в Open Graph — одно и то же событие.
      if (art.dateModified !== meta(html, 'article:modified_time')) {
        bad(`${url}: дата правки в разметке и в Open Graph разная`)
      }
    }
  }
}

// ── Карта сайта ───────────────────────────────────────────────────────────
const maps = readdirSync(root).filter((f) => /^sitemap-\d+\.xml$/.test(f))
if (maps.length === 0) bad('нет карты сайта (sitemap-0.xml)')

const entries = new Map()
for (const m of maps) {
  const xml = readFileSync(join(root, m), 'utf8')
  for (const block of xml.split('<url>').slice(1)) {
    const loc = block.match(/<loc>([^<]+)<\/loc>/)?.[1]
    if (!loc) continue
    entries.set(loc, {
      lastmod: block.match(/<lastmod>([^<]+)<\/lastmod>/)?.[1],
      priority: block.match(/<priority>([^<]+)<\/priority>/)?.[1],
      changefreq: block.match(/<changefreq>([^<]+)<\/changefreq>/)?.[1],
    })
  }
}

if (entries.size > 0) {
  const paths = new Set([...entries.keys()].map((u) => new URL(u).pathname))

  for (const p of indexable) {
    // Адрес страницы в карте сайта записан с подпапкой сборки.
    const want = [...paths].some((x) => x.endsWith(p.url) || x === p.url)
    if (!want) bad(`карта сайта потеряла страницу ${p.url}`)
  }
  if (paths.size !== indexable.length) {
    const extra = paths.size - indexable.length
    if (extra > 0) warn(`в карте сайта на ${extra} адрес(ов) больше, чем страниц в сборке`)
  }
  if ([...entries.keys()].some((u) => u.includes('/404'))) bad('страница 404 попала в карту сайта')

  for (const [loc, e] of entries) {
    if (!loc.endsWith('/')) bad(`адрес в карте сайта без косой черты на конце: ${loc}`)
    if (!e.lastmod) bad(`в карте сайта нет даты изменения у ${new URL(loc).pathname}`)
    if (!e.priority) warn(`в карте сайта нет приоритета у ${new URL(loc).pathname}`)
    if (!e.changefreq) warn(`в карте сайта нет частоты обновления у ${new URL(loc).pathname}`)
  }
}

// ── robots.txt ────────────────────────────────────────────────────────────
if (draft) {
  if (!/Disallow:\s*\//.test(robots)) bad('черновик не закрыт в robots.txt')
} else {
  if (!/^Sitemap:\s*https?:\/\/\S+sitemap-index\.xml/m.test(robots)) {
    bad('в robots.txt нет строки Sitemap с адресом карты сайта')
  }
  if (!/^Allow:\s*\//m.test(robots)) warn('в robots.txt нет строки Allow: /')
}

// ── Лента RSS ─────────────────────────────────────────────────────────────
const rssPath = join(root, 'rss.xml')
if (!existsSync(rssPath)) {
  bad('нет ленты rss.xml')
} else {
  const rss = readFileSync(rssPath, 'utf8')
  const links = [...rss.matchAll(/<link>([^<]+)<\/link>/g)].map((m) => m[1]).slice(1)
  const articles = indexable.filter((p) => /^\/baza-znaniy\/.+\//.test(p.url))
  if (links.length !== articles.length) {
    bad(`в ленте ${links.length} записей, а статей на сайте ${articles.length}`)
  }
  for (const l of links) {
    const path = new URL(l).pathname
    if (!articles.some((a) => path.endsWith(a.url))) bad(`лента ведёт на несуществующую статью ${path}`)
  }
  if (!/<atom:link[^>]+rel="self"/.test(rss)) warn('в ленте нет ссылки на саму себя (atom:link rel="self")')
  if (!/<language>ru<\/language>/.test(rss)) warn('в ленте не указан язык')
}

// ── Значки, манифест и ключ IndexNow ──────────────────────────────────────
for (const f of ['favicon.svg', 'favicon-32.png', 'favicon-192.png', 'apple-touch-icon.png', 'logo-512.png', 'og.png', 'site.webmanifest']) {
  if (!existsSync(join(root, f))) bad(`в сборке нет файла ${f}`)
}

const manifestPath = join(root, 'site.webmanifest')
if (existsSync(manifestPath)) {
  try {
    const m = JSON.parse(readFileSync(manifestPath, 'utf8'))
    for (const icon of m.icons ?? []) {
      // Пути в манифесте относительные нарочно: сайт может жить в подпапке.
      if (icon.src.startsWith('/')) bad(`в манифесте абсолютный путь к значку ${icon.src} — в подпапке он сломается`)
      else if (!existsSync(join(root, icon.src))) bad(`манифест ссылается на несуществующий значок ${icon.src}`)
    }
  } catch (e) {
    bad(`site.webmanifest не разбирается как JSON (${e.message})`)
  }
}

const seoSrc = readFileSync(join(here, '../src/config/seo.ts'), 'utf8')
const key = seoSrc.match(/indexNowKey:\s*'([^']*)'/)?.[1]
if (!key) bad('в src/config/seo.ts нет ключа IndexNow')
else if (!existsSync(join(pub, `${key}.txt`))) {
  bad(`ключ IndexNow ${key} есть в настройках, но файла public/${key}.txt нет — отправку отклонят`)
} else if (readFileSync(join(pub, `${key}.txt`), 'utf8').trim() !== key) {
  bad(`файл public/${key}.txt содержит не тот ключ, что в настройках`)
}

// ── Вывод ─────────────────────────────────────────────────────────────────
if (warnings.length > 0) {
  console.log(`Предупреждения (${warnings.length}):`)
  warnings.forEach((w) => console.log(`  ! ${w}`))
  console.log('')
}

if (problems.length > 0) {
  console.error(`✗ Проблемы для поисковиков (${problems.length}):`)
  problems.forEach((p) => console.error(`  · ${p}`))
  process.exit(1)
}

console.log(
  `✓ Мета-теги, микроразметка, карта сайта, лента и значки в порядке: ${pages.length} страниц` +
    (draft ? ' (черновик закрыт от индексации)' : ''),
)
