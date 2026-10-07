// Отрисовка схем в SVG: BPMN 2.0 (пулы, дорожки, задачи, события, шлюзы,
// потоки управления и сообщений), оргструктура и цепочка процессов в духе
// ARIS Express, контекстная диаграмма IDEF0, столбчатая диаграмма.
// Работает в браузере: перенос строк меряется настоящим шрифтом через canvas.
(function () {
  const FONT = "'Liberation Sans', Arial, sans-serif";
  const C = {
    task: '#E4F2DA', taskS: '#3E7A2B',
    gw: '#FFF4C7', gwS: '#9A7400',
    start: '#2E7D32', end: '#C0392B', inter: '#1F5FA8',
    laneH: '#EDF1F5', laneS: '#55606B',
    ext: '#F2F4F7', extS: '#55606B',
    text: '#1B1F23', muted: '#55606B',
    flow: '#22262A', msg: '#4A5560',
    prob: '#C0392B', impr: '#1F5FA8',
  };
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const ctx = document.createElement('canvas').getContext('2d');
  function measure(t, size, weight = 'normal', style = 'normal') {
    ctx.font = `${style} ${weight} ${size}px ${FONT}`;
    return ctx.measureText(t).width;
  }
  // Неразрывные пробелы: число не отрывается от «дн.», «%», «чел.»; «части 2 (А)» — одной строкой.
  const nb = (t) => String(t)
    .replace(/(\d) (?=(дн\.|%|чел\.|ч\b))/g, '$1\u00a0')
    .replace(/(≈|≤) (?=\d)/g, '$1')
    .replace(/части (\d) \(/g, 'части\u00a0$1\u00a0(');
  function wrap(text, maxW, size, weight, style) {
    const out = [];
    for (const para of nb(text).split('\n')) {
      // слово шире строки переносим по дефису
      const toks = [];
      for (const w of para.split(' ')) {
        if (w.includes('-') && measure(w, size, weight, style) > maxW) {
          const parts = w.split(/(?<=-)/);
          parts.forEach((p, i) => toks.push({ t: p, sp: i === 0 }));
        } else toks.push({ t: w, sp: true });
      }
      let line = '';
      for (const { t: w, sp } of toks) {
        const t = line ? line + (sp ? ' ' : '') + w : w;
        if (!line || measure(t, size, weight, style) <= maxW) line = t;
        else { out.push(line); line = w; }
      }
      out.push(line);
    }
    return out;
  }
  // Текстовый блок. valign: middle — y центр; top — y верхний край; bottom — y нижний край.
  function tb(x, y, text, o = {}) {
    const size = o.size || 12.5, weight = o.weight || 'normal', style = o.italic ? 'italic' : 'normal';
    const lines = o.nowrap ? String(text).split('\n') : wrap(text, o.maxW || 108, size, weight, style);
    const LH = size * (o.lh || 1.18);
    const va = o.valign || 'middle';
    let y0;
    if (va === 'middle') y0 = y - ((lines.length - 1) * LH) / 2 + size * 0.36;
    else if (va === 'top') y0 = y + size * 0.82;
    else y0 = y - (lines.length - 1) * LH - size * 0.24;
    const anchor = o.anchor || 'middle';
    const halo = o.halo ? ` stroke="#fff" stroke-width="${o.halo}" stroke-linejoin="round" paint-order="stroke"` : '';
    const tsp = lines.map((l, i) => `<tspan x="${x.toFixed(1)}" y="${(y0 + i * LH).toFixed(1)}">${esc(l)}</tspan>`).join('');
    const w = Math.max(...lines.map((l) => measure(l, size, weight, style)));
    return {
      svg: `<text font-family="${FONT}" font-size="${size}" font-weight="${weight}"${o.italic ? ' font-style="italic"' : ''} fill="${o.fill || C.text}" text-anchor="${anchor}"${halo}>${tsp}</text>`,
      lines, h: lines.length * LH, w,
    };
  }
  // Повёрнутый на -90° текст (заголовки пулов и дорожек).
  function vtext(cx, cy, text, o = {}) {
    const size = o.size || 12.5, lines = String(text).split('\n'), LH = size * 1.15;
    const y0 = -((lines.length - 1) * LH) / 2 + size * 0.36;
    const tsp = lines.map((l, i) => `<tspan x="0" y="${(y0 + i * LH).toFixed(1)}">${esc(l)}</tspan>`).join('');
    return `<text transform="translate(${cx.toFixed(1)},${cy.toFixed(1)}) rotate(-90)" font-family="${FONT}" font-size="${size}" font-weight="${o.weight || 'bold'}" fill="${o.fill || C.text}" text-anchor="middle">${tsp}</text>`;
  }
  const defs = `<defs>
    <marker id="seq" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0,0.8 L10,5 L0,9.2 z" fill="${C.flow}"/></marker>
    <marker id="msgEnd" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="10" markerHeight="10" orient="auto" markerUnits="userSpaceOnUse"><path d="M0.8,1 L9.5,5 L0.8,9 z" fill="#fff" stroke="${C.msg}" stroke-width="1.2"/></marker>
    <marker id="msgStart" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="9" markerHeight="9" orient="auto" markerUnits="userSpaceOnUse"><circle cx="5" cy="5" r="3.8" fill="#fff" stroke="${C.msg}" stroke-width="1.2"/></marker>
    <marker id="arr" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="10" markerHeight="10" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0.8 L10,5 L0,9.2 z" fill="${C.flow}"/></marker>
  </defs>`;
  const wrapSvg = (w, h, body) =>
    `<svg xmlns="http://www.w3.org/2000/svg" width="${Math.ceil(w)}" height="${Math.ceil(h)}" viewBox="0 0 ${Math.ceil(w)} ${Math.ceil(h)}">${defs}<rect x="0" y="0" width="${Math.ceil(w)}" height="${Math.ceil(h)}" fill="#fff"/>${body}</svg>`;

  // ---------- значки ----------
  function gear(x, y) {
    let s = `<g stroke="${C.taskS}" fill="none">`;
    for (let i = 0; i < 8; i++) {
      const a = (i * Math.PI) / 4;
      s += `<line x1="${(x + 4.6 * Math.cos(a)).toFixed(2)}" y1="${(y + 4.6 * Math.sin(a)).toFixed(2)}" x2="${(x + 7.4 * Math.cos(a)).toFixed(2)}" y2="${(y + 7.4 * Math.sin(a)).toFixed(2)}" stroke-width="2.4"/>`;
    }
    return s + `<circle cx="${x}" cy="${y}" r="5" stroke-width="1.6" fill="#fff"/><circle cx="${x}" cy="${y}" r="1.8" stroke-width="1.2"/></g>`;
  }
  function envelope(x, y, filled) {
    return `<g><rect x="${x - 7}" y="${y - 5}" width="14" height="10" fill="${filled ? C.inter : '#fff'}" stroke="${C.inter}" stroke-width="1.2"/><path d="M${x - 7},${y - 5} L${x},${y + 0.6} L${x + 7},${y - 5}" fill="none" stroke="${filled ? '#fff' : C.inter}" stroke-width="1.2"/></g>`;
  }
  function linkArrow(x, y, filled) {
    return `<path d="M${x - 7},${y - 3.5} L${x + 1},${y - 3.5} L${x + 1},${y - 7.5} L${x + 8},${y} L${x + 1},${y + 7.5} L${x + 1},${y + 3.5} L${x - 7},${y + 3.5} z" fill="${filled ? C.inter : '#fff'}" stroke="${C.inter}" stroke-width="1.2"/>`;
  }
  function clock(x, y) {
    let s = `<circle cx="${x}" cy="${y}" r="11.5" fill="#fff" stroke="${C.start}" stroke-width="1.3"/>`;
    for (let i = 0; i < 12; i++) {
      const a = (i * Math.PI) / 6;
      s += `<line x1="${(x + 9 * Math.cos(a)).toFixed(2)}" y1="${(y + 9 * Math.sin(a)).toFixed(2)}" x2="${(x + 11 * Math.cos(a)).toFixed(2)}" y2="${(y + 11 * Math.sin(a)).toFixed(2)}" stroke="${C.start}" stroke-width="1"/>`;
    }
    return s + `<path d="M${x},${y - 7.5} L${x},${y} L${x + 5.5},${y + 2.5}" fill="none" stroke="${C.start}" stroke-width="1.4"/>`;
  }
  function badge(x, y, t, color) {
    return `<g><circle cx="${x}" cy="${y}" r="12" fill="${color}" stroke="#fff" stroke-width="1.5"/>${tb(x, y, t, { size: 9.5, weight: 'bold', fill: '#fff', nowrap: true }).svg}</g>`;
  }
  function durTag(xr, y, t) {
    const w = measure(t, 10, 'normal') + 10;
    return `<g><rect x="${(xr - w).toFixed(1)}" y="${(y - 8).toFixed(1)}" width="${w.toFixed(1)}" height="16" rx="8" fill="#fff" stroke="${C.muted}" stroke-width="0.9"/>${tb(xr - w / 2, y, t, { size: 10, fill: C.muted, nowrap: true }).svg}</g>`;
  }

  // ---------- элементы BPMN ----------
  const isGw = (n) => n.type === 'xor' || n.type === 'and';
  const isEv = (n) => ['start', 'timer', 'end', 'msg', 'linkIn', 'linkOut'].includes(n.type);
  const SLOT = { task: 142, svc: 142, sub: 142, gw: 100, ev: 104 };
  const slotOf = (n) => n.slot || (isGw(n) ? SLOT.gw : isEv(n) ? SLOT.ev : SLOT.task);

  function sizeNode(n) {
    if (isGw(n)) { n.w = n.h = 48; return; }
    if (isEv(n)) { n.w = n.h = 36; return; }
    n.w = n.boxW || 120;
    const t = tb(0, 0, n.label, { size: 12.2, maxW: n.w - 12 });
    n.h = Math.max(68, t.h + 20 + (n.type === 'svc' ? 8 : 0) + (n.type === 'sub' ? 10 : 0));
  }

  function drawNode(n) {
    const { x, y } = n;
    let s = '';
    if (n.type === 'task' || n.type === 'svc' || n.type === 'sub') {
      s += `<rect x="${x - n.w / 2}" y="${y - n.h / 2}" width="${n.w}" height="${n.h}" rx="10" fill="${C.task}" stroke="${C.taskS}" stroke-width="${n.hl ? 2.6 : 1.4}"/>`;
      const shift = n.type === 'svc' ? 4 : n.type === 'sub' ? -5 : 0;
      s += tb(x, y + shift, n.label, { size: 12.2, maxW: n.w - 12 }).svg;
      if (n.type === 'svc') s += gear(x - n.w / 2 + 12, y - n.h / 2 + 12);
      if (n.type === 'sub') s += `<rect x="${x - 6}" y="${y + n.h / 2 - 15}" width="12" height="12" fill="#fff" stroke="${C.taskS}" stroke-width="1.1"/><path d="M${x - 3.5},${y + n.h / 2 - 9} h7 M${x},${y + n.h / 2 - 12.5} v7" stroke="${C.taskS}" stroke-width="1.3"/>`;
      if (n.dur) s += durTag(x + n.w / 2 - 3, y + n.h / 2, n.dur);
      if (n.badge) s += badge(x + n.w / 2 - 3, y - n.h / 2 + 2, n.badge, n.badge.startsWith('П') ? C.prob : C.impr);
    } else if (isGw(n)) {
      s += `<path d="M${x},${y - 24} L${x + 24},${y} L${x},${y + 24} L${x - 24},${y} z" fill="${C.gw}" stroke="${C.gwS}" stroke-width="1.5"/>`;
      if (n.type === 'xor') s += `<path d="M${x - 7.5},${y - 7.5} L${x + 7.5},${y + 7.5} M${x + 7.5},${y - 7.5} L${x - 7.5},${y + 7.5}" stroke="${C.text}" stroke-width="3.2" stroke-linecap="round"/>`;
      else s += `<path d="M${x - 10},${y} L${x + 10},${y} M${x},${y - 10} L${x},${y + 10}" stroke="${C.text}" stroke-width="3.4" stroke-linecap="round"/>`;
      if (n.label) {
        const below = n.lpos === 'bottom';
        s += tb(x + (n.ldx || 0), below ? y + 29 : y - 29, n.label, { size: 11.5, maxW: n.lw || 112, valign: below ? 'top' : 'bottom', fill: C.text, halo: 3 }).svg;
      }
    } else {
      const r = 18;
      if (n.type === 'start') s += `<circle cx="${x}" cy="${y}" r="${r}" fill="#fff" stroke="${C.start}" stroke-width="2"/>`;
      if (n.type === 'timer') s += `<circle cx="${x}" cy="${y}" r="${r}" fill="#fff" stroke="${C.start}" stroke-width="2"/>` + clock(x, y);
      if (n.type === 'end') s += `<circle cx="${x}" cy="${y}" r="${r}" fill="#fff" stroke="${C.end}" stroke-width="4"/>`;
      if (n.type === 'msg' || n.type === 'linkIn' || n.type === 'linkOut') {
        s += `<circle cx="${x}" cy="${y}" r="${r}" fill="#fff" stroke="${C.inter}" stroke-width="1.5"/><circle cx="${x}" cy="${y}" r="${r - 3.6}" fill="none" stroke="${C.inter}" stroke-width="1.5"/>`;
        if (n.type === 'msg') s += envelope(x, y, false);
        else s += linkArrow(x - 0.5, y, n.type === 'linkOut');
      }
      if (n.label) {
        const above = n.lpos === 'top';
        s += tb(x, above ? y - 23 : y + 23, n.label, { size: 11.3, maxW: n.lw || 112, valign: above ? 'bottom' : 'top', halo: 3 }).svg;
      }
    }
    return s;
  }

  function anchor(n, side, off = 0) {
    if (side === 'L') return [n.x - n.w / 2, n.y + off];
    if (side === 'R') return [n.x + n.w / 2, n.y + off];
    if (side === 'T') return [n.x + off, n.y - n.h / 2];
    return [n.x + off, n.y + n.h / 2];
  }

  function bpmn(def) {
    const nodes = def.nodes.map((n) => ({ ...n }));
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    nodes.forEach(sizeNode);
    const ncol = Math.max(...nodes.map((n) => n.col)) + 1;
    const colW = Array.from({ length: ncol }, (_, c) => (def.colW && def.colW[c]) || Math.max(60, ...nodes.filter((n) => n.col === c).map(slotOf)));
    const POOL_L = 10, POOL_HDR = 30, LANE_HDR = 48, PAD = 12;
    const left = POOL_L + POOL_HDR + LANE_HDR + PAD;
    const colLeft = (c) => left + colW.slice(0, c).reduce((a, b) => a + b, 0);
    const colX = (c) => colLeft(c) + colW[c] / 2;
    const W = left + colW.reduce((a, b) => a + b, 0) + 14 + POOL_L;
    const EXT_H = 46, GAP = 58;
    let y = 10;
    const top = def.top || [], bot = def.bottom || [];
    const pools = [];
    if (top.length) { for (const p of top) pools.push({ ...p, where: 'top', y, h: EXT_H }); y += EXT_H + GAP; }
    const mainTop = y;
    const lanes = def.lanes.map((l) => { const o = { ...l, y, h: l.h || 140 }; o.yc = y + o.h / 2; y += o.h; return o; });
    const laneById = Object.fromEntries(lanes.map((l) => [l.id, l]));
    const mainBot = y;
    if (bot.length) { y += GAP; for (const p of bot) pools.push({ ...p, where: 'bot', y, h: EXT_H }); y += EXT_H; }
    const H = y + 10;
    const last = ncol - 1;
    for (const p of pools) {
      p.x1 = p.from === 0 ? POOL_L : colLeft(p.from) + 2;
      p.x2 = (p.to >= last ? W - POOL_L : colLeft(p.to + 1) - 2);
    }
    for (const n of nodes) { n.x = colX(n.col) + (n.dx || 0); n.y = laneById[n.lane].yc + (n.dy || 0); }

    const P = {
      ...byId,
      laneTop: (id) => laneById[id].y, laneBot: (id) => laneById[id].y + laneById[id].h,
      colX, colLeft,
    };

    let bg = '', fl = '', ms = '', nd = '', lb = '';
    // пулы и дорожки
    bg += `<rect x="${POOL_L}" y="${mainTop}" width="${W - 2 * POOL_L}" height="${mainBot - mainTop}" fill="#fff" stroke="${C.laneS}" stroke-width="1.4"/>`;
    bg += `<rect x="${POOL_L}" y="${mainTop}" width="${POOL_HDR}" height="${mainBot - mainTop}" fill="${C.laneH}" stroke="${C.laneS}" stroke-width="1.4"/>`;
    bg += vtext(POOL_L + POOL_HDR / 2, (mainTop + mainBot) / 2, def.pool, { size: 13 });
    for (const l of lanes) {
      bg += `<rect x="${POOL_L + POOL_HDR}" y="${l.y}" width="${LANE_HDR}" height="${l.h}" fill="${C.laneH}" stroke="${C.laneS}" stroke-width="1"/>`;
      bg += `<line x1="${POOL_L + POOL_HDR}" y1="${l.y}" x2="${W - POOL_L}" y2="${l.y}" stroke="${C.laneS}" stroke-width="1"/>`;
      bg += vtext(POOL_L + POOL_HDR + LANE_HDR / 2, l.yc, l.name, { size: 11.8 });
    }
    for (const p of pools) {
      bg += `<rect x="${p.x1}" y="${p.y}" width="${p.x2 - p.x1}" height="${p.h}" fill="${C.ext}" stroke="${C.extS}" stroke-width="1.4"/>`;
      bg += tb((p.x1 + p.x2) / 2, p.y + p.h / 2, p.name, { size: 12.5, weight: 'bold', maxW: p.x2 - p.x1 - 12 }).svg;
    }
    // потоки управления
    for (const f of def.flows) {
      const [a, b, o = {}] = f;
      const A = byId[a], B = byId[b];
      if (!A || !B) throw new Error('flow ' + a + '→' + b);
      let fa = o.fa, ta = o.ta;
      const dy = B.y - A.y;
      if (!fa && !ta) {
        if (Math.abs(dy) < 1) { fa = 'R'; ta = 'L'; }
        else if (isGw(A) && B.x > A.x) { fa = dy < 0 ? 'T' : 'B'; ta = 'L'; }
        else if (isGw(B) && B.x > A.x) { fa = 'R'; ta = dy < 0 ? 'B' : 'T'; }
        else { fa = 'R'; ta = 'L'; }
      }
      fa = fa || 'R'; ta = ta || 'L';
      const p1 = anchor(A, fa, o.fdx || 0), p2 = anchor(B, ta, o.tdx || 0);
      let mid = [];
      if (o.via) mid = o.via(P);
      else if ('LR'.includes(fa) && 'LR'.includes(ta)) {
        if (Math.abs(p1[1] - p2[1]) > 0.5) { const mx = typeof o.mx === 'function' ? o.mx(P) : o.mx != null ? o.mx : (p1[0] + p2[0]) / 2; mid = [[mx, p1[1]], [mx, p2[1]]]; }
      } else if ('TB'.includes(fa) && 'LR'.includes(ta)) mid = [[p1[0], p2[1]]];
      else if ('LR'.includes(fa) && 'TB'.includes(ta)) mid = [[p2[0], p1[1]]];
      else if (Math.abs(p1[0] - p2[0]) > 0.5) { const my = o.my != null ? o.my : (p1[1] + p2[1]) / 2; mid = [[p1[0], my], [p2[0], my]]; }
      const pts = [p1, ...mid, p2];
      fl += `<polyline points="${pts.map((p) => p.map((v) => v.toFixed(1)).join(',')).join(' ')}" fill="none" stroke="${C.flow}" stroke-width="1.5" stroke-linejoin="round" marker-end="url(#seq)"/>`;
      if (o.label) {
        const [dx, dyl] = o.lp || ('TB'.includes(fa) ? [7, fa === 'T' ? -12 : 14] : [6, -10]);
        lb += tb(p1[0] + dx, p1[1] + dyl, o.label, { size: 11, anchor: o.la || 'start', nowrap: true, halo: 3.5, fill: '#333' }).svg;
      }
    }
    // потоки сообщений
    const poolByName = (nm) => pools.find((p) => p.name === nm || p.key === nm);
    for (const m of def.msgs || []) {
      const nodeEnd = byId[m.node];
      const pool = poolByName(m.pool);
      if (!nodeEnd || !pool) throw new Error('msg ' + m.node + ' ' + m.pool);
      const x = nodeEnd.x + (m.dx || 0);
      const halfH = isEv(nodeEnd) ? Math.sqrt(Math.max(0, 18 * 18 - (m.dx || 0) ** 2)) : nodeEnd.h / 2;
      const nodeY = pool.where === 'top' ? nodeEnd.y - halfH : nodeEnd.y + halfH;
      const poolY = pool.where === 'top' ? pool.y + pool.h : pool.y;
      const out = m.dir !== 'in';
      const [y1, y2] = out ? [nodeY, poolY] : [poolY, nodeY];
      ms += `<line x1="${x}" y1="${y1}" x2="${x}" y2="${y2}" stroke="${C.msg}" stroke-width="1.3" stroke-dasharray="6 4" marker-start="url(#msgStart)" marker-end="url(#msgEnd)"/>`;
      if (m.label) {
        const gy = (pool.where === 'top' ? pool.y + pool.h + GAP / 2 : pool.y - GAP / 2) + (m.ly || 0);
        const side = m.side || ((m.dx || 0) < 0 ? 'l' : 'r');
        lb += tb(side === 'r' ? x + 6 : x - 6, gy, m.label, { size: 10.5, italic: true, maxW: m.lw || 132, anchor: side === 'r' ? 'start' : 'end', fill: C.msg, halo: 3 }).svg;
      }
    }
    for (const n of nodes) nd += drawNode(n);
    return { svg: wrapSvg(W, H, bg + fl + ms + nd + lb), w: W, h: H };
  }

  // ---------- оргструктура (ARIS Organizational chart) ----------
  function personGlyph(x, y) {
    return `<g fill="none" stroke="#8A6D00" stroke-width="1.3"><circle cx="${x}" cy="${y - 4}" r="3.4"/><path d="M${x - 6},${y + 7} Q${x - 6},${y} ${x},${y} Q${x + 6},${y} ${x + 6},${y + 7}"/></g>`;
  }
  function orgBox(b) {
    const fill = '#FFF3B5', stroke = b.hl ? C.impr : '#A88400';
    const sw = b.hl ? 3 : 1.4;
    let s = '';
    if (b.kind === 'pos') {
      s += `<rect x="${b.x - b.w / 2}" y="${b.y - b.h / 2}" width="${b.w}" height="${b.h}" rx="3" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
      s += personGlyph(b.x - b.w / 2 + 14, b.y);
      s += tb(b.x + 8, b.y, b.label, { size: b.size || 14.5, maxW: b.w - 36, weight: b.bold ? 'bold' : 'normal' }).svg;
    } else {
      s += `<rect x="${b.x - b.w / 2}" y="${b.y - b.h / 2}" width="${b.w}" height="${b.h}" rx="${b.h / 2}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
      s += `<line x1="${b.x - b.w / 2 + 16}" y1="${b.y - b.h / 2 + 5}" x2="${b.x - b.w / 2 + 16}" y2="${b.y + b.h / 2 - 5}" stroke="#A88400" stroke-width="1.2"/>`;
      s += tb(b.x + 6, b.y, b.label, { size: b.size || 14.5, maxW: b.w - 38, weight: b.bold ? 'bold' : 'normal' }).svg;
    }
    return s;
  }

  // ---------- шевроны VAD ----------
  function chevron(x, y, w, h, fill, stroke, sw, first) {
    const d = 18;
    const pts = first
      ? [[x, y], [x + w - d, y], [x + w, y + h / 2], [x + w - d, y + h], [x, y + h]]
      : [[x, y], [x + w - d, y], [x + w, y + h / 2], [x + w - d, y + h], [x, y + h], [x + d, y + h / 2]];
    return `<polygon points="${pts.map((p) => p.join(',')).join(' ')}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>`;
  }

  window.D = { C, FONT, tb, vtext, wrapSvg, bpmn, orgBox, chevron, measure, drawNode, sizeNode, badge, durTag, esc };
})();
