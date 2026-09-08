import { defineConfig } from 'astro/config'
import sitemap from '@astrojs/sitemap'
import { execFileSync } from 'node:child_process'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

// Куда собираем сайт.
//
// Боевой режим (свой домен):   SITE_URL=https://ваш-домен.ru  BASE_PATH=/
// Превью на GitHub Pages:      SITE_URL=https://<логин>.github.io  BASE_PATH=/<репозиторий>/norma/  NOINDEX=1
//
// NOINDEX=1 закрывает сборку от поисковиков (мета-тег robots и robots.txt) —
// черновик с превью-ссылкой не должен попасть в выдачу. Боевая сборка на своём
// домене делается без NOINDEX.
const SITE_URL = process.env.SITE_URL || 'https://example.ru'
const BASE_PATH = process.env.BASE_PATH || '/'

// ── Даты изменения для карты сайта ────────────────────────────────────────
//
// lastmod — единственное поле карты сайта, которое поисковики действительно
// читают, и единственное, которое они перестают читать навсегда, если поймают
// на неправде. Поэтому здесь два правила.
//
// Первое: у статьи дата берётся из её собственного поля updated — той самой,
// что стоит на странице под штампом «Сверено». Карта сайта и страница обязаны
// говорить одно и то же.
//
// Второе: у остальных страниц дата берётся из истории git — когда файл
// страницы правился в последний раз. Если истории нет (сборка из архива
// или мелкая копия репозитория), даты не будет вовсе. Это осознанный отказ:
// поставить сюда время сборки — значит на каждой публикации сообщать роботу,
// что изменились все двадцать страниц разом. За такое lastmod и перестают
// учитывать.
const gitDate = (() => {
  try {
    const shallow = execFileSync('git', ['rev-parse', '--is-shallow-repository'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
    if (shallow !== 'false') return () => undefined
  } catch {
    return () => undefined
  }
  return (file) => {
    try {
      const out = execFileSync('git', ['log', '-1', '--format=%cI', '--', file], {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      }).trim()
      return out || undefined
    } catch {
      return undefined
    }
  }
})()

// Даты статей — из заголовков markdown. Читаем сами, а не через коллекцию:
// конфиг выполняется до того, как Astro поднимет содержимое.
const articleDates = (() => {
  const map = new Map()
  const dir = 'src/content/articles'
  if (!existsSync(dir)) return map
  for (const name of readdirSync(dir)) {
    if (!name.endsWith('.md')) continue
    const head = readFileSync(join(dir, name), 'utf8').split('\n---')[0]
    const pick = (key) => head.match(new RegExp(`^${key}:\\s*([0-9]{4}-[0-9]{2}-[0-9]{2})`, 'm'))?.[1]
    const date = pick('updated') ?? pick('published')
    if (date) map.set(name.replace(/\.md$/, ''), new Date(`${date}T00:00:00Z`).toISOString())
  }
  return map
})()

// Адрес страницы → файл, из которого она собрана.
const sourceOf = (path) => {
  const clean = path.replace(/^\/|\/$/g, '')
  const candidates = clean
    ? [`src/pages/${clean}.astro`, `src/pages/${clean}/index.astro`]
    : ['src/pages/index.astro']
  return candidates.find(existsSync)
}

const lastmodFor = (path) => {
  const article = path.match(/^\/baza-znaniy\/([^/]+)\/$/)
  if (article) return articleDates.get(article[1])
  const src = sourceOf(path)
  return src ? gitDate(src) : undefined
}

// Приоритет и частота обновления.
//
// Google эти два поля игнорирует и говорит об этом прямо, Яндекс принимает
// как подсказку. Держим их не ради веса страницы, а ради очерёдности обхода:
// робот с ограниченным лимитом должен сначала взять главную и услуги,
// а не политику обработки данных.
const RULES = [
  [/^\/$/, 1.0, 'weekly'],
  [/^\/uslugi\/([^/]+\/)?$/, 0.9, 'monthly'],
  [/^\/(stoimost|dokumenty|komu-nuzhna-sro|proverit-sro|kontakty)\/$/, 0.8, 'monthly'],
  [/^\/baza-znaniy\/$/, 0.7, 'weekly'],
  [/^\/baza-znaniy\/[^/]+\/$/, 0.6, 'monthly'],
  [/^\/politika\/$/, 0.2, 'yearly'],
]

export default defineConfig({
  site: SITE_URL,
  base: BASE_PATH,
  trailingSlash: 'always',
  // Политика обработки данных индексируется наравне с остальными страницами:
  // поисковики считают её признаком добросовестного сайта.
  integrations: [
    sitemap({
      serialize(item) {
        const path = new URL(item.url).pathname.replace(BASE_PATH.replace(/\/$/, ''), '') || '/'
        const rule = RULES.find(([re]) => re.test(path))
        if (rule) {
          item.priority = rule[1]
          item.changefreq = rule[2]
        }
        const lastmod = lastmodFor(path)
        if (lastmod) item.lastmod = lastmod
        return item
      },
    }),
  ],
  build: {
    format: 'directory',
    inlineStylesheets: 'auto',
  },
})
