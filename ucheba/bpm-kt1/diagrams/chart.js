// Столбчатая диаграмма: длительность этапов AS-IS и TO-BE (данные — data.json).
(function () {
  const { tb, wrapSvg } = window.D;
  const INK = '#1B1F23', INK2 = '#52514E', GRID = '#E4E4E1';
  const ASIS = '#EB6834', TOBE = '#2A78D6';
  window.DIAGRAMS.chart = () => {
    const st = window.DATA.stages;
    const sum = (a) => Math.round(a.reduce((s, [, v]) => s + v, 0) * 10) / 10;
    const W = 1120, x0 = 370, x1 = 1060, top = 64, rowH = 48, barH = 15, gap = 2;
    const max = 50, sx = (v) => x0 + ((x1 - x0) * v) / max;
    const H = top + st.length * rowH + 44;
    const fmt = (v) => String(v).replace('.', ',');
    let s = '';
    // легенда
    s += `<rect x="${x0}" y="18" width="14" height="14" rx="3" fill="${ASIS}"/>` + tb(x0 + 20, 25, 'AS-IS (как есть)', { size: 15, anchor: 'start', nowrap: true, fill: INK }).svg;
    s += `<rect x="${x0 + 220}" y="18" width="14" height="14" rx="3" fill="${TOBE}"/>` + tb(x0 + 240, 25, 'TO-BE (как будет)', { size: 15, anchor: 'start', nowrap: true, fill: INK }).svg;
    s += tb(20, 25, 'Этап процесса', { size: 14.5, anchor: 'start', nowrap: true, fill: INK2, weight: 'bold' }).svg;
    // сетка и ось
    for (let v = 0; v <= max; v += 10) {
      s += `<line x1="${sx(v)}" y1="${top - 10}" x2="${sx(v)}" y2="${top + st.length * rowH}" stroke="${GRID}" stroke-width="1"/>`;
      s += tb(sx(v), top + st.length * rowH + 17, String(v), { size: 14, nowrap: true, fill: INK2 }).svg;
    }
    s += tb((x0 + x1) / 2, top + st.length * rowH + 36, 'календарных дней', { size: 14, nowrap: true, fill: INK2 }).svg;
    const bar = (y, v, color) => {
      const w = Math.max(3, sx(v) - x0);
      const r = Math.min(4, w / 2);
      return `<path d="M${x0},${y} h${w - r} a${r},${r} 0 0 1 ${r},${r} v${barH - 2 * r} a${r},${r} 0 0 1 -${r},${r} h-${w - r} z" fill="${color}"/>` +
        tb(x0 + w + 6, y + barH / 2, fmt(v), { size: 13.5, anchor: 'start', nowrap: true, fill: INK }).svg;
    };
    st.forEach((d, i) => {
      const y = top + i * rowH;
      const fixed = window.DATA.fixedStages.includes(d.n);
      s += tb(20, y + rowH / 2 - 2, `${d.n}. ${d.name}`, { size: 14.5, anchor: 'start', maxW: 330, fill: fixed ? INK2 : INK }).svg;
      const yc = y + rowH / 2 - barH - gap / 2 - 2;
      s += bar(yc, sum(d.asis), ASIS);
      s += bar(yc + barH + gap, sum(d.tobe), TOBE);
    });
    s += `<line x1="${x0}" y1="${top - 10}" x2="${x0}" y2="${top + st.length * rowH}" stroke="#8A8A86" stroke-width="1"/>`;
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };
})();
