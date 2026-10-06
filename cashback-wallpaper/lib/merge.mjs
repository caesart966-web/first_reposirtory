// Сводит данные со скринов в разделы таблицы.
//
// Дубли склеиваются в три шага:
// 1. один банк на нескольких скринах (или под разными подписями) — один раздел;
// 2. одна категория внутри банка — одна строка («Кафе» + «Рестораны»,
//    повтор на двух скринах); если проценты разные, остаётся больший;
// 3. одна категория у разных банков — по `duplicates`:
//    "keep" — остаётся у каждого банка, с одинаковым названием и иконкой;
//    "best" — только у банка, где процент выше (при равенстве — у обоих).
import { resolveCategory } from './categories.mjs';
import { resolveBank } from './banks.mjs';

export function parsePercent(v) {
  if (typeof v === 'number') return v;
  const m = String(v).replace(',', '.').match(/-?\d+(\.\d+)?/);
  if (!m) throw new Error(`Не понял процент: «${v}»`);
  return Number(m[0]);
}

export function formatPercent(p) {
  return `${String(p).replace('.', ',')}%`;
}

export function buildSections(cfg) {
  const notes = [];
  const banks = new Map();
  for (const b of cfg.banks) {
    const name = resolveBank(b.name);
    if (!banks.has(name)) banks.set(name, { name, note: b.note ?? null, rows: new Map() });
    else notes.push(`Банк «${name}» встретился дважды — разделы склеены`);
    const bank = banks.get(name);
    for (const item of b.categories) {
      const raw = typeof item === 'string' ? item : item.name;
      const percent = parsePercent(item.percent);
      const cat = resolveCategory(raw, { icon: item.icon, label: item.label });
      if (!cat.known) notes.push(`Нет иконки для «${raw}» — стоит запасная (${cat.icon})`);
      const prev = bank.rows.get(cat.key);
      if (prev) {
        notes.push(`${name}: «${raw}» склеено с «${prev.sources.join('», «')}»` +
          (prev.percent !== percent ? ` (было ${prev.percent}% и ${percent}%, оставлено ${Math.max(prev.percent, percent)}%)` : ''));
        prev.percent = Math.max(prev.percent, percent);
        prev.sources.push(raw);
      } else {
        bank.rows.set(cat.key, { ...cat, percent, sources: [raw] });
      }
    }
  }

  const sections = [...banks.values()].map((b) => ({ name: b.name, note: b.note, rows: [...b.rows.values()] }));

  // Одна категория у нескольких банков.
  const owners = new Map();
  for (const s of sections) for (const r of s.rows) {
    if (!owners.has(r.key)) owners.set(r.key, []);
    owners.get(r.key).push({ s, r });
  }
  const mode = cfg.duplicates ?? 'keep';
  for (const [, list] of owners) {
    if (list.length < 2) continue;
    const label = list.map(({ s, r }) => `${s.name} ${r.percent}%`).join(', ');
    if (mode === 'best') {
      const max = Math.max(...list.map(({ r }) => r.percent));
      for (const { s, r } of list) if (r.percent < max) s.rows = s.rows.filter((x) => x !== r);
      notes.push(`«${list[0].r.name}» у нескольких банков (${label}) — оставлено, где ${max}%`);
    } else {
      notes.push(`«${list[0].r.name}» у нескольких банков (${label}) — оставлено у всех`);
    }
  }

  if ((cfg.sort ?? 'percent') === 'percent') {
    for (const s of sections) s.rows.sort((a, b) => b.percent - a.percent);
  }
  return { sections: sections.filter((s) => s.rows.length), notes };
}
