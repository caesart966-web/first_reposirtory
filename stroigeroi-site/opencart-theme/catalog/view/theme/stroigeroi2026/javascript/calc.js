/* ==========================================================================
   Строй-Герой — строительный калькулятор.

   Грузится только на странице калькулятора: 14 расчётов весят больше,
   чем весь app.js, а нужны на одной странице.

   Как устроено. Каждый расчёт — запись в CALCS: поля, формула и тексты.
   Разметку полей, выбор калькулятора, ответ, список покупок и отправку
   расчёта менеджеру делает общий движок ниже, поэтому новый калькулятор —
   это одна запись, без правки вёрстки и шаблонов.

   Правило то же, что было у первых трёх вкладок: чего нельзя знать
   за покупателя, мы не подставляем. Расход смеси и краски, вес мешка,
   площадь в упаковке, мощность секции радиатора — всё с упаковки, поля
   пустые. Геометрия (листы, плитка, ячейки потолка, кладка) считается
   явно, и каждое допущение — шаг стоек, шаг саморезов, длина профиля —
   видно и меняется в «Дополнительных параметрах».
   ========================================================================== */

(function () {
  'use strict';

  var root = document.querySelector('[data-calcs]');
  if (!root) return;

  var $ = function (sel, el) { return (el || document).querySelector(sel); };
  var $$ = function (sel, el) {
    return Array.prototype.slice.call((el || document).querySelectorAll(sel));
  };
  var NB = ' ';

  /* ======================================================================
     Числа и слова по-русски
     ====================================================================== */

  /* Дробная часть — через запятую, тысячи — пробелом: «1 910», «2,7». */
  function ru(value, digits) {
    return Number(value).toLocaleString('ru-RU', {
      minimumFractionDigits: digits || 0,
      maximumFractionDigits: digits === undefined ? 2 : digits
    });
  }

  /* Вверх до целого. Дроби в JS неточные: 90 м² гипсокартона с запасом
     10 % — ровно 33 листа, а деление даёт 33,00000000000001, и Math.ceil
     насчитывал 34. Хвост в миллиардную долю отбрасываем. */
  function up(x) { return Math.ceil(x - 1e-9); }

  /* 1 лист, 2 листа, 5 листов, 11 листов, 21 лист, 22 листа */
  function plural(n, forms) {
    var tens = n % 100;
    var unit = n % 10;
    if (tens >= 11 && tens <= 14) return forms[2];
    if (unit === 1) return forms[0];
    if (unit >= 2 && unit <= 4) return forms[1];
    return forms[2];
  }

  /* «2,7» и «2.7» — одно и то же; пустое поле — NaN, а не ноль. */
  function parse(raw) {
    var text = String(raw).replace(/[\s ]/g, '').replace(',', '.');
    if (text === '') return NaN;
    var v = Number(text);
    return isFinite(v) ? v : NaN;
  }

  function pos(x) { return typeof x === 'number' && !isNaN(x) && x > 0; }
  function reserveOf(x) { return pos(x) ? x : 0; }

  var W = {
    sheet: ['лист', 'листа', 'листов'],
    bag: ['мешок', 'мешка', 'мешков'],
    can: ['банка', 'банки', 'банок'],
    roll: ['рулон', 'рулона', 'рулонов'],
    pack: ['упаковка', 'упаковки', 'упаковок'],
    tile: ['плитка', 'плитки', 'плиток'],
    plate: ['плита', 'плиты', 'плит'],
    panel: ['панель', 'панели', 'панелей'],
    brick: ['кирпич', 'кирпича', 'кирпичей'],
    block: ['блок', 'блока', 'блоков'],
    pallet: ['поддон', 'поддона', 'поддонов'],
    section: ['секция', 'секции', 'секций']
  };

  function qty(it) {
    return ru(it.n) + NB + (Array.isArray(it.unit) ? plural(it.n, it.unit) : it.unit);
  }

  /* Лишних нулей не печатаем: «20 м²», «2,7 м», а не «20,0 м²» */
  var m2 = function (x) { return ru(x) + NB + 'м²'; };
  var m3 = function (x) { return ru(x) + NB + 'м³'; };
  var mm = function (x) { return ru(x) + NB + 'м'; };
  var pc = function (x) { return ru(x) + NB + '%'; };

  /* Висячие предлоги и оторванные единицы — те же правила, что build.mjs
     применяет к страницам макета. Тексты калькулятора собирает скрипт,
     и сборка до них не достаёт. Правило «число + единица» здесь смотрит
     вперёд на букву, а не на \b: \b в JS знает только латиницу. */
  var SHORT = 'а|в|и|к|о|с|у|я|бы|во|да|до|же|за|из|ко|ли|на|не|ни|но|об|от|по|со|то|ту|уж|для|при|над|под|про|без';
  var reShort = new RegExp('(^|[\\s(«"])(' + SHORT + ')[ ]+(?=[«"(0-9A-Za-zА-Яа-яЁё])', 'gi');
  function typo(text) {
    return String(text)
      .replace(reShort, '$1$2' + NB)
      .replace(reShort, '$1$2' + NB)
      .replace(/(\S) +—/g, '$1' + NB + '—')
      .replace(/(\d) +(₽|%|м²|м³|мм|см|м|кг|л|шт\.|Вт|кВт)(?![0-9A-Za-zА-Яа-яЁё²³])/g, '$1' + NB + '$2');
  }

  function esc(text) {
    return String(text).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  var txt = function (text) { return esc(typo(text)); };

  /* ======================================================================
     Описание полей
     ====================================================================== */

  function extend(a, b) {
    if (b) Object.keys(b).forEach(function (k) { a[k] = b[k]; });
    return a;
  }
  /* num — число с единицей; sel — список; seg — переключатель на 2–4
     варианта (виден сразу, без раскрытия списка).
     Настройки: ph — подсказка в пустом поле, hint — строка под полем,
     more — спрятать в «Дополнительные параметры», show(v) — показывать
     поле только при таких значениях других полей. */
  function num(name, label, unit, value, o) {
    return extend({ t: 'num', name: name, label: label, unit: unit, value: value === '' || value === undefined ? '' : String(value) }, o);
  }
  function sel(name, label, options, value, o) {
    return extend({ t: 'sel', name: name, label: label, options: options, value: value }, o);
  }
  function seg(name, label, options, value, o) {
    return extend({ t: 'seg', name: name, label: label, options: options, value: value }, o);
  }

  function item(name, n, unit) { return { name: name, n: n, unit: unit }; }
  function need(text, rows) { return { need: text, rows: rows || [] }; }

  var ICON = function (path) {
    return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + path + '</svg>';
  };
  var I = {
    gkl: ICON('<path d="M7 3h11v15H7z"/><path d="M4 6v15h11"/>'),
    frame: ICON('<path d="M3 4h18M3 20h18M6 4v16M12 4v16M18 4v16"/>'),
    mix: ICON('<path d="M7 4h10l2 4v11a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V8z"/><path d="M5 8h14M10 13h4"/>'),
    paint: ICON('<rect x="4" y="3" width="13" height="5" rx="1"/><path d="M17 5.5h3v5h-8.5v3"/><rect x="10" y="13.5" width="3" height="7" rx="1"/>'),
    wallpaper: ICON('<path d="M4 6a3 3 0 0 1 6 0v14H4z"/><path d="M7 3h12v12h-9"/>'),
    tile: ICON('<rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="8" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/><rect x="13" y="13" width="8" height="8" rx="1"/>'),
    floor: ICON('<path d="M3 5h18v14H3z"/><path d="M3 9.7h18M3 14.3h18M10 5v4.7M16 9.7v4.6M7 14.3V19"/>'),
    ceiling: ICON('<path d="M3 4h18M8 4v4M16 4v4"/><path d="M4 8h16v12H4z"/><path d="M4 14h16M12 8v12"/>'),
    panels: ICON('<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M8 3v18M12 3v18M16 3v18"/>'),
    bricks: ICON('<path d="M3 5h18v14H3z"/><path d="M3 9.7h18M3 14.3h18M8 5v4.7M16 5v4.7M12 9.7v4.6M8 14.3V19M16 14.3V19"/>'),
    concrete: ICON('<path d="M12 3 20 7.5v9L12 21l-8-4.5v-9z"/><path d="M12 12 20 7.5M12 12 4 7.5M12 12v9"/>'),
    insulation: ICON('<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 10c3 0 3 3 6 3s3-3 6-3 3 3 6 3"/>'),
    roof: ICON('<path d="M2 12 12 4l10 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-5h4v5"/>'),
    radiator: ICON('<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M7.5 6v12M12 6v12M16.5 6v12M5 18v2M19 18v2"/>')
  };

  var SHEETS = [['2.5', '1200 × 2500 мм'], ['2', '1200 × 2000 мм'], ['2.7', '1200 × 2700 мм'], ['3', '1200 × 3000 мм']];
  var sheetName = function (len) {
    for (var i = 0; i < SHEETS.length; i++) if (SHEETS[i][0] === len) return SHEETS[i][1];
    return '';
  };

  /* ======================================================================
     Калькуляторы
     ====================================================================== */

  var CALCS = [

    /* ---------------------------------------------------------------- */
    {
      id: 'gkl', hash: 'gipsokarton', icon: I.gkl,
      title: 'Гипсокартон', short: 'Листы на обшивку',
      lead: 'Сколько листов уйдёт на обшивку стен или потолка.',
      search: 'гипсокартон',
      fields: [
        num('area', 'Площадь обшивки', 'м²', 20, { hint: 'По стенам и потолку, без вычета проёмов: подрезка всё равно съест часть листа.' }),
        sel('sheet', 'Размер листа', SHEETS, '2.5'),
        seg('layers', 'Слоёв обшивки', [['1', 'Один'], ['2', 'Два']], '1'),
        num('reserve', 'Запас на подрезку', '%', 10)
      ],
      calc: function (v) {
        if (!pos(v.area)) return need('Впишите площадь обшивки.');
        var sheet = 1.2 * Number(v.sheet);
        var layers = Number(v.layers);
        var r = reserveOf(v.reserve);
        var total = v.area * layers;
        var sheets = up(total * (1 + r / 100) / sheet);
        return {
          items: [item('Гипсокартон ' + sheetName(v.sheet), sheets, W.sheet)],
          rows: [['Площадь обшивки', m2(total)], ['Площадь листа', m2(sheet)], ['Запас', pc(r)]],
          note: 'Оценка по площади: проёмы и раскладка листов могут изменить число. Профили, саморезы и дюбели посчитает калькулятор «Перегородка».',
          summary: m2(v.area) + ', ' + (layers === 2 ? 'два слоя' : 'один слой')
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'frame', hash: 'peregorodka', icon: I.frame,
      title: 'Перегородка', short: 'Гипсокартон на каркасе',
      lead: 'Листы, профили, саморезы и дюбели на перегородку или обшивку стены по каркасу.',
      search: 'профиль для гипсокартона',
      fields: [
        num('length', 'Длина перегородки', 'м', 4),
        num('height', 'Высота', 'м', 2.7),
        seg('sides', 'Обшивка', [['2', 'С двух сторон'], ['1', 'С одной']], '2'),
        seg('layers', 'Слоёв с каждой стороны', [['1', 'Один'], ['2', 'Два']], '1'),
        sel('sheet', 'Размер листа', SHEETS, '2.5'),
        seg('step', 'Шаг стоек', [['0.6', '600 мм'], ['0.4', '400 мм']], '0.6'),
        sel('profile', 'Длина профиля', [['3', '3 м'], ['4', '4 м']], '3'),
        num('reserve', 'Запас на листы', '%', 10, { more: true }),
        num('screw', 'Шаг саморезов по стойке', 'мм', 250, { more: true }),
        num('dowel', 'Шаг дюбелей', 'мм', 500, { more: true })
      ],
      calc: function (v) {
        var L = v.length;
        var H = v.height;
        if (!pos(L) || !pos(H)) return need('Впишите длину и высоту перегородки.');
        var sheetLen = Number(v.sheet);
        var sides = Number(v.sides);
        var layers = Number(v.layers);
        var step = Number(v.step);
        var PL = Number(v.profile);
        var r = reserveOf(v.reserve);
        var screwStep = pos(v.screw) ? v.screw / 1000 : 0.25;
        var dowelStep = pos(v.dowel) ? v.dowel / 1000 : 0.5;

        var face = L * H;
        var sheets = up(face * sides * layers * (1 + r / 100) / (1.2 * sheetLen));
        /* Стойки через шаг плюс крайняя; если стена выше профиля, стойку
           наращивают — целых профилей на стойку столько, сколько нужно
           по высоте. Направляющие — по полу и по потолку. */
        var studs = up(L / step) + 1;
        var studPieces = studs * up(H / PL);
        var guides = 2 * up(L / PL);
        /* Лист крепится ко всем стойкам под ним: на ширину 1200 мм это три
           стойки при шаге 600 и четыре при шаге 400. */
        var perSheet = (Math.round(1.2 / step) + 1) * (up(sheetLen / screwStep) + 1);
        var screws = sheets * perSheet;
        var frameScrews = studs * 4;
        var dowels = 2 * (up(L / dowelStep) + 1) + 2 * (up(H / dowelStep) + 1);
        var tape = 2 * (L + H);
        /* Серпянка — на швы наружного слоя: вертикальные между листами
           и горизонтальные, если лист короче высоты. */
        var joints = (Math.max(0, up(L / 1.2) - 1) * H + Math.max(0, up(H / sheetLen) - 1) * L) * sides;

        return {
          items: [
            item('Гипсокартон ' + sheetName(v.sheet), sheets, W.sheet),
            item('Профиль стоечный ПС, ' + ru(PL) + ' м', studPieces, 'шт.'),
            item('Профиль направляющий ПН, ' + ru(PL) + ' м', guides, 'шт.'),
            item('Саморезы для гипсокартона', screws, 'шт.'),
            item('Саморезы для каркаса', frameScrews, 'шт.'),
            item('Дюбель-гвозди', dowels, 'шт.'),
            item('Лента уплотнительная', Math.round(tape * 10) / 10, 'м'),
            item('Серпянка для швов', Math.round(joints * 10) / 10, 'м')
          ],
          rows: [
            ['Площадь одной стороны', m2(face)],
            ['Стоек', ru(studs) + ' через ' + ru(step * 1000) + ' мм'],
            ['Саморезов на лист', ru(perSheet) + ', шаг ' + ru(screwStep * 1000) + ' мм'],
            ['Саморезов для каркаса', '4 на стойку'],
            ['Дюбели', 'по полу, потолку и стенам через ' + ru(dowelStep * 1000) + ' мм'],
            ['Запас на листы', pc(r)]
          ],
          note: 'Для одного слоя берут саморезы 25 мм, для второго — 35 мм. Дверной проём не вычитаем: вокруг него ставят дополнительные стойки, а обрезки листов уйдут на подрезку.',
          summary: mm(L) + ' × ' + mm(H) + ', ' + (sides === 2 ? 'обшивка с двух сторон' : 'с одной стороны')
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'mix', hash: 'smesi', icon: I.mix,
      title: 'Сухие смеси', short: 'Штукатурка, шпатлёвка, стяжка',
      lead: 'Сколько мешков штукатурки, шпатлёвки или смеси для стяжки нужно на площадь.',
      search: function (v) { return MIX_NAMES[v.kind][1]; },
      fields: [
        sel('kind', 'Смесь', [['plaster', 'Штукатурка'], ['putty', 'Шпатлёвка'], ['screed', 'Стяжка, наливной пол'], ['other', 'Другая сухая смесь']], 'plaster'),
        num('area', 'Площадь', 'м²', 20),
        num('thick', 'Толщина слоя', 'мм', 10),
        num('usage', 'Расход на 1 м² при слое 1 мм', 'кг', '', { ph: 'с упаковки' }),
        num('bag', 'Вес мешка', 'кг', '', { ph: 'с упаковки' }),
        num('reserve', 'Запас', '%', 10)
      ],
      hint: 'Расход и вес мешка — на упаковке. Если расход указан на слой 10 мм, разделите его на 10. Своих цифр не подставляем: у разных смесей расход отличается в разы.',
      calc: function (v) {
        if (!pos(v.area) || !pos(v.thick)) return need('Впишите площадь и толщину слоя.');
        var rows = [['Площадь', m2(v.area)], ['Слой', ru(v.thick) + NB + 'мм']];
        if (!pos(v.usage) || !pos(v.bag)) {
          return need('Осталось вписать расход и вес мешка — оба числа есть на упаковке смеси.', rows);
        }
        var r = reserveOf(v.reserve);
        var kg = v.area * v.thick * v.usage * (1 + r / 100);
        var bags = up(kg / v.bag);
        return {
          items: [item(MIX_NAMES[v.kind][0] + ', мешки по ' + ru(v.bag) + NB + 'кг', bags, W.bag)],
          rows: rows.concat([['Нужно смеси', ru(Math.round(kg)) + NB + 'кг'], ['Запас', pc(r)]]),
          note: 'Расход взят из вашей строки — сверьтесь с упаковкой конкретной смеси. На неровных стенах слой толще в среднем, чем на маяках.',
          summary: MIX_NAMES[v.kind][0].toLowerCase() + ', ' + m2(v.area) + ', слой ' + ru(v.thick) + NB + 'мм'
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'paint', hash: 'kraska', icon: I.paint,
      title: 'Краска и грунтовка', short: 'Литры и банки',
      lead: 'Сколько банок краски, грунтовки или лака нужно на стены или потолок.',
      search: function (v) { return PAINT_NAMES[v.kind][1]; },
      fields: [
        sel('kind', 'Материал', [['paint', 'Краска'], ['primer', 'Грунтовка'], ['varnish', 'Лак, пропитка']], 'paint'),
        seg('mode', 'Площадь', [['area', 'Знаю площадь'], ['room', 'По размерам комнаты']], 'area'),
        num('area', 'Площадь окрашивания', 'м²', 30, { show: function (v) { return v.mode === 'area'; } }),
        seg('surf', 'Что красим', [['walls', 'Стены'], ['ceiling', 'Потолок'], ['both', 'Стены и потолок']], 'walls', { show: function (v) { return v.mode === 'room'; } }),
        num('length', 'Длина комнаты', 'м', 4, { show: function (v) { return v.mode === 'room'; } }),
        num('width', 'Ширина комнаты', 'м', 3, { show: function (v) { return v.mode === 'room'; } }),
        num('height', 'Высота стен', 'м', 2.7, { show: function (v) { return v.mode === 'room' && v.surf !== 'ceiling'; } }),
        num('openings', 'Окна и двери', 'м²', 3, { show: function (v) { return v.mode === 'room' && v.surf !== 'ceiling'; }, hint: 'Их площадь вычтем из стен.' }),
        seg('layers', 'Слоёв', [['1', '1'], ['2', '2'], ['3', '3']], '2'),
        seg('rateUnit', 'Расход на банке указан', [['m2l', 'м² на 1 л'], ['mlm2', 'мл на 1 м²']], 'm2l'),
        num('rate', 'Расход', function (v) { return v.rateUnit === 'mlm2' ? 'мл/м²' : 'м²/л'; }, '', { ph: 'с банки' }),
        num('can', 'Объём банки', 'л', '', { ph: 'с банки' }),
        num('reserve', 'Запас', '%', 10, { more: true })
      ],
      hint: 'Расход пишут на банке по-разному: «1 л на 8–10 м²» или «100–150 мл на 1 м²» — выберите, как у вас. Для пористых и тёмных поверхностей берите расход по большей цифре.',
      calc: function (v) {
        var area;
        var rows = [];
        if (v.mode === 'room') {
          if (!pos(v.length) || !pos(v.width)) return need('Впишите длину и ширину комнаты.');
          var walls = 0;
          var ceiling = 0;
          if (v.surf !== 'ceiling') {
            if (!pos(v.height)) return need('Впишите высоту стен.');
            walls = Math.max(0, 2 * (v.length + v.width) * v.height - (pos(v.openings) ? v.openings : 0));
            rows.push(['Стены без окон и дверей', m2(walls)]);
          }
          if (v.surf !== 'walls') {
            ceiling = v.length * v.width;
            rows.push(['Потолок', m2(ceiling)]);
          }
          area = walls + ceiling;
        } else {
          if (!pos(v.area)) return need('Впишите площадь окрашивания.');
          area = v.area;
          rows.push(['Площадь', m2(area)]);
        }
        var layers = Number(v.layers);
        rows.push(['Слоёв', ru(layers)]);
        if (!pos(v.rate)) return need('Впишите расход с банки — и калькулятор посчитает литры.', rows);
        var r = reserveOf(v.reserve);
        var liters = (v.rateUnit === 'mlm2' ? area * layers * v.rate / 1000 : area * layers / v.rate) * (1 + r / 100);
        var name = PAINT_NAMES[v.kind][0];
        rows.push(['Запас', pc(r)]);
        if (!pos(v.can)) {
          return {
            items: [item(name, Math.round(liters * 10) / 10, 'л')],
            rows: rows,
            note: 'Впишите объём банки — посчитаем, сколько банок брать.',
            summary: m2(area) + ', ' + ru(layers) + ' ' + plural(layers, ['слой', 'слоя', 'слоёв'])
          };
        }
        var cans = up(liters / v.can);
        rows.push(['Всего', ru(liters, 1) + NB + 'л']);
        return {
          items: [item(name + ', банки по ' + ru(v.can) + NB + 'л', cans, W.can)],
          rows: rows,
          note: 'Банки одной партии: оттенок у разных партий может отличаться, особенно при колеровке.',
          summary: m2(area) + ', ' + ru(layers) + ' ' + plural(layers, ['слой', 'слоя', 'слоёв'])
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'wallpaper', hash: 'oboi', icon: I.wallpaper,
      title: 'Обои', short: 'Рулоны с учётом рисунка',
      lead: 'Сколько рулонов нужно на комнату: по полосам, с подгонкой рисунка.',
      search: 'обои',
      fields: [
        num('length', 'Длина комнаты', 'м', 4),
        num('width', 'Ширина комнаты', 'м', 3),
        num('height', 'Высота стен', 'м', 2.7),
        num('doors', 'Ширина дверей', 'м', 0, { hint: 'Сумма по всем дверям. Окна не вычитаем: над ними и под ними обои тоже клеят.' }),
        sel('roll', 'Рулон', [['0.53x10.05', '0,53 × 10,05 м'], ['1.06x10.05', '1,06 × 10,05 м'], ['custom', 'Другой размер']], '0.53x10.05'),
        num('rollW', 'Ширина рулона', 'м', '', { ph: 'с этикетки', show: function (v) { return v.roll === 'custom'; } }),
        num('rollL', 'Длина рулона', 'м', '', { ph: 'с этикетки', show: function (v) { return v.roll === 'custom'; } }),
        num('rapport', 'Раппорт', 'см', 0, { hint: 'Шаг рисунка — на этикетке. Ноль — рисунок подгонять не надо.' }),
        num('trim', 'Запас на подрезку полосы', 'см', 10, { more: true }),
        num('glue', 'Пачки клея хватает на', 'рул.', '', { more: true, ph: 'с пачки' })
      ],
      calc: function (v) {
        if (!pos(v.length) || !pos(v.width) || !pos(v.height)) return need('Впишите длину и ширину комнаты и высоту стен.');
        var rollW;
        var rollL;
        if (v.roll === 'custom') {
          rollW = v.rollW;
          rollL = v.rollL;
          if (!pos(rollW) || !pos(rollL)) return need('Впишите ширину и длину рулона — они на этикетке.');
        } else {
          rollW = Number(v.roll.split('x')[0]);
          rollL = Number(v.roll.split('x')[1]);
        }
        var perimeter = 2 * (v.length + v.width) - (pos(v.doors) ? v.doors : 0);
        if (perimeter <= 0) return need('Двери получились шире стен — проверьте размеры.');
        var strip = v.height + (pos(v.rapport) ? v.rapport / 100 : 0) + (pos(v.trim) ? v.trim / 100 : 0);
        var perRoll = Math.floor(rollL / strip + 1e-9);
        if (perRoll < 1) return need('Полоса выходит длиннее рулона: ' + mm(strip) + ' при рулоне ' + mm(rollL) + '.');
        var strips = up(perimeter / rollW);
        var rolls = up(strips / perRoll);
        var items = [item('Обои ' + ru(rollW) + ' × ' + ru(rollL) + NB + 'м', rolls, W.roll)];
        if (pos(v.glue)) items.push(item('Клей для обоев', up(rolls / v.glue), W.pack));
        return {
          items: items,
          rows: [
            ['Периметр без дверей', mm(perimeter)],
            ['Длина полосы', mm(strip)],
            ['Полос нужно', ru(strips)],
            ['Полос из одного рулона', ru(perRoll)]
          ],
          note: 'Берите рулоны одной партии — её номер на этикетке: оттенок у разных партий может отличаться.',
          summary: 'комната ' + mm(v.length) + ' × ' + mm(v.width) + ', высота ' + mm(v.height)
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'tile', hash: 'plitka', icon: I.tile,
      title: 'Плитка', short: 'Плитка, клей и затирка',
      lead: 'Сколько плитки, упаковок, клея и затирки нужно на пол или стены.',
      search: 'плитка',
      fields: [
        num('area', 'Площадь укладки', 'м²', 10, { hint: 'Пол — длина × ширина. Стены — периметр × высота минус двери.' }),
        num('tileL', 'Длина плитки', 'мм', 300),
        num('tileW', 'Ширина плитки', 'мм', 300),
        num('joint', 'Шов', 'мм', 2),
        num('reserve', 'Запас на подрезку', '%', 10, { hint: 'При укладке по диагонали берут больше.' }),
        num('perPack', 'Плиток в упаковке', 'шт.', '', { ph: 'с коробки' }),
        num('glueRate', 'Расход клея на 1 м²', 'кг', '', { more: true, ph: 'с мешка' }),
        num('glueBag', 'Вес мешка клея', 'кг', '', { more: true, ph: 'с мешка' }),
        num('thick', 'Толщина плитки', 'мм', '', { more: true, ph: 'с коробки' }),
        num('density', 'Плотность затирки', 'кг/дм³', '', { more: true, ph: 'с упаковки' }),
        num('groutPack', 'Упаковка затирки', 'кг', '', { more: true, ph: 'с упаковки' })
      ],
      hint: 'Клей и затирку считаем, если заполнить их поля в «Дополнительных параметрах»: расход клея — на мешке, плотность затирки — на её упаковке.',
      calc: function (v) {
        if (!pos(v.area) || !pos(v.tileL) || !pos(v.tileW)) return need('Впишите площадь и размер плитки.');
        var a = v.tileL;
        var b = v.tileW;
        var j = pos(v.joint) ? v.joint : 0;
        var r = reserveOf(v.reserve);
        var module = (a + j) * (b + j) / 1e6;
        var tiles = up(v.area * (1 + r / 100) / module);
        var name = 'Плитка ' + ru(a) + ' × ' + ru(b) + NB + 'мм';
        var items = [];
        if (pos(v.perPack)) {
          items.push(item(name + ', упаковки по ' + ru(v.perPack) + NB + 'шт.', up(tiles / v.perPack), W.pack));
          items.push(item('Это плиток', tiles, 'шт.'));
        } else {
          items.push(item(name, tiles, W.tile));
        }
        var rows = [
          ['Площадь с запасом', m2(v.area * (1 + r / 100))],
          ['Плиток по площади', ru(tiles) + ' — это ' + m2(tiles * a * b / 1e6)]
        ];
        if (pos(v.glueRate)) {
          var glue = v.area * v.glueRate * (1 + r / 100);
          items.push(pos(v.glueBag)
            ? item('Плиточный клей, мешки по ' + ru(v.glueBag) + NB + 'кг', up(glue / v.glueBag), W.bag)
            : item('Плиточный клей', Math.round(glue), 'кг'));
          rows.push(['Клея', ru(Math.round(glue)) + NB + 'кг']);
        }
        if (pos(v.thick) && pos(v.density) && j > 0) {
          /* Формула с упаковок затирки: (A + B) ÷ (A × B) × толщина ×
             ширина шва × плотность — кг на 1 м². */
          var perM2 = (a + b) / (a * b) * v.thick * j * v.density;
          var grout = v.area * perM2 * (1 + r / 100);
          items.push(pos(v.groutPack)
            ? item('Затирка, упаковки по ' + ru(v.groutPack) + NB + 'кг', up(grout / v.groutPack), W.pack)
            : item('Затирка', Math.round(grout * 10) / 10, 'кг'));
          rows.push(['Расход затирки', ru(perM2, 2) + NB + 'кг на 1 м²']);
        }
        rows.push(['Запас', pc(r)]);
        return {
          items: items,
          rows: rows,
          note: 'Плитку берите из одной партии и одного калибра — они написаны на коробке.',
          summary: m2(v.area) + ', плитка ' + ru(a) + ' × ' + ru(b) + NB + 'мм'
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'floor', hash: 'laminat', icon: I.floor,
      title: 'Ламинат', short: 'Упаковки, подложка, плинтус',
      lead: 'Сколько упаковок ламината или паркетной доски, подложки и плинтуса нужно на комнату.',
      search: 'ламинат',
      fields: [
        num('length', 'Длина комнаты', 'м', 5),
        num('width', 'Ширина комнаты', 'м', 4),
        num('pack', 'В упаковке ламината', 'м²', '', { ph: 'с упаковки' }),
        num('reserve', 'Запас на подрезку', '%', 10, { hint: 'При укладке по диагонали берут больше.' }),
        num('under', 'Подложка: в рулоне или пачке', 'м²', '', { ph: 'с упаковки' }),
        num('plinth', 'Длина плинтуса', 'м', 2.5, { more: true }),
        num('doors', 'Ширина дверей', 'м', 0.8, { more: true, hint: 'Плинтус по дверному проёму не идёт.' })
      ],
      calc: function (v) {
        if (!pos(v.length) || !pos(v.width)) return need('Впишите длину и ширину комнаты.');
        var r = reserveOf(v.reserve);
        var area = v.length * v.width;
        var needArea = area * (1 + r / 100);
        var items = [];
        items.push(pos(v.pack)
          ? item('Ламинат, упаковки по ' + ru(v.pack) + NB + 'м²', up(needArea / v.pack), W.pack)
          : item('Ламинат', Math.round(needArea * 10) / 10, 'м²'));
        if (pos(v.under)) items.push(item('Подложка, упаковки по ' + ru(v.under) + NB + 'м²', up(needArea / v.under), W.pack));
        var perimeter = Math.max(0, 2 * (v.length + v.width) - (pos(v.doors) ? v.doors : 0));
        if (pos(v.plinth)) items.push(item('Плинтус ' + ru(v.plinth) + NB + 'м', up(perimeter * (1 + r / 100) / v.plinth), 'шт.'));
        return {
          items: items,
          rows: [['Площадь пола', m2(area)], ['С запасом', m2(needArea)], ['Периметр без дверей', mm(perimeter)], ['Запас', pc(r)]],
          note: pos(v.pack)
            ? 'Уголки, заглушки и соединители для плинтуса — по числу углов и стыков: у прямоугольной комнаты четыре внутренних угла.'
            : 'Впишите, сколько м² в упаковке, — посчитаем упаковки.',
          summary: 'комната ' + mm(v.length) + ' × ' + mm(v.width)
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'ceiling', hash: 'armstrong', icon: I.ceiling,
      title: 'Потолок «Армстронг»', short: 'Плиты, профили, подвесы',
      lead: 'Плиты 600 × 600, профили, уголок и подвесы на подвесной потолок.',
      search: 'армстронг',
      fields: [
        num('length', 'Длина комнаты', 'м', 5),
        num('width', 'Ширина комнаты', 'м', 4),
        num('lamps', 'Светильники 600 × 600 вместо плит', 'шт.', 0),
        num('runner', 'Длина главного профиля', 'м', 3.6, { more: true }),
        num('angle', 'Длина пристенного уголка', 'м', 3, { more: true }),
        num('hang', 'Шаг подвесов по главному профилю', 'м', 1.2, { more: true })
      ],
      hint: 'Длины профиля и уголка — на ценнике. Главный профиль идёт вдоль длинной стены через 1,2 м, поперечные 1,2 и 0,6 м делят потолок на ячейки 600 × 600.',
      calc: function (v) {
        if (!pos(v.length) || !pos(v.width)) return need('Впишите длину и ширину комнаты.');
        var L = Math.max(v.length, v.width);
        var Wd = Math.min(v.length, v.width);
        var runner = pos(v.runner) ? v.runner : 3.6;
        var angle = pos(v.angle) ? v.angle : 3;
        var hang = pos(v.hang) ? v.hang : 1.2;
        var lamps = pos(v.lamps) ? Math.round(v.lamps) : 0;

        /* Ячейки 600 × 600: неполная у стены тоже требует плиты — её режут. */
        var nx = up(L / 0.6);
        var ny = up(Wd / 0.6);
        var plates = Math.max(0, nx * ny - lamps);
        /* Линии главного профиля через 1,2 м поперёк короткой стороны;
           края лежат на пристенном уголке. */
        var lines = Math.max(0, up(Wd / 1.2) - 1);
        var mains = lines * up(L / runner);
        var tees12 = (nx - 1) * (lines + 1);
        var tees06 = Math.max(0, ny - 1 - lines) * nx;
        var angles = 2 * up(L / angle) + 2 * up(Wd / angle);
        var hangers = lines * (up(L / hang) + 1);

        var items = [item('Плиты 600 × 600 мм', plates, W.plate)];
        if (lamps) items.push(item('Светильники 600 × 600 мм', lamps, 'шт.'));
        if (mains) items.push(item('Профиль главный ' + ru(runner) + NB + 'м', mains, 'шт.'));
        items.push(item('Профиль поперечный 1,2 м', tees12, 'шт.'));
        if (tees06) items.push(item('Профиль поперечный 0,6 м', tees06, 'шт.'));
        items.push(item('Уголок пристенный ' + ru(angle) + NB + 'м', angles, 'шт.'));
        if (hangers) {
          items.push(item('Подвесы с тягой', hangers, 'шт.'));
          items.push(item('Дюбели или анкеры для подвесов', hangers, 'шт.'));
        }
        return {
          items: items,
          rows: [
            ['Площадь потолка', m2(L * Wd)],
            ['Ячеек 600 × 600', ru(nx) + ' × ' + ru(ny)],
            ['Линий главного профиля', ru(lines) + ', через 1,2 м'],
            ['Периметр', mm(2 * (L + Wd))]
          ],
          note: 'Крайние ячейки у стен обычно неполные — плиты для них подрезают, поэтому плит больше, чем площадь ÷ 0,36. Уголок крепят к стенам дюбелями.',
          summary: 'комната ' + mm(v.length) + ' × ' + mm(v.width)
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'panels', hash: 'paneli', icon: I.panels,
      title: 'Панели и вагонка', short: 'ПВХ, МДФ, вагонка',
      lead: 'Сколько панелей ПВХ, МДФ или досок вагонки нужно на стены или потолок.',
      search: 'панели',
      fields: [
        num('area', 'Площадь', 'м²', 10, { hint: 'Стены — периметр × высота минус окна и двери.' }),
        num('panelL', 'Длина панели', 'м', 3),
        num('panelW', 'Рабочая ширина панели', 'м', 0.25, { hint: 'Без шипа — на этикетке так и пишут: «полезная» или «рабочая».' }),
        num('reserve', 'Запас на подрезку', '%', 10),
        num('perPack', 'Панелей в упаковке', 'шт.', '', { more: true, ph: 'с упаковки' })
      ],
      calc: function (v) {
        if (!pos(v.area) || !pos(v.panelL) || !pos(v.panelW)) return need('Впишите площадь и размер панели.');
        var r = reserveOf(v.reserve);
        var one = v.panelL * v.panelW;
        var panels = up(v.area * (1 + r / 100) / one);
        var items = [item('Панели ' + ru(v.panelL) + ' × ' + ru(v.panelW) + NB + 'м', panels, W.panel)];
        if (pos(v.perPack)) items.push(item('Это упаковок по ' + ru(v.perPack) + NB + 'шт.', up(panels / v.perPack), W.pack));
        return {
          items: items,
          rows: [['Площадь с запасом', m2(v.area * (1 + r / 100))], ['Площадь одной панели', m2(one)], ['Запас', pc(r)]],
          note: 'Стартовый профиль, углы и плинтус считают по периметру — по длине стен и углов.',
          summary: m2(v.area) + ', панель ' + ru(v.panelL) + ' × ' + ru(v.panelW) + NB + 'м'
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'masonry', hash: 'kladka', icon: I.bricks,
      title: 'Кирпич и блоки', short: 'Штуки и раствор',
      lead: 'Сколько кирпича или блоков и раствора уйдёт на стены.',
      search: function (v) { return v.mat === 'block' ? 'блок' : 'кирпич'; },
      fields: [
        num('length', 'Длина стен', 'м', 10, { hint: 'Сумма длин всех стен.' }),
        num('height', 'Высота стен', 'м', 2.7),
        num('openings', 'Окна и двери', 'м²', 0),
        sel('mat', 'Материал', [['k65', 'Кирпич одинарный 250 × 120 × 65'], ['k88', 'Кирпич полуторный 250 × 120 × 88'], ['block', 'Блок — свой размер']], 'k65'),
        seg('bricks', 'Толщина стены', [['0.5', 'В полкирпича'], ['1', 'В кирпич'], ['1.5', 'В полтора'], ['2', 'В два']], '1', { show: function (v) { return v.mat !== 'block'; } }),
        num('bl', 'Длина блока', 'мм', 600, { show: function (v) { return v.mat === 'block'; } }),
        num('bh', 'Высота блока', 'мм', 200, { show: function (v) { return v.mat === 'block'; } }),
        num('bt', 'Толщина стены — ширина блока', 'мм', 300, { show: function (v) { return v.mat === 'block'; } }),
        num('joint', 'Шов', 'мм', 10, { hint: 'На растворе — около 10 мм, на клею — 2–3 мм.' }),
        num('reserve', 'Запас на бой и подрезку', '%', 5),
        num('pallet', 'Штук на поддоне', 'шт.', '', { more: true, ph: 'у продавца' })
      ],
      calc: function (v) {
        if (!pos(v.length) || !pos(v.height)) return need('Впишите длину и высоту стен.');
        var area = v.length * v.height - (pos(v.openings) ? v.openings : 0);
        if (area <= 0) return need('Окна и двери получились больше стен — проверьте размеры.');
        var j = pos(v.joint) ? v.joint / 1000 : 0;
        var r = reserveOf(v.reserve);
        var perM2;
        var thick;
        var oneVol;
        var name;
        var forms;
        if (v.mat === 'block') {
          if (!pos(v.bl) || !pos(v.bh) || !pos(v.bt)) return need('Впишите размер блока.');
          var l = v.bl / 1000;
          var h = v.bh / 1000;
          thick = v.bt / 1000;
          perM2 = 1 / ((l + j) * (h + j));
          oneVol = l * h * thick;
          name = 'Блоки ' + ru(v.bl) + ' × ' + ru(v.bh) + ' × ' + ru(v.bt) + NB + 'мм';
          forms = W.block;
        } else {
          var bh = v.mat === 'k88' ? 0.088 : 0.065;
          var t = Number(v.bricks);
          /* Стена в полкирпича — один ряд «ложком»; в кирпич — два,
             в полтора — три, в два — четыре. Толщины 120, 250, 380, 510 мм. */
          thick = { '0.5': 0.12, '1': 0.25, '1.5': 0.38, '2': 0.51 }[v.bricks];
          perM2 = 2 * t / ((0.25 + j) * (bh + j));
          oneVol = 0.25 * 0.12 * bh;
          name = v.mat === 'k88' ? 'Кирпич полуторный' : 'Кирпич одинарный';
          forms = W.brick;
        }
        var base = area * perM2;
        var pieces = up(base * (1 + r / 100));
        var mortar = Math.max(0, area * thick - base * oneVol);
        var items = [item(name, pieces, forms)];
        if (pos(v.pallet)) items.push(item('Это поддонов по ' + ru(v.pallet) + NB + 'шт.', up(pieces / v.pallet), W.pallet));
        items.push(item(v.mat === 'block' ? 'Раствор или клей' : 'Раствор', Math.round(mortar * 100) / 100, 'м³'));
        return {
          items: items,
          rows: [
            ['Площадь кладки', m2(area)],
            ['Объём кладки', m3(area * thick)],
            ['Штук на 1 м² стены', ru(perM2, 1)],
            ['Запас', pc(r)]
          ],
          note: 'Раствор — это объём швов без запаса. Сколько мешков сухой смеси нужно на 1 м³ раствора или кладки — на её упаковке.',
          summary: m2(area) + ' стен, ' + name.toLowerCase()
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'concrete', hash: 'beton', icon: I.concrete,
      title: 'Бетон', short: 'Плита, лента, столбы',
      lead: 'Сколько кубов бетона нужно на плиту, ленточный фундамент или столбы.',
      search: 'бетон',
      fields: [
        seg('kind', 'Что заливаем', [['slab', 'Плита'], ['strip', 'Лента'], ['piles', 'Столбы']], 'slab'),
        num('len', 'Длина плиты', 'м', 6, { show: function (v) { return v.kind === 'slab'; } }),
        num('wid', 'Ширина плиты', 'м', 6, { show: function (v) { return v.kind === 'slab'; } }),
        num('thick', 'Толщина плиты', 'см', 20, { show: function (v) { return v.kind === 'slab'; } }),
        num('slen', 'Общая длина ленты', 'м', 24, { show: function (v) { return v.kind === 'strip'; }, hint: 'Периметр плюс внутренние стены.' }),
        num('swid', 'Ширина ленты', 'см', 40, { show: function (v) { return v.kind === 'strip'; } }),
        num('shei', 'Высота ленты', 'см', 80, { show: function (v) { return v.kind === 'strip'; } }),
        num('count', 'Столбов', 'шт.', 12, { show: function (v) { return v.kind === 'piles'; } }),
        num('diam', 'Диаметр столба', 'см', 20, { show: function (v) { return v.kind === 'piles'; } }),
        num('pheight', 'Высота столба', 'м', 1.5, { show: function (v) { return v.kind === 'piles'; } }),
        num('reserve', 'Запас', '%', 5, { hint: 'На уплотнение и неровности основания.' }),
        num('bag', 'Выход из мешка сухой смеси', 'л', '', { more: true, ph: 'с мешка' })
      ],
      calc: function (v) {
        var vol;
        var rows = [];
        var summary;
        if (v.kind === 'strip') {
          if (!pos(v.slen) || !pos(v.swid) || !pos(v.shei)) return need('Впишите длину, ширину и высоту ленты.');
          vol = v.slen * v.swid / 100 * v.shei / 100;
          rows.push(['Лента', mm(v.slen) + ' × ' + ru(v.swid) + ' × ' + ru(v.shei) + NB + 'см']);
          summary = 'лента ' + mm(v.slen);
        } else if (v.kind === 'piles') {
          if (!pos(v.count) || !pos(v.diam) || !pos(v.pheight)) return need('Впишите число, диаметр и высоту столбов.');
          vol = Math.round(v.count) * Math.PI * Math.pow(v.diam / 200, 2) * v.pheight;
          rows.push(['Столбы', ru(Math.round(v.count)) + ' шт. ⌀ ' + ru(v.diam) + NB + 'см, ' + mm(v.pheight)]);
          summary = ru(Math.round(v.count)) + ' столбов';
        } else {
          if (!pos(v.len) || !pos(v.wid) || !pos(v.thick)) return need('Впишите длину, ширину и толщину плиты.');
          vol = v.len * v.wid * v.thick / 100;
          rows.push(['Плита', mm(v.len) + ' × ' + mm(v.wid) + ' × ' + ru(v.thick) + NB + 'см']);
          summary = 'плита ' + mm(v.len) + ' × ' + mm(v.wid);
        }
        var r = reserveOf(v.reserve);
        var total = vol * (1 + r / 100);
        rows.push(['Объём без запаса', m3(vol)], ['Запас', pc(r)]);
        var items = [item('Бетон', Math.round(total * 100) / 100, 'м³')];
        if (pos(v.bag)) items.push(item('Сухая смесь, мешки с выходом ' + ru(v.bag) + NB + 'л', up(total * 1000 / v.bag), W.bag));
        return {
          items: items,
          rows: rows,
          note: 'Сколько цемента, песка и щебня нужно на куб, зависит от марки бетона и материалов — спросите у менеджера.',
          summary: summary
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'insulation', hash: 'uteplitel', icon: I.insulation,
      title: 'Утеплитель', short: 'Слои и упаковки',
      lead: 'Сколько упаковок утеплителя нужно на площадь при нужной толщине.',
      search: 'утеплитель',
      fields: [
        num('area', 'Площадь утепления', 'м²', 50),
        num('need', 'Нужная толщина утеплителя', 'мм', 100),
        num('plate', 'Толщина плиты в упаковке', 'мм', 50),
        num('pack', 'В упаковке', 'м²', '', { ph: 'с упаковки' }),
        num('reserve', 'Запас', '%', 5)
      ],
      calc: function (v) {
        if (!pos(v.area) || !pos(v.need) || !pos(v.plate)) return need('Впишите площадь, нужную толщину и толщину плиты.');
        var layers = up(v.need / v.plate);
        var r = reserveOf(v.reserve);
        var plates = v.area * layers * (1 + r / 100);
        var name = 'Утеплитель ' + ru(v.plate) + NB + 'мм';
        return {
          items: [pos(v.pack)
            ? item(name + ', упаковки по ' + ru(v.pack) + NB + 'м²', up(plates / v.pack), W.pack)
            : item(name, Math.round(plates * 10) / 10, 'м²')],
          rows: [
            ['Слоёв', ru(layers) + ' по ' + ru(v.plate) + NB + 'мм'],
            ['Площадь плит с запасом', m2(plates)],
            ['Объём утеплителя', m3(v.area * v.need / 1000)]
          ],
          note: pos(v.pack)
            ? 'Швы плит второго слоя смещают относительно первого — так не остаётся сквозных щелей.'
            : 'Впишите, сколько м² в упаковке, — посчитаем упаковки.',
          summary: m2(v.area) + ', ' + ru(v.need) + NB + 'мм'
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'roof', hash: 'krovlya', icon: I.roof,
      title: 'Кровля', short: 'Профнастил, металлочерепица',
      lead: 'Сколько листов профнастила или металлочерепицы и планок конька нужно на крышу.',
      search: 'профнастил',
      fields: [
        num('roofLen', 'Длина ската по карнизу', 'м', 8),
        num('slopeLen', 'Длина ската от конька до карниза', 'м', 4),
        seg('slopes', 'Скатов', [['2', 'Два'], ['1', 'Один']], '2'),
        num('useful', 'Рабочая ширина листа', 'м', '', { ph: 'с листа', hint: 'Ширина с учётом нахлёста — у профнастила и металлочерепицы её пишут отдельно.' }),
        num('sheetLen', 'Длина листа', 'м', '', { more: true, ph: 'пусто — лист на весь скат' }),
        num('overlap', 'Нахлёст листов по длине', 'см', 20, { more: true }),
        num('ridge', 'Длина планки конька', 'м', 2, { more: true }),
        num('ridgeOver', 'Нахлёст планок конька', 'см', 10, { more: true })
      ],
      calc: function (v) {
        if (!pos(v.roofLen) || !pos(v.slopeLen)) return need('Впишите длину ската по карнизу и от конька до карниза.');
        if (!pos(v.useful)) return need('Впишите рабочую ширину листа — она есть в описании товара.');
        var slopes = Number(v.slopes);
        var columns = up(v.roofLen / v.useful);
        var ov = pos(v.overlap) ? v.overlap / 100 : 0;
        var rows = 1;
        var len = v.slopeLen;
        if (pos(v.sheetLen) && v.sheetLen < v.slopeLen) {
          if (v.sheetLen <= ov) return need('Лист короче нахлёста — проверьте длину листа.');
          rows = up((v.slopeLen - ov) / (v.sheetLen - ov));
          len = v.sheetLen;
        }
        var sheets = columns * rows * slopes;
        var items = [item('Листы длиной ' + ru(len) + NB + 'м', sheets, W.sheet)];
        if (slopes === 2 && pos(v.ridge)) {
          var step = v.ridge - (pos(v.ridgeOver) ? v.ridgeOver / 100 : 0);
          if (step > 0) items.push(item('Конёк ' + ru(v.ridge) + NB + 'м', up(v.roofLen / step), 'шт.'));
        }
        return {
          items: items,
          rows: [
            ['Листов в ряд на скате', ru(columns)],
            ['Рядов по длине ската', ru(rows)],
            ['Площадь кровли', m2(v.roofLen * v.slopeLen * slopes)]
          ],
          note: 'Длину листа обычно заказывают «скат плюс свес» — уточните у менеджера. Саморезы, карнизные и торцевые планки считаются отдельно.',
          summary: ru(slopes) + ' ' + plural(slopes, ['скат', 'ската', 'скатов']) + ' ' + mm(v.roofLen) + ' × ' + mm(v.slopeLen)
        };
      }
    },

    /* ---------------------------------------------------------------- */
    {
      id: 'radiator', hash: 'radiatory', icon: I.radiator,
      title: 'Радиаторы', short: 'Секции на комнату',
      lead: 'Сколько тепла нужно комнате и сколько секций радиатора. Прикидка для квартиры.',
      search: 'радиатор',
      fields: [
        num('area', 'Площадь комнаты', 'м²', 15),
        num('height', 'Высота потолка', 'м', 2.7),
        sel('norm', 'Дом', [['41', 'Панельный — 41 Вт на 1 м³'], ['34', 'Кирпичный — 34 Вт на 1 м³']], '41'),
        seg('walls', 'Стен на улицу', [['1', 'Одна'], ['1.2', 'Две — угловая'], ['1.4', 'Три']], '1'),
        num('power', 'Мощность одной секции', 'Вт', '', { ph: 'если знаете — из паспорта' })
      ],
      hint: '41 и 34 Вт на 1 м³ — распространённая норма тепла для квартиры в панельном и кирпичном доме; угловой комнате добавляют 20 %, комнате с тремя стенами на улицу — 40 %, к итогу — запас 15 % (обычно советуют от 10 до 20 %). Для частного дома такой расчёт не годится: там всё решают материал стен и утепление.',
      calc: function (v) {
        if (!pos(v.area) || !pos(v.height)) return need('Впишите площадь комнаты и высоту потолка.');
        var RESERVE = 15;
        var norm = Number(v.norm);
        var walls = Number(v.walls) || 1;
        var volume = v.area * v.height;
        var heat = up(volume * norm * walls * (1 + RESERVE / 100));
        var extra = Math.round((walls - 1) * 100);
        var rows = [
          ['Объём комнаты', ru(volume, 1) + NB + 'м³'],
          ['Тепла на 1 м³', ru(norm) + NB + 'Вт'],
          ['Стены на улицу', extra ? '+' + ru(extra) + NB + '%' : 'одна'],
          ['Запас', pc(RESERVE)]
        ];
        var summary = 'комната ' + m2(v.area) + ', потолок ' + mm(v.height);
        if (!pos(v.power)) {
          return {
            eyebrow: 'Нужно тепла',
            items: [item('Тепло для комнаты', heat, 'Вт')],
            rows: rows,
            note: 'Впишите мощность одной секции из паспорта радиатора — посчитаем секции. У стального панельного радиатора секций нет: берите модель мощностью не меньше этой цифры.',
            summary: summary
          };
        }
        var sections = up(heat / v.power);
        return {
          items: [item('Секции радиатора по ' + ru(v.power) + NB + 'Вт', sections, W.section)],
          rows: [['Нужно тепла с запасом', ru(heat) + NB + 'Вт']].concat(rows),
          note: 'Прикидка по объёму комнаты, а не расчёт теплопотерь. Первому и последнему этажу, большому окну и нижнему подключению радиатора тепла нужно больше. Если секций много, их делят на два радиатора — например, под каждым окном.',
          summary: summary
        };
      }
    }
  ];

  var MIX_NAMES = {
    plaster: ['Штукатурка', 'штукатурка'],
    putty: ['Шпатлёвка', 'шпатлевка'],
    screed: ['Смесь для стяжки', 'стяжка'],
    other: ['Сухая смесь', 'смесь']
  };
  var PAINT_NAMES = {
    paint: ['Краска', 'краска'],
    primer: ['Грунтовка', 'грунтовка'],
    varnish: ['Лак или пропитка', 'лак']
  };

  var byId = {};
  CALCS.forEach(function (c) { byId[c.id] = c; });

  /* ======================================================================
     Память: последние значения каждого калькулятора и список покупок.
     Только на этом устройстве; недоступное хранилище (частный режим) —
     не ошибка, калькулятор просто начинает с чистого листа.
     ====================================================================== */
  var store = {
    get: function (key, fallback) {
      try {
        var raw = localStorage.getItem('sg-calc-' + key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch (e) { return fallback; }
    },
    set: function (key, value) {
      try { localStorage.setItem('sg-calc-' + key, JSON.stringify(value)); } catch (e) { /* без памяти */ }
    },
    drop: function (key) {
      try { localStorage.removeItem('sg-calc-' + key); } catch (e) { /* без памяти */ }
    }
  };

  function toast(text) {
    var note = $('[data-demo-note]');
    if (!note) return;
    note.textContent = text;
    note.hidden = false;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(function () { note.hidden = true; }, 3200);
  }

  /* ======================================================================
     Разметка
     ====================================================================== */

  var picker = $('[data-calc-picker]', root);
  var form = $('[data-calc-form]', root);
  var result = $('[data-calc-result]', root);
  var current = null;
  var last = null;

  picker.innerHTML = '<ul class="calc-picker__list">' + CALCS.map(function (c) {
    return '<li><button class="calc-pick" type="button" data-calc-pick="' + c.id + '" aria-pressed="false">' +
      '<span class="calc-pick__icon">' + c.icon + '</span>' +
      '<span class="calc-pick__body"><span class="calc-pick__title">' + txt(c.title) + '</span>' +
      '<span class="calc-pick__text">' + txt(c.short) + '</span></span></button></li>';
  }).join('') + '</ul>';

  function unitOf(f, v) { return typeof f.unit === 'function' ? f.unit(v) : f.unit; }

  function fieldHtml(f, saved) {
    var id = 'cf-' + f.name;
    var value = saved && saved[f.name] !== undefined ? saved[f.name] : f.value;
    var hint = f.hint ? '<p class="calc__field-hint">' + txt(f.hint) + '</p>' : '';
    if (f.t === 'seg') {
      return '<fieldset class="calc__field calc__seg" data-field="' + f.name + '"><legend>' + txt(f.label) + '</legend><div class="seg">' +
        f.options.map(function (o) {
          return '<label class="seg__opt"><input type="radio" name="' + f.name + '" value="' + esc(o[0]) + '"' + (o[0] === value ? ' checked' : '') + '><span>' + txt(o[1]) + '</span></label>';
        }).join('') + '</div>' + hint + '</fieldset>';
    }
    if (f.t === 'sel') {
      return '<div class="calc__field" data-field="' + f.name + '"><label for="' + id + '">' + txt(f.label) + '</label><select id="' + id + '" name="' + f.name + '">' +
        f.options.map(function (o) {
          return '<option value="' + esc(o[0]) + '"' + (o[0] === value ? ' selected' : '') + '>' + esc(o[1]) + '</option>';
        }).join('') + '</select>' + hint + '</div>';
    }
    var unit = unitOf(f, {});
    return '<div class="calc__field" data-field="' + f.name + '"><label for="' + id + '">' + txt(f.label) + '</label>' +
      '<div class="calc__input"><input id="' + id + '" name="' + f.name + '" type="text" inputmode="decimal" autocomplete="off" value="' + esc(String(value).replace('.', ',')) + '"' +
      (f.ph ? ' placeholder="' + esc(f.ph) + '"' : '') + '>' +
      (unit !== undefined ? '<span class="calc__unit" data-unit-for="' + f.name + '">' + esc(unit) + '</span>' : '') + '</div>' + hint + '</div>';
  }

  function renderForm(c) {
    var saved = store.get('v-' + c.id, null);
    var main = c.fields.filter(function (f) { return !f.more; });
    var more = c.fields.filter(function (f) { return f.more; });
    form.innerHTML =
      '<div class="calc__head"><span class="calc__head-icon">' + c.icon + '</span>' +
      '<div class="calc__head-text"><h2 class="calc__title" id="calc-title">' + txt(c.title) + '</h2><p class="calc__lead">' + txt(c.lead) + '</p></div>' +
      '<button class="calc__reset" type="button" data-calc-reset>Сбросить</button></div>' +
      '<div class="calc__grid">' + main.map(function (f) { return fieldHtml(f, saved); }).join('') + '</div>' +
      (more.length ? '<details class="calc__more"' + (store.get('more-' + c.id, false) ? ' open' : '') + '><summary>Дополнительные параметры</summary><div class="calc__grid">' +
        more.map(function (f) { return fieldHtml(f, saved); }).join('') + '</div></details>' : '') +
      (c.hint ? '<p class="calc__hint">' + txt(c.hint) + '</p>' : '');
    form.setAttribute('aria-labelledby', 'calc-title');
  }

  /* Поле ищем по имени селектором, а не через form.elements: поле
     «length» там не найти — form.elements.length это число полей формы. */
  function control(name) { return form.querySelector('[name="' + name + '"]'); }

  function read(c) {
    var v = {};
    var raw = {};
    c.fields.forEach(function (f) {
      if (f.t === 'seg') {
        var on = form.querySelector('input[name="' + f.name + '"]:checked');
        v[f.name] = raw[f.name] = on ? on.value : f.value;
      } else if (f.t === 'sel') {
        var s = control(f.name);
        v[f.name] = raw[f.name] = s ? s.value : f.value;
      } else {
        var input = control(f.name);
        raw[f.name] = input ? input.value : '';
        v[f.name] = parse(raw[f.name]);
      }
    });
    return { v: v, raw: raw };
  }

  /* ======================================================================
     Ответ
     ====================================================================== */

  var liveTimer;

  function render(c, r) {
    var answer = $('[data-calc-answer]', result);
    var caption = $('[data-calc-caption]', result);
    var buy = $('[data-calc-buy]', result);
    var rows = $('[data-calc-rows]', result);
    var how = $('[data-calc-how]', result);
    var note = $('[data-calc-note]', result);
    var eyebrow = $('[data-calc-eyebrow]', result);
    var ok = !r.need && r.items && r.items.length;

    eyebrow.textContent = ok ? (r.eyebrow || 'Нужно купить') : c.title;
    var before = answer.textContent;
    answer.textContent = ok ? qty(r.items[0]) : '—';
    caption.textContent = ok ? r.items[0].name : '';
    caption.hidden = !ok;
    if (ok && before !== answer.textContent) {
      answer.classList.remove('is-changed');
      void answer.offsetWidth;
      answer.classList.add('is-changed');
    }
    buy.innerHTML = ok && r.items.length > 1 ? r.items.map(function (it) {
      return '<li><span>' + txt(it.name) + '</span><b>' + esc(qty(it)) + '</b></li>';
    }).join('') : '';
    buy.hidden = !(ok && r.items.length > 1);
    rows.innerHTML = (r.rows || []).map(function (row) {
      return '<li><span>' + txt(row[0]) + '</span><b>' + txt(row[1]) + '</b></li>';
    }).join('');
    how.hidden = !(r.rows && r.rows.length);
    note.textContent = typo(ok ? (r.note || '') : r.need);
    $$('[data-calc-add], [data-calc-copy], [data-calc-send]', result).forEach(function (b) { b.disabled = !ok; });

    var find = $('[data-calc-find]', result);
    var term = typeof c.search === 'function' ? c.search(last.v) : c.search;
    find.href = (root.getAttribute('data-search-url') || '') + encodeURIComponent(term);
    find.textContent = 'Найти в каталоге: ' + term;

    var peek = $('[data-calc-peek-value]', root);
    if (peek) {
      peek.textContent = ok ? qty(r.items[0]) : '';
      peekState.ok = ok;
      peekState.update();
    }

    /* Экранному диктору — только итог и только когда человек перестал
       печатать, а не на каждую цифру. */
    clearTimeout(liveTimer);
    liveTimer = setTimeout(function () {
      var live = $('[data-calc-live]', root);
      if (live) live.textContent = ok ? (r.eyebrow || 'Нужно купить') + ': ' + qty(r.items[0]) + ', ' + r.items[0].name : '';
    }, 900);
  }

  /* Плашка с итогом для телефона: видна, пока форма на экране, а сам
     итог — нет (на узком экране он стоит под формой). */
  var peekState = { ok: false, form: false, result: true, update: function () {} };
  var peekBtn = $('[data-calc-peek]', root);
  if (peekBtn && 'IntersectionObserver' in window && window.matchMedia) {
    var narrow = window.matchMedia('(max-width: 1023px)');
    peekState.update = function () {
      peekBtn.hidden = !(narrow.matches && peekState.ok && peekState.form && !peekState.result);
    };
    new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.target === result) peekState.result = e.isIntersecting;
        else peekState.form = e.isIntersecting;
      });
      peekState.update();
    }).observe(result);
    new IntersectionObserver(function (entries) {
      peekState.form = entries[entries.length - 1].isIntersecting;
      peekState.update();
    }).observe(form);
    peekBtn.addEventListener('click', function () {
      var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      result.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'start' });
    });
  }

  var saveTimer;

  function recount() {
    var c = current;
    last = read(c);
    c.fields.forEach(function (f) {
      var box = form.querySelector('[data-field="' + f.name + '"]');
      if (!box) return;
      if (f.show) box.hidden = !f.show(last.v);
      if (f.t === 'num') {
        var input = control(f.name);
        var bad = last.raw[f.name].trim() !== '' && isNaN(last.v[f.name]);
        input.setAttribute('aria-invalid', bad ? 'true' : 'false');
        if (typeof f.unit === 'function') {
          var u = form.querySelector('[data-unit-for="' + f.name + '"]');
          if (u) u.textContent = f.unit(last.v);
        }
      }
    });
    last.r = c.calc(last.v);
    render(c, last.r);
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () { store.set('v-' + c.id, last.raw); }, 400);
  }

  function pick(id, fromUser) {
    var c = byId[id] || CALCS[0];
    current = c;
    $$('[data-calc-pick]', picker).forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-calc-pick') === c.id ? 'true' : 'false');
    });
    renderForm(c);
    recount();
    store.set('last', c.id);
    if (fromUser && window.history && history.replaceState) {
      /* Адрес собираем целиком: в теме OpenCart на странице стоит
         <base href>, и голое «#oboi» указало бы на главную. */
      history.replaceState(null, '', location.pathname + location.search + '#' + c.hash);
    }
    /* На телефоне выбор — лента, которую листают вбок: выбранный
       калькулятор должен быть на виду, а не за краем экрана. Листаем саму
       ленту, а не страницу: scrollIntoView дёрнул бы страницу вниз. */
    var btn = picker.querySelector('[data-calc-pick="' + c.id + '"]');
    var strip = picker.querySelector('.calc-picker__list');
    if (btn && strip && strip.scrollWidth > strip.clientWidth + 4) {
      var shift = btn.getBoundingClientRect().left - strip.getBoundingClientRect().left;
      strip.scrollLeft += shift - 16;
    }
  }

  /* ======================================================================
     Текст расчёта: копировать, в список, менеджеру
     ====================================================================== */

  function lines(c, r) {
    var out = [c.title + (r.summary ? ': ' + r.summary : '')];
    r.items.forEach(function (it) { out.push('— ' + it.name + ': ' + qty(it)); });
    return out;
  }

  function fullText(c, r) {
    var out = ['Строй-Герой — строительный калькулятор'].concat(lines(c, r));
    if (r.rows && r.rows.length) {
      out.push('Как считали: ' + r.rows.map(function (row) { return row[0] + ' — ' + row[1]; }).join('; '));
    }
    out.push(location.href.split('#')[0] + '#' + c.hash);
    return out.join('\n');
  }

  function copyText(text, done) {
    var fallback = function () {
      var area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(area);
      toast(ok ? done : 'Не получилось скопировать — выделите текст вручную.');
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(function () { toast(done); }, fallback);
    } else {
      fallback();
    }
  }

  /* Расчёт уходит менеджеру вместе с заявкой на звонок: у формы звонка
     есть поле вопроса (до 2000 знаков), и обработчик пишет его в письмо.
     Поле добавляем в форму сами и вычищаем, если форму открыли другой
     кнопкой, — чтобы чужой расчёт не приехал в обычную заявку.

     Знаки обработчик считает не так, как JS: перевод строки браузер
     отправляет парой \r\n, а & " < > движок хранит как &amp; &quot;
     &lt; &gt;. Меряем так же — иначе длинный список обработчик отклонил
     бы целиком, и человек увидел бы только «Не получилось отправить». */
  var LIMIT = 2000;
  var ENT = { '&': '&amp;', '"': '&quot;', '<': '&lt;', '>': '&gt;' };
  function sentLength(text) {
    return String(text).replace(/\r?\n/g, '\r\n').replace(/[&"<>]/g, function (ch) { return ENT[ch]; }).length;
  }
  /* Не влезло — обрезаем целыми строками и ставим «…». */
  function fit(text) {
    if (sentLength(text) <= LIMIT) return text;
    var rows = text.split('\n');
    while (rows.length > 1 && sentLength(rows.join('\n') + '\n…') > LIMIT) rows.pop();
    return rows.join('\n') + '\n…';
  }
  /* Форма внутри окна «Заказать звонок»: в теме у неё есть метка
     data-callback-form, в макете нет — ищем по самому окну. */
  function callbackForm() { return $('#modal-callback form'); }

  function attach(text, said) {
    var cb = callbackForm();
    if (!cb) return;
    var field = cb.querySelector('input[name="message"]');
    if (!field) {
      field = document.createElement('input');
      field.type = 'hidden';
      field.name = 'message';
      cb.appendChild(field);
    }
    field.value = fit(text);
    var note = cb.querySelector('[data-calc-attached]');
    if (!note) {
      note = document.createElement('p');
      note.className = 'calc__attached';
      note.setAttribute('data-calc-attached', '');
      var before = cb.querySelector('.consent') || cb.querySelector('button[type="submit"]');
      if (before) before.parentNode.insertBefore(note, before);
      else cb.appendChild(note);
    }
    note.textContent = typo(said);
    note.hidden = false;
  }

  function detach() {
    var cb = callbackForm();
    if (!cb) return;
    var field = cb.querySelector('input[name="message"]');
    if (field) field.value = '';
    var note = cb.querySelector('[data-calc-attached]');
    if (note) note.hidden = true;
  }

  document.addEventListener('click', function (e) {
    var opener = e.target.closest('[data-modal-open="modal-callback"]');
    if (opener && !opener.hasAttribute('data-calc-send')) detach();
  }, true);

  /* ======================================================================
     Список покупок
     ====================================================================== */

  var list = store.get('list', []);
  if (!Array.isArray(list)) list = [];
  var listBox = $('[data-calc-list]', root);

  function renderList() {
    if (!listBox) return;
    listBox.hidden = !list.length;
    var body = $('[data-calc-list-body]', listBox);
    var count = $('[data-calc-list-count]', listBox);
    if (count) count.textContent = list.length ? ru(list.length) + ' ' + plural(list.length, ['расчёт', 'расчёта', 'расчётов']) : '';
    body.innerHTML = list.map(function (entry, i) {
      return '<li class="calc-list__entry"><p class="calc-list__name">' + txt(entry.title) + '</p>' +
        (entry.summary ? '<p class="calc-list__summary">' + txt(entry.summary) + '</p>' : '') +
        '<ul class="calc-list__items">' + entry.items.map(function (it) {
          return '<li><span>' + txt(it[0]) + '</span><b>' + esc(it[1]) + '</b></li>';
        }).join('') + '</ul>' +
        '<button class="calc-list__remove" type="button" data-calc-list-remove="' + i + '" aria-label="Убрать из списка: ' + esc(entry.title) + '">' +
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6 6 18"/></svg></button></li>';
    }).join('');
  }

  var CALC_FORMS = ['расчёт', 'расчёта', 'расчётов'];

  /* Первые n расчётов списка текстом; без n — весь список. */
  function listText(n) {
    var out = ['Строй-Герой — список покупок по калькулятору'];
    list.slice(0, n === undefined ? list.length : n).forEach(function (entry) {
      out.push('');
      out.push(entry.title + (entry.summary ? ': ' + entry.summary : ''));
      entry.items.forEach(function (it) { out.push('— ' + it[0] + ': ' + it[1]); });
    });
    return out.join('\n');
  }

  /* Для заявки: целыми расчётами, сколько поместится в её предел,
     и строка о тех, что не вошли, — менеджер должен знать, что это
     не весь список. */
  function listMessage() {
    for (var n = list.length; ; n--) {
      var text = listText(n);
      var rest = list.length - n;
      if (rest) {
        text += '\n\nИ ещё ' + ru(rest) + ' ' + plural(rest, CALC_FORMS) + ' в списке у покупателя — в заявку ' +
          plural(rest, ['не поместился', 'не поместились', 'не поместились']) + '.';
      }
      /* Один расчёт — строк десять, в предел он помещается всегда. */
      if (n <= 1 || sentLength(text) <= LIMIT) return { text: text, n: n };
    }
  }

  function saveList() { store.set('list', list); renderList(); }

  /* ======================================================================
     События
     ====================================================================== */

  picker.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-calc-pick]');
    if (btn) pick(btn.getAttribute('data-calc-pick'), true);
  });
  form.addEventListener('input', recount);
  form.addEventListener('change', recount);
  form.addEventListener('submit', function (e) { e.preventDefault(); });
  form.addEventListener('toggle', function (e) {
    if (e.target.classList && e.target.classList.contains('calc__more')) store.set('more-' + current.id, e.target.open);
  }, true);
  form.addEventListener('click', function (e) {
    if (!e.target.closest('[data-calc-reset]')) return;
    store.drop('v-' + current.id);
    renderForm(current);
    recount();
    toast('Значения по умолчанию');
  });

  result.addEventListener('click', function (e) {
    if (!last || !last.r || last.r.need) return;
    var c = current;
    var r = last.r;
    if (e.target.closest('[data-calc-add]')) {
      list.push({
        title: c.title,
        summary: r.summary || '',
        items: r.items.map(function (it) { return [it.name, qty(it)]; })
      });
      saveList();
      toast('Добавлено в список покупок — он ниже');
    } else if (e.target.closest('[data-calc-copy]')) {
      copyText(fullText(c, r), 'Расчёт скопирован — вставьте его в сообщение');
    } else if (e.target.closest('[data-calc-send]')) {
      /* Кавычки внутри кавычек — «лапки»: «Потолок „Армстронг“». */
      var named = c.title.replace(/«/g, '„').replace(/»/g, '“');
      attach(fullText(c, r), 'К заявке приложен расчёт «' + named + '». Менеджер увидит его в письме и перезвонит.');
    }
  });

  if (listBox) {
    listBox.addEventListener('click', function (e) {
      var remove = e.target.closest('[data-calc-list-remove]');
      if (remove) {
        list.splice(Number(remove.getAttribute('data-calc-list-remove')), 1);
        saveList();
        return;
      }
      if (e.target.closest('[data-calc-list-copy]')) {
        copyText(listText(), 'Список скопирован');
      } else if (e.target.closest('[data-calc-list-send]')) {
        var sent = listMessage();
        var all = list.length;
        attach(sent.text, sent.n === all
          ? 'К заявке приложен список покупок, ' + ru(all) + ' ' + plural(all, CALC_FORMS) + '. Менеджер увидит его в письме и перезвонит.'
          : 'В заявку ' + plural(sent.n, ['поместился', 'поместились', 'поместились']) + ' ' + ru(sent.n) + ' ' +
            plural(sent.n, CALC_FORMS) + ' из ' + ru(all) + ' — длиннее 2000 знаков она не принимает. Остальные продиктуйте менеджеру, когда он перезвонит.');
      } else if (e.target.closest('[data-calc-list-print]')) {
        var stamp = $('[data-print-date]');
        if (stamp) {
          stamp.textContent = new Date().toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
        }
        document.body.classList.add('is-print-calc');
        window.print();
      } else if (e.target.closest('[data-calc-list-clear]')) {
        list = [];
        saveList();
        toast('Список очищен');
      }
    });
  }
  window.addEventListener('afterprint', function () { document.body.classList.remove('is-print-calc'); });

  /* ======================================================================
     Старт: калькулятор из адреса (#oboi), иначе последний открытый.
     Старые адреса вкладок — #gipsokarton, #smesi, #radiatory — те же.
     ====================================================================== */

  var start = null;
  var fromHash = false;
  CALCS.forEach(function (c) {
    if (location.hash === '#' + c.hash) { start = c.id; fromHash = true; }
  });
  if (!start) start = store.get('last', CALCS[0].id);
  pick(start, false);
  renderList();
  if (fromHash && root.scrollIntoView) {
    /* Пришли по ссылке «Калькулятор радиаторов» — сразу к форме, а не
       к ряду карточек выбора. */
    requestAnimationFrame(function () { $('.calc', root).scrollIntoView({ block: 'start' }); });
  }
})();
