// Длина страницы по разделам: сколько экранов занимает каждый и где
// начинается форма заявки.
//
// Запуск:  node scripts/measure-length.mjs [адрес сайта] [путь]
//          (по умолчанию http://127.0.0.1:4321 и главная)
//
// Зачем. Длину главной дважды обсуждали на глаз, и оба раза глаз ошибся:
// «ужмём до 18 экранов» подрезкой абзацев дало 4 %, а разговор о целых
// разделах — 57 %. Решать, какой раздел убрать, надо по цифрам: этот
// скрипт показывает, сколько места у каждого раздела на телефоне
// и на компьютере и на каком экране человек добирается до заявки.
// Слова считаются по видимому тексту: свёрнутые ответы в вопросах
// не считаются, как их и не видит посетитель.

import { chromium } from './lib/browser.mjs'

const BASE = process.argv[2] || 'http://127.0.0.1:4321'
const PATH = process.argv[3] || '/'
const browser = await chromium.launch()

for (const [w, h, name] of [[390, 844, 'телефон'], [1440, 900, 'компьютер']]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  await page.goto(BASE + PATH, { waitUntil: 'networkidle' })
  const r = await page.evaluate(() => {
    const words = (el) => (el.innerText || '').split(/\s+/).filter(Boolean).length
    const main = document.querySelector('main') || document.body
    const parts = [...main.children]
      .map((el) => {
        const b = el.getBoundingClientRect()
        const title = el.querySelector('h1, h2')?.textContent?.trim().replace(/\s+/g, ' ') || el.className
        return { id: el.id ? '#' + el.id : '', title, h: Math.round(b.height), words: words(el) }
      })
      .filter((p) => p.h > 0)
    const form = document.querySelector('#lead-form-el')
    return {
      parts,
      total: document.documentElement.scrollHeight,
      words: words(main),
      form: form ? Math.round(form.getBoundingClientRect().top + scrollY) : null,
    }
  })
  const scr = (px) => (px / h).toFixed(1)
  console.log(`\n${name} ${w}×${h}: ${scr(r.total)} экрана, ${r.words} слов` +
    (r.form === null ? ', формы нет' : `, форма заявки с ${scr(r.form)}-го экрана`))
  for (const p of r.parts) {
    console.log(`  ${scr(p.h).padStart(5)} экр.  ${String(p.words).padStart(4)} сл.  ${p.id} ${p.title.slice(0, 60)}`)
  }
  await ctx.close()
}
await browser.close()
