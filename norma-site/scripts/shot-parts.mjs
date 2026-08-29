// Снимки по частям — чтобы посмотреть страницу кусками, а не одной длинной лентой.
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:4321'
const OUT = process.argv[2]
const path = process.argv[3] || '/'
const name = process.argv[4] || 'part'
const w = Number(process.argv[5] || 1360)
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: w, height: 900 }, isMobile: w < 500, hasTouch: w < 500 })
await p.goto(BASE + path, { waitUntil: 'networkidle' })
await p.evaluate(async () => { await new Promise((d)=>{let y=0;const s=()=>{y+=innerHeight;scrollTo(0,y);y<document.body.scrollHeight?setTimeout(s,120):(scrollTo(0,0),setTimeout(d,500))};s()}) })
await p.waitForFunction(() => !document.querySelector('.rv:not(.in)'), { timeout: 8000 }).catch(()=>{})
const total = await p.evaluate(() => document.body.scrollHeight)
const step = 1600
let i = 0
for (let y = 0; y < total; y += step, i++) {
  await p.evaluate((yy) => window.scrollTo(0, yy), y)
  await p.waitForTimeout(250)
  await p.screenshot({ path: `${OUT}/${name}-${String(i).padStart(2,'0')}.png` })
}
await b.close()
console.log(`частей: ${i}`)
