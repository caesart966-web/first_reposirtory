// Отрисовка схем в SVG в стиле ARIS Express: объемные фигуры с градиентом,
// бликом и тенью, белые значки в левом верхнем углу, жирный шрифт, тонкие
// линии со скругленными углами и открытыми стрелками.
// Что рисует: BPMN 2.0 (пулы, дорожки, задачи, события, шлюзы, потоки управления
// и сообщений), оргструктуру, цепочки процессов (VAD), контекстную диаграмму IDEF0.
// Работает в браузере: перенос строк меряется настоящим шрифтом через canvas.
(function () {
  // Шрифт фигур в ARIS Express похож на Tahoma Bold; ближайший из доступных — DejaVu Sans.
  const FONT = "'DejaVu Sans', Tahoma, Verdana, sans-serif";
  const C = {
    text: '#000000', muted: '#4A4F55',
    flow: '#333333', msg: '#555555',
    laneS: '#6F7A82',
    prob: '#C0141B', impr: '#1F5FA8',
    // для совместимости со старыми вызовами
    taskS: '#46A010', ext: '#E9EDEF', extS: '#7E888F', inter: '#C46400', start: '#2F7F0E', end: '#8E140C',
  };
  // Цвета фигур ARIS Express: верх и низ градиента, обводка.
  const KIND = {
    func: { top: '#73EC2E', bot: '#CDF900', edge: '#46A010' }, // функция, задача, процесс VAD
    event: { top: '#FF8A00', bot: '#FFD41F', edge: '#C46400' }, // событие
    org: { top: '#FFC600', bot: '#FFF900', edge: '#C79F00' }, // орг. единица, должность
    doc: { top: '#8F9898', bot: '#D5DADA', edge: '#6A7373' }, // документ, внешний участник
    gw: { top: '#585858', bot: '#ABABAB', edge: '#3A3A3A' }, // шлюз (правило)
    ext: { top: '#BFC8CE', bot: '#EEF1F3', edge: '#7E888F' }, // свернутый пул
    start: { top: '#3FCB1E', bot: '#BDF23C', edge: '#2F7F0E' },
    end: { top: '#D9241A', bot: '#FF8355', edge: '#8E140C' },
    hdr: { top: '#D3D9DE', bot: '#F3F5F6', edge: '#77828A' }, // заголовки пулов и дорожек
  };
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const f1 = (v) => (Math.round(v * 10) / 10).toString();
  const ctx = document.createElement('canvas').getContext('2d');
  function measure(t, size, weight = 'normal', style = 'normal') {
    ctx.font = `${style} ${weight} ${size}px ${FONT}`;
    return ctx.measureText(t).width;
  }
  // Неразрывные пробелы: число не отрывается от «дн.», «%», «чел.»; «части 2 (А)» — одной строкой.
  const nb = (t) => String(t)
    .replace(/(\d) (?=(дн\.|%|чел\.|ч\b))/g, '$1 ')
    .replace(/части (\d) \(/g, 'части $1 (');
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
    const size = o.size || 12, weight = o.weight || 'normal', style = o.italic ? 'italic' : 'normal';
    const lines = o.nowrap ? String(text).split('\n') : wrap(text, o.maxW || 108, size, weight, style);
    const LH = size * (o.lh || 1.2);
    const va = o.valign || 'middle';
    let y0;
    if (va === 'middle') y0 = y - ((lines.length - 1) * LH) / 2 + size * 0.36;
    else if (va === 'top') y0 = y + size * 0.82;
    else y0 = y - (lines.length - 1) * LH - size * 0.24;
    const anchor = o.anchor || 'middle';
    const halo = o.halo ? ` stroke="#fff" stroke-width="${o.halo}" stroke-linejoin="round" paint-order="stroke"` : '';
    const tsp = lines.map((l, i) => `<tspan x="${f1(x)}" y="${f1(y0 + i * LH)}">${esc(l)}</tspan>`).join('');
    const w = Math.max(...lines.map((l) => measure(l, size, weight, style)));
    return {
      svg: `<text font-family="${FONT}" font-size="${size}" font-weight="${weight}"${o.italic ? ' font-style="italic"' : ''} fill="${o.fill || C.text}" text-anchor="${anchor}"${halo}>${tsp}</text>`,
      lines, h: lines.length * LH, w,
    };
  }
  // Повёрнутый на -90° текст (заголовки пулов и дорожек).
  function vtext(cx, cy, text, o = {}) {
    const size = o.size || 12, lines = String(text).split('\n'), LH = size * 1.18;
    const y0 = -((lines.length - 1) * LH) / 2 + size * 0.36;
    const tsp = lines.map((l, i) => `<tspan x="0" y="${f1(y0 + i * LH)}">${esc(l)}</tspan>`).join('');
    return `<text transform="translate(${f1(cx)},${f1(cy)}) rotate(-90)" font-family="${FONT}" font-size="${size}" font-weight="${o.weight || 'bold'}" fill="${o.fill || C.text}" text-anchor="middle">${tsp}</text>`;
  }

  // ---------- общие определения: градиенты, блик, тень, стрелки ----------
  const grad = Object.entries(KIND).map(([k, v]) =>
    `<linearGradient id="g_${k}" x1="0" y1="0" x2="0.25" y2="1"><stop offset="0" stop-color="${v.top}"/><stop offset="1" stop-color="${v.bot}"/></linearGradient>`).join('');
  const defs = `<defs>${grad}
    <linearGradient id="gloss" x1="1" y1="0" x2="0.15" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.92"/><stop offset="0.45" stop-color="#fff" stop-opacity="0.5"/><stop offset="1" stop-color="#fff" stop-opacity="0.22"/></linearGradient>
    <filter id="sh" x="-20%" y="-20%" width="150%" height="160%"><feGaussianBlur stdDeviation="1.4"/></filter>
    <marker id="seq" viewBox="0 0 10 10" refX="9.6" refY="5" markerWidth="10" markerHeight="10" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M1.2,0.9 L9.6,5 L1.2,9.1" fill="none" stroke="${C.flow}" stroke-width="1.4" stroke-linejoin="miter"/></marker>
    <marker id="arr" viewBox="0 0 10 10" refX="9.6" refY="5" markerWidth="10" markerHeight="10" orient="auto" markerUnits="userSpaceOnUse"><path d="M1.2,0.9 L9.6,5 L1.2,9.1" fill="none" stroke="${C.flow}" stroke-width="1.4"/></marker>
    <marker id="msgEnd" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="10" markerHeight="10" orient="auto" markerUnits="userSpaceOnUse"><path d="M0.8,1 L9.5,5 L0.8,9 z" fill="#fff" stroke="${C.msg}" stroke-width="1.1"/></marker>
    <marker id="msgStart" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8" orient="auto" markerUnits="userSpaceOnUse"><circle cx="5" cy="5" r="3.6" fill="#fff" stroke="${C.msg}" stroke-width="1.1"/></marker>
  </defs>`;
  const wrapSvg = (w, h, body) =>
    `<svg xmlns="http://www.w3.org/2000/svg" width="${Math.ceil(w)}" height="${Math.ceil(h)}" viewBox="0 0 ${Math.ceil(w)} ${Math.ceil(h)}">${defs}<rect x="0" y="0" width="${Math.ceil(w)}" height="${Math.ceil(h)}" fill="#fff"/>${body}</svg>`;

  // ---------- контуры фигур ----------
  const rrect = (x, y, w, h, r) => `M${f1(x + r)},${f1(y)} H${f1(x + w - r)} A${r},${r} 0 0 1 ${f1(x + w)},${f1(y + r)} V${f1(y + h - r)} A${r},${r} 0 0 1 ${f1(x + w - r)},${f1(y + h)} H${f1(x + r)} A${r},${r} 0 0 1 ${f1(x)},${f1(y + h - r)} V${f1(y + r)} A${r},${r} 0 0 1 ${f1(x + r)},${f1(y)} Z`;
  // Многоугольник со скругленными углами.
  function roundPoly(pts, r) {
    const n = pts.length;
    let d = '';
    for (let i = 0; i < n; i++) {
      const p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n];
      const l1 = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]), l2 = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
      const rr = Math.min(r, l1 / 2, l2 / 2);
      const a = [p1[0] - ((p1[0] - p0[0]) / l1) * rr, p1[1] - ((p1[1] - p0[1]) / l1) * rr];
      const b = [p1[0] + ((p2[0] - p1[0]) / l2) * rr, p1[1] + ((p2[1] - p1[1]) / l2) * rr];
      d += `${i ? 'L' : 'M'}${f1(a[0])},${f1(a[1])} Q${f1(p1[0])},${f1(p1[1])} ${f1(b[0])},${f1(b[1])} `;
    }
    return d + 'Z';
  }
  const circlePath = (cx, cy, r) => `M${f1(cx - r)},${f1(cy)} A${r},${r} 0 1 0 ${f1(cx + r)},${f1(cy)} A${r},${r} 0 1 0 ${f1(cx - r)},${f1(cy)} Z`;
  const hexPts = (x, y, w, h) => { const k = Math.min(22, w * 0.14); return [[x + k, y], [x + w - k, y], [x + w, y + h / 2], [x + w - k, y + h], [x + k, y + h], [x, y + h / 2]]; };
  const chevPts = (x, y, w, h, first) => {
    const d = Math.min(22, h * 0.28);
    return first
      ? [[x, y], [x + w - d, y], [x + w, y + h / 2], [x + w - d, y + h], [x, y + h]]
      : [[x, y], [x + w - d, y], [x + w, y + h / 2], [x + w - d, y + h], [x, y + h], [x + d, y + h / 2]];
  };

  // Объемная фигура ARIS: тень, градиент, блик, светлая кромка внутри, обводка.
  let clipN = 0;
  function gloss(d, box, kind, o = {}) {
    const K = KIND[kind];
    const { x, y, w, h } = box;
    const id = `cp${++clipN}`;
    const sw = o.sw || 1.5;
    let s = '';
    if (!o.noShadow) s += `<path d="${d}" transform="translate(3.6,3.6)" fill="#6E6E6E" fill-opacity="0.55" filter="url(#sh)"/>`;
    s += `<clipPath id="${id}"><path d="${d}"/></clipPath>`;
    s += `<path d="${d}" fill="url(#g_${kind})"/>`;
    s += `<path clip-path="url(#${id})" d="M${f1(x - 3)},${f1(y - 3)} H${f1(x + w + 3)} V${f1(y + h * 0.34)} C${f1(x + w * 0.68)},${f1(y + h * 0.5)} ${f1(x + w * 0.3)},${f1(y + h * 0.53)} ${f1(x - 3)},${f1(y + h * 0.47)} Z" fill="url(#gloss)"/>`;
    s += `<path clip-path="url(#${id})" d="${d}" fill="none" stroke="#fff" stroke-opacity="0.5" stroke-width="4"/>`;
    s += `<path d="${d}" fill="none" stroke="${K.edge}" stroke-width="${sw}" stroke-linejoin="round"/>`;
    if (o.hl) s += `<path d="${o.hlPath || d}" fill="none" stroke="${C.impr}" stroke-width="3.2" stroke-linejoin="round" transform="${o.hlT || ''}"/>`;
    return s;
  }
  const box = (x, y, w, h, kind, o = {}) => gloss(rrect(x, y, w, h, o.r ?? 5), { x, y, w, h }, kind, o);

  // ---------- белые значки ARIS (левый верхний угол фигуры) ----------
  const ICON_STROKE = 'stroke="#000" stroke-opacity="0.22" stroke-width="0.7"';
  // Функция: стрелка с вырезом и шестеренка.
  function iconFunc(x, y, k = 1) {
    const p = (a, b) => `${f1(x + a * k)},${f1(y + b * k)}`;
    let s = `<path d="M${p(0, 4)} L${p(13, 4)} L${p(13, 0)} L${p(22, 9)} L${p(13, 18)} L${p(13, 14)} L${p(0, 14)} L${p(4.5, 9)} Z" fill="#fff" ${ICON_STROKE}/>`;
    const cx = x + 29 * k, cy = y + 9 * k;
    let teeth = '';
    for (let i = 0; i < 10; i++) {
      const a = (i * Math.PI) / 5;
      teeth += `M${f1(cx + 6.2 * k * Math.cos(a))},${f1(cy + 6.2 * k * Math.sin(a))} L${f1(cx + 9 * k * Math.cos(a))},${f1(cy + 9 * k * Math.sin(a))} `;
    }
    s += `<path d="${teeth}" stroke="#fff" stroke-width="${f1(2.2 * k)}" stroke-linecap="butt"/>`;
    s += `<circle cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(5.2 * k)}" fill="none" stroke="#fff" stroke-width="${f1(2.6 * k)}"/>`;
    return s;
  }
  // Сервисная задача: две шестеренки.
  function iconGears(x, y, k = 1) {
    const g = (cx, cy, r) => {
      let t = '';
      for (let i = 0; i < 8; i++) {
        const a = (i * Math.PI) / 4 + 0.2;
        t += `M${f1(cx + r * 0.7 * Math.cos(a))},${f1(cy + r * 0.7 * Math.sin(a))} L${f1(cx + r * Math.cos(a))},${f1(cy + r * Math.sin(a))} `;
      }
      return `<path d="${t}" stroke="#fff" stroke-width="${f1(2.3 * k)}"/><circle cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r * 0.6)}" fill="none" stroke="#fff" stroke-width="${f1(2.4 * k)}"/>`;
    };
    return g(x + 8 * k, y + 8 * k, 8 * k) + g(x + 19 * k, y + 13 * k, 6 * k);
  }
  // Событие: кружок и стрелка.
  function iconEvent(x, y, k = 1) {
    const p = (a, b) => `${f1(x + a * k)},${f1(y + b * k)}`;
    return `<circle cx="${f1(x + 4.5 * k)}" cy="${f1(y + 7 * k)}" r="${f1(4.5 * k)}" fill="#fff" ${ICON_STROKE}/>` +
      `<path d="M${p(9, 4.5)} L${p(19, 4.5)} L${p(19, 0)} L${p(27, 7)} L${p(19, 14)} L${p(19, 9.5)} L${p(9, 9.5)} Z" fill="#fff" ${ICON_STROKE}/>`;
  }
  // Должность: один человек.
  function person(cx, y, k = 1) {
    return `<circle cx="${f1(cx)}" cy="${f1(y + 4.5 * k)}" r="${f1(4.3 * k)}" fill="#fff" ${ICON_STROKE}/>` +
      `<path d="M${f1(cx - 7.5 * k)},${f1(y + 19 * k)} L${f1(cx - 7.5 * k)},${f1(y + 14.5 * k)} Q${f1(cx - 7.5 * k)},${f1(y + 9.5 * k)} ${f1(cx)},${f1(y + 9.5 * k)} Q${f1(cx + 7.5 * k)},${f1(y + 9.5 * k)} ${f1(cx + 7.5 * k)},${f1(y + 14.5 * k)} L${f1(cx + 7.5 * k)},${f1(y + 19 * k)} Z" fill="#fff" ${ICON_STROKE}/>`;
  }
  const iconPos = (x, y, k = 1) => person(x + 8 * k, y, k);
  // Организационная единица: группа людей.
  const iconOrg = (x, y, k = 1) => person(x + 7 * k, y + 3 * k, k * 0.8) + person(x + 15 * k, y + 1.5 * k, k * 0.88) + person(x + 24 * k, y, k);
  // Документ: лист с загнутым углом и строками.
  function iconDoc(x, y, k = 1) {
    const p = (a, b) => `${f1(x + a * k)},${f1(y + b * k)}`;
    let s = `<path d="M${p(0, 0)} L${p(11, 0)} L${p(16, 5)} L${p(16, 20)} L${p(0, 20)} Z" fill="#fff" ${ICON_STROKE}/>`;
    for (let i = 0; i < 4; i++) s += `<path d="M${p(3, 7 + i * 3.4)} L${p(13, 7 + i * 3.4)}" stroke="#8F9898" stroke-width="${f1(1.1 * k)}"/>`;
    return s;
  }

  // ---------- соединения ----------
  // Ломаная со скругленными углами (как линии ARIS Express).
  function roundPath(ptsIn, r = 7) {
    const pts = ptsIn.filter((p, i) => i === 0 || Math.hypot(p[0] - ptsIn[i - 1][0], p[1] - ptsIn[i - 1][1]) > 0.3);
    let d = `M${f1(pts[0][0])},${f1(pts[0][1])}`;
    for (let i = 1; i < pts.length - 1; i++) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
      const l1 = Math.hypot(x1 - x0, y1 - y0), l2 = Math.hypot(x2 - x1, y2 - y1);
      const rr = Math.min(r, l1 / 2, l2 / 2);
      const ax = x1 - ((x1 - x0) / l1) * rr, ay = y1 - ((y1 - y0) / l1) * rr;
      const bx = x1 + ((x2 - x1) / l2) * rr, by = y1 + ((y2 - y1) / l2) * rr;
      d += ` L${f1(ax)},${f1(ay)} Q${f1(x1)},${f1(y1)} ${f1(bx)},${f1(by)}`;
    }
    const last = pts[pts.length - 1];
    return d + ` L${f1(last[0])},${f1(last[1])}`;
  }
  const conn = (pts, o = {}) => `<path d="${roundPath(pts, o.r ?? 7)}" fill="none" stroke="${o.color || C.flow}" stroke-width="${o.sw || 1.4}"${o.arrow ? ' marker-end="url(#seq)"' : ''}${o.dash ? ` stroke-dasharray="${o.dash}"` : ''}/>`;

  // ---------- пометки на задачах ----------
  function badge(xr, yt, t, color) {
    const w = measure(t, 9.5, 'bold') + 9;
    return `<g><rect x="${f1(xr - w)}" y="${f1(yt)}" width="${f1(w)}" height="15" rx="3" fill="#fff" fill-opacity="0.92" stroke="${color}" stroke-width="1.1"/>${tb(xr - w / 2, yt + 7.5, t, { size: 9.5, weight: 'bold', fill: color, nowrap: true }).svg}</g>`;
  }
  const durTag = (xr, yb, t) => tb(xr, yb, t, { size: 9.4, fill: '#20380A', nowrap: true, anchor: 'end', valign: 'bottom' }).svg;

  // ---------- элементы BPMN ----------
  const isGw = (n) => n.type === 'xor' || n.type === 'and';
  const isEv = (n) => ['start', 'timer', 'end', 'msg', 'linkIn', 'linkOut'].includes(n.type);
  const SLOT = { task: 162, svc: 162, sub: 162, gw: 100, ev: 106 };
  const slotOf = (n) => n.slot || (isGw(n) ? SLOT.gw : isEv(n) ? SLOT.ev : SLOT.task);
  const TS = 11; // кегль подписи в задаче
  const ICON_ROW = 24;

  function sizeNode(n) {
    if (isGw(n)) { n.w = n.h = 50; return; }
    if (isEv(n)) { n.w = n.h = 38; return; }
    n.w = n.boxW || 140;
    const t = tb(0, 0, n.label, { size: TS, weight: 'bold', maxW: n.w - 14 });
    n.h = Math.max(70, ICON_ROW + t.h + (n.dur ? 16 : 8) + 4);
  }

  function drawNode(n) {
    const { x, y } = n;
    let s = '';
    if (n.type === 'task' || n.type === 'svc' || n.type === 'sub') {
      const x0 = x - n.w / 2, y0 = y - n.h / 2;
      s += box(x0, y0, n.w, n.h, 'func', { hl: n.hl });
      s += n.type === 'svc' ? iconGears(x0 + 7, y0 + 4, 1.05) : iconFunc(x0 + 7, y0 + 5, 1.02);
      const top = y0 + ICON_ROW, bot = y0 + n.h - (n.dur ? 15 : 6);
      s += tb(x, (top + bot) / 2, n.label, { size: TS, weight: 'bold', maxW: n.w - 14 }).svg;
      if (n.dur) s += durTag(x0 + n.w - 7, y0 + n.h - 5, n.dur);
      if (n.badge) s += badge(x0 + n.w - 6, y0 + 5, n.badge, n.badge.startsWith('П') ? C.prob : C.impr);
    } else if (isGw(n)) {
      const r = 25;
      s += gloss(roundPoly([[x, y - r], [x + r, y], [x, y + r], [x - r, y]], 5), { x: x - r, y: y - r, w: 2 * r, h: 2 * r }, 'gw');
      const m = n.type === 'xor'
        ? `M${x - 7.5},${y - 7.5} L${x + 7.5},${y + 7.5} M${x + 7.5},${y - 7.5} L${x - 7.5},${y + 7.5}`
        : `M${x - 10},${y} L${x + 10},${y} M${x},${y - 10} L${x},${y + 10}`;
      s += `<path d="${m}" stroke="#2A2A2A" stroke-opacity="0.45" stroke-width="7" stroke-linecap="round"/><path d="${m}" stroke="#fff" stroke-width="4.6" stroke-linecap="round"/>`;
      if (n.label) {
        const below = n.lpos === 'bottom';
        s += tb(x + (n.ldx || 0), below ? y + 31 : y - 31, n.label, { size: 10.6, maxW: n.lw || 116, valign: below ? 'top' : 'bottom', halo: 3 }).svg;
      }
    } else {
      const r = 19;
      const kind = n.type === 'start' || n.type === 'timer' ? 'start' : n.type === 'end' ? 'end' : 'event';
      s += gloss(circlePath(x, y, r), { x: x - r, y: y - r, w: 2 * r, h: 2 * r }, kind, { sw: n.type === 'end' ? 3.6 : 1.5 });
      if (kind === 'event') s += `<circle cx="${x}" cy="${y}" r="${r - 4}" fill="none" stroke="${KIND.event.edge}" stroke-width="1.3"/>`;
      if (n.type === 'msg') {
        s += `<rect x="${x - 8}" y="${y - 5.5}" width="16" height="11" fill="#fff" stroke="${KIND.event.edge}" stroke-width="1"/><path d="M${x - 8},${y - 5.5} L${x},${y + 1} L${x + 8},${y - 5.5}" fill="none" stroke="${KIND.event.edge}" stroke-width="1"/>`;
      } else if (n.type === 'linkIn' || n.type === 'linkOut') {
        const d = `M${x - 8},${y - 3.6} L${x + 1},${y - 3.6} L${x + 1},${y - 8} L${x + 9},${y} L${x + 1},${y + 8} L${x + 1},${y + 3.6} L${x - 8},${y + 3.6} Z`;
        s += n.type === 'linkOut' ? `<path d="${d}" fill="#fff" stroke="${KIND.event.edge}" stroke-width="1"/>` : `<path d="${d}" fill="none" stroke="#fff" stroke-width="2"/><path d="${d}" fill="none" stroke="${KIND.event.edge}" stroke-width="0.7"/>`;
      }
      if (n.label) {
        const above = n.lpos === 'top';
        s += tb(x, above ? y - 24 : y + 24, n.label, { size: 10.6, maxW: n.lw || 112, valign: above ? 'bottom' : 'top', halo: 3 }).svg;
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
    const POOL_L = 10, POOL_HDR = 30, LANE_HDR = 50, PAD = 12;
    const left = POOL_L + POOL_HDR + LANE_HDR + PAD;
    const colLeft = (c) => left + colW.slice(0, c).reduce((a, b) => a + b, 0);
    const colX = (c) => colLeft(c) + colW[c] / 2;
    const W = left + colW.reduce((a, b) => a + b, 0) + 14 + POOL_L;
    const EXT_H = 46, GAP = 60;
    let y = 10;
    const top = def.top || [], bot = def.bottom || [];
    const pools = [];
    if (top.length) { for (const p of top) pools.push({ ...p, where: 'top', y, h: EXT_H }); y += EXT_H + GAP; }
    const mainTop = y;
    const lanes = def.lanes.map((l) => { const o = { ...l, y, h: l.h || 140 }; o.yc = y + o.h / 2; y += o.h; return o; });
    const laneById = Object.fromEntries(lanes.map((l) => [l.id, l]));
    const mainBot = y;
    if (bot.length) { y += GAP; for (const p of bot) pools.push({ ...p, where: 'bot', y, h: EXT_H }); y += EXT_H; }
    const H = y + 14;
    const last = ncol - 1;
    for (const p of pools) {
      p.x1 = p.from === 0 ? POOL_L : colLeft(p.from) + 3;
      p.x2 = (p.to >= last ? W - POOL_L - 4 : colLeft(p.to + 1) - 3);
    }
    for (const n of nodes) { n.x = colX(n.col) + (n.dx || 0); n.y = laneById[n.lane].yc + (n.dy || 0); }

    const P = {
      ...byId,
      laneTop: (id) => laneById[id].y, laneBot: (id) => laneById[id].y + laneById[id].h,
      colX, colLeft,
    };

    let bg = '', fl = '', ms = '', nd = '', lb = '';
    // пул компании и дорожки
    const PW = W - 2 * POOL_L - 4;
    bg += `<rect x="${POOL_L + 3.6}" y="${mainTop + 3.6}" width="${PW}" height="${mainBot - mainTop}" fill="#6E6E6E" fill-opacity="0.35" filter="url(#sh)"/>`;
    bg += `<rect x="${POOL_L}" y="${mainTop}" width="${PW}" height="${mainBot - mainTop}" fill="#fff"/>`;
    bg += `<rect x="${POOL_L}" y="${mainTop}" width="${POOL_HDR}" height="${mainBot - mainTop}" fill="url(#g_hdr)" stroke="${C.laneS}" stroke-width="1.2"/>`;
    bg += vtext(POOL_L + POOL_HDR / 2, (mainTop + mainBot) / 2, def.pool, { size: 12.5 });
    for (const l of lanes) {
      bg += `<rect x="${POOL_L + POOL_HDR}" y="${l.y}" width="${LANE_HDR}" height="${l.h}" fill="url(#g_hdr)" stroke="${C.laneS}" stroke-width="1"/>`;
      bg += `<line x1="${POOL_L + POOL_HDR}" y1="${l.y}" x2="${POOL_L + PW}" y2="${l.y}" stroke="${C.laneS}" stroke-width="1"/>`;
      bg += vtext(POOL_L + POOL_HDR + LANE_HDR / 2, l.yc, l.name, { size: 11 });
    }
    bg += `<rect x="${POOL_L}" y="${mainTop}" width="${PW}" height="${mainBot - mainTop}" fill="none" stroke="${C.laneS}" stroke-width="1.4"/>`;
    // свернутые пулы внешних участников
    for (const p of pools) {
      bg += box(p.x1, p.y, p.x2 - p.x1, p.h, 'ext', { r: 2 });
      bg += tb((p.x1 + p.x2) / 2, p.y + p.h / 2, p.name, { size: 12, weight: 'bold', maxW: p.x2 - p.x1 - 12 }).svg;
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
      fl += conn([p1, ...mid, p2], { arrow: true });
      if (o.label) {
        const [dx, dyl] = o.lp || ('TB'.includes(fa) ? [7, fa === 'T' ? -12 : 14] : [6, -10]);
        lb += tb(p1[0] + dx, p1[1] + dyl, o.label, { size: 10.4, anchor: o.la || 'start', nowrap: true, halo: 3.5 }).svg;
      }
    }
    // потоки сообщений
    const poolByName = (nm) => pools.find((p) => p.name === nm || p.key === nm);
    for (const m of def.msgs || []) {
      const nodeEnd = byId[m.node];
      const pool = poolByName(m.pool);
      if (!nodeEnd || !pool) throw new Error('msg ' + m.node + ' ' + m.pool);
      const x = nodeEnd.x + (m.dx || 0);
      const halfH = isEv(nodeEnd) ? Math.sqrt(Math.max(0, 19 * 19 - (m.dx || 0) ** 2)) : nodeEnd.h / 2;
      const nodeY = pool.where === 'top' ? nodeEnd.y - halfH : nodeEnd.y + halfH;
      const poolY = pool.where === 'top' ? pool.y + pool.h : pool.y;
      const out = m.dir !== 'in';
      const [y1, y2] = out ? [nodeY, poolY] : [poolY, nodeY];
      ms += `<line x1="${x}" y1="${f1(y1)}" x2="${x}" y2="${f1(y2)}" stroke="${C.msg}" stroke-width="1.2" stroke-dasharray="6 4" marker-start="url(#msgStart)" marker-end="url(#msgEnd)"/>`;
      if (m.label) {
        const gy = (pool.where === 'top' ? pool.y + pool.h + GAP / 2 : pool.y - GAP / 2) + (m.ly || 0);
        const side = m.side || ((m.dx || 0) < 0 ? 'l' : 'r');
        lb += tb(side === 'r' ? x + 6 : x - 6, gy, m.label, { size: 9.8, maxW: m.lw || 132, anchor: side === 'r' ? 'start' : 'end', fill: '#333', halo: 3 }).svg;
      }
    }
    for (const n of nodes) nd += drawNode(n);
    return { svg: wrapSvg(W, H, bg + fl + ms + nd + lb), w: W, h: H };
  }

  // ---------- оргструктура (ARIS Organizational chart) ----------
  // kind: 'unit' — организационная единица (группа людей), 'pos' — должность (один человек).
  function orgBox(b) {
    const x = b.x - b.w / 2, y = b.y - b.h / 2;
    let s = box(x, y, b.w, b.h, 'org', { r: 4 });
    if (b.hl) s += `<rect x="${x - 5}" y="${y - 5}" width="${b.w + 10}" height="${b.h + 10}" rx="7" fill="none" stroke="${C.impr}" stroke-width="3"/>`;
    s += b.kind === 'pos' ? iconPos(x + 6, y + 4, Math.min(1.05, (b.h - 8) / 20)) : iconOrg(x + 5, y + 4, Math.min(1.05, (b.h - 8) / 21));
    s += tb(b.x + 16, b.y, b.label, { size: b.size || 12, maxW: b.w - 56, weight: 'bold' }).svg;
    return s;
  }

  // ---------- процесс VAD (шеврон ARIS) ----------
  function vchev(x, y, w, h, o = {}) {
    const pts = chevPts(x, y, w, h, o.first);
    let s = gloss(roundPoly(pts, 3), { x, y, w, h }, o.kind || 'func');
    if (o.hl) s += `<path d="${roundPoly(chevPts(x - 5, y - 5, w + 10, h + 10, o.first), 4)}" fill="none" stroke="${C.impr}" stroke-width="3.2"/>`;
    s += iconFunc(x + (o.first ? 8 : Math.min(22, h * 0.28) + 4), y + 6, 0.92);
    return s;
  }
  // Событие ARIS (шестиугольник) и документ — для VAD и легенды.
  const hexEvent = (x, y, w, h) => gloss(roundPoly(hexPts(x, y, w, h), 3), { x, y, w, h }, 'event') + iconEvent(x + Math.min(22, w * 0.14) + 2, y + 6, 0.8);
  const docBox = (x, y, w, h) => box(x, y, w, h, 'doc') + iconDoc(x + 7, y + 5, 0.85);

  // для совместимости со старыми вызовами
  function chevron(x, y, w, h, fill, stroke, sw, first) { return vchev(x, y, w, h, { first }); }

  window.D = {
    C, KIND, FONT, tb, vtext, wrapSvg, bpmn, orgBox, chevron, vchev, hexEvent, docBox, box, gloss, conn, roundPath,
    measure, drawNode, sizeNode, badge, durTag, esc, iconFunc, iconOrg, iconPos, iconEvent, iconDoc, iconGears,
  };
})();
