// Рисует все схемы в Chromium и сохраняет PNG (для Word) и SVG (исходники).
// Запуск: node render.mjs [имя схемы ...]
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
// playwright и docx стоят глобально — берём их из глобальной папки npm.
const require = createRequire(join(execSync('npm root -g').toString().trim(), 'noop.js'));
const { chromium } = require('playwright');
const out = join(here, 'build', 'img');
mkdirSync(out, { recursive: true });

const data = readFileSync(join(here, 'data.json'), 'utf8');
// Шрифт ARIS Express — Tahoma (обычный и жирный). Файлы кладет get-fonts.sh в build/fonts,
// в страницу они встраиваются data:-адресом: setContent открывает about:blank, и file:// не грузится.
const fontDir = join(here, 'build', 'fonts');
const face = (file, weight) => {
  const p = join(fontDir, file);
  if (!existsSync(p)) throw new Error(`Нет шрифта ${p}. Запустите ./get-fonts.sh`);
  return `@font-face{font-family:Tahoma;font-weight:${weight};src:url(data:font/ttf;base64,${readFileSync(p).toString('base64')}) format('truetype')}`;
};
const fonts = face('tahoma.ttf', 400) + face('tahomabd.ttf', 700);
const html = `<!doctype html><html><head><meta charset="utf-8"><style>${fonts}body{margin:0;background:#fff}</style></head><body><div id="c"></div><script>document.fonts.load('400 12px Tahoma');document.fonts.load('700 12px Tahoma');</script></body></html>`;

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
const page = await browser.newPage({ deviceScaleFactor: 3, viewport: { width: 1800, height: 1200 } });
page.on('pageerror', (e) => { console.error('Ошибка на странице:', e.message); process.exitCode = 1; });
await page.setContent(html);
// сначала шрифт, потом скрипты схем: перенос строк меряется по Tahoma
await page.evaluate(async () => { await document.fonts.load('400 12px Tahoma'); await document.fonts.load('700 12px Tahoma'); await document.fonts.ready; });
if (!(await page.evaluate(() => document.fonts.check('700 12px Tahoma')))) throw new Error('Tahoma не загрузился');
await page.addScriptTag({ content: `window.DATA = ${data};` });
for (const f of ['diagrams/lib.js', 'diagrams/defs.js', 'diagrams/chart.js']) await page.addScriptTag({ content: readFileSync(join(here, f), 'utf8') });

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
