/*
 * Выгрузка реестра членов СРО с reestr.nostroy.ru через публичный API списка.
 *
 * Запуск: открыть страницу реестра нужной СРО в Chrome, F12 -> Console,
 * вставить весь файл, Enter. Скрипт сам обойдёт все страницы и скачает
 * .xlsx и .csv. Никакой кнопки "сформировать реестр" не требуется.
 *
 * Настройки (по желанию, задать ДО вставки скрипта):
 *   window.SRO_EXPORT_CONFIG = { sroId: 410, pageCount: 100, concurrency: 4 };
 *
 * После выгрузки данные остаются в window.SRO_RESULT,
 * повторное сохранение — SRO_SAVE('xlsx') или SRO_SAVE('csv').
 */
(function () {
  'use strict';

  var DEFAULTS = {
    sroId: null, // null -> определить из URL, иначе 410
    origin: null, // null -> текущий origin, если это nostroy.ru
    pageCount: null, // null -> подобрать максимальный, который принимает сервер
    concurrency: 4, // одновременных запросов
    delayMs: 120, // пауза между запросами, чтобы не долбить сервер
    retries: 4, // повторы при сетевой ошибке / 429 / 5xx
    headers: 'ru', // 'ru' — переводить известные колонки, 'raw' — как в API
    formats: ['xlsx', 'csv'],
    maxPages: 5000 // предохранитель от бесконечного цикла
  };

  // ---------------------------------------------------------------- утилиты

  function sleep(ms) {
    return new Promise(function (r) { setTimeout(r, ms); });
  }

  function log() {
    var args = ['[СРО-выгрузка]'].concat(Array.prototype.slice.call(arguments));
    console.log.apply(console, args);
  }

  function isPlainObject(v) {
    return v !== null && typeof v === 'object' && !Array.isArray(v);
  }

  // ------------------------------------------------------- разбор ответа API

  /** Находит в ответе массив записей, как бы ни назывался ключ. */
  function pickItems(payload) {
    var best = null;
    (function walk(node, depth) {
      if (depth > 5 || node === null || typeof node !== 'object') return;
      if (Array.isArray(node)) {
        var objects = node.filter(isPlainObject).length;
        if (objects > 0 && (best === null || objects > best.length)) best = node;
        return;
      }
      for (var k in node) {
        if (Object.prototype.hasOwnProperty.call(node, k)) walk(node[k], depth + 1);
      }
    })(payload, 0);
    return best || [];
  }

  /** Достаёт из ответа метаданные пагинации, как бы они ни назывались. */
  function pickMeta(payload) {
    var meta = { countPages: null, count: null };
    (function walk(node, depth) {
      if (depth > 5 || node === null || typeof node !== 'object' || Array.isArray(node)) return;
      for (var k in node) {
        if (!Object.prototype.hasOwnProperty.call(node, k)) continue;
        var v = node[k];
        var n = typeof v === 'number' ? v : (typeof v === 'string' && /^\d+$/.test(v) ? Number(v) : null);
        if (n !== null) {
          if (meta.countPages === null && /^(countpages|pagescount|pages|totalpages|last_?page)$/i.test(k)) meta.countPages = n;
          if (meta.count === null && /^(count|total|totalcount|totalitems|records)$/i.test(k)) meta.count = n;
        }
        walk(v, depth + 1);
      }
    })(payload, 0);
    return meta;
  }

  // ------------------------------------------------------------- запрос к API

  function readCookie(name) {
    var m = (typeof document !== 'undefined' ? document.cookie : '').match(
      new RegExp('(?:^|; )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]*)')
    );
    return m ? decodeURIComponent(m[1]) : null;
  }

  function makeFetchPage(cfg) {
    var url = cfg.origin + '/api/sro/' + cfg.sroId + '/member/list';

    return async function fetchPage(page, pageCount) {
      var lastErr = null;
      for (var attempt = 0; attempt <= cfg.retries; attempt++) {
        if (attempt > 0) await sleep(Math.min(8000, 500 * Math.pow(2, attempt - 1)));
        try {
          var headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
          var xsrf = readCookie('XSRF-TOKEN');
          if (xsrf) headers['X-XSRF-TOKEN'] = xsrf;

          var resp = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: headers,
            body: JSON.stringify({
              filters: {},
              page: page,
              pageCount: String(pageCount),
              sortBy: {}
            })
          });

          if (resp.status === 401 || resp.status === 403 || resp.status === 419) {
            throw new Error(
              'HTTP ' + resp.status + ': сессия не принята. Обнови страницу реестра и запусти скрипт заново.'
            );
          }
          if (resp.status === 429 || resp.status >= 500) {
            lastErr = new Error('HTTP ' + resp.status + ' на странице ' + page);
            continue; // повторяем
          }
          if (!resp.ok) throw new Error('HTTP ' + resp.status + ' на странице ' + page);

          return await resp.json();
        } catch (e) {
          lastErr = e;
          if (/сессия не принята/.test(String(e && e.message))) throw e;
        }
      }
      throw lastErr || new Error('Не удалось получить страницу ' + page);
    };
  }

  /** Подбирает максимальный pageCount, который сервер реально отдаёт. */
  async function probePageCount(fetchPage, candidates) {
    var fallback = 20;
    for (var i = 0; i < candidates.length; i++) {
      var want = candidates[i];
      var json = await fetchPage(1, want);
      var got = pickItems(json).length;
      var total = pickMeta(json).count;
      if (got >= want || (total !== null && got >= total)) {
        log('сервер отдаёт по ' + got + ' записей на страницу — используем pageCount=' + want);
        return { pageCount: want, firstPage: json };
      }
      log('pageCount=' + want + ' сервер урезал до ' + got + ', пробуем меньше');
      if (got > fallback) fallback = got;
    }
    log('используем pageCount=' + fallback);
    return { pageCount: fallback, firstPage: null };
  }

  // ------------------------------------------------------ сбор всех страниц

  async function fetchAll(cfg) {
    var fetchPage = makeFetchPage(cfg);
    var pageCount, firstPage;

    if (cfg.pageCount) {
      pageCount = cfg.pageCount;
      firstPage = await fetchPage(1, pageCount);
    } else {
      var probe = await probePageCount(fetchPage, [500, 100, 50, 20]);
      pageCount = probe.pageCount;
      firstPage = probe.firstPage || (await fetchPage(1, pageCount));
    }

    var meta = pickMeta(firstPage);
    var firstItems = pickItems(firstPage);
    if (!firstItems.length) throw new Error('API вернул пустой список — проверь sroId и что ты на нужной странице реестра.');

    var totalPages = meta.countPages;
    if (totalPages === null && meta.count !== null) totalPages = Math.ceil(meta.count / pageCount);
    if (totalPages === null) totalPages = cfg.maxPages;
    totalPages = Math.min(totalPages, cfg.maxPages);

    log('всего записей: ' + (meta.count === null ? '?' : meta.count) + ', страниц: ' + totalPages);

    var pages = new Array(totalPages);
    pages[0] = firstItems;

    var next = 2;
    var done = 1;
    var failed = [];

    async function worker() {
      while (true) {
        var page = next++;
        if (page > totalPages) return;
        try {
          var json = await fetchPage(page, pageCount);
          pages[page - 1] = pickItems(json);
        } catch (e) {
          failed.push({ page: page, error: String(e && e.message || e) });
          pages[page - 1] = [];
        }
        done++;
        if (done % 5 === 0 || done === totalPages) {
          log('страниц загружено ' + done + '/' + totalPages + ' (' + Math.round((done / totalPages) * 100) + '%)');
        }
        if (cfg.delayMs) await sleep(cfg.delayMs);
      }
    }

    var workers = [];
    for (var w = 0; w < Math.max(1, cfg.concurrency); w++) workers.push(worker());
    await Promise.all(workers);

    // склейка + дедупликация (на случай сдвига пагинации между запросами)
    var rows = [];
    var seen = Object.create(null);
    for (var p = 0; p < pages.length; p++) {
      var chunk = pages[p] || [];
      for (var i = 0; i < chunk.length; i++) {
        var row = chunk[i];
        var key = row && (row.id !== undefined ? 'id:' + row.id : JSON.stringify(row));
        if (seen[key]) continue;
        seen[key] = true;
        rows.push(row);
      }
    }

    if (failed.length) {
      console.warn('[СРО-выгрузка] не удалось загрузить страниц: ' + failed.length, failed);
    }
    if (meta.count !== null && rows.length !== meta.count) {
      console.warn(
        '[СРО-выгрузка] собрано ' + rows.length + ' из ' + meta.count +
        ' записей. Причина — пропущенные страницы или дубли в выдаче API.'
      );
    }

    return { rows: rows, expected: meta.count, failedPages: failed, pageCount: pageCount };
  }

  // --------------------------------------------------- плоская таблица из JSON

  function flattenRow(obj, out, prefix, depth) {
    out = out || {};
    prefix = prefix || '';
    depth = depth || 0;
    if (depth > 4) return out;

    for (var k in obj) {
      if (!Object.prototype.hasOwnProperty.call(obj, k)) continue;
      var v = obj[k];
      var path = prefix ? prefix + '.' + k : k;

      if (v === null || v === undefined) {
        out[path] = '';
      } else if (Array.isArray(v)) {
        if (v.every(function (x) { return x === null || typeof x !== 'object'; })) {
          out[path] = v.join('; ');
        } else if (v.length === 1 && isPlainObject(v[0])) {
          flattenRow(v[0], out, path, depth + 1);
        } else {
          out[path] = v.map(function (x) {
            return isPlainObject(x) ? (x.name || x.title || JSON.stringify(x)) : String(x);
          }).join(' | ');
        }
      } else if (isPlainObject(v)) {
        flattenRow(v, out, path, depth + 1);
      } else if (typeof v === 'boolean') {
        out[path] = v ? 'да' : 'нет';
      } else {
        out[path] = v;
      }
    }
    return out;
  }

  var RU_HEADERS = {
    id: 'ID',
    name: 'Наименование',
    fullname: 'Полное наименование',
    full_name: 'Полное наименование',
    shortname: 'Краткое наименование',
    short_name: 'Краткое наименование',
    inn: 'ИНН',
    kpp: 'КПП',
    ogrn: 'ОГРН/ОГРНИП',
    ogrnip: 'ОГРН/ОГРНИП',
    okpo: 'ОКПО',
    number: 'Регистрационный номер',
    registration_number: 'Регистрационный номер',
    registrationnumber: 'Регистрационный номер',
    reg_number: 'Регистрационный номер',
    regnumber: 'Регистрационный номер',
    status: 'Статус',
    statusname: 'Статус',
    status_name: 'Статус',
    registration_date: 'Дата регистрации',
    registrationdate: 'Дата регистрации',
    date_registration: 'Дата регистрации',
    exclusion_date: 'Дата исключения',
    exclusiondate: 'Дата исключения',
    address: 'Адрес',
    legal_address: 'Юридический адрес',
    phone: 'Телефон',
    email: 'E-mail',
    site: 'Сайт',
    website: 'Сайт',
    director: 'Руководитель',
    head: 'Руководитель',
    chief: 'Руководитель',
    sro: 'СРО',
    sro_name: 'СРО',
    region: 'Регион'
  };

  var RU_PATTERNS = [
    [/(compensation|comp|kf).*(vv|vozmeshhen|vozmesch)/i, 'КФ ВВ (взнос)'],
    [/(compensation|comp|kf).*(odo|obespechen)/i, 'КФ ОДО (взнос)'],
    [/level.*(vv|responsib|otvet)/i, 'Уровень ответственности ВВ'],
    [/level.*(odo|dogovor)/i, 'Уровень ответственности ОДО'],
    [/(vv).*level/i, 'Уровень ответственности ВВ'],
    [/(odo).*level/i, 'Уровень ответственности ОДО'],
    [/(right|pravo).*(osobo|opasn|technical)/i, 'Право на особо опасные объекты'],
    [/(right|pravo).*(atom|nuclear)/i, 'Право на объекты атомной энергии'],
    [/basis|osnovanie/i, 'Основание'],
    [/note|comment|primech/i, 'Примечание']
  ];

  function humanHeader(path, mode) {
    if (mode === 'raw') return path;

    var normalized = String(path).replace(/[_.]/g, '');
    for (var i = 0; i < RU_PATTERNS.length; i++) {
      if (RU_PATTERNS[i][0].test(path) || RU_PATTERNS[i][0].test(normalized)) return RU_PATTERNS[i][1];
    }

    // Вложенные поля показываем вместе с родителем ("СРО → Наименование"),
    // иначе sro.name и levels.name превратились бы в одинаковое "Наименование".
    var segments = String(path).split('.');
    return segments.map(function (s) {
      return RU_HEADERS[s.toLowerCase()] || s;
    }).join(' → ');
  }

  var PRIORITY = [
    /^(name|full_?name|short_?name)$/i,
    /reg.*num|^number$/i,
    /^inn$/i,
    /ogrn/i,
    /status/i,
    /registration_?date|date.*registr/i,
    /exclusion|iskl/i
  ];

  function buildTable(rows, headerMode) {
    var flat = rows.map(function (r) { return flattenRow(r); });

    var columns = [];
    var seen = Object.create(null);
    flat.forEach(function (r) {
      for (var k in r) {
        if (Object.prototype.hasOwnProperty.call(r, k) && !seen[k]) { seen[k] = true; columns.push(k); }
      }
    });

    // Приоритетные колонки — вперёд. Сначала верхнеуровневые поля; вложенные
    // поднимаем, только если наверху вообще ничего не нашлось.
    var head = [];
    PRIORITY.forEach(function (re) {
      columns.forEach(function (c) {
        if (c.indexOf('.') === -1 && head.indexOf(c) === -1 && re.test(c)) head.push(c);
      });
    });
    if (!head.length) {
      PRIORITY.forEach(function (re) {
        columns.forEach(function (c) {
          if (head.indexOf(c) === -1 && re.test(c.split('.').pop())) head.push(c);
        });
      });
    }
    var tail = columns.filter(function (c) { return head.indexOf(c) === -1; });
    columns = head.concat(tail);

    // Заголовки обязаны быть уникальными, иначе в Excel не понять, что где.
    var usedHeaders = Object.create(null);
    var headers = columns.map(function (c) {
      var h = humanHeader(c, headerMode);
      if (usedHeaders[h]) h = h + ' (' + c + ')';
      usedHeaders[h] = true;
      return h;
    });
    var data = flat.map(function (r) {
      return columns.map(function (c) { return r[c] === undefined ? '' : r[c]; });
    });

    return { columns: columns, headers: headers, data: data };
  }

  // ------------------------------------------------------------------- CSV

  function toCSV(table) {
    var sep = ';';
    function cell(v) {
      var s = v === null || v === undefined ? '' : String(v);
      if (s.indexOf(sep) !== -1 || s.indexOf('"') !== -1 || /[\r\n]/.test(s)) {
        s = '"' + s.replace(/"/g, '""') + '"';
      }
      return s;
    }
    var lines = [table.headers.map(cell).join(sep)];
    table.data.forEach(function (row) { lines.push(row.map(cell).join(sep)); });
    return '﻿' + lines.join('\r\n') + '\r\n'; // BOM — чтобы Excel увидел UTF-8
  }

  // ------------------------------------------------------------------ XLSX
  // Минимальный генератор .xlsx: ZIP (без сжатия) + OOXML с inline-строками.

  function crc32(buf) {
    var table = crc32._t;
    if (!table) {
      table = crc32._t = new Int32Array(256);
      for (var i = 0; i < 256; i++) {
        var c = i;
        for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
        table[i] = c;
      }
    }
    var crc = -1;
    for (var j = 0; j < buf.length; j++) crc = (crc >>> 8) ^ table[(crc ^ buf[j]) & 0xFF];
    return (crc ^ -1) >>> 0;
  }

  function dosDateTime(d) {
    var year = Math.max(1980, d.getFullYear());
    return {
      time: (d.getHours() << 11) | (d.getMinutes() << 5) | (Math.floor(d.getSeconds() / 2)),
      date: ((year - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate()
    };
  }

  function makeZip(files) {
    var enc = new TextEncoder();
    var dt = dosDateTime(new Date());
    var parts = [];
    var central = [];
    var offset = 0;

    files.forEach(function (f) {
      var nameBytes = enc.encode(f.name);
      var crc = crc32(f.data);
      var local = new Uint8Array(30 + nameBytes.length);
      var dv = new DataView(local.buffer);
      dv.setUint32(0, 0x04034b50, true);
      dv.setUint16(4, 20, true);
      dv.setUint16(6, 0x0800, true); // UTF-8 имена
      dv.setUint16(8, 0, true); // без сжатия
      dv.setUint16(10, dt.time, true);
      dv.setUint16(12, dt.date, true);
      dv.setUint32(14, crc, true);
      dv.setUint32(18, f.data.length, true);
      dv.setUint32(22, f.data.length, true);
      dv.setUint16(26, nameBytes.length, true);
      dv.setUint16(28, 0, true);
      local.set(nameBytes, 30);

      parts.push(local, f.data);
      central.push({ nameBytes: nameBytes, crc: crc, size: f.data.length, offset: offset });
      offset += local.length + f.data.length;
    });

    var cdParts = [];
    var cdSize = 0;
    central.forEach(function (e) {
      var rec = new Uint8Array(46 + e.nameBytes.length);
      var dv = new DataView(rec.buffer);
      dv.setUint32(0, 0x02014b50, true);
      dv.setUint16(4, 20, true);
      dv.setUint16(6, 20, true);
      dv.setUint16(8, 0x0800, true);
      dv.setUint16(10, 0, true);
      dv.setUint16(12, dt.time, true);
      dv.setUint16(14, dt.date, true);
      dv.setUint32(16, e.crc, true);
      dv.setUint32(20, e.size, true);
      dv.setUint32(24, e.size, true);
      dv.setUint16(28, e.nameBytes.length, true);
      dv.setUint32(42, e.offset, true);
      rec.set(e.nameBytes, 46);
      cdParts.push(rec);
      cdSize += rec.length;
    });

    var eocd = new Uint8Array(22);
    var edv = new DataView(eocd.buffer);
    edv.setUint32(0, 0x06054b50, true);
    edv.setUint16(8, central.length, true);
    edv.setUint16(10, central.length, true);
    edv.setUint32(12, cdSize, true);
    edv.setUint32(16, offset, true);

    var all = parts.concat(cdParts, [eocd]);
    var total = all.reduce(function (s, a) { return s + a.length; }, 0);
    var out = new Uint8Array(total);
    var pos = 0;
    all.forEach(function (a) { out.set(a, pos); pos += a.length; });
    return out;
  }

  function xmlEscape(s) {
    return String(s)
      .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function colLetter(n) { // 1 -> A
    var s = '';
    while (n > 0) {
      var r = (n - 1) % 26;
      s = String.fromCharCode(65 + r) + s;
      n = Math.floor((n - 1) / 26);
    }
    return s;
  }

  var FORCE_TEXT = /inn|ogrn|kpp|okpo|snils|phone|тел|bik|schet|account/i;

  function toXLSX(table, sheetName) {
    var enc = new TextEncoder();
    var nCols = table.headers.length;
    var nRows = table.data.length + 1;

    var rowsXml = [];
    var headerCells = table.headers.map(function (h, i) {
      return '<c r="' + colLetter(i + 1) + '1" t="inlineStr" s="1"><is><t xml:space="preserve">' +
        xmlEscape(h) + '</t></is></c>';
    });
    rowsXml.push('<row r="1">' + headerCells.join('') + '</row>');

    var widths = table.headers.map(function (h) { return String(h).length + 2; });

    table.data.forEach(function (row, ri) {
      var cells = [];
      for (var ci = 0; ci < nCols; ci++) {
        var v = row[ci];
        if (v === '' || v === null || v === undefined) continue;
        var ref = colLetter(ci + 1) + (ri + 2);
        var len = String(v).length;
        if (len + 2 > widths[ci]) widths[ci] = Math.min(60, len + 2);

        var numeric = typeof v === 'number' && isFinite(v) && !FORCE_TEXT.test(table.columns[ci]);
        if (numeric) {
          cells.push('<c r="' + ref + '"><v>' + v + '</v></c>');
        } else {
          cells.push('<c r="' + ref + '" t="inlineStr"><is><t xml:space="preserve">' + xmlEscape(v) + '</t></is></c>');
        }
      }
      rowsXml.push('<row r="' + (ri + 2) + '">' + cells.join('') + '</row>');
    });

    var colsXml = widths.map(function (w, i) {
      return '<col min="' + (i + 1) + '" max="' + (i + 1) + '" width="' + Math.max(8, w) + '" customWidth="1"/>';
    }).join('');

    var dim = 'A1:' + colLetter(nCols) + nRows;
    var sheet =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
      '<dimension ref="' + dim + '"/>' +
      '<sheetViews><sheetView workbookViewId="0">' +
      '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>' +
      '</sheetView></sheetViews>' +
      '<sheetFormatPr defaultRowHeight="15"/>' +
      '<cols>' + colsXml + '</cols>' +
      '<sheetData>' + rowsXml.join('') + '</sheetData>' +
      '<autoFilter ref="' + dim + '"/>' +
      '</worksheet>';

    var contentTypes =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
      '<Default Extension="xml" ContentType="application/xml"/>' +
      '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
      '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' +
      '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' +
      '</Types>';

    var rels =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>' +
      '</Relationships>';

    var workbook =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ' +
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
      '<sheets><sheet name="' + xmlEscape((sheetName || 'Реестр').slice(0, 31)) + '" sheetId="1" r:id="rId1"/></sheets>' +
      '</workbook>';

    var wbRels =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>' +
      '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' +
      '</Relationships>';

    var styles =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
      '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>' +
      '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>' +
      '<fills count="2"><fill><patternFill patternType="none"/></fill>' +
      '<fill><patternFill patternType="gray125"/></fill></fills>' +
      '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>' +
      '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' +
      '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>' +
      '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>' +
      '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>' +
      '</styleSheet>';

    return makeZip([
      { name: '[Content_Types].xml', data: enc.encode(contentTypes) },
      { name: '_rels/.rels', data: enc.encode(rels) },
      { name: 'xl/workbook.xml', data: enc.encode(workbook) },
      { name: 'xl/_rels/workbook.xml.rels', data: enc.encode(wbRels) },
      { name: 'xl/styles.xml', data: enc.encode(styles) },
      { name: 'xl/worksheets/sheet1.xml', data: enc.encode(sheet) }
    ]);
  }

  // -------------------------------------------------------------- скачивание

  function download(filename, data, mime) {
    var blob = new Blob([data], { type: mime });
    try {
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      setTimeout(function () {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 2000);
      log('файл сохранён: ' + filename);
    } catch (e) {
      console.error('[СРО-выгрузка] не удалось скачать автоматически:', e);
      log('данные в window.SRO_RESULT, повтори сохранение командой SRO_SAVE("xlsx")');
    }
  }

  // ------------------------------------------------------------------- запуск

  function resolveConfig(userCfg) {
    var cfg = {};
    for (var k in DEFAULTS) cfg[k] = DEFAULTS[k];
    var fromWindow = (typeof window !== 'undefined' && window.SRO_EXPORT_CONFIG) || {};
    [fromWindow, userCfg || {}].forEach(function (src) {
      for (var key in src) if (Object.prototype.hasOwnProperty.call(src, key)) cfg[key] = src[key];
    });

    if (!cfg.origin) {
      var loc = typeof location !== 'undefined' ? location : null;
      cfg.origin = loc && /nostroy\.ru$/i.test(loc.hostname) ? loc.origin : 'https://reestr.nostroy.ru';
    }
    if (!cfg.sroId) {
      var path = typeof location !== 'undefined' ? location.pathname + location.search : '';
      var m = path.match(/(?:sro|reestr)\D{0,12}?(\d{1,6})(?!\d)/i) || path.match(/(\d{1,6})(?!.*\d)/);
      cfg.sroId = m ? Number(m[1]) : 410;
    }
    return cfg;
  }

  function saveTable(table, format, cfg, stamp) {
    var base = 'reestr_nostroy_sro_' + cfg.sroId + '_' + stamp;
    if (format === 'csv') {
      download(base + '.csv', toCSV(table), 'text/csv;charset=utf-8');
    } else {
      download(
        base + '.xlsx',
        toXLSX(table, 'СРО ' + cfg.sroId),
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      );
    }
  }

  async function run(userCfg) {
    var cfg = resolveConfig(userCfg);
    var started = Date.now();
    log('СРО id=' + cfg.sroId + ', API ' + cfg.origin + '/api/sro/' + cfg.sroId + '/member/list');

    var result = await fetchAll(cfg);
    var table = buildTable(result.rows, cfg.headers);
    var stamp = new Date().toISOString().slice(0, 10);

    if (typeof window !== 'undefined') {
      window.SRO_RESULT = { rows: result.rows, table: table, config: cfg, failedPages: result.failedPages };
      window.SRO_SAVE = function (format) { saveTable(table, format || 'xlsx', cfg, stamp); };
    }

    (cfg.formats || ['xlsx']).forEach(function (f) { saveTable(table, f, cfg, stamp); });

    log(
      'готово: ' + table.data.length + ' записей, ' + table.headers.length +
      ' колонок, за ' + Math.round((Date.now() - started) / 1000) + ' c'
    );
    log('колонки:', table.headers.join(' | '));
    if (result.failedPages.length) {
      log('НЕ загружены страницы: ' + result.failedPages.map(function (f) { return f.page; }).join(', ') +
        ' — запусти скрипт ещё раз, чтобы добрать.');
    }
    return window && window.SRO_RESULT;
  }

  var api = {
    run: run,
    fetchAll: fetchAll,
    buildTable: buildTable,
    toCSV: toCSV,
    toXLSX: toXLSX,
    flattenRow: flattenRow,
    pickItems: pickItems,
    pickMeta: pickMeta,
    resolveConfig: resolveConfig
  };

  if (typeof globalThis !== 'undefined') globalThis.SRO_EXPORT = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;

  var autorun = typeof window !== 'undefined' && !globalThis.SRO_EXPORT_NO_AUTORUN;
  if (autorun) {
    run().catch(function (e) {
      console.error('[СРО-выгрузка] ошибка:', e);
      log('если ошибка про сессию — обнови страницу реестра и запусти скрипт заново.');
    });
  }
})();
