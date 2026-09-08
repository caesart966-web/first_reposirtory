import { chromium } from 'playwright'
import { mkdirSync } from 'fs'
const OUT = '/tmp/claude-0/-home-user-first-reposirtory/092035c2-3b5c-50fa-8257-cfedbfa751dd/scratchpad/audit'
mkdirSync(OUT, { recursive: true })
const url = process.argv[2]
const tag = process.argv[3]
const w = Number(process.argv[4] || 1280)
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: w, height: 1000 } })
await p.goto('http://127.0.0.1:4321' + url, { waitUntil: 'networkidle' })
await p.evaluate(() => document.querySelectorAll('.rv').forEach(e => e.classList.add('in')))
await p.waitForTimeout(700)
const h = await p.evaluate(() => document.body.scrollHeight)
const step = 1250
let i = 0
for (let y = 0; y < h; y += step) {
  await p.evaluate((y) => window.scrollTo(0, y), y)
  await p.waitForTimeout(250)
  await p.screenshot({ path: `${OUT}/${tag}-${String(++i).padStart(2, '0')}.png` })
}
console.log(`${tag}: высота ${h}px, ${i} кадров`)
await b.close()
