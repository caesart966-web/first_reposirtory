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
// С 20.10.2026 готовый текст виден сразу, а скрипт страницы его подхватывает
// (hydrateRoot, src/lib/start.tsx) — раньше текст был спрятан классом
// pre-wait, пока скрипт не соберёт страницу заново, и первый экран на
// телефоне ждал скрипт ~1,9 с. В <head> встаёт строчка, которая до первой
// отрисовки:
// - решает, пришёл ли человек со своей страницы или кнопкой «Назад»
//   (как lib/arrival.ts): тогда arrived — без вступления первого экрана,
//   и arrived-settling — блоки, выплывающие по прокрутке, видны сразу, пока
//   скрипт не подхватил страницу (иначе плавная смена страниц снимала бы
//   их пустыми); ставит data-arrival, чтобы скрипт не решал это второй раз;
// - через 4 секунды без скрипта (очень медленная сеть, старый браузер)
//   ставит pre-late: открывает блоки, которые иначе ждали бы скрипта.
//   Скрипт успел — класс mounted (lib/mounted.ts), и pre-late не нужен.
//
// Строчка стоит сразу после viewport, до стилей: встроенный скрипт после
// <link rel="stylesheet"> ждал бы загрузки стилей и задерживал разбор страницы.
import { readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const site = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dist = join(site, 'dist')
const ssrDir = join(site, 'dist-ssr')
const { render, ARTICLE_SLUGS, checkArticlePlaces } = await import(pathToFileURL(join(ssrDir, 'entry-server.js')).href)
checkArticlePlaces()

const HEAD =
  '<style>html.pre-late .reveal,html.pre-late .reveal-words .w>span{opacity:1!important;transform:none!important}</style>' +
  '<script>(function(h){try{var n=performance.getEntriesByType("navigation")[0],i=!!n&&n.type==="back_forward";' +
  'if(!i&&document.referrer)i=new URL(document.referrer).origin===location.origin;' +
  'if(i)h.classList.add("arrived","arrived-settling")}catch(e){}h.setAttribute("data-arrival","");' +
  'setTimeout(function(){if(!h.classList.contains("mounted"))h.classList.add("pre-late","arrived")},4000)' +
  '})(document.documentElement)</script>'

// Строчка в конце <body> — для плавной смены страниц (20.10.2026).
// Chrome решает, будет ли смена, в момент первой отрисовки новой страницы —
// по правилу @view-transition из её стилей. Пока скрипт блокировал отрисовку,
// к этому моменту стили были уже применены: скрипт сам их читал. Без
// блокировки первая отрисовка опережала применение стилей, Chrome считал,
// что страница смену не заказывала, и переход пропадал — через раз,
// а при медленном скрипте почти всегда (10 переходов из 10 без смены).
// Встроенный скрипт в конце <body> не даёт разбору страницы закончиться,
// пока стили не загружены, и читает стиль корня — к первой отрисовке правило
// уже известно (20 переходов из 20). Скрипт страницы при этом по-прежнему
// не ждут. Стережёт test-site.mjs: «переход между страницами: срабатывает».
const TAIL = '<script>getComputedStyle(document.documentElement).viewTransitionName</script>'

// Шрифты текста — заранее (20.10.2026). Пока скрипт блокировал отрисовку,
// шрифты успевали прийти к первому кадру сами. Теперь готовый текст виден
// раньше, и без предзагрузки он на ~0,6 с показывался запасным шрифтом,
// а затем строки перескакивали на Onest и Brygada (сдвиг вёрстки до 0,03).
// С предзагрузкой текст сразу фирменным шрифтом, сдвига нет, а первый кадр
// всё равно раньше прежнего. Четыре файла — кириллица и латиница обоих
// шрифтов: в латинской части не только латиница, но пробел, цифры, «» и —.
const FONT_RE = /^(onest|brygada-1918)-(cyrillic|latin)-wght-normal-[\w-]+\.woff2$/
const fonts = readdirSync(join(dist, 'assets')).filter((name) => FONT_RE.test(name)).sort()
if (fonts.length !== 4) throw new Error(`Шрифтов для предзагрузки ${fonts.length}, ожидалось 4: ${fonts.join(', ')}`)

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
  // Адрес страницы от корня сайта — для подсветки в меню (entry-server.tsx).
  const dir = relative(dist, dirname(file)).split('\\').join('/')
  const body = render({ root, path: dir ? `/${dir}/` : '/', sro, service, page: pageKind, article })
  if (article !== undefined) articlesSeen.add(article)
  if (!/<h1[\s>]/.test(body)) throw new Error(`${name}: в собранной странице нет <h1>`)

  const viewport = html.match(/<meta name="viewport"[^>]*>/)
  if (!viewport) throw new Error(`${name}: нет <meta name="viewport">`)
  // Путь до assets — тот же, что у стилей страницы (глубина у страниц разная).
  const css = html.match(/<link rel="stylesheet" crossorigin href="([^"]*?)assets\//)
  if (!css) throw new Error(`${name}: не нашёл ссылку на стили`)
  const preloads = fonts
    .map((font) => `<link rel="preload" href="${css[1]}assets/${font}" as="font" type="font/woff2" crossorigin>`)
    .join('')
  html = html.replace(viewport[0], `${viewport[0]}\n    ${HEAD}\n    ${preloads}`)
  html = html.replace(whole, `<div id="root"${attrs}>${body}</div>`)
  if (html.split('</body>').length !== 2) throw new Error(`${name}: ожидался один </body>`)
  html = html.replace('</body>', `  ${TAIL}\n  </body>`)
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
