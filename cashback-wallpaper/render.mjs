#!/usr/bin/env node
// node render.mjs wallpapers/2026-10.json [--device iphone-17-pro] [--out out/x.png]
//
// 1. Сводит категории со скринов в разделы по банкам (lib/merge.mjs).
// 2. Раскладывает таблицу: одна колонка, если влезает, иначе две; таблица
//    по центру и не выше ~42 % экрана, не заходит под часы и нижние кнопки.
// 3. Смотрит на фон под таблицей: светлое стекло с тёмным текстом или тёмное
//    со светлым, оттенок — из цвета фона.
// 4. Подбирает плотность стекла по НАСТОЯЩИМ пикселям: снимает обои без
//    текста и под каждой строкой меряет контраст. Стекло делается ровно
//    настолько плотным, чтобы самая слабая строка дала 4,5:1, — не плотнее:
//    иначе это уже не стекло, а плашка.
// 5. Сохраняет обои и предпросмотр с часами экрана блокировки.
import { readFileSync, mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, resolve, basename, extname } from 'node:path';
import { chromium } from 'playwright';
import { buildSections } from './lib/merge.mjs';
import { buildHtml } from './lib/page.mjs';
import { DEVICES, DEFAULT_DEVICE, DPR } from './lib/devices.mjs';

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args.splice(i, 2)[1] : undefined; };
const outArg = opt('--out');
const deviceArg = opt('--device');
const placementArg = opt('--placement');
const cfgPath = args[0];
if (!cfgPath) {
  console.error('Использование: node render.mjs <обои.json> [--device ' + Object.keys(DEVICES).join('|') + '] [--out файл.png]');
  process.exit(1);
}
const cfgDir = dirname(resolve(cfgPath));
const cfg = JSON.parse(readFileSync(cfgPath, 'utf8'));
const deviceKey = deviceArg ?? cfg.device ?? DEFAULT_DEVICE;
const device = DEVICES[deviceKey];
if (!device) throw new Error(`Нет такого экрана: ${deviceKey}. Есть: ${Object.keys(DEVICES).join(', ')}`);

const TEXT_TARGET = 4.5; // WCAG AA для обычного текста
const ICON_TARGET = 3; // для значков
// Доли высоты экрана: таблица не заходит выше часов (top) и ниже кнопок
// (bottom), не выше maxH и стоит центром на center.
// under-clock — для крупных часов iOS 26: они опускаются почти до середины
// экрана (на снимке пользователя низ цифр — 49,5 % высоты), и таблица
// по центру легла бы на цифры.
const PLACEMENTS = {
  center: { top: 0.29, bottom: 0.86, maxH: 0.42, center: 0.5 },
  'under-clock': { top: 0.505, bottom: 0.865, maxH: 0.36, center: 0.685 },
};
const placement = placementArg ?? cfg.placement ?? 'center';
if (!PLACEMENTS[placement]) throw new Error(`Нет такого размещения: ${placement}. Есть: ${Object.keys(PLACEMENTS).join(', ')}`);
const ZONE = { ...PLACEMENTS[placement], ...(cfg.zone ?? {}) };

// ---------- данные ----------
const { sections, notes } = buildSections(cfg);
if (!sections.length) throw new Error('В обоях нет ни одной категории');

const bgPath = resolve(cfgDir, cfg.background);
if (!existsSync(bgPath)) throw new Error(`Нет файла фона: ${bgPath}`);
const mime = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp' }[extname(bgPath).toLowerCase()];
if (!mime) throw new Error(`Фон ${basename(bgPath)}: нужен JPG, PNG или WebP (HEIC сначала перевести)`);
const bgDataUrl = `data:${mime};base64,${readFileSync(bgPath).toString('base64')}`;

const now = new Date();
const html = buildHtml({
  device,
  bgDataUrl,
  bgPosition: cfg.bgPosition ?? '50% 50%',
  sections,
  title: cfg.title === undefined ? null : cfg.title,
  phrase: cfg.phrase ?? null,
  phraseFont: cfg.phraseFont ?? 'serif',
  lockscreen: {
    time: '9:41',
    date: now.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }).replace(/^./, (c) => c.toUpperCase()),
  },
});

const outPath = resolve(outArg ?? resolve('out', basename(cfgPath, '.json') + '.png'));
mkdirSync(dirname(outPath), { recursive: true });

// ---------- цвет ----------
function hslToRgb(h, s, l) {
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [f(0), f(8), f(4)].map((v) => Math.round(v * 255));
}
const rgbStr = (c) => c.join(' ');

function theme(stats) {
  const { h, s } = stats;
  // Светлый текст выигрывает при равенстве: на фото средней яркости тёмное
  // стекло со светлыми буквами читается «как на iPhone», светлое — серым пятном.
  const light = stats.contrastWhite >= stats.contrastBlack * 0.8;
  if (light) {
    return {
      mode: 'dark-glass',
      vars: {
        '--ink': rgbStr(hslToRgb(h, Math.min(s * 0.4, 0.22), 0.975)),
        '--fill': rgbStr(hslToRgb(h, Math.min(s * 0.7, 0.4), 0.1)),
        '--edge-hi': '255 255 255', '--edge-hi-a': '.42', '--edge-lo-a': '.08',
        '--line-a': '.22', '--soft-a': '.11', '--shadow-a': '.32', '--sat': '1.4',
      },
      alpha: { min: 0.14, max: 0.82 },
    };
  }
  return {
    mode: 'light-glass',
    vars: {
      '--ink': rgbStr(hslToRgb(h, Math.min(s * 0.6, 0.35), 0.13)),
      '--fill': rgbStr(hslToRgb(h, Math.min(s * 0.5, 0.35), 0.975)),
      '--edge-hi': '255 255 255', '--edge-hi-a': '.9', '--edge-lo-a': '.32',
      '--line-a': '.17', '--soft-a': '.085', '--shadow-a': '.14', '--sat': '1.6',
    },
    alpha: { min: 0.2, max: 0.88 },
  };
}

// ---------- функции страницы ----------
// Раскладка: перебор от самой крупной и простой к плотной, первая подошедшая.
function arrange({ zone }) {
  const root = document.documentElement;
  const W = innerWidth, H = innerHeight;
  const glass = document.getElementById('glass');
  const colsEl = document.getElementById('cols');
  const stage = document.getElementById('stage');
  const phrase = document.getElementById('phrase');
  const banks = [...document.querySelectorAll('.bank')];
  const tries = [];
  const one = { cols: 1, tw: 0.64, row: 27, pad: 18, cg: 20 };
  const two = { cols: 2, tw: 0.9, row: 27, pad: 18, cg: 20 };
  // Плотнее строки и уже поля — раньше, чем мельче буквы: кегль дороже воздуха.
  // На узком экране (393 pt) длинные названия («Перекрёсток Доставка»)
  // упираются в ширину колонки, а не в высоту.
  const tight = { cols: 2, tw: 0.95, row: 23, pad: 12, cg: 12 };
  for (const s of [1, 0.94]) tries.push({ ...one, s });
  for (const s of [1, 0.94, 0.88]) tries.push({ ...two, s });
  for (const s of [0.94, 0.88, 0.84, 0.8, 0.76, 0.72]) tries.push({ ...tight, s });

  const build = (cols) => {
    colsEl.innerHTML = '';
    if (cols === 1 || banks.length < 2) {
      const c = document.createElement('div'); c.className = 'col';
      banks.forEach((b) => c.appendChild(b)); colsEl.appendChild(c);
      return;
    }
    // Делим по порядку банков так, чтобы колонки вышли как можно ровнее.
    const one = document.createElement('div'); one.className = 'col';
    banks.forEach((b) => one.appendChild(b)); colsEl.appendChild(one);
    const hs = banks.map((b) => b.offsetHeight);
    let best = 1, bestH = Infinity;
    for (let k = 1; k < banks.length; k++) {
      const a = hs.slice(0, k).reduce((x, y) => x + y, 0), b = hs.slice(k).reduce((x, y) => x + y, 0);
      if (Math.max(a, b) < bestH) { bestH = Math.max(a, b); best = k; }
    }
    colsEl.innerHTML = '';
    for (const part of [banks.slice(0, best), banks.slice(best)]) {
      const c = document.createElement('div'); c.className = 'col';
      part.forEach((b) => c.appendChild(b)); colsEl.appendChild(c);
    }
  };

  let chosen = null;
  for (const t of tries) {
    root.style.setProperty('--s', t.s);
    root.style.setProperty('--tw', `${Math.round(W * t.tw)}px`);
    root.style.setProperty('--row', `${t.row}px`);
    root.style.setProperty('--pad', `${t.pad}px`);
    root.style.setProperty('--cg', `${t.cg}px`);
    build(t.cols);
    const overflow = [...document.querySelectorAll('.nm')].some((n) => n.scrollWidth > n.clientWidth + 0.5);
    if (!overflow && glass.offsetHeight <= H * zone.maxH) { chosen = t; break; }
  }
  const fits = Boolean(chosen);
  chosen ??= tries[tries.length - 1];

  // По центру экрана; если не помещается между часами и кнопками — сдвиг.
  const gh = glass.offsetHeight;
  const ph = phrase ? phrase.offsetHeight + parseFloat(getComputedStyle(phrase).marginTop) : 0;
  let top = H * zone.center - gh / 2;
  top = Math.max(top, H * zone.top);
  top = Math.min(top, H * zone.bottom - gh - ph);
  stage.style.top = `${Math.round(top)}px`;
  return { ...chosen, fits, glassHeight: gh, top: Math.round(top), cols: document.querySelectorAll('.col').length };
}

function setVars(vars) {
  for (const [k, v] of Object.entries(vars)) document.documentElement.style.setProperty(k, String(v));
}

function rectOf(sel) {
  const els = [...document.querySelectorAll(sel)];
  if (!els.length) return null;
  const rs = els.map((e) => e.getBoundingClientRect());
  const x = Math.min(...rs.map((r) => r.left)), y = Math.min(...rs.map((r) => r.top));
  return { x, y, width: Math.max(...rs.map((r) => r.right)) - x, height: Math.max(...rs.map((r) => r.bottom)) - y };
}

// Что меряем: каждая строка текста и каждая иконка, с её цветом и прозрачностью.
function collectTargets() {
  const parse = (str) => {
    const m = str.match(/rgba?\(([^)]+)\)/);
    const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    return [p[0], p[1], p[2], p[3] ?? 1];
  };
  const out = [];
  const add = (el, kind, color, target) => {
    let rects;
    if (kind === 'icon') rects = [el.getBoundingClientRect()];
    else { const r = document.createRange(); r.selectNodeContents(el); rects = [...r.getClientRects()]; }
    for (const rc of rects) {
      if (rc.width < 1 || rc.height < 1) continue;
      // Строчный блок выше самих букв: берём середину по высоте, где буквы.
      const pad = kind === 'icon' ? 0 : rc.height * 0.18;
      out.push({ kind, label: (el.textContent || el.closest('.row')?.textContent || '').trim().slice(0, 40), color, target,
        x: rc.left, y: rc.top + pad, w: rc.width, h: rc.height - pad * 2 });
    }
  };
  document.querySelectorAll('.t, .title').forEach((el) => add(el, 'text', parse(getComputedStyle(el).color), 4.5));
  document.querySelectorAll('.ic').forEach((el) => add(el, 'icon', parse(getComputedStyle(el).stroke), 3));
  const ph = document.getElementById('phrase');
  if (ph) add(ph, 'phrase', parse(getComputedStyle(ph).color), 4.5);
  return out;
}

// Контраст под каждой целью по снимку без текста. Цвет буквы смешивается
// с фоном по её прозрачности (в sRGB, как смешивает браузер); берётся 2-й
// процентиль по пикселям — самое слабое место строки, без единичных пылинок.
async function measure({ b64, clip, dpr, targets }) {
  const img = new Image();
  img.src = `data:image/png;base64,${b64}`;
  await img.decode();
  const cv = document.createElement('canvas');
  cv.width = img.width; cv.height = img.height;
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(img, 0, 0);
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const lum = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  return targets.map((t) => {
    const x0 = Math.max(0, Math.floor((t.x - clip.x) * dpr)), y0 = Math.max(0, Math.floor((t.y - clip.y) * dpr));
    const w = Math.min(cv.width - x0, Math.ceil(t.w * dpr)), h = Math.min(cv.height - y0, Math.ceil(t.h * dpr));
    if (w <= 0 || h <= 0) return { ...t, contrast: null };
    const d = ctx.getImageData(x0, y0, w, h).data;
    const [ir, ig, ib, ia] = t.color;
    const cs = [];
    for (let i = 0; i < d.length; i += 4) {
      const r = d[i], g = d[i + 1], b = d[i + 2];
      const lb = lum(r, g, b);
      const lt = lum(ia * ir + (1 - ia) * r, ia * ig + (1 - ia) * g, ia * ib + (1 - ia) * b);
      cs.push((Math.max(lb, lt) + 0.05) / (Math.min(lb, lt) + 0.05));
    }
    cs.sort((a, b) => a - b);
    return { kind: t.kind, label: t.label, target: t.target, contrast: cs[Math.floor(cs.length * 0.02)] };
  });
}

// Фон под таблицей: средний цвет, оттенок и чем лучше читается — белым или чёрным.
async function bgStats({ b64 }) {
  const img = new Image();
  img.src = `data:image/png;base64,${b64}`;
  await img.decode();
  const cv = document.createElement('canvas');
  cv.width = 48; cv.height = Math.max(8, Math.round(48 * img.height / img.width));
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(img, 0, 0, cv.width, cv.height);
  const d = ctx.getImageData(0, 0, cv.width, cv.height).data;
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const ls = []; let R = 0, G = 0, Bc = 0, n = 0;
  for (let i = 0; i < d.length; i += 4) {
    ls.push(0.2126 * lin(d[i]) + 0.7152 * lin(d[i + 1]) + 0.0722 * lin(d[i + 2]));
    R += d[i]; G += d[i + 1]; Bc += d[i + 2]; n++;
  }
  ls.sort((a, b) => a - b);
  const med = ls[Math.floor(ls.length / 2)];
  const [r, g, b] = [R / n / 255, G / n / 255, Bc / n / 255];
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  let h = 0, s = 0;
  if (mx !== mn) {
    const dd = mx - mn;
    s = dd / (1 - Math.abs(2 * l - 1));
    h = mx === r ? 60 * (((g - b) / dd) % 6) : mx === g ? 60 * ((b - r) / dd + 2) : 60 * ((r - g) / dd + 4);
    if (h < 0) h += 360;
  }
  return { h, s, l, median: med, p10: ls[Math.floor(ls.length * 0.1)], p90: ls[Math.floor(ls.length * 0.9)],
    contrastWhite: 1.05 / (med + 0.05), contrastBlack: (med + 0.05) / 0.05 };
}

// ---------- сборка ----------
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: device.w, height: device.h }, deviceScaleFactor: DPR });
  await page.setContent(html, { waitUntil: 'load' });
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map((i) => i.decode())); });
  const fontsOk = await page.evaluate(() => document.fonts.check('13px Inter', 'Кэшбэк 5%'));
  if (!fontsOk) throw new Error('Шрифт Inter не загрузился');

  const layout = await page.evaluate(arrange, { zone: ZONE });
  if (!layout.fits) notes.push('Таблица не влезла в отведённую высоту даже в две колонки мелким кеглем — слишком много категорий');

  const snap = async (cls, clip) => {
    await page.evaluate((c) => { document.documentElement.className = c; }, cls);
    const buf = await page.screenshot({ clip, type: 'png', animations: 'disabled' });
    await page.evaluate(() => { document.documentElement.className = ''; });
    return buf.toString('base64');
  };

  // Фон под стеклом (с запасом по краям, как берёт размытие).
  const g = await page.evaluate(rectOf, '#glass');
  const area = { x: Math.max(0, g.x - 20), y: Math.max(0, g.y - 20), width: Math.min(device.w, g.width + 40), height: g.height + 40 };
  const stats = await page.evaluate(bgStats, { b64: await snap('m-bare', area) });
  const th = theme(stats);
  await page.evaluate(setVars, th.vars);

  const clipAll = await page.evaluate(() => {
    const els = ['#glass', '#phrase'].map((s) => document.querySelector(s)).filter(Boolean).map((e) => e.getBoundingClientRect());
    const x = Math.max(0, Math.min(...els.map((r) => r.left)) - 30), y = Math.max(0, Math.min(...els.map((r) => r.top)) - 30);
    return { x, y, width: Math.min(innerWidth - x, Math.max(...els.map((r) => r.right)) - x + 30), height: Math.min(innerHeight - y, Math.max(...els.map((r) => r.bottom)) - y + 30) };
  });

  const run = async () => {
    const targets = await page.evaluate(collectTargets);
    return page.evaluate(measure, { b64: await snap('m-text', clipAll), clip: clipAll, dpr: DPR, targets });
  };
  const worst = (res, kinds) => res.filter((r) => kinds.includes(r.kind) && r.contrast != null)
    .reduce((m, r) => (!m || r.contrast / r.target < m.contrast / m.target ? r : m), null);

  // Фраза лежит прямо на фоне: её цвет выбирается отдельно, по фону под ней.
  let phraseInfo = null;
  if (cfg.phrase) {
    const options = [th.vars['--ink'], th.mode === 'dark-glass' ? '24 24 28' : '255 255 255'];
    let best = null;
    for (const ink of options) {
      const glow = ink.split(' ').map(Number).reduce((a, b) => a + b, 0) > 384 ? '0 0 0' : '255 255 255';
      await page.evaluate(setVars, { '--phrase-ink': ink, '--phrase-glow': glow, '--phrase-glow-a': 0 });
      const p = worst(await run(), ['phrase']);
      if (!best || p.contrast > best.contrast) best = { ink, glow, contrast: p.contrast };
    }
    let glowA = 0;
    await page.evaluate(setVars, { '--phrase-ink': best.ink, '--phrase-glow': best.glow, '--phrase-glow-a': 0 });
    // Не хватает контраста — мягкий ореол за буквами, а не плашка.
    while (best.contrast < TEXT_TARGET && glowA < 0.75) {
      glowA = +(glowA + 0.15).toFixed(2);
      await page.evaluate(setVars, { '--phrase-glow-a': glowA });
      best.contrast = worst(await run(), ['phrase']).contrast;
    }
    phraseInfo = { ink: best.ink, glow: glowA, contrast: +best.contrast.toFixed(2) };
    if (best.contrast < TEXT_TARGET) notes.push(`Фраза: контраст ${best.contrast.toFixed(2)}:1 — фон под ней слишком пёстрый`);
  }

  // Плотность стекла: от прозрачного к плотному, первая, где всё читается.
  let alpha = th.alpha.min, res;
  for (;;) {
    await page.evaluate(setVars, { '--fill-a': alpha.toFixed(3) });
    res = await run();
    const wt = worst(res, ['text']), wi = worst(res, ['icon']);
    const ok = wt.contrast >= TEXT_TARGET + 0.1 && (!wi || wi.contrast >= ICON_TARGET);
    if (ok || alpha >= th.alpha.max) break;
    alpha = Math.min(th.alpha.max, alpha + 0.03);
  }
  const wt = worst(res, ['text']), wi = worst(res, ['icon']);
  if (wt.contrast < TEXT_TARGET) notes.push(`Слабее всего читается «${wt.label}»: ${wt.contrast.toFixed(2)}:1`);

  await page.evaluate(() => { document.documentElement.className = ''; });
  await page.screenshot({ path: outPath, type: 'png', animations: 'disabled' });
  const previewPath = outPath.replace(/\.png$/, '-preview.png');
  await page.evaluate(() => { document.documentElement.className = 'preview'; });
  await page.screenshot({ path: previewPath, type: 'png', animations: 'disabled' });

  const report = {
    out: outPath,
    preview: previewPath,
    device: `${deviceKey} — ${device.label}, ${device.w * DPR}×${device.h * DPR}`,
    layout: { columns: layout.cols, scale: layout.s, top: layout.top, glassHeight: layout.glassHeight },
    background: { median: +stats.median.toFixed(3), hue: Math.round(stats.h), sat: +stats.s.toFixed(2) },
    glass: { mode: th.mode, fill: +alpha.toFixed(3) },
    contrast: { textMin: +wt.contrast.toFixed(2), textMinAt: wt.label, iconMin: wi ? +wi.contrast.toFixed(2) : null, phrase: phraseInfo },
    sections: sections.map((s) => `${s.name}: ${s.rows.map((r) => `${r.name} ${r.percent}%`).join(', ')}`),
    notes,
  };
  writeFileSync(outPath.replace(/\.png$/, '.report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
