// Собирает картинку-превью (og-image) для мессенджеров и соцсетей.
// Рисуется в браузере из HTML и сохраняется в public/og.png — 1200×630.
//
// Запуск (после npm install):  node scripts/make-og.mjs
// Повторять нужно, только если поменялись название, телефон или оформление.

import { chromium } from 'playwright'
import { writeFile, readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const out = resolve(here, '../public/og.png')

// Данные берём из того же конфига, что и сайт, — чтобы картинка не разошлась с текстом.
const site = await import(resolve(here, '../src/config/site.ts')).catch(() => null)
const PHONE = site?.SITE?.phone ?? '+7 931 969-86-64'

// Фирменный знак берём из того же файла, что и сайт, — чтобы картинка-превью
// не разошлась с логотипом в шапке.
const markFile = await readFile(resolve(here, '../src/components/LogoMark.astro'), 'utf8')
const MARK = markFile.slice(markFile.indexOf('<svg'), markFile.lastIndexOf('</svg>') + 6)
  .replace(/height=\{[^}]+\}/, 'height="58"')
  .replace(/width=\{[^}]+\}/, 'width="58"')
  .replace(/class=\{[^}]+\}/, '')

const html = `<!doctype html>
<html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Onest:wght@500;800&family=JetBrains+Mono:wght@400&display=swap">
<style>
  * { box-sizing: border-box; margin: 0; }
  body {
    width: 1200px; height: 630px;
    background: #0B1D33;
    color: #fff;
    font-family: 'Onest', sans-serif;
    padding: 72px 80px;
    display: flex; flex-direction: column; justify-content: space-between;
    background-image:
      linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px);
    background-size: 60px 60px;
    position: relative; overflow: hidden;
  }
  .glow { position: absolute; inset: 0; background: radial-gradient(700px 400px at 82% 8%, rgba(53,214,204,.22), transparent 70%); }
  .row { position: relative; display: flex; align-items: center; gap: 16px; }
  .mark { display: grid; place-items: center; color: #35D6CC; }
  .brand b { font-size: 26px; font-weight: 800; letter-spacing: .07em; display: block; line-height: 1.1; }
  .brand span { font-size: 15px; color: #9FB1C7; }
  h1 { position: relative; font-size: 62px; font-weight: 800; line-height: 1.1; letter-spacing: -.02em; max-width: 17ch; }
  h1 em { font-style: normal; color: #35D6CC; }
  .foot { position: relative; display: flex; align-items: flex-end; justify-content: space-between; gap: 40px; }
  .facts { display: flex; gap: 40px; }
  .fact b { display: block; font-size: 30px; font-weight: 800; color: #fff; line-height: 1.1; }
  .fact span { font-size: 15px; color: #9FB1C7; }
  .phone { font-family: 'JetBrains Mono', monospace; font-size: 26px; color: #35D6CC; white-space: nowrap; }
</style></head>
<body>
  <div class="glow"></div>
  <div class="row">
    <div class="mark">${MARK}</div>
    <div class="brand"><b>НОРМА</b><span>вступление в СРО · НРС · НОК · лицензии</span></div>
  </div>
  <h1>Вступление в СРО <em>без устаревших норм</em></h1>
  <div class="foot">
    <div class="facts">
      <div class="fact"><b>24 часа</b><span>выписка из реестра</span></div>
      <div class="fact"><b>0 ₽</b><span>подготовка документов</span></div>
      <div class="fact"><b>10 млн ₽</b><span>актуальный порог</span></div>
    </div>
    <div class="phone">${PHONE}</div>
  </div>
</body></html>`

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } })
await page.setContent(html, { waitUntil: 'networkidle' })
await page.waitForTimeout(600) // дать шрифтам дорисоваться
const buffer = await page.screenshot({ type: 'png' })
await writeFile(out, buffer)
await browser.close()

console.log(`Картинка-превью сохранена: ${out}`)
