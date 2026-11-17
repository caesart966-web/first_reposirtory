// Разведка реестров СРО — для робота GitHub «НОРМА: разведка реестра СРО».
//
// ЗАЧЕМ. Заказчик спросил про каталог всех СРО на сайте (17.11.2026).
// Каталог допустим только из государственного реестра и только если его
// можно обновлять роботом: СРО исключают, и устаревший список — неправда
// на сайте. Реестры (Ростехнадзор, НОСТРОЙ, НОПРИЗ) из среды, где пишется
// сайт, закрыты сетевой политикой, у GitHub — открыты. Робот открывает
// адреса и печатает в журнал, ЧТО они отдают: код ответа, тип, размер,
// заголовок, сколько на странице номеров вида СРО-С-…, какие адреса /api/
// упоминаются в разметке и в скриптах страницы, начало ответа.
//
// Робот только читает и ничего не публикует. Адреса — только с сайтов
// реестров (список HOSTS).
//
// Запуск: ADRESA="адрес адрес" [METOD=POST TELO='{"…":…}'] node scripts/probe-registry.mjs

const HOSTS = ['nostroy.ru', 'nopriz.ru', 'gosnadzor.ru', 'data.gov.ru']
const UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'

const urls = (process.env.ADRESA || process.argv.slice(2).join(' ')).split(/\s+/).filter(Boolean)
const method = (process.env.METOD || 'GET').toUpperCase()
const body = process.env.TELO || ''
const HEAD = Number(process.env.NACHALO) || 1500

const allowed = (u) => {
  try {
    const x = new URL(u)
    return x.protocol === 'https:' && HOSTS.some((d) => x.hostname === d || x.hostname.endsWith('.' + d))
  } catch {
    return false
  }
}

if (!urls.length) {
  console.error('✗ Нет адресов: впишите их в поле «adresa».')
  process.exit(1)
}

const get = async (u, opts = {}) => {
  const res = await fetch(u, {
    method: opts.method || 'GET',
    headers: {
      'User-Agent': UA,
      Accept: opts.accept || 'text/html,application/json;q=0.9,*/*;q=0.8',
      'Accept-Language': 'ru-RU,ru;q=0.9',
      ...(opts.body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: opts.body || undefined,
    redirect: 'follow',
    signal: AbortSignal.timeout(40000),
  })
  const buf = Buffer.from(await res.arrayBuffer())
  return { res, text: buf.toString('utf8'), size: buf.length }
}

const uniq = (a) => [...new Set(a)]
const apiPaths = (s) => uniq((s.match(/["'`](\/?api\/[A-Za-z0-9_\-/{}.:?=&]+)["'`]/g) || []).map((x) => x.slice(1, -1)))
const fullUrls = (s) => uniq((s.match(/https?:\/\/[A-Za-z0-9.-]+(?:nostroy|nopriz|gosnadzor)\.ru\/[A-Za-z0-9_\-/.?=&]*/g) || []))

const shape = (v, depth = 0) => {
  if (Array.isArray(v)) return `[${v.length}] ${v.length ? shape(v[0], depth + 1) : ''}`
  if (v && typeof v === 'object') {
    if (depth > 2) return '{…}'
    return '{ ' + Object.entries(v).slice(0, 25).map(([k, x]) => `${k}: ${shape(x, depth + 1)}`).join(', ') + ' }'
  }
  return typeof v === 'string' ? JSON.stringify(v.slice(0, 60)) : String(v)
}

let bad = 0
for (const u of urls) {
  console.log('\n' + '═'.repeat(78) + '\n' + method + ' ' + u)
  if (!allowed(u)) {
    console.log('✗ адрес не из списка сайтов реестров — пропущен')
    bad++
    continue
  }
  try {
    const { res, text, size } = await get(u, { method, body: method === 'POST' ? body : '' })
    const type = res.headers.get('content-type') || ''
    console.log(`код ${res.status} · ${type} · ${size} байт · итоговый адрес ${res.url}`)
    const reg = text.match(/СРО-[СПИ]-\d+-\d{8}/g) || []
    console.log(`номеров вида СРО-С/П/И-…: ${reg.length} (разных ${uniq(reg).length})`)
    if (/json/.test(type) || /^\s*[[{]/.test(text)) {
      try {
        console.log('JSON: ' + shape(JSON.parse(text)).slice(0, 3000))
      } catch {
        console.log('похоже на JSON, но не разбирается')
      }
    } else {
      const title = (text.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1]
      if (title) console.log('заголовок: ' + title.trim().replace(/\s+/g, ' '))
      // Скрипты страницы и подгружаемые куски (link rel=prefetch/preload):
      // у приложений-реестров адрес данных живёт в кусках, а не в разметке.
      const scripts = uniq([
        ...[...text.matchAll(/<script[^>]+src=["']([^"']+)["']/gi)].map((m) => m[1]),
        ...[...text.matchAll(/<link[^>]+href=["']([^"']+\.js)["']/gi)].map((m) => m[1]),
      ].map((x) => new URL(x, res.url).href))
      console.log(`скриптов: ${scripts.length}`)
      const inHtml = apiPaths(text)
      if (inHtml.length) console.log('адреса api в разметке: ' + inHtml.slice(0, 40).join('  '))
      const links = fullUrls(text)
      if (links.length) console.log('ссылки на реестры в разметке (до 40): ' + links.slice(0, 40).join('  '))
      const seen = new Set()
      for (const s of scripts.filter((s) => allowed(s) && !/vendors/.test(s)).slice(0, 25)) {
        try {
          const js = await get(s, { accept: '*/*' })
          // Строки, похожие на адрес данных: абсолютные адреса и пути
          // с api / sro / member / reestr / registry.
          const found = uniq([
            ...apiPaths(js.text),
            ...(js.text.match(/["'`](https?:\/\/[^"'`\s]{6,160})["'`]/g) || []).map((x) => x.slice(1, -1)),
            ...(js.text.match(/["'`](\/?[A-Za-z0-9_\-]*(?:api|sro|member|reestr|registry|export|xls|csv)[A-Za-z0-9_\-/{}.:?=&]*)["'`]/gi) || []).map((x) => x.slice(1, -1)),
          ]).filter((x) => x.length > 3 && !seen.has(x))
          found.forEach((x) => seen.add(x))
          console.log(`  скрипт ${s} — ${js.size} байт, новых адресов: ${found.length}`)
          if (found.length) console.log('    ' + found.slice(0, 80).join('  '))
        } catch (e) {
          console.log(`  скрипт ${s} — ошибка: ${e.message}`)
        }
      }
    }
    console.log('— начало ответа —\n' + text.slice(0, HEAD).replace(/\s+/g, ' '))
  } catch (e) {
    console.log('✗ ошибка: ' + e.message)
    bad++
  }
}
if (bad === urls.length) process.exit(1)
