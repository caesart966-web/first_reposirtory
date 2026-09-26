// Сборка сайта для боевого хостинга и архив, готовый к заливке.
//
// Запуск:  npm run release -- norma-sro.ru
//
// Зачем отдельный скрипт, а не «соберите с нужными переменными». Боевая
// сборка отличается от превью пятью значениями, и забыть любое из них можно
// молча — сайт соберётся и будет выглядеть рабочим:
//
//   • не задан SITE_URL          → в карте сайта и микроразметке example.ru;
//   • остался BASE_PATH          → все ссылки ведут в /first_reposirtory/norma/;
//   • остался PUBLIC_NOINDEX     → robots.txt запрещает индексацию, и сайта
//                                  в поиске не будет вообще, а узнаете
//                                  об этом через месяц;
//   • не задан PUBLIC_LEAD_ENDPOINT → форма не отправляет заявки, а честно
//                                  показывает телефон: выглядит как задумано,
//                                  но заявки с сайта не приходят;
//   • не заполнен submit.php     → письма уходят от example.ru и попадают
//                                  в спам, либо не уходят вовсе.
//
// Поэтому скрипт задаёт всё сам из одного значения — домена, — а потом
// ПРОВЕРЯЕТ собранное на следы превью. Проверка важнее сборки: она ловит
// ровно тот класс ошибок, который иначе замечают постфактум.
//
// Исходники при этом не трогаются: submit.php с доменом правится уже
// в dist. В репозитории домена нет, и это нарочно — иначе при смене домена
// он остался бы в двух местах.

import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '..')
const dist = join(root, 'dist')

const red = (s) => `\x1b[31m${s}\x1b[0m`
const green = (s) => `\x1b[32m${s}\x1b[0m`
const dim = (s) => `\x1b[2m${s}\x1b[0m`
const bold = (s) => `\x1b[1m${s}\x1b[0m`

let problems = 0
const fail = (m) => { console.log(`  ${red('✗')} ${m}`); problems++ }
const ok = (m) => console.log(`  ${green('✓')} ${m}`)

// ── Домен ─────────────────────────────────────────────────────────────────
//
// Принимаем только голое имя: без протокола, без слеша, без www. Всё это
// потом склеивается в адреса, и лишний слеш даёт https://домен.ru//stoimost/.
const raw = process.argv[2]
if (!raw) {
  console.log(`
${bold('Сборка сайта для боевого хостинга.')}

  npm run release -- ваш-домен.ru

  npm run release -- ваш-домен.ru  ящик@ваш-домен.ru

Домен пишется без https:// и без www — например ${bold('norma-sro.ru')}.
Вторым аргументом — ящик, от которого уходят письма с заявками. Если его
не указать, берётся ${bold('zayavka@ваш-домен.ru')}; ящик должен быть заведён
на хостинге, иначе письма уйдут в спам.
`)
  process.exit(1)
}

const domain = raw.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/+$/, '')
if (!/^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(domain)) {
  console.log(red(`Не похоже на домен: «${raw}». Нужно голое имя вида norma-sro.ru.`))
  process.exit(1)
}
if (domain.startsWith('www.')) {
  console.log(red('Домен пишется без www: сайт сам перенаправляет www на основной адрес.'))
  process.exit(1)
}

const siteUrl = `https://${domain}`

// ── Ящик, от которого уходят письма с заявками ────────────────────────────
//
// Он ОБЯЗАН существовать на хостинге. Адрес на чужом домене или ящик,
// которого нет, — и письмо не пройдёт проверку подлинности отправителя:
// почта получателя сочтёт его подделкой и положит в спам. Молча, без
// единой ошибки на сайте: форма скажет «заявка отправлена», а заявки
// вы не увидите.
//
// Поэтому адрес задаётся явно, а не угадывается. По умолчанию zayavka@,
// но если ящик называется иначе — передайте его вторым аргументом:
//   npm run release -- norma-sro.ru info@norma-sro.ru
const fromArg = process.argv[3]
if (fromArg && !/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(fromArg)) {
  console.log(red(`«${fromArg}» не похоже на адрес почты.`))
  process.exit(1)
}
if (fromArg && !fromArg.toLowerCase().endsWith(`@${domain}`)) {
  console.log(red(`Ящик ${fromArg} не на домене ${domain}.`))
  console.log('С чужого домена письма не пройдут проверку подлинности и уйдут в спам.\n')
  process.exit(1)
}
const mailFrom = fromArg ? fromArg.toLowerCase() : `zayavka@${domain}`

// ── Токен формы ───────────────────────────────────────────────────────────
//
// Он должен совпадать в двух местах: в submit.php на хостинге и в разметке
// страницы. Поэтому берём его ИЗ submit.php, а не задаём здесь: так у него
// одна точка правды, и рассогласоваться нечему.
const phpSrcPath = join(root, 'public/api/submit.php')
const phpSrc = readFileSync(phpSrcPath, 'utf8')
const tokenMatch = phpSrc.match(/const FORM_TOKEN = '([^']+)'/)
if (!tokenMatch) {
  console.log(red('В public/api/submit.php не нашёлся FORM_TOKEN — проверьте файл.'))
  process.exit(1)
}
const token = tokenMatch[1]
const mailTo = (phpSrc.match(/const MAIL_TO = '([^']+)'/) || [])[1] || '(не задан)'

console.log(`
${bold('Боевая сборка')}
  домен            ${bold(domain)}
  адрес сайта      ${siteUrl}
  заявки приходят  ${mailTo}
  письма уходят от ${bold(mailFrom)}  ← этот ящик должен существовать на хостинге
  токен формы      ${token}
`)

// ── 1. Сборка ─────────────────────────────────────────────────────────────
console.log(bold('1. Сборка'))
const env = {
  ...process.env,
  SITE_URL: siteUrl,
  BASE_PATH: '/',
  PUBLIC_LEAD_ENDPOINT: '/api/submit.php',
  PUBLIC_LEAD_TOKEN: token,
}
// Превью-переменные вычищаем явно: если они остались в окружении от прошлой
// команды, сборка молча получится превью-сборкой с боевым адресом.
delete env.PUBLIC_NOINDEX
delete env.NOINDEX

try {
  execFileSync('npm', ['run', 'build'], { cwd: root, env, stdio: ['ignore', 'pipe', 'inherit'] })
  ok('сайт собран')
} catch {
  console.log(red('\nСборка не прошла. Выше написано почему.'))
  process.exit(1)
}

// ── 2. Обработчик заявок ──────────────────────────────────────────────────
console.log(`\n${bold('2. Приём заявок')}`)
const phpDistPath = join(dist, 'api/submit.php')
let php = readFileSync(phpDistPath, 'utf8')
php = php.replace(/const MAIL_FROM = '[^']*';/, `const MAIL_FROM = '${mailFrom}';`)
php = php.replace(/const ALLOWED_HOST = '[^']*';/, `const ALLOWED_HOST = '${domain}';`)
writeFileSync(phpDistPath, php)

if (!php.includes(`const MAIL_FROM = '${mailFrom}';`)) fail('MAIL_FROM не подставился')
else ok(`MAIL_FROM = ${mailFrom}`)
if (!php.includes(`const ALLOWED_HOST = '${domain}';`)) fail('ALLOWED_HOST не подставился')
else ok(`ALLOWED_HOST = ${domain}`)

// Синтаксис PHP проверяем настоящим PHP, если он есть в системе. Опечатка
// в этом файле даёт не «форма не работает», а белый экран на весь обработчик.
try {
  execFileSync('php', ['-l', phpDistPath], { stdio: 'pipe' })
  ok('синтаксис submit.php в порядке')
} catch (e) {
  const out = String(e.stdout || e.stderr || e.message)
  if (/not found|ENOENT/i.test(out)) console.log(`  ${dim('· php в системе нет, синтаксис не проверен')}`)
  else fail(`submit.php не разбирается: ${out.split('\n')[0]}`)
}

// ── 3. Следы превью ───────────────────────────────────────────────────────
//
// Самая дорогая ошибка запуска: сайт выглядит рабочим, а в разметке остался
// адрес черновика. Ищем по всем текстовым файлам сборки.
console.log(`\n${bold('3. Следы превью в сборке')}`)

const textFiles = []
const walk = (d) => {
  for (const name of readdirSync(d)) {
    const p = join(d, name)
    if (statSync(p).isDirectory()) walk(p)
    else if (/\.(html|xml|txt|json|webmanifest|php|css|js)$/.test(name)) textFiles.push(p)
  }
}
walk(dist)

const TRACES = [
  { what: 'example.ru', why: 'адрес-заглушка из astro.config.mjs' },
  { what: 'github.io', why: 'адрес превью' },
  { what: '/first_reposirtory/', why: 'подпапка превью' },
  // submit.php исключён нарочно: «ваш-домен.ru» стоит там в пояснении
  // к константе, а сами константы проверены шагом выше по значению.
  // Выкинуть пояснение было бы хуже: его читает тот, кто правит файл руками.
  { what: 'ваш-домен.ru', why: 'placeholder из инструкции', skip: ['api/submit.php'] },
]
for (const t of TRACES) {
  const hits = textFiles
    .filter((p) => !(t.skip || []).includes(relative(dist, p)))
    .filter((p) => readFileSync(p, 'utf8').includes(t.what))
  if (hits.length) {
    fail(`«${t.what}» (${t.why}) встречается в ${hits.length} файлах, например ${relative(dist, hits[0])}`)
  } else ok(`«${t.what}» не встречается`)
}

// ── 4. Сайт открыт поисковикам ────────────────────────────────────────────
console.log(`\n${bold('4. Открыт ли сайт поисковикам')}`)
const robots = readFileSync(join(dist, 'robots.txt'), 'utf8')
if (/Disallow:\s*\/\s*$/m.test(robots)) fail('robots.txt запрещает индексацию — осталась переменная PUBLIC_NOINDEX')
else ok('robots.txt разрешает обход')
if (!robots.includes(`${siteUrl}/sitemap-index.xml`)) fail('в robots.txt не тот адрес карты сайта')
else ok('карта сайта указана с боевым адресом')

// Две страницы закрыты от индексации намеренно и пропом noindex, а не
// переменной: страница результатов поиска (одна такая в выдаче ничего
// не даёт, а тысяча размывает сайт) и страница 404.
//
// Список написан руками, и это осознанно: смысл проверки — поймать
// PUBLIC_NOINDEX, протёкший в боевую сборку, а он закрывает ВСЕ страницы
// разом. Список, собранный из исходников, такую беду пропустил бы, потому
// что «ожидаемым» стало бы ровно то, что собралось. Появится третья
// закрытая страница — проверка упадёт, и это правильный повод убедиться,
// что её закрыли нарочно.
const NOINDEX_OK = ['404.html', 'poisk/index.html']
const noindexed = textFiles
  .filter((p) => p.endsWith('.html') && /<meta[^>]+name="robots"[^>]+noindex/i.test(readFileSync(p, 'utf8')))
  .map((p) => relative(dist, p))
const unexpected = noindexed.filter((p) => !NOINDEX_OK.includes(p))
const missing = NOINDEX_OK.filter((p) => !noindexed.includes(p))
if (unexpected.length) fail(`закрыты от индексации сверх задуманного: ${unexpected.join(', ')}`)
else if (missing.length) fail(`перестали быть закрытыми: ${missing.join(', ')}`)
else ok(`мета-тег noindex только на ${NOINDEX_OK.join(' и ')}`)

// ── 5. Форма отправляет заявки ────────────────────────────────────────────
console.log(`\n${bold('5. Форма заявки')}`)
const contacts = readFileSync(join(dist, 'kontakty/index.html'), 'utf8')
if (!contacts.includes('/api/submit.php')) fail('в форме не прописан адрес обработчика — заявки уходить не будут')
else ok('форма отправляет на /api/submit.php')
if (!contacts.includes(token)) fail('в форме нет токена — обработчик отклонит заявку')
else ok('токен формы на месте')

// ── 6. Файлы для сервера ──────────────────────────────────────────────────
console.log(`\n${bold('6. Файлы для сервера')}`)
for (const f of ['.htaccess', 'api/.htaccess', 'api/submit.php', '404.html', 'sitemap-index.xml', 'search-index.json']) {
  if (existsSync(join(dist, f))) ok(f)
  else fail(`${f} не попал в сборку`)
}

// ── 7. Архив ──────────────────────────────────────────────────────────────
if (problems) {
  console.log(`\n${red(`Архив не собран: ${problems} проблем${problems === 1 ? 'а' : ''}. Сначала их.`)}\n`)
  process.exit(1)
}

console.log(`\n${bold('7. Архив')}`)
const releases = join(root, 'release')
mkdirSync(releases, { recursive: true })
const stamp = new Date().toISOString().slice(0, 10)
const zipName = `${domain}-${stamp}.zip`
const zipPath = join(releases, zipName)
// -r по точке забирает и скрытые файлы, а .htaccess здесь два и оба нужны.
execFileSync('zip', ['-r', '-q', '-X', zipPath, '.'], { cwd: dist })
const mb = (statSync(zipPath).size / 1024 / 1024).toFixed(1)
ok(`${relative(root, zipPath)} — ${mb} МБ`)

console.log(`
${green(bold('Готово.'))} Что дальше, по шагам:

  1. В панели Timeweb: ${bold('Сайты → Добавить сайт')}, домен ${bold(domain)},
     корневая папка ${bold('public_html')}, версия PHP ${bold('8.0 или новее')}.
  2. Почта → создать ящик ${bold(mailFrom)} (письма заявок уходят от него;
     с чужого домена они попадут в спам).
  3. ${bold('СНАЧАЛА СЕРТИФИКАТ, ПОТОМ ФАЙЛЫ.')} В панели выпустить бесплатный
     ${bold('SSL (Let\'s Encrypt)')} и дождаться, пока он выпустится.
     В архиве лежит .htaccess, который отправляет всех на https: залитый
     до сертификата, он сделает сайт недоступным совсем — файлы будут
     на месте, а браузер покажет ошибку сертификата.
  4. Файловый менеджер → зайти в public_html, ${bold('удалить')} то, что там
     положил хостинг (index.html-заглушку), загрузить ${bold(zipName)}
     и распаковать прямо там.
  5. В панели включить ${bold('перенаправление на HTTPS')} и основное
     зеркало ${bold('без www')}.
  6. Проверить своими глазами:
       ${siteUrl}/                      — открывается
       ${siteUrl}/stoimost/             — открывается
       ${siteUrl}/несуществующая/       — ваша страница 404, не заглушка хостинга
       ${siteUrl}/robots.txt            — Allow, а не Disallow
       ${siteUrl}/api/leads.log.php     — ПУСТАЯ страница (там перс. данные)
  7. Отправить себе тестовую заявку через форму на /kontakty/ и ${bold('проверить папку «Спам»')}.
  8. ${bold('Уведомление в Роскомнадзор — до первой настоящей заявки')}, не после.
     Раздел 21 инструкции.
  9. Добавить сайт в Яндекс.Вебмастер и Google Search Console,
     указать карту сайта ${siteUrl}/sitemap-index.xml
`)
