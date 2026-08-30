// Проверка собранного сайта перед публикацией.
//
// Ловит три вещи, которые ломают сайт незаметно:
//  1. внутренние ссылки в никуда (опечатка в адресе — страница 404);
//  2. заглушки href="#" — кнопка, которая никуда не ведёт;
//  3. проблемы SEO: нет title/description, нет H1 или их несколько,
//     одинаковые title и description на разных страницах;
//  4. слипшиеся слова: Astro съедает перенос строки перед <b>, <a> и <strong>,
//     и в тексте появляется «конкретной СРО.Мои услуги». Лечится {' '}
//     в конце предыдущей строки.
//
// Запуск: node scripts/check-links.mjs [папка_сборки]

import { readdir, readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

const DIST = resolve(process.argv[2] || 'dist')

async function htmlFiles(dir) {
  const out = []
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) out.push(...(await htmlFiles(full)))
    else if (entry.name.endsWith('.html')) out.push(full)
  }
  return out
}

const problems = []
const warnings = []
const titles = new Map()
const descriptions = new Map()

const files = await htmlFiles(DIST)

for (const file of files) {
  const html = await readFile(file, 'utf8')
  const pageUrl = '/' + relative(DIST, file).replace(/index\.html$/, '').replace(/\\/g, '/')

  // Слипшиеся слова на стыке с выделением. Пустой <i></i> — это кружок
  // в плашке городов, там пробел не нужен, поэтому он исключён.
  const text = html.replace(/<(script|style)\b[\s\S]*?<\/\1>/g, '')
  for (const m of text.matchAll(/[\wА-Яа-яЁё.,;:!?»)]<(?:b|strong|em|a|code)\b[^>]*>[^<]{0,30}/g)) {
    problems.push(`${pageUrl}: пропал пробел → ${m[0].slice(0, 45)}`)
  }
  for (const m of text.matchAll(/<\/(?:b|strong|em|a|code)>[\wА-Яа-яЁё]/g)) {
    problems.push(`${pageUrl}: пропал пробел после выделения → ${m[0]}`)
  }

  // ── SEO ──
  const title = html.match(/<title>([\s\S]*?)<\/title>/)?.[1]?.trim()
  const desc = html.match(/<meta name="description" content="([^"]*)"/)?.[1]?.trim()
  const h1 = [...html.matchAll(/<h1[\s>]/g)].length

  if (!title) problems.push(`${pageUrl}: нет <title>`)
  else if (titles.has(title)) problems.push(`${pageUrl}: title дублирует ${titles.get(title)}`)
  else titles.set(title, pageUrl)

  if (!desc) problems.push(`${pageUrl}: нет meta description`)
  else if (descriptions.has(desc)) problems.push(`${pageUrl}: description дублирует ${descriptions.get(desc)}`)
  else descriptions.set(desc, pageUrl)

  if (h1 === 0) problems.push(`${pageUrl}: нет <h1>`)
  if (h1 > 1) problems.push(`${pageUrl}: ${h1} заголовков <h1>, должен быть один`)

  if (title && title.length > 70) warnings.push(`${pageUrl}: title длиннее 70 знаков (${title.length})`)
  if (desc && desc.length > 200) warnings.push(`${pageUrl}: description длиннее 200 знаков (${desc.length})`)

  // ── Ссылки ──
  for (const m of html.matchAll(/href="([^"]+)"/g)) {
    const raw = m[1]

    if (raw === '#') {
      problems.push(`${pageUrl}: заглушка href="#" — кнопка никуда не ведёт`)
      continue
    }
    if (/^(https?:|mailto:|tel:|data:)/.test(raw) || raw.startsWith('#')) continue

    const [pathPart] = raw.split('#')
    if (!pathPart) continue

    // Абсолютные внутренние адреса проверяем по файлам сборки.
    const target = pathPart.startsWith('/')
      ? join(DIST, pathPart)
      : resolve(file, '..', pathPart)

    const candidates = [target, join(target, 'index.html'), `${target}.html`]
    if (!candidates.some((c) => existsSync(c))) {
      problems.push(`${pageUrl}: битая ссылка → ${raw}`)
    }
  }
}

console.log(`Проверено страниц: ${files.length}`)

if (warnings.length) {
  console.log(`\nПредупреждения (${warnings.length}):`)
  warnings.forEach((w) => console.log('  ! ' + w))
}

if (problems.length) {
  console.log(`\nОШИБКИ (${problems.length}):`)
  problems.forEach((p) => console.log('  ✗ ' + p))
  process.exit(1)
}

console.log('\n✓ Битых ссылок и заглушек нет, мета-теги уникальны, слова не слиплись.')
