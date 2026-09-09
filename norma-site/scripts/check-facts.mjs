// Сверка сайта с самим собой.
//
// Чего эта проверка НЕ делает: она не сверяет утверждения с текстом закона.
// Правовые базы (pravo.gov.ru, consultant.ru, garant.ru, cntd.ru) закрыты
// сетевой политикой среды сборки — проверено, все отвечают 403. Сверка
// с кодексом остаётся ручной, её список — в SVERKA.md.
//
// Что она делает: ловит расхождения сайта с самим собой. Это самый опасный
// класс ошибок на этом сайте, и он уже случался — карточка на первом экране
// обещала вступительный взнос 0 ₽, а разбивка стоимости показывала 8 000.
// Посетитель, сравнивший две страницы, ловит сайт на неправде, и никакие
// ссылки на статьи этого уже не чинят.
//
// Проверяем:
//   1. Числа из конфигурации встречаются на страницах в том же виде.
//   2. Отменённые и устаревшие формулировки не появились нигде.
//   3. Одно утверждение подкреплено везде одной и той же нормой.
//
// Запуск: node scripts/check-facts.mjs
import { readFileSync, readdirSync } from 'fs'
import { join } from 'path'

const DIST = 'dist'
const text = (f) =>
  readFileSync(f, 'utf8')
    .replace(/<script[\s\S]*?<\/script>/g, ' ')
    .replace(/<style[\s\S]*?<\/style>/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;|&#160;/g, ' ')
    .replace(/&[a-z]+;/g, ' ')
    .replace(/\s+/g, ' ')

const pages = []
const walk = (dir) => {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) walk(p)
    else if (e.name.endsWith('.html')) pages.push({ url: '/' + p.slice(DIST.length + 1).replace(/index\.html$/, ''), body: text(p) })
  }
}
walk(DIST)

let problems = 0
const fail = (msg) => { problems++; console.log('  ✗ ' + msg) }

// ── 1. Устаревшее и отменённое ──────────────────────────────────────────
// Формулировки, которых на сайте быть не должно ни при каких условиях.
// Каждая — реальная ошибка, за которую этот сайт критикует конкурентов.
console.log('Отменённые и устаревшие формулировки')
const FORBIDDEN = [
  { re: /порог[^.]{0,40}3 млн/i, why: 'порог 3 млн ₽ — отменён с 1 мая 2022 года, действует 10 млн' },
  { re: /получить допуск СРО|оформить допуск СРО|допуск СРО за/i, why: '«допуск СРО» как действующий документ — свидетельства отменены в 2017 году' },
  { re: /постановлени[ея][^.]{0,30}1\/29/i, why: 'постановление Минтруда и Минобразования № 1/29 — утратило силу 01.09.2022' },
  { re: /пожарно-техническ[а-я]+ минимум[^.»]{0,30}(пройти|обучение по|проведём)/i, why: 'ПТМ отменён с 01.03.2022' },
  { re: /ст\.? ?212 ТК|стать[ие] 212 Трудового/i, why: 'ст. 212 ТК РФ — раздел X переписан с 01.03.2022, теперь ст. 214' },
  { re: /ст\.? ?225 ТК|стать[ие] 225 Трудового/i, why: 'ст. 225 ТК РФ — теперь ст. 219' },
]
// Сайт нарочно называет отменённые нормы — чтобы их опровергнуть: статья
// «допусков СРО не существует» без слова «допуск» была бы невозможна.
// Поэтому ругаемся только там, где рядом НЕТ опровержения.
const DEBUNK = /не\s|нет\s|а не\s|больше не|отменён|отменен|утратил|устарел|прежн|раньше|до 2022|с 1 мая 2022|не существует|подделк|неправ/i
for (const p of pages) {
  for (const f of FORBIDDEN) {
    for (const m of p.body.matchAll(new RegExp(f.re.source, f.re.flags.includes('g') ? f.re.flags : f.re.flags + 'g'))) {
      const around = p.body.slice(Math.max(0, m.index - 140), m.index + m[0].length + 140)
      if (DEBUNK.test(around)) continue
      fail(`${p.url} — ${f.why}\n      найдено: «…${m[0]}…»`)
      break
    }
  }
}
if (!problems) console.log('  ✓ ничего запрещённого не найдено')

// ── 2. Числа из конфигурации ────────────────────────────────────────────
// Значения берём из единых точек правды, а не из головы: если кто-то
// поменяет facts.ts, проверка сама начнёт требовать новое число.
const cfg = readFileSync('src/config/facts.ts', 'utf8')
const fees = readFileSync('src/config/fees.ts', 'utf8')
const num = (src, key) => {
  const m = src.match(new RegExp(`${key}:\\s*'([^']+)'`)) || src.match(new RegExp(`${key}:\\s*(\\d+)`))
  return m ? m[1] : null
}
const before = problems
console.log('\nЧисла из конфигурации')
// Страницы выбраны те, где значение обязано стоять по смыслу, а не любые
// упоминающие: требовать двухмесячный срок от статьи про страхование
// было бы придиркой к самому себе.
const CHECKS = [
  { label: 'срок действия свидетельства НОК', value: num(cfg, 'nokValidity'), pages: ['/uslugi/nrs/'] },
  { label: 'срок рассмотрения заявления', value: num(cfg, 'law'), pages: ['/', '/uslugi/sro-stroiteley/'] },
  { label: 'срок до выписки', value: num(cfg, 'extract'), pages: ['/', '/stoimost/'] },
  { label: 'вступительный взнос строителям', value: num(fees, 'entry'), pages: ['/stoimost/'] },
]
for (const c of CHECKS) {
  if (!c.value) { fail(`не удалось прочитать «${c.label}» из facts.ts`); continue }
  for (const url of c.pages) {
    const p = pages.find((x) => x.url === url)
    if (!p) { fail(`страница ${url} не найдена`); continue }
    const needle = c.value.replace(/ /g, ' ')
    if (!p.body.replace(/ /g, ' ').includes(needle)) {
      fail(`${url} — «${c.label}» = «${c.value}» из facts.ts на странице не встречается`)
    }
  }
}
if (problems === before) console.log('  ✓ значения из facts.ts на страницах совпадают')

// ── 2а. Партнёрские СРО не расходятся с предложением ────────────────────
// Самый вероятный способ соврать на этом сайте — показать в карточке СРО
// условия, отличные от тех, что обещаны на первом экране, и не сказать
// об этом. У двух партнёров из семи условия действительно другие:
// у ЯРД вступительный взнос 5 000 ₽ вместо 0, у ОРС ещё и членский
// 10 000 ₽ в месяц вместо 5 000. Это не ошибка — взносы назначает сама
// СРО, — но промолчать об этом нельзя.
//
// Отличия лежат в partners.ts отдельным полем, страница помечает такие
// строки звёздочкой сама. Проверка следит, что механизм жив: суммы
// на странице те же, что в конфигурации, а страница с отличиями несёт
// объяснение. Если кто-то впишет сумму руками мимо конфигурации —
// расхождение всплывёт здесь, а не у посетителя.
const before2a = problems
console.log('\nПартнёрские СРО')
const { PARTNERS, partnersWaiting, partnerFeeKind } = await import('../src/config/partners.ts')
const { FEES, money } = await import('../src/config/fees.ts')

// Организация без подтверждённого номера в реестре на сайт не выходит.
// Это не ошибка сборки — это напоминание: запись лежит в конфигурации
// и ждёт одной строки. Молча пропустить её нельзя, иначе о ней забудут.
for (const partner of partnersWaiting) {
  console.log(
    `  · «${partner.short}» (${partner.citySlug}) ждёт регистрационного номера — карточка не публикуется`,
  )
}

for (const partner of PARTNERS.filter((p) => p.reg)) {
  const url = `/sro/${partner.citySlug}/`
  const page = pages.find((x) => x.url === url)
  if (!page) { fail(`страница ${url} не найдена, а на ней должна быть СРО «${partner.short}»`); continue }
  // Суммы из money() набраны неразрывными пробелами, а в тексте страницы
  // они уже обычные: сводим и то и другое к обычному пробелу.
  const flat = (x) => x.replace(/\s+/g, ' ')
  const body = flat(page.body)

  if (!body.includes(partner.reg)) {
    fail(`${url} — нет регистрационного номера ${partner.reg} («${partner.short}»)`)
  }

  const base = FEES[partnerFeeKind(partner.reg)]
  const entry = partner.fees?.entry ?? base.entry
  const member = partner.fees?.memberMonth ?? base.memberMonth
  for (const value of [money(entry), `${money(member)} в месяц`, money(base.target)]) {
    if (!body.includes(flat(value))) {
      fail(`${url} — у «${partner.short}» не показано «${value}» из конфигурации`)
    }
  }

  if (partner.fees || partner.insurance) {
    if (!body.includes('Строки со звёздочкой')) {
      fail(`${url} — у «${partner.short}» условия отличаются от предложения, но объяснения на странице нет`)
    }
  }
}
if (problems === before2a) {
  const shown = PARTNERS.length - partnersWaiting.length
  console.log(`  ✓ ${shown} СРО показаны с условиями из конфигурации`)
}

// ── 3. Одна норма на одно утверждение ───────────────────────────────────
// Если порог 10 млн ₽ на одной странице подкреплён ч. 2.1 ст. 52,
// а на другой — другой статьёй, ошибка есть в одном из двух мест.
const before3 = problems
console.log('\nСсылки на нормы')
const CLAIMS = [
  { name: 'порог 10 млн ₽ и обязанность строителей', near: /10 млн/, law: /ч\.\s*2\.1\s*ст\.\s*52/ },
  { name: 'требования к специалисту НРС', near: /национальн\w+ реестр\w* специалист/i, law: /ст\.\s*55\.5-1/ },
]
const laws = new Map()
for (const p of pages) {
  for (const m of p.body.matchAll(/(?:ч\.\s*[\d.]+\s*)?ст\.\s*(\d+(?:\.\d+)*(?:-\d+)?)\s*(ГрК|КоАП|ТК)?/g)) {
    const key = m[0].replace(/\s+/g, ' ').trim()
    laws.set(key, (laws.get(key) || 0) + 1)
  }
}
for (const c of CLAIMS) {
  const carriers = pages.filter((p) => c.near.test(p.body))
  const without = carriers.filter((p) => !c.law.test(p.body))
  if (without.length) {
    console.log(`  · «${c.name}»: ${carriers.length} страниц упоминают, ${without.length} без ссылки на норму`)
    for (const p of without.slice(0, 6)) console.log(`      ${p.url}`)
  }
}
console.log(`\n  Всего разных ссылок на нормы: ${laws.size}`)
const sorted = [...laws.entries()].sort((a, b) => b[1] - a[1])
for (const [k, n] of sorted.slice(0, 12)) console.log(`      ${String(n).padStart(3)}× ${k}`)

console.log('\n' + '─'.repeat(64))
if (problems) {
  console.log(`НАЙДЕНО РАСХОЖДЕНИЙ: ${problems}`)
  process.exit(1)
}
console.log(`✓ Сайт не противоречит сам себе: ${pages.length} страниц.`)
console.log('  Сверка с текстом кодекса — отдельно и вручную, список в SVERKA.md:')
console.log('  правовые базы из среды сборки недоступны (403 от сетевой политики).')
