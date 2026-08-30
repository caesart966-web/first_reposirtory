// Проверяет, что приложение «Заказы» не перехватывает соседние сайты.
//
// Зачем. На GitHub Pages по одному адресу лежит несколько проектов:
// приложение в корне /first_reposirtory/, а рядом в подпапках сайты
// /norma/, /sro/, /pto/, /stroigeroi/. Приложение — PWA: у него есть
// служебный скрипт (service worker), который работает на весь адрес
// целиком и умеет отвечать из кэша, когда интернета нет.
//
// В этом и была ловушка. Скрипту сказано: «на любой неизвестный адрес
// отдавай главную страницу приложения» — это нужно, чтобы приложение
// открывалось офлайн с любой внутренней ссылки. Но «любой адрес» включал
// и соседние сайты: посетитель открывал ссылку на сайт СРО и попадал
// в «Заказы». Лечится списком исключений navigateFallbackDenylist
// в vite.config.ts.
//
// Здесь мы сверяем два списка: какие сайты реально лежат рядом в сборке
// и какие из них перечислены в исключениях. Если появится новый сайт,
// а исключение под него забудут, сборка упадёт здесь, а не у посетителя.
//
// Запуск: node scripts/check-neighbours.mjs [папка_сборки]
// В сборке этот скрипт вызывается после того, как все сайты разложены.

import { readdir, readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, resolve } from 'node:path'

const DIST = resolve(process.argv[2] || 'dist')
const SW = join(DIST, 'sw.js')

if (!existsSync(SW)) {
  console.error(`✗ Не найден служебный скрипт ${SW}. Сначала соберите приложение: npm run build`)
  process.exit(1)
}

// Соседний сайт — это папка со своей index.html. У папок assets и icons
// её нет, поэтому они сюда не попадают.
const neighbours = []
for (const entry of await readdir(DIST, { withFileTypes: true })) {
  if (entry.isDirectory() && existsSync(join(DIST, entry.name, 'index.html'))) {
    neighbours.push(entry.name)
  }
}

const sw = await readFile(SW, 'utf8')

// Достаём список исключений из собранного скрипта.
const found = sw.match(/denylist:\s*\[([^\]]*)\]/)
const patterns = []
if (found) {
  for (const m of found[1].matchAll(/\/((?:\\.|[^/\\])*)\//g)) {
    try {
      patterns.push(new RegExp(m[1]))
    } catch {
      console.error(`✗ Не удалось разобрать исключение: ${m[0]}`)
      process.exit(1)
    }
  }
}

const uncovered = neighbours.filter((n) => !patterns.some((re) => re.test(`/first_reposirtory/${n}/`)))

console.log(`Сайтов рядом с приложением: ${neighbours.length ? neighbours.join(', ') : 'нет'}`)
console.log(`Исключений в служебном скрипте: ${patterns.length}`)

if (uncovered.length) {
  console.error(
    `\n✗ Приложение перехватит эти сайты: ${uncovered.join(', ')}\n` +
      `  Добавьте их в navigateFallbackDenylist в orders-app/vite.config.ts,\n` +
      `  иначе по ссылке на сайт посетитель увидит «Заказы».`,
  )
  process.exit(1)
}

console.log('\n✓ Соседние сайты открываются сами, приложение их не перехватывает.')
