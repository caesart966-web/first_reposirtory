#!/usr/bin/env node
//
// Аудит ЖИВОГО сайта для поисковых систем и ИИ-помощников.
//
//   node seo-audit/audit.mjs https://sro-ssss.ru
//   node seo-audit/audit.mjs https://sro-ssss.ru --limit 500 --json отчёт.json
//
// Чем это отличается от norma-site/scripts/check-seo.mjs. Тот смотрит папку
// dist до публикации и знает, каким сайт задуман: где какие страницы, что
// должно быть в карте сайта. Здесь наоборот — исходников нет, есть чужой
// боевой домен. Поэтому проверка идёт снаружи, глазами робота: обходит сайт
// по ссылкам, как это делает Яндекс, и сверяет увиденное с тем, что сайт
// сам про себя говорит в robots.txt, карте сайта и микроразметке.
//
// Ошибки этого класса не видны в браузере вообще. Сайт открывается, выглядит
// прилично, а в выдаче его нет — потому что canonical на всех страницах
// показывает на главную, карта сайта отдаёт 404, а половина текста
// дорисовывается скриптом, которого робот не выполняет.
//
// Зависимостей нет намеренно: аудит запускают на чужой машине и на хостинге
// заказчика, где npm install делать не станут. Нужен только Node 18+.

import { writeFileSync } from 'node:fs'

// ── Аргументы ─────────────────────────────────────────────────────────────

const argv = process.argv.slice(2)
const flag = (name, def) => {
  const i = argv.indexOf(`--${name}`)
  return i === -1 ? def : argv[i + 1]
}
const has = (name) => argv.includes(`--${name}`)

const start = argv.find((a) => !a.startsWith('--') && argv[argv.indexOf(a) - 1]?.startsWith('--') === false)
  ?? argv.find((a) => /^https?:\/\//.test(a))

if (!start) {
  console.error(`Аудит сайта для поисковых систем и ИИ-помощников.

  node seo-audit/audit.mjs https://адрес.ру [ключи]

Ключи:
  --limit N          сколько страниц обойти (по умолчанию 300)
  --concurrency N    сколько запросов разом (по умолчанию 4)
  --delay N          пауза между запросами, мс (по умолчанию 150)
  --json файл        сохранить находки машинным форматом
  --ignore-robots    обходить страницы, закрытые в robots.txt
  --quiet            не показывать ход обхода`)
  process.exit(1)
}

const ORIGIN = new URL(start).origin
const LIMIT = Number(flag('limit', 300))
const CONCURRENCY = Number(flag('concurrency', 4))
const DELAY = Number(flag('delay', 150))
const TIMEOUT = Number(flag('timeout', 25000)) 
const QUIET = has('quiet')
const IGNORE_ROBOTS = has('ignore-robots')

// Представляемся честно. Робот, который прикидывается браузером, однажды
// попадёт под блокировку вместе с настоящими посетителями, и разбираться
// в этом будет некому.
//
// Только латиница: значение заголовка HTTP — байтовая строка, и кириллица
// в ней роняет сам запрос («Cannot convert argument to a ByteString»),
// причём одинаково на всех адресах — со стороны это выглядит как сайт,
// который вообще не отвечает.
const UA = 'Mozilla/5.0 (compatible; SeoAuditBot/1.0; site audit requested by the site owner)'

// ── Находки ───────────────────────────────────────────────────────────────
//
// Уровень — это не «насколько некрасиво», а «что будет, если не чинить».
// Критично — страница или сайт не попадёт в выдачу либо попадёт не тем,
// чем является. Важно — попадёт, но проиграет соседям. Замечание — заметно
// на длинной дистанции.

const CRIT = 'критично'
const HIGH = 'важно'
const NOTE = 'замечание'
const INFO = 'сведения'

// Русское числительное. Отчёт читает человек, и «2 страниц в 1 группах»
// в нём выглядит ровно так, как выглядит.
const plural = (n, one, few, many) => {
  const a = Math.abs(n) % 100
  if (a > 10 && a < 20) return many
  const b = a % 10
  if (b === 1) return one
  if (b > 1 && b < 5) return few
  return many
}
const N = (n, one, few, many) => `${n} ${plural(n, one, few, many)}`

const findings = []
const add = (level, code, title, where, hint) =>
  findings.push({ level, code, title, where: where ?? null, hint: hint ?? null })

// ── Сеть ──────────────────────────────────────────────────────────────────

const decodeEnt = (s) =>
  String(s)
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
    .replace(/&nbsp;/g, ' ')
    .replace(/&laquo;/g, '«').replace(/&raquo;/g, '»')
    .replace(/&mdash;/g, '—').replace(/&ndash;/g, '–')
    .replace(/&quot;/g, '"').replace(/&apos;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')

async function once(url, method = 'GET') {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT)
  const t0 = Date.now()
  try {
    const res = await fetch(url, {
      method,
      redirect: 'manual',
      signal: ctrl.signal,
      headers: { 'user-agent': UA, accept: 'text/html,application/xhtml+xml,*/*;q=0.8', 'accept-language': 'ru-RU,ru;q=0.9' },
    })
    const redirect = res.status >= 300 && res.status < 400
    const body = method === 'HEAD' || redirect ? '' : await res.text()
    return {
      ok: true,
      status: res.status,
      ms: Date.now() - t0,
      bytes: Buffer.byteLength(body),
      body,
      headers: Object.fromEntries([...res.headers.entries()].map(([k, v]) => [k.toLowerCase(), v])),
      location: res.headers.get('location'),
    }
  } catch (e) {
    return { ok: false, status: 0, ms: Date.now() - t0, bytes: 0, body: '', headers: {}, error: e.name === 'AbortError' ? `нет ответа за ${TIMEOUT} мс` : e.message }
  } finally {
    clearTimeout(timer)
  }
}

// Один сетевой сбой — не приговор: боевые хостинги роняют соединение
// под нагрузкой обхода. Два подряд — уже факт, о котором стоит написать.
async function get(url, method = 'GET') {
  const chain = []
  let cur = url
  for (let hop = 0; hop < 6; hop++) {
    let r = await once(cur, method)
    if (!r.ok && !/за \d+ мс/.test(r.error ?? '')) r = await once(cur, method)
    chain.push({ url: cur, status: r.status })
    if (r.status >= 300 && r.status < 400 && r.location) {
      try { cur = new URL(r.location, cur).href } catch { break }
      continue
    }
    return { ...r, chain, finalUrl: cur }
  }
  return { ok: false, status: 0, error: 'кольцо перенаправлений', chain, finalUrl: cur, headers: {}, body: '', bytes: 0, ms: 0 }
}

// ── Разбор HTML ───────────────────────────────────────────────────────────
//
// Регулярками, а не разбором дерева: тащить парсер ради двух десятков полей
// не стоит, а разметка живых сайтов всё равно ломаная — настоящий парсер
// на ней спотыкается там, где регулярка просто не найдёт тег.

const attrs = (tag) => {
  const out = {}
  for (const m of tag.matchAll(/([a-zA-Z_:][-\w:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))/g)) {
    out[m[1].toLowerCase()] = decodeEnt(m[2] ?? m[3] ?? m[4] ?? '')
  }
  for (const m of tag.matchAll(/\s([a-zA-Z_:][-\w:.]*)(?=[\s>/])/g)) {
    if (!(m[1].toLowerCase() in out)) out[m[1].toLowerCase()] = ''
  }
  return out
}

const tagsOf = (html, name) => [...html.matchAll(new RegExp(`<${name}\\b[^>]*>`, 'gi'))].map((m) => m[0])

function parse(html) {
  const p = {}
  p.lang = attrs(html.match(/<html\b[^>]*>/i)?.[0] ?? '').lang ?? ''
  p.title = decodeEnt((html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1] ?? '').replace(/\s+/g, ' ').trim())

  p.meta = {}
  for (const tag of tagsOf(html, 'meta')) {
    const a = attrs(tag)
    const key = (a.name ?? a.property ?? a['http-equiv'] ?? '').toLowerCase()
    if (key && a.content !== undefined) p.meta[key] = a.content
    if (a.charset !== undefined) p.charset = a.charset
  }
  if (!p.charset && /charset=/i.test(p.meta['content-type'] ?? '')) p.charset = 'из content-type'

  p.links = {}
  p.hrefs = []
  for (const tag of tagsOf(html, 'link')) {
    const a = attrs(tag)
    const rel = (a.rel ?? '').toLowerCase()
    if (rel && a.href) (p.links[rel] ??= []).push(a.href)
  }

  p.headings = [...html.matchAll(/<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi)].map((m) => ({
    level: Number(m[1]),
    text: decodeEnt(m[2].replace(/<[^>]*>/g, ' ')).replace(/\s+/g, ' ').trim(),
  }))

  p.anchors = []
  for (const m of html.matchAll(/<a\b([^>]*)>/gi)) {
    const a = attrs('<a' + m[1] + '>')
    if (a.href) p.anchors.push({ href: a.href, rel: (a.rel ?? '').toLowerCase(), text: '' })
  }
  for (const m of html.matchAll(/<a\b[^>]*>([\s\S]*?)<\/a>/gi)) {
    const text = decodeEnt(m[1].replace(/<[^>]*>/g, ' ')).replace(/\s+/g, ' ').trim()
    const idx = p.anchors.findIndex((x) => x.text === '' && !x.done)
    if (idx !== -1) { p.anchors[idx].text = text; p.anchors[idx].done = true }
  }

  p.images = tagsOf(html, 'img').map(attrs)
  p.scripts = tagsOf(html, 'script')
  p.inlineScriptBytes = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)]
    .reduce((n, m) => n + Buffer.byteLength(m[1]), 0)
  p.inlineStyleBytes = [...html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)]
    .reduce((n, m) => n + Buffer.byteLength(m[1]), 0)

  p.jsonld = [...html.matchAll(/<script\b[^>]*type\s*=\s*["']?application\/ld\+json["']?[^>]*>([\s\S]*?)<\/script>/gi)]
    .map((m) => m[1])
  p.microdata = /itemscope/i.test(html)

  // Видимый текст. Скрипты, стили и комментарии выбрасываем целиком —
  // иначе тысяча строк JS засчитается сайту как содержательный текст,
  // и «мало текста» не сработает ровно там, где текста нет вовсе.
  const visible = html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ')
    .replace(/<svg[\s\S]*?<\/svg>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<[^>]+>/g, ' ')
  p.text = decodeEnt(visible).replace(/\s+/g, ' ').trim()
  p.words = p.text ? p.text.split(/[\s ]+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length : 0

  return p
}

// ── Адреса ────────────────────────────────────────────────────────────────

const TRACKING = /^(utm_|yclid$|gclid$|ymclid$|fbclid$|_openstat$|from$|roistat)/i

function normalize(href, base) {
  let u
  try { u = new URL(href, base) } catch { return null }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') return null
  u.hash = ''
  for (const k of [...u.searchParams.keys()]) if (TRACKING.test(k)) u.searchParams.delete(k)
  u.search = u.searchParams.toString() ? `?${u.searchParams}` : ''
  return u.href
}

const isInternal = (url) => { try { return new URL(url).origin === ORIGIN } catch { return false } }
const isPageLike = (url) => !/\.(pdf|docx?|xlsx?|pptx?|zip|rar|7z|jpe?g|png|gif|webp|avif|svg|ico|mp4|webm|mp3|css|js|json|xml|txt|rtf|csv)$/i.test(new URL(url).pathname)
const short = (url) => { try { const u = new URL(url); return (u.pathname + u.search) || '/' } catch { return url } }

// ── robots.txt ────────────────────────────────────────────────────────────
//
// Разбираем как поисковик: группы по User-agent, самое длинное правило
// побеждает, Allow при равной длине сильнее Disallow.

function parseRobots(txt) {
  const groups = []
  let cur = null
  const sitemaps = []
  const other = []
  for (const raw of txt.split(/\r?\n/)) {
    const line = raw.replace(/#.*$/, '').trim()
    if (!line) continue
    const [k, ...rest] = line.split(':')
    const key = k.trim().toLowerCase()
    const val = rest.join(':').trim()
    if (key === 'user-agent') {
      if (!cur || cur.rules.length) { cur = { agents: [], rules: [] }; groups.push(cur) }
      cur.agents.push(val.toLowerCase())
    } else if (key === 'allow' || key === 'disallow') {
      if (!cur) { cur = { agents: ['*'], rules: [] }; groups.push(cur) }
      cur.rules.push({ allow: key === 'allow', path: val })
    } else if (key === 'sitemap') sitemaps.push(val)
    else other.push({ key, val })
  }
  return { groups, sitemaps, other }
}

function robotsAllows(robots, agent, pathname) {
  if (!robots) return true
  const a = agent.toLowerCase()
  const exact = robots.groups.filter((g) => g.agents.some((x) => x !== '*' && a.includes(x)))
  const group = exact.length ? exact : robots.groups.filter((g) => g.agents.includes('*'))
  let best = null
  for (const g of group) {
    for (const r of g.rules) {
      if (r.path === '') continue
      const re = new RegExp('^' + r.path.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\$$/, '$'))
      if (re.test(pathname)) {
        if (!best || r.path.length > best.path.length || (r.path.length === best.path.length && r.allow)) best = r
      }
    }
  }
  return best ? best.allow : true
}

// ── Обход ─────────────────────────────────────────────────────────────────

const pages = new Map()      // url → разобранная страница
const linkStatus = new Map() // url → статус (в т.ч. не-HTML)
const inbound = new Map()    // url → сколько внутренних ссылок на него
const queue = []
const seen = new Set()
let robots = null
let robotsRes = null

// Читается до обхода: краулер спрашивает у robots.txt, куда ему можно,
// а проверки самого файла идут позже, вместе с остальными проверками сайта.
async function loadRobots() {
  robotsRes = await get(`${ORIGIN}/robots.txt`)
  if (robotsRes.status === 200 && robotsRes.body.trim() && !/<html/i.test(robotsRes.body)) {
    robots = parseRobots(robotsRes.body)
  }
}

const enqueue = (url, depth, from) => {
  if (!isInternal(url) || seen.has(url)) return
  seen.add(url)
  queue.push({ url, depth, from })
}

async function crawl() {
  const home = normalize(start, start)
  enqueue(home, 0, null)
  let done = 0

  const worker = async () => {
    for (;;) {
      const job = queue.shift()
      if (!job) return
      if (pages.size >= LIMIT) return
      if (DELAY) await new Promise((r) => setTimeout(r, DELAY))

      const res = await get(job.url)
      linkStatus.set(job.url, res.status)
      done++
      if (!QUIET) process.stderr.write(`\r  обойдено ${String(done).padStart(4)} · в очереди ${String(queue.length).padStart(4)} · ${short(job.url).slice(0, 48).padEnd(48)}`)

      if (!res.ok) { add(CRIT, 'net', 'страница не отвечает', `${short(job.url)} — ${res.error}`); continue }

      const ct = res.headers['content-type'] ?? ''
      if (!/text\/html/i.test(ct)) continue
      if (res.status !== 200) continue

      const p = parse(res.body)
      p.url = job.url
      p.depth = job.depth
      p.res = res
      p.from = job.from
      pages.set(job.url, p)

      for (const a of p.anchors) {
        const abs = normalize(a.href, job.url)
        if (!abs || !isInternal(abs)) continue
        inbound.set(abs, (inbound.get(abs) ?? 0) + 1)
        if (!isPageLike(abs)) { if (!seen.has(abs)) { seen.add(abs); linkStatus.set(abs, null) } ; continue }
        if (a.rel.includes('nofollow')) continue
        const path = new URL(abs).pathname
        if (!IGNORE_ROBOTS && !robotsAllows(robots, 'yandexbot', path)) continue
        enqueue(abs, job.depth + 1, job.url)
      }
    }
  }

  await Promise.all(Array.from({ length: CONCURRENCY }, worker))
  if (!QUIET) process.stderr.write('\r' + ' '.repeat(100) + '\r')
}

// ── Проверки одной страницы ───────────────────────────────────────────────

const AI_BOTS = [
  ['GPTBot', 'ChatGPT: обучение и обход'],
  ['OAI-SearchBot', 'ChatGPT Search: показ сайта в ответах'],
  ['ChatGPT-User', 'ChatGPT: переход по ссылке в диалоге'],
  ['PerplexityBot', 'Perplexity: индекс'],
  ['Perplexity-User', 'Perplexity: переход по ссылке'],
  ['ClaudeBot', 'Claude: обход'],
  ['Claude-User', 'Claude: переход по ссылке в диалоге'],
  ['Google-Extended', 'Gemini и обзоры от ИИ в Google'],
  ['Applebot-Extended', 'Apple Intelligence'],
  ['CCBot', 'Common Crawl — из него учится половина моделей'],
  ['Amazonbot', 'Amazon / Alexa'],
  ['meta-externalagent', 'Meta AI'],
  ['Bytespider', 'TikTok / Doubao'],
]

function checkPage(p) {
  const u = short(p.url)
  const self = p.res.finalUrl ?? p.url
  const meta = p.meta
  const robotsMeta = (meta.robots ?? '').toLowerCase()
  const noindex = /noindex/.test(robotsMeta) || /noindex/.test((meta.yandex ?? '').toLowerCase())
  p.noindex = noindex

  if (p.res.chain.length > 1) {
    add(NOTE, 'link-redirect', 'внутренняя ссылка ведёт через перенаправление',
      `${u} → ${short(self)}`,
      'Каждый переход — лишний запрос и потеря части ссылочного веса. Ссылки внутри сайта должны вести сразу на конечный адрес.')
  }

  if (noindex) {
    add(INFO, 'noindex', 'страница закрыта от индексации мета-тегом', u,
      'Если это раздел, который должен искаться, — снимите noindex.')
  }

  // ── Заголовок и описание: то, что человек видит в выдаче ────────────────
  if (!p.title) add(CRIT, 'title-missing', 'нет тега <title>', u, 'Без заголовка поисковик придумает его сам из текста страницы — как правило, неудачно.')
  else if (p.title.length < 25) add(HIGH, 'title-short', 'слишком короткий <title>', `${u} — «${p.title}» (${p.title.length})`, 'В сниппет помещается 60–70 знаков. Короткий заголовок не отвечает ни на один запрос целиком.')
  else if (p.title.length > 70) add(NOTE, 'title-long', 'длинный <title>: хвост обрежется в выдаче', `${u} — ${p.title.length} знаков`, 'Главное — в первые 60 знаков; название компании лучше в конец.')

  const desc = meta.description ?? ''
  if (!desc) add(HIGH, 'desc-missing', 'нет описания (meta description)', u, 'Яндекс и Google соберут сниппет из случайного куска текста. Описание — единственный способ управлять тем, что видит человек в выдаче.')
  else if (desc.length < 50) add(NOTE, 'desc-short', 'слишком короткое описание', `${u} — ${desc.length} знаков`, 'Рабочая длина — 120–180 знаков.')
  else if (desc.length > 220) add(NOTE, 'desc-long', 'слишком длинное описание', `${u} — ${desc.length} знаков`)

  // ── Заголовки в тексте ─────────────────────────────────────────────────
  const h1 = p.headings.filter((h) => h.level === 1)
  if (h1.length === 0) add(HIGH, 'h1-missing', 'на странице нет заголовка H1', u, 'H1 говорит поисковику, о чём страница. Его отсутствие — самая частая причина, по которой страница ранжируется не по своему запросу.')
  else if (h1.length > 1) add(NOTE, 'h1-many', 'несколько H1 на одной странице', `${u} — ${N(h1.length, 'штука', 'штуки', 'штук')}`, 'H1 должен быть один: он отвечает на вопрос «что это за страница».')
  else if (!h1[0].text) add(HIGH, 'h1-empty', 'H1 пустой (картинка или значок без текста)', u)

  let prev = 0
  for (const h of p.headings) {
    if (prev && h.level > prev + 1) {
      add(NOTE, 'heading-skip', 'пропущен уровень заголовка', `${u} — H${prev} → H${h.level}`,
        'Заголовки — это оглавление страницы. Пропуск уровня ломает его и для поисковика, и для читалки с экрана.')
      break
    }
    prev = h.level
  }

  // ── Технические сигналы ────────────────────────────────────────────────
  if (!p.lang) add(NOTE, 'lang-missing', 'у тега <html> нет атрибута lang', u, 'Для русскоязычного сайта: <html lang="ru">.')
  if (!meta.viewport) add(CRIT, 'viewport-missing', 'нет мета-тега viewport', u, 'Без него телефон показывает сайт уменьшенной копией десктопа. Мобильная выдача такую страницу понижает.')
  if (!p.charset) add(HIGH, 'charset-missing', 'не объявлена кодировка', u, '<meta charset="utf-8"> первой строкой в <head>.')

  const canon = (p.links.canonical ?? [])[0]
  if (!canon && !noindex) {
    add(HIGH, 'canonical-missing', 'нет canonical', u,
      'Без canonical любой адрес с меткой (?utm_source=…) становится для поисковика отдельной страницей-дублем.')
  } else if (canon) {
    if (!/^https?:\/\//i.test(canon)) add(HIGH, 'canonical-relative', 'canonical записан относительным адресом', `${u} → ${canon}`, 'Canonical должен быть полным адресом с https:// и доменом.')
    const abs = normalize(canon, self)
    if (abs && abs !== normalize(self, self)) {
      const sameButSlash = abs.replace(/\/$/, '') === normalize(self, self)?.replace(/\/$/, '')
      add(sameButSlash ? NOTE : CRIT, 'canonical-other',
        sameButSlash ? 'canonical отличается косой чертой на конце' : 'canonical показывает на другую страницу',
        `${u} → ${short(abs)}`,
        sameButSlash ? 'Выберите один вид адреса и держитесь его везде.' :
          'Поисковик выбросит эту страницу из выдачи и оставит ту, на которую показывает canonical. Если это не задумано — страница потеряна.')
    }
  }

  // ── Карточка ссылки в мессенджерах и соцсетях ──────────────────────────
  const ogNeed = ['og:title', 'og:description', 'og:image', 'og:url', 'og:type']
  const ogMissing = ogNeed.filter((k) => !meta[k])
  if (ogMissing.length === ogNeed.length) {
    add(HIGH, 'og-none', 'нет Open Graph: ссылка в мессенджере придёт голой строкой', u,
      'og:title, og:description, og:image, og:url, og:type. Ссылку на сайт пересылают в WhatsApp и Telegram чаще, чем открывают из выдачи.')
  } else if (ogMissing.length) {
    add(NOTE, 'og-partial', 'Open Graph заполнен наполовину', `${u} — нет: ${ogMissing.join(', ')}`)
  }
  if (meta['og:url'] && canon) {
    const a = normalize(meta['og:url'], self), b = normalize(canon, self)
    if (a && b && a !== b) add(NOTE, 'og-url-mismatch', 'og:url и canonical показывают на разные адреса', u)
  }

  // ── Микроразметка ──────────────────────────────────────────────────────
  if (p.jsonld.length === 0) {
    add(p.microdata ? NOTE : HIGH, 'jsonld-missing',
      p.microdata ? 'микроразметка только старым способом (microdata)' : 'нет микроразметки JSON-LD', u,
      'Через неё поисковик понимает, что перед ним организация, услуга, статья или вопрос-ответ. Без неё расширенный вид сниппета недоступен, а ИИ-помощники берут со страницы меньше.')
  } else {
    const types = new Set()
    const declared = new Set(), refs = []
    for (const raw of p.jsonld) {
      let data
      try { data = JSON.parse(raw) } catch (e) {
        add(HIGH, 'jsonld-broken', 'микроразметка не разбирается как JSON', `${u} — ${e.message}`,
          'Сломанная разметка не просто не работает — поисковик перестаёт доверять и остальной.')
        continue
      }
      const walk = (v) => {
        if (Array.isArray(v)) return v.forEach(walk)
        if (!v || typeof v !== 'object') return
        if (v['@type']) [].concat(v['@type']).forEach((t) => types.add(t))
        // Узел с одним только @id — это ссылка на другой узел, а не объявление.
        if (typeof v['@id'] === 'string') {
          if (Object.keys(v).length > 1) declared.add(v['@id'])
          else refs.push(v['@id'])
        }
        Object.values(v).forEach(walk)
      }
      walk(data)
    }
    p.schemaTypes = types
    for (const r of new Set(refs)) if (!declared.has(r)) add(NOTE, 'jsonld-ref', 'микроразметка ссылается на необъявленный узел', `${u} → ${r}`)
    if (p.depth > 0 && !types.has('BreadcrumbList')) {
      add(NOTE, 'breadcrumbs-missing', 'нет разметки хлебных крошек', u,
        'С ней в выдаче вместо голого адреса показывается путь «Главная › Раздел › Страница» — сниппет становится шире и понятнее.')
    }
  }

  // ── Картинки ───────────────────────────────────────────────────────────
  const noAlt = p.images.filter((i) => i.alt === undefined)
  if (noAlt.length) add(NOTE, 'img-alt', 'у картинок нет подписи alt', `${u} — ${noAlt.length} из ${N(p.images.length, 'картинки', 'картинок', 'картинок')}`,
    'Alt — это и поиск по картинкам, и доступность, и подстраховка, когда картинка не загрузилась.')
  const noSize = p.images.filter((i) => i.src && !(i.width && i.height) && !/^data:/.test(i.src))
  if (noSize.length > 2) add(NOTE, 'img-size', 'у картинок не заданы width и height', `${u} — ${N(noSize.length, 'картинка', 'картинки', 'картинок')}`,
    'Браузер не знает, сколько места занять, и текст прыгает при загрузке. Это прямо ухудшает CLS — один из трёх показателей Core Web Vitals.')
  const lazyMissing = p.images.length > 4 && p.images.filter((i) => i.loading === 'lazy').length === 0
  if (lazyMissing) add(NOTE, 'img-lazy', 'ни одна картинка не грузится отложенно', `${u} — ${N(p.images.length, 'картинка', 'картинки', 'картинок')}`, 'loading="lazy" всем картинкам ниже первого экрана.')

  // ── Содержимое ─────────────────────────────────────────────────────────
  if (!noindex && p.words < 250) {
    const jsHeavy = p.words < 120 && p.scripts.length >= 3
    add(jsHeavy ? CRIT : NOTE, jsHeavy ? 'js-rendered' : 'thin',
      jsHeavy ? 'текста на странице почти нет — содержимое, похоже, дорисовывает скрипт' : 'мало текста на странице',
      `${u} — ${N(p.words, 'слово', 'слова', 'слов')}, скриптов ${p.scripts.length}`,
      jsHeavy
        ? 'Робот Яндекса выполняет JavaScript выборочно и с задержкой в недели. Если реестр, новости или каталог собираются на стороне браузера — для поиска их нет. Нужен серверный рендеринг или предрендер.'
        : 'Страница с 100 словами не ответит ни на один развёрнутый запрос.')
  }

  // ── Скорость и вес ─────────────────────────────────────────────────────
  if (p.res.bytes > 200 * 1024) add(NOTE, 'html-heavy', 'тяжёлый HTML', `${u} — ${(p.res.bytes / 1024).toFixed(0)} КБ`, 'Обычная страница — 30–80 КБ. Всё сверх этого чаще всего вставленные стили и данные, которым место в отдельных файлах.')
  if (p.res.ms > 1500) add(HIGH, 'slow', 'страница отвечает дольше 1,5 с', `${u} — ${p.res.ms} мс`, 'Скорость ответа сервера — прямой фактор ранжирования и первое, что видит робот.')
  if (p.inlineScriptBytes > 100 * 1024) add(NOTE, 'inline-js', 'много кода прямо в HTML', `${u} — ${(p.inlineScriptBytes / 1024).toFixed(0)} КБ скриптов внутри страницы`)

  // ── Смешанное содержимое ───────────────────────────────────────────────
  if (self.startsWith('https://')) {
    const httpRes = [...p.res.body.matchAll(/(?:src|href)\s*=\s*["'](http:\/\/[^"']+)["']/gi)]
      .map((m) => m[1]).filter((x) => !/^http:\/\/(www\.)?(w3\.org|schema\.org|purl\.org|ogp\.me)/.test(x))
    if (httpRes.length) add(HIGH, 'mixed', 'на защищённой странице есть ссылки по http://', `${u} — ${httpRes.length} шт., напр. ${httpRes[0].slice(0, 60)}`,
      'Браузер блокирует такие файлы молча: картинка не покажется, скрипт не выполнится.')
  }

  // ── Адрес страницы ─────────────────────────────────────────────────────
  const path = new URL(self).pathname
  if (/[A-Z]/.test(path)) add(NOTE, 'url-case', 'заглавные буквы в адресе', u, 'Для сервера /Uslugi и /uslugi — разные страницы. Это готовый дубль.')
  if (/_/.test(path)) add(NOTE, 'url-underscore', 'подчёркивание в адресе', u, 'Разделитель слов в адресе — дефис.')
  if (/%[0-9a-f]{2}/i.test(path)) add(NOTE, 'url-cyrillic', 'кириллица в адресе', u, 'В ссылках, письмах и отчётах такой адрес превращается в нечитаемую строку из процентов.')
  if (p.depth > 4) add(NOTE, 'url-deep', 'страница глубоко от главной', `${u} — ${N(p.depth, 'переход', 'перехода', 'переходов')} от главной`, 'Всё, что дальше 3–4 кликов, обходится реже и ранжируется хуже.')
}

// ── Проверки сайта целиком ────────────────────────────────────────────────

function detectEngine(home) {
  const h = (home.res.body + JSON.stringify(home.res.headers)).toLowerCase()
  const marks = [
    [/\/bitrix\/|bitrix_sessid|1c-bitrix/, '1С-Битрикс'],
    [/wp-content|wp-includes|wp-json/, 'WordPress'],
    [/tilda|tildacdn/, 'Tilda'],
    [/\/local\/templates\//, '1С-Битрикс (свой шаблон)'],
    [/modx|assets\/components/, 'MODX'],
    [/joomla|\/media\/jui\//, 'Joomla'],
    [/drupal-settings-json|\/sites\/default\/files\//, 'Drupal'],
    [/cs\.cart|\/var\/themes_repository\//, 'CS-Cart'],
    [/nuxt|__NUXT__/, 'Nuxt (JavaScript)'],
    [/__NEXT_DATA__/, 'Next.js (JavaScript)'],
    [/data-reactroot|react\.production/, 'React (JavaScript)'],
    [/umi\.cms|umicms/, 'UMI.CMS'],
    [/netcat/, 'NetCat'],
  ]
  return marks.filter(([re]) => re.test(h)).map(([, name]) => name)
}

async function checkSite() {
  const home = pages.get(normalize(start, start)) ?? [...pages.values()][0]

  // ── robots.txt ─────────────────────────────────────────────────────────
  const r = robotsRes
  if (!robots) {
    add(CRIT, 'robots-missing', 'нет robots.txt', `${ORIGIN}/robots.txt — ответ ${r.status || r.error}`,
      'Без него поисковик обходит служебные адреса, корзины и результаты фильтров, тратя на них лимит обхода вместо настоящих страниц.')
  } else {
    const all = robots.groups.filter((g) => g.agents.includes('*'))
    if (all.some((g) => g.rules.some((x) => !x.allow && x.path === '/'))) {
      add(CRIT, 'robots-disallow-all', 'robots.txt закрывает от индексации весь сайт', 'Disallow: /',
        'Пока эта строка на месте, ничего остальное не имеет значения: сайта в поиске не будет.')
    }
    if (!robots.sitemaps.length) {
      add(HIGH, 'robots-no-sitemap', 'в robots.txt нет строки Sitemap', ORIGIN,
        'Строка Sitemap: https://домен/sitemap.xml — самый простой способ показать поисковику все страницы разом.')
    }
    for (const { key } of robots.other) {
      if (key === 'host') add(NOTE, 'robots-host', 'в robots.txt осталась устаревшая директива Host', ORIGIN, 'Яндекс не учитывает её с 2018 года; главное зеркало задаётся редиректом на один домен.')
      if (key === 'crawl-delay') add(NOTE, 'robots-crawl-delay', 'в robots.txt осталась директива Crawl-delay', ORIGIN, 'Яндекс не учитывает её с 2018 года — скорость обхода задаётся в Вебмастере.')
    }
    if (!robots.other.some(({ key }) => key === 'clean-param') && [...pages.keys()].some((u) => u.includes('?'))) {
      add(NOTE, 'robots-clean-param', 'нет Clean-param, а адреса с параметрами на сайте есть', ORIGIN,
        'Clean-param убирает из индекса дубли вида ?sort=, ?page=, ?utm_source=. Директива понимается только Яндексом, но в русскоязычной выдаче это половина дела.')
    }
    for (const asset of ['/css/', '/js/', '/assets/', '/static/', '/bitrix/templates/']) {
      if (!robotsAllows(robots, 'googlebot', asset + 'x.css')) {
        add(HIGH, 'robots-assets', 'robots.txt закрывает стили или скрипты', `запрещено: ${asset}`,
          'Google рисует страницу целиком, чтобы оценить её на телефоне. Со скрытыми стилями он видит голый текст и считает страницу неадаптированной.')
        break
      }
    }

    // ИИ-помощники — то, ради чего затевается GEO. Здесь важно понимать,
    // что закрыто, а что открыто: закрытый GPTBot означает, что сайта нет
    // в ответах ChatGPT, и никакой llms.txt этого не исправит.
    const blocked = AI_BOTS.filter(([bot]) => !robotsAllows(robots, bot, '/'))
    if (blocked.length) {
      add(HIGH, 'robots-ai-blocked', 'robots.txt закрывает роботов ИИ-сервисов',
        blocked.map(([b, why]) => `${b} — ${why}`).join('; '),
        'Если сайт хотят видеть в ответах ИИ, этих роботов надо пускать. Если наоборот — решение осознанное, и тогда задача «попасть в ответы ИИ» снимается.')
    } else {
      add(INFO, 'robots-ai-open', 'роботы ИИ-сервисов не заблокированы', 'GPTBot, PerplexityBot, ClaudeBot, Google-Extended и другие проходят')
    }
    for (const bot of ['yandexbot', 'googlebot']) {
      if (!robotsAllows(robots, bot, '/')) add(CRIT, 'robots-search-blocked', `robots.txt закрывает ${bot}`, ORIGIN)
    }
  }

  // ── Карта сайта ────────────────────────────────────────────────────────
  const candidates = new Set([...(robots?.sitemaps ?? []), `${ORIGIN}/sitemap.xml`, `${ORIGIN}/sitemap_index.xml`, `${ORIGIN}/sitemap-index.xml`])
  const sitemapUrls = new Map()
  let sitemapFound = false

  const readSitemap = async (url, depth = 0) => {
    if (depth > 2) return
    const res = await get(url)
    if (res.status !== 200) {
      if ((robots?.sitemaps ?? []).includes(url)) {
        add(CRIT, 'sitemap-broken', 'карта сайта, указанная в robots.txt, не открывается', `${url} — ответ ${res.status || res.error}`)
      }
      return
    }
    if (/\.gz$/i.test(url)) { add(INFO, 'sitemap-gz', 'карта сайта сжата (.gz) — содержимое не проверялось', url); sitemapFound = true; return }
    if (!/<(urlset|sitemapindex)/i.test(res.body)) {
      add(HIGH, 'sitemap-not-xml', 'по адресу карты сайта лежит не XML', url); return
    }
    sitemapFound = true
    for (const m of res.body.matchAll(/<sitemap>[\s\S]*?<loc>([^<]+)<\/loc>/gi)) await readSitemap(m[1].trim(), depth + 1)
    for (const m of res.body.matchAll(/<url>([\s\S]*?)<\/url>/gi)) {
      const loc = m[1].match(/<loc>([^<]+)<\/loc>/i)?.[1]?.trim()
      if (loc) sitemapUrls.set(normalize(loc, ORIGIN) ?? loc, { lastmod: m[1].match(/<lastmod>([^<]+)<\/lastmod>/i)?.[1] })
    }
  }
  for (const c of candidates) await readSitemap(c)

  if (!sitemapFound) {
    add(CRIT, 'sitemap-missing', 'карта сайта не найдена', `искали: ${[...candidates].map(short).join(', ')}`,
      'Без неё поисковик находит страницы только по ссылкам. Всё, на что нет прямой ссылки из меню, в индекс не попадёт.')
  } else {
    const noLastmod = [...sitemapUrls.values()].filter((v) => !v.lastmod).length
    if (noLastmod === sitemapUrls.size && sitemapUrls.size) {
      add(NOTE, 'sitemap-no-lastmod', 'в карте сайта нет дат изменения (lastmod)', N(sitemapUrls.size, 'адрес', 'адреса', 'адресов'),
        'По дате поисковик решает, что перечитывать в первую очередь. Только дата должна быть настоящей: если при каждой публикации меняются все страницы разом, поисковик перестаёт учитывать её вовсе.')
    }
    const crawled = new Set([...pages.keys()].filter((u) => !pages.get(u).noindex))
    const missing = [...crawled].filter((u) => !sitemapUrls.has(u) && !sitemapUrls.has(u + '/') && !sitemapUrls.has(u.replace(/\/$/, '')))
    if (missing.length) {
      add(HIGH, 'sitemap-gaps', 'страницы сайта отсутствуют в карте сайта',
        `${missing.length} из ${N(crawled.size, 'страницы', 'страниц', 'страниц')}: ${missing.slice(0, 5).map(short).join(', ')}`,
        'Такие страницы поисковик найдёт позже остальных или не найдёт вовсе.')
    }
    // Адреса из карты, до которых нет ссылок с сайта: либо страница-сирота,
    // либо карта отстала от жизни и ведёт в никуда.
    const orphans = [...sitemapUrls.keys()].filter((u) => isInternal(u) && !pages.has(u) && !inbound.has(u)).slice(0, 40)
    if (orphans.length) {
      const sample = []
      for (const u of orphans.slice(0, 10)) {
        const res = await get(u, 'HEAD')
        sample.push({ u, status: res.status })
      }
      const dead = sample.filter((s) => s.status >= 400 || s.status === 0)
      if (dead.length) add(HIGH, 'sitemap-dead', 'карта сайта ведёт на несуществующие страницы',
        dead.slice(0, 5).map((d) => `${short(d.u)} — ${d.status || 'нет ответа'}`).join('; '),
        'Поисковик считает это признаком заброшенного сайта и снижает частоту обхода.')
      const alive = sample.filter((s) => s.status === 200)
      if (alive.length) add(NOTE, 'orphan', 'страницы есть в карте сайта, но на них нет ссылок с самого сайта',
        alive.slice(0, 5).map((d) => short(d.u)).join('; '),
        'Страница без входящих ссылок почти не получает веса и ранжируется сама по себе.')
    }
  }

  // ── Один сайт — один адрес ─────────────────────────────────────────────
  const { protocol, host } = new URL(ORIGIN)
  const altHost = host.startsWith('www.') ? host.slice(4) : 'www.' + host
  const alt = await get(`${protocol}//${altHost}/`)
  if (alt.status === 200 && alt.chain.length === 1) {
    add(CRIT, 'mirror', 'сайт открывается по двум адресам сразу, без перенаправления',
      `${host} и ${altHost} — оба отвечают 200`,
      'Для поисковика это два разных сайта с одинаковым содержимым. Вес делится пополам, а какой из них показывать — он решает сам. Лечится постоянным редиректом 301 на один из адресов.')
  }
  if (protocol === 'https:') {
    const plain = await get(`http://${host}/`)
    if (plain.status === 200) {
      add(CRIT, 'http-open', 'сайт открывается по незащищённому http:// без перенаправления', `http://${host}/`,
        'Тот же дубль плюс предупреждение браузера. Нужен постоянный редирект 301 на https://.')
    } else if (plain.chain.length > 2) {
      add(NOTE, 'http-chain', 'от http:// до конечного адреса несколько перенаправлений подряд', plain.chain.map((c) => short(c.url)).join(' → '))
    }
  } else {
    add(CRIT, 'no-https', 'сайт работает без защищённого соединения', ORIGIN,
      'Браузеры помечают такой сайт как ненадёжный, форма заявки на нём собирает персональные данные открытым текстом, а поисковики считают HTTPS фактором ранжирования с 2014 года.')
  }

  // Косая черта на конце. Проверяем на живых страницах: если оба вида
  // отдают 200 и каждый считает себя главным — это дубль на каждой странице
  // сайта разом, самая массовая ошибка из всех возможных.
  const sample = [...pages.values()].filter((p) => new URL(p.url).pathname !== '/').slice(0, 3)
  for (const p of sample) {
    const u = new URL(p.url)
    const variant = u.pathname.endsWith('/') ? p.url.replace(/\/(\?|$)/, '$1') : p.url.replace(/(\?|$)/, '/$1')
    if (variant === p.url) continue
    const res = await get(variant)
    if (res.status === 200 && res.chain.length === 1) {
      const c = (parse(res.body).links.canonical ?? [])[0]
      const points = c ? normalize(c, variant) : null
      if (!points || points === normalize(variant, variant)) {
        add(CRIT, 'slash-dup', 'адрес с косой чертой на конце и без неё — две разные страницы',
          `${short(p.url)} и ${short(variant)} обе отвечают 200`,
          'Каждая страница сайта существует в двух экземплярах. Нужен 301 с одного вида на другой.')
        break
      }
    }
  }

  // ── Несуществующая страница ────────────────────────────────────────────
  const ghost = await get(`${ORIGIN}/net-takoy-stranicy-${Date.now()}/`)
  if (ghost.status === 200) {
    add(CRIT, 'soft-404', 'несуществующая страница отвечает «200 ОК»',
      short(ghost.finalUrl),
      'Поисковик решает, что по любому адресу на сайте что-то есть, и заносит в индекс бесконечное число пустых страниц. Ответ должен быть 404.')
  } else if (ghost.status >= 300 && ghost.status < 400) {
    add(HIGH, 'redirect-404', 'несуществующая страница перенаправляет вместо ответа 404', `→ ${short(ghost.finalUrl)}`,
      'Перенаправление на главную поисковик считает мягкой ошибкой 404 и всё равно исключает адрес — но сначала тратит на него обход.')
  }

  // ── Оглавление для ИИ-помощников ───────────────────────────────────────
  const llms = await get(`${ORIGIN}/llms.txt`)
  if (llms.status !== 200 || /<html/i.test(llms.body)) {
    add(NOTE, 'llms-missing', 'нет llms.txt', ORIGIN,
      'Договорённость молодая и её пока читают не все, но файл стоит десяти минут: это короткое оглавление сайта в markdown для ИИ-помощников.')
  }

  // ── Счётчики, права, заголовки ─────────────────────────────────────────
  if (home) {
    const html = home.res.body
    if (!/mc\.yandex\.ru|ym\(\s*\d+/.test(html)) {
      add(HIGH, 'metrika-missing', 'на главной не найдена Яндекс.Метрика', ORIGIN,
        'Без Метрики нельзя ни увидеть, откуда идут заявки, ни настроить цели, ни передать данные в Директ. Плюс Метрика — источник поведенческих данных для самого Яндекса.')
    }
    if (!home.meta['yandex-verification'] && !/yandex_verification/i.test(html)) {
      add(NOTE, 'webmaster-meta', 'нет мета-тега подтверждения прав в Яндекс.Вебмастере', ORIGIN,
        'Права можно подтвердить и файлом, и записью DNS — тогда замечание снимается. Но без Вебмастера не видно ни ошибок обхода, ни запросов, по которым сайт показывают.')
    }
    const h = home.res.headers
    if (!h['strict-transport-security']) add(NOTE, 'hsts', 'нет заголовка HSTS', ORIGIN, 'Strict-Transport-Security заставляет браузер идти сразу по https и убирает лишнее перенаправление.')
    if (h['x-powered-by'] || h['server']?.match(/\d/)) {
      add(INFO, 'server-version', 'сервер сообщает свою версию в заголовках', `${h.server ?? ''} ${h['x-powered-by'] ?? ''}`.trim())
    }
    const engine = detectEngine(home)
    if (engine.length) add(INFO, 'engine', 'движок сайта (определён по разметке)', engine.join(', '))
  }

  // ── Дубли между страницами ─────────────────────────────────────────────
  const byTitle = new Map(), byDesc = new Map(), byH1 = new Map(), byText = new Map()
  for (const p of pages.values()) {
    if (p.noindex) continue
    const push = (map, key) => { if (key) (map.get(key) ?? map.set(key, []).get(key)).push(p.url) }
    push(byTitle, p.title)
    push(byDesc, p.meta.description)
    push(byH1, p.headings.find((h) => h.level === 1)?.text)
    push(byText, p.words > 80 ? p.text.slice(0, 600) : null)
  }
  const dup = (map, level, code, title, hint) => {
    const groups = [...map.entries()].filter(([, list]) => list.length > 1)
    if (!groups.length) return
    const total = groups.reduce((n, [, l]) => n + l.length, 0)
    add(level, code, title, `${N(total, 'страница', 'страницы', 'страниц')} в ${N(groups.length, 'группе', 'группах', 'группах')}, напр.: ${groups[0][1].slice(0, 3).map(short).join(', ')}`, hint)
  }
  dup(byTitle, CRIT, 'title-dup', 'одинаковый <title> у разных страниц',
    'Поисковик считает такие страницы дублями и оставляет в выдаче одну. Заголовок должен отвечать на запрос именно этой страницы.')
  dup(byDesc, HIGH, 'desc-dup', 'одинаковое описание у разных страниц',
    'Одно описание на весь сайт равносильно его отсутствию: сниппет будет собран автоматически.')
  dup(byH1, NOTE, 'h1-dup', 'одинаковый H1 у разных страниц', 'Чаще всего это название компании вместо темы страницы.')
  dup(byText, CRIT, 'text-dup', 'одинаковый текст у разных адресов',
    'Полные дубли делят между собой вес и мешают друг другу. Лечится canonical или склейкой страниц.')

  // ── Страницы без входящих ссылок ───────────────────────────────────────
  const noIn = [...pages.values()].filter((p) => p.depth > 0 && (inbound.get(p.url) ?? 0) <= 1)
  if (noIn.length > 3) {
    add(NOTE, 'weak-linking', 'на многие страницы ведёт единственная ссылка',
      `${N(noIn.length, 'страница', 'страницы', 'страниц')}, напр.: ${noIn.slice(0, 4).map((p) => short(p.url)).join(', ')}`,
      'Перелинковка внутри сайта — самый дешёвый способ поднять важные страницы: ссылки из текста статей, блок «читайте также», крошки.')
  }

  // ── Битые внутренние ссылки ────────────────────────────────────────────
  const unknown = [...linkStatus.entries()].filter(([, s]) => s === null).map(([u]) => u).slice(0, 60)
  for (const u of unknown) {
    const res = await get(u, 'HEAD')
    linkStatus.set(u, res.status)
  }
  const broken = [...linkStatus.entries()].filter(([, s]) => s !== null && (s >= 400 || s === 0))
  if (broken.length) {
    add(HIGH, 'broken', 'битые ссылки внутри сайта',
      `${N(broken.length, 'ссылка', 'ссылки', 'ссылок')}: ${broken.slice(0, 5).map(([u, s]) => `${short(u)} — ${s || 'нет ответа'}`).join('; ')}`,
      'Битая ссылка тратит обход впустую и уводит посетителя в тупик.')
  }

  // ── Разметка вопросов и услуг по сайту ─────────────────────────────────
  const allTypes = new Set()
  for (const p of pages.values()) for (const t of p.schemaTypes ?? []) allTypes.add(t)
  for (const [type, why] of [
    ['Organization', 'узел организации: название, адрес, телефон, реквизиты — основа для карточки в выдаче и для ИИ-помощников'],
    ['FAQPage', 'вопросы и ответы: попадание в быстрые ответы и в пересказы ИИ'],
    ['BreadcrumbList', 'хлебные крошки: путь вместо голого адреса в сниппете'],
  ]) {
    const ok = [...allTypes].some((t) => t === type || (type === 'Organization' && /Organization|LocalBusiness|ProfessionalService|NGO/.test(t)))
    if (!ok) add(HIGH, `schema-${type}`, `на сайте нигде нет разметки ${type}`, why)
  }
}

// ── Отчёт ─────────────────────────────────────────────────────────────────
//
// Находки собираются по коду, а не сыплются по одной: «нет описания»
// на восьмидесяти страницах — это одна задача, а не восемьдесят строк,
// в которых тонут остальные девять.

const ORDER = [CRIT, HIGH, NOTE, INFO]

function report() {
  const groups = new Map()
  for (const f of findings) {
    const g = groups.get(f.code) ?? { level: f.level, code: f.code, title: f.title, hint: f.hint, wheres: [] }
    if (f.where) g.wheres.push(f.where)
    if (!g.hint && f.hint) g.hint = f.hint
    groups.set(f.code, g)
  }
  for (const g of groups.values()) if (g.code === 'noindex') g.title += ` (${N(g.wheres.length, 'страница', 'страницы', 'страниц')})`
  const list = [...groups.values()].sort((a, b) => ORDER.indexOf(a.level) - ORDER.indexOf(b.level) || b.wheres.length - a.wheres.length)

  const line = '─'.repeat(76)
  const kb = (n) => `${(n / 1024).toFixed(0)} КБ`
  const arr = [...pages.values()]
  const avg = (f) => (arr.length ? Math.round(arr.reduce((s, p) => s + f(p), 0) / arr.length) : 0)

  console.log(`\n${line}\n  Аудит ${ORIGIN} для поисковых систем и ИИ-помощников\n  ${new Date().toLocaleString('ru-RU', { dateStyle: 'long' })}\n${line}\n`)
  console.log(`  Обойдено страниц:      ${pages.size}${pages.size >= LIMIT ? ` (упёрлось в --limit ${LIMIT})` : ''}`)
  console.log(`  Средний вес HTML:      ${kb(avg((p) => p.res.bytes))}`)
  console.log(`  Среднее время ответа:  ${avg((p) => p.res.ms)} мс`)
  console.log(`  Средний объём текста:  ${N(avg((p) => p.words), "слово", "слова", "слов")}`)
  const closed = arr.filter((p) => p.noindex).length
  if (closed) console.log(`  Закрыто от индексации: ${closed}`)

  for (const level of ORDER) {
    const part = list.filter((f) => f.level === level)
    if (!part.length) continue
    console.log(`\n${line}\n  ${level.toUpperCase()} — ${part.length}\n${line}`)
    part.forEach((f, i) => {
      console.log(`\n${String(i + 1).padStart(3)}. ${f.title}`)
      const show = f.wheres.slice(0, 6)
      for (const w of show) console.log(`     · ${w}`)
      if (f.wheres.length > show.length) console.log(`     · … и ещё ${f.wheres.length - show.length}`)
      if (f.hint) console.log(`     → ${f.hint}`)
    })
  }

  console.log(`\n${line}\n  ЧЕГО ЭТА ПРОВЕРКА НЕ ВИДИТ\n${line}
  Обход снаружи отвечает на вопрос «что мешает роботу», но не на вопрос
  «почему сайт проигрывает соседям». Руками проверяются:

  · Яндекс.Вебмастер — страницы, исключённые из поиска, и причина по каждой;
    запросы, по которым сайт показывают, и место в выдаче.
  · Регион сайта в Вебмастере. Для организации, работающей по городу, это
    решает больше, чем половина пунктов выше.
  · Карточка организации в Яндекс.Бизнесе и на картах — отзывы, часы, фото.
  · Скорость на настоящем канале: PageSpeed Insights и «Скорость сайта»
    в Метрике. Время ответа сервера отсюда — только первая треть картины.
  · Тексты: отвечают ли они на запрос, которым их ищут, и не переписаны ли
    у соседа. Робот считает слова, а не смысл.
  · Ссылки с чужих сайтов и упоминания названия — их отсюда не видно вовсе.\n`)

  const crit = list.filter((f) => f.level === CRIT).length
  const high = list.filter((f) => f.level === HIGH).length
  console.log(`${line}\n  Итого: критично — ${crit}, важно — ${high}, замечаний — ${list.filter((f) => f.level === NOTE).length}\n${line}\n`)

  const out = flag('json', null)
  if (out) {
    writeFileSync(out, JSON.stringify({
      origin: ORIGIN,
      checkedAt: new Date().toISOString(),
      pages: arr.map((p) => ({
        url: p.url, status: p.res.status, ms: p.res.ms, bytes: p.res.bytes, words: p.words,
        title: p.title, description: p.meta.description ?? null,
        h1: p.headings.filter((h) => h.level === 1).map((h) => h.text),
        canonical: (p.links.canonical ?? [])[0] ?? null, noindex: !!p.noindex, depth: p.depth,
        schema: [...(p.schemaTypes ?? [])],
      })),
      findings: list,
    }, null, 2))
    console.log(`  Машинный отчёт: ${out}\n`)
  }
  return crit
}

// ── Запуск ────────────────────────────────────────────────────────────────

if (!QUIET) console.error(`Обход ${ORIGIN} (до ${LIMIT} страниц, ${CONCURRENCY} запроса разом)…`)
await loadRobots()
await crawl()
for (const p of pages.values()) checkPage(p)
await checkSite()
const critical = report()
process.exit(critical > 0 ? 1 : 0)
