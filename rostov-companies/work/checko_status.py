"""Статус в ЕГРЮЛ/ЕГРИП и контакты всех компаний списка — через API Checko.

Запуск (из этой папки):
    python checko_status.py              ключ возьмёт из CHECKO_API_KEY, checko_key.txt или спросит
    python checko_status.py --limit 100  не больше 100 запросов за этот запуск
    python checko_status.py --offline    без запросов: пересобрать таблицу из уже скачанного

Один запрос на компанию. Каждый ответ сохраняется в checko_cache/<ИНН>.json,
поэтому повторный запуск не тратит запросы на уже полученные компании и
продолжает с места остановки (бесплатный тариф Checko — 100 запросов в сутки:
запускайте раз в день, пока не скажет «все компании получены»).

Ключей может быть несколько — в checko_key.txt по одному в строке (или через
запятую в CHECKO_API_KEY). Когда у ключа кончается лимит или баланс, программа
сама берёт следующий и повторяет ту же компанию; кэш общий, ключ на него не влияет.

Первыми идут компании, по которым поиск ничего не дал, затем — без почты,
затем остальные: если лимит кончится на середине, самое нужное уже будет.

Итог: out/checko.json (разобранные ответы) и таблица
«Строители_РО_статус_и_почты.xlsx» (собирает build.py, нужен openpyxl).
Стандартная библиотека Python 3.8+, без сторонних пакетов.
"""
import argparse
import collections
import csv
import getpass
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = '06.10.2026, сборка 8'
HERE = os.path.dirname(os.path.abspath(__file__))
API = os.environ.get('CHECKO_API_URL', 'https://api.checko.ru/v2').rstrip('/')
CACHE = os.path.join(HERE, 'checko_cache')
KEY_FILE = os.path.join(HERE, 'checko_key.txt')
RESULT = os.path.join(HERE, 'out', 'checko.json')
TABLE = 'Строители_РО_статус_и_почты.xlsx'

EMAIL = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
# Ошибки, после которых дальше спрашивать бессмысленно: ключ, лимит, деньги.
FATAL = re.compile(r'ключ|key|лимит|limit|баланс|balance|средств|тариф|оплат|доступ|access|forbidden|превыш', re.I)
NOT_FOUND = re.compile(r'не найден|not found|отсутств|нет данных', re.I)
# «Слишком часто» — подождать и повторить тем же ключом, а не выбрасывать ключ.
RATE = re.compile(r'в секунд|в минуту|per second|per minute|слишком част|too many|частот', re.I)

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors='replace')
    except Exception:  # noqa: BLE001 — старый Python или необычная консоль
        pass


# ---------------------------------------------------------------- разбор ответа

def text_of(v):
    """Текст из значения любой формы: строка, {"Наим": ...}, список."""
    if v is None or isinstance(v, bool):
        return ''
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, dict):
        for k in ('Наим', 'Название', 'Текст', 'Статус', 'Описание'):
            if isinstance(v.get(k), str) and v[k].strip():
                return v[k].strip()
        return ''
    if isinstance(v, list):
        return '; '.join(t for t in (text_of(x) for x in v) if t)
    return ''


def ru_date(s):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s or '')
    return f'{m.group(3)}.{m.group(2)}.{m.group(1)}' if m else (s or '')


def strings_in(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from strings_in(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings_in(v)


def contacts(data):
    """Почты, телефоны и сайт — только из блока контактов самой компании.

    Весь ответ не обходится нарочно: в нём есть учредители, связанные
    компании и руководитель, и их почты приписались бы не той организации.
    """
    block = data.get('Контакты')
    if block is None:
        # только точные имена: подстрока «тел» сидит и в «Учредитель», и в «Руководитель»
        block = {k: v for k, v in data.items() if re.fullmatch(
            r'тел\w*|емэйл|e?-?mail|почта|эл\w*почт\w*|вебсайт|сайт|контакт\w*', k, re.I)}
    emails, phones, site = [], [], ''
    if isinstance(block, dict):
        for k, v in block.items():
            if re.search(r'тел|phone', k, re.I):
                for s in strings_in(v):
                    if s.strip() and s.strip() not in phones:
                        phones.append(s.strip())
            elif re.search(r'сайт|site|url|web', k, re.I):
                site = site or text_of(v) or next(strings_in(v), '')
    for s in strings_in(block):
        for e in EMAIL.findall(s):
            if e.lower() not in emails:
                emails.append(e.lower())
    return emails, phones, site


def head_of(data):
    r = data.get('Руковод')
    if isinstance(r, list):
        r = r[0] if r else None
    if not isinstance(r, dict):
        return ''
    post = r.get('ДолжнРук') or r.get('НаимДолжн') or r.get('Должн') or ''
    return ' '.join(x for x in (text_of(post), r.get('ФИО') or '') if x)


def classify(data, is_ip):
    """Статус Checko -> категория таблицы. Возвращает (статус, дата, пояснение)."""
    st = data.get('Статус')
    st_text = text_of(st)
    st_date = st.get('Дата', '') if isinstance(st, dict) else ''
    end_date = ''
    for k in ('ДатаЛикв', 'ДатаПрекращ', 'ДатаПрекр'):
        if isinstance(data.get(k), str) and data[k]:
            end_date = data[k]
    reason = ''
    for k in ('Ликвид', 'Прекращ', 'СпПрекр'):
        v = data.get(k)
        if isinstance(v, dict):
            reason = reason or text_of(v)
            end_date = end_date or (v.get('Дата') or '')
        elif isinstance(v, str) and v:
            reason = reason or v
    t = f'{st_text} | {reason}'.lower()

    upcoming = 'предстоящ' in t
    closed = bool(end_date) or (not upcoming and re.search(
        r'ликвидирован|прекратил|прекращен|не действ|недейств|исключен[аоы]? из', t))
    if closed:
        if 'исключ' in t:
            status = 'Исключена ФНС'
        elif re.search(r'присоедин|реорганиз|слиян|преобраз|разделен|выделен', t):
            status = 'Реорганизована'
        elif is_ip:
            status = 'ИП прекратил деятельность'
        else:
            status = 'Ликвидирована'
    elif upcoming:
        status = 'Предстоящее исключение'
    elif re.search(r'банкрот|конкурсн|наблюдени|внешн\w* управлен|оздоровлен', t):
        status = 'Банкротство'
    elif re.search(r'ликвидац|ликвидир', t):
        status = 'В процессе ликвидации'
    elif re.search(r'действ|реорганизац', t):
        status = 'Действует'
    else:
        status = 'Не установлено'

    detail = f'ЕГРЮЛ/ЕГРИП (Checko): «{st_text or "статус не указан"}»'
    if reason:
        detail += f'; прекращение: {reason}'
    if status == 'Действует' and 'реорганизац' in t:
        detail += '; в процессе реорганизации'
    return status, ru_date(end_date if closed else st_date), detail


def parse(inn, company, payload):
    """Ответ Checko -> запись для build.py (тот же формат, что у поиска)."""
    meta = payload.get('meta') or {}
    data = payload.get('data') or {}
    is_ip = len(inn) == 12
    if meta.get('status') == 'error' or not data:
        msg = meta.get('message') or 'пустой ответ'
        return {'inn': inn, 'status': 'Не установлено', 'status_date': '', 'email': '',
                'status_detail': f'Checko: {msg}', 'current_name': '', 'source': 'Checko API',
                'searches': 1, 'via': 'checko', 'phones': '', 'site': ''}
    status, date, detail = classify(data, is_ip)
    got = str(data.get('ИНН') or '')
    if got and got != inn:
        detail += f'; ВНИМАНИЕ: Checko вернул ИНН {got}'
        status = 'Не установлено'
    ogrn = str(data.get('ОГРНИП') or data.get('ОГРН') or '')
    if is_ip and ogrn and company.get('ogrn') and ogrn != company['ogrn']:
        detail += f'; ОГРНИП сменился: в файле {company["ogrn"]}, сейчас {ogrn} (новая регистрация)'
    efrsb = data.get('ЕФРСБ')
    if isinstance(efrsb, list) and efrsb and status not in ('Банкротство',):
        last = efrsb[-1] if isinstance(efrsb[-1], dict) else {}
        detail += f'; в ЕФРСБ сообщений: {len(efrsb)}' + (
            f' (последнее: {text_of(last.get("Тип"))} {ru_date(last.get("Дата", ""))})' if last else '')
    emails, phones, site = contacts(data)
    name = data.get('НаимСокр') or data.get('НаимПолн') or (f'ИП {data["ФИО"]}' if data.get('ФИО') else '')
    addr = data.get('ЮрАдрес')
    return {
        'inn': inn, 'status': status, 'status_date': date, 'status_detail': detail,
        'email': '; '.join(emails), 'current_name': name,
        'source': f'Checko API (ЕГРЮЛ/ЕГРИП), https://checko.ru/search?query={inn}',
        'searches': 1, 'via': 'checko', 'phones': '; '.join(phones[:5]), 'site': site,
        'address': text_of(addr.get('АдресПолн')) if isinstance(addr, dict) else text_of(addr),
        'head': head_of(data),
    }


# ---------------------------------------------------------------- запросы

# «key1=…», «ключ 2: …», «API key = …» — подпись перед ключом отбрасывается
LABEL = re.compile(r'^(?:(?:checko|чекко|мой|my)[ _-]?)?(?:api[ _-]?)?(?:key|ключ|token|токен)'
                   r'\s*(?:№|#)?\s*\d*\s*[:=]\s*', re.I)
KEY_SHAPE = re.compile(r'[A-Za-z0-9_.+/-]{8,}={0,2}')


def split_keys(text):
    """Ключи из текста: по строкам, в строке — через пробел, запятую или «;».

    Пропускаются пустые строки, комментарии (#), подписи вида «key1=» и всё,
    что на ключ не похоже (кириллица, короткие слова): Блокнот и человек
    добавляют такое охотно, а неверный «ключ» Checko просто отвергнет.
    """
    keys = []
    for line in (text or '').splitlines():
        line = line.strip().lstrip('\ufeff')
        if not line or line.startswith('#'):
            continue
        for token in re.split(r'[\s,;]+', LABEL.sub('', line)):
            token = LABEL.sub('', token.strip('"\'«»`'))
            if KEY_SHAPE.fullmatch(token):
                keys.append(token)
    return keys


def mask(key):
    """В вывод ключ попадает только последними четырьмя знаками."""
    return f'…{key[-4:]}' if len(key) > 8 else '…'


def key_files():
    """Текстовые файлы с ключами рядом с программой: checko_key.txt, ключи.txt, keys.txt, api.txt…

    Берётся любой .txt (или файл без расширения), в имени которого есть
    key / ключ / checko / api, — человек называет список как ему удобно.
    «ключи.txt.txt» тоже подходит: Windows прячет расширения, и Блокнот
    охотно дописывает второе .txt. README и файлы программы не читаются.
    """
    out = []
    for name in sorted(os.listdir(HERE), key=lambda n: (n.lower() != 'checko_key.txt', n.lower())):
        low = name.lower()
        path = os.path.join(HERE, name)
        if (os.path.isfile(path) and re.search(r'key|ключ|checko|api', low) and 'readme' not in low
                and (low.endswith('.txt') or '.' not in low) and os.path.getsize(path) < 1_000_000):
            out.append(path)
    return out


def get_keys(args):
    keys = split_keys(args.key) + split_keys(os.environ.get('CHECKO_API_KEY', ''))
    if not keys:
        for path in key_files():
            with open(path, encoding='utf-8-sig', errors='replace') as f:
                found = split_keys(f.read())
            print(f'Ключи из «{os.path.basename(path)}»: {len(found)} шт.')
            keys += found
    if keys:
        return list(dict.fromkeys(keys))
    print('Файла с ключами рядом с программой нет. Положите его в эту папку:')
    print(f'    {HERE}')
    print('  имя — любое со словом «ключ», «key» или «api» (например, ключи.txt), по одному ключу в строке.')
    up = os.path.dirname(HERE)
    near = [n for n in os.listdir(up) if re.search(r'key|ключ|checko|api', n.lower())
            and n.lower().endswith('.txt') and os.path.isfile(os.path.join(up, n))]
    if near:
        print(f'  Похожий файл лежит на папку выше: «{near[0]}» — перенесите его сюда и запустите снова.')
    print('Нужен API-ключ Checko (checko.ru -> API -> ключ).')
    print('Вставьте ключ правой кнопкой мыши или Ctrl+V и нажмите Enter — символы на экране')
    print('не появятся, так и должно быть. Ключей несколько — вставляйте по одному.')
    print('Когда ключи кончатся, просто нажмите Enter.')
    while True:
        try:
            k = getpass.getpass(f'Ключ №{len(keys) + 1}: ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not k:
            if keys:
                break
            print('  Нужен хотя бы один ключ.')
            try:
                leave = input('  Выйти без проверки? [д/Н]: ').strip().lower() in ('д', 'да', 'y', 'yes')
            except (EOFError, KeyboardInterrupt):
                leave = True
            if leave:
                break
            continue
        got = [x for x in split_keys(k) if x not in keys]
        if not got:
            print('  Это не похоже на ключ (или он уже введён) — вставьте ещё раз или нажмите Enter.')
            continue
        keys += got
        print('  Принят: ' + ', '.join(mask(x) for x in got))
    try:
        save = keys and input('Сохранить ключи, чтобы завтра не вводить заново? [Д/н]: ').strip().lower() in ('', 'д', 'да', 'y', 'yes')
    except (EOFError, KeyboardInterrupt):
        save = False
    if save:
        with open(KEY_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(keys) + '\n')
    return keys


def fetch(inn, key):
    """Один запрос. Возвращает (payload | None, текст ошибки)."""
    endpoint = 'entrepreneur' if len(inn) == 12 else 'company'
    url = f'{API}/{endpoint}?' + urllib.parse.urlencode({'key': key, 'inn': inn})
    req = urllib.request.Request(url, headers={'User-Agent': 'rostov-companies/1.0', 'Accept': 'application/json'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode('utf-8')), ''
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'replace')
            try:
                payload = json.loads(body)
                if isinstance(payload, dict) and payload.get('meta'):
                    return payload, ''
            except ValueError:
                pass
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(5 * (attempt + 1))
                continue
            return None, f'HTTP {e.code}: {body[:200]}'
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            return None, f'сеть: {getattr(e, "reason", e)}'
        except ValueError:
            return None, 'ответ не JSON'
    return None, 'не удалось'


def cached(inn):
    p = os.path.join(CACHE, f'{inn}.json')
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    return None


def order(companies):
    """Сначала то, что поиск не нашёл, потом без почты, потом остальное."""
    best = {}
    for f in glob.glob(os.path.join(HERE, 'out', '*.json')):
        if os.path.basename(f) == 'checko.json':
            continue
        for r in json.load(open(f, encoding='utf-8')):
            if (r.get('searches') or 0) > 0:
                found = r.get('status', 'Не установлено') != 'Не установлено'
                score = 2 * found + bool(r.get('email'))
                best[r['inn']] = max(best.get(r['inn'], 0), score)
    return sorted(companies, key=lambda c: best.get(c['inn'], 0))


def main():
    ap = argparse.ArgumentParser(description='Статус и контакты компаний через API Checko')
    ap.add_argument('--key', help='API-ключ, несколько — через запятую (лучше через checko_key.txt)')
    ap.add_argument('--limit', type=int, default=0, help='не больше N запросов за запуск')
    ap.add_argument('--delay', type=float, default=0.4, help='пауза между запросами, с')
    ap.add_argument('--only', default='', help='только эти ИНН через запятую')
    ap.add_argument('--offline', action='store_true', help='без запросов, только пересобрать таблицу')
    args = ap.parse_args()
    os.chdir(HERE)
    os.makedirs(CACHE, exist_ok=True)
    print(f'Проверка через Checko, версия {VERSION}')

    seen, companies = set(), []
    for x in json.load(open('all.json', encoding='utf-8')):
        if x['ИНН'] not in seen:
            seen.add(x['ИНН'])
            companies.append({'inn': x['ИНН'], 'ogrn': x['ОГРН/ОГРНИП'],
                              'name': x['Сокращенное наименование'] or x['Полное наименование']})
    scope = companies
    if args.only:
        want = {s.strip() for s in args.only.split(',') if s.strip()}
        scope = [c for c in companies if c['inn'] in want]
    todo = [c for c in order(scope) if cached(c['inn']) is None]
    print(f'Компаний: {len(scope)}, уже получено: {len(scope) - len(todo)}, осталось: {len(todo)}')

    stop = ''
    if todo and not args.offline:
        keys = get_keys(args)
        if not keys:
            sys.exit('Ключ не введён — выхожу.')
        if len(keys) > 1:
            print(f'Ключей: {len(keys)} — когда у ключа кончится лимит, перейду к следующему.')
        ki = done = errors = 0
        used = collections.Counter()
        metas = {}
        refused = {}   # ключи, которые Checko не принял (не лимит), — для подсказки в конце
        for c in todo:
            if args.limit and done >= args.limit:
                stop = f'достигнут --limit {args.limit}'
                break
            waits = 0
            while True:
                payload, err = fetch(c['inn'], keys[ki])
                m = (payload or {}).get('meta') or {}
                msg = str(m.get('message') or '')
                if 'today_request_count' in m:
                    metas[ki] = m
                if payload is None or m.get('status') != 'error' or NOT_FOUND.search(msg):
                    break
                if RATE.search(msg) and waits < 3:      # слишком часто — подождать тем же ключом
                    waits += 1
                    time.sleep(5 * waits)
                    continue
                if not FATAL.search(msg):
                    break
                # ключ выбыл (лимит, баланс, неверный) — та же компания следующим ключом
                print(f'  Ключ №{ki + 1} ({mask(keys[ki])}): {msg}')
                if not re.search(r'лимит|limit|превыш|баланс|balance|средств|оплат|тариф', msg, re.I):
                    refused[ki] = msg
                if ki + 1 >= len(keys):
                    stop = f'Checko: {msg}' + (' — у всех ключей' if len(keys) > 1 else '')
                    break
                ki += 1
                print(f'  Переключаюсь на ключ №{ki + 1} ({mask(keys[ki])}) и продолжаю с той же компании.')
            if stop:
                break
            done += 1
            if payload is None:
                errors += 1
                print(f'  [{done}] {c["inn"]} {c["name"][:40]} — ошибка: {err}')
                if errors >= 5:
                    stop = 'пять ошибок подряд — проверьте интернет и попробуйте позже'
                    break
                continue
            if m.get('status') == 'error' and not NOT_FOUND.search(msg):
                errors += 1
                print(f'  [{done}] {c["inn"]} — Checko: {msg}')
                if errors >= 5:
                    stop = f'пять ошибок подряд, последняя: {msg}'
                    break
                continue
            errors = 0
            used[ki] += 1
            with open(os.path.join(CACHE, f'{c["inn"]}.json'), 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False)
            r = parse(c['inn'], c, payload)
            print(f'  [{done}/{len(todo)}] {c["inn"]} {c["name"][:38]:<38} {r["status"]:<24} {r["email"][:40]}')
            time.sleep(args.delay)
        for i in sorted(set(used) | set(metas)):
            meta = metas.get(i, {})
            print(f'Ключ №{i + 1} ({mask(keys[i])}): получено за этот запуск {used[i]}, '
                  f'по счётчику Checko сегодня {meta.get("today_request_count", "?")}, баланс {meta.get("balance", "?")}')
        for i, msg in refused.items():
            print(f'Ключ №{i + 1} ({mask(keys[i])}) Checko не принял: {msg}. Проверьте его в личном кабинете '
                  'или уберите из checko_key.txt (там по одному ключу в строке).')

    # разбор всего кэша заново — так правка разбора не требует новых запросов
    results = []
    for c in order(companies):
        payload = cached(c['inn'])
        if payload is not None:
            results.append(parse(c['inn'], c, payload))
    os.makedirs(os.path.dirname(RESULT), exist_ok=True)
    with open(RESULT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    with open('checko_results.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['ИНН', 'Статус', 'Дата', 'Почта', 'Телефоны', 'Сайт', 'Наименование', 'Пояснение'])
        for r in results:
            w.writerow([r['inn'], r['status'], r['status_date'], r['email'], r.get('phones', ''),
                        r.get('site', ''), r['current_name'], r['status_detail']])

    left = len(companies) - len(results)
    print(f'\nПолучено из Checko: {len(results)} из {len(companies)}.', end=' ')
    print('Все компании получены.' if not left else f'Осталось {left} — запустите снова (завтра, если кончился суточный лимит).')
    if stop:
        print(f'Остановлено: {stop}')

    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print('Для таблицы Excel нужен openpyxl: python -m pip install openpyxl\n'
              'Пока результат — в checko_results.csv (открывается в Excel).')
        return
    sys.stdout.flush()
    rc = subprocess.call([sys.executable, 'build.py', TABLE])
    if rc == 0:
        print(f'Таблица готова: {os.path.join(HERE, TABLE)}')


if __name__ == '__main__':
    main()
