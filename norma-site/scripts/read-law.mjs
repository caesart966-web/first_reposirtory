// Читает текст нормы с правовых сайтов — для робота GitHub
// «НОРМА: прочитать текст закона».
//
// ЗАЧЕМ. Сайт стоит на том, что у каждого утверждения есть статья закона,
// а правовые базы (Консультант, Гарант, zakonrf, rulaws, pravo.gov.ru)
// из среды, где пишется сайт, закрыты сетевой политикой. Поэтому до
// 15.10.2026 сверка шла по выдержкам поиска, а они расходятся: размер
// штрафа по ст. 9.5.1 КоАП сайты по теме называют тремя разными (от 40 тыс.
// до 1 млн ₽). У GitHub доступ к этим сайтам есть — робот открывает
// страницу, вынимает текст и печатает его в журнал запуска; весь текст
// кладёт в Artifacts. Статья на сайт пишется по тексту закона, а не по
// пересказу.
//
// Робот только читает. Адреса — только с правовых и государственных сайтов
// (список ниже): робот не должен становиться открытым «скачай что угодно».
//
// Запуск: ADRESA="адрес адрес" ISKAT="фраза|фраза" node scripts/read-law.mjs
//   ADRESA — адреса страниц через пробел или с новой строки;
//   ISKAT  — необязательно: фразы через «|», вокруг каждой печатается окно
//            текста (OKNO знаков, по умолчанию 1500). Без фраз печатается
//            начало текста страницы.

import { mkdirSync, writeFileSync } from 'node:fs'

const HOSTS = [
  'consultant.ru', 'garant.ru', 'zakonrf.info', 'rulaws.ru', 'pravo.gov.ru',
  'cntd.ru', 'kodeks.systema.ru', 'legalacts.ru', 'ppt.ru', 'sudact.ru',
  'vsrf.ru', 'kad.arbitr.ru', 'minstroyrf.gov.ru', 'nostroy.ru', 'nopriz.ru',
  'normacs.info', 'gosnadzor.ru', 'fas.gov.ru', 'minfin.gov.ru', 'government.ru',
  'duma.gov.ru', 'sozd.duma.gov.ru', 'kremlin.ru',
]
const UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'

const urls = (process.env.ADRESA || process.argv.slice(2).join(' ')).split(/\s+/).filter(Boolean)
const phrases = (process.env.ISKAT || '').split('|').map((s) => s.trim()).filter(Boolean)
const WIN = Number(process.env.OKNO) || 1500

if (!urls.length) {
  console.error('✗ Нет адресов: впишите их в поле «adresa».')
  process.exit(1)
}

const allowed = (u) => {
  try {
    const h = new URL(u).hostname
    return new URL(u).protocol === 'https:' && HOSTS.some((d) => h === d || h.endsWith('.' + d))
  } catch {
    return false
  }
}

const ENT = { nbsp: ' ', laquo: '«', raquo: '»', mdash: '—', ndash: '–', quot: '"', amp: '&', lt: '<', gt: '>', sect: '§', hellip: '…' }
function toText(html) {
  return html
    .replace(/<(script|style|noscript|svg)\b[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<(br|\/p|\/div|\/li|\/h\d|\/tr|\/table|p|li|h\d|tr)\b[^>]*>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(+n))
    .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
    .replace(/&([a-z]+);/gi, (m, n) => ENT[n.toLowerCase()] ?? m)
    .replace(/[ \t ]+/g, ' ')
    .replace(/ *\n[ \n]*/g, '\n')
    .trim()
}

async function load(u) {
  const res = await fetch(u, { headers: { 'User-Agent': UA, 'Accept-Language': 'ru' }, redirect: 'follow' })
  const buf = Buffer.from(await res.arrayBuffer())
  // Кодировка: из заголовка, иначе из meta, иначе utf-8 (часть зеркал — windows-1251).
  let cs = res.headers.get('content-type')?.match(/charset=([\w-]+)/i)?.[1]
  if (!cs) cs = buf.toString('latin1').match(/<meta[^>]+charset=["']?([\w-]+)/i)?.[1]
  let html
  try {
    html = new TextDecoder(cs || 'utf-8').decode(buf)
  } catch {
    html = new TextDecoder('utf-8').decode(buf)
  }
  return { status: res.status, url: res.url, html }
}

mkdirSync('law-text', { recursive: true })
let ok = 0
for (const [i, u] of urls.entries()) {
  console.log(`\n══════ ${u}`)
  if (!allowed(u)) {
    console.log('✗ Не правовой и не государственный сайт — не открываю (список в scripts/read-law.mjs).')
    continue
  }
  let r
  try {
    r = await load(u)
  } catch (e) {
    console.log(`✗ Не открылся: ${e.message}`)
    continue
  }
  const title = r.html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]?.replace(/\s+/g, ' ').trim() ?? '—'
  const text = toText(r.html)
  console.log(`  ответ ${r.status}${r.url !== u ? ` · после переходов: ${r.url}` : ''}`)
  console.log(`  заголовок: ${title}`)
  console.log(`  текст: ${text.length} знаков`)
  writeFileSync(`law-text/${String(i + 1).padStart(2, '0')}.txt`, `${u}\n${title}\n\n${text}\n`)
  if (r.status !== 200 || text.length < 200) {
    console.log('✗ Страница пустая или с ошибкой — текста нормы в ней нет.')
    continue
  }
  ok++
  if (!phrases.length) {
    console.log(`\n${text.slice(0, 6000)}${text.length > 6000 ? '\n…(дальше — в Artifacts)' : ''}`)
    continue
  }
  const low = text.toLowerCase()
  for (const p of phrases) {
    let from = 0
    let n = 0
    for (;;) {
      const at = low.indexOf(p.toLowerCase(), from)
      if (at < 0 || n >= 3) break
      n++
      const a = Math.max(0, at - 200)
      console.log(`\n── «${p}» (${n}):\n${text.slice(a, at + WIN)}`)
      from = at + p.length
    }
    if (!n) console.log(`\n── «${p}»: на странице не найдено`)
  }
}

console.log(`\n${ok ? '✓' : '✗'} Прочитано страниц: ${ok} из ${urls.length}. Полные тексты — в Artifacts запуска (law-text).`)
process.exit(ok ? 0 : 1)
