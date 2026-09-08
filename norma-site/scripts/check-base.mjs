// Проверяет, что сайт не ломается в подпапке.
//
// Зачем. Сайт живёт по адресу вида /репозиторий/norma/, и все внутренние
// ссылки должны начинаться с этой подпапки. Ссылки, поставленные
// компонентами, проходят через href() и получают её. Ссылки, написанные
// в markdown-статьях, — нет: «/proverit-sro/» так и уходит в разметку
// и на боевом адресе ведёт в корень домена, где ничего нет.
//
// Так и случилось: двадцать девять ссылок внутри статей вели на страницу
// «Site not found» от GitHub. Обычная проверка ссылок этого не видела,
// потому что гоняется на локальном превью, где подпапки нет вовсе,
// и там эти ссылки работают.
//
// Поэтому проверка отдельная и работает не с сервером, а с готовой
// сборкой: собирать нужно с той же подпапкой, что и на боевом адресе.
//
// Запуск: npm run check:base   (соберёт с тестовой подпапкой и проверит)
import { readdirSync, readFileSync } from 'fs'
import { join } from 'path'

const DIST = 'dist'
const BASE = process.env.BASE_PATH || '/'
const base = BASE.replace(/\/$/, '')

if (!base) {
  console.log('· Сборка сделана без подпапки (BASE_PATH=/) — проверять нечего.')
  console.log('  Запускайте через npm run check:base, он подставит подпапку сам.')
  process.exit(0)
}

const files = []
const walk = (dir) => {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) walk(p)
    else if (e.name.endsWith('.html')) files.push(p)
  }
}
walk(DIST)

let bad = 0
let checked = 0
for (const f of files) {
  const html = readFileSync(f, 'utf8')
  const url = '/' + f.slice(DIST.length + 1).replace(/index\.html$/, '')
  for (const m of html.matchAll(/(href|src)="(\/[^"]*)"/g)) {
    const val = m[2]
    checked++
    // Двойной слэш — это внешний адрес вида //example.com
    if (val.startsWith('//')) continue
    if (val.startsWith(base + '/') || val === base) continue
    bad++
    console.log(`  ✗ ${url}\n      ${m[1]}="${val}" — без подпапки ${base}`)
  }
}

console.log()
if (bad) {
  console.log(`ССЫЛОК БЕЗ ПОДПАПКИ: ${bad} из ${checked}`)
  console.log('На боевом адресе они ведут в корень домена, где ничего нет.')
  console.log('Ссылки в компонентах оборачивайте в href(), ссылки в статьях')
  console.log('чинятся сами — см. withBase в src/pages/baza-znaniy/[...slug].astro.')
  process.exit(1)
}
console.log(`✓ Все ${checked} внутренних ссылок работают в подпапке ${base}`)
