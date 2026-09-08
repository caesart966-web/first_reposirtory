// Карта сайта: список всех адресов для Яндекса и Google.
//
// Поисковик находит главную, но не обязан догадаться, что есть ещё три
// страницы видов СРО и семь страниц услуг: ссылки на них лежат в выпадающем
// меню, которое собирается скриптом. Карта сайта называет все адреса прямо.
//
// Список страниц не пишется руками, а собирается из самих файлов: каждая
// страница сайта — это отдельный index.html со своей точкой входа (см.
// vite.config.ts). Появится новая — попадёт в карту сама.
//
// lastmod намеренно нет: неверная дата хуже отсутствующей, а честную взять
// неоткуда — файл собирается не в момент правки страницы.
//
// Запуск: node scripts/build-sitemap.mjs
import { readdirSync, statSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
// Тот же плейсхолдер, что в canonical и og:url: домен подставляется одной
// командой после покупки — scripts/set-domain.mjs.
const ORIGIN = 'https://example.com'
const SKIP = new Set(['node_modules', 'dist', 'public', 'src', 'scripts', 'assets-src', '.git'])

/** Все index.html проекта, кроме служебных каталогов. */
function pages(dir = root, prefix = '') {
  const out = []
  for (const entry of readdirSync(dir)) {
    if (SKIP.has(entry) || entry.startsWith('.')) continue
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) out.push(...pages(full, `${prefix}${entry}/`))
    else if (entry === 'index.html') out.push(prefix)
  }
  return out
}

// Главная первой, дальше по алфавиту — так карту проще читать глазами.
const urls = pages().sort((a, b) => (a === '' ? -1 : b === '' ? 1 : a.localeCompare(b)))
const xml = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ...urls.map((u) => `  <url><loc>${ORIGIN}/${u}</loc></url>`),
  '</urlset>',
  '',
].join('\n')

writeFileSync(resolve(root, 'public/sitemap.xml'), xml)
console.log(`sitemap.xml готов: ${urls.length} адресов`)
for (const u of urls) console.log('  /' + u)
