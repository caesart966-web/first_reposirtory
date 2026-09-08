// Робот-наблюдатель: следит, не изменился ли закон под сайтом.
//
// ЧТО ОН ДЕЛАЕТ И ЧЕГО НЕ ДЕЛАЕТ.
//
// Делает: раз в неделю открывает страницы норм, на которых стоит сайт,
// снимает с каждой отпечаток (хэш значимого текста) и сравнивает
// с прошлым снимком в scripts/law-snapshot.json. Если отпечаток разошёлся —
// значит редакцию нормы правили, и это повод перечитать статью на сайте.
// Заодно смотрит, не появилось ли новых федеральных законов, вносящих
// изменения в Градостроительный кодекс.
//
// НЕ делает: не правит статьи, не двигает дату на печати, ничего не
// публикует. Причина не в лени, а в цене ошибки. Штамп «Сверено с законом»
// — обещание владельца сайта своим клиентам, и если его будет двигать
// скрипт, штамп перестанет означать сверку и станет означать «скрипт
// отработал». А автоматическая правка текста по различию в разметке —
// прямой путь однажды опубликовать неверный совет под видом проверенного.
// Поэтому робот только показывает пальцем; решение остаётся за человеком.
//
// Отдельно: молчание робота не считается успехом. Если источник не открылся,
// он так и пишет — «не смог проверить», и это не то же самое, что «ничего
// не изменилось».
//
// Запуск: node scripts/watch-law.mjs           — сравнить с прошлым снимком
//         node scripts/watch-law.mjs --update  — записать новый снимок
import { createHash } from 'crypto'
import { readFileSync, writeFileSync, existsSync } from 'fs'

const SNAP = 'scripts/law-snapshot.json'
const UPDATE = process.argv.includes('--update')

// Нормы, на которых стоит сайт. Ссылки ведут на общедоступные зеркала
// кодекса: официальный портал pravo.gov.ru отдаёт документ целиком одним
// файлом и для построчного слежения неудобен.
const SOURCES = [
  { id: 'grk-52', what: 'Ст. 52 ГрК — обязанность членства строителей, порог 10 млн, техзаказчик', urls: [
    'https://www.consultant.ru/document/cons_doc_LAW_51040/df32b8231cf067c4d4e864c717eb6b398358b504/',
    'https://www.zakonrf.info/gradostroitelniy-kodeks/52/',
    'https://rulaws.ru/Gradostroitelnyy-kodeks/Glava-6/Statya-52/',
  ] },
  { id: 'grk-47', what: 'Ст. 47 ГрК — инженерные изыскания', urls: [
    'https://www.zakonrf.info/gradostroitelniy-kodeks/47/',
    'https://rulaws.ru/Gradostroitelnyy-kodeks/Glava-6/Statya-47/',
  ] },
  { id: 'grk-48', what: 'Ст. 48 ГрК — архитектурно-строительное проектирование', urls: [
    'https://www.zakonrf.info/gradostroitelniy-kodeks/48/',
    'https://rulaws.ru/Gradostroitelnyy-kodeks/Glava-6/Statya-48/',
  ] },
  { id: 'grk-55-5', what: 'Ст. 55.5 ГрК — требования к членам, два специалиста НРС', urls: [
    'https://www.zakonrf.info/gradostroitelniy-kodeks/55.5/',
    'https://rulaws.ru/Gradostroitelnyy-kodeks/Glava-6.1/Statya-55.5/',
  ] },
  { id: 'grk-55-5-1', what: 'Ст. 55.5-1 ГрК — специалисты и национальный реестр', urls: [
    'https://www.zakonrf.info/gradostroitelniy-kodeks/55.5-1/',
    'https://rulaws.ru/Gradostroitelnyy-kodeks/Glava-6.1/Statya-55.5-1/',
  ] },
  { id: 'grk-55-6', what: 'Ст. 55.6 ГрК — приём в члены, региональный принцип, срок', urls: [
    'https://www.zakonrf.info/gradostroitelniy-kodeks/55.6/',
    'https://rulaws.ru/Gradostroitelnyy-kodeks/Glava-6.1/Statya-55.6/',
  ] },
  { id: 'grk-55-7', what: 'Ст. 55.7 ГрК — прекращение членства, невозврат взносов', urls: [
    'https://www.zakonrf.info/gradostroitelniy-kodeks/55.7/',
    'https://rulaws.ru/Gradostroitelnyy-kodeks/Glava-6.1/Statya-55.7/',
  ] },
  { id: 'grk-55-16', what: 'Ст. 55.16 ГрК — компенсационные фонды и уровни ответственности', urls: [
    'https://www.zakonrf.info/gradostroitelniy-kodeks/55.16/',
    'https://rulaws.ru/Gradostroitelnyy-kodeks/Glava-6.1/Statya-55.16/',
  ] },
  { id: 'grk-55-31', what: 'Ст. 55.31 ГрК — снос объектов', urls: [
    'https://www.zakonrf.info/gradostroitelniy-kodeks/55.31/',
    'https://rulaws.ru/Gradostroitelnyy-kodeks/Glava-6.4/Statya-55.31/',
  ] },
  // Отдельный источник и самый ценный: не текст статьи, а дата редакции
  // кодекса целиком. Именно она первой показывает, что вышел закон,
  // меняющий ГрК, — так проглядели 309-ФЗ, работавший полгода.
  { id: 'grk-edition', what: 'Дата действующей редакции Градостроительного кодекса', edition: true, urls: [
    'https://www.zakonrf.info/gradostroitelniy-kodeks/',
    'https://rulaws.ru/Gradostroitelnyy-kodeks/',
  ] },
]

// Значимый текст: снимаем разметку, скрипты и стили, схлопываем пробелы.
// Без этого отпечаток менялся бы от каждой перестановки баннера на чужом
// сайте, и робот кричал бы каждую неделю.
const meaningful = (html) =>
  html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&[a-z]+;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const fingerprint = (text) => createHash('sha256').update(text).digest('hex').slice(0, 16)

/** Самая поздняя дата вида «ред. от 28.12.2025» на странице. */
const editionDate = (text) => {
  const found = [...text.matchAll(/ред(?:акци[ий])?\.?\s*от\s*(\d{2})\.(\d{2})\.(\d{4})/gi)]
    .map((m) => `${m[3]}-${m[2]}-${m[1]}`)
  return found.length ? found.sort().at(-1) : null
}

const fetchText = async (url) => {
  const res = await fetch(url, {
    headers: { 'User-Agent': 'Mozilla/5.0 (compatible; norma-site law watcher)' },
    signal: AbortSignal.timeout(25000),
  })
  if (!res.ok) throw new Error(`ответ ${res.status}`)
  return await res.text()
}

const prev = existsSync(SNAP) ? JSON.parse(readFileSync(SNAP, 'utf8')) : { taken: null, sources: {} }
const now = { taken: new Date().toISOString().slice(0, 10), sources: {} }

const changed = []
const failed = []
const same = []

for (const src of SOURCES) {
  let ok = false
  const tried = []
  for (const url of src.urls) {
    try {
      const text = meaningful(await fetchText(url))
      // Слишком короткая страница — заглушка или капча, а не норма.
      if (text.length < 2000) throw new Error(`страница короткая (${text.length} знаков)`)

      // Отпечаток хранится ПО АДРЕСУ, а не по норме. У разных зеркал разное
      // обрамление страницы, и если на этой неделе ответило другое зеркало,
      // сравнение отпечатков между ними дало бы ложную тревогу.
      const key = `${src.id}@${url}`
      const value = src.edition
        ? { date: editionDate(text), len: text.length, what: src.what, url }
        : { fp: fingerprint(text), len: text.length, what: src.what, url }
      now.sources[key] = value

      const was = prev.sources[key]
      if (!was) same.push(`${src.what} — снимок по этому адресу сделан впервые`)
      else if (src.edition && was.date !== value.date) {
        changed.push({ ...src, url, note: `дата редакции: было ${was.date || 'не найдено'}, стало ${value.date || 'не найдено'}` })
      } else if (!src.edition && was.fp !== value.fp) {
        changed.push({ ...src, url, note: `текст правили: длина была ${was.len}, стала ${value.len} знаков` })
      } else same.push(src.what)

      ok = true
      break
    } catch (e) {
      tried.push(`${new URL(url).hostname} — ${e.message}`)
    }
  }
  if (!ok) {
    failed.push({ ...src, why: tried.join('; ') })
    // Прошлые отпечатки сохраняем: одна неудачная неделя не должна стирать
    // историю, иначе следующая сверка объявит «снимок сделан впервые».
    for (const [k, v] of Object.entries(prev.sources)) {
      if (k.startsWith(src.id + '@')) now.sources[k] = v
    }
  }
}

// Возраст печати. Штамп «Сверено с законом» с датой полугодовой давности
// работает против сайта сильнее, чем отсутствие штампа: он говорит
// «мы проверяли», и дата тут же говорит «давно».
const SEAL_MAX_DAYS = 90
let sealNote = null
try {
  const site = readFileSync('src/config/site.ts', 'utf8')
  const iso = site.match(/checkedDateISO:\s*'(\d{4}-\d{2}-\d{2})'/)?.[1]
  if (iso) {
    const days = Math.round((Date.now() - Date.parse(iso)) / 86400000)
    if (days > SEAL_MAX_DAYS) sealNote = `Дата на печати — ${iso}, это ${days} дней назад.`
  }
} catch {
  /* нет файла — не беда, это не основная работа робота */
}

const lines = []
lines.push(`Наблюдение за нормами, ${now.taken}`)
lines.push(`Прошлый снимок: ${prev.taken || 'не было'}`)
lines.push('')

if (changed.length) {
  lines.push('## ИЗМЕНИЛОСЬ — перечитать статьи на сайте')
  for (const c of changed) {
    lines.push(`- **${c.what}**`)
    lines.push(`  ${c.url}`)
    lines.push(`  ${c.note}`)
  }
  lines.push('')
  lines.push('Отпечаток меняется от любой правки текста нормы, включая техническую.')
  lines.push('Откройте страницу и сравните с тем, что написано на сайте. Если норма')
  lines.push('изменилась по существу — поправьте статью и поднимите дату в её шапке.')
  lines.push('')
}

if (failed.length) {
  lines.push('## НЕ СМОГ ПРОВЕРИТЬ')
  for (const f of failed) lines.push(`- ${f.what} — ${f.why}`)
  lines.push('')
  lines.push('Это не «всё в порядке». Источник мог закрыться от роботов или сменить')
  lines.push('адрес. Проверьте вручную или замените ссылку в scripts/watch-law.mjs.')
  lines.push('')
}

if (!changed.length && !failed.length) {
  lines.push('## Всё сошлось')
  lines.push(`Ни одна из ${SOURCES.length} норм за неделю не менялась.`)
  lines.push('')
}

if (sealNote) {
  lines.push('## Печать пора обновить')
  lines.push(sealNote)
  lines.push('')
  lines.push('Пройдите SVERKA.md и поднимите SITE.checkedDate. Робот эту дату')
  lines.push('не двигает: «Сверено с законом» — обещание человека.')
  lines.push('')
}

lines.push('---')
lines.push('Робот только смотрит. Он не правит статьи и не двигает дату на печати:')
lines.push('«Сверено с законом» — обещание человека, и ставить его должен человек.')

const report = lines.join('\n')
console.log(report)
if (process.env.GITHUB_OUTPUT) {
  const alarm = changed.length || failed.length || sealNote ? 1 : 0
  writeFileSync(
    process.env.GITHUB_OUTPUT,
    `changed=${changed.length}\nfailed=${failed.length}\nseal=${sealNote ? 1 : 0}\nalarm=${alarm}\n`,
    { flag: 'a' },
  )
}
writeFileSync('law-report.md', report)

if (UPDATE) {
  writeFileSync(SNAP, JSON.stringify(now, null, 2) + '\n')
  console.log(`\nСнимок обновлён: ${SNAP}`)
}
