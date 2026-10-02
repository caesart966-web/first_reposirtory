#!/usr/bin/env node
// Сборка брендбуков.
//
//   node brandbooks/build.mjs                 — собрать brandbooks/*.html
//   node brandbooks/build.mjs --fragments DIR — то же плюс страницы без
//                                               <head> для публикации артефактом
//
// Исходники — brandbooks/src/*.html. Сборка делает две вещи.
//
// 1. Подставляет фотографии. В исходнике стоит {{img:путь от корня репозитория}},
//    в готовый файл кадр уходит data URI: брендбук — один файл, его можно
//    переслать или открыть без папки с картинками.
//
// 2. Сверяет брендбук с сайтом. Знак, цвета и контакты в брендбуке нарисованы
//    и написаны руками, а живут они в исходниках сайтов. Положенный однажды
//    в папку брендбук разойдётся с сайтом при первой правке телефона или
//    оттенка, и заметить это будет некому. Поэтому каждый контур знака, каждый
//    код цвета и каждый контакт читается из исходника сайта и ищется
//    в готовом брендбуке; не нашёлся — сборка падает и называет, что и где.

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { dirname, join, resolve, extname } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, '..')
const read = (p) => readFileSync(join(ROOT, p), 'utf8')

const MIME = { '.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.avif': 'image/avif', '.svg': 'image/svg+xml' }

// Все значения d="…" из куска разметки.
const paths = (src) => [...src.matchAll(/\bd="([^"]+)"/g)].map((m) => m[1])

// Значения CSS-переменных вида --имя: #HEX из блока :root.
function cssVars(css, names) {
  const out = {}
  for (const n of names) {
    const m = css.match(new RegExp(`--${n}:\\s*(#[0-9a-fA-F]{6})\\b`))
    if (!m) throw new Error(`в стилях сайта нет переменной --${n}`)
    out[n] = m[1]
  }
  return out
}

// Строковое поле из TS/JS-конфига: имя: 'значение'.
function field(src, name, file) {
  const m = src.match(new RegExp(`\\b${name}:\\s*'([^']+)'`))
  if (!m) throw new Error(`в ${file} нет поля ${name}`)
  return m[1]
}

const BOOKS = [
  {
    id: 'norma',
    checks() {
      const logo = read('norma-site/src/components/LogoMark.astro')
      const css = read('norma-site/src/styles/global.css')
      const site = read('norma-site/src/config/site.ts')
      const f = (n) => field(site, n, 'norma-site/src/config/site.ts')
      const colors = cssVars(css, ['paper-2', 'ink', 'muted', 'line', 'dark', 'dark-2', 'on-dark', 'on-dark-muted', 'acc', 'acc-deep', 'acc-soft', 'acc-bright', 'good', 'good-bright', 'good-bg'])
      return [
        ...paths(logo).map((d) => ['контур знака из LogoMark.astro', d]),
        ...Object.entries(colors).map(([n, v]) => [`цвет --${n} из global.css`, v]),
        ['дата печати SITE.checkedDate', f('checkedDate')],
        ['телефон SITE.phone', f('phone')],
        ['почта SITE.email', f('email')],
        ['ИНН SITE.inn', f('inn')],
        ['ОГРНИП SITE.ogrnip', f('ogrnip')],
        ['владелец SITE.legalName', f('legalName')],
        ['подпись SITE.brandTag', f('brandTag')],
      ]
    },
  },
  {
    id: 'biznes-grupp',
    checks() {
      const ill = read('sro-site/src/components/illustrations.tsx')
      const mark = ill.slice(ill.indexOf('export function ScalesMark'), ill.indexOf('</svg>', ill.indexOf('export function ScalesMark')))
      if (!mark) throw new Error('в illustrations.tsx нет ScalesMark')
      const tw = read('sro-site/tailwind.config.js')
      const hexes = [...tw.slice(tw.indexOf('accent:'), tw.indexOf('fontFamily')).matchAll(/(\d{2,3}):\s*'(#[0-9A-Fa-f]{6})'/g)]
      if (hexes.length < 20) throw new Error('в tailwind.config.js не нашлись шкалы accent и neutral')
      const contacts = read('sro-site/src/content/contacts.ts')
      const f = (n) => field(contacts, n, 'sro-site/src/content/contacts.ts')
      return [
        ...paths(mark).map((d) => ['контур знака ScalesMark', d]),
        ...hexes.map((m) => [`цвет ${m[1]} из tailwind.config.js`, m[2]]),
        ['название CONTACTS.brand', f('brand')],
        ['телефон CONTACTS.phone', f('phone')],
        ['почта CONTACTS.email', f('email')],
      ]
    },
  },
  {
    id: 'x-pto',
    checks() {
      const logo = read('pto-site/assets/img/logo.svg')
      const css = read('pto-site/assets/style.css')
      const site = JSON.parse(read('pto-site/data/site.json'))
      const colors = cssVars(css, ['navy', 'navy-900', 'navy-800', 'navy-600', 'accent', 'accent-700', 'accent-300', 'accent-050', 'bg', 'surface-alt', 'line', 'line-strong', 'ink-muted', 'ink-soft', 'ink-inverse-muted', 'ok'])
      return [
        ...paths(logo).map((d) => ['контур знака из assets/img/logo.svg', d]),
        ...Object.entries(colors).map(([n, v]) => [`цвет --${n} из style.css`, v]),
        ['название company.name', site.company.name],
        ['подпись company.tagline', site.company.tagline],
        ['ИНН company.inn', site.company.inn],
        ['ОГРНИП company.ogrnip', site.company.ogrnip],
        ['телефон contacts.phone_display', site.contacts.phone_display],
        ['почта contacts.email', site.contacts.email],
        ['Telegram contacts.telegram_display', site.contacts.telegram_display],
      ]
    },
  },
]

const norm = (s) => s.replace(/\s+/g, ' ').trim().toLowerCase()

const args = process.argv.slice(2)
const fragIdx = args.indexOf('--fragments')
const fragDir = fragIdx >= 0 ? resolve(args[fragIdx + 1] || '') : null
if (fragIdx >= 0 && !args[fragIdx + 1]) {
  console.error('--fragments: укажите папку')
  process.exit(2)
}

let failed = 0
for (const book of BOOKS) {
  const srcPath = join(HERE, 'src', `${book.id}.html`)
  if (!existsSync(srcPath)) {
    console.error(`✗ ${book.id}: нет исходника ${srcPath}`)
    failed++
    continue
  }
  let html = readFileSync(srcPath, 'utf8')

  html = html.replace(/\{\{img:([^}]+)\}\}/g, (_, rel) => {
    const file = join(ROOT, rel.trim())
    const mime = MIME[extname(file).toLowerCase()]
    if (!mime) throw new Error(`${book.id}: неизвестный тип картинки ${rel}`)
    return `data:${mime};base64,${readFileSync(file).toString('base64')}`
  })

  const hay = norm(html)
  const missing = book.checks().filter(([, needle]) => !hay.includes(norm(needle)))
  if (missing.length) {
    failed++
    console.error(`✗ ${book.id}: брендбук разошёлся с сайтом`)
    for (const [what, needle] of missing) console.error(`    ${what}: «${needle}» в брендбуке не найден`)
    continue
  }

  // Готовый файл: всё до первого </style> — в <head>, остальное — в <body>.
  const cut = html.indexOf('</style>') + '</style>'.length
  const page = [
    '<!doctype html>',
    '<html lang="ru">',
    '<head>',
    '<meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
    `<!-- Собрано brandbooks/build.mjs из brandbooks/src/${book.id}.html. Правьте исходник, не этот файл. -->`,
    html.slice(0, cut).trim(),
    '</head>',
    '<body>',
    html.slice(cut).trim(),
    '</body>',
    '</html>',
    '',
  ].join('\n')
  writeFileSync(join(HERE, `${book.id}.html`), page)

  if (fragDir) {
    mkdirSync(fragDir, { recursive: true })
    writeFileSync(join(fragDir, `${book.id}.html`), html)
  }
  console.log(`✓ ${book.id}: ${book.checks().length} сверок, ${(page.length / 1024).toFixed(0)} КБ`)
}

if (failed) process.exit(1)
