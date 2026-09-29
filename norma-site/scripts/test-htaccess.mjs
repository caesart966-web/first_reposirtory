// Проверяет public/.htaccess на настоящем Apache: переходы, закрытые файлы,
// проверку сертификата и кеш.
//
// Запуск:  npm run build && npm run test:htaccess
// Нужен Apache 2.4 (в Ubuntu: sudo apt-get install apache2). Без него
// проверка не проходит, а не пропускается молча: остальные проверки
// гоняются на предпросмотре, который .htaccess не читает вовсе, и эта —
// единственная, что видит правила так, как их видит хостинг.
//
// Зачем она появилась. Сторонний аудит 29.09.2026 написал, что внутренние
// страницы отвечают «Too many redirects». Открыть боевой домен из среды
// сборки нельзя (сетевая политика), и проверить было нечем. На Apache
// за прокси, как у Timeweb (SSL снимает nginx и сообщает о нём заголовком
// X-Forwarded-Proto), петли не нашлось — её даёт только клиент, который
// сам срезает косую черту в конце адреса. Зато нашлось другое: /stoimost
// уходил на /stoimost/ через http (это делал сам Apache, mod_dir), и с www
// выходило четыре перехода. Теперь любой вариант адреса — один переход
// сразу на канонический, и это здесь стережётся.
//
// Домен в проверке условный (site.test): файл от домена не зависит.

import { spawn, spawnSync } from 'node:child_process'
import { chmodSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { createServer, request } from 'node:http'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const HOST = 'site.test'
const DIST = resolve('dist')

if (!existsSync(join(DIST, 'index.html'))) {
  console.error('✗ Сайт не собран. Сначала: npm run build')
  process.exit(1)
}

const which = (cmd) => spawnSync('sh', ['-c', `command -v ${cmd}`], { encoding: 'utf8' }).stdout.trim()
const APACHE = process.env.APACHE_BIN || ['/usr/sbin/apache2', '/usr/sbin/httpd'].find(existsSync) || which('apache2') || which('httpd')
if (!APACHE) {
  console.error('✗ Не найден Apache. Установите его (Ubuntu: sudo apt-get install apache2) или укажите путь в APACHE_BIN.')
  process.exit(1)
}
const MODULES = ['/usr/lib/apache2/modules', '/usr/lib64/httpd/modules', '/usr/lib/httpd/modules', '/usr/libexec/apache2'].find(existsSync)
if (!MODULES) {
  console.error('✗ Не найдена папка модулей Apache.')
  process.exit(1)
}

// Свободный порт: спрашиваем у системы и сразу отпускаем.
const port = await new Promise((ok) => {
  const s = createServer().listen(0, '127.0.0.1', () => {
    const p = s.address().port
    s.close(() => ok(p))
  })
})

// Копия сборки во временной папке. Права 755: под root Apache отдаёт файлы
// от имени www-data, и закрытая папка дала бы 403 на всё подряд.
const work = mkdtempSync(join(tmpdir(), 'norma-htaccess-'))
chmodSync(work, 0o755)
const root = join(work, 'root')
cpSync(DIST, root, { recursive: true })
// То, что на хостинге появляется само: файл проверки Let's Encrypt,
// забытый после распаковки архив, дамп и журнал заявок.
const TOKEN = 'proverka-sertifikata-123'
cpSync(join(DIST, 'index.html'), join(root, 'site.zip'))
cpSync(join(DIST, 'index.html'), join(root, 'dump.sql'))
writeFileSync(join(root, 'api', 'leads.log.php'), '<?php exit; ?>\n{"name":"тест"}\n')
const acme = join(root, '.well-known', 'acme-challenge')
mkdirSync(acme, { recursive: true })
writeFileSync(join(acme, TOKEN), TOKEN)
spawnSync('chmod', ['-R', 'a+rX', work])

const mod = (name, file) => `LoadModule ${name}_module ${MODULES}/${file}`
const conf = join(work, 'httpd.conf')
writeFileSync(
  conf,
  [
    `ServerRoot "${work}"`,
    `DefaultRuntimeDir "${work}"`,
    `PidFile "${work}/httpd.pid"`,
    `Listen 127.0.0.1:${port}`,
    mod('mpm_event', 'mod_mpm_event.so'),
    mod('authz_core', 'mod_authz_core.so'),
    mod('dir', 'mod_dir.so'),
    mod('mime', 'mod_mime.so'),
    mod('rewrite', 'mod_rewrite.so'),
    mod('headers', 'mod_headers.so'),
    mod('filter', 'mod_filter.so'),
    mod('deflate', 'mod_deflate.so'),
    ...(process.getuid?.() === 0 ? ['User www-data', 'Group www-data'] : []),
    ...(existsSync('/etc/mime.types') ? ['TypesConfig /etc/mime.types'] : []),
    `ErrorLog "${work}/error.log"`,
    'LogLevel warn',
    `ServerName ${HOST}`,
    'UseCanonicalName Off',
    `DocumentRoot "${root}"`,
    'DirectoryIndex index.html',
    `<Directory "${root}">`,
    '  AllowOverride All',
    '  Require all granted',
    '</Directory>',
    '',
  ].join('\n'),
)

const syntax = spawnSync(APACHE, ['-f', conf, '-t'], { encoding: 'utf8' })
if (syntax.status !== 0) {
  console.error('✗ Apache не принял настройки проверки:\n' + syntax.stderr)
  rmSync(work, { recursive: true, force: true })
  process.exit(1)
}

// Своя группа процессов (detached): останавливаясь, Apache шлёт SIGTERM
// всей группе, и без неё вместе с ним гасли проверка и оболочка.
const httpd = spawn(APACHE, ['-f', conf, '-DFOREGROUND'], { stdio: 'ignore', detached: true })
httpd.unref() // иначе Node ждал бы Apache и не завершался
const cleanup = () => {
  try {
    process.kill(-httpd.pid, 'SIGTERM')
  } catch {}
  rmSync(work, { recursive: true, force: true })
}
process.on('exit', cleanup)
process.on('SIGINT', () => process.exit(130))

// Запрос так, как его передаёт nginx хостинга: схема — заголовком.
function get(url) {
  const u = new URL(url)
  return new Promise((ok, fail) => {
    const req = request(
      {
        host: '127.0.0.1',
        port,
        path: u.pathname + u.search,
        headers: { Host: u.host, 'X-Forwarded-Proto': u.protocol.replace(':', '') },
      },
      (res) => {
        let body = ''
        res.setEncoding('utf8')
        res.on('data', (c) => (body += c))
        res.on('end', () => ok({ status: res.statusCode, headers: res.headers, body }))
      },
    )
    req.on('error', fail)
    req.setTimeout(5000, () => req.destroy(new Error('нет ответа за 5 с')))
    req.end()
  })
}

// Идёт по переходам, как браузер, но не дальше шести.
async function follow(url) {
  const hops = []
  let res
  for (let i = 0; i < 6; i++) {
    res = await get(url)
    if (res.status < 300 || res.status >= 400) break
    const next = new URL(res.headers.location, url).toString()
    hops.push(next)
    url = next
  }
  return { ...res, hops, final: url }
}

const until = Date.now() + 10000
for (;;) {
  try {
    await get(`https://${HOST}/robots.txt`)
    break
  } catch {
    if (Date.now() > until) {
      console.error('✗ Apache не поднялся за 10 секунд.')
      try {
        console.error(readFileSync(join(work, 'error.log'), 'utf8').slice(-2000))
      } catch {}
      process.exit(1)
    }
    await new Promise((r) => setTimeout(r, 150))
  }
}

const S = `https://${HOST}`
const CASES = [
  // Канонические адреса отвечают сразу, без единого перехода.
  { url: `${S}/`, status: 200 },
  { url: `${S}/stoimost/`, status: 200, cache: 'no-cache' },
  { url: `${S}/uslugi/sro-stroiteley/`, status: 200 },
  { url: `${S}/baza-znaniy/kak-vstupit-v-sro/`, status: 200 },
  { url: `${S}/sitemap-index.xml`, status: 200 },
  { url: `${S}/robots.txt`, status: 200 },
  { url: `${S}/favicon.ico`, status: 200, cache: 'max-age=2592000' },
  // Любой другой вариант адреса — ровно один переход на канонический.
  { url: `${S}/stoimost`, status: 200, to: `${S}/stoimost/` },
  { url: `http://${HOST}/stoimost/`, status: 200, to: `${S}/stoimost/` },
  { url: `http://www.${HOST}/stoimost`, status: 200, to: `${S}/stoimost/` },
  { url: `https://www.${HOST}/baza-znaniy/kak-vstupit-v-sro/`, status: 200, to: `${S}/baza-znaniy/kak-vstupit-v-sro/` },
  { url: `${S}/baza-znaniy/kak-vstupit-v-sro?utm_source=test`, status: 200, to: `${S}/baza-znaniy/kak-vstupit-v-sro/?utm_source=test` },
  { url: `http://${HOST}/`, status: 200, to: `${S}/` },
  // Своя страница 404, а не заглушка хостинга и не переход.
  { url: `${S}/net-takoy-stranicy/`, status: 404, body: 'Такой страницы нет' },
  // Let's Encrypt проверяет владение доменом по http — без перехода на https.
  { url: `http://${HOST}/.well-known/acme-challenge/${TOKEN}`, status: 200, body: TOKEN },
  // Закрытое: забытый архив и дамп, служебный файл, журнал заявок.
  { url: `${S}/site.zip`, status: 403 },
  { url: `${S}/dump.sql`, status: 403 },
  { url: `${S}/.htaccess`, status: 403 },
  { url: `${S}/api/leads.log.php`, status: 403 },
]

let failed = 0
for (const c of CASES) {
  const r = await follow(c.url)
  const want = c.to ? [c.to] : []
  const problems = []
  if (r.status !== c.status) problems.push(`ответ ${r.status}, нужен ${c.status}`)
  if (r.hops.length !== want.length || r.hops.some((h, i) => h !== want[i])) {
    problems.push(`переходы: ${r.hops.length ? r.hops.join(' → ') : 'нет'}; нужны: ${want.length ? want.join(' → ') : 'нет'}`)
  }
  if (c.body && !r.body.includes(c.body)) problems.push(`в ответе нет «${c.body}»`)
  if (c.cache && !String(r.headers['cache-control'] ?? '').includes(c.cache)) {
    problems.push(`Cache-Control: ${r.headers['cache-control'] ?? 'нет'}, нужен ${c.cache}`)
  }
  if (problems.length) {
    failed++
    console.log(`  ✗ ${c.url}\n      ${problems.join('\n      ')}`)
  } else {
    console.log(`  ✓ ${c.url} — ${r.status}${r.hops.length ? `, один переход → ${r.final}` : ''}`)
  }
}

if (failed) {
  console.error(`\n✗ .htaccess: ${failed} из ${CASES.length} проверок не прошли`)
  process.exit(1)
}
console.log(`\n✓ .htaccess на Apache: ${CASES.length} проверок, петель нет, каждый неканонический адрес — один переход`)
process.exit(0)
