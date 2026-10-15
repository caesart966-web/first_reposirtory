// Какие страницы изменились между двумя боевыми архивами — для переобхода.
//
// Запуск:  npm run changed -- release/старый.zip release/новый.zip
//
// Сравнивается то, что видит поисковик: заголовок окна, описание, H1 и текст
// <main>. Скрипты, стили и рисунки не в счёт — правка оформления страницу
// для поиска не меняет, и отправлять её на переобход незачем.
//
// Итог — список в консоли и файл indexnow.txt рядом с package.json: по нему
// робот в GitHub Actions («НОРМА: отправить изменённые страницы в IndexNow»)
// отправляет адреса Яндексу после того, как архив залит на хостинг. Список
// пишется из сравнения, а не по памяти: по памяти он однажды уже разошёлся
// с тем, что поменялось на самом деле (README, «После каждой заливки»).

import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { basename, join } from 'node:path'

const [oldZip, newZip] = process.argv.slice(2)
if (!oldZip || !newZip || !existsSync(oldZip) || !existsSync(newZip)) {
  console.error('Запуск: npm run changed -- release/старый.zip release/новый.zip')
  process.exit(1)
}

const unpack = (zip) => {
  const dir = mkdtempSync(join(tmpdir(), 'norma-changed-'))
  execFileSync('unzip', ['-q', zip, '-d', dir])
  return dir
}
const A = unpack(oldZip)
const B = unpack(newZip)

const sitemap = readFileSync(join(B, 'sitemap-0.xml'), 'utf8')
const locs = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1])
const paths = locs.map((u) => new URL(u).pathname)
const host = new URL(locs[0]).host
// Отпечаток карты сайта нового архива. Робот сравнит его с картой на живом
// сайте и откажется отправлять адреса, если архив ещё не залит: позвать
// робота на старую версию страниц — значит потратить переобход впустую.
const sitemapHash = createHash('sha256').update(sitemap).digest('hex')

const text = (s) =>
  (s || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;|&#160;/g, ' ')
    .replace(/&[a-z]+;|&#\d+;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
const view = (html) => {
  const clean = html.replace(/<(script|style|svg)\b[\s\S]*?<\/\1>/g, ' ')
  return {
    title: text(clean.match(/<title>([\s\S]*?)<\/title>/)?.[1]),
    desc: clean.match(/<meta name="description" content="([^"]*)"/)?.[1] || '',
    h1: text(clean.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/)?.[1]),
    main: text(clean.match(/<main\b[^>]*>([\s\S]*?)<\/main>/)?.[1]),
  }
}

const changed = []
for (const p of paths) {
  const fa = join(A, p, 'index.html')
  const fb = join(B, p, 'index.html')
  if (!existsSync(fb)) continue
  if (!existsSync(fa)) {
    changed.push({ p, what: 'новая страница' })
    continue
  }
  const a = view(readFileSync(fa, 'utf8'))
  const b = view(readFileSync(fb, 'utf8'))
  const what = []
  if (a.title !== b.title) what.push('заголовок')
  if (a.desc !== b.desc) what.push('описание')
  if (a.h1 !== b.h1) what.push('H1')
  if (a.main !== b.main) what.push('текст')
  if (what.length) changed.push({ p, what: what.join(', ') })
}

rmSync(A, { recursive: true, force: true })
rmSync(B, { recursive: true, force: true })

for (const c of changed) console.log(`${c.p.padEnd(56)} ${c.what}`)
console.log(`\nИзменилось страниц: ${changed.length} из ${paths.length}.`)

writeFileSync(
  'indexnow.txt',
  [
    `# Изменённые страницы: ${basename(oldZip)} → ${basename(newZip)}`,
    '# Собрано командой npm run changed. Отправляет их в IndexNow робот',
    '# «НОРМА: отправить изменённые страницы в IndexNow» (GitHub → Actions).',
    `# archive: ${basename(newZip)}`,
    `# host: ${host}`,
    `# sitemap-sha256: ${sitemapHash}`,
    ...changed.map((c) => c.p),
    '',
  ].join('\n'),
)
console.log('Список записан в indexnow.txt — закоммитьте его вместе с архивом.')
