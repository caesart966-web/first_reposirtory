// Страницы раздела «Статьи» из src/content/articles.ts (15.10.2026).
//
// У каждой страницы сайта свой index.html со своим <title>, описанием
// и адресом (см. vite.config.ts) — поисковик видит их ещё до скрипта.
// Страницы статей пишет этот скрипт, а не человек: заголовок и описание
// живут в одном месте, в articles.ts, и разойтись со страницей не могут.
// Сборка проверяет, что для каждой статьи страница есть (prerender.mjs).
//
// Запуск — `npm run articles`: этот скрипт, затем микроразметка
// (build-jsonld.mjs), карта сайта (build-sitemap.mjs) и домен
// (set-domain.mjs). Папку статьи, которой больше нет в articles.ts,
// скрипт удаляет — только если её страницу писал он сам (метка GENERATED).
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { ogName } from './og-name.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
// Node 22.18+ снимает типы с .ts сам: данные читаются из того же файла,
// что и сайт, без второй копии.
const { ARTICLES, ARTICLES_PATH } = await import(pathToFileURL(resolve(root, 'src/content/articles.ts')).href)

const BRAND = 'ООО «БИЗНЕС-ГРУПП»'
const GENERATED = '<!-- Страница собрана scripts/build-articles.mjs из src/content/articles.ts — правки вносить там. -->'
// Домен — из canonical главной (его вписал set-domain.mjs): одна точка правды.
const origin = readFileSync(resolve(root, 'index.html'), 'utf8').match(/<link rel="canonical" href="(https?:\/\/[^/"]+)\//)?.[1]
if (!origin) throw new Error('Не нашёл canonical главной — откуда взять домен?')

const esc = (text) => text.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')

// Картинка для мессенджеров: своя, если build-og.mjs --pages её уже нарисовал,
// иначе общая og.png. У новой статьи своей картинки ещё нет: она рисуется
// по готовой странице, после сборки (порядок — в build-og.mjs).
const ogImage = (url) =>
  existsSync(resolve(root, 'public/og', ogName(url))) ? `${origin}/og/${ogName(url)}` : `${origin}/og.png`

function html({ url, depth, title, description, type, extraMeta = '', mount }) {
  const up = '../'.repeat(depth)
  return `<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>${esc(title)}</title>
    <meta name="description" content="${esc(description)}" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="${origin}/${url}" />
    <link rel="icon" type="image/svg+xml" href="${up}favicon.svg" />
    <!-- Safari не берёт SVG для ярлыка «на экран Домой»: без PNG
         вместо знака компании там окажется скриншот страницы. -->
    <link rel="apple-touch-icon" href="${up}apple-touch-icon.png" />
    <meta name="theme-color" content="#FBF9F5" />
    <meta property="og:type" content="${type}" />
    <meta property="og:locale" content="ru_RU" />
    <meta property="og:site_name" content="${esc(`${BRAND} · Вступление в СРО`)}" />
    <meta property="og:title" content="${esc(title)}" />
    <meta property="og:description" content="${esc(description)}" />
    <meta property="og:url" content="${origin}/${url}" />
${extraMeta}    <!-- Картинка карточки в мессенджерах и соцсетях — своя у страницы
         (с 22.10.2026): знак, имя компании и заголовок этой страницы,
         без фотографии — карточка показывается размером с ноготь.
         Пересобирается: node scripts/build-og.mjs --pages -->
    <meta property="og:image" content="${ogImage(url)}" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta property="og:image:alt" content="${esc(title)}" />
    <meta name="twitter:card" content="summary_large_image" />
    <!-- Без JS reveal-блоки остались бы прозрачными: страница выглядела бы пустой -->
    <noscript>
      <style>
        .reveal,
        .reveal-words .w > span,
        .reveal-image,
        .reveal-image img {
          opacity: 1 !important;
          transform: none !important;
          clip-path: none !important;
        }
      </style>
    </noscript>
  </head>
  <body>
    ${GENERATED}
    ${mount}
    <script type="module" src="/src/stati.tsx"></script>
  </body>
</html>
`
}

const dir = resolve(root, ARTICLES_PATH)
mkdirSync(dir, { recursive: true })

// Список статей.
writeFileSync(
  join(dir, 'index.html'),
  html({
    url: `${ARTICLES_PATH}/`,
    depth: 1,
    title: `Статьи о вступлении в СРО — ${BRAND}`,
    description:
      'Статьи о вступлении в СРО строителей, проектировщиков и изыскателей со ссылками на Градостроительный кодекс: кому нужно членство, как выбрать и проверить СРО.',
    type: 'website',
    mount: '<div id="root" data-page="stati" data-root="../"></div>',
  }),
)

const slugs = new Set()
for (const article of ARTICLES) {
  if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(article.slug)) throw new Error(`Адрес статьи латиницей через дефис: «${article.slug}»`)
  if (slugs.has(article.slug)) throw new Error(`Две статьи с адресом «${article.slug}»`)
  slugs.add(article.slug)
  const at = join(dir, article.slug)
  mkdirSync(at, { recursive: true })
  writeFileSync(
    join(at, 'index.html'),
    html({
      url: `${ARTICLES_PATH}/${article.slug}/`,
      depth: 2,
      title: `${article.seoTitle ?? article.title} — ${BRAND}`,
      description: article.description,
      type: 'article',
      // Даты для поисковика и для микроразметки (build-jsonld.mjs берёт их
      // отсюда): выход и последняя сверка с законом.
      extraMeta:
        `    <meta property="article:published_time" content="${article.published}" />\n` +
        `    <meta property="article:modified_time" content="${article.checked}" />\n`,
      mount: `<div id="root" data-article="${article.slug}" data-root="../../"></div>`,
    }),
  )
}

// Папки статей, которых больше нет в данных.
for (const entry of readdirSync(dir, { withFileTypes: true })) {
  if (!entry.isDirectory() || slugs.has(entry.name)) continue
  const page = join(dir, entry.name, 'index.html')
  if (existsSync(page) && readFileSync(page, 'utf8').includes(GENERATED)) {
    rmSync(join(dir, entry.name), { recursive: true })
    console.log(`  удалена страница снятой статьи: ${entry.name}`)
  }
}

console.log(`статьи: список и ${ARTICLES.length} страниц в ${ARTICLES_PATH}/`)
