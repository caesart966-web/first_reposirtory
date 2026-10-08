// Определения всех схем работы (Fix Price, импорт товаров из Китая).
// Каждая функция возвращает { svg, w, h }. Оформление в стиле ARIS Express — в lib.js.
(function () {
  const { C, tb, wrapSvg, bpmn, orgBox, vchev, hexEvent, box, conn, drawNode, sizeNode, badge, iconFunc, iconGears } = window.D;
  const KM = 'Категорийный\nменеджер', RK = 'Руководитель\nкатегории', IMP = 'Отдел\nимпорта', KK = 'Контроль\nкачества',
    F = 'Финансовая\nслужба', LG = 'Транспортная\nлогистика', DC = 'Распредели-\nтельный центр';
  const POOL = 'Fix Price (ООО «Бэст Прайс»)';
  const AG = 'Торговый агент и фабрика (КНР)', LAB = 'Испытательная лаборатория', BANK = 'Уполномоченный банк',
    FWD = 'Экспедитор', BROKER = 'Таможенный представитель', CUST = 'Таможенный орган', GIS = 'ГИС МТ «Честный знак»';
  const MAIN = 42, UP = -64; // строки внутри высокой дорожки
  const LINE = '#4A4A4A';

  const DIAGRAMS = {};

  // ---------- 1. Организационная структура (ARIS Organizational Chart, укрупненно) ----------
  DIAGRAMS.org = () => {
    const W = 1150, H = 690;
    let s = '';
    const line = (pts) => conn(pts, { r: 6, color: LINE, sw: 1.4 });
    const boxes = [];
    boxes.push({ x: 570, y: 40, w: 470, h: 46, label: 'ПАО «Фикс Прайс» (материнская компания группы)', kind: 'unit', size: 12.5 });
    boxes.push({ x: 570, y: 118, w: 470, h: 46, label: 'Генеральный директор ООО «Бэст Прайс»', kind: 'pos', size: 12.5 });
    s += line([[570, 63], [570, 95]]) + line([[570, 141], [570, 172]]);
    s += line([[160, 172], [874, 172]]);
    const com = { x: 165, y: 214, w: 290, h: 46, label: 'Коммерческая дирекция', kind: 'pos', size: 12.5 };
    const log = { x: 455, y: 214, w: 260, h: 46, label: 'Дирекция по логистике', kind: 'pos', size: 12.5 };
    boxes.push(com, log);
    s += line([[160, 172], [160, 191]]) + line([[455, 172], [455, 191]]);
    const comKids = ['Категорийный менеджмент', 'Отдел импорта', 'Закупки у российских поставщиков', 'Контроль качества и сертификация', 'Собственные торговые марки'];
    comKids.forEach((t, j) => {
      const y = 284 + j * 58;
      s += line([[40, y], [58, y]]);
      boxes.push({ x: 192, y, w: 268, h: 44, label: t, kind: 'unit', hl: j === 1, size: 11.5 });
    });
    s += line([[40, 237], [40, 284 + 4 * 58]]);
    ['Распределительные центры', 'Транспортная логистика'].forEach((t, j) => {
      const y = 284 + j * 58;
      s += line([[342, y], [360, y]]);
      boxes.push({ x: 471, y, w: 222, h: 44, label: t, kind: 'unit', size: 11.5 });
    });
    s += line([[342, 237], [342, 284 + 58]]);
    const cols = [
      { x: 742, items: ['Операционная дирекция (магазины)', 'Финансовая дирекция', 'Дирекция по персоналу', 'Дирекция по ИТ'] },
      { x: 1012, items: ['Развитие сети и недвижимость', 'Маркетинг и лояльность', 'Франчайзинг и зарубежные рынки', 'Юридическая служба'] },
    ];
    for (const c of cols) {
      const comb = c.x - 138;
      s += line([[comb, 172], [comb, 214 + 3 * 58]]);
      c.items.forEach((t, j) => {
        const y = 214 + j * 58;
        s += line([[comb, y], [c.x - 125, y]]);
        boxes.push({ x: c.x, y, w: 250, h: 44, label: t, kind: 'pos', size: 11.5 });
      });
    }
    for (const b of boxes) s += orgBox(b);
    const lx = 420, ly = 505;
    s += `<rect x="${lx}" y="${ly}" width="712" height="168" rx="4" fill="#FAFAFA" stroke="#B9BEC3"/>`;
    s += tb(lx + 16, ly + 22, 'Условные обозначения (ARIS, Organizational Chart)', { size: 12.5, weight: 'bold', anchor: 'start', nowrap: true }).svg;
    s += orgBox({ x: lx + 110, y: ly + 64, w: 190, h: 40, label: 'Должность', kind: 'pos', size: 11.5 });
    s += orgBox({ x: lx + 335, y: ly + 64, w: 230, h: 40, label: 'Организационная единица', kind: 'unit', size: 11.5 });
    s += `<rect x="${lx + 480}" y="${ly + 48}" width="44" height="32" rx="6" fill="none" stroke="${C.impr}" stroke-width="3"/>`;
    s += tb(lx + 534, ly + 64, 'объект\nисследования', { size: 11.5, anchor: 'start', nowrap: true }).svg;
    s += tb(lx + 16, ly + 116, 'Численность группы: более 49 тыс. человек (2025 г.).', { size: 12, anchor: 'start', nowrap: true }).svg;
    s += tb(lx + 16, ly + 142, 'Структура укрупненная, составлена по открытым данным.', { size: 12, anchor: 'start', nowrap: true, fill: C.muted }).svg;
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };

  // ---------- 2. Процессы верхнего уровня (ARIS VAD) ----------
  DIAGRAMS.vad = () => {
    const W = 1150, H = 676;
    let s = '';
    const band = (y, h, title) => `<rect x="14" y="${y}" width="${W - 28}" height="${h}" rx="4" fill="#F7F8FA" stroke="#B9BEC3"/>` + tb(30, y + 18, title, { size: 13.5, weight: 'bold', anchor: 'start', nowrap: true }).svg;
    const chev = (x, y, w, h, code, name, o = {}) => {
      let r = vchev(x, y, w, h, o);
      const size = o.size || 11.2;
      const d = o.first ? 0 : Math.min(22, h * 0.28);
      const cx = x + d / 2 + (w - d) / 2 - 6;
      const mw = w - d - 34;
      const t = tb(cx, 0, name, { size, maxW: mw, weight: 'bold' });
      const top = y + 18 + (h - 18 - (16 + t.h)) / 2;
      r += tb(cx, top, code, { size: 12.5, weight: 'bold', valign: 'top', nowrap: true }).svg;
      r += tb(cx, top + 16, name, { size, maxW: mw, valign: 'top', weight: 'bold' }).svg;
      return r;
    };
    s += band(14, 148, 'Процессы управления');
    const U = [['У1', 'Стратегическое управление и развитие сети'], ['У2', 'Финансовое управление и бюджетирование'], ['У3', 'Управление ассортиментом и ценовыми точками'], ['У4', 'Управление качеством и соответствием требованиям ЕАЭС']];
    U.forEach(([c, n], i) => (s += chev(30 + i * 274, 50, 268, 92, c, n, { first: i === 0 })));
    s += band(184, 270, 'Основные процессы (цепочка создания ценности)');
    const io = (x, w, text) => {
      let r = hexEvent(x, 274, w, 94);
      r += tb(x + w / 2, 327, text, { size: 11, weight: 'bold', maxW: w - 26 }).svg;
      return r;
    };
    s += io(24, 110, 'Запросы покупателей');
    s += chev(142, 274, 170, 94, 'О1', 'Планирование ассортимента и закупок');
    s += chev(316, 226, 170, 86, 'О2', 'Импорт товаров из КНР', { hl: true });
    s += chev(316, 324, 170, 86, 'О2а', 'Закупки у российских поставщиков', { size: 10.6 });
    s += chev(498, 274, 170, 94, 'О3', 'Логистика: распредели­тельные центры');
    s += chev(672, 274, 170, 94, 'О4', 'Продажи: магазины сети и франчайзи');
    s += chev(846, 274, 170, 94, 'О5', 'Работа с покупателями, лояльность');
    s += io(1022, 106, 'Товар у покупателя');
    s += tb(401, 436, 'объект исследования: О2', { size: 12, weight: 'bold', fill: C.impr, nowrap: true }).svg;
    s += band(486, 176, 'Обеспечивающие процессы');
    const S = [['В1', 'Бухгалтерский учет и валютный контроль'], ['В2', 'Контроль качества и сертификация'], ['В3', 'Управление персоналом'], ['В4', 'ИТ-обеспечение (Fix Price IT)'], ['В5', 'Развитие сети и недвижимость'], ['В6', 'Правовое сопровождение']];
    S.forEach(([c, n], i) => (s += chev(30 + i * 182, 526, 176, 108, c, n, { first: i === 0 })));
    const blockArrow = (x, y1, y2) => {
      const d = y2 > y1 ? 1 : -1;
      return `<path d="M${x - 9},${y1} L${x + 9},${y1} L${x + 9},${y2 - d * 10} L${x + 17},${y2 - d * 10} L${x},${y2} L${x - 17},${y2 - d * 10} L${x - 9},${y2 - d * 10} z" fill="#B8C2CE"/>`;
    };
    s += blockArrow(220, 164, 182) + blockArrow(900, 164, 182);
    s += blockArrow(220, 484, 456) + blockArrow(900, 484, 456);
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };

  // ---------- 3. Границы процесса: контекстная диаграмма IDEF0 ----------
  DIAGRAMS.context = () => {
    const W = 1120, H = 650;
    let s = '';
    const bx1 = 400, bx2 = 720, by1 = 262, by2 = 432;
    const ln = (pts) => conn(pts, { arrow: true, r: 7 });
    const lab = (x, y, t, anchor = 'start', maxW = 350) => tb(x, y, t, { size: 12.5, anchor, maxW, valign: 'bottom', halo: 3 }).svg;
    s += box(bx1, by1, bx2 - bx1, by2 - by1, 'func', { r: 5 }) + iconFunc(bx1 + 10, by1 + 9, 1.1);
    s += tb((bx1 + bx2) / 2, (by1 + by2) / 2 - 10, 'Импорт товаров из КНР', { size: 17, weight: 'bold', maxW: 290 }).svg;
    s += tb((bx1 + bx2) / 2, (by1 + by2) / 2 + 30, 'от плана закупок до готовности товара к отгрузке в магазины', { size: 12, weight: 'bold', maxW: 270, fill: '#24420A' }).svg;
    s += tb(bx2 - 10, by2 - 12, 'А0', { size: 12.5, weight: 'bold', anchor: 'end', nowrap: true }).svg;
    const ins = ['План закупок импортных товаров', 'Предложения фабрик через агентов', 'Денежные средства (юани)', 'Товар фабрики в КНР'];
    ins.forEach((t, i) => { const y = 290 + i * 40; s += ln([[30, y], [bx1, y]]) + lab(36, y - 5, t); });
    const outs = ['Товар на РЦ, готов к отгрузке', 'Себестоимость партии', 'ДТ, декларации, коды маркировки', 'Претензия агенту'];
    outs.forEach((t, i) => { const y = 290 + i * 40; s += ln([[bx2, y], [W - 24, y]]) + lab(bx2 + 12, y - 5, t); });
    const ctlL = [['Таможенный кодекс ЕАЭС, закон № 289-ФЗ', 530], ['Закон № 173-ФЗ, Инструкция Банка России № 181-И (валютный контроль)', 480], ['Технические регламенты ЕАЭС, правила маркировки', 430]];
    ctlL.forEach(([t, x], i) => { const y = 62 + i * 52; s += ln([[30, y], [x, y], [x, by1]]) + lab(36, y - 5, t, 'start', 430); });
    const ctlR = [['Контракт с агентом, Инкотермс 2020', 600], ['Ценовые точки, регламенты компании', 660]];
    ctlR.forEach(([t, x], i) => { const y = 62 + i * 52; s += ln([[W - 24, y], [x, y], [x, by1]]) + lab(W - 30, y - 5, t, 'end', 380); });
    const mL = [['Коммерческая дирекция', 430], ['Контроль качества и сертификация', 480], ['Логистика, распределительные центры', 530]];
    mL.forEach(([t, x], i) => { const y = 490 + i * 50; s += ln([[30, y], [x, y], [x, by2]]) + lab(36, y - 5, t); });
    const mR = [['ИТ-сервис для поставщиков КНР, LEAD WMS', 660], ['Агенты, банк, экспедитор, брокер', 600]];
    mR.forEach(([t, x], i) => { const y = 490 + i * 50; s += ln([[W - 24, y], [x, y], [x, by2]]) + lab(W - 30, y - 5, t, 'end', 380); });
    const side = (x, y, t, a = 'start') => tb(x, y, t, { size: 12, weight: 'bold', fill: '#3A3F45', anchor: a, nowrap: true }).svg;
    s += side(30, 20, 'УПРАВЛЕНИЕ (нормы и правила)') + side(30, 250, 'ВХОДЫ') + side(W - 24, 250, 'ВЫХОДЫ', 'end') + side(30, 636, 'МЕХАНИЗМЫ (исполнители и ресурсы)');
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };

  // ---------- 4. Декомпозиция процесса О2 (VAD 2-го уровня) ----------
  DIAGRAMS.decomp = () => {
    const W = 1120, H = 452;
    let s = '';
    const st = [
      ['1', 'Формирование заказа', 'Категорийный менеджер'],
      ['2', 'Поиск фабрики и согласование образца', 'Категорийный менеджер, агент в КНР'],
      ['3', 'Упаковка и размещение заказа', 'Категорийный менеджер, отдел импорта'],
      ['4', 'Сертификация и оплата аванса', 'Контроль качества, финансовая служба'],
      ['5', 'Производство на фабрике', 'Фабрика (контроль: агент, отдел импорта)'],
      ['6', 'Инспекция, оплата и отгрузка', 'Контроль качества, финансы, логистика'],
      ['7', 'Международная перевозка', 'Экспедитор (контроль: логистика)'],
      ['8', 'Таможенное оформление', 'Отдел импорта, таможенный представитель'],
      ['9', 'Доставка на РЦ и приемка', 'Транспортная логистика, РЦ'],
      ['10', 'Распределение по магазинам', 'Категорийный менеджер, РЦ'],
    ];
    s += tb(20, 22, 'Начало: утвержден план закупок. Окончание: товар на РЦ готов к отгрузке в магазины.', { size: 13, anchor: 'start', nowrap: true, weight: 'bold' }).svg;
    st.forEach(([n, name, own], i) => {
      const row = Math.floor(i / 5), k = i % 5;
      const x = 20 + k * 216, y = 46 + row * 196;
      const ext = i === 4 || i === 6;
      const first = k === 0 && row === 0;
      s += conn([[x + 104, y + 92], [x + 104, y + 114]], { color: LINE, sw: 1.3 });
      s += vchev(x, y, 206, 92, { first, kind: ext ? 'doc' : 'func' });
      const cx = x + (first ? 103 : 112) - 4;
      const t = tb(cx, 0, name, { size: 11.2, maxW: 150, weight: 'bold' });
      const top = y + 16 + (92 - 16 - (17 + t.h)) / 2;
      s += tb(cx, top, n, { size: 13, weight: 'bold', valign: 'top', nowrap: true }).svg;
      s += tb(cx, top + 17, name, { size: 11.2, maxW: 150, valign: 'top', weight: 'bold' }).svg;
      s += orgBox({ x: x + 104, y: y + 140, w: 200, h: 52, label: own, kind: 'unit', size: 10.4 });
    });
    s += tb(20, 440, 'Серым выделены этапы внешних участников, под этапами показаны исполнители (организационные единицы).', { size: 12, anchor: 'start', nowrap: true, fill: C.muted }).svg;
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };

  // ---------- 5. Условные обозначения BPMN ----------
  DIAGRAMS.legend = () => {
    const W = 1680, H = 258;
    let s = '';
    const colW = 336, rowH = 80;
    const cell = (c, r) => [20 + c * colW, 26 + r * rowH];
    const txt = (x, y, t) => tb(x, y, t, { size: 12, anchor: 'start', maxW: 240 }).svg;
    const node = (type, c, r, label, dx = 24) => {
      const [x, y] = cell(c, r);
      const n = { type, x: x + dx, y: y + 22 };
      sizeNode(n);
      return drawNode(n) + txt(x + dx + 34, y + 22, label);
    };
    s += node('start', 0, 0, 'Стартовое событие');
    s += node('msg', 1, 0, 'Промежуточное событие: получено сообщение');
    s += node('linkOut', 2, 0, 'Событие-ссылка: переход к другой части схемы');
    s += node('end', 3, 0, 'Конечное событие');
    {
      const [x, y] = cell(4, 0);
      s += box(x, y + 4, 64, 36, 'ext', { r: 2 }) + txt(x + 78, y + 22, 'Свернутый пул внешнего участника');
    }
    {
      const [x, y] = cell(0, 1);
      s += box(x, y, 70, 46, 'func') + iconFunc(x + 6, y + 5, 0.75) + txt(x + 84, y + 23, 'Задача (выполняет сотрудник)');
    }
    {
      const [x, y] = cell(1, 1);
      s += box(x, y, 70, 46, 'func') + iconGears(x + 6, y + 4, 0.8) + txt(x + 84, y + 23, 'Сервисная задача (выполняется в ИТ-системе)');
    }
    s += node('xor', 2, 1, 'Исключающий шлюз (выбор одной ветви)', 28);
    s += node('and', 3, 1, 'Параллельный шлюз (все ветви одновременно)', 28);
    {
      const [x, y] = cell(4, 1);
      s += `<rect x="${x}" y="${y}" width="64" height="44" fill="#fff" stroke="${C.laneS}"/><rect x="${x}" y="${y}" width="9" height="44" fill="url(#g_hdr)" stroke="${C.laneS}"/><rect x="${x + 9}" y="${y}" width="12" height="44" fill="url(#g_hdr)" stroke="${C.laneS}"/><line x1="${x + 9}" y1="${y + 22}" x2="${x + 64}" y2="${y + 22}" stroke="${C.laneS}"/>` + txt(x + 78, y + 22, 'Пул компании, разделенный на дорожки');
    }
    {
      const [x, y] = cell(0, 2);
      s += conn([[x, y + 22], [x + 62, y + 22]], { arrow: true }) + txt(x + 78, y + 22, 'Поток управления');
    }
    {
      const [x, y] = cell(1, 2);
      s += `<line x1="${x + 4}" y1="${y + 22}" x2="${x + 62}" y2="${y + 22}" stroke="${C.msg}" stroke-width="1.2" stroke-dasharray="6 4" marker-start="url(#msgStart)" marker-end="url(#msgEnd)"/>` + txt(x + 78, y + 22, 'Поток сообщений (обмен с внешним участником)');
    }
    {
      const [x, y] = cell(2, 2);
      s += badge(x + 30, y + 14, 'П1', C.prob) + badge(x + 66, y + 14, 'И1', C.impr) + txt(x + 78, y + 22, 'Номер проблемы (п. 10) и изменения (п. 11)');
    }
    {
      const [x, y] = cell(3, 2);
      s += tb(x + 62, y + 22, '3 дн.', { size: 11, anchor: 'end', nowrap: true, fill: '#20380A' }).svg + txt(x + 78, y + 22, 'Длительность (оценка), внизу справа в задаче');
    }
    return { svg: wrapSvg(W, H, s), w: W, h: H };
  };

  // ================= AS IS =================
  // Часть 1: выбор товара и размещение заказа
  DIAGRAMS.asis1 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'rk', name: RK, h: 140 }, { id: 'km', name: KM, h: 204 }],
    top: [{ name: AG, from: 0, to: 99 }],
    nodes: [
      { id: 's1', type: 'start', lane: 'km', col: 0, label: 'Утвержден план закупок на сезон' },
      { id: 'a1', type: 'task', lane: 'km', col: 1, label: 'Сформировать заказ: товар, количество, ценовая точка', dur: '3 дн.' },
      { id: 'a2', type: 'task', lane: 'km', col: 2, label: 'Направить агенту техническое задание на товар' },
      { id: 'e1', type: 'msg', lane: 'km', col: 3, label: 'Получены предложения и образцы (10 дн.)' },
      { id: 'a3', type: 'task', lane: 'km', col: 4, label: 'Оценить образцы, рассчитать себестоимость под ценовую точку', dur: '2 дн.', badge: 'П1' },
      { id: 'a4', type: 'task', lane: 'rk', col: 5, label: 'Рассмотреть товар и цену', dur: '3 дн.', badge: 'П1' },
      { id: 'g1', type: 'xor', lane: 'rk', col: 6, label: 'Утверждено?', lpos: 'bottom' },
      { id: 'a5', type: 'task', lane: 'km', col: 7, label: 'Разместить заказ у агента', dur: '2 дн.' },
      { id: 'a6', type: 'task', lane: 'km', col: 8, label: 'Согласовать упаковку и надписи на русском языке', badge: 'П3' },
      { id: 'g1b', type: 'xor', lane: 'km', col: 9, label: 'Макет принят?' },
      { id: 'L1', type: 'linkOut', lane: 'km', col: 10, label: 'Переход к части 2 (А)' },
    ],
    flows: [
      ['s1', 'a1'], ['a1', 'a2'], ['a2', 'e1'], ['e1', 'a3'], ['a3', 'a4'], ['a4', 'g1'],
      ['g1', 'a5', { fa: 'R', ta: 'L', label: 'да', mx: (P) => P.a5.x - 76 }],
      ['g1', 'a2', { fa: 'T', ta: 'T', tdx: 34, label: 'нет, новый образец (40%)', via: (P) => [[P.g1.x, P.laneTop('rk') + 13], [P.a2.x + 34, P.laneTop('rk') + 13]] }],
      ['a5', 'a6'], ['a6', 'g1b'],
      ['g1b', 'L1', { label: 'да' }],
      ['g1b', 'a6', { fa: 'B', ta: 'B', label: 'нет, переделка (20%, 7 дн.)', lp: [-8, 60], la: 'end', via: (P) => [[P.g1b.x, P.a6.y + 64], [P.a6.x, P.a6.y + 64]] }],
    ],
    msgs: [
      { node: 'a2', pool: AG, dx: -20, dir: 'out', side: 'l', label: 'ТЗ, целевая цена', lw: 90 },
      { node: 'e1', pool: AG, dir: 'in', label: 'Предложения, образцы', lw: 90 },
      { node: 'a5', pool: AG, dir: 'out', label: 'Заказ', lw: 90 },
      { node: 'a6', pool: AG, dx: -16, dir: 'out', label: 'Макет упаковки', lw: 80 },
      { node: 'a6', pool: AG, dx: 16, dir: 'in', label: 'Правки', lw: 80 },
    ],
  });

  // Часть 2: сертификация, оплата и производство
  DIAGRAMS.asis2 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'imp', name: IMP, h: 140 }, { id: 'kk', name: KK, h: 262 }, { id: 'fin', name: F, h: 130 }],
    top: [{ name: LAB, from: 0, to: 3 }, { name: AG, from: 4, to: 99 }],
    bottom: [{ name: GIS, from: 0, to: 4 }, { name: BANK, from: 5, to: 99 }],
    nodes: [
      { id: 'L2', type: 'linkIn', lane: 'imp', col: 0, label: 'Из части 1 (А)' },
      { id: 'gA', type: 'xor', lane: 'kk', dy: MAIN, col: 1, label: 'Есть действующая декларация?', lpos: 'bottom', lw: 120 },
      { id: 'b2', type: 'task', lane: 'kk', dy: UP, col: 2, label: 'Провести испытания и оформить декларацию соответствия', dur: '21 дн.', badge: 'П2', boxW: 150, slot: 172 },
      { id: 'gB', type: 'xor', lane: 'kk', dy: MAIN, col: 3 },
      { id: 'b5', type: 'task', lane: 'imp', col: 4, label: 'Заказать коды маркировки и передать фабрике через ИТ-сервис' },
      { id: 'b3', type: 'task', lane: 'imp', col: 5, label: 'Оформить служебную записку на аванс', dur: '1 дн.', badge: 'П4' },
      { id: 'b4', type: 'task', lane: 'fin', col: 6, label: 'Оплатить аванс агенту', dur: '6 дн.', badge: 'П4' },
      { id: 'e2', type: 'msg', lane: 'imp', col: 7, label: 'Партия готова (35 дн.)' },
      { id: 'b6', type: 'task', lane: 'kk', dy: MAIN, col: 8, label: 'Провести инспекцию партии перед отгрузкой', dur: '2 дн.' },
      { id: 'g2', type: 'xor', lane: 'kk', dy: MAIN, col: 9, label: 'Брак выявлен?', lpos: 'bottom' },
      { id: 'b7', type: 'task', lane: 'kk', dy: UP, col: 10, label: 'Направить замечания агенту, дождаться исправления', dur: '10 дн.' },
      { id: 'b8', type: 'task', lane: 'fin', col: 11, label: 'Оплатить остаток по служебной записке', dur: '7 дн.', badge: 'П4' },
      { id: 'L3', type: 'linkOut', lane: 'imp', col: 12, label: 'Переход к части 3 (Б)' },
    ],
    flows: [
      ['L2', 'gA', { fa: 'R', ta: 'L' }],
      ['gA', 'b2', { label: 'нет (50%)' }],
      ['gA', 'gB', { label: 'да' }],
      ['b2', 'gB'],
      ['gB', 'b5'], ['b5', 'b3'], ['b3', 'b4'], ['b4', 'e2'], ['e2', 'b6'], ['b6', 'g2'],
      ['g2', 'b7', { label: 'да (10%)' }],
      ['b7', 'b6', { fa: 'T', ta: 'T', fdx: -30, via: (P) => [[P.b7.x - 30, P.laneTop('kk') + 7], [P.b6.x, P.laneTop('kk') + 7]] }],
      ['g2', 'b8', { fa: 'R', ta: 'L', label: 'нет', mx: (P) => P.b8.x - 76 }],
      ['b8', 'L3'],
    ],
    msgs: [
      { node: 'b2', pool: LAB, dx: -16, dir: 'out', label: 'Образцы, документы', lw: 80 },
      { node: 'b2', pool: LAB, dx: 16, dir: 'in', label: 'Протокол испытаний', lw: 80 },
      { node: 'b5', pool: GIS, dir: 'in', label: 'Коды маркировки', lw: 80 },
      { node: 'b5', pool: AG, dir: 'out', label: 'Коды для нанесения', lw: 80 },
      { node: 'b4', pool: BANK, dir: 'out', label: 'Платеж (аванс)', lw: 90 },
      { node: 'e2', pool: AG, dir: 'in', label: 'Уведомление о готовности', lw: 90 },
      { node: 'b7', pool: AG, dx: 14, dir: 'out', side: 'l', label: 'Замечания', lw: 80 },
      { node: 'b7', pool: AG, dx: 36, dir: 'in', label: 'Исправленная партия', lw: 90 },
      { node: 'b8', pool: BANK, dir: 'out', side: 'l', label: 'Платеж (остаток)', lw: 90 },
    ],
  });

  // Часть 3: отгрузка, перевозка и таможенное оформление
  DIAGRAMS.asis3 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'imp', name: IMP, h: 262 }, { id: 'log', name: LG, h: 130 }, { id: 'fin', name: F, h: 130 }],
    top: [{ name: AG, from: 0, to: 99 }],
    bottom: [{ name: FWD, from: 0, to: 4 }, { name: BROKER, from: 5, to: 7 }, { name: CUST, from: 8, to: 99 }],
    nodes: [
      { id: 'L4', type: 'linkIn', lane: 'log', col: 0, label: 'Из части 2 (Б)' },
      { id: 'c1', type: 'task', lane: 'log', col: 1, label: 'Запросить ставки и забронировать контейнер', dur: '7 дн.', badge: 'П5' },
      { id: 'e3', type: 'msg', lane: 'imp', dy: MAIN, col: 2, label: 'Товар отгружен, документы получены (3 дн.)', slot: 190, lw: 104 },
      { id: 'c2', type: 'task', lane: 'log', col: 3, label: 'Контролировать перевозку по данным экспедитора', dur: '35 дн. в пути' },
      { id: 'e4', type: 'msg', lane: 'log', col: 4, label: 'Контейнер прибыл, размещен на СВХ', lpos: 'top' },
      { id: 'c3', type: 'task', lane: 'imp', dy: MAIN, col: 5, label: 'Передать документы таможенному представителю', dur: '2 дн.', badge: 'П6' },
      { id: 'g3', type: 'xor', lane: 'imp', dy: MAIN, col: 6, label: 'Замечания к документам?', lpos: 'bottom' },
      { id: 'c4', type: 'task', lane: 'imp', dy: UP, col: 7, label: 'Запросить исправленные документы у агента', dur: '4 дн.', badge: 'П6' },
      { id: 'c5', type: 'task', lane: 'fin', col: 8, label: 'Оплатить таможенные платежи', dur: '1 дн.' },
      { id: 'e5', type: 'msg', lane: 'imp', dy: MAIN, col: 9, label: 'Товар выпущен (1 дн.)', lpos: 'top' },
      { id: 'L5', type: 'linkOut', lane: 'imp', dy: MAIN, col: 10, label: 'Переход к части 4 (В)' },
    ],
    flows: [
      ['L4', 'c1'], ['c1', 'e3', { mx: (P) => P.e3.x - 62 }], ['e3', 'c2', { mx: (P) => P.e3.x + 62 }], ['c2', 'e4'], ['e4', 'c3'], ['c3', 'g3'],
      ['g3', 'c4', { label: 'да (30%)' }],
      ['c4', 'c3', { fa: 'T', ta: 'T', fdx: -30, via: (P) => [[P.c4.x - 30, P.laneTop('imp') + 7], [P.c3.x, P.laneTop('imp') + 7]] }],
      ['g3', 'c5', { fa: 'R', ta: 'L', label: 'нет', mx: (P) => P.c5.x - 76 }],
      ['c5', 'e5'], ['e5', 'L5'],
    ],
    msgs: [
      { node: 'c1', pool: FWD, dx: -16, dir: 'out', label: 'Запрос ставок', lw: 80 },
      { node: 'c1', pool: FWD, dx: 16, dir: 'in', label: 'Бронь', lw: 70 },
      { node: 'e3', pool: AG, dir: 'in', label: 'Инвойс, упаковочный лист, коносамент', lw: 110 },
      { node: 'c2', pool: FWD, dir: 'in', label: 'Статус', lw: 70 },
      { node: 'e4', pool: FWD, dir: 'in', label: 'Уведомление о прибытии', lw: 84 },
      { node: 'c3', pool: BROKER, dir: 'out', label: 'Документы для ДТ', lw: 90 },
      { node: 'c4', pool: AG, dx: 14, dir: 'out', side: 'l', label: 'Замечания', lw: 80 },
      { node: 'c4', pool: AG, dx: 36, dir: 'in', label: 'Исправленные документы', lw: 96 },
      { node: 'c5', pool: CUST, dir: 'out', side: 'l', label: 'Таможенные платежи', lw: 90 },
      { node: 'e5', pool: CUST, dir: 'in', label: 'Решение о выпуске', lw: 90 },
    ],
  });

  // Часть 4: доставка на РЦ, приемка и распределение по магазинам
  DIAGRAMS.asis4 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'imp', name: IMP, h: 130 }, { id: 'km', name: KM, h: 130 }, { id: 'log', name: LG, h: 130 }, { id: 'dc', name: DC, h: 130 }],
    top: [{ name: AG, from: 0, to: 99 }],
    nodes: [
      { id: 'L6', type: 'linkIn', lane: 'log', col: 0, label: 'Из части 3 (В)' },
      { id: 'd1', type: 'task', lane: 'log', col: 1, label: 'Заказать транспорт и вывезти контейнер на РЦ', dur: '2 дн.' },
      { id: 'd2', type: 'task', lane: 'dc', col: 2, label: 'Ожидать свободное окно разгрузки', dur: '2 дн.', badge: 'П7' },
      { id: 'd3', type: 'task', lane: 'dc', col: 3, label: 'Принять товар в LEAD WMS, проверить коды маркировки', dur: '1 дн.' },
      { id: 'g4', type: 'xor', lane: 'dc', col: 4, label: 'Расхождения есть?', lpos: 'bottom' },
      { id: 'd4', type: 'task', lane: 'imp', col: 5, label: 'Направить претензию агенту', dur: '5 дн.' },
      { id: 'g5', type: 'xor', lane: 'dc', col: 6 },
      { id: 'd5', type: 'task', lane: 'km', col: 7, label: 'Рассчитать распределение товара по магазинам', dur: '3 дн.', badge: 'П8' },
      { id: 'end1', type: 'end', lane: 'dc', col: 8, label: 'Товар готов к отгрузке в магазины', lw: 140, slot: 156 },
    ],
    flows: [
      ['L6', 'd1'], ['d1', 'd2'], ['d2', 'd3'], ['d3', 'g4'],
      ['g4', 'd4', { label: 'да (20%)' }], ['g4', 'g5', { label: 'нет' }], ['d4', 'g5'],
      ['g5', 'd5', { fa: 'R', ta: 'L' }], ['d5', 'end1'],
    ],
    msgs: [{ node: 'd4', pool: AG, dir: 'out', label: 'Акт, претензия', lw: 90 }],
  });

  // ================= TO BE =================
  // Часть 1: выбор товара и размещение заказа
  DIAGRAMS.tobe1 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'rk', name: RK, h: 140 }, { id: 'km', name: KM, h: 150 }],
    top: [{ name: AG, from: 0, to: 99 }],
    nodes: [
      { id: 's2', type: 'start', lane: 'km', col: 0, label: 'Утвержден план закупок на сезон' },
      { id: 'h1', type: 'task', lane: 'km', col: 1, label: 'Сформировать заказ: товар, количество, ценовая точка', dur: '3 дн.' },
      { id: 'h2', type: 'task', lane: 'km', col: 2, label: 'Направить агенту ТЗ и шаблон упаковки на русском языке', badge: 'И3' },
      { id: 'e1', type: 'msg', lane: 'km', col: 3, label: 'Получены фото и видео образцов (5 дн.)' },
      { id: 'h3', type: 'task', lane: 'km', col: 4, label: 'Оценить образцы онлайн вместе с агентом, рассчитать себестоимость', dur: '2 дн.', badge: 'И1' },
      { id: 'h4', type: 'task', lane: 'rk', col: 5, label: 'Утвердить товар и цену на онлайн-комитете', dur: '1 дн.', badge: 'И1' },
      { id: 'g1', type: 'xor', lane: 'rk', col: 6, label: 'Утверждено?', lpos: 'bottom' },
      { id: 'h5', type: 'task', lane: 'km', col: 7, label: 'Разместить заказ с согласованным макетом упаковки', dur: '1 дн.', badge: 'И3' },
      { id: 'L7', type: 'linkOut', lane: 'km', col: 8, label: 'Переход к части 2 (А)' },
    ],
    flows: [
      ['s2', 'h1'], ['h1', 'h2'], ['h2', 'e1'], ['e1', 'h3'], ['h3', 'h4'], ['h4', 'g1'],
      ['g1', 'h5', { fa: 'R', ta: 'L', label: 'да', mx: (P) => P.h5.x - 76 }],
      ['g1', 'h3', { fa: 'T', ta: 'T', label: 'нет, онлайн-доработка (40%)', via: (P) => [[P.g1.x, P.laneTop('rk') + 13], [P.h3.x, P.laneTop('rk') + 13]] }],
      ['h5', 'L7'],
    ],
    msgs: [
      { node: 'h2', pool: AG, dir: 'out', label: 'ТЗ, шаблон упаковки', lw: 90 },
      { node: 'e1', pool: AG, dir: 'in', label: 'Фото и видео образцов', lw: 90 },
      { node: 'h5', pool: AG, dir: 'out', label: 'Заказ, макет', lw: 90 },
    ],
  });

  // Часть 2: оплата, параллельная подготовка, производство, инспекция
  DIAGRAMS.tobe2 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'imp', name: IMP, h: 140 }, { id: 'kk', name: KK, h: 262 }, { id: 'log', name: LG, h: 130 }, { id: 'fin', name: F, h: 130 }],
    top: [{ name: LAB, from: 0, to: 3 }, { name: AG, from: 4, to: 99 }],
    bottom: [{ name: BANK, from: 0, to: 2 }, { name: GIS, from: 3, to: 99 }],
    nodes: [
      { id: 'L8', type: 'linkIn', lane: 'imp', col: 0, label: 'Из части 1 (А)' },
      { id: 'k3', type: 'svc', lane: 'fin', col: 1, label: 'Оплатить аванс по платежному календарю', dur: '3 дн.', badge: 'И4' },
      { id: 'g6', type: 'and', lane: 'kk', dy: MAIN, col: 2 },
      { id: 'k1', type: 'task', lane: 'kk', dy: MAIN, col: 3, label: 'Оформить декларацию на новые позиции параллельно с производством', dur: '21 дн., параллельно', badge: 'И2', boxW: 150, slot: 172 },
      { id: 'k7', type: 'task', lane: 'log', col: 3, label: 'Забронировать контейнер на плановую дату готовности', dur: '1 дн.', badge: 'И5', boxW: 150, slot: 172 },
      { id: 'k2', type: 'task', lane: 'imp', col: 4, label: 'Заказать коды маркировки и передать фабрике через ИТ-сервис' },
      { id: 'g7', type: 'and', lane: 'kk', dy: MAIN, col: 5 },
      { id: 'e6', type: 'msg', lane: 'imp', col: 6, label: 'Партия готова (35 дн.)' },
      { id: 'k4', type: 'task', lane: 'kk', dy: MAIN, col: 7, label: 'Инспекция партии и проверка проектов документов', dur: '2 дн.', badge: 'И6' },
      { id: 'g8', type: 'xor', lane: 'kk', dy: MAIN, col: 8, label: 'Брак или ошибки?', lpos: 'bottom' },
      { id: 'k5', type: 'task', lane: 'kk', dy: UP, col: 9, label: 'Направить замечания агенту, дождаться исправления', dur: '10 дн.' },
      { id: 'e7', type: 'msg', lane: 'imp', col: 10, label: 'Товар отгружен, копия коносамента получена' },
      { id: 'L9', type: 'linkOut', lane: 'imp', col: 11, label: 'Переход к части 3 (Б)' },
    ],
    flows: [
      ['L8', 'k3'],
      ['k3', 'g6', { fa: 'T', ta: 'L' }],
      ['g6', 'k1'],
      ['g6', 'k2', { fa: 'T', ta: 'L' }],
      ['g6', 'k7', { fa: 'B', ta: 'L' }],
      ['k1', 'g7'],
      ['k2', 'g7', { fa: 'R', ta: 'T' }],
      ['k7', 'g7', { fa: 'R', ta: 'B' }],
      ['g7', 'e6', { fa: 'R', ta: 'L' }],
      ['e6', 'k4'], ['k4', 'g8'],
      ['g8', 'k5', { label: 'да (10%)' }],
      ['k5', 'k4', { fa: 'T', ta: 'T', fdx: -30, via: (P) => [[P.k5.x - 30, P.laneTop('kk') + 7], [P.k4.x, P.laneTop('kk') + 7]] }],
      ['g8', 'e7', { fa: 'R', ta: 'L', label: 'нет', mx: (P) => P.e7.x - 60 }],
      ['e7', 'L9'],
    ],
    msgs: [
      { node: 'k3', pool: BANK, dir: 'out', label: 'Платеж (аванс)', lw: 90 },
      { node: 'k1', pool: LAB, dx: -16, dir: 'out', label: 'Образцы, документы', lw: 80 },
      { node: 'k1', pool: LAB, dx: 16, dir: 'in', label: 'Протокол испытаний', lw: 80 },
      { node: 'k2', pool: GIS, dir: 'in', label: 'Коды маркировки', lw: 80 },
      { node: 'k2', pool: AG, dir: 'out', label: 'Коды для нанесения', lw: 80 },
      { node: 'e6', pool: AG, dir: 'in', label: 'Уведомление, проекты документов', lw: 100 },
      { node: 'k5', pool: AG, dx: 14, dir: 'out', side: 'l', label: 'Замечания', lw: 80 },
      { node: 'k5', pool: AG, dx: 36, dir: 'in', label: 'Исправления', lw: 80 },
      { node: 'e7', pool: AG, dir: 'in', label: 'Документы, копия коносамента', lw: 100 },
    ],
  });

  // Часть 3: перевозка, предварительное декларирование, план распределения
  DIAGRAMS.tobe3 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'imp', name: IMP, h: 140 }, { id: 'km', name: KM, h: 130 }, { id: 'log', name: LG, h: 130 }, { id: 'fin', name: F, h: 130 }],
    top: [{ name: BROKER, from: 0, to: 2 }, { name: FWD, from: 3, to: 99 }],
    bottom: [{ name: BANK, from: 0, to: 2 }, { name: CUST, from: 3, to: 99 }],
    nodes: [
      { id: 'L10', type: 'linkIn', lane: 'km', col: 0, label: 'Из части 2 (Б)' },
      { id: 'g11', type: 'and', lane: 'km', col: 1 },
      { id: 'm2', type: 'task', lane: 'imp', col: 2, label: 'Передать проверенные документы брокеру для предварительной ДТ', dur: '1 дн., в пути', badge: 'И6' },
      { id: 'm5', type: 'task', lane: 'km', col: 2, label: 'Рассчитать распределение по магазинам до прибытия', dur: '1 дн., в пути', badge: 'И8' },
      { id: 'm1', type: 'svc', lane: 'fin', col: 2, label: 'Оплатить остаток против копии коносамента', dur: '5 дн., в пути', badge: 'И4' },
      { id: 'm4', type: 'task', lane: 'log', col: 3, label: 'Отслеживать ETA, забронировать окно разгрузки на РЦ', dur: '35 дн. в пути', badge: 'И7' },
      { id: 'm3', type: 'task', lane: 'fin', col: 3, label: 'Внести авансовые таможенные платежи', dur: '1 дн., в пути', badge: 'И6' },
      { id: 'e8', type: 'msg', lane: 'log', col: 4, label: 'Контейнер прибыл' },
      { id: 'g12', type: 'and', lane: 'km', col: 5 },
      { id: 'e9', type: 'msg', lane: 'imp', col: 6, label: 'Товар выпущен (1 дн.)', lpos: 'top' },
      { id: 'L11', type: 'linkOut', lane: 'imp', col: 7, label: 'Переход к части 4 (В)' },
    ],
    flows: [
      ['L10', 'g11'],
      ['g11', 'm2', { fa: 'T', ta: 'L' }],
      ['g11', 'm5'],
      ['g11', 'm4', { fa: 'B', ta: 'L' }],
      ['g11', 'm1', { fa: 'B', ta: 'L' }],
      ['m1', 'm3'],
      ['m4', 'e8'],
      ['m2', 'g12', { fa: 'R', ta: 'T' }],
      ['m5', 'g12'],
      ['e8', 'g12', { fa: 'R', ta: 'B' }],
      ['m3', 'g12', { fa: 'R', ta: 'B' }],
      ['g12', 'e9', { fa: 'R', ta: 'L', mx: (P) => P.e9.x - 50 }],
      ['e9', 'L11'],
    ],
    msgs: [
      { node: 'm1', pool: BANK, dir: 'out', label: 'Платеж (остаток)', lw: 90 },
      { node: 'm2', pool: BROKER, dir: 'out', side: 'l', label: 'Документы для предварительной ДТ', lw: 110 },
      { node: 'm3', pool: CUST, dir: 'out', label: 'Авансовые платежи', lw: 90 },
      { node: 'm4', pool: FWD, dx: -16, dir: 'in', side: 'l', label: 'Статус и ETA', lw: 80 },
      { node: 'm4', pool: FWD, dx: 16, dir: 'out', label: 'Заявка на вывоз', lw: 80 },
      { node: 'e8', pool: FWD, dir: 'in', label: 'Уведомление о прибытии', lw: 90 },
      { node: 'e9', pool: CUST, dir: 'in', label: 'Решение о выпуске', lw: 90 },
    ],
  });

  // Часть 4: доставка на РЦ, приемка и отгрузка по готовому распределению
  DIAGRAMS.tobe4 = () => bpmn({
    pool: POOL,
    lanes: [{ id: 'imp', name: IMP, h: 130 }, { id: 'log', name: LG, h: 130 }, { id: 'dc', name: DC, h: 130 }],
    top: [{ name: AG, from: 0, to: 99 }],
    nodes: [
      { id: 'L12', type: 'linkIn', lane: 'log', col: 0, label: 'Из части 3 (В)' },
      { id: 'n1', type: 'task', lane: 'log', col: 1, label: 'Доставить контейнер на РЦ к забронированному окну', dur: '1 дн.', badge: 'И7' },
      { id: 'n2', type: 'task', lane: 'dc', col: 2, label: 'Принять товар в LEAD WMS, проверить коды маркировки', dur: '1 дн.' },
      { id: 'g9', type: 'xor', lane: 'dc', col: 3, label: 'Расхождения есть?', lpos: 'bottom' },
      { id: 'n3', type: 'task', lane: 'imp', col: 4, label: 'Направить претензию агенту в день приемки', dur: 'в тот же день' },
      { id: 'g10', type: 'xor', lane: 'dc', col: 5 },
      { id: 'n4', type: 'svc', lane: 'dc', col: 6, label: 'Сформировать отгрузки по готовому распределению', dur: '0,5 дн.', badge: 'И8', boxW: 150, slot: 172 },
      { id: 'end2', type: 'end', lane: 'dc', col: 7, label: 'Товар готов к отгрузке в магазины', lw: 140, slot: 156 },
    ],
    flows: [
      ['L12', 'n1'], ['n1', 'n2'], ['n2', 'g9'], ['g9', 'n3', { label: 'да (20%)' }], ['g9', 'g10', { label: 'нет' }],
      ['n3', 'g10'], ['g10', 'n4'], ['n4', 'end2'],
    ],
    msgs: [{ node: 'n3', pool: AG, dir: 'out', label: 'Акт, фото, претензия', lw: 90 }],
  });

  window.DIAGRAMS = DIAGRAMS;
})();
