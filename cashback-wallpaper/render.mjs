/* Сборка обоев: HTML → страница в Chromium → PNG.

   Кадр снимается браузером, а не рисуется вручную в графической
   библиотеке, ради одной вещи: backdrop-filter. Настоящее размытие
   подложки под стеклом — это то, что отличает «полупрозрачное стекло»
   от «прямоугольника с прозрачностью», и повторить его сложением
   слоёв нельзя. Заодно даром достаются шрифты, переносы и SVG.

   Порядок шагов важен: сначала фон и шрифты, потом раскладка,
   и только потом подгонка цвета. Мерить контраст под карточкой,
   пока карточка не встала на место, бессмысленно. */

import { chromium } from 'playwright';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildHtml, mergeBanks } from './src/template.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

const dataPath = resolve(HERE, arg('data', 'data/wallpaper.json'));
const cfg = JSON.parse(await readFile(dataPath, 'utf8'));

if (arg('preset')) cfg.background = arg('preset');
if (arg('width')) cfg.size = { ...cfg.size, width: +arg('width') };
if (arg('height')) cfg.size = { ...cfg.size, height: +arg('height') };

const { banks, notes } = mergeBanks(cfg.banks);
cfg.banks = banks;
notes.forEach((n) => console.log(`  объединено: ${n}`));

const outName = arg('out', `wallpaper-${cfg.background}-${cfg.size.width}x${cfg.size.height}.png`);
const outPath = resolve(HERE, 'out', outName);
const htmlPath = join(HERE, 'out', '.page.html');

await mkdir(join(HERE, 'out'), { recursive: true });
await writeFile(htmlPath, buildHtml(cfg));

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: cfg.size.width, height: cfg.size.height },
  deviceScaleFactor: 1,
});

await page.goto(`file://${htmlPath}`);
await page.addScriptTag({ path: join(HERE, 'src/background.js') });
await page.addScriptTag({ path: join(HERE, 'src/adapt.js') });

/* Фон либо рисуется пресетом, либо берётся файлом — путь в конфиге.
   Дальше обе ветки одинаковы: adapt.js читает пиксели с <img>
   и не знает, откуда они взялись. */
const custom = cfg.backgroundFile ? resolve(HERE, cfg.backgroundFile) : null;
const customData = custom
  ? `data:image/${custom.endsWith('.png') ? 'png' : 'jpeg'};base64,` + (await readFile(custom)).toString('base64')
  : null;

await page.evaluate(async ({ w, h, preset, customData }) => {
  const img = document.getElementById('bg');
  img.src = customData || window.__makeBackground(w, h, preset);
  await img.decode();
  await document.fonts.ready;
}, { w: cfg.size.width, h: cfg.size.height, preset: cfg.background, customData });

const report = await page.evaluate(() => window.__adapt());

/* Кадр снимается после подгонки: значения CSS-переменных меняются
   в этот же тик, а браузер должен успеть перерисовать стекло. */
await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
await page.screenshot({ path: outPath, type: 'png' });

const box = await page.locator('.card').boundingBox();
await browser.close();

const pct = (v) => `${Math.round(v * 100)}%`;
console.log(`\n  ${outName}`);
console.log(`  фон .............. ${cfg.background}${custom ? ` (файл: ${cfg.backgroundFile})` : ''}`);
console.log(`  тема ............. ${report.theme === 'dark' ? 'светлый текст на тёмном стекле' : 'тёмный текст на светлом стекле'}`);
console.log(`  стекло ........... заливка ${pct(report.glassAlpha)}, размытие 30px`);
console.log(`  контраст текста .. ${report.textContrast}:1 ${report.textContrastOk ? '✓' : '— НЕ ДОТЯГИВАЕТ до 4.5'}`);
console.log(`  подписи .......... непрозрачность ${pct(report.mutedAlpha)}`);
for (const [src, b] of Object.entries(report.brands)) {
  const moved = b.moved ? `подсветлён на ${(b.moved * 100).toFixed(0)}% светлоты` : 'без правки';
  console.log(`  цвет ${src} → ${b.hex}  ${b.contrast}:1  (${moved})`);
}
console.log(`  таблица .......... ${Math.round(box.width)}×${Math.round(box.height)} px, ${pct(box.width / cfg.size.width)} ширины экрана`);

if (!report.textContrastOk) process.exitCode = 1;
