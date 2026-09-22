#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Выгрузка 1С -> каталог OpenCart.

Зачем отдельный инструмент, а не «залить файл».
1С отдаёт не каталог магазина, а свою внутреннюю таблицу. В названиях
товаров живут служебные пометки, которыми кладовщик двигает строки
в списке («ЯРаспродажа!!!», «ЯУдалить!!!», «+» в начале), внутренние
коды хвостом («//599628»), дважды закодированные кавычки («&quot;»)
и лишние пробелы. Всё это на витрине выглядит ошибкой магазина.

Ещё важнее то, чего в выгрузке нет: фотографий, остатков, производителей
и названий у тринадцати разделов из четырнадцати. Скрипт про это
не молчит и не додумывает - он отказывается собирать SQL, пока
названия разделов не подтверждены человеком.

Что делает:
  1. читает YML-выгрузку;
  2. чистит названия, объясняя каждую правку в отчёте;
  3. откладывает в сторону то, что нельзя публиковать честно
     (цена 0, пометка «удалить»);
  4. собирает 1c/predprosmotr.html - показать заказчику;
  5. собирает 1c/import.sql для phpMyAdmin, но только когда
     все разделы названы и подтверждены.

Запуск:
    python3 tools/1c-import.py
    python3 tools/1c-import.py 1c/вашфайл.xml
"""

import html
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / '1c/vygruzka-2026-09-23.xml'
CATS = ROOT / '1c/kategorii.csv'
OUT_HTML = ROOT / '1c/predprosmotr.html'
OUT_SQL = ROOT / '1c/import.sql'
OUT_TXT = ROOT / '1c/otchet.txt'
DATE = ''

# Служебные пометки 1С в начале названия. Распознаём только те, значение
# которых известно наверняка; всё остальное вида «Я…!!!» попадает
# в отчёт отдельной строкой, а не вычищается наугад.
# «Я» впереди - приём кладовщика: буква гонит строку в конец списка в 1С.
# Она есть не у всех («Распродажа!!!» встречается и без неё) и написана
# как придётся: «Яраспродажа», «ЯРаспродщажа» с опечаткой. Поэтому
# буква необязательна, а корень слова допускает любой хвост.
MARK_SALE = re.compile(r'^\s*[яЯ]?\s*[Рр]аспрод[а-яё]*!+\s*', re.U)
MARK_DROP = re.compile(r'^\s*[яЯ]?\s*[Уу]далить!+\s*', re.U)
MARK_ANY = re.compile(r'^\s*[яЯ][А-Яа-яЁё]{3,}!+', re.U)
TAIL_CODE = re.compile(r'\s*//\s*(\S[^/]*?)\s*$')


def unescape_twice(s):
    """«&amp;quot;» - это кавычка, закодированная дважды: один раз в 1С,
    второй при сборке файла. Раскодируем, пока строка меняется, но
    не больше двух раз: дальше можно съесть настоящий «&» из названия."""
    for _ in range(2):
        out = html.unescape(s)
        if out == s:
            break
        s = out
    return s


def clean_name(raw):
    """Возвращает (название, артикул, список пометок)."""
    marks = []
    s = unescape_twice(raw)
    if s != raw:
        marks.append('раскодированы кавычки')

    if MARK_DROP.match(s):
        marks.append('ПОМЕЧЕН В 1С НА УДАЛЕНИЕ')
        s = MARK_DROP.sub('', s)
    elif MARK_SALE.match(s):
        marks.append('распродажа')
        s = MARK_SALE.sub('', s)
    elif MARK_ANY.match(s):
        marks.append('НЕПОНЯТНАЯ ПОМЕТКА 1С')

    model = ''
    m = TAIL_CODE.search(s)
    if m:
        model = m.group(1)[:64]
        s = TAIL_CODE.sub('', s)
        marks.append('код из названия перенесён в артикул')

    if s.lstrip().startswith('+'):
        s = s.lstrip()[1:]
        marks.append('убран «+» в начале')

    t = re.sub(r'\s+', ' ', s).strip()
    if t != s.strip():
        marks.append('лишние пробелы')
    return t, model, marks


# Русские буквы латиницей для адреса страницы. Таблица обычная,
# «яндексовская»: щ -> sch, ю -> yu, я -> ya, мягкий и твёрдый знаки
# пропадают. Меняете таблицу - меняются адреса уже опубликованных
# товаров, а это потерянные позиции в поиске.
TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def slug(text, limit=90):
    """Адрес страницы из названия товара."""
    out = []
    for ch in text.lower():
        out.append(TRANSLIT.get(ch, ch))
    s = re.sub(r'[^a-z0-9]+', '-', ''.join(out)).strip('-')
    if len(s) > limit:
        # Режем по дефису, чтобы адрес не обрывался посреди слова.
        s = s[:limit].rsplit('-', 1)[0]
    return s


def unique_slugs(pairs):
    """pairs: список (ключ, текст). Возвращает ключ -> адрес.
    Повторы разводятся числом: два разных товара с одинаковым
    названием в выгрузке есть, и без этого второй затёр бы первый."""
    seen = Counter()
    out = {}
    for key, text in pairs:
        base = slug(text) or 'tovar'
        seen[base] += 1
        out[key] = base if seen[base] == 1 else f'{base}-{seen[base]}'
    return out


def read_cats():
    """guid -> (название, подтверждено)"""
    out = {}
    if not CATS.exists():
        return out
    for line in CATS.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(';')]
        if len(parts) < 3:
            continue
        out[parts[0]] = (parts[1], parts[2].lower() in ('да', 'yes', '1'))
    return out


def q(s):
    """Строка для MySQL. Экранируем и обратную косую, и кавычку:
    при sql_mode по умолчанию обратная косая - тоже экранирующий знак,
    и без первой замены «C:\\» в названии съело бы следующий символ."""
    s = str(s).replace('\\', '\\\\').replace("'", "\\'")
    s = ''.join(ch for ch in s if ch >= ' ' or ch in '\n\t')
    return "'" + s + "'"


def main():
    global DATE
    root = ET.parse(SRC).getroot()
    DATE = root.get('date') or 'дата не указана'
    shop = root.find('shop')
    file_cats = {c.get('id'): (c.text or '').strip() for c in shop.find('categories')}
    offers = list(shop.find('offers'))

    cats = read_cats()
    goods, dropped = [], []
    mark_count = Counter()

    for o in offers:
        guid = o.get('id')
        raw = o.findtext('name') or ''
        name, model, marks = clean_name(raw)
        for m in marks:
            mark_count[m] += 1
        price = float((o.findtext('price') or '0').replace(',', '.'))
        rec = {
            'guid': guid, 'cat': o.findtext('categoryId') or '', 'raw': raw.strip(),
            'name': name, 'model': model, 'price': price,
            'descr': (o.findtext('description') or '').strip(), 'marks': marks,
        }
        why = []
        if 'ПОМЕЧЕН В 1С НА УДАЛЕНИЕ' in marks:
            why.append('помечен в 1С на удаление')
        if price <= 0:
            why.append('цена 0')
        if not name:
            why.append('пустое название')
        if why:
            rec['why'] = why
            dropped.append(rec)
        else:
            goods.append(rec)

    by_cat = defaultdict(list)
    for g in goods:
        by_cat[g['cat']].append(g)

    # ---- отчёт ----------------------------------------------------------
    rep = []
    rep.append(f'Выгрузка : {SRC.name}, дата {root.get("date")}')
    rep.append(f'Товаров в файле : {len(offers)}')
    rep.append(f'Готовы к публикации : {len(goods)}')
    rep.append(f'Отложено : {len(dropped)}')
    rep.append('')
    rep.append('Что поправлено в названиях:')
    for k, v in mark_count.most_common():
        rep.append(f'  {v:4}  {k}')
    rep.append('')
    rep.append('Отложено и почему:')
    for d in dropped:
        rep.append(f'  - {d["raw"][:70]}')
        rep.append(f'      {", ".join(d["why"])}')
    rep.append('')

    rep.append('Разделы:')
    unnamed = []
    for cid, items in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
        name, ok = cats.get(cid, ('', False))
        src = ' (название пришло из 1С)' if file_cats.get(cid) else ''
        if not name:
            state = 'НАЗВАНИЯ НЕТ'
            unnamed.append(cid)
        elif not ok:
            state = f'«{name}» — не подтверждено'
            unnamed.append(cid)
        else:
            state = f'«{name}»'
        rep.append(f'  {len(items):4} тов.  {cid}  {state}{src}')
    rep.append('')

    missing = []
    if not any(o.find('picture') is not None for o in offers):
        missing.append('фотографии — нет ни у одного товара из 246')
    if not any(o.find('vendor') is not None for o in offers):
        missing.append('производитель (vendor) — нет ни у одного')
    if not any(o.find('vendorCode') is not None for o in offers):
        missing.append('артикул отдельным полем — нет (берём из хвоста названия, если он есть)')
    if not any(o.get('available') for o in offers):
        missing.append('остатки и признак наличия — нет')
    if not any(o.find('param') is not None for o in offers):
        missing.append('характеристики (мощность, размер) — нет')
    withdesc = sum(1 for o in offers if o.findtext('description'))
    missing.append(f'описания — есть у {withdesc} товаров из {len(offers)}')
    rep.append('Чего в выгрузке нет (просить у заказчика):')
    for m in missing:
        rep.append(f'  - {m}')

    text = '\n'.join(rep) + '\n'
    OUT_TXT.write_text(text, encoding='utf-8')
    print(text)

    write_html(by_cat, cats, file_cats, dropped, mark_count)

    if unnamed:
        print(f'SQL не собран: у {len(unnamed)} разделов название не подтверждено.')
        print(f'Откройте {CATS.relative_to(ROOT)}, поправьте названия и поставьте «да».')
        return 1

    write_sql(by_cat, cats)
    print(f'Собран {OUT_SQL.relative_to(ROOT)}: {len(goods)} товаров, {len(by_cat)} разделов.')
    return 0


def esc(s):
    return html.escape(str(s), quote=True)


def rub(x):
    return f'{x:,.0f}'.replace(',', ' ') + ' ₽' if x == int(x) else f'{x:,.2f}'.replace(',', ' ') + ' ₽'


def write_html(by_cat, cats, file_cats, dropped, mark_count):
    """Страница для заказчика: что попадёт в каталог и как будет называться.
    Сравнение «было в 1С -> станет на сайте» показывается только там, где
    название менялось: иначе из-за трёх сотен одинаковых строк не видно
    тех двадцати, где правка настоящая."""
    total = sum(len(v) for v in by_cat.values())
    p = ['<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>Выгрузка 1С — что попадёт на сайт</title><style>',
         'body{font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;'
         'background:#fff;color:#14181d}',
         '.wrap{max-width:900px;margin:0 auto;padding:24px 16px 64px}',
         'h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:32px 0 8px}',
         '.lead{color:#5b6672;margin:0 0 24px}',
         'table{border-collapse:collapse;width:100%;font-size:15px}',
         'th,td{border-bottom:1px solid #e6e9ed;padding:7px 8px;text-align:left;vertical-align:top}',
         'th{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#5b6672}',
         'td.p{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}',
         '.name{font-weight:600}.was{color:#8a95a1;font-size:13px}',
         '.ask{background:#fff6e5;border:1px solid #f0d089;border-radius:8px;padding:12px 14px;margin:8px 0 20px}',
         '.bad{background:#fdeceb;border:1px solid #f0b3ae;border-radius:8px;padding:12px 14px}',
         '.n{color:#5b6672;font-size:14px;font-weight:400}',
         'code{background:#f1f3f5;padding:1px 5px;border-radius:4px;font-size:13px}',
         '</style></head><body><div class="wrap">']
    p.append(f'<h1>Выгрузка 1С — что попадёт на сайт</h1>')
    p.append(f'<p class="lead">{total} товаров в {len(by_cat)} разделах. '
             f'Отложено {len(dropped)}.</p>')

    need = [cid for cid in by_cat if not cats.get(cid, ('', False))[1]]
    if need:
        p.append('<div class="ask"><b>Нужно от вас: названия разделов.</b><br>'
                 '1С прислала товары, но названия разделов — нет, только номера. '
                 'Ниже под каждым разделом стоит название, которое мы предлагаем '
                 'по его товарам. Посмотрите и скажите, какие менять. '
                 'Пока не подтвердите — в каталог ничего не заливаем.</div>')
        p.append('<p class="lead">Серой строкой под товаром написано, что мы поправили '
                 'в его названии: служебные пометки 1С («ЯРаспродажа!!!», «+» в начале, '
                 'код через две косые черты) на витрине магазина выглядят ошибкой.</p>')

    for cid, items in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
        name, ok = cats.get(cid, ('', False))
        src = file_cats.get(cid)
        tag = '' if ok else (' <span class="n">— название из 1С, подтвердите</span>' if src
                             else ' <span class="n">— название предлагаем мы, подтвердите</span>')
        p.append(f'<h2>{esc(name or "Без названия")} <span class="n">({len(items)})</span>{tag}</h2>')
        p.append('<table><tr><th>Товар</th><th>Артикул</th><th>Цена</th></tr>')
        for g in sorted(items, key=lambda x: x['name']):
            # Показываем не старое название целиком, а что именно
            # с ним сделали: полные строки из 1С отличаются от новых
            # одной приставкой, и из-за трёхсот почти одинаковых пар
            # не видно тех двадцати, где правка настоящая.
            was = ''
            if g['marks']:
                was = f'<div class="was">в 1С: {esc(", ".join(g["marks"]))}</div>'
            p.append(f'<tr><td><span class="name">{esc(g["name"])}</span>{was}</td>'
                     f'<td>{esc(g["model"]) or "—"}</td>'
                     f'<td class="p">{rub(g["price"])}</td></tr>')
        p.append('</table>')

    if dropped:
        p.append('<h2>Отложено — на сайт не попадёт</h2><div class="bad">')
        p.append('<table><tr><th>Товар</th><th>Почему</th></tr>')
        for d in dropped:
            p.append(f'<tr><td>{esc(d["raw"])}</td><td>{esc(", ".join(d["why"]))}</td></tr>')
        p.append('</table></div>')

    p.append('<h2>Чего в выгрузке не хватает</h2><ul>'
             '<li><b>Фотографий нет ни у одного товара.</b> Карточки будут пустыми.</li>'
             '<li>Нет остатков — сайт будет писать «Уточняйте наличие».</li>'
             '<li>Нет производителя и характеристик.</li>'
             '<li>Описание есть у 11 товаров из 246.</li></ul>')
    p.append('</div></body></html>')
    OUT_HTML.write_text('\n'.join(p), encoding='utf-8')


SQL_HEAD = """-- =====================================================================
--  Строй-Герой: загрузка каталога из выгрузки 1С
--  Собрано tools/1c-import.py — руками этот файл не правят.
--  Источник: {src}, выгрузка от {date}
--  Товаров: {n}, разделов: {c}
-- =====================================================================
--
--  ПЕРЕД ЗАПУСКОМ: сделайте копию базы (phpMyAdmin -> Экспорт).
--
--  Скрипт можно запускать повторно: товар, который уже загружен,
--  второй раз не добавится — он опознаётся по номеру из 1С (поле SKU).
--
--  Но скрипт только ДОБАВЛЯЕТ. Если в 1С поменяли цену или название
--  у товара, который уже на сайте, повторный запуск их не подтянет:
--  иначе он затирал бы и правки, сделанные в админке руками.
--  Обновление цен — отдельная задача, её делаем, когда понадобится.
--
--  ДВЕ НАСТРОЙКИ, которые выбираете вы.
--
--  1. Показывать товары сразу или завести скрытыми. Поставьте 0,
--     если хотите сначала дождаться фотографий, и 1, если показывать
--     сразу. Переключается потом и в админке, разом для всех.
SET @status := 1;
--
--  2. Родительский раздел для новых разделов каталога. 0 — верхний
--     уровень, разделы встанут в главное меню сайта. Если хотите
--     сложить всё внутрь существующего раздела, впишите его номер
--     (виден в адресе раздела в админке).
SET @parent := 0;
--
-- ---------------------------------------------------------------------
--  Дальше руками ничего менять не нужно.
-- ---------------------------------------------------------------------
--  Язык, склад и единицы берём из настроек самого магазина, а не числом:
--  на разных установках эти номера разные, и жёстко вписанная единица
--  однажды разложит товары по чужим справочникам.
SET @store := 0;
SET @lang  := (SELECT language_id FROM `oc_language`
               WHERE code = (SELECT value FROM `oc_setting`
                             WHERE `key` = 'config_language' AND store_id = @store LIMIT 1)
               LIMIT 1);
SET @lang  := IFNULL(@lang, 1);
SET @wcls  := IFNULL((SELECT value FROM `oc_setting`
                      WHERE `key` = 'config_weight_class_id' AND store_id = @store LIMIT 1), 1);
SET @lcls  := IFNULL((SELECT value FROM `oc_setting`
                      WHERE `key` = 'config_length_class_id' AND store_id = @store LIMIT 1), 1);

--  Остатков в выгрузке нет. Врать «в наличии» нельзя, писать «нет
--  на складе» — тоже неправда. Заводим отдельное состояние склада.
SET @stock := (SELECT stock_status_id FROM `oc_stock_status`
               WHERE name = 'Уточняйте наличие' AND language_id = @lang LIMIT 1);
INSERT INTO `oc_stock_status` (language_id, name)
SELECT @lang, 'Уточняйте наличие' FROM DUAL WHERE @stock IS NULL;
SET @stock := IFNULL(@stock, LAST_INSERT_ID());

--  Промежуточная таблица. Не временная нарочно: после загрузки в неё
--  можно заглянуть и увидеть, что именно приехало из 1С и каким
--  товаром это стало на сайте.
DROP TABLE IF EXISTS `oc_import_1c`;
CREATE TABLE `oc_import_1c` (
  `guid`        CHAR(36)      NOT NULL,
  `cat_guid`    CHAR(36)      NOT NULL,
  `name`        VARCHAR(255)  NOT NULL,
  `model`       VARCHAR(64)   NOT NULL,
  `price`       DECIMAL(15,4) NOT NULL,
  `descr`       TEXT          NOT NULL,
  `keyword`     VARCHAR(255)  NOT NULL,
  `category_id` INT DEFAULT NULL,
  `product_id`  INT DEFAULT NULL,
  PRIMARY KEY (`guid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;
--  Кодировка именно utf8, а не utf8mb4: такими установщик ocStore
--  создаёт все свои таблицы. Если у промежуточной будет другая,
--  MySQL откажется сравнивать её колонки с колонками магазина
--  («Illegal mix of collations»), и загрузка встанет на первом же
--  соединении таблиц. На всякий случай сравнения ниже идут ещё
--  и через CAST AS BINARY: номера из 1С и адреса страниц — латиница
--  и цифры, побайтового сравнения им достаточно, а от кодировки
--  оно уже не зависит.

INSERT INTO `oc_import_1c` (`guid`,`cat_guid`,`name`,`model`,`price`,`descr`,`keyword`) VALUES
"""

SQL_TAIL = """
-- ---- Товары ---------------------------------------------------------
--  Номер из 1С кладём в SKU: по нему товар опознаётся при повторной
--  загрузке. Артикул (model) виден покупателю на карточке, и туда
--  идёт код из названия, если он там был.
INSERT INTO `oc_product`
  (`model`,`sku`,`upc`,`ean`,`jan`,`isbn`,`mpn`,`location`,`quantity`,`stock_status_id`,
   `image`,`manufacturer_id`,`shipping`,`price`,`points`,`tax_class_id`,`date_available`,
   `weight`,`weight_class_id`,`length`,`width`,`height`,`length_class_id`,
   `subtract`,`minimum`,`sort_order`,`status`,`viewed`,`date_added`,`date_modified`)
SELECT i.`model`, i.`guid`, '', '', '', '', '', '', 0, @stock,
       '', 0, 1, i.`price`, 0, 0, CURDATE(),
       0, @wcls, 0, 0, 0, @lcls,
       0, 1, 0, @status, 0, NOW(), NOW()
FROM `oc_import_1c` i
WHERE NOT EXISTS (SELECT 1 FROM `oc_product` p
                  WHERE CAST(p.`sku` AS BINARY) = CAST(i.`guid` AS BINARY));

UPDATE `oc_import_1c` i
  JOIN `oc_product` p ON CAST(p.`sku` AS BINARY) = CAST(i.`guid` AS BINARY)
  SET i.`product_id` = p.`product_id`;

INSERT IGNORE INTO `oc_product_description`
  (`product_id`,`language_id`,`name`,`description`,`tag`,`meta_title`,`meta_description`,`meta_keyword`)
SELECT i.`product_id`, @lang, i.`name`, i.`descr`, '', i.`name`, '', ''
FROM `oc_import_1c` i WHERE i.`product_id` IS NOT NULL;

INSERT IGNORE INTO `oc_product_to_store` (`product_id`,`store_id`)
SELECT i.`product_id`, @store FROM `oc_import_1c` i WHERE i.`product_id` IS NOT NULL;

INSERT IGNORE INTO `oc_product_to_category` (`product_id`,`category_id`)
SELECT i.`product_id`, i.`category_id` FROM `oc_import_1c` i
WHERE i.`product_id` IS NOT NULL AND i.`category_id` IS NOT NULL;

-- ---- Что получилось -------------------------------------------------
SELECT COUNT(*) AS `строк из 1С` FROM `oc_import_1c`;
SELECT COUNT(*) AS `заведено товаров` FROM `oc_import_1c` WHERE `product_id` IS NOT NULL;
SELECT COUNT(*) AS `без раздела` FROM `oc_import_1c` WHERE `category_id` IS NULL;

-- ---- Человекопонятные адреса ----------------------------------------
--  Без этого раздела товар открывается по адресу вида
--  index.php?route=product/product&product_id=123 - работает, но
--  и человеку, и поисковику такой адрес не говорит ничего.
--
--  Если адрес уже кем-то занят, мы его НЕ трогаем, а отказываемся
--  от своего: в oc_seo_url нет запрета на повторы, и два одинаковых
--  адреса открывали бы одну и ту же страницу вместо двух разных.
--  Повторный запуск скрипта поэтому ничего не добавляет: адрес уже
--  занят нашей же прошлой строкой.
--
--  Весь этот раздел можно удалить, если человекопонятные адреса
--  в магазине выключены - тогда он просто ничего не даёт.
UPDATE `oc_import_1c` i
  JOIN `oc_seo_url` s
    ON CAST(LOWER(s.`keyword`) AS BINARY) = CAST(i.`keyword` AS BINARY)
   AND s.`store_id` = @store AND s.`language_id` = @lang
  SET i.`keyword` = '';

INSERT INTO `oc_seo_url` (`store_id`,`language_id`,`query`,`keyword`)
SELECT @store, @lang, CONCAT('product_id=', i.`product_id`), i.`keyword`
FROM `oc_import_1c` i
WHERE i.`product_id` IS NOT NULL AND i.`keyword` <> '';

SELECT COUNT(*) AS `адресов заведено` FROM `oc_import_1c` WHERE `keyword` <> '';

--  Если какие-то из этих товаров уже были на сайте, заведённые руками,
--  они не опознаются по номеру из 1С и удвоятся. Этот запрос показывает
--  одинаковые названия — если список пуст, дублей нет.
SELECT pd.`name` AS `повторяется название`, COUNT(*) AS `штук`
FROM `oc_product_description` pd
WHERE pd.`language_id` = @lang
GROUP BY pd.`name` HAVING COUNT(*) > 1
ORDER BY 2 DESC;
"""



def scan(text):
    """Проходит текст так, как его прочтёт сервер: возвращает
    (осталось_внутри_строки, глубина_скобок, число_запятых_вне_скобок_1_уровня)."""
    in_str = esc = False
    depth = 0
    commas = 0
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == "'":
                in_str = False
            continue
        if ch == "'":
            in_str = True
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == ',' and depth == 1:
            commas += 1
    return in_str, depth, commas


def verify_sql(text, rows, cols):
    """Проверка собранного SQL без базы данных.

    Настоящей MySQL под рукой нет, а самая вероятная поломка здесь
    одна и известна: апостроф или обратная косая в названии товара,
    от которых строковая скобка закрывается посреди фразы, и остаток
    файла выполняется как команды. В сегодняшней выгрузке таких знаков
    нет ни одного - в следующей будут.

    Поэтому файл прочитывается посимвольно, как его прочтёт сервер.
    Каждая строка значений проверяется отдельно, а не куском файла
    до первой точки с запятой: точка с запятой может оказаться внутри
    названия товара, и тогда проверялся бы огрызок.
    """
    bad = []
    for i, row in enumerate(rows, 1):
        in_str, depth, commas = scan(row)
        if in_str:
            bad.append(f'строка значений {i}: кончилась внутри строковой скобки '
                       f'- апостроф в названии не экранирован')
        elif depth:
            bad.append(f'строка значений {i}: не закрыто скобок: {depth}')
        elif commas != cols - 1:
            bad.append(f'строка значений {i}: полей {commas + 1}, ожидалось {cols}')
    in_str, depth, _ = scan(text)
    if in_str:
        bad.append('файл кончился внутри строковой скобки')
    if depth:
        bad.append(f'по всему файлу не закрыто скобок: {depth}')
    return bad


def write_sql(by_cat, cats):
    order = sorted(by_cat.items(), key=lambda kv: -len(kv[1]))
    slugs = unique_slugs(
        [(('cat', cid), cats[cid][0]) for cid, _ in order]
        + [(('prod', g['guid']), g['name']) for _, items in order for g in items])
    rows = []
    for cid, items in by_cat.items():
        for g in items:
            rows.append('  (' + ', '.join([
                q(g['guid']), q(cid), q(g['name'][:255]), q(g['model'][:64]),
                f'{g["price"]:.4f}', q(g['descr']), q(slugs[('prod', g['guid'])]),
            ]) + ')')
    n = len(rows)

    out = [SQL_HEAD.format(src=SRC.name, date=DATE, n=n, c=len(by_cat))]
    out.append(',\n'.join(rows) + ';\n')

    out.append('\n-- ---- Разделы каталога ----------------------------------------------\n'
               '--  Раздел ищется по названию: если такой уже есть, второй\n'
               '--  не заводится, а товары ложатся в существующий.\n')
    for cid, items in order:
        name = cats[cid][0]
        out.append(f'\n-- {name} ({len(items)} тов.)')
        out.append(f'SET @cat := (SELECT category_id FROM `oc_category_description`\n'
                   f'             WHERE name = {q(name)} AND language_id = @lang LIMIT 1);')
        # top = 1 только у разделов верхнего уровня: по этому полю движок
        # собирает главное меню. С нулём раздел заводится, товары в него
        # ложатся, а в меню сайта его нет - и найти его можно только
        # поиском. Ровно так и выглядит «каталог залили, а на сайте пусто».
        out.append('INSERT INTO `oc_category` (`image`,`parent_id`,`top`,`column`,`sort_order`,'
                   '`status`,`date_added`,`date_modified`)\n'
                   "SELECT '', @parent, IF(@parent = 0, 1, 0), 1, 0, 1, NOW(), NOW()\n"
                   '  FROM DUAL WHERE @cat IS NULL;')
        out.append('SET @cat := IFNULL(@cat, LAST_INSERT_ID());')
        out.append('INSERT IGNORE INTO `oc_category_description` (`category_id`,`language_id`,'
                   '`name`,`description`,`meta_title`,`meta_description`,`meta_keyword`)\n'
                   f'VALUES (@cat, @lang, {q(name)}, \'\', {q(name)}, \'\', \'\');')
        out.append('INSERT IGNORE INTO `oc_category_to_store` (`category_id`,`store_id`) '
                   'VALUES (@cat, @store);')
        # Путь до раздела движок хранит отдельной таблицей и сам её
        # не достроит. Сначала переносим путь родителя, потом дописываем
        # себя на следующем уровне; у раздела верхнего уровня строк
        # родителя нет, и уровень выходит нулевым.
        out.append('INSERT IGNORE INTO `oc_category_path` (`category_id`,`path_id`,`level`)\n'
                   'SELECT @cat, p.`path_id`, p.`level` FROM `oc_category_path` p\n'
                   ' WHERE p.`category_id` = @parent;')
        out.append('SET @lvl := (SELECT IFNULL(MAX(`level`) + 1, 0) FROM `oc_category_path`\n'
                   '              WHERE `category_id` = @cat);')
        out.append('INSERT IGNORE INTO `oc_category_path` (`category_id`,`path_id`,`level`) '
                   'VALUES (@cat, @cat, @lvl);')
        out.append(f'UPDATE `oc_import_1c` SET `category_id` = @cat WHERE `cat_guid` = {q(cid)};')
        kw = slugs[('cat', cid)]
        out.append(f'SET @kw := (SELECT 1 FROM `oc_seo_url` WHERE `keyword` = {q(kw)}\n'
                   '              AND `store_id` = @store AND `language_id` = @lang LIMIT 1);')
        out.append('INSERT INTO `oc_seo_url` (`store_id`,`language_id`,`query`,`keyword`)\n'
                   f"SELECT @store, @lang, CONCAT('category_id=', @cat), {q(kw)}\n"
                   '  FROM DUAL WHERE @kw IS NULL;')

    out.append(SQL_TAIL)
    text = '\n'.join(out) + '\n'

    # Собранный файл проверяется до записи: битый SQL лучше не отдавать
    # вовсе, чем отдать и узнать о поломке на живой базе.
    bad = verify_sql(text, rows, 7)
    if bad:
        print('SQL не записан, в нём ошибки:')
        for b in bad:
            print('  ', b)
        raise SystemExit(2)

    OUT_SQL.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
