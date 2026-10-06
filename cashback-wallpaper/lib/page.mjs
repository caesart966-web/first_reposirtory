// Разметка обоев. Всё — шрифты, фон, иконки — встраивается в страницу
// data-адресами: страница открывается через setContent (about:blank),
// и файлы по file:// браузер оттуда не грузит — подставил бы системный шрифт
// без единой ошибки.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { formatPercent } from './merge.mjs';

const require = createRequire(import.meta.url);

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

function fontFace(family, pkg, file, weight, style, range) {
  const path = require.resolve(`@fontsource/${pkg}/files/${file}`);
  const b64 = readFileSync(path).toString('base64');
  return `@font-face{font-family:'${family}';font-style:${style};font-weight:${weight};font-display:block;` +
    `src:url(data:font/woff2;base64,${b64}) format('woff2');unicode-range:${range}}`;
}

const LATIN = 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD';
const CYR = 'U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116';

function fonts() {
  const out = [];
  for (const w of [400, 500, 600]) {
    out.push(fontFace('Inter', 'inter', `inter-latin-${w}-normal.woff2`, w, 'normal', LATIN));
    out.push(fontFace('Inter', 'inter', `inter-cyrillic-${w}-normal.woff2`, w, 'normal', CYR));
  }
  for (const st of ['normal', 'italic']) {
    out.push(fontFace('Cormorant', 'cormorant-garamond', `cormorant-garamond-latin-500-${st}.woff2`, 500, st, LATIN));
    out.push(fontFace('Cormorant', 'cormorant-garamond', `cormorant-garamond-cyrillic-500-${st}.woff2`, 500, st, CYR));
  }
  return out.join('\n');
}

const iconCache = new Map();
export function icon(name) {
  if (!iconCache.has(name)) {
    const svg = readFileSync(require.resolve(`lucide-static/icons/${name}.svg`), 'utf8');
    const inner = svg.slice(svg.indexOf('>', svg.indexOf('<svg')) + 1, svg.lastIndexOf('</svg>')).trim();
    iconCache.set(name, inner);
  }
  return `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${iconCache.get(name)}</svg>`;
}

export function buildHtml({ device, bgDataUrl, bgPosition, sections, title, phrase, phraseFont, lockscreen }) {
  const banks = sections.map((s) => `
    <section class="bank">
      <div class="bh"><span class="t">${esc(s.name)}</span>${s.note ? `<span class="t bn">${esc(s.note)}</span>` : ''}</div>
      ${s.rows.map((r) => `
      <div class="row">${icon(r.icon)}<span class="t nm">${esc(r.name)}</span><span class="t pc">${esc(formatPercent(r.percent))}</span></div>`).join('')}
    </section>`).join('');

  return `<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>
${fonts()}
:root{
  --W:${device.w}px; --H:${device.h}px; --s:1; --cols:1;
  --ink:255 255 255; --ink-a:1; --fill:20 20 24; --fill-a:.24;
  --edge-hi:255 255 255; --edge-hi-a:.5; --edge-lo-a:.1;
  --line-a:.2; --soft-a:.1; --shadow-a:.28; --blur:22px; --sat:1.5;
  --phrase-ink:255 255 255; --phrase-glow:0 0 0; --phrase-glow-a:0;
  --hair:.5px; --row:27px; --pad:18px; --cg:20px; --tw:${Math.round(device.w * 0.64)}px;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:var(--W);height:var(--H);overflow:hidden;background:#111}
body{position:relative;font-family:Inter,sans-serif;-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:${esc(bgPosition)}}
.stage{position:absolute;left:0;right:0;top:0;display:flex;flex-direction:column;align-items:center}

/* Стекло: размытый фон под ним, лёгкая заливка в тон фона, кромка-блик
   толщиной в волос и мягкая тень снизу. */
.glass{position:relative;width:var(--tw);border-radius:calc(26px*var(--s));
  padding:calc(15px*var(--s)) calc(var(--pad)*var(--s)) calc(13px*var(--s));
  background:linear-gradient(160deg,rgb(var(--fill)/calc(var(--fill-a)*.75)),rgb(var(--fill)/var(--fill-a)) 55%,rgb(var(--fill)/calc(var(--fill-a)*1.15)));
  -webkit-backdrop-filter:blur(var(--blur)) saturate(var(--sat));backdrop-filter:blur(var(--blur)) saturate(var(--sat));
  box-shadow:0 calc(18px*var(--s)) calc(44px*var(--s)) calc(-16px*var(--s)) rgb(0 0 0/var(--shadow-a))}
.glass::before{content:'';position:absolute;inset:0;border-radius:inherit;padding:.6px;pointer-events:none;
  background:linear-gradient(150deg,rgb(var(--edge-hi)/var(--edge-hi-a)),rgb(var(--edge-hi)/var(--edge-lo-a)) 35%,rgb(var(--edge-hi)/var(--edge-lo-a)) 70%,rgb(var(--edge-hi)/calc(var(--edge-hi-a)*.6)));
  mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);mask-composite:exclude}
.title{text-align:center;font-weight:500;font-size:calc(9.5px*var(--s));letter-spacing:.22em;text-transform:uppercase;
  color:rgb(var(--ink)/calc(var(--ink-a)*.66));padding-bottom:calc(11px*var(--s));
  border-bottom:var(--hair) solid rgb(var(--ink)/var(--line-a));margin-bottom:calc(11px*var(--s))}
.cols{display:flex;gap:calc(var(--cg)*var(--s))}
.col{flex:1 1 0;min-width:0}
.col+.col{border-left:var(--hair) solid rgb(var(--ink)/var(--line-a));padding-left:calc(var(--cg)*var(--s))}
.bank+.bank{border-top:var(--hair) solid rgb(var(--ink)/var(--line-a));margin-top:calc(10px*var(--s));padding-top:calc(11px*var(--s))}
.bh{display:flex;justify-content:space-between;align-items:baseline;gap:8px;
  font-weight:600;font-size:calc(9.5px*var(--s));letter-spacing:.16em;text-transform:uppercase;
  color:rgb(var(--ink)/calc(var(--ink-a)*.8));padding-bottom:calc(4px*var(--s))}
.bn{font-weight:500;letter-spacing:.06em;text-transform:none;font-size:calc(9.5px*var(--s))}
.row{position:relative;display:grid;grid-template-columns:auto 1fr auto;align-items:center;
  column-gap:calc(9px*var(--s));height:calc(var(--row)*var(--s))}
.row+.row::before{content:'';position:absolute;top:0;right:0;left:calc(24px*var(--s));
  border-top:var(--hair) solid rgb(var(--ink)/var(--soft-a))}
.ic{width:calc(15px*var(--s));height:calc(15px*var(--s));fill:none;stroke:rgb(var(--ink)/calc(var(--ink-a)*.86));
  stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.nm{font-size:calc(12.5px*var(--s));font-weight:400;color:rgb(var(--ink)/calc(var(--ink-a)*.92));
  white-space:nowrap;overflow:hidden;letter-spacing:-.005em}
.pc{font-size:calc(12.5px*var(--s));font-weight:500;color:rgb(var(--ink)/var(--ink-a));
  font-variant-numeric:tabular-nums;letter-spacing:.01em;padding-left:4px}
.phrase{margin-top:calc(18px*var(--s));max-width:78%;text-align:center;color:rgb(var(--phrase-ink));
  text-shadow:0 0 14px rgb(var(--phrase-glow)/var(--phrase-glow-a)),0 0 3px rgb(var(--phrase-glow)/calc(var(--phrase-glow-a)*.6))}
.phrase.serif{font-family:Cormorant,serif;font-style:italic;font-weight:500;font-size:calc(21px*var(--s));line-height:1.2;letter-spacing:.01em}
.phrase.sans{font-family:Inter,sans-serif;font-weight:400;font-size:calc(13px*var(--s));line-height:1.35;letter-spacing:.04em}

/* Замеры: текст прозрачен (тень фразы остаётся — она часть подложки),
   стекло и фраза на месте. */
html.m-text .t,html.m-text .title,html.m-text .phrase{color:transparent!important}
html.m-text .ic{stroke:transparent!important}
html.m-bare .glass,html.m-bare .phrase{visibility:hidden}

/* Предпросмотр экрана блокировки — только для проверки, в обои не идёт. */
.lockwrap{display:none}html.preview .lockwrap{display:block}
.lock{position:absolute;left:0;right:0;text-align:center;color:#fff;pointer-events:none;mix-blend-mode:normal}
.lock .d{top:0;font:600 17px/1 Inter;opacity:.85}
.lock .c{font:600 96px/1 Inter;letter-spacing:-.02em;opacity:.92}
.lock-bottom{position:absolute;bottom:34px;left:44px;right:44px;display:flex;justify-content:space-between}
.lock-bottom i{width:50px;height:50px;border-radius:50%;background:rgb(0 0 0/.28);backdrop-filter:blur(10px)}
.lock-bar{position:absolute;bottom:9px;left:50%;width:140px;height:5px;margin-left:-70px;border-radius:3px;background:#fff;opacity:.9}
</style></head><body>
<img class="bg" src="${bgDataUrl}" alt="">
<div class="stage" id="stage">
  <div class="glass" id="glass">
    ${title ? `<div class="title">${esc(title)}</div>` : ''}
    <div class="cols" id="cols"><div class="col">${banks}</div></div>
  </div>
  ${phrase ? `<p class="phrase ${phraseFont === 'sans' ? 'sans' : 'serif'}" id="phrase">${esc(phrase)}</p>` : ''}
</div>
<div class="lockwrap"><div class="lock" style="top:${Math.round(device.h * 0.085)}px"><div class="d">${esc(lockscreen.date)}</div><div class="c" style="margin-top:4px">${esc(lockscreen.time)}</div></div>
<div class="lock-bottom"><i></i><i></i></div><div class="lock-bar"></div></div>
</body></html>`;
}
