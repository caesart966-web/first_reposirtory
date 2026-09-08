// Микроразметка Schema.org для Яндекса и Google.
//
// Поисковик читает страницу как текст и не знает, что «6164132279» — это ИНН,
// а «+7 900 133-02-19» — телефон компании, а не случайное число в тексте.
// Микроразметка называет это прямо, и по ней собирается карточка организации
// в поиске и хлебные крошки под ссылкой.
//
// Разметка пишется в статический HTML, а не выводится из React: Яндекс
// выполняет скрипты не всегда, и разметка, появляющаяся только после запуска
// приложения, для него может не существовать вовсе.
//
// Данные берутся из тех же файлов, что и сам сайт (contacts.ts, facts.ts,
// regions.ts, заголовки страниц), второго источника правды нет. Набор
// jsonld.mjs сверяет разметку с тем, что реально отрисовано на странице:
// разойтись молча они не смогут.
//
// Тип Organization, а не LocalBusiness: LocalBusiness означает место, куда
// приходят клиенты, а сайт прямо говорит «дистанционно, личный визит
// не требуется». Заявлять приём посетителей мы не будем.
//
// Запуск: node scripts/build-jsonld.mjs
import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const ORIGIN = 'https://example.com'
const read = (p) => readFileSync(resolve(root, p), 'utf8')
const one = (src, re, what) => {
  const m = src.match(re)
  if (!m) throw new Error(`не нашёл в исходниках: ${what}`)
  return m[1]
}

const contacts = read('src/content/contacts.ts')
const facts = read('src/content/facts.ts')
const regionsSrc = read('src/content/regions.ts')

const brand = one(contacts, /brand: '([^']+)'/, 'brand')
const phone = one(contacts, /phone: '([^']+)'/, 'phone')
const email = one(contacts, /email: '([^']+)'/, 'email')
const messengers = ['whatsapp', 'telegram', 'max']
  .map((k) => contacts.match(new RegExp(`${k}: '(https://[^']+)'`))?.[1])
  .filter(Boolean)
const legalName = one(facts, /legalName: '([^']+)'/, 'legalName')
const inn = one(facts, /inn: '([^']+)'/, 'inn')
const address = one(facts, /address:\s*'([^']+)'/, 'address')
// Список регионов — тот же, что в блоке «География работы» на странице.
const regions = [...regionsSrc.matchAll(/name: '([^']+)', point:/g)].map((m) => m[1])
if (regions.length === 0) throw new Error('не нашёл список регионов')

// «Ростовская область, г. Ростов-на-Дону, ул. Социалистическая, зд. 74, офис 406/19»
const [addrRegion, addrCity, ...addrStreet] = address.split(', ')

const organization = {
  '@type': 'Organization',
  '@id': `${ORIGIN}/#organization`,
  name: brand,
  legalName,
  url: `${ORIGIN}/`,
  logo: `${ORIGIN}/apple-touch-icon.png`,
  image: `${ORIGIN}/og.png`,
  description:
    'Вступление в СРО строителей, проектировщиков и изыскателей: подбор ' +
    'саморегулируемой организации, подготовка документов, специалисты НРС ' +
    'и независимая оценка квалификации, сопровождение до внесения в реестр членов.',
  telephone: phone,
  email,
  taxID: inn,
  address: {
    '@type': 'PostalAddress',
    addressCountry: 'RU',
    addressRegion: addrRegion,
    addressLocality: addrCity.replace(/^г\.\s*/, ''),
    streetAddress: addrStreet.join(', '),
  },
  areaServed: regions.map((name) => ({ '@type': 'AdministrativeArea', name })),
  ...(messengers.length ? { sameAs: messengers } : {}),
}

/** Все страницы сайта: каждая — отдельный index.html со своей точкой входа. */
const SKIP = new Set(['node_modules', 'dist', 'public', 'src', 'scripts', 'assets-src', '.git'])
function pages(dir = root, prefix = '') {
  const out = []
  for (const entry of readdirSync(dir)) {
    if (SKIP.has(entry) || entry.startsWith('.')) continue
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) out.push(...pages(full, `${prefix}${entry}/`))
    else if (entry === 'index.html') out.push({ path: full, url: prefix })
  }
  return out
}

// Раздел, в который вложена страница. Оба раздела — секции главной, своих
// адресов у них нет, поэтому в крошках стоят якоря.
const SECTION = {
  'sro-': { name: 'Виды СРО', url: `${ORIGIN}/#types` },
  uslugi: { name: 'Услуги', url: `${ORIGIN}/#services` },
}

const MARK = '<!-- Микроразметка Schema.org, собрана scripts/build-jsonld.mjs -->'
const BLOCK = /[ \t]*<!-- Микроразметка Schema\.org[\s\S]*?<\/script>\n/

let written = 0
for (const page of pages()) {
  const src = readFileSync(page.path, 'utf8')
  const graph = [organization]

  if (page.url) {
    // Название страницы берём из её же <title>, чтобы крошка не разошлась
    // с тем, что видит человек во вкладке.
    const title = one(src, /<title>([^<]+)<\/title>/, `title в ${page.url}`)
    const short = title.replace(new RegExp(`\\s*—\\s*${legalName}$`), '').trim()
    const section = SECTION[page.url.startsWith('uslugi/') ? 'uslugi' : 'sro-']
    graph.push({
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Главная', item: `${ORIGIN}/` },
        { '@type': 'ListItem', position: 2, name: section.name, item: section.url },
        { '@type': 'ListItem', position: 3, name: short, item: `${ORIGIN}/${page.url}` },
      ],
    })
  }

  const json = JSON.stringify({ '@context': 'https://schema.org', '@graph': graph }, null, 2)
    .split('\n')
    .map((line, i) => (i === 0 ? line : '      ' + line))
    .join('\n')
  const block = `    ${MARK}\n    <script type="application/ld+json">\n      ${json}\n    </script>\n`

  let out = BLOCK.test(src) ? src.replace(BLOCK, block) : src.replace(/([ \t]*<\/head>)/, `${block}$1`)
  if (out !== src) {
    writeFileSync(page.path, out)
    written += 1
  }
}
console.log(`микроразметка записана в ${written} страниц; регионов в areaServed: ${regions.length}`)
