/* Проверка готового кадра по настоящим пикселям.

   adapt.js считает контраст ДО съёмки и по приближению: он усредняет фон
   так, как это предположительно сделает backdrop-filter. Предположение
   может разойтись с тем, что нарисовал браузер, — размытие у стекла своё,
   насыщенность подкручена, зерно фона добавляет разброса. Поэтому здесь
   меряется результат: кадр снимается дважды — с текстом и без него, —
   и под каждой надписью берутся те самые пиксели, поверх которых она
   легла. Ниже 4.5:1 для текста и 3:1 для иконок сборка падает.

   Заодно ловится молчаливая беда: длинное название категории, которое
   вёрстка обрежет многоточием. На обоях это не заметят до самого телефона. */

import { chromium } from 'playwright';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildHtml, mergeBanks } from '../src/template.mjs';

const HERE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const PRESETS = ['midnight', 'graphite', 'indigo', 'paper'];
const TARGETS = { text: 4.5, icon: 3.0 };

const cfg0 = JSON.parse(await readFile(join(HERE, 'data/wallpaper.json'), 'utf8'));
const browser = await chromium.launch();
let failures = 0, checks = 0;

for (const preset of PRESETS) {
  const cfg = { ...JSON.parse(JSON.stringify(cfg0)), background: preset };
  cfg.banks = mergeBanks(cfg.banks).banks;

  const htmlPath = join(HERE, 'out', `.check-${preset}.html`);
  await mkdir(join(HERE, 'out'), { recursive: true });
  await writeFile(htmlPath, buildHtml(cfg));

  const page = await browser.newPage({
    viewport: { width: cfg.size.width, height: cfg.size.height },
    deviceScaleFactor: 1,
  });
  await page.goto(`file://${htmlPath}`);
  await page.addScriptTag({ path: join(HERE, 'src/background.js') });
  await page.addScriptTag({ path: join(HERE, 'src/adapt.js') });
  await page.evaluate(async ({ w, h, preset }) => {
    const img = document.getElementById('bg');
    img.src = window.__makeBackground(w, h, preset);
    await img.decode();
    await document.fonts.ready;
  }, { w: cfg.size.width, h: cfg.size.height, preset });
  await page.evaluate(() => window.__adapt());
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));

  /* Что меряем: селектор, чем считается (текст или иконка) и цвет,
     который браузер реально применил, — а не тот, что задумывался. */
  const items = await page.evaluate(() => {
    const out = [];
    const pick = (sel, kind) => {
      for (const el of document.querySelectorAll(sel)) {
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        const cs = getComputedStyle(el);
        out.push({
          kind, sel,
          text: (el.textContent || '').trim().slice(0, 30),
          color: kind === 'icon' ? cs.color : cs.color,
          opacity: parseFloat(cs.opacity),
          rect: { x: r.left, y: r.top, w: r.width, h: r.height },
          clipped: el.scrollWidth > el.clientWidth + 1,
        });
      }
    };
    pick('.caption', 'text');
    pick('.bank__name', 'text');
    pick('.row__label', 'text');
    pick('.row__pct b', 'text');
    pick('.row__pct i', 'text');
    pick('.row__ico', 'icon');
    return out;
  });

  /* Второй кадр — тот же, но надписи спрятаны. visibility: hidden
     не трогает раскладку, поэтому прямоугольники из первого кадра
     указывают ровно на те пиксели, что были под буквами. */
  await page.evaluate(() => {
    for (const el of document.querySelectorAll('.caption,.bank__name,.row__label,.row__pct,.row__ico'))
      el.style.visibility = 'hidden';
  });
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
  const shot = (await page.screenshot({ type: 'png' })).toString('base64');
  await page.close();

  /* Пиксели читаются в отдельной пустой странице: сам кадр для этого
     не годится — canvas не умеет снимать backdrop-filter. */
  const probe = await browser.newPage();
  const results = await probe.evaluate(async ({ shot, items, targets }) => {
    const srgbToLin = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
    const lum = (r, g, b) => 0.2126 * srgbToLin(r / 255) + 0.7152 * srgbToLin(g / 255) + 0.0722 * srgbToLin(b / 255);
    const ratio = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const parse = (css) => css.match(/[\d.]+/g).slice(0, 4).map(Number);

    const img = new Image();
    img.src = 'data:image/png;base64,' + shot;
    await img.decode();
    const cv = document.createElement('canvas');
    cv.width = img.width; cv.height = img.height;
    const ctx = cv.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(img, 0, 0);

    return items.map((it) => {
      const { x, y, w, h } = it.rect;
      const d = ctx.getImageData(Math.round(x), Math.round(y), Math.max(1, Math.round(w)), Math.max(1, Math.round(h))).data;
      let lo = 1, hi = 0;
      for (let i = 0; i < d.length; i += 4) {
        const L = lum(d[i], d[i + 1], d[i + 2]);
        if (L < lo) lo = L;
        if (L > hi) hi = L;
      }
      /* Цвет надписи — с учётом её собственной прозрачности: сливается она
         с фоном уже после наложения, и мерить надо то, что видно. */
      const [r, g, b, a = 1] = parse(it.color);
      const alpha = a * (it.opacity ?? 1);
      const mix = (bgL) => {
        /* Приблизить фон одним серым по яркости достаточно: интерес
           не в оттенке, а в том, тонет надпись или нет. */
        const bg = Math.pow(bgL, 1 / 2.2) * 255;
        return lum(r * alpha + bg * (1 - alpha), g * alpha + bg * (1 - alpha), b * alpha + bg * (1 - alpha));
      };
      const worst = Math.min(ratio(mix(lo), lo), ratio(mix(hi), hi));
      return { ...it, contrast: +worst.toFixed(2), target: targets[it.kind] };
    });
  }, { shot, items, targets: TARGETS });
  await probe.close();

  const bad = results.filter((r) => r.contrast < r.target);
  const clipped = results.filter((r) => r.clipped);
  checks += results.length;
  failures += bad.length + clipped.length;

  const min = Math.min(...results.map((r) => r.contrast));
  console.log(`${bad.length || clipped.length ? '✗' : '✓'} ${preset.padEnd(9)} ${results.length} замеров, минимум ${min.toFixed(2)}:1`);
  for (const r of bad) console.log(`    контраст ${r.contrast}:1 < ${r.target} — ${r.sel} «${r.text}»`);
  for (const r of clipped) console.log(`    обрезано многоточием — ${r.sel} «${r.text}»`);
}

await browser.close();
console.log(`\n${failures ? '✗' : '✓'} ${checks} замеров, ${failures} нарушений`);
process.exitCode = failures ? 1 : 0;
