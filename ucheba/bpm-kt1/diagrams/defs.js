// Определения всех схем работы. Каждая функция возвращает { svg, w, h }.
(function () {
  const { C, tb, wrapSvg, bpmn, orgBox, chevron, drawNode, sizeNode, badge, durTag } = window.D;
  const V = 'Отдел закупок\nи ВЭД', CD = 'Коммерческий\nдиректор', F = 'Финансовая\nслужба', LG = 'Отдел\nлогистики', WH = 'Склад';
  const POOL = 'ООО «НеваИмпорт»';
  const SUP = 'Поставщик (КНР)';
  const MAIN = 40, UP = -58; // строки внутри высокой дорожки ВЭД

  const DIAGRAMS = {};

  // ---------- 1. Организационная структура ----------
  DIAGRAMS.org = () => {
    const W = 1120, H = 690;
    let s = '';
    const line = (pts) => `<polyline points="${pts.map((p) => p.join(',')).join(' ')}" fill="none" stroke="#6B6B6B" stroke-width="1.5"/>`;
    const gd = { x: 560, y: 44, w: 270, h: 46, label: 'Генеральный директор', kind: 'pos', bold: true };
    const staff = [
      { x: 330, y: 128, w: 170, h: 42, label: 'Юрист', kind: 'pos' },
      { x: 130, y: 128, w: 200, h: 42, label: 'Специалист по персоналу', kind: 'pos' },
      { x: 800, y: 128, w: 250, h: 42, label: 'ИТ-служба (2 чел.)', kind: 'unit' },
    ];
    const dirs = [
      { x: 190, y: 245, w: 300, h: 46, label: 'Коммерческий директор', kind: 'pos', bold: true },
      { x: 560, y: 245, w: 300, h: 46, label: 'Финансовый директор', kind: 'pos', bold: true },
      { x: 930, y: 245, w: 300, h: 46, label: 'Директор по логистике', kind: 'pos', bold: true },
    ];
    const deps = [
      ['Отдел оптовых продаж (6 чел.)', 'Отдел электронной торговли (3 чел.)', 'Отдел закупок и ВЭД (5 чел.)'],
      ['Бухгалтерия (3 чел.)', 'Финансово-экономический отдел (2 чел.)'],
      ['Транспортный отдел (2 чел.)', 'Склад (12 чел.)'],
    ];
    s += line([[560, 67], [560, 205]]);
    s += line([[130, 128], [800, 128]]);
    s += line([[190, 205], [930, 205]]);
    for (const d of dirs) s += line([[d.x, 205], [d.x, 222]]);
    const boxes = [gd, ...staff, ...dirs];
    dirs.forEach((d, i) => {
      const comb = d.x - 135;
      const ys = deps[i].map((_, j) => 310 + j * 56);
      s += line([[comb, 268], [comb, ys[ys.length - 1]]]);
      deps[i].forEach((t, j) => {
        s += line([[comb, ys[j]], [d.x - 120, ys[j]]]);
        boxes.push({ x: d.x + 20, y: ys[j], w: 280, h: 42, label: t, kind: 'unit', hl: i === 0 && j === 2 });
      });
    });
    // должности внутри отдела закупок и ВЭД
    const ved = boxes.find((b) => b.hl);
    const pos = ['Руководитель отдела (1)', 'Менеджер по закупкам (2)', 'Специалист по ВЭД и таможенному оформлению (1)', 'Специалист по сертификации (1)'];
    const py = [482, 532, 588, 644];
    s += line([[ved.x - 112, ved.y + 21], [ved.x - 112, py[3]]]);
    pos.forEach((t, j) => {
      s += line([[ved.x - 112, py[j]], [ved.x - 90, py[j]]]);
      boxes.push({ x: ved.x + 40, y: py[j], w: 260, h: j === 2 ? 48 : 40, label: t, kind: 'pos' });
    });
    for (const b of boxes) s += orgBox(b);
    s += tb(ved.x + 175, ved.y, 'объект исследования', { size: 14, anchor: 'start', fill: C.impr, weight: 'bold', nowrap: true }).svg;
    // условные обозначения
    const lx = 470, ly = 520;
    s += `<rect x="${lx}" y="${ly}" width="610" height="150" rx="6" fill="#FAFAFA" stroke="#C9C9C9"/>`;
    s += tb(lx + 16, ly + 22, 'Условные обозначения (ARIS, Organizational Chart)', { size: 14, weight: 'bold', anchor: 'start', nowrap: true }).svg;
    s += orgBox({ x: lx + 90, y: ly + 62, w: 150, h: 36, label: 'Должность', kind: 'pos' });
    s += orgBox({ x: lx + 290, y: ly + 62, w: 230, h: 36, label: 'Орг. единица', kind: 'unit' });
    s += `<rect x="${lx + 440}" y="${ly + 46}" width="40" height="32" rx="16" fill="#FFF3B5" stroke="${C.impr}" stroke-width="3"/>`;
    s += tb(lx + 490, ly + 62, 'объект\nисследования', { size: 13, anchor: 'start', nowrap: true }).svg;
    s += tb(lx + 16, ly + 112, 'Численность: 41 человек. Линии показывают прямое подчинение.', { size: 14, anchor: 'start', nowrap: true }).svg;
    s += tb(lx + 16, ly + 136, 'В скобках указано число сотрудников.', { size: 14, anchor: 'start', nowrap: true, fill: C.muted }).svg;
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };

  // ---------- 2. Процессы верхнего уровня (VAD) ----------
  DIAGRAMS.vad = () => {
    const W = 1120, H = 610;
    let s = '';
    const band = (y, h, title) => `<rect x="14" y="${y}" width="${W - 28}" height="${h}" rx="8" fill="#F7F8FA" stroke="#C5CBD3"/>` + tb(30, y + 18, title, { size: 15, weight: 'bold', anchor: 'start', nowrap: true, fill: '#2B3440' }).svg;
    const chev = (x, y, w, h, code, name, fill, first, hl) => {
      let r = chevron(x, y, w, h, fill, hl ? C.impr : '#4F6B3F', hl ? 3.2 : 1.3, first);
      const cx = x + (first ? (w - 18) / 2 : w / 2 + 2);
      const t = tb(cx, 0, name, { size: 13.6, maxW: w - 44 });
      const total = 17 + t.h;
      const top = y + h / 2 - total / 2;
      r += tb(cx, top, code, { size: 14, weight: 'bold', valign: 'top', nowrap: true }).svg;
      r += tb(cx, top + 17, name, { size: 13.6, maxW: w - 44, valign: 'top' }).svg;
      return r;
    };
    s += band(14, 136, 'Процессы управления');
    const U = [['У1', 'Стратегическое управление и планирование'], ['У2', 'Бюджетирование и управление финансами'], ['У3', 'Управление ассортиментом и ценообразованием'], ['У4', 'Управление рисками и соответствием требованиям ВЭД']];
    U.forEach(([c, n], i) => (s += chev(30 + i * 266, 54, 258, 76, c, n, '#DCE7F4', i === 0)));
    s += band(180, 220, 'Основные процессы (цепочка создания ценности)');
    s += `<rect x="28" y="238" width="92" height="86" rx="8" fill="#fff" stroke="#8A96A3"/>` + tb(74, 281, 'Запросы\nклиентов', { size: 13.5, maxW: 84, nowrap: true }).svg;
    const O = [['О1', 'Планирование закупок и управление запасами'], ['О2', 'Импортная закупка товара'], ['О3', 'Складская логистика'], ['О4', 'Продажи: опт и маркетплейсы'], ['О5', 'Доставка клиентам и сервис (возвраты, гарантия)']];
    O.forEach(([c, n], i) => (s += chev(130 + i * 177, 234, 173, 94, c, n, '#D3EAC4', false, i === 1)));
    s += `<rect x="1018" y="238" width="86" height="86" rx="8" fill="#fff" stroke="#8A96A3"/>` + tb(1061, 281, 'Товар\nу клиента', { size: 13.5, maxW: 80, nowrap: true }).svg;
    s += tb(130 + 177 + 86, 352, 'объект исследования', { size: 14, weight: 'bold', fill: C.impr, nowrap: true }).svg;
    s += tb(560, 380, 'Клиенты: строительные и монтажные организации, магазины строительных товаров, маркетплейсы', { size: 13.5, fill: C.muted, nowrap: true, italic: true }).svg;
    s += band(430, 166, 'Обеспечивающие процессы');
    const S = [['П1', 'Бухгалтерский учет и валютный контроль'], ['П2', 'Подтверждение соответствия (сертификация)'], ['П3', 'Управление персоналом'], ['П4', 'ИТ-обеспечение (1С, связь)'], ['П5', 'Правовое сопровождение (договоры, претензии)'], ['П6', 'Административно-хозяйственное обеспечение']];
    S.forEach(([c, n], i) => (s += chev(30 + i * 177, 474, 173, 100, c, n, '#F1E8D6', i === 0)));
    const blockArrow = (x, y1, y2) => {
      const d = y2 > y1 ? 1 : -1;
      return `<path d="M${x - 9},${y1} L${x + 9},${y1} L${x + 9},${y2 - d * 10} L${x + 17},${y2 - d * 10} L${x},${y2} L${x - 17},${y2 - d * 10} L${x - 9},${y2 - d * 10} z" fill="#B8C2CE"/>`;
    };
    s += blockArrow(330, 152, 178) + blockArrow(790, 152, 178);
    s += blockArrow(330, 428, 402) + blockArrow(790, 428, 402);
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };

  // ---------- 3. Границы процесса: контекстная диаграмма IDEF0 ----------
  DIAGRAMS.context = () => {
    const W = 1120, H = 650;
    let s = '';
    const bx1 = 400, bx2 = 720, by1 = 262, by2 = 432;
    const ln = (pts) => `<polyline points="${pts.map((p) => p.join(',')).join(' ')}" fill="none" stroke="${C.flow}" stroke-width="1.6" stroke-linejoin="round" marker-end="url(#arr)"/>`;
    const lab = (x, y, t, anchor = 'start', maxW = 350) => tb(x, y, t, { size: 14, anchor, maxW, valign: 'bottom', halo: 3 }).svg;
    s += `<rect x="${bx1}" y="${by1}" width="${bx2 - bx1}" height="${by2 - by1}" fill="#E4F2DA" stroke="${C.taskS}" stroke-width="2.4"/>`;
    s += tb((bx1 + bx2) / 2, (by1 + by2) / 2 - 10, 'Импортная закупка товара', { size: 19, weight: 'bold', maxW: 280 }).svg;
    s += tb((bx1 + bx2) / 2, (by1 + by2) / 2 + 28, 'от утвержденного плана закупок до оприходования товара', { size: 14, maxW: 270, fill: C.muted }).svg;
    s += tb(bx2 - 10, by2 - 10, 'А0', { size: 13, weight: 'bold', anchor: 'end', nowrap: true }).svg;
    // входы
    const ins = ['Потребность в товаре (план закупок)', 'Коммерческие предложения поставщиков', 'Денежные средства на оплату', 'Товар у поставщика (КНР)'];
    ins.forEach((t, i) => { const y = 290 + i * 40; s += ln([[30, y], [bx1, y]]) + lab(36, y - 5, t); });
    // выходы
    const outs = ['Товар доступен к продаже', 'Себестоимость партии', 'Документы поставки: контракт, ДТ и др.', 'Претензия поставщику'];
    outs.forEach((t, i) => { const y = 290 + i * 40; s += ln([[bx2, y], [W - 24, y]]) + lab(bx2 + 12, y - 5, t); });
    // управление (сверху)
    const ctlL = [['Таможенный кодекс ЕАЭС, закон № 289-ФЗ', 530], ['Закон № 173-ФЗ, Инструкция Банка России № 181-И (валютный контроль)', 480], ['Технические регламенты ЕАЭС (подтверждение соответствия)', 430]];
    ctlL.forEach(([t, x], i) => { const y = 62 + i * 52; s += ln([[30, y], [x, y], [x, by1]]) + lab(36, y - 5, t, 'start', 430); });
    const ctlR = [['Условия контракта, Инкотермс 2020', 600], ['Регламенты компании: лимиты, учетная политика', 660]];
    ctlR.forEach(([t, x], i) => { const y = 62 + i * 52; s += ln([[W - 24, y], [x, y], [x, by1]]) + lab(W - 30, y - 5, t, 'end', 380); });
    // механизмы (снизу)
    const mL = [['Отдел закупок и ВЭД', 430], ['Финансовая служба', 480], ['Отдел логистики и склад', 530]];
    mL.forEach(([t, x], i) => { const y = 490 + i * 50; s += ln([[30, y], [x, y], [x, by2]]) + lab(36, y - 5, t); });
    const mR = [['1С:УТ, Excel, почта, мессенджеры', 660], ['Банк, экспедитор, таможенный представитель', 600]];
    mR.forEach(([t, x], i) => { const y = 490 + i * 50; s += ln([[W - 24, y], [x, y], [x, by2]]) + lab(W - 30, y - 5, t, 'end', 380); });
    // подписи сторон
    const side = (x, y, t, a = 'start') => tb(x, y, t, { size: 13, weight: 'bold', fill: C.impr, anchor: a, nowrap: true }).svg;
    s += side(30, 20, 'УПРАВЛЕНИЕ (нормы и правила)') + side(30, 250, 'ВХОДЫ') + side(W - 24, 250, 'ВЫХОДЫ', 'end') + side(30, 636, 'МЕХАНИЗМЫ (исполнители и ресурсы)');
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };

  // ---------- 4. Декомпозиция процесса О2 (VAD 2-го уровня) ----------
  DIAGRAMS.decomp = () => {
    const W = 1120, H = 420;
    let s = '';
    const st = [
      ['1', 'Формирование заказа поставщику', 'Отдел закупок и ВЭД'],
      ['2', 'Выбор поставщика и согласование условий', 'Отдел закупок и ВЭД, коммерческий директор'],
      ['3', 'Заключение контракта, валютный контроль', 'Отдел закупок и ВЭД, финансовая служба'],
      ['4', 'Оплата аванса', 'Финансовая служба'],
      ['5', 'Производство у поставщика', 'Поставщик (контроль: отдел закупок и ВЭД)'],
      ['6', 'Оплата остатка и отгрузка', 'Финансовая служба, отдел логистики'],
      ['7', 'Международная перевозка', 'Экспедитор (контроль: отдел логистики)'],
      ['8', 'Таможенное оформление, подтверждение соответствия', 'Отдел закупок и ВЭД, таможенный представитель'],
      ['9', 'Доставка на склад и приемка', 'Отдел логистики, склад'],
      ['10', 'Оприходование и расчет себестоимости', 'Финансовая служба'],
    ];
    s += tb(20, 24, 'Начало: утвержден план закупок. Окончание: товар доступен к продаже.', { size: 15, anchor: 'start', nowrap: true, weight: 'bold', fill: '#2B3440' }).svg;
    st.forEach(([n, name, own], i) => {
      const row = Math.floor(i / 5), k = i % 5;
      const x = 20 + k * 216, y = 50 + row * 180;
      const ext = i === 4 || i === 6;
      s += chevron(x, y, 210, 92, ext ? '#EEF1F4' : '#D3EAC4', ext ? '#7D8894' : '#4F6B3F', 1.3, k === 0 && row === 0);
      const cx = x + 107;
      const t = tb(cx, 0, name, { size: 14, maxW: 156 });
      const top = y + 46 - (17 + t.h) / 2;
      s += tb(cx, top, n, { size: 15, weight: 'bold', valign: 'top', nowrap: true }).svg;
      s += tb(cx, top + 18, name, { size: 14, maxW: 156, valign: 'top' }).svg;
      s += `<ellipse cx="${x + 102}" cy="${y + 126}" rx="104" ry="29" fill="#FFF3B5" stroke="#A88400" stroke-width="1"/>`;
      s += tb(x + 100, y + 124, own, { size: 12.3, maxW: 168 }).svg;
    });
    s += tb(20, 410, 'Серым выделены этапы внешних участников, желтым показаны исполнители этапов.', { size: 13.5, anchor: 'start', nowrap: true, fill: C.muted, italic: true }).svg;
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };

  // ---------- 5. Условные обозначения BPMN ----------
  DIAGRAMS.legend = () => {
    const W = 1680, H = 250;
    let s = '';
    const colW = 336, rowH = 74;
    const cell = (c, r) => [20 + c * colW, 28 + r * rowH];
    const txt = (x, y, t) => tb(x, y, t, { size: 12.5, anchor: 'start', maxW: 250 }).svg;
    const ev = (type, c, r, label) => {
      const [x, y] = cell(c, r);
      const n = { type, x: x + 22, y: y + 18 };
      sizeNode(n);
      return drawNode(n) + txt(x + 52, y + 18, label);
    };
    s += ev('start', 0, 0, 'Стартовое событие');
    s += ev('timer', 1, 0, 'Стартовое событие «таймер»');
    s += ev('msg', 2, 0, 'Промежуточное событие: получено сообщение');
    s += ev('linkOut', 3, 0, 'Событие-ссылка: переход к следующей части схемы');
    s += ev('end', 4, 0, 'Конечное событие');
    const box = (c, r, kind, label) => {
      const [x, y] = cell(c, r);
      const b = `<rect x="${x}" y="${y}" width="60" height="38" rx="8" fill="${C.task}" stroke="${C.taskS}" stroke-width="1.4"/>`;
      return b + txt(x + 72, y + 19, label);
    };
    s += box(0, 1, 'task', 'Задача (выполняет сотрудник)');
    // сервисная задача, с шестеренкой
    {
      const [x, y] = cell(1, 1);
      const n = { type: 'svc', label: '', x: x + 30, y: y + 19, boxW: 60 };
      sizeNode(n); n.h = 38;
      s += drawNode(n) + txt(x + 72, y + 19, 'Сервисная задача (выполняется в 1С автоматически)');
    }
    {
      const [x, y] = cell(2, 1);
      const n = { type: 'sub', label: '', x: x + 30, y: y + 19, boxW: 60 };
      sizeNode(n); n.h = 38;
      s += drawNode(n) + txt(x + 72, y + 19, 'Свернутый подпроцесс');
    }
    const gw = (type, c, r, label) => {
      const [x, y] = cell(c, r);
      const n = { type, x: x + 26, y: y + 19 };
      sizeNode(n);
      return drawNode(n) + txt(x + 60, y + 19, label);
    };
    s += gw('xor', 3, 1, 'Исключающий шлюз (выбор одной ветви)');
    s += gw('and', 4, 1, 'Параллельный шлюз (все ветви одновременно)');
    {
      const [x, y] = cell(0, 2);
      s += `<line x1="${x}" y1="${y + 19}" x2="${x + 58}" y2="${y + 19}" stroke="${C.flow}" stroke-width="1.5" marker-end="url(#seq)"/>` + txt(x + 72, y + 19, 'Поток управления');
    }
    {
      const [x, y] = cell(1, 2);
      s += `<line x1="${x + 4}" y1="${y + 19}" x2="${x + 58}" y2="${y + 19}" stroke="${C.msg}" stroke-width="1.3" stroke-dasharray="6 4" marker-start="url(#msgStart)" marker-end="url(#msgEnd)"/>` + txt(x + 72, y + 19, 'Поток сообщений (обмен с внешним участником)');
    }
    {
      const [x, y] = cell(2, 2);
      s += badge(x + 14, y + 19, 'П1', C.prob) + badge(x + 44, y + 19, 'И1', C.impr) + txt(x + 72, y + 19, 'Номер проблемы (п. 10) и изменения (п. 11)');
    }
    {
      const [x, y] = cell(3, 2);
      s += durTag(x + 56, y + 19, '2 дн.') + txt(x + 72, y + 19, 'Длительность этапа (допущение модели)');
    }
    {
      const [x, y] = cell(4, 2);
      s += `<rect x="${x}" y="${y + 2}" width="60" height="34" fill="${C.ext}" stroke="${C.extS}" stroke-width="1.3"/>` + txt(x + 72, y + 19, 'Свернутый пул внешнего участника');
    }
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };

  // ---------- AS-IS, часть 1: заказ и контракт ----------
  DIAGRAMS.asis1 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'cd', name: CD, h: 130 }, { id: 'ved', name: V, h: 150 }],
    top: [{ name: SUP, from: 0, to: 99 }],
    nodes: [
      { id: 's1', type: 'start', lane: 'ved', col: 0, label: 'Утвержден план закупок на месяц' },
      { id: 'a1', type: 'task', lane: 'ved', col: 1, label: 'Сверить остатки в 1С и сформировать заказ в Excel', dur: '2 дн.', badge: 'П1' },
      { id: 'a2', type: 'task', lane: 'ved', col: 2, label: 'Разослать запрос цен поставщикам (почта, WeChat)', badge: 'П2' },
      { id: 'e1', type: 'msg', lane: 'ved', col: 3, label: 'КП получены (5 дн.)' },
      { id: 'a3', type: 'task', lane: 'ved', col: 4, label: 'Сравнить КП вручную, подготовить служебную записку', dur: '1 дн.', badge: 'П2' },
      { id: 'a4', type: 'task', lane: 'cd', col: 5, label: 'Рассмотреть выбор поставщика и условия', dur: '2 дн.', badge: 'П3' },
      { id: 'g1', type: 'xor', lane: 'cd', col: 6, label: 'Согласовано?', lpos: 'bottom' },
      { id: 'a5', type: 'task', lane: 'ved', col: 7, label: 'Подготовить отдельный контракт и спецификацию на поставку', dur: '4 дн.', badge: 'П4' },
      { id: 'a6', type: 'task', lane: 'cd', col: 8, label: 'Подписать контракт', dur: '1 дн.', badge: 'П3' },
      { id: 'a7', type: 'task', lane: 'ved', col: 9, label: 'Направить подписанный контракт поставщику' },
      { id: 'L1', type: 'linkOut', lane: 'ved', col: 10, label: 'Переход к части 2 (А)' },
    ],
    flows: [
      ['s1', 'a1'], ['a1', 'a2'], ['a2', 'e1'], ['e1', 'a3'], ['a3', 'a4'], ['a4', 'g1'],
      ['g1', 'a5', { fa: 'R', ta: 'L', label: 'да', mx: (P) => P.a5.x - 76 }],
      ['g1', 'a3', { fa: 'T', ta: 'T', label: 'нет (30%)', via: (P) => [[P.g1.x, P.laneTop('cd') + 13], [P.a3.x, P.laneTop('cd') + 13]] }],
      ['a5', 'a6'], ['a6', 'a7'], ['a7', 'L1'],
    ],
    msgs: [
      { node: 'a2', pool: SUP, dir: 'out', label: 'Запрос цен' },
      { node: 'e1', pool: SUP, dir: 'in', label: 'Коммерческие предложения', lw: 100 },
      { node: 'a5', pool: SUP, dx: -16, dir: 'out', label: 'Проект контракта', lw: 90 },
      { node: 'a5', pool: SUP, dx: 16, dir: 'in', label: 'Правки, согласие', lw: 90 },
      { node: 'a7', pool: SUP, dir: 'out', label: 'Подписанный контракт', lw: 100 },
    ],
  });

  // ---------- AS-IS, часть 2: оплата, производство, отгрузка ----------
  const BANK = 'Уполномоченный банк', FWD = 'Экспедитор';
  DIAGRAMS.asis2 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'ved', name: V, h: 150 }, { id: 'fin', name: F, h: 130 }, { id: 'log', name: LG, h: 130 }],
    top: [{ name: SUP, from: 0, to: 99 }],
    bottom: [{ name: BANK, from: 0, to: 7 }, { name: FWD, from: 8, to: 99 }],
    nodes: [
      { id: 'L2', type: 'linkIn', lane: 'ved', col: 0, label: 'Из части 1 (А)' },
      { id: 'b1', type: 'task', lane: 'ved', col: 1, label: 'Оформить служебную записку на оплату аванса', dur: '1 дн.', badge: 'П3' },
      { id: 'b2', type: 'task', lane: 'fin', col: 2, label: 'Поставить контракт на учет в банке', dur: '2 дн.', badge: 'П4' },
      { id: 'b3', type: 'task', lane: 'fin', col: 3, label: 'Оплатить аванс 30% (исполнение платежа банком)', dur: '10 дн.', badge: 'П5' },
      { id: 'e2', type: 'msg', lane: 'ved', col: 4, label: 'Товар готов (производство 30 дн.)' },
      { id: 'g2', type: 'and', lane: 'ved', col: 5 },
      { id: 'b4', type: 'task', lane: 'ved', col: 6, label: 'Оформить служебную записку на оплату остатка', dur: '1 дн.', badge: 'П3' },
      { id: 'b5', type: 'task', lane: 'fin', col: 7, label: 'Оплатить остаток 70% до отгрузки', dur: '10 дн.', badge: 'П5' },
      { id: 'b6', type: 'task', lane: 'log', col: 8, label: 'Запросить ставки и забронировать контейнер', dur: '7 дн.', badge: 'П6' },
      { id: 'g3', type: 'and', lane: 'fin', col: 9 },
      { id: 'e3', type: 'msg', lane: 'ved', col: 10, label: 'Товар отгружен (3 дн.)' },
      { id: 'L3', type: 'linkOut', lane: 'ved', col: 11, label: 'Переход к части 3 (Б)' },
    ],
    flows: [
      ['L2', 'b1'], ['b1', 'b2'], ['b2', 'b3'], ['b3', 'e2'], ['e2', 'g2'], ['g2', 'b4'], ['g2', 'b6'],
      ['b4', 'b5'], ['b5', 'g3'], ['b6', 'g3'], ['g3', 'e3'], ['e3', 'L3'],
    ],
    msgs: [
      { node: 'b2', pool: BANK, dir: 'out', label: 'Сведения о контракте', lw: 90 },
      { node: 'b3', pool: BANK, dir: 'out', label: 'Платеж (аванс)', lw: 90 },
      { node: 'e2', pool: SUP, dir: 'in', label: 'Уведомление о готовности', lw: 100 },
      { node: 'b5', pool: BANK, dir: 'out', side: 'l', label: 'Платеж (остаток)', lw: 90 },
      { node: 'b6', pool: FWD, dx: -16, dir: 'out', label: 'Запрос ставок, заявка', lw: 90 },
      { node: 'b6', pool: FWD, dx: 16, dir: 'in', label: 'Ставка, бронь', lw: 90 },
      { node: 'e3', pool: SUP, dir: 'in', label: 'Инвойс, упаковочный лист, коносамент', lw: 120 },
    ],
  });

  // ---------- AS-IS, часть 3: перевозка и таможенное оформление ----------
  const CERT = 'Орган по сертификации', BROKER = 'Таможенный представитель', CUST = 'Таможенный орган';
  DIAGRAMS.asis3 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'ved', name: V, h: 230 }, { id: 'fin', name: F, h: 130 }, { id: 'log', name: LG, h: 130 }],
    top: [{ name: SUP, from: 0, to: 5 }, { name: CERT, from: 6, to: 99 }],
    bottom: [{ name: FWD, from: 0, to: 2 }, { name: BROKER, from: 3, to: 8 }, { name: CUST, from: 9, to: 99 }],
    nodes: [
      { id: 'L4', type: 'linkIn', lane: 'log', col: 0, label: 'Из части 2 (Б)' },
      { id: 'd1', type: 'task', lane: 'log', col: 1, label: 'Отслеживать груз: звонки и письма экспедитору', dur: '45 дн. в пути', badge: 'П6' },
      { id: 'e4', type: 'msg', lane: 'log', col: 2, label: 'Груз прибыл, размещен на СВХ', lpos: 'top' },
      { id: 'd2', type: 'task', lane: 'ved', dy: MAIN, col: 3, label: 'Передать документы таможенному представителю', dur: '2 дн.', badge: 'П7' },
      { id: 'g4', type: 'xor', lane: 'ved', dy: MAIN, col: 4, label: 'Замечания к документам?', lpos: 'bottom' },
      { id: 'd3', type: 'task', lane: 'ved', dy: UP, col: 5, label: 'Запросить исправленные документы у поставщика', dur: '4 дн.', badge: 'П7' },
      { id: 'g5', type: 'xor', lane: 'ved', dy: MAIN, col: 6, label: 'Декларации соответствия есть на все товары?', lpos: 'bottom', lw: 120 },
      { id: 'd4', type: 'task', lane: 'ved', dy: UP, col: 7, label: 'Оформить декларацию соответствия (груз ждет на СВХ)', dur: '14 дн.', badge: 'П8' },
      { id: 'g6', type: 'xor', lane: 'ved', dy: MAIN, col: 8 },
      { id: 'd5', type: 'task', lane: 'fin', col: 9, label: 'Оплатить таможенные платежи по запросу брокера', dur: '2 дн.' },
      { id: 'e5', type: 'msg', lane: 'ved', dy: MAIN, col: 10, label: 'Товар выпущен (1 дн.)', lpos: 'top' },
      { id: 'L5', type: 'linkOut', lane: 'ved', dy: MAIN, col: 11, label: 'Переход к части 4 (В)' },
    ],
    flows: [
      ['L4', 'd1'], ['d1', 'e4'], ['e4', 'd2'], ['d2', 'g4'],
      ['g4', 'd3', { label: 'да (40%)' }],
      ['d3', 'd2', { fa: 'T', ta: 'T', fdx: -30, via: (P) => [[P.d3.x - 30, P.laneTop('ved') + 12], [P.d2.x, P.laneTop('ved') + 12]] }],
      ['g4', 'g5', { label: 'нет' }],
      ['g5', 'd4', { label: 'нет (30%)' }],
      ['g5', 'g6', { label: 'да' }],
      ['d4', 'g6'], ['g6', 'd5'], ['d5', 'e5'], ['e5', 'L5'],
    ],
    msgs: [
      { node: 'd1', pool: FWD, dx: -16, dir: 'out', label: 'Запрос статуса', lw: 80 },
      { node: 'd1', pool: FWD, dx: 16, dir: 'in', label: 'Статус груза', lw: 80 },
      { node: 'e4', pool: FWD, dir: 'in', label: 'Уведомление о прибытии', lw: 84 },
      { node: 'd2', pool: BROKER, dir: 'out', label: 'Документы для ДТ', lw: 100 },
      { node: 'd3', pool: SUP, dx: 14, dir: 'out', side: 'l', label: 'Замечания', lw: 90 },
      { node: 'd3', pool: SUP, dx: 36, dir: 'in', label: 'Исправленные документы', lw: 96 },
      { node: 'd4', pool: CERT, dx: -16, dir: 'out', label: 'Заявка, техдокументация', lw: 96 },
      { node: 'd4', pool: CERT, dx: 16, dir: 'in', label: 'Декларация соответствия', lw: 96 },
      { node: 'd5', pool: CUST, dir: 'out', label: 'Таможенные платежи', lw: 90 },
      { node: 'e5', pool: CUST, dir: 'in', label: 'Решение о выпуске', lw: 90 },
    ],
  });

  // ---------- AS-IS, часть 4: склад и оприходование ----------
  DIAGRAMS.asis4 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'ved', name: V, h: 130 }, { id: 'fin', name: F, h: 130 }, { id: 'log', name: LG, h: 130 }, { id: 'wh', name: WH, h: 130 }],
    top: [{ name: SUP, from: 0, to: 99 }],
    nodes: [
      { id: 'L6', type: 'linkIn', lane: 'log', col: 0, label: 'Из части 3 (В)' },
      { id: 'f1', type: 'task', lane: 'log', col: 1, label: 'Заказать машину и вывезти контейнер со СВХ на склад', dur: '2 дн.' },
      { id: 'f2', type: 'task', lane: 'wh', col: 2, label: 'Пересчитать товар вручную, сверить с упаковочным листом', dur: '2 дн.', badge: 'П9' },
      { id: 'g7', type: 'xor', lane: 'wh', col: 3, label: 'Расхождения есть?', lpos: 'bottom' },
      { id: 'f3', type: 'task', lane: 'ved', col: 4, label: 'Составить акт и претензию поставщику', dur: '7 дн.', badge: 'П9' },
      { id: 'g8', type: 'xor', lane: 'wh', col: 5 },
      { id: 'f4', type: 'task', lane: 'fin', col: 6, label: 'Дождаться ДТ и счетов, оприходовать товар в 1С', dur: '2 дн.', badge: 'П10' },
      { id: 'f5', type: 'task', lane: 'fin', col: 7, label: 'Рассчитать себестоимость партии в Excel', dur: '2 дн.', badge: 'П10' },
      { id: 'end1', type: 'end', lane: 'fin', col: 8, label: 'Товар оприходован и доступен к продаже' },
    ],
    flows: [
      ['L6', 'f1'], ['f1', 'f2'], ['f2', 'g7'], ['g7', 'f3', { label: 'да (15%)' }], ['g7', 'g8', { label: 'нет' }],
      ['f3', 'g8'], ['g8', 'f4', { fa: 'R', ta: 'L' }], ['f4', 'f5'], ['f5', 'end1'],
    ],
    msgs: [{ node: 'f3', pool: SUP, dir: 'out', label: 'Акт, претензия', lw: 90 }],
  });

  // ---------- TO-BE, часть 1: заказ и спецификация ----------
  DIAGRAMS.tobe1 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'cd', name: CD, h: 130 }, { id: 'ved', name: V, h: 236 }],
    top: [{ name: SUP, from: 0, to: 99 }],
    nodes: [
      { id: 's2', type: 'timer', lane: 'ved', dy: MAIN, col: 0, label: 'Еженедельный цикл планирования' },
      { id: 'h1', type: 'svc', lane: 'ved', dy: MAIN, col: 1, label: 'Рассчитать потребность: остатки, продажи, страховой запас, срок поставки', dur: 'авто', badge: 'И1', boxW: 128, slot: 150 },
      { id: 'h2', type: 'task', lane: 'ved', dy: MAIN, col: 2, label: 'Проверить и утвердить заказ поставщику', dur: '1 дн.', badge: 'И1' },
      { id: 'g9', type: 'xor', lane: 'ved', dy: MAIN, col: 3, label: 'Новая позиция или новый поставщик?', lpos: 'bottom' },
      { id: 'h3', type: 'sub', lane: 'ved', dy: UP, col: 4, label: 'Выбрать поставщика: запрос цен, оценка по критериям', dur: '6 дн.', badge: 'И2' },
      { id: 'g10', type: 'xor', lane: 'ved', dy: MAIN, col: 5 },
      { id: 'h4', type: 'task', lane: 'ved', dy: MAIN, col: 6, label: 'Сформировать спецификацию к рамочному контракту по шаблону', dur: '2 дн.', badge: 'И2' },
      { id: 'g11', type: 'xor', lane: 'ved', dy: MAIN, col: 7, label: 'Сумма в пределах лимита отдела?', lpos: 'bottom' },
      { id: 'h5', type: 'task', lane: 'ved', dy: MAIN, col: 8, label: 'Согласовать в 1С (руководитель отдела)', dur: '0,5 дн.', badge: 'И3' },
      { id: 'h6', type: 'task', lane: 'cd', col: 8, label: 'Согласовать в 1С (коммерческий директор)', dur: '0,5 дн.', badge: 'И3' },
      { id: 'g12', type: 'xor', lane: 'ved', dy: MAIN, col: 9 },
      { id: 'h7', type: 'task', lane: 'ved', dy: MAIN, col: 10, label: 'Подписать спецификацию через ЭДО, направить поставщику', dur: '0,5 дн.', badge: 'И3' },
      { id: 'L7', type: 'linkOut', lane: 'ved', dy: MAIN, col: 11, label: 'Переход к части 2 (А)' },
    ],
    flows: [
      ['s2', 'h1'], ['h1', 'h2'], ['h2', 'g9'],
      ['g9', 'h3', { label: 'да (20%)' }], ['g9', 'g10', { label: 'нет' }], ['h3', 'g10'],
      ['g10', 'h4'], ['h4', 'g11'],
      ['g11', 'h5', { label: 'да' }], ['g11', 'h6', { label: 'нет' }],
      ['h5', 'g12'], ['h6', 'g12'], ['g12', 'h7'], ['h7', 'L7'],
    ],
    msgs: [
      { node: 'h3', pool: SUP, dx: -16, dir: 'out', label: 'Запрос цен', lw: 80 },
      { node: 'h3', pool: SUP, dx: 16, dir: 'in', label: 'КП', lw: 80 },
      { node: 'h4', pool: SUP, dx: -16, dir: 'out', label: 'Спецификация', lw: 90 },
      { node: 'h4', pool: SUP, dx: 16, dir: 'in', label: 'Подтверждение (PI)', lw: 90 },
      { node: 'h7', pool: SUP, dir: 'out', label: 'Подписанная спецификация', lw: 100 },
    ],
  });

  // ---------- TO-BE, часть 2: оплата, производство, подготовка отгрузки ----------
  DIAGRAMS.tobe2 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'ved', name: V, h: 236 }, { id: 'fin', name: F, h: 130 }, { id: 'log', name: LG, h: 130 }],
    top: [{ name: CERT, from: 0, to: 2 }, { name: BROKER, from: 3, to: 4 }, { name: SUP, from: 5, to: 99 }],
    bottom: [{ name: BANK, from: 0, to: 2 }, { name: FWD, from: 3, to: 99 }],
    nodes: [
      { id: 'L8', type: 'linkIn', lane: 'ved', dy: MAIN, col: 0, label: 'Из части 1 (А)' },
      { id: 'g13', type: 'and', lane: 'ved', dy: MAIN, col: 1 },
      { id: 'k2', type: 'task', lane: 'ved', dy: MAIN, col: 2, label: 'Новые позиции: оформить декларацию соответствия', dur: '14 дн.', badge: 'И7' },
      { id: 'k1', type: 'svc', lane: 'fin', col: 2, label: 'Оплатить аванс по платежному календарю', dur: '5 дн.', badge: 'И4' },
      { id: 'k3', type: 'task', lane: 'ved', dy: MAIN, col: 3, label: 'Согласовать коды ТН ВЭД и шаблоны документов с брокером', dur: '1 дн.', badge: 'И6' },
      { id: 'k4', type: 'task', lane: 'log', col: 3, label: 'Забронировать контейнер на плановую дату готовности', dur: '1 дн.', badge: 'И5' },
      { id: 'g14', type: 'and', lane: 'fin', col: 4 },
      { id: 'e6', type: 'msg', lane: 'ved', dy: MAIN, col: 5, label: 'Товар готов (30 дн.), проекты документов получены' },
      { id: 'k5', type: 'task', lane: 'ved', dy: MAIN, col: 6, label: 'Проверить проекты инвойса и упаковочного листа по чек-листу', dur: '1 дн.', badge: 'И6' },
      { id: 'g15', type: 'xor', lane: 'ved', dy: MAIN, col: 7, label: 'Есть замечания?', lpos: 'bottom' },
      { id: 'k6', type: 'task', lane: 'ved', dy: UP, col: 8, label: 'Исправить документы с поставщиком до отгрузки', dur: '1 дн.', badge: 'И6' },
      { id: 'k7', type: 'task', lane: 'log', col: 9, label: 'Подтвердить отгрузку экспедитору', dur: '2 дн.', badge: 'И5' },
      { id: 'e7', type: 'msg', lane: 'ved', dy: MAIN, col: 10, label: 'Товар отгружен, копия коносамента получена' },
      { id: 'L9', type: 'linkOut', lane: 'ved', dy: MAIN, col: 11, label: 'Переход к части 3 (Б)' },
    ],
    flows: [
      ['L8', 'g13'], ['g13', 'k2'], ['g13', 'k1'], ['g13', 'k4'],
      ['k2', 'k3'], ['k3', 'g14'], ['k1', 'g14'], ['k4', 'g14'],
      ['g14', 'e6', { fa: 'R', ta: 'L' }], ['e6', 'k5'], ['k5', 'g15'],
      ['g15', 'k6', { label: 'да (10%)' }],
      ['k6', 'k5', { fa: 'T', ta: 'T', fdx: -30, via: (P) => [[P.k6.x - 30, P.laneTop('ved') + 12], [P.k5.x, P.laneTop('ved') + 12]] }],
      ['g15', 'k7', { fa: 'R', ta: 'L', label: 'нет', mx: (P) => P.k7.x - 76 }], ['k7', 'e7'], ['e7', 'L9'],
    ],
    msgs: [
      { node: 'k2', pool: CERT, dx: -16, dir: 'out', label: 'Заявка, техдокументация', lw: 90 },
      { node: 'k2', pool: CERT, dx: 16, dir: 'in', label: 'Декларация соответствия', lw: 84, ly: -14 },
      { node: 'k3', pool: BROKER, dx: -16, dir: 'out', label: 'Проекты документов', lw: 80, ly: 14 },
      { node: 'k3', pool: BROKER, dx: 16, dir: 'in', label: 'Коды ТН ВЭД', lw: 80 },
      { node: 'k1', pool: BANK, dir: 'out', side: 'l', label: 'Платеж (аванс)', lw: 90 },
      { node: 'k4', pool: FWD, dx: -16, dir: 'out', label: 'Бронь', lw: 70 },
      { node: 'k4', pool: FWD, dx: 16, dir: 'in', label: 'Подтверждение брони', lw: 90 },
      { node: 'e6', pool: SUP, dir: 'in', label: 'Уведомление, проекты документов', lw: 104 },
      { node: 'k6', pool: SUP, dx: 14, dir: 'out', side: 'l', label: 'Замечания', lw: 80 },
      { node: 'k6', pool: SUP, dx: 36, dir: 'in', label: 'Исправленные проекты', lw: 90 },
      { node: 'k7', pool: FWD, dir: 'out', label: 'Подтверждение отгрузки', lw: 90 },
      { node: 'e7', pool: SUP, dir: 'in', label: 'Документы, копия коносамента', lw: 100 },
    ],
  });

  // ---------- TO-BE, часть 3: перевозка и предварительное декларирование ----------
  DIAGRAMS.tobe3 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'ved', name: V, h: 140 }, { id: 'log', name: LG, h: 130 }, { id: 'fin', name: F, h: 130 }],
    top: [{ name: BROKER, from: 0, to: 3 }, { name: FWD, from: 4, to: 99 }],
    bottom: [{ name: BANK, from: 0, to: 2 }, { name: CUST, from: 3, to: 99 }],
    nodes: [
      { id: 'L10', type: 'linkIn', lane: 'fin', col: 0, label: 'Из части 2 (Б)' },
      { id: 'm1', type: 'svc', lane: 'fin', col: 1, label: 'Оплатить остаток 70% против копии коносамента', dur: '5 дн., в пути', badge: 'И4' },
      { id: 'm2', type: 'task', lane: 'ved', col: 2, label: 'Передать документы брокеру для предварительного декларирования', dur: '1 дн., в пути', badge: 'И8' },
      { id: 'm3', type: 'task', lane: 'fin', col: 3, label: 'Внести авансовые таможенные платежи', dur: '1 дн., в пути', badge: 'И8' },
      { id: 'm4', type: 'task', lane: 'log', col: 4, label: 'Отслеживать ETA в 1С, заказать транспорт к прибытию', dur: '45 дн. в пути', badge: 'И5' },
      { id: 'e8', type: 'msg', lane: 'log', col: 5, label: 'Груз прибыл в порт' },
      { id: 'e9', type: 'msg', lane: 'ved', col: 6, label: 'Товар выпущен (1 дн.)', lpos: 'top' },
      { id: 'L11', type: 'linkOut', lane: 'ved', col: 7, label: 'Переход к части 4 (В)' },
    ],
    flows: [['L10', 'm1'], ['m1', 'm2'], ['m2', 'm3'], ['m3', 'm4'], ['m4', 'e8'], ['e8', 'e9'], ['e9', 'L11']],
    msgs: [
      { node: 'm1', pool: BANK, dir: 'out', label: 'Платеж (остаток)', lw: 90 },
      { node: 'm2', pool: BROKER, dir: 'out', label: 'Документы для предварительной ДТ', lw: 110 },
      { node: 'm3', pool: CUST, dir: 'out', label: 'Авансовые платежи', lw: 90 },
      { node: 'm4', pool: FWD, dx: -16, dir: 'in', label: 'Статус и ETA', lw: 80 },
      { node: 'm4', pool: FWD, dx: 16, dir: 'out', label: 'Заявка на вывоз', lw: 80 },
      { node: 'e8', pool: FWD, dir: 'in', label: 'Уведомление о прибытии', lw: 90 },
      { node: 'e9', pool: CUST, dir: 'in', label: 'Решение о выпуске', lw: 90 },
    ],
  });

  // ---------- TO-BE, часть 4: склад и оприходование ----------
  DIAGRAMS.tobe4 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'ved', name: V, h: 130 }, { id: 'fin', name: F, h: 130 }, { id: 'log', name: LG, h: 130 }, { id: 'wh', name: WH, h: 130 }],
    top: [{ name: SUP, from: 0, to: 99 }],
    nodes: [
      { id: 'L12', type: 'linkIn', lane: 'log', col: 0, label: 'Из части 3 (В)' },
      { id: 'n1', type: 'task', lane: 'log', col: 1, label: 'Вывезти товар из порта на склад (транспорт заказан заранее)', dur: '1 дн.' },
      { id: 'n2', type: 'task', lane: 'wh', col: 2, label: 'Принять товар со сканированием (ТСД), расхождения сразу в 1С', dur: '1 дн.', badge: 'И9' },
      { id: 'g17', type: 'xor', lane: 'wh', col: 3, label: 'Расхождения есть?', lpos: 'bottom' },
      { id: 'n3', type: 'task', lane: 'ved', col: 4, label: 'Направить претензию поставщику по шаблону в день приемки', dur: 'до 1 дн.', badge: 'И9' },
      { id: 'g18', type: 'xor', lane: 'wh', col: 5 },
      { id: 'n4', type: 'svc', lane: 'fin', col: 6, label: 'Провести поступление в 1С, распределить доп. расходы на себестоимость', dur: '0,5 дн.', badge: 'И10', boxW: 128, slot: 150 },
      { id: 'end2', type: 'end', lane: 'fin', col: 7, label: 'Товар оприходован и доступен к продаже в день приемки' },
    ],
    flows: [
      ['L12', 'n1'], ['n1', 'n2'], ['n2', 'g17'], ['g17', 'n3', { label: 'да' }], ['g17', 'g18', { label: 'нет' }],
      ['n3', 'g18'], ['g18', 'n4', { fa: 'R', ta: 'L' }], ['n4', 'end2'],
    ],
    msgs: [{ node: 'n3', pool: SUP, dir: 'out', label: 'Акт, фото, претензия', lw: 90 }],
  });

  window.DIAGRAMS = DIAGRAMS;
})();
