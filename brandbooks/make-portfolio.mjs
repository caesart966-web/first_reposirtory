#!/usr/bin/env node
// Портфолио брендбуков для Kwork: node brandbooks/make-portfolio.mjs
//   → brandbooks/portfolio/<бренд>/00-oblozhka.jpg, 01-….jpg … , rolik.mp4
//
// Запускать после node brandbooks/build.mjs. Папка portfolio в git не идёт:
// это выгрузка, она пересобирается этой командой. Только картинки или только
// ролик: PORTFOLIO_ONLY=images | video.
//
// Картинки 1920×1280 — размер, который Kwork рекомендует для работ (3 : 2).
// Ролик 1920×1080: брендбук пролистывается сверху донизу, до 75 с и до 50 МБ —
// лимиты Kwork; скрипт проверяет оба и падает, если вышел за них.
//
// Контакты заказчиков на картинках и в ролике заменены нейтральными: телефоны
// и номера ИНН/ОГРНИП — нулями, почта, сайты и мессенджеры — словами, имена —
// «Имя Фамилия». Модерация Kwork правит или отклоняет работы с контактами
// и ссылками, а портфолио исполнителя — не место для телефона заказчика.
// После замены скрипт читает текст страницы: остался хоть один настоящий
// контакт — картинки не пишутся.

import { mkdirSync, mkdtempSync, writeFileSync, statSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { execSync, spawn } from 'node:child_process'

const HERE = dirname(fileURLToPath(import.meta.url))
const OUT = join(HERE, 'portfolio')
const ONLY = process.env.PORTFOLIO_ONLY || ''

// ── Замена контактов ───────────────────────────────────────────────────────
// Порядок важен: сначала частные случаи, потом общие.
const MASK = [
  ['сайта (norma-sro|x-pto)\\.ru', 'gi', 'сайта заказчика'],
  ['\\s·\\sbiznesgrp\\.ru', 'gi', ''],
  ['X-PTO\\.RU', 'g', 'X-PTO'],
  ['\\+7[\\s(]*\\d{3}\\)?\\s*\\d{3}-\\d{2}-\\d{2}', 'g', '+7 000 000-00-00'],
  ['[\\w.-]+@[\\w-]+\\.(ru|рф|com)', 'gi', 'почта'],
  ['@[A-Za-z0-9_]{3,}', 'g', 'мессенджер'],
  ['(norma-sro|biznesgrp|x-pto)\\.ru', 'gi', 'сайт'],
  ['(ИНН|ОГРНИП)\\s\\d+', 'g', '$1 000000000000'],
  ['ИП Багишев Алихан Ахадович', 'g', 'ИП Фамилия Имя Отчество'],
  ['ИП Яковлев Андрей Эдуардович', 'g', 'ИП Фамилия Имя Отчество'],
  ['Алихан Багишев', 'g', 'Имя Фамилия'],
  ['ИП Багишев А\\. А\\.', 'g', 'ИП Фамилия И. О.'],
  ['А\\. Багишев', 'g', 'И. Фамилия'],
]
// Чего в готовой картинке быть не должно ни в каком виде.
const FORBIDDEN = ['931 969', '133-02-19', '685-13-77', '@mail.ru', 'norma-sro', 'biznesgrp', 'x-pto.ru', 'ptotver', 'Багишев', 'Яковлев', '470418675847', '326784700317132', '695014483664', '324690000060065', '9001330219']

// ── Оформление слайдов-подложек ────────────────────────────────────────────
const THEMES = {
  norma: {
    name: 'Брендбук «НОРМА»',
    fonts: 'family=Literata:ital,opsz,wght@0,7..72,400..800;1,7..72,400..700&family=Golos+Text:wght@400..700',
    css: `--bg:#EFEAE1;--fg:#16130F;--muted:#6B6459;--accent:#B0202B;--bar:#FFFFFF;--dot:#E5E0D5;--display:'Literata',Georgia,serif;--dw:700;--sans:'Golos Text',system-ui,sans-serif;--ls:-0.015em;`,
    deco: 'radial-gradient(70% 60% at 100% 0%, rgba(176,32,43,.10), transparent 60%), radial-gradient(60% 60% at 0% 100%, rgba(22,19,15,.06), transparent 70%)',
  },
  'biznes-grupp': {
    name: 'Брендбук ООО «БИЗНЕС-ГРУПП»',
    fonts: 'family=Brygada+1918:ital,wght@0,400..700;1,400..700&family=Onest:wght@300..700',
    css: `--bg:#1C1815;--fg:#F5F1EA;--muted:#A79D91;--accent:#C09A68;--bar:#26211D;--dot:#4D3A26;--display:'Brygada 1918',Georgia,serif;--dw:500;--sans:'Onest',system-ui,sans-serif;--ls:-0.02em;`,
    deco: 'radial-gradient(60% 70% at 85% 30%, rgba(192,154,104,.16), transparent 70%)',
  },
  'x-pto': {
    name: 'Брендбук X-PTO',
    fonts: 'family=Geologica:wght,SHRP@500..800,100&family=Inter:wght@400..700&family=JetBrains+Mono:wght@400..600',
    css: `--bg:#0d1c30;--fg:#FFFFFF;--muted:#b9c7d9;--accent:#7fb0ff;--bar:#142c48;--dot:#22415f;--display:'Geologica',Inter,sans-serif;--dw:800;--sans:'Inter',system-ui,sans-serif;--ls:-0.03em;`,
    deco: 'radial-gradient(60% 70% at 80% 35%, rgba(31,111,235,.28), transparent 70%), linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px) 0 0/56px 56px, linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px) 0 0/56px 56px',
  },
}

// ── Слайды ─────────────────────────────────────────────────────────────────
// crop    — кадр страницы 1440×960 с того места, где начинается раздел (+ сдвиг);
// device  — экран компьютера и телефон с одним разделом; сдвиг пропускает
//           заголовок раздела, иначе он стоял бы на слайде трижды;
// phones  — три телефона;
// pages   — все разделы брендбука одним полотном.
const SLIDES = {
  norma: [
    { file: '01-znak', type: 'device', sel: '#znak', deskOffset: 100, mobOffset: 330, title: 'Знак', text: 'Монограмма «Н», в которой читается латинская N. Построение на сетке, охранное поле, цветовые версии.' },
    { file: '02-logotip', type: 'crop', sel: '#logotip', offset: 40 },
    { file: '03-cvet', type: 'crop', sel: '#cvet', offset: 60 },
    { file: '04-shrifty', type: 'crop', sel: '#shrifty', offset: 60 },
    { file: '05-grafika', type: 'crop', sel: '#grafika', offset: 60 },
    { file: '06-telefon', type: 'phones', shots: [['header.cover', 0], ['#cvet', 0], ['#nositeli', 0]], title: 'На телефоне', text: 'Брендбук читается с любого экрана: разделы перестраиваются в одну колонку.' },
    { file: '07-nositeli', type: 'crop', sel: '#nositeli', offset: 60 },
    { file: '08-vse-razdely', type: 'pages', title: 'Десять статей', text: 'Идея, знак, логотип, цвет, шрифты, графика, движение, фотография, голос и носители.' },
  ],
  'biznes-grupp': [
    { file: '01-znak', type: 'device', sel: '#znak', deskOffset: 390, mobOffset: 330, title: 'Весы под фронтоном', text: 'Фронтон — здание и стройка, весы — закон. Знак на сетке с отметками уровней.' },
    { file: '02-logotip', type: 'crop', sel: '#logotip', offset: 300 },
    { file: '03-cvet', type: 'crop', sel: '#cvet', offset: 60 },
    { file: '04-foto', type: 'crop', sel: '#foto', offset: 60 },
    { file: '05-teksty', type: 'crop', sel: '#teksty', offset: 0 },
    { file: '06-telefon', type: 'phones', shots: [['header.cover', 0], ['#foto', 0], ['#nositeli', 0]], title: 'На телефоне', text: 'Каждый раздел перестраивается в одну колонку.' },
    { file: '07-nositeli', type: 'crop', sel: '#nositeli', offset: 60 },
    { file: '08-vse-razdely', type: 'pages', title: 'Десять разделов', text: 'Основа, знак, логотип, цвет, шрифты, фотография, движение, элементы, тексты и носители.' },
  ],
  'x-pto': [
    { file: '01-znak', type: 'device', sel: '#znak', deskOffset: 250, mobOffset: 300, title: 'Знак', text: 'Монограмма из двух контурных штрихов на сетке 64 × 64. Акцентный луч — внизу слева.' },
    { file: '02-cvet', type: 'crop', sel: '#cvet', offset: -24 },
    { file: '03-shrifty', type: 'crop', sel: '#shrifty', offset: -24 },
    { file: '04-foto', type: 'crop', sel: '#foto', offset: -24 },
    { file: '05-temnaya-tema', type: 'device', sel: '#logotip', deskOffset: 230, mobOffset: 300, dark: true, title: 'Две темы', text: 'Как и сайт, брендбук работает в светлой и тёмной теме.' },
    { file: '06-telefon', type: 'phones', shots: [['header.cover', 0], ['#cvet', 0], ['#foto', 0]], title: 'На телефоне', text: 'Листы альбома перестраиваются в одну колонку, основная надпись — в две.' },
    { file: '07-nositeli', type: 'crop', sel: '#nositeli', offset: -24 },
    { file: '08-vse-listy', type: 'pages', title: 'Альбом из десяти листов', text: 'У каждого листа рамка и основная надпись, как в комплекте чертежей.' },
  ],
}

// ── Браузер ────────────────────────────────────────────────────────────────
async function loadPlaywright() {
  try {
    return await import('playwright')
  } catch {}
  try {
    const root = execSync('npm root -g', { encoding: 'utf8' }).trim()
    return await import(pathToFileURL(join(root, 'playwright', 'index.mjs')).href)
  } catch {}
  console.error('Нужен playwright: npm i -g playwright && npx playwright install chromium')
  process.exit(1)
}
const { chromium } = await loadPlaywright()
const browser = await chromium.launch()

async function routeFonts(ctx) {
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, async (route) => {
    const req = route.request()
    const res = await fetch(req.url(), { headers: { 'user-agent': req.headers()['user-agent'] } })
    await route.fulfill({
      status: res.status,
      body: Buffer.from(await res.arrayBuffer()),
      headers: { 'content-type': res.headers.get('content-type') || 'application/octet-stream', 'access-control-allow-origin': '*' },
    })
  })
}

// Страница брендбука: шрифты загружены, контакты заменены, подсказки скрыты.
async function openBook(id, { width, height, dpr = 1, dark = false }) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: dpr, colorScheme: dark ? 'dark' : 'light', reducedMotion: 'reduce' })
  await routeFonts(ctx)
  const page = await ctx.newPage()
  await page.goto(pathToFileURL(join(HERE, `${id}.html`)).href, { waitUntil: 'networkidle' })
  await page.evaluate(() => document.fonts.ready)
  await page.addStyleTag({ content: '.pdf-hide, .toast { display: none !important; } html { scroll-behavior: auto !important; } .cover { min-height: 960px; display: flex; flex-direction: column; } .cover-main { flex: 1; }' })
  const left = await page.evaluate(({ rules, forbidden }) => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
    const nodes = []
    while (walker.nextNode()) {
      const p = walker.currentNode.parentElement
      if (p && !p.closest('script, style')) nodes.push(walker.currentNode)
    }
    for (const n of nodes) {
      let t = n.nodeValue
      for (const [re, flags, rep] of rules) t = t.replace(new RegExp(re, flags), rep)
      if (t !== n.nodeValue) n.nodeValue = t
    }
    document.querySelectorAll('.cover-meta dt').forEach((dt) => {
      if (/Владелец|Сайт/.test(dt.textContent)) { dt.nextElementSibling?.remove(); dt.remove() }
    })
    const text = nodes.map((n) => n.nodeValue).join(' ').toLowerCase()
    return forbidden.filter((f) => text.includes(f.toLowerCase()))
  }, { rules: MASK, forbidden: FORBIDDEN })
  if (left.length) throw new Error(`${id}: после замены остались контакты: ${left.join(', ')}`)
  await page.waitForTimeout(300)
  return { ctx, page }
}

async function scrollTo(page, sel, offset, vh) {
  await page.evaluate(({ sel, offset, vh }) => {
    const el = document.querySelector(sel)
    if (!el) throw new Error(`нет элемента ${sel}`)
    const top = el.getBoundingClientRect().top + window.scrollY + offset
    window.scrollTo(0, Math.max(0, Math.min(top, document.documentElement.scrollHeight - vh)))
  }, { sel, offset, vh })
  await page.waitForTimeout(120)
}

// ── Подложка слайда ────────────────────────────────────────────────────────
function slideHTML(theme, slide, img) {
  const cap = `<div class="cap"><h1>${slide.title}</h1><p>${slide.text}</p></div><p class="brand">${theme.name}</p>`
  let body = ''
  if (slide.type === 'device') {
    body = `<div class="desk"><div class="bar"><i></i><i></i><i></i></div><img src="${img.desk}"></div>
      <div class="phone" style="left:470px;top:430px"><div class="scr"><img src="${img.mob}"></div></div>`
  } else if (slide.type === 'phones') {
    body = img.mobs.map((src, i) => `<div class="phone big" style="left:${560 + i * 440}px;top:${i === 1 ? 210 : 290}px"><div class="scr"><img src="${src}"></div></div>`).join('')
  } else if (slide.type === 'pages') {
    const cols = [[], [], [], [], [], []]
    img.pages.forEach((p, i) => cols[i % cols.length].push(p))
    // Повтор, чтобы колонки не кончались раньше полотна.
    body = `<div class="wall">${cols.map((c, ci) => `<div class="col" style="margin-top:${(ci % 2) * -260}px">${[...c, ...c].map((p) => `<img src="${p}">`).join('')}</div>`).join('')}</div><div class="shade"></div>`
  }
  return `<!doctype html><html lang="ru"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?${theme.fonts}&display=swap">
<style>
:root{${theme.css}}
*{box-sizing:border-box}
html,body{margin:0;width:1920px;height:1280px;overflow:hidden;background:var(--bg);color:var(--fg);font-family:var(--sans);-webkit-font-smoothing:antialiased}
.slide{position:relative;width:1920px;height:1280px;overflow:hidden;background:${theme.deco},var(--bg)}
.cap{position:absolute;left:112px;top:112px;width:340px;z-index:3}
.cap h1{margin:0 0 26px;font-family:var(--display);font-weight:var(--dw);font-variation-settings:"SHRP" 100;font-size:74px;line-height:1.02;letter-spacing:var(--ls);text-wrap:balance}
.cap p{margin:0;font-size:23px;line-height:1.5;color:var(--muted);text-wrap:pretty}
.brand{position:absolute;left:112px;bottom:92px;margin:0;font-size:17px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);z-index:3}
.brand::before{content:"";display:block;width:44px;height:2px;background:var(--accent);margin-bottom:18px}
.desk{position:absolute;right:112px;top:140px;width:1230px;border-radius:16px;overflow:hidden;background:var(--bar);box-shadow:0 2px 4px rgba(0,0,0,.08),0 50px 90px -40px rgba(0,0,0,.55)}
.desk .bar{height:40px;display:flex;gap:9px;align-items:center;padding:0 18px}
.desk .bar i{width:12px;height:12px;border-radius:50%;background:var(--dot)}
.desk img{display:block;width:100%}
.phone{position:absolute;width:330px;height:690px;border-radius:52px;background:#0b0b0c;padding:11px;box-shadow:0 0 0 2px rgba(255,255,255,.08) inset,0 60px 90px -40px rgba(0,0,0,.65);z-index:2}
.phone.big{width:380px;height:794px;border-radius:58px;padding:12px}
.scr{width:100%;height:100%;border-radius:42px;overflow:hidden;position:relative;background:#fff}
.phone.big .scr{border-radius:47px}
.scr img{display:block;width:100%}
.scr::before{content:"";position:absolute;top:11px;left:50%;width:100px;height:29px;margin-left:-50px;border-radius:15px;background:#0b0b0c;z-index:1}
.wall{position:absolute;left:520px;top:-240px;display:flex;gap:30px;transform:rotate(-8deg);transform-origin:0 0}
.col{display:flex;flex-direction:column;gap:30px;width:330px}
.col img{display:block;width:100%;border-radius:8px;box-shadow:0 30px 60px -30px rgba(0,0,0,.6)}
.shade{position:absolute;inset:0;background:linear-gradient(90deg,var(--bg) 0%,var(--bg) 30%,transparent 46%);z-index:1}
</style></head><body><div class="slide">${body}${cap}</div></body></html>`
}

async function renderSlide(html, dir, file) {
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1280 }, deviceScaleFactor: 1 })
  await routeFonts(ctx)
  const page = await ctx.newPage()
  const tmp = join(dir, `${file}.html`)
  writeFileSync(tmp, html)
  await page.goto(pathToFileURL(tmp).href, { waitUntil: 'networkidle' })
  await page.evaluate(() => document.fonts.ready)
  await page.evaluate(() => Promise.all([...document.images].map((i) => i.decode().catch(() => {}))))
  const buf = await page.screenshot({ type: 'jpeg', quality: 90 })
  await ctx.close()
  return buf
}

// ── Картинки одного брендбука ──────────────────────────────────────────────
async function makeImages(id) {
  const dir = join(OUT, id)
  mkdirSync(dir, { recursive: true })
  const tmp = mkdtempSync(join(tmpdir(), `portfolio-${id}-`))
  const theme = THEMES[id]
  const save = (name, buf) => {
    writeFileSync(join(dir, `${name}.jpg`), buf)
    const mb = statSync(join(dir, `${name}.jpg`)).size / 1048576
    if (mb > 10) throw new Error(`${id}/${name}.jpg: ${mb.toFixed(1)} МБ, Kwork принимает до 10`)
  }

  // Кадры страницы 1440×960 при плотности 4/3 — ровно 1920×1280.
  const crop = await openBook(id, { width: 1440, height: 960, dpr: 4 / 3 })
  await crop.page.evaluate(() => window.scrollTo(0, 0))
  save('00-oblozhka', await crop.page.screenshot({ type: 'jpeg', quality: 92 }))
  for (const s of SLIDES[id].filter((s) => s.type === 'crop')) {
    await scrollTo(crop.page, s.sel, s.offset || 0, 960)
    save(s.file, await crop.page.screenshot({ type: 'jpeg', quality: 92 }))
  }
  await crop.ctx.close()

  // Остальные слайды собираются из снимков.
  const desk = await openBook(id, { width: 1440, height: 900, dpr: 1.25 })
  const mob = await openBook(id, { width: 390, height: 844, dpr: 2 })
  const deskDark = SLIDES[id].some((s) => s.dark) ? await openBook(id, { width: 1440, height: 900, dpr: 1.25, dark: true }) : null
  const mobDark = deskDark ? await openBook(id, { width: 390, height: 844, dpr: 2, dark: true }) : null
  const shot = async (p, sel, offset, vh, name) => {
    await scrollTo(p, sel, offset, vh)
    const f = join(tmp, `${name}.png`)
    await p.screenshot({ path: f })
    return pathToFileURL(f).href
  }

  for (const s of SLIDES[id].filter((s) => s.type !== 'crop')) {
    const img = {}
    if (s.type === 'device') {
      img.desk = await shot((s.dark ? deskDark : desk).page, s.sel, s.deskOffset || 0, 900, `${s.file}-desk`)
      img.mob = await shot((s.dark ? mobDark : mob).page, s.sel, s.mobOffset || 0, 844, `${s.file}-mob`)
    } else if (s.type === 'phones') {
      img.mobs = []
      for (const [i, [sel, off]] of s.shots.entries()) img.mobs.push(await shot(mob.page, sel, off, 844, `${s.file}-${i}`))
    } else if (s.type === 'pages') {
      const thumb = await openBook(id, { width: 1440, height: 900, dpr: 0.5 })
      const els = await thumb.page.$$('body > header, body > nav, body > section, body > main > section, body > footer')
      img.pages = []
      for (const [i, el] of els.entries()) {
        const box = await el.boundingBox()
        if (!box || box.height < 300) continue
        const f = join(tmp, `${s.file}-${i}.png`)
        await el.screenshot({ path: f })
        img.pages.push(pathToFileURL(f).href)
      }
      await thumb.ctx.close()
    }
    save(s.file, await renderSlide(slideHTML(theme, s, img), tmp, s.file))
  }
  for (const b of [desk, mob, deskDark, mobDark]) if (b) await b.ctx.close()
  rmSync(tmp, { recursive: true, force: true })
  console.log(`✓ ${id}: ${SLIDES[id].length + 1} картинок 1920×1280`)
}

// ── Ролик ──────────────────────────────────────────────────────────────────
// Кадр за кадром: прокрутка на 14 px (420 px в секунду при 30 кадрах),
// снимок уходит прямо в ffmpeg. От скорости машины ролик не зависит.
async function makeVideo(id) {
  const FPS = 30
  const STEP = 14
  const { ctx, page } = await openBook(id, { width: 1440, height: 810, dpr: 4 / 3 })
  const total = await page.evaluate(() => document.documentElement.scrollHeight - innerHeight)
  const ys = [...Array(36).fill(0)]
  for (let y = 0; y < total; y += STEP) ys.push(y)
  ys.push(...Array(30).fill(total))
  const seconds = ys.length / FPS
  if (seconds > 75) throw new Error(`${id}: ролик ${seconds.toFixed(0)} с, Kwork принимает до 75`)

  const out = join(OUT, id, 'rolik.mp4')
  mkdirSync(dirname(out), { recursive: true })
  const ff = spawn(process.env.FFMPEG || 'ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] })
  const done = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error(`ffmpeg вышел с кодом ${c}`)))))
  for (const y of ys) {
    await page.evaluate((y) => window.scrollTo(0, y), y)
    const buf = await page.screenshot({ type: 'jpeg', quality: 90 })
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r))
  }
  ff.stdin.end()
  await done
  await ctx.close()
  const mb = statSync(out).size / 1048576
  if (mb > 50) throw new Error(`${id}: ролик ${mb.toFixed(0)} МБ, Kwork принимает до 50`)
  console.log(`✓ ${id}: ролик ${seconds.toFixed(0)} с, ${mb.toFixed(1)} МБ`)
}

let failed = 0
for (const id of Object.keys(SLIDES)) {
  try {
    if (ONLY !== 'video') await makeImages(id)
    if (ONLY !== 'images') await makeVideo(id)
  } catch (e) {
    console.error(`✗ ${e.message}`)
    failed++
  }
}
await browser.close()
if (failed) process.exit(1)
