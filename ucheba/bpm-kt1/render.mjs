// Рисует все схемы в Chromium и сохраняет PNG (для Word) и SVG (исходники).
// Запуск: node render.mjs [имя схемы ...]
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
// playwright и docx стоят глобально — берём их из глобальной папки npm.
const require = createRequire(join(execSync('npm root -g').toString().trim(), 'noop.js'));
const { chromium } = require('playwright');
const out = join(here, 'build', 'img');
mkdirSync(out, { recursive: true });

const data = readFileSync(join(here, 'data.json'), 'utf8');
const scripts = `<script>window.DATA = ${data};</script>` + ['diagrams/lib.js', 'diagrams/defs.js', 'diagrams/chart.js']
  .map((f) => `<script>${readFileSync(join(here, f), 'utf8')}</script>`).join('\n');
const html = `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#fff}</style></head><body><div id="c"></div>${scripts}</body></html>`;

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
const page = await browser.newPage({ deviceScaleFactor: 3, viewport: { width: 1800, height: 1200 } });
page.on('pageerror', (e) => { console.error('Ошибка на странице:', e.message); process.exitCode = 1; });
await page.setContent(html);
await page.evaluate(() => document.fonts.ready);

const names = process.argv.slice(2).length ? process.argv.slice(2) : await page.evaluate(() => Object.keys(window.DIAGRAMS));
for (const name of names) {
  const r = await page.evaluate((n) => {
    const d = window.DIAGRAMS[n]();
    document.getElementById('c').innerHTML = d.svg;
    return { svg: d.svg, w: d.w, h: d.h };
  }, name);
  writeFileSync(join(out, `${name}.svg`), r.svg);
  await page.locator('#c svg').screenshot({ path: join(out, `${name}.png`) });
  writeFileSync(join(out, `${name}.json`), JSON.stringify({ w: Math.ceil(r.w), h: Math.ceil(r.h) }));
  console.log(`${name}: ${Math.ceil(r.w)}×${Math.ceil(r.h)}`);
}
await browser.close();
