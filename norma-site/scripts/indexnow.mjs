// Отправляет адреса сайта в IndexNow — протокол мгновенной переиндексации.
//
// Запуск:  npm run indexnow           — все адреса из карты сайта
//          npm run indexnow -- /stoimost/ /uslugi/nrs/   — только эти
//
// Кто слушает: Яндекс, Bing, Naver, Seznam. Google в IndexNow не участвует
// и говорит об этом прямо — у него для этого Search Console и обход по карте
// сайта. То есть команда ускоряет Яндекс, а Яндекс для этого сайта — главный.
//
// Обычный порядок: поменяли цену или статью → опубликовали → запустили
// команду. Робот приходит в тот же день, а не через неделю.
//
// Ключ и файл-подтверждение. Поисковик обязан убедиться, что адреса шлёт
// владелец сайта, и проверяет это единственным способом: ключ из запроса
// должен лежать на самом сайте файлом <ключ>.txt. Файл уже создан в public/.
// Меняете ключ в src/config/seo.ts — переименуйте и файл.

import { readFile, readdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const dist = resolve(here, '../dist')

// Ключ читаем разбором строки, а не импортом: seo.ts — файл TypeScript,
// и обычный node его не выполнит.
const seo = await readFile(resolve(here, '../src/config/seo.ts'), 'utf8')
const key = seo.match(/indexNowKey:\s*'([^']*)'/)?.[1] ?? ''

if (!/^[0-9a-zA-Z-]{8,128}$/.test(key)) {
  console.error('✗ В src/config/seo.ts нет ключа IndexNow (нужно 8–128 знаков).')
  process.exit(1)
}

// Адреса берём из карты сайта — той самой, что уходит поисковикам.
// Второй список адресов рядом с первым обязательно разойдётся с ним.
const files = (await readdir(dist)).filter((f) => /^sitemap-\d+\.xml$/.test(f))
if (files.length === 0) {
  console.error('✗ Не найдена карта сайта в dist/. Сначала: npm run build')
  process.exit(1)
}

let urls = []
for (const f of files) {
  const xml = await readFile(join(dist, f), 'utf8')
  urls.push(...[...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]))
}

const host = new URL(urls[0]).host

// Черновик отправлять нельзя. Превью на GitHub Pages закрыто от индексации
// мета-тегом и robots.txt, и просить робота его обойти — значит просить
// проиндексировать то, что сами же и закрыли.
if (/example\.(ru|com)$/.test(host) || host.endsWith('github.io')) {
  console.error(`✗ Адрес сайта — ${host}. Это черновик, а не боевой домен.`)
  console.error('  Соберите сайт с SITE_URL=https://ваш-домен.ru и без PUBLIC_NOINDEX.')
  process.exit(1)
}

// Ключ-файл обязан лежать на сайте: без него поисковик отвергнет отправку.
const keyFileNames = (await readdir(resolve(here, '../public'))).filter((f) => f === `${key}.txt`)
if (keyFileNames.length === 0) {
  console.error(`✗ В public/ нет файла ${key}.txt — поисковик не сможет проверить владение сайтом.`)
  process.exit(1)
}

// Можно отправить только часть адресов: аргументами командной строки.
const only = process.argv.slice(2).filter((a) => a.startsWith('/'))
if (only.length > 0) {
  const wanted = new Set(only.map((p) => new URL(p, `https://${host}`).pathname))
  urls = urls.filter((u) => wanted.has(new URL(u).pathname))
  if (urls.length === 0) {
    console.error('✗ Ни один из указанных адресов не найден в карте сайта.')
    process.exit(1)
  }
}

const payload = {
  host,
  key,
  keyLocation: `https://${host}/${key}.txt`,
  urlList: urls,
}

console.log(`Отправляю ${urls.length} адрес(ов) сайта ${host} в IndexNow…`)

const res = await fetch('https://api.indexnow.org/indexnow', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json; charset=utf-8' },
  body: JSON.stringify(payload),
})

// Ответы протокола: 200 и 202 — принято; 403 — ключ не подтверждён
// (нет файла на сайте или он с другим содержимым); 422 — адреса
// не с этого домена; 429 — слишком часто.
const hints = {
  403: 'ключ не подтверждён: проверьте, что https://' + host + '/' + key + '.txt открывается и содержит сам ключ',
  422: 'адреса не совпадают с доменом, с которого отправлены',
  429: 'слишком частая отправка — попробуйте позже',
}

if (res.ok || res.status === 202) {
  console.log(`✓ Принято (${res.status}). Робот придёт в ближайшие часы.`)
} else {
  console.error(`✗ Отказ ${res.status}${hints[res.status] ? ': ' + hints[res.status] : ''}`)
  process.exit(1)
}
