// Отрисовка схем в SVG в стиле ARIS (образец владельца — модель eEPC из ARIS,
// присланная PDF 08.10.2026). Плоские фигуры без бликов и теней: слева цветная
// полоса с белым значком типа объекта, справа белое поле с подписью; шрифт Arial
// обычного начертания; тонкие черные линии с открытой стрелкой.
// Цвета сняты с образца пипеткой: функция #298927, должность #E29E30, документ
// и внешний участник #AAAAAA, информационная система #0B578B, событие #BA1B78,
// оператор #5E5E5E, интерфейс процесса #808080.
// Что рисует: eEPC (события, функции, операторы, роли, документы, системы,
// интерфейсы процессов), оргструктуру, цепочки процессов (VAD), контекстную
// диаграмму IDEF0. Работает в браузере: перенос строк меряется шрифтом через canvas.
(function () {
  const FONT = "Arial, 'Liberation Sans', sans-serif";
  const C = {
    text: '#000000', muted: '#555555',
    line: '#1E1E1E',
    func: '#298927', role: '#E29E30', ext: '#AAAAAA', doc: '#AAAAAA', app: '#0B578B',
    event: '#BA1B78', op: '#5E5E5E', iface: '#808080', edge: '#C4C4C4',
    prob: '#C0141B', impr: '#1F5FA8',
  };
  const FS = 11; // кегль подписей в фигурах
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const f1 = (v) => (Math.round(v * 10) / 10).toString();
  const ctx = document.createElement('canvas').getContext('2d');
  function measure(t, size, weight = 'normal', style = 'normal') {
    ctx.font = `${style} ${weight} ${size}px ${FONT}`;
    return ctx.measureText(t).width;
  }
  // Неразрывные пробелы: число не отрывается от «дн.», «%»; «Часть 2» — одной строкой.
  const nb = (t) => String(t)
    .replace(/(\d) (?=(дн\.|%|чел\.|ч\b))/g, '$1 ')
    .replace(/(Часть|часть) (\d)/g, '$1 $2')
    .replace(/(^|\s)([уУвВиИсСкКоОаА]) /g, '$1$2 ');
  function wrap(text, maxW, size, weight, style) {
    const out = [];
    for (const para of nb(text).split('\n')) {
      const toks = [];
      for (const w of para.split(' ')) {
        if (w.includes('-') && measure(w, size, weight, style) > maxW) {
          w.split(/(?<=-)/).forEach((p, i) => toks.push({ t: p, sp: i === 0 }));
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
    const size = o.size || FS, weight = o.weight || 'normal', style = o.italic ? 'italic' : 'normal';
    const lines = o.nowrap ? String(text).split('\n') : wrap(text, o.maxW || 108, size, weight, style);
    const LH = size * (o.lh || 1.15);
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
  const textH = (text, maxW, size = FS) => tb(0, 0, text, { maxW, size }).h;
  // Повёрнутый на -90° текст.
  function vtext(cx, cy, text, o = {}) {
    const size = o.size || FS, lines = String(text).split('\n'), LH = size * 1.18;
    const y0 = -((lines.length - 1) * LH) / 2 + size * 0.36;
    const tsp = lines.map((l, i) => `<tspan x="0" y="${f1(y0 + i * LH)}">${esc(l)}</tspan>`).join('');
    return `<text transform="translate(${f1(cx)},${f1(cy)}) rotate(-90)" font-family="${FONT}" font-size="${size}" font-weight="${o.weight || 'normal'}" fill="${o.fill || C.text}" text-anchor="middle">${tsp}</text>`;
  }

  // Открытая стрелка ARIS: две тонкие черты под острым углом.
  const defs = `<defs>
    <marker id="arr" viewBox="0 0 10 10" refX="9.6" refY="5" markerWidth="10" markerHeight="10" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M1.2,1.2 L9.6,5 L1.2,8.8" fill="none" stroke="${C.line}" stroke-width="1.1"/></marker>
  </defs>`;
  const wrapSvg = (w, h, body) =>
    `<svg xmlns="http://www.w3.org/2000/svg" width="${Math.ceil(w)}" height="${Math.ceil(h)}" viewBox="0 0 ${Math.ceil(w)} ${Math.ceil(h)}">${defs}<rect x="0" y="0" width="${Math.ceil(w)}" height="${Math.ceil(h)}" fill="#fff"/>${body}</svg>`;

  // ---------- белые значки (рисуются в цветной полосе) ----------
  const W = '#fff';
  // Функция: две сплошные стрелки «>>».
  const iconFunc = (cx, cy, k = 1) => {
    const t = (x0) => `M${f1(cx + x0 * k)},${f1(cy - 6 * k)} L${f1(cx + (x0 + 7) * k)},${f1(cy)} L${f1(cx + x0 * k)},${f1(cy + 6 * k)} Z`;
    return `<path d="${t(-7.5)} ${t(0.5)}" fill="${W}"/>`;
  };
  // Человек: голова и плечи с белым воротником.
  const iconPerson = (cx, cy, k = 1, bg = C.role) => {
    const P = (a, b) => `${f1(cx + a * k)},${f1(cy + b * k)}`;
    return `<circle cx="${f1(cx)}" cy="${f1(cy - 4.6 * k)}" r="${f1(3.6 * k)}" fill="${W}"/>` +
      `<path d="M${P(-7, 7)} L${P(-7, 3.5)} Q${P(-7, -0.2)} ${P(-3.2, -0.2)} L${P(3.2, -0.2)} Q${P(7, -0.2)} ${P(7, 3.5)} L${P(7, 7)} Z" fill="${W}"/>` +
      `<path d="M${P(-1.6, -0.2)} L${P(0, 3.6)} L${P(1.6, -0.2)} Z" fill="${bg}"/>`;
  };
  // Группа людей (внешний участник, подразделение): три силуэта, задние меньше.
  const iconGroup = (cx, cy, k = 1, bg = C.ext) => {
    const one = (dx, s, op) => {
      const P = (a, b) => `${f1(cx + (dx + a * s) * k)},${f1(cy + b * s * k)}`;
      return `<g opacity="${op}"><circle cx="${f1(cx + dx * k)}" cy="${f1(cy - 4.4 * s * k)}" r="${f1(3.3 * s * k)}" fill="${W}"/>` +
        `<path d="M${P(-6.2, 7.6)} L${P(-6.2, 3.4)} Q${P(-6.2, -0.4)} ${P(-2.6, -0.4)} L${P(2.6, -0.4)} Q${P(6.2, -0.4)} ${P(6.2, 3.4)} L${P(6.2, 7.6)} Z" fill="${W}"/></g>`;
    };
    return one(-6.5, 0.72, 0.75) + one(-2.5, 0.86, 0.88) + `<g>${one(3.2, 1, 1)}</g>`;
  };
  // Документ: дискета.
  const iconDoc = (cx, cy, k = 1, bg = C.doc) => {
    const P = (a, b) => `${f1(cx + a * k)},${f1(cy + b * k)}`;
    return `<path d="M${P(-7.5, -7.5)} L${P(5, -7.5)} L${P(7.5, -5)} L${P(7.5, 7.5)} L${P(-7.5, 7.5)} Z" fill="${W}"/>` +
      `<rect x="${f1(cx - 4.4 * k)}" y="${f1(cy - 7.5 * k)}" width="${f1(7.6 * k)}" height="${f1(4.2 * k)}" fill="${bg}"/>` +
      `<rect x="${f1(cx - 5 * k)}" y="${f1(cy + 0.6 * k)}" width="${f1(10 * k)}" height="${f1(5.2 * k)}" fill="${bg}"/>` +
      `<path d="M${P(-3.5, 2.6)} L${P(3.5, 2.6)} M${P(-3.5, 4.4)} L${P(3.5, 4.4)}" stroke="${W}" stroke-width="${f1(0.9 * k)}"/>`;
  };
  // Пакет документов: стопка карточек.
  const iconDocs = (cx, cy, k = 1, bg = C.doc) => {
    const card = (dx, dy) => `<rect x="${f1(cx + (dx - 7) * k)}" y="${f1(cy + (dy - 4.5) * k)}" width="${f1(14 * k)}" height="${f1(9 * k)}" rx="${f1(1 * k)}" fill="${W}" stroke="${bg}" stroke-width="${f1(1.2 * k)}"/>`;
    return card(2.4, -3.2) + card(0.6, -1) + card(-1.4, 1.6) + `<path d="M${f1(cx - 8.4 * k)},${f1(cy + 1 * k)} L${f1(cx - 8.4 * k)},${f1(cy + 6.8 * k)} L${f1(cx + 6.2 * k)},${f1(cy + 6.8 * k)}" fill="none" stroke="${W}" stroke-width="${f1(1.4 * k)}"/>`;
  };
  // Информационная система: окно с точками в заголовке.
  const iconApp = (cx, cy, k = 1, bg = C.app) =>
    `<rect x="${f1(cx - 8 * k)}" y="${f1(cy - 6 * k)}" width="${f1(16 * k)}" height="${f1(12 * k)}" fill="none" stroke="${W}" stroke-width="${f1(1.5 * k)}"/>` +
    `<path d="M${f1(cx - 8 * k)},${f1(cy - 2.6 * k)} L${f1(cx + 8 * k)},${f1(cy - 2.6 * k)}" stroke="${W}" stroke-width="${f1(1.3 * k)}"/>` +
    [2.6, 4.6, 6.6].map((d) => `<rect x="${f1(cx + (d - 6.2) * k + 3.2 * k)}" y="${f1(cy - 5 * k)}" width="${f1(1.2 * k)}" height="${f1(1.2 * k)}" fill="${W}"/>`).join('');
  // Флажок события.
  const iconFlag = (cx, cy, k = 1) => {
    const P = (a, b) => `${f1(cx + a * k)},${f1(cy + b * k)}`;
    return `<path d="M${P(-3.6, -5.6)} L${P(-1.2, 6.4)}" stroke="${W}" stroke-width="${f1(1.3 * k)}"/>` +
      `<path d="M${P(-3.4, -5.4)} Q${P(-0.6, -6.6)} ${P(1.2, -5.6)} Q${P(3, -4.6)} ${P(5.2, -5.6)} L${P(6.2, -0.6)} Q${P(4, 0.4)} ${P(2.2, -0.6)} Q${P(0.4, -1.6)} ${P(-2.4, -0.4)} Z" fill="${W}"/>`;
  };
  // Интерфейс процесса: флажок и «>>».
  const iconIface = (cx, cy, k = 1) => iconFlag(cx - 2 * k, cy - 2 * k, 0.9 * k) +
    `<path d="M${f1(cx + 0.5 * k)},${f1(cy + 2 * k)} L${f1(cx + 4.5 * k)},${f1(cy + 4.6 * k)} L${f1(cx + 0.5 * k)},${f1(cy + 7.2 * k)} Z M${f1(cx + 4.8 * k)},${f1(cy + 2 * k)} L${f1(cx + 8.8 * k)},${f1(cy + 4.6 * k)} L${f1(cx + 4.8 * k)},${f1(cy + 7.2 * k)} Z" fill="${W}"/>`;
  // Значок «есть вложенная модель»: темный квадрат с деревом.
  const hierMark = (x, y) => `<rect x="${f1(x)}" y="${f1(y)}" width="13" height="13" fill="#4A4A4A"/>` +
    `<path d="M${f1(x + 5)},${f1(y + 2.2)} h3 v2.6 h-3 Z M${f1(x + 2)},${f1(y + 8.2)} h3 v2.6 h-3 Z M${f1(x + 8)},${f1(y + 8.2)} h3 v2.6 h-3 Z" fill="${W}"/>` +
    `<path d="M${f1(x + 6.5)},${f1(y + 4.8)} V${f1(y + 6.6)} M${f1(x + 3.5)},${f1(y + 8.2)} V${f1(y + 6.6)} H${f1(x + 9.5)} V${f1(y + 8.2)}" fill="none" stroke="${W}" stroke-width="0.9"/>`;

  // ---------- фигуры ----------
  // Карточка ARIS: цветная полоса со значком и белое поле с подписью.
  const KIND = {
    func: { color: C.func, icon: iconFunc, strip: 36, r: 4, inset: [3, 1.5, 1.5] },
    role: { color: C.role, icon: iconPerson, strip: 34, r: 0, inset: [3, 1.5, 1.5] },
    unit: { color: C.role, icon: iconGroup, strip: 34, r: 0, inset: [3, 1.5, 1.5] },
    ext: { color: C.ext, icon: iconGroup, strip: 34, r: 0, inset: [3, 1.5, 1.5] },
    doc: { color: C.doc, icon: iconDoc, strip: 32, r: 0, inset: [3, 3, 3] },
    docs: { color: C.doc, icon: iconDocs, strip: 32, r: 0, inset: [3, 3, 3] },
    app: { color: C.app, icon: iconApp, strip: 34, r: 0, inset: [3, 1.5, 1.5] },
  };
  function card(kind, x, y, w, h, label, o = {}) {
    const K = KIND[kind];
    const [ti, ri, bi] = K.inset;
    const color = o.color || K.color;
    let s = `<rect x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}" rx="${K.r}" fill="${color}"/>`;
    const px = x + K.strip, py = y + ti, pw = w - K.strip - ri, ph = h - ti - bi;
    s += `<rect x="${f1(px)}" y="${f1(py)}" width="${f1(pw)}" height="${f1(ph)}" fill="#fff"/>`;
    if (ri < 2) s += `<path d="M${f1(px + pw)},${f1(py)} V${f1(py + ph)} H${f1(px)}" fill="none" stroke="${C.edge}" stroke-width="1"/>`;
    s += K.icon(x + K.strip / 2, y + h / 2, o.iconK || 1, color);
    if (label != null) s += tb(px + pw / 2, py + ph / 2, label, { size: o.size || FS, maxW: pw - 8, weight: o.weight }).svg;
    if (o.hl) s += `<rect x="${f1(x - 4)}" y="${f1(y - 4)}" width="${f1(w + 8)}" height="${f1(h + 8)}" rx="5" fill="none" stroke="${C.impr}" stroke-width="2.6"/>`;
    return s;
  }
  const cardH = (kind, w, label, min, size = FS) => Math.max(min, textH(label, w - KIND[kind].strip - 10, size) + 12);

  // Событие: шестиугольник, слева цветной с флажком, справа белый треугольник.
  function eventShape(x, y, w = 46, h = 24) {
    const x0 = x - w / 2, y0 = y - h / 2, k = w * 0.24, xr = x0 + w - k;
    let s = `<path d="M${f1(x0)},${f1(y)} L${f1(x0 + k)},${f1(y0)} L${f1(xr)},${f1(y0)} L${f1(xr)},${f1(y0 + h)} L${f1(x0 + k)},${f1(y0 + h)} Z" fill="${C.event}"/>`;
    s += `<path d="M${f1(xr)},${f1(y0 + 0.5)} L${f1(x0 + w)},${f1(y)} L${f1(xr)},${f1(y0 + h - 0.5)} Z" fill="#fff" stroke="${C.edge}" stroke-width="1"/>`;
    s += `<path d="M${f1(xr)},${f1(y0)} L${f1(xr)},${f1(y0 + h)}" stroke="${C.event}" stroke-width="1"/>`;
    s += iconFlag(x0 + k + (xr - x0 - k) / 2 - 2, y, h / 24);
    return s;
  }
  // Крупное событие с подписью внутри (для VAD).
  function bigEvent(x0, y0, w, h, label, o = {}) {
    const k = Math.min(18, h * 0.32), y = y0 + h / 2, strip = 34;
    let s = `<path d="M${f1(x0)},${f1(y)} L${f1(x0 + k)},${f1(y0)} L${f1(x0 + w - k)},${f1(y0)} L${f1(x0 + w)},${f1(y)} L${f1(x0 + w - k)},${f1(y0 + h)} L${f1(x0 + k)},${f1(y0 + h)} Z" fill="${C.event}"/>`;
    s += `<path d="M${f1(x0 + k + strip - 6)},${f1(y0 + 3)} L${f1(x0 + w - k - 1)},${f1(y0 + 3)} L${f1(x0 + w - 3)},${f1(y)} L${f1(x0 + w - k - 1)},${f1(y0 + h - 1.5)} L${f1(x0 + k + strip - 6)},${f1(y0 + h - 1.5)} Z" fill="#fff"/>`;
    s += iconFlag(x0 + k / 2 + strip / 2 - 2, y, 1);
    const pl = x0 + k + strip - 6, pr = x0 + w - k;
    s += tb((pl + pr) / 2, y, label, { size: o.size || FS, maxW: pr - pl - 4 }).svg;
    return s;
  }
  // Оператор: темно-серый круг с белым знаком.
  function opShape(x, y, type, r = 16) {
    let s = `<circle cx="${f1(x)}" cy="${f1(y)}" r="${r}" fill="${C.op}"/>`;
    const a = r * 0.36;
    if (type === 'xor') s += `<path d="M${f1(x - a)},${f1(y - a)} L${f1(x + a)},${f1(y + a)} M${f1(x + a)},${f1(y - a)} L${f1(x - a)},${f1(y + a)}" stroke="#fff" stroke-width="${f1(r * 0.24)}"/>`;
    else if (type === 'and') s += `<path d="M${f1(x - a)},${f1(y + a * 0.6)} L${f1(x)},${f1(y - a * 0.7)} L${f1(x + a)},${f1(y + a * 0.6)}" fill="none" stroke="#fff" stroke-width="${f1(r * 0.24)}"/>`;
    else s += `<path d="M${f1(x - a)},${f1(y - a * 0.6)} L${f1(x)},${f1(y + a * 0.7)} L${f1(x + a)},${f1(y - a * 0.6)}" fill="none" stroke="#fff" stroke-width="${f1(r * 0.24)}"/>`;
    return s;
  }
  // Интерфейс процесса: серая карточка с «хвостом»-стрелкой снизу и значком модели.
  // Название процесса пишется над фигурой (как у события), в белом поле — код модели.
  function ifaceShape(x, y, w, h, code, o = {}) {
    const x0 = x - w / 2, y0 = y - h / 2, strip = 34, tail = 12;
    let s = `<path d="M${f1(x0 + w * 0.14)},${f1(y0 + h - 6)} L${f1(x0 + w - 4)},${f1(y0 + h - 6)} L${f1(x0 + w + 12)},${f1(y0 + h * 0.62)} L${f1(x0 + w + 14)},${f1(y0 + h * 0.62)} L${f1(x0 + w - 2)},${f1(y0 + h + tail)} L${f1(x0 + w * 0.3)},${f1(y0 + h + tail)} Z" fill="${C.iface}"/>`;
    s += `<rect x="${f1(x0)}" y="${f1(y0)}" width="${f1(w)}" height="${f1(h)}" rx="5" fill="${C.iface}"/>`;
    s += `<rect x="${f1(x0 + strip)}" y="${f1(y0 + 3)}" width="${f1(w - strip - 4)}" height="${f1(h - 9)}" fill="#fff"/>`;
    s += iconIface(x0 + strip / 2 - 2, y0 + h / 2 - 3, 1);
    if (code) s += tb(x0 + strip + (w - strip - 4) / 2, y0 + 3 + (h - 9) / 2, code, { size: o.size || FS, maxW: w - strip - 12 }).svg;
    s += hierMark(x0 - 17, y0 - 1);
    return s;
  }

  // ---------- соединения ----------
  const line = (pts, o = {}) => `<polyline points="${pts.map((p) => p.map((v) => f1(v)).join(',')).join(' ')}" fill="none" stroke="${o.color || C.line}" stroke-width="${o.sw || 1.1}"${o.arrow ? ' marker-end="url(#arr)"' : ''}${o.start ? ' marker-start="url(#arr)"' : ''}${o.dash ? ` stroke-dasharray="${o.dash}"` : ''}/>`;
  const conn = (pts, o = {}) => line(pts, o);

  // ---------- модель eEPC (вертикальная, как в образце) ----------
  // def.cols — x центров колонок; def.nodes — узлы по порядку. Узлы колонки M без «at»
  // идут сверху вниз друг за другом и соединяются стрелкой (кроме cut: true).
  // Узел с «at» ставится на высоту узла at (+dy). У функции roles — должности и внешние
  // участники справа (буква связи code), docs — документы и системы слева (dir in/out).
  const FN_W = 150, SIDE_W = 148, EV_W = 46, EV_H = 24, OP_R = 16, IF_W = 112, IF_H = 38;
  function sizeNode(n) {
    if (n.t === 'fn') { n.w = n.w || FN_W; n.h = Math.max(62, textH(n.label, n.w - 36 - 10) + 16); }
    else if (n.t === 'ev') { n.w = EV_W; n.h = EV_H; n.lh = n.label ? textH(n.label, n.lw || 230) : 0; }
    else if (n.t === 'xor' || n.t === 'and' || n.t === 'or') { n.w = n.h = OP_R * 2; }
    else if (n.t === 'if') { n.w = n.w || IF_W; n.h = IF_H; n.lh = n.label ? textH(n.label, n.lw || 260) : 0; }
  }
  const topExtra = (n) => (n.t === 'ev' || n.t === 'if' ? n.lh + 6 : n.t === 'fn' && (n.num || n.badge) ? 14 : 0);
  const botExtra = (n) => (n.t === 'fn' && n.dur ? 15 : n.t === 'if' ? 12 : 0);

  // Подпись над событием или интерфейсом: белая подложка, чтобы входящая линия не резала буквы.
  function topLabel(cx, yb, label, maxW) {
    const t = tb(cx, yb, label, { maxW, valign: 'bottom' });
    return `<rect x="${f1(cx - t.w / 2 - 2)}" y="${f1(yb - t.h - 1)}" width="${f1(t.w + 4)}" height="${f1(t.h + 2)}" fill="#fff"/>` + t.svg;
  }
  function epc(def) {
    const cols = { D: 96, M: 292, R: 474, B: 660, BR: 846, ...(def.cols || {}) };
    const nodes = def.nodes.map((n) => ({ ...n, col: n.col || 'M' }));
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    nodes.forEach(sizeNode);
    // Узлы без «at» идут цепочками: основная (chain не задан) и боковые (chain: 'A' и т. п.).
    // Первый узел боковой цепочки начинается под узлом from; after — не выше указанных узлов.
    const chains = {};
    const bottom = (a) => a.y + a.h / 2 + botExtra(a);
    for (const n of nodes) {
      n.x = typeof n.col === 'number' ? n.col : cols[n.col];
      if (n.dx) n.x += n.dx;
      if (n.at) { const a = byId[n.at]; n.y = a.y + (n.dy || 0); continue; }
      const key = n.chain || 'main';
      let c = chains[key];
      if (!c) { c = chains[key] = { cursor: n.from ? bottom(byId[n.from]) : def.top || 26, prev: null }; }
      let cur = c.prev ? bottom(c.prev) : c.cursor;
      for (const id of [].concat(n.after || [])) cur = Math.max(cur, bottom(byId[id]));
      n.y = cur + (def.gap || 20) + topExtra(n) + (n.gap || 0) + n.h / 2;
      n.prev = c.prev; c.prev = n;
    }
    // боковые фигуры
    const side = [];
    for (const n of nodes) {
      const place = (list, col, defKind) => {
        if (!list || !list.length) return;
        const items = list.map((r) => {
          const kind = r.kind || defKind;
          const w = r.w || def.sideW || SIDE_W;
          const h = cardH(kind, w, r.label, kind === 'app' || kind === 'doc' || kind === 'docs' ? 34 : 44);
          return { ...r, kind, w, h };
        });
        const total = items.reduce((s, r) => s + r.h, 0) + (items.length - 1) * 10;
        let yy = n.y - total / 2 + (col === 'R' ? n.rdy || 0 : n.ddy || 0);
        const cx = typeof col === 'number' ? col : cols[col];
        for (const r of items) { r.x = cx; r.y = yy + r.h / 2; yy += r.h + 10; r.fn = n; r.side = col === 'D' || (typeof col === 'number' && col < n.x) ? 'L' : 'R'; side.push(r); }
      };
      place(n.roles, n.rcol || 'R', 'role');
      place(n.docs, n.dcol || 'D', 'doc');
    }
    // точки привязки
    const anchor = (n, s, off = 0) => {
      if (s === 'L') return [n.x - n.w / 2, n.y + off];
      if (s === 'R') return [n.x + n.w / 2, n.y + off];
      if (s === 'T') return [n.x + off, n.y - n.h / 2];
      return [n.x + off, n.y + n.h / 2 + (n.t === 'if' ? 12 : 0)];
    };
    let ed = '', sh = '', lb = '';
    const edgePts = [];
    const P = { ...byId, cols };
    const flow = (A, B, o = {}) => {
      let fa = o.fa, ta = o.ta;
      if (!fa && !ta) {
        if (Math.abs(A.x - B.x) < 1) { fa = B.y > A.y ? 'B' : 'T'; ta = B.y > A.y ? 'T' : 'B'; }
        else if (Math.abs(A.y - B.y) < 1) { fa = B.x > A.x ? 'R' : 'L'; ta = B.x > A.x ? 'L' : 'R'; }
        else if (B.y > A.y) { fa = B.x > A.x ? 'R' : 'L'; ta = 'T'; }
        else { fa = 'B'; ta = 'L'; }
      }
      const p1 = anchor(A, fa || 'B', o.fdx || 0), p2 = anchor(B, ta || 'T', o.tdx || 0);
      let mid = [];
      if (o.via) { P.__from = A; P.__to = B; mid = o.via(P); }
      else if ('LR'.includes(fa) && 'TB'.includes(ta)) mid = [[p2[0], p1[1]]];
      else if ('TB'.includes(fa) && 'LR'.includes(ta)) mid = [[p1[0], p2[1]]];
      else if ('TB'.includes(fa) && 'TB'.includes(ta) && Math.abs(p1[0] - p2[0]) > 0.5) { const my = o.my != null ? o.my : (p1[1] + p2[1]) / 2; mid = [[p1[0], my], [p2[0], my]]; }
      else if ('LR'.includes(fa) && 'LR'.includes(ta) && Math.abs(p1[1] - p2[1]) > 0.5) { const mx = o.mx != null ? o.mx : (p1[0] + p2[0]) / 2; mid = [[mx, p1[1]], [mx, p2[1]]]; }
      edgePts.push(p1, ...mid, p2);
      ed += line([p1, ...mid, p2], { arrow: true });
      if (o.label) lb += tb(p1[0] + (o.lp ? o.lp[0] : 6), p1[1] + (o.lp ? o.lp[1] : -6), o.label, { size: FS - 0.5, anchor: o.la || 'start', nowrap: true }).svg;
    };
    for (const n of nodes) if (n.prev && !n.cut && !n.at) flow(n.prev, n);
    for (const [a, b, o] of def.flows || []) flow(byId[a], byId[b], o || {});
    // связи ролей и документов
    const groups = new Map();
    for (const r of side) { const k = r.fn.id + r.side; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(r); }
    for (const list of groups.values()) {
      const n = list[0].fn, right = list[0].side === 'R';
      const fx = right ? n.x + n.w / 2 : n.x - n.w / 2;
      const ex = (r) => (right ? r.x - r.w / 2 : r.x + r.w / 2);
      const busX = right ? fx + Math.min(14, (ex(list[0]) - fx) / 2) : fx - Math.min(14, (fx - ex(list[0])) / 2);
      for (const r of list) {
        const pts = Math.abs(r.y - n.y) < 1 ? [[fx, n.y], [ex(r), r.y]] : [[fx, n.y], [busX, n.y], [busX, r.y], [ex(r), r.y]];
        if (r.dir === 'in') ed += line(pts.slice().reverse(), { arrow: true });
        else ed += line(pts, { arrow: r.dir === 'out' });
        if (r.code) lb += tb(ex(r) - 4, r.y + 9, r.code, { size: FS, anchor: 'end', valign: 'top', nowrap: true }).svg;
      }
    }
    for (const r of side) {
      sh += card(r.kind, r.x - r.w / 2, r.y - r.h / 2, r.w, r.h, r.label);
      if (r.kind === 'app') sh += hierMark(r.x - r.w / 2 - 16, r.y - r.h / 2 - 1);
    }
    // узлы
    for (const n of nodes) {
      const x0 = n.x - n.w / 2, y0 = n.y - n.h / 2;
      if (n.t === 'fn') {
        sh += card('func', x0, y0, n.w, n.h, n.label, { hl: n.hl });
        if (n.num) lb += tb(x0 + 2, y0 - 4, n.num, { size: FS - 0.5, anchor: 'start', valign: 'bottom', nowrap: true }).svg;
        if (n.badge) lb += tb(x0 + n.w, y0 - 4, n.badge, { size: FS - 0.5, weight: 'bold', anchor: 'end', valign: 'bottom', nowrap: true, fill: n.badge.startsWith('П') ? C.prob : C.impr }).svg;
        if (n.dur) lb += tb(n.x + 4, y0 + n.h + 3, n.dur, { size: FS - 0.5, anchor: 'start', valign: 'top', nowrap: true }).svg;
      } else if (n.t === 'ev') {
        sh += eventShape(n.x, n.y);
        if (n.label) lb += topLabel(n.x + (n.ldx || 0), y0 - 5, n.label, n.lw || 230);
      } else if (n.t === 'if') {
        sh += ifaceShape(n.x, n.y, n.w, n.h, n.code);
        if (n.label) lb += topLabel(n.x + (n.ldx || 0), y0 - 5, n.label, n.lw || 260);
      } else {
        sh += opShape(n.x, n.y, n.t, OP_R);
      }
    }
    // размеры
    let maxX = 0, maxY = 0;
    const ext = (x, y) => { maxX = Math.max(maxX, x); maxY = Math.max(maxY, y); };
    for (const n of nodes) { ext(n.x + n.w / 2 + (n.t === 'if' ? 16 : 0), n.y + n.h / 2 + botExtra(n) + 4); if ((n.t === 'ev' || n.t === 'if') && n.label) ext(n.x + (n.lw || (n.t === 'if' ? 260 : 230)) / 2, 0); }
    for (const r of side) ext(r.x + r.w / 2, r.y + r.h / 2);
    for (const p of edgePts) ext(p[0] + 8, p[1] + 8);
    const Wd = def.width || maxX + 16, Hd = def.height || maxY + 16;
    return { svg: wrapSvg(Wd, Hd, ed + sh + lb), w: Wd, h: Hd };
  }

  // ---------- оргструктура (ARIS Organizational chart) ----------
  // kind: 'unit' — организационная единица, 'pos' — должность.
  function orgBox(b) {
    const x = b.x - b.w / 2, y = b.y - b.h / 2;
    return card(b.kind === 'pos' ? 'role' : 'unit', x, y, b.w, b.h, b.label, { size: b.size || FS, hl: b.hl });
  }

  // ---------- процесс VAD (шеврон) ----------
  const chevPts = (x, y, w, h, first, d) => (first
    ? [[x, y], [x + w - d, y], [x + w, y + h / 2], [x + w - d, y + h], [x, y + h]]
    : [[x, y], [x + w - d, y], [x + w, y + h / 2], [x + w - d, y + h], [x, y + h], [x + d, y + h / 2]]);
  const ptsPath = (pts) => 'M' + pts.map((p) => p.map(f1).join(',')).join(' L') + ' Z';
  // Возвращает svg и центр белого поля (px, pw) для подписи.
  function vchev(x, y, w, h, o = {}) {
    const d = Math.min(20, h * 0.26), strip = 30;
    const color = o.kind === 'doc' ? C.ext : C.func;
    let s = `<path d="${ptsPath(chevPts(x, y, w, h, o.first, d))}" fill="${color}"/>`;
    const sx = x + (o.first ? 0 : d) + strip; // левая граница белого поля
    const panel = [[sx, y + 3], [x + w - d - 1, y + 3], [x + w - 3, y + h / 2], [x + w - d - 1, y + h - 1.5], [sx, y + h - 1.5]];
    s += `<path d="${ptsPath(panel)}" fill="#fff"/>`;
    s += iconFunc(sx - strip / 2 - (o.first ? 0 : 2), y + h / 2, 1);
    if (o.hl) s += `<path d="${ptsPath(chevPts(x - 5, y - 5, w + 10, h + 10, o.first, d + 2))}" fill="none" stroke="${C.impr}" stroke-width="2.6" stroke-linejoin="round"/>`;
    return s;
  }
  const vchevPanel = (x, w, h, first) => { const d = Math.min(20, h * 0.26); const sx = x + (first ? 0 : d) + 30; return { cx: (sx + x + w - d / 2) / 2 - 2, w: x + w - d / 2 - sx - 8 }; };
  function chevron(x, y, w, h, fill, stroke, sw, first) { return vchev(x, y, w, h, { first }); }

  window.D = {
    C, FS, FONT, tb, vtext, wrapSvg, measure, esc, textH,
    card, cardH, eventShape, bigEvent, opShape, ifaceShape, hierMark, line, conn,
    epc, orgBox, vchev, vchevPanel, chevron, iconFunc, KIND,
  };
})();
