// Поиск по сайту: разбор слов, морфология и подбор совпадений.
//
// Живёт отдельным файлом, потому что им пользуются двое: строка поиска
// в шапке и страница результатов. Индекс собирается после сборки
// (scripts/make-search-index.mjs) и содержит обычный текст страниц —
// разбор на слова идёт уже в браузере. Так у поиска одна реализация,
// а не две, которые однажды разойдутся.

// ── Морфология ────────────────────────────────────────────────────────────
//
// Без неё поиск бесполезен: «взносы» не находят по слову «взнос»,
// а половина запросов приходит именно в такой форме. Здесь стеммер
// Портера для русского (алгоритм Snowball) — он отрезает окончания
// и оставляет основу.
//
// Одного стеммера мало. «Вступить» он сводит к «вступ», а «вступление» —
// к «вступлен»: разные части речи дают разные основы, и точное сравнение
// их не сведёт. Поэтому совпадением считается ещё и общее начало основ
// не короче четырёх букв — см. same() ниже.

const VOWELS = 'аеиоуыэюя'
const isVowel = (c: string) => VOWELS.includes(c)

// Списки окончаний из описания алгоритма. Внутри каждого — от длинных
// к коротким: снимать нужно самое длинное подходящее.
const byLength = (a: string[]) => [...a].sort((x, y) => y.length - x.length)

const GERUND_AYA = byLength(['вшись', 'вши', 'в'])
const GERUND = byLength(['ившись', 'ывшись', 'ивши', 'ывши', 'ив', 'ыв'])
const ADJECTIVE = byLength([
  'ее', 'ие', 'ые', 'ое', 'ими', 'ыми', 'ей', 'ий', 'ый', 'ой', 'ем', 'им', 'ым', 'ом',
  'его', 'ого', 'ему', 'ому', 'их', 'ых', 'ую', 'юю', 'ая', 'яя', 'ою', 'ею',
])
const PARTICIPLE_AYA = byLength(['ем', 'нн', 'вш', 'ющ', 'щ'])
const PARTICIPLE = byLength(['ивш', 'ывш', 'ующ'])
const REFLEXIVE = byLength(['ся', 'сь'])
const VERB_AYA = byLength([
  'ла', 'на', 'ете', 'йте', 'ли', 'й', 'л', 'ем', 'н', 'ло', 'но', 'ет', 'ют', 'ны', 'ть', 'ешь', 'нно',
])
const VERB = byLength([
  'ила', 'ыла', 'ена', 'ейте', 'уйте', 'ите', 'или', 'ыли', 'ей', 'уй', 'ил', 'ыл', 'им', 'ым', 'ен',
  'ило', 'ыло', 'ено', 'ят', 'ует', 'уют', 'ит', 'ыт', 'ены', 'ить', 'ыть', 'ишь', 'ую', 'ю',
])
const NOUN = byLength([
  'а', 'ев', 'ов', 'ие', 'ье', 'е', 'иями', 'ями', 'ами', 'еи', 'ии', 'и', 'ией', 'ей', 'ой', 'ий', 'й',
  'иям', 'ям', 'ием', 'ем', 'ам', 'ом', 'о', 'у', 'ах', 'иях', 'ях', 'ы', 'ь', 'ию', 'ью', 'ю', 'ия', 'ья', 'я',
])
const DERIVATIONAL = byLength(['ост', 'ость'])
const SUPERLATIVE = byLength(['ейш', 'ейше'])

/** Границы областей слова, в которых алгоритму разрешено резать. */
const regions = (w: string) => {
  let rv = w.length
  for (let i = 0; i < w.length; i++) {
    if (isVowel(w[i])) {
      rv = i + 1
      break
    }
  }
  let r1 = w.length
  for (let i = 1; i < w.length; i++) {
    if (!isVowel(w[i]) && isVowel(w[i - 1])) {
      r1 = i + 1
      break
    }
  }
  let r2 = w.length
  for (let i = r1 + 1; i < w.length; i++) {
    if (!isVowel(w[i]) && isVowel(w[i - 1])) {
      r2 = i + 1
      break
    }
  }
  return { rv, r1, r2 }
}

export const stem = (raw: string): string => {
  const word = raw.toLowerCase().replace(/ё/g, 'е')
  // Латиница и цифры морфологии не имеют: «НОСТРОЙ», «СРО», «10».
  if (!/[а-я]/.test(word)) return word
  if (word.length < 4) return word

  const { rv, r2 } = regions(word)
  let s = word

  const endsInRV = (suffix: string) => s.length - suffix.length >= rv && s.endsWith(suffix)
  const cut = (list: string[], afterAYa: boolean) => {
    for (const suffix of list) {
      if (!endsInRV(suffix)) continue
      if (afterAYa) {
        const before = s[s.length - suffix.length - 1]
        if (before !== 'а' && before !== 'я') continue
      }
      s = s.slice(0, s.length - suffix.length)
      return true
    }
    return false
  }

  // Шаг 1. Деепричастие; иначе возвратная частица и затем прилагательное,
  // глагол или существительное — что найдётся первым.
  if (!cut(GERUND, false) && !cut(GERUND_AYA, true)) {
    cut(REFLEXIVE, false)
    const adjectival = () => {
      if (!cut(ADJECTIVE, false)) return false
      if (!cut(PARTICIPLE, false)) cut(PARTICIPLE_AYA, true)
      return true
    }
    adjectival() || cut(VERB_AYA, true) || cut(VERB, false) || cut(NOUN, false)
  }

  // Шаг 2. Конечное «и».
  if (endsInRV('и')) s = s.slice(0, -1)

  // Шаг 3. Словообразовательный суффикс — только в глубине слова.
  for (const suffix of DERIVATIONAL) {
    if (s.length - suffix.length >= r2 && s.endsWith(suffix)) {
      s = s.slice(0, s.length - suffix.length)
      break
    }
  }

  // Шаг 4. Удвоенное «н», превосходная степень, мягкий знак.
  if (s.endsWith('нн')) s = s.slice(0, -1)
  else if (cut(SUPERLATIVE, false) && s.endsWith('нн')) s = s.slice(0, -1)
  if (s.endsWith('ь')) s = s.slice(0, -1)

  return s
}

// Слова, которые есть в любом тексте и потому не сужают поиск.
const STOP = new Set([
  'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так',
  'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было',
  'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг',
  'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж',
  'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть',
  'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего',
  'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'кто', 'этот', 'того', 'потому', 'этого', 'какой',
  'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее', 'были', 'куда',
  'зачем', 'всех', 'никогда', 'можно', 'при', 'об', 'хоть', 'после', 'над', 'больше', 'тот',
  'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя',
  'впрочем', 'свою', 'этой', 'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им',
  'более', 'всегда', 'конечно', 'всю', 'между', 'это',
])

/** Текст → список основ. Пунктуация и стоп-слова отбрасываются. */
export const tokens = (text: string): string[] => {
  const out: string[] = []
  for (const word of text.toLowerCase().replace(/ё/g, 'е').split(/[^0-9a-zа-я]+/)) {
    if (!word || word.length < 2) continue
    if (STOP.has(word)) continue
    out.push(stem(word))
  }
  return out
}

/**
 * Две основы считаются одним словом, если совпали целиком или одна
 * начинает другую и общее начало не короче четырёх букв.
 *
 * Порог не случайный. Ниже четырёх «про» начинает совпадать с «проект»,
 * «проверка» и «промышленность» разом — поиск перестаёт отличать
 * что угодно от чего угодно.
 */
export const same = (query: string, target: string): boolean => {
  if (query === target) return true
  const short = query.length <= target.length ? query : target
  const long = short === query ? target : query
  return short.length >= 4 && long.startsWith(short)
}

export type Doc = {
  /** Адрес страницы */
  u: string
  /** Заголовок H1 */
  t: string
  /** Описание для поисковиков */
  d: string
  /** Заголовки разделов */
  h: string[]
  /** Текст страницы */
  b: string
}

export type Hit = {
  doc: Doc
  score: number
  /** Отрывок текста вокруг найденного слова, слова обёрнуты в <mark> */
  snippet: string
}

/**
 * Вес поля. Совпадение в заголовке значит больше, чем в тексте:
 * страница «Стоимость» по запросу «стоимость» должна стоять выше
 * статьи, где это слово встретилось в третьем абзаце.
 */
const WEIGHT = { title: 12, heading: 5, description: 4, body: 1 }

type Prepared = Doc & { _t: string[]; _h: string[]; _d: string[]; _b: string[] }

/** Разбор индекса на основы. Делается один раз, результат переиспользуется. */
export const prepare = (docs: Doc[]): Prepared[] =>
  docs.map((d) => ({
    ...d,
    _t: tokens(d.t),
    _h: tokens(d.h.join(' ')),
    _d: tokens(d.d),
    _b: tokens(d.b),
  }))

const escapeHtml = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

/** Отрывок вокруг первого совпадения, с подсветкой всех найденных слов. */
const makeSnippet = (text: string, queryStems: string[], length = 190): string => {
  const words = [...text.matchAll(/[0-9A-Za-zА-Яа-яЁё]+/g)]
  let at = -1
  for (const m of words) {
    const s = stem(m[0])
    if (queryStems.some((q) => same(q, s))) {
      at = m.index ?? 0
      break
    }
  }
  if (at < 0) at = 0

  let from = Math.max(0, at - Math.floor(length / 3))
  // Не режем посреди слова.
  if (from > 0) {
    const space = text.indexOf(' ', from)
    if (space > 0 && space - from < 25) from = space + 1
  }
  let to = Math.min(text.length, from + length)
  if (to < text.length) {
    const space = text.lastIndexOf(' ', to)
    if (space > from + length / 2) to = space
  }

  const piece = escapeHtml(text.slice(from, to))
  const marked = piece.replace(/[0-9A-Za-zА-Яа-яЁё]+/g, (w) =>
    queryStems.some((q) => same(q, stem(w))) ? `<mark>${w}</mark>` : w,
  )
  return (from > 0 ? '…' : '') + marked + (to < text.length ? '…' : '')
}

/**
 * Поиск. Страница попадает в ответ, только если найдены ВСЕ слова запроса:
 * запрос из двух слов — это уточнение, а не расширение.
 *
 * Считается по правилам BM25, и это не украшательство — без двух его
 * поправок поиск на этом сайте выдавал заведомо неверный порядок.
 *
 * Поправка первая: РЕДКОСТЬ СЛОВА. Слово «СРО» стоит на всех сорока
 * четырёх страницах и потому не различает ничего; «субподряд» — различает
 * всё. Без неё по запросу «допуск СРО» первой шла оглавительная страница
 * базы знаний, а статья «допусков СРО не существует» не попадала и в тройку.
 *
 * Поправка вторая: ДЛИНА СТРАНИЦЫ. Главная и оглавления длинные и говорят
 * понемногу обо всём, поэтому набирали больше совпадений, чем страница,
 * посвящённая именно запросу. Без неё по запросу «документы для вступления»
 * первой шла главная, а страница «Документы» — второй.
 *
 * Плюс насыщение: второе вхождение слова весит меньше первого, десятое —
 * почти ничего. Иначе страницу можно было бы поднять простым повтором.
 */
const K = 1.6

export const search = (docs: Prepared[], query: string, limit = 30): Hit[] => {
  const q = [...new Set(tokens(query))]
  if (q.length === 0 || docs.length === 0) return []

  const avg = docs.reduce((sum, d) => sum + d._b.length, 0) / docs.length || 1

  // Сколько раз слово встретилось в поле. Совпадение по общему началу
  // («вступить» → «вступление») считается за половину точного.
  const freq = (list: string[], term: string) => {
    let n = 0
    for (const s of list) {
      if (s === term) n += 1
      else if (same(term, s)) n += 0.5
    }
    return n
  }

  const stats = docs.map((doc) =>
    q.map((term) => ({
      t: freq(doc._t, term),
      h: freq(doc._h, term),
      d: freq(doc._d, term),
      b: freq(doc._b, term),
    })),
  )

  const idf = q.map((_, i) => {
    const df = stats.filter((s) => s[i].t + s[i].h + s[i].d + s[i].b > 0).length
    return Math.log(1 + (docs.length - df + 0.5) / (df + 0.5))
  })

  const hits: Hit[] = []
  docs.forEach((doc, di) => {
    let score = 0
    for (let i = 0; i < q.length; i++) {
      const s = stats[di][i]
      if (s.t + s.h + s.d + s.b === 0) return
      const norm = 0.3 + 0.7 * (doc._b.length / avg)
      const sat = (n: number, weight: number, ln: number) =>
        n === 0 ? 0 : (weight * n * (K + 1)) / (n + K * ln)
      score +=
        idf[i] *
        (sat(s.t, WEIGHT.title, 1) +
          sat(s.h, WEIGHT.heading, 1) +
          sat(s.d, WEIGHT.description, 1) +
          sat(s.b, WEIGHT.body, norm))
    }
    hits.push({ doc, score, snippet: makeSnippet(doc.b, q) })
  })

  return hits.sort((a, b) => b.score - a.score).slice(0, limit)
}

// ── Показ результатов ─────────────────────────────────────────────────────
//
// Разметку строит общая функция: результаты показываются в двух местах —
// в строке поиска в шапке и на странице результатов. Разойдись они,
// одно и то же слово подсвечивалось бы в одном месте и не подсвечивалось
// в другом.

const SECTIONS: [RegExp, string][] = [
  [/^\/$/, 'Главная'],
  [/^\/uslugi\/./, 'Услуги'],
  [/^\/uslugi\/$/, 'Услуги'],
  [/^\/baza-znaniy\/./, 'База знаний'],
  [/^\/baza-znaniy\/$/, 'База знаний'],
]

/** Название раздела для строки под заголовком результата. */
export const sectionOf = (url: string): string => {
  for (const [re, label] of SECTIONS) if (re.test(url)) return label
  return ''
}

/** Список найденного разметкой. base — подпапка, в которой живёт сайт. */
export const hitsHtml = (hits: Hit[], base: string): string => {
  const prefix = base.replace(/\/$/, '')
  return hits
    .map((h) => {
      const section = sectionOf(h.doc.u)
      return (
        `<a class="s-hit" href="${prefix}${h.doc.u}">` +
        (section ? `<span class="s-sec">${escapeHtml(section)}</span>` : '') +
        `<span class="s-title">${escapeHtml(h.doc.t)}</span>` +
        `<span class="s-snip">${h.snippet}</span>` +
        `</a>`
      )
    })
    .join('')
}

/** Склонение числа найденного: 1 страница, 2 страницы, 5 страниц. */
export const foundLabel = (n: number): string => {
  const ten = n % 100
  const one = n % 10
  if (ten >= 11 && ten <= 14) return `${n} страниц`
  if (one === 1) return `${n} страница`
  if (one >= 2 && one <= 4) return `${n} страницы`
  return `${n} страниц`
}
