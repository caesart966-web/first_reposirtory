/* Разметка и стили обоев. Один файл на всё оформление: страница живёт
   ровно один кадр, разносить её по частям незачем.

   Все размеры записаны в пикселях макета 1080 и умножаются на --s.
   Поэтому те же обои собираются под 1440×3200 без единой правки цифр:
   меняется одно число, пропорции держатся. */

import { guessIcon, iconSvg } from './icons.mjs';

/* Объединение повторов. Внутри банка одинаковые категории схлопываются
   в одну (берётся больший процент), между банками категория остаётся
   там, где процент выше: две одинаковых строки подряд в таблице
   на четыре пункта — это не таблица, а список опечаток. */
export function mergeBanks(banks) {
  const notes = [];
  const key = (t) => t.toLowerCase().replace(/[её]/g, 'е').replace(/[^а-яa-z0-9]+/gi, ' ').trim();

  const cleaned = banks.map((b) => {
    const seen = new Map();
    for (const c of b.categories) {
      const k = key(c.title);
      const prev = seen.get(k);
      if (!prev) seen.set(k, { ...c });
      else {
        notes.push(`${b.name}: «${prev.title}» и «${c.title}» — одна категория, оставлен ${Math.max(prev.percent, c.percent)}%`);
        prev.percent = Math.max(prev.percent, c.percent);
      }
    }
    return { ...b, categories: [...seen.values()] };
  });

  const best = new Map();
  cleaned.forEach((b, bi) =>
    b.categories.forEach((c) => {
      const k = key(c.title);
      const prev = best.get(k);
      if (!prev || c.percent > prev.percent) best.set(k, { bi, percent: c.percent, title: c.title, bank: b.name });
    })
  );

  const out = cleaned.map((b, bi) => ({
    ...b,
    categories: b.categories.filter((c) => {
      const w = best.get(key(c.title));
      if (w.bi === bi) return true;
      notes.push(`«${c.title}» есть в обоих банках — оставлена у «${w.bank}» (${w.percent}% против ${c.percent}%)`);
      return false;
    }),
  }));

  return { banks: out.filter((b) => b.categories.length), notes };
}

const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

function bankHtml(bank) {
  const rows = bank.categories
    .map((c) => `
        <li class="row">
          <span class="row__ico">${iconSvg(c.icon || guessIcon(c.title))}</span>
          <span class="row__label">${esc(c.title)}</span>
          <span class="row__pct"><b>${esc(c.percent)}</b><i>%</i></span>
        </li>`)
    .join('');

  return `
    <section class="bank" data-brand="${esc(bank.brand)}">
      <header class="bank__head">
        <span class="bank__dot"></span>
        <h2 class="bank__name">${esc(bank.name)}</h2>
        <span class="bank__rule"></span>
      </header>
      <ul class="rows">${rows}</ul>
    </section>`;
}

export function buildHtml(cfg) {
  const { width, height } = cfg.size;
  const s = width / 1080;
  const px = (n) => `calc(${n} * var(--s))`;

  return `<!doctype html>
<meta charset="utf-8">
<title>Обои с кэшбэком</title>
<style>
/* Inter — рубленый с широким диапазоном насыщенности: тонкая подпись
   и плотный процент берутся из одного семейства, поэтому таблица
   выглядит набранной, а не собранной из разных шрифтов.
   Golos подставляется только там, где у Inter нет знака (₽). */
@font-face { font-family: Inter; font-style: normal; font-weight: 100 900;
  src: url("../fonts/inter-cyrillic.woff2") format("woff2");
  unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; }
@font-face { font-family: Inter; font-style: normal; font-weight: 100 900;
  src: url("../fonts/inter-latin.woff2") format("woff2");
  unicode-range: U+0000-00FF, U+2013-2014, U+2018-201D, U+2026, U+2212; }
@font-face { font-family: Golos; font-style: normal; font-weight: 400 900;
  src: url("../fonts/golos-cyrillic.woff2") format("woff2-variations");
  unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; }
@font-face { font-family: Golos; font-style: normal; font-weight: 400 900;
  src: url("../fonts/golos-latin.woff2") format("woff2-variations");
  unicode-range: U+0000-00FF, U+20BD, U+2116; }

:root {
  --s: ${s};
  --icon-stroke: 1.55;

  /* Значения ниже — только запасные. Настоящие ставит adapt.js,
     измерив пиксели фона под карточкой. */
  --glass: rgba(10,13,18,.38);
  --ink: #fff;
  --ink-muted: rgba(255,255,255,.7);
  --hairline: rgba(255,255,255,.16);
  --hairline-soft: rgba(255,255,255,.09);
  --edge-top: rgba(255,255,255,.22);
  --card-shadow: 0 30px 80px rgba(0,0,0,.45);
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: ${width}px; height: ${height}px; overflow: hidden; }
body {
  font-family: Inter, Golos, system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  text-rendering: geometricPrecision;
  background: #06080d;
}

#bg { position: fixed; inset: 0; width: 100%; height: 100%; object-fit: cover; }

.stage {
  position: relative; width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  transform: translateY(${px(`${cfg.card.offsetY || 0}px`)});
}

.card {
  width: ${px(`${cfg.card.width}px`)};
  padding: ${px('46px')} ${px('42px')} ${px('38px')};
  border-radius: ${px('44px')};
  background: var(--glass);
  -webkit-backdrop-filter: blur(${px('30px')}) saturate(1.4);
  backdrop-filter: blur(${px('30px')}) saturate(1.4);
  border: 1px solid var(--hairline);
  box-shadow: var(--card-shadow), inset 0 1px 0 var(--edge-top);
  color: var(--ink);
}

.caption {
  font-size: ${px('21px')};
  font-weight: 500;
  letter-spacing: .26em;
  text-transform: uppercase;
  color: var(--ink-muted);
  padding-bottom: ${px('26px')};
  border-bottom: 1px solid var(--hairline-soft);
}

.bank { padding-top: ${px('36px')}; }

/* Шапка банка: точка, имя, линейка до правого края — всё фирменным цветом.
   Цвет ставится сюда и только сюда: покрасить в него ещё и проценты
   значило бы уравнять банк и его условия, а это разные вещи. */
.bank__head {
  display: flex; align-items: center; gap: ${px('14px')};
  padding-bottom: ${px('16px')};
}
.bank__dot {
  width: ${px('10px')}; height: ${px('10px')};
  border-radius: 50%; background: var(--brand); flex: none;
}
.bank__name {
  font-size: ${px('30px')}; font-weight: 600; letter-spacing: .005em;
  color: var(--brand); white-space: nowrap;
}
.bank__rule { flex: 1; height: 1px; background: var(--brand); opacity: .34; }

.rows { list-style: none; }
.row {
  display: flex; align-items: center; gap: ${px('22px')};
  padding: ${px('17px')} 0;
}
.row + .row { border-top: 1px solid var(--hairline-soft); }

.row__ico { flex: none; width: ${px('34px')}; height: ${px('34px')}; opacity: .92; }
.row__ico svg { width: 100%; height: 100%; display: block; }

.row__label {
  flex: 1; font-size: ${px('32px')}; font-weight: 400; letter-spacing: .002em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* Проценты — колонка постоянной ширины с табличными цифрами: без этого
   «1%» и «10%» разъезжаются, и правый край таблицы перестаёт быть краем. */
.row__pct {
  flex: none; min-width: ${px('86px')}; text-align: right;
  font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1;
  font-size: ${px('32px')};
}
.row__pct b { font-weight: 600; }
.row__pct i { font-style: normal; font-weight: 400; font-size: .82em;
  color: var(--ink-muted); padding-left: ${px('2px')}; }
</style>

<img id="bg" alt="">
<div class="stage">
  <div class="card">
    ${cfg.caption ? `<div class="caption">${esc(cfg.caption)}</div>` : ''}
    <div class="banks">${cfg.banks.map(bankHtml).join('')}</div>
  </div>
</div>`;
}
