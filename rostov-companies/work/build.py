"""Сборка итоговой таблицы.

Источники:
  all.json           — обе выгрузки реестра СРО (parse.py);
  out/batch_*.json,
  out/r*.json        — веб-поиск по ИНН (по каждому ИНН берётся лучший результат);
  out/checko.json    — ЕГРЮЛ/ЕГРИП через API Checko (checko_status.py).

Статус из Checko важнее статуса из поиска: это выписка из реестра, а не
пересказ выдачи. Почты из обоих источников объединяются.

python build.py "Строители_РО_статус_и_почты.xlsx"
"""
import collections
import glob
import json
import os
import re
import sys

from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors='replace')
    except Exception:  # noqa: BLE001
        pass

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = ARGS[0] if ARGS else 'result.xlsx'
SIMPLE = '--simple' in sys.argv   # один лист с главными столбцами (просьба заказчика)


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def score(r):
    return 2 * (r.get('status', 'Не установлено') != 'Не установлено') + bool(r.get('email'))


src = load('all.json')
res = {}
for f in sorted(glob.glob('out/batch_*.json')) + sorted(glob.glob('out/r*.json')):
    for r in load(f):
        if (r.get('searches') or 0) > 0 and (r['inn'] not in res or score(r) >= score(res[r['inn']])):
            res[r['inn']] = r
chk = {r['inn']: r for r in load('out/checko.json')} if os.path.exists('out/checko.json') else {}

GROUP = {
    'Действует': 'Действует',
    'В процессе ликвидации': 'Закрывается',
    'Банкротство': 'Закрывается',
    'Предстоящее исключение': 'Закрывается',
    'Ликвидирована': 'Не существует',
    'Исключена ФНС': 'Не существует',
    'Реорганизована': 'Не существует',
    'ИП прекратил деятельность': 'Не существует',
    'Не установлено': 'Не найдено',
    'Ещё не проверялась': 'Не проверялась',
}
ORDER = ['Действует', 'Закрывается', 'Не существует', 'Не найдено', 'Не проверялась']
FILL = {'Действует': 'E2F0D9', 'Закрывается': 'FFF2CC', 'Не существует': 'F8D7DA',
        'Не найдено': 'EDEDED', 'Не проверялась': 'FFFFFF'}

# дубли по ИНН (одна компания есть в обоих файлах) сливаются в одну строку
rows = {}
for x in src:
    inn = x['ИНН']
    file_ = '1' if x['_src'].startswith('файл 1') else '2'
    if 'Статус права' in x:
        m = {'Действует': 'член СРО', 'Прекращено': 'прекращено',
             'Приостановлено': 'приостановлено', '': 'нет данных'}.get(x['Статус права'], x['Статус права'])
    else:
        d = x.get('Дата прекращения членства', '')
        m = f'прекращено {d}' if d else 'член СРО'
    where = f'файл {file_}, № {x["N п/п"]}'
    member = 'Да' if m == 'член СРО' else 'Приостановлено' if m == 'приостановлено' else 'Нет'
    extra = dict(  # остальные столбцы исходных файлов — переносятся как есть
        full=x.get('Полное наименование', ''), sro_reg=x.get('Регистрационный номер в реестре СРО', ''),
        sro_date=x.get('Дата регистрации в реестре СРО', ''), gos_date=x.get('Дата государственной регистрации', ''),
        kf=x.get('КФ', ''), decision=x.get('Решение', ''), file_email=x.get('электронная почта', ''),
    )
    if inn in rows:  # компания есть в обоих файлах — различающиеся значения через «; »
        rows[inn]['where'] += '; ' + where
        rows[inn]['sro'] += '; ' + m
        rank = ['Нет', 'Приостановлено', 'Да']
        rows[inn]['member'] = max(rows[inn]['member'], member, key=rank.index)
        for k, v in extra.items():
            if v and v not in rows[inn][k].split('; '):
                rows[inn][k] = f'{rows[inn][k]}; {v}' if rows[inn][k] else v
        continue
    rows[inn] = dict(
        inn=inn, ogrn=x['ОГРН/ОГРНИП'],
        name=x['Сокращенное наименование'] or x['Полное наименование'],
        phone=x.get('Контактные телефоны', ''),
        addr=x.get('юр адрес') or x.get('Адрес места нахождения юридического лица', ''),
        head=x.get('ФИО') or x.get('Фамилия, имя, отчество (при наличии) для ИП', ''),
        sro=m, where=where, member=member, **extra,
    )


def emails_of(*records):
    out = []
    for r in records:
        for e in re.split(r'[;,\s]+', (r or {}).get('email', '') or ''):
            e = e.strip().lower()
            if '@' in e and e not in out:
                out.append(e)
    return '; '.join(out)


RECHECK = re.compile(r'перепровер|не подтвержд|противореч|косвенн|реорганиз|не указал|не указана страниц'
                     r'|источник[^.;]{0,30}не указ|актуальност\w* не указ|устаревш|вероятн|ВНИМАНИЕ', re.I)
recs = []
for inn, r in rows.items():
    s, c = res.get(inn), chk.get(inn)
    if c and c['status'] != 'Не установлено':
        main, via = c, 'Checko'           # выписка из реестра
    elif s:
        main, via = s, 'поиск'
    elif c:
        main, via = c, 'Checko'           # Checko ответил, но статуса нет (не найден)
    else:
        main, via = {}, ''
    st = main.get('status') or 'Ещё не проверялась'
    if st not in GROUP:
        print('!! неизвестный статус', inn, st)
        st = 'Не установлено'
    det = main.get('status_detail', '') or ''
    if via == 'поиск' and c:
        det += f' | {c["status_detail"]}'
    recheck = ''
    if st not in ('Ещё не проверялась', 'Не установлено'):
        if RECHECK.search(det) or (via == 'поиск' and not main.get('source')):
            recheck = 'да'
    sources = [x.get('source', '') for x in (c, s) if x and x.get('source')]
    recs.append(dict(r, group=GROUP[st], status=st, date=main.get('status_date', ''), recheck=recheck,
                     email=emails_of(c, s, {'email': r['file_email']}),
                     phones=(c or {}).get('phones', ''), site=(c or {}).get('site', ''),
                     cur=main.get('current_name', '') or (s or {}).get('current_name', ''),
                     detail=det, source=' '.join(sources), via=via))
recs.sort(key=lambda r: (ORDER.index(r['group']), r['email'] == '', r['name'].lower()))


# ---------------------------------------------------------------- понятные поля для рабочих листов

def phones_merged(*parts):
    """Телефоны из файла и из Checko одной строкой, без повторов (сверка по последним 10 цифрам)."""
    out, seen = [], set()
    for part in parts:
        for p in re.split(r'[;,]\s*', part or ''):
            p = p.strip()
            digits = re.sub(r'\D', '', p)
            if len(digits) < 6 or digits[-10:] in seen:
                continue
            seen.add(digits[-10:])
            out.append(p)
    return ', '.join(out)


LATIN_LOOKALIKE = str.maketrans('ABCEHKMOPTXY', 'АВСЕНКМОРТХУ')


def plain(name):
    """Название без формы, кавычек и регистра — чтобы заметить настоящую смену названия."""
    t = re.sub(r'[^0-9A-ZА-ЯЁ ]', ' ', (name or '').upper().translate(LATIN_LOOKALIKE))
    t = re.sub(r'\b(ООО|ОАО|ЗАО|АО|ПАО|НАО|ИП|МУП|МКУ|МБУ|МУ|ГУП|ФГУП|ГБУ|СЗ|ТД|СК|ФИРМА|'
               r'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ|СПЕЦИАЛИЗИРОВАННЫЙ ЗАСТРОЙЩИК)\b', ' ', t)
    return re.sub(r'\s+', '', t)


def same_name(a, b):
    """Одно ли это название: реестр пишет его сокращённо («Донская Строительная Компания» —
    «ДСК», «ТехГазМонтаж» — «ТГМ»), иногда с опечаткой или в скобках после полного."""
    pa, pb = plain(a), plain(b)
    if not pa or not pb or pa == pb or pa in pb or pb in pa or edits(pa, pb) <= 2:
        return True
    short, long_ = sorted((pa, pb), key=len)
    rest = iter(long_)
    return short[0] == long_[0] and all(ch in rest for ch in short)   # сокращение: буквы по порядку


def what_happens(r):
    """Человеческое описание статуса: что с компанией."""
    d, st = r['detail'].lower(), r['status']
    if st == 'Банкротство':
        if 'наблюдени' in d:
            return 'Банкротство: наблюдение'
        if 'конкурсн' in d:
            return 'Банкротство: конкурсное производство'
        return 'Дело о банкротстве'
    if st == 'В процессе ликвидации':
        return 'Ликвидируется'
    if st == 'Предстоящее исключение':
        return 'Налоговая готовит исключение из реестра' + (' (недостоверные сведения)' if 'недостовер' in d else '')
    if st == 'Исключена ФНС':
        if 'недостовер' in d:
            return 'Исключена налоговой: недостоверные сведения'
        if 'недейств' in d:
            return 'Исключена налоговой как недействующая'
        return 'Исключена налоговой'
    if st == 'Реорганизована':
        for k, v in (('присоедин', 'присоединена к другой компании'), ('слияни', 'слияние с другой компанией'),
                     ('преобраз', 'преобразована в другую форму'), ('разделен', 'разделена')):
            if k in d:
                return f'Реорганизована: {v}'
        return 'Реорганизована'
    if st == 'Ликвидирована':
        return 'Ликвидирована после банкротства' if 'конкурсного производства' in d else 'Ликвидирована'
    if st == 'ИП прекратил деятельность':
        return 'ИП закрыт'
    return st


def note_of(r):
    d, notes = r['detail'], []
    if 'в процессе реорганизации' in d or 'находится в процессе реорганизации' in d.lower():
        notes.append('идёт реорганизация')
    if 'места нахождения' in d:
        notes.append('меняет адрес')
    if 'ОГРНИП сменился' in d:
        notes.append('ИП перерегистрирован (новый ОГРНИП)')
    if 'косвенно' in d:
        notes.append('статус по косвенным признакам')
    if r['cur'] and not same_name(r['cur'], r['name']):
        notes.append(f'сейчас называется: {r["cur"]}')
    if r['recheck'] and r['via'] == 'поиск':
        notes.append('перепроверить по ссылке')
    return '; '.join(notes)


def edits(a, b):
    """Расстояние Левенштейна (сколько букв поправить, чтобы из a получить b)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def main_emails(emails, site='', limit=3):
    """Почты без опечаток: похожие адреса (до 2 букв разницы) — одна группа, из неё один адрес.

    В госзакупках адрес компании переписывают руками, и Checko собирает все
    варианты: office@…, ofice@…, officce@…. Верный — тот, от которого остальные
    отличаются меньше всего (центр группы); первыми идут самые большие группы:
    адрес, который писали чаще, скорее всего и есть рабочий. Ещё раньше — адреса
    на домене сайта компании: это её собственная почта.
    """
    dom = re.sub(r'^(https?://)?(www\.)?', '', (site or '').lower()).split('/')[0]
    own = lambda e: bool(dom) and (e.split('@')[-1] == dom or e.split('@')[-1].endswith('.' + dom))  # noqa: E731
    left = [e for e in emails.split('; ') if e]
    groups = []
    while left:
        seed = left.pop(0)
        group = [seed] + [e for e in left if edits(seed, e) <= 2]
        left = [e for e in left if e not in group]
        groups.append(min(group, key=lambda e: (sum(edits(e, o) for o in group), group.index(e))))
        groups[-1] = (groups[-1], len(group))
    groups.sort(key=lambda g: (not own(g[0]), -g[1]))
    best = [g[0] for g in groups[:limit]]
    return '; '.join(best), len(emails.split('; ')) - len(best) if emails else 0


VIA = {'Checko': 'ЕГРЮЛ (Checko)', 'поиск': 'поиск в интернете', '': '—'}
for r in recs:
    r['email_main'], hidden = main_emails(r['email'], r['site'])
    r['all_phones'] = phones_merged(r['phone'], r['phones'])
    r['what'] = what_happens(r)
    r['note'] = note_of(r)
    if hidden:
        r['note'] = '; '.join(x for x in (r['note'], f'ещё адресов: {hidden} — лист «Все данные»') if x)
    r['via_h'] = VIA.get(r['via'], r['via'])
    if r['via'] == 'Checko':
        r['why'] = 'в реестре по этому ИНН не найдена — проверить по ссылке'
    elif r['group'] == 'Не найдено':
        r['why'] = 'поиск статус не нашёл, через Checko ещё не проверялась — проверится при следующем запуске'
    else:
        r['why'] = 'не хватило лимита ключей — проверится при следующем запуске программы'

# ---------------------------------------------------------------- оформление
# Цвета: текст — чернила, статус — только полоской или заливкой рядом с подписью (никогда без неё).
INK, INK2 = '0B0B0B', '52514E'
STATUS = {'Действует': '0CA30C', 'Закрывается': 'FAB219', 'Не существует': 'D03B3B',
          'Не найдено': '8C8C8C', 'Не проверялась': '8C8C8C'}
F = Font(name='Arial', size=10, color=INK)
FS = Font(name='Arial', size=10, color=INK2)
FB = Font(name='Arial', size=10, bold=True, color=INK)
FL = Font(name='Arial', size=10, color='0563C1', underline='single')
FH = Font(name='Arial', size=10, bold=True, color='FFFFFF')
HFILL = PatternFill('solid', fgColor='1F2D3D')
BAND = PatternFill('solid', fgColor='F4F4F2')
thin = Side(style='thin', color='D9D9D6')
BRD = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical='top')
LINK = 'Открыть'
DATES = {'date', 'sro_date', 'gos_date'}
TEXT = {'inn', 'ogrn', 'sro_reg'}


def as_date(v):
    m = re.fullmatch(r'(\d{2})\.(\d{2})\.(\d{4})', str(v or '').strip())
    return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else v


def url_of(site):
    site = (site or '').split()[0] if site else ''
    return site if not site or site.startswith(('http://', 'https://')) else f'http://{site}'


def lines_for(value, width):
    """Сколько строк займёт текст в столбце такой ширины — с запасом: перенос идёт по словам."""
    if value in (None, '') or isinstance(value, (int, float, datetime)):
        return 1
    per = max(1, int(width * 0.95))
    return sum(max(1, -(-len(part) // per)) for part in str(value).split('\n'))


def table(ws, cols, items, colored=(), freeze='C2', tab=None, max_lines=6):
    """cols: (заголовок, ширина, поле | None — номер строки | 'LINK' — карточка по ИНН)."""
    ws.append([h for h, _, _ in cols])
    for c in ws[1]:
        c.font, c.fill, c.border = FH, HFILL, BRD
        c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
    for i, r in enumerate(items, 1):
        ws.append([i if k is None else LINK if k == 'LINK' else as_date(r[k]) if k in DATES else r[k]
                   for _, _, k in cols])
        row, lines = ws.max_row, 1
        for j, (_, w, k) in enumerate(cols, 1):
            c = ws.cell(row, j)
            c.font, c.alignment, c.border = F, WRAP, BRD
            if i % 2 == 0:
                c.fill = BAND
            if k == 'LINK':
                c.hyperlink, c.font = f'https://www.rusprofile.ru/search?query={r["inn"]}', FL
            elif k == 'site' and r['site']:
                c.hyperlink, c.font = url_of(r['site']), FL
            elif k in TEXT:
                c.number_format = '@'
            elif k in DATES and isinstance(c.value, datetime):
                c.number_format = 'DD.MM.YYYY'
                c.alignment = Alignment(vertical='top', horizontal='left')
            elif k in ('note', 'via_h', 'why', 'detail', 'source'):
                c.font = FS
            elif k == 'recheck' and r['recheck']:
                c.font = Font(name='Arial', size=10, bold=True, color='C00000')
            if k == 'group':
                c.font = FB
            if k in colored:
                c.fill = PatternFill('solid', fgColor=FILL[r['group']])
            lines = max(lines, lines_for(c.value, w))
        ws.row_dimensions[row].height = 13.5 * min(lines, max_lines) + 3
    for j, (_, w, _) in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = freeze
    ws.auto_filter.ref = f'A1:{get_column_letter(len(cols))}{max(ws.max_row, 2)}'
    ws.row_dimensions[1].height = 32
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.print_title_rows = '1:1'
    if tab:
        ws.sheet_properties.tabColor = tab


ALL = [  # полная таблица: Итог — B, Статус — C, Почта — E (на них стоят формулы «Сводки»)
    ('№', 6, None), ('Итог', 15, 'group'), ('Статус в ЕГРЮЛ / ЕГРИП', 24, 'status'),
    ('Дата события', 13, 'date'), ('Электронная почта', 32, 'email'),
    ('Телефоны (Checko)', 22, 'phones'), ('Сайт (Checko)', 20, 'site'),
    ('Наименование (из файла)', 38, 'name'), ('Текущее наименование', 26, 'cur'),
    ('ИНН', 13, 'inn'), ('ОГРН / ОГРНИП', 16, 'ogrn'), ('Телефон (из файла)', 20, 'phone'),
    ('Адрес (из файла)', 50, 'addr'), ('Руководитель (из файла)', 38, 'head'),
    ('Членство в СРО (по файлу)', 20, 'sro'), ('Рег. номер в реестре СРО', 12, 'sro_reg'),
    ('Дата вступления в СРО', 13, 'sro_date'), ('Решение СРО (по файлу)', 40, 'decision'),
    ('Взнос в КФ (по файлу)', 12, 'kf'), ('Дата гос. регистрации', 13, 'gos_date'),
    ('Полное наименование (из файла)', 50, 'full'), ('Где в исходных файлах', 20, 'where'),
    ('Откуда статус', 12, 'via'), ('Что сказано в источнике', 60, 'detail'), ('Источник', 45, 'source'),
    ('Перепроверить', 14, 'recheck'), ('Проверить самому', 12, 'LINK'),
]
ACTIVE = [
    ('№', 6, None), ('Компания', 36, 'name'), ('ИНН', 13, 'inn'), ('Электронная почта', 34, 'email_main'),
    ('Телефоны', 30, 'all_phones'), ('Сайт', 22, 'site'), ('Руководитель (по файлу)', 30, 'head'),
    ('Адрес (по файлу)', 44, 'addr'), ('Членство в СРО', 16, 'sro'), ('Примечание', 30, 'note'),
    ('Карточка', 10, 'LINK'),
]
EMAILS = [
    ('№', 6, None), ('Компания', 38, 'name'), ('ИНН', 13, 'inn'), ('Основная почта', 32, 'email1'),
    ('Другие адреса', 38, 'email_rest'), ('Телефоны', 30, 'all_phones'), ('Сайт', 24, 'site'),
    ('Карточка', 10, 'LINK'),
]
CLOSING = [
    ('№', 6, None), ('Компания', 36, 'name'), ('ИНН', 13, 'inn'), ('Что происходит', 34, 'what'),
    ('С какой даты', 12, 'date'), ('Электронная почта', 30, 'email_main'), ('Телефоны', 28, 'all_phones'),
    ('Руководитель (по файлу)', 30, 'head'), ('Карточка', 10, 'LINK'),
]
GONE = [
    ('№', 6, None), ('Компания', 38, 'name'), ('ИНН', 13, 'inn'), ('Как прекратила работу', 42, 'what'),
    ('Дата', 12, 'date'), ('Членство в СРО', 18, 'sro'), ('Карточка', 10, 'LINK'),
]
LEFT = [
    ('№', 6, None), ('Компания', 36, 'name'), ('ИНН', 13, 'inn'), ('Почему нет статуса', 40, 'why'),
    ('Электронная почта', 30, 'email_main'), ('Телефоны', 28, 'all_phones'), ('Карточка', 10, 'LINK'),
]
for r in recs:
    first, *rest = (r['email_main'].split('; ') if r['email_main'] else [''])
    r['email1'], r['email_rest'] = first, '; '.join(rest)
    if not r['via'] == 'Checko' and r['via']:
        r['note'] = '; '.join(x for x in (r['note'], 'статус по поиску в интернете') if x)

SIMPLE_STATUS = {'Действует': 'Действует', 'Банкротство': 'Банкрот', 'В процессе ликвидации': 'Закрывается',
                 'Предстоящее исключение': 'Закрывается'}
SIMPLE_FILL = {'Действует': 'E2F0D9', 'Банкрот': 'F8D7DA', 'Закрывается': 'FFF2CC', 'Не действует': 'E7E6E6',
               'Нет данных': 'FFFFFF'}


def simple_status(r):
    if r['group'] == 'Не существует':
        return 'Не действует'
    return SIMPLE_STATUS.get(r['status'], 'Нет данных')


def build_simple(path):
    """Один лист: статус, №, компания, ИНН, почта, телефон, сайт, руководитель, адрес, член СРО."""
    from openpyxl.comments import Comment
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.worksheet.datavalidation import DataValidation
    order = list(SIMPLE_FILL)
    items = sorted(recs, key=lambda r: (order.index(simple_status(r)), plain(r['name']) or r['name']))
    cols = [('Статус', 15, 'st'), ('№', 6, None), ('Компания', 40, 'name'), ('ИНН', 13, 'inn'),
            ('Электронная почта', 34, 'email_main'), ('Телефон', 28, 'all_phones'), ('Сайт', 24, 'site'),
            ('Руководитель', 34, 'head'), ('Адрес', 50, 'addr'), ('Член СРО', 14, 'member')]
    wb = Workbook()
    ws = wb.active
    ws.title = 'Компании'
    ws.sheet_view.showGridLines = False
    last = get_column_letter(len(cols))
    top, first = 3, 4                      # строка шапки и первая строка данных
    end = first + len(items) - 1
    ws.merge_cells(f'A1:{last}1')
    ws['A1'] = f'Строительные компании Ростовской области — {len(items)} компаний (реестр Союза «Строители Ростовской области»), октябрь 2026'
    ws['A1'].font = Font(name='Arial', size=14, bold=True, color=INK)
    ws['A1'].alignment = Alignment(vertical='center')
    ws.row_dimensions[1].height = 26
    ws.merge_cells(f'A2:{last}2')
    rng = f'$A${first}:$A${end}'
    ws['A2'] = ('="Действует — "&COUNTIF({0},"Действует")&"     Банкрот — "&COUNTIF({0},"Банкрот")'
                '&"     Закрывается — "&COUNTIF({0},"Закрывается")&"     Не действует — "&COUNTIF({0},"Не действует")'
                '&"     С почтой — "&COUNTIF($E${1}:$E${2},"?*")'
                '&"          Отбор и сортировка — стрелка в заголовке столбца (например, «Статус» → «Действует»)"'
                ).format(rng, first, end)
    ws['A2'].font = Font(name='Arial', size=10, bold=True, color=INK2)
    ws['A2'].alignment = Alignment(vertical='center')
    ws.row_dimensions[2].height = 22
    for j, (h, w, _) in enumerate(cols, 1):
        c = ws.cell(top, j, h)
        c.font, c.fill, c.border = FH, HFILL, BRD
        c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[top].height = 26
    ws.cell(top, 1).comment = Comment('Статус по реестру налоговой (ЕГРЮЛ/ЕГРИП) через Checko, октябрь 2026.\n'
                                      'Действует — работает. Банкрот — идёт банкротство. Закрывается — ликвидация '
                                      'или налоговая готовит исключение. Не действует — уже закрыта.', 'Claude')
    ws.cell(top, len(cols)).comment = Comment('По выгрузкам реестра Союза «Строители Ростовской области».', 'Claude')
    for i, r in enumerate(items, 1):
        row = top + i
        vals = {'st': simple_status(r)}
        for j, (_, w, k) in enumerate(cols, 1):
            c = ws.cell(row, j, i if k is None else vals.get(k, r.get(k, '')))
            c.font, c.border = F, BRD
            c.alignment = Alignment(wrap_text=True, vertical='top')
            if k == 'inn':
                c.number_format = '@'
            elif k == 'site' and r['site']:
                c.hyperlink, c.font = url_of(r['site']), FL
            elif k in ('st', 'member'):
                c.alignment = Alignment(horizontal='center', vertical='top')
            if k == 'st':
                c.font = FB
        lines = max(lines_for(ws.cell(row, j).value, w) for j, (_, w, _) in enumerate(cols, 1))
        ws.row_dimensions[row].height = 13.5 * min(lines, 5) + 3
    # статус — выбор из списка, цвет идёт за значением (меняется, если выбрать другой)
    dv = DataValidation(type='list', formula1='"Действует,Банкрот,Закрывается,Не действует"', allow_blank=True)
    dv.add(f'A{first}:A{end}')
    ws.add_data_validation(dv)
    for val, color in SIMPLE_FILL.items():
        if val != 'Нет данных':
            ws.conditional_formatting.add(f'A{first}:A{end}', CellIsRule(
                operator='equal', formula=[f'"{val}"'], fill=PatternFill('solid', fgColor=color)))
    dm = DataValidation(type='list', formula1='"Да,Нет,Приостановлено"', allow_blank=True)
    dm.add(f'{last}{first}:{last}{end}')
    ws.add_data_validation(dm)
    ws.freeze_panes = f'C{first}'
    ws.auto_filter.ref = f'A{top}:{last}{end}'
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.print_title_rows = f'{top}:{top}'
    wb.save(path)
    print('Простая таблица:', path, '|', dict(collections.Counter(simple_status(r) for r in recs)),
          '| с почтой:', sum(1 for r in recs if r['email_main']))


if SIMPLE:
    build_simple(OUT)
    sys.exit(0)

by = collections.defaultdict(list)
for r in recs:
    by[r['group']].append(r)
wb = Workbook()
sv = wb.active
sv.title = 'Сводка'
sv.sheet_properties.tabColor = '1F2D3D'
table(wb.create_sheet('Действующие'), ACTIVE, by['Действует'], tab=STATUS['Действует'])
table(wb.create_sheet('Почты'), EMAILS, [r for r in by['Действует'] if r['email1']], tab='2A78D6')
table(wb.create_sheet('Закрываются'), CLOSING,
      sorted(by['Закрывается'], key=lambda r: (r['what'], r['name'].lower())), tab=STATUS['Закрывается'])
GONE_ORDER = ['Ликвидирована', 'Ликвидирована после банкротства', 'Исключена налоговой', 'Реорганизована', 'ИП закрыт']


def gone_key(r):
    hits = [i for i, k in enumerate(GONE_ORDER) if r['what'].startswith(k)]
    kind = max(hits, key=lambda i: len(GONE_ORDER[i])) if hits else len(GONE_ORDER)   # самое длинное совпадение
    d = re.fullmatch(r'(\d{2})\.(\d{2})\.(\d{4})', r['date'] or '')
    return kind, -(int(d.group(3) + d.group(2) + d.group(1)) if d else 0), r['name'].lower()


table(wb.create_sheet('Не существуют'), GONE, sorted(by['Не существует'], key=gone_key), tab=STATUS['Не существует'])
left = by['Не найдено'] + by['Не проверялась']
if left:
    table(wb.create_sheet('Не проверены'), LEFT, left, tab=STATUS['Не найдено'])
wa = wb.create_sheet('Все данные')
table(wa, ALL, recs, colored=('group', 'status', 'date'), freeze='I2', tab='8C8C8C', max_lines=4)

# ---------------------------------------------------------------- «Сводка»: карточки и разбивка, формулы по «Все данные»
COL = {h: j for j, (h, _, _) in enumerate(ALL, 1)}
assert (COL['Итог'], COL['Статус в ЕГРЮЛ / ЕГРИП'], COL['Электронная почта']) == (2, 3, 5)
N = wa.max_row
A = f"'Все данные'!$B$2:$B${N}"
S = f"'Все данные'!$C$2:$C${N}"
E = f"'Все данные'!$E$2:$E${N}"
for col in 'ABCDEFGH':
    sv.column_dimensions[col].width = 15
sv.sheet_view.showGridLines = False


def merged(rng, value, font, fill=None, align=None, height=None):
    sv.merge_cells(rng)
    c = sv[rng.split(':')[0]]
    c.value, c.font = value, font
    c.alignment = align or Alignment(wrap_text=True, vertical='center')
    if fill:
        for row in sv[rng]:
            for x in row:
                x.fill = fill
    if height:
        sv.row_dimensions[c.row].height = height
    return c


checked = sum(1 for r in recs if r['via'] == 'Checko' and r['group'] not in ('Не найдено', 'Не проверялась'))
merged('A1:H1', 'Строительные компании Ростовской области — итог проверки', Font(name='Arial', size=16, bold=True, color=INK), height=28)
merged('A2:H2', f'{len(recs)} компаний из реестра Союза «Строители Ростовской области» (два файла выгрузки). '
                f'Статус по реестру налоговой (ЕГРЮЛ/ЕГРИП) через Checko — у {checked} из {len(recs)}, проверка — октябрь 2026.',
       Font(name='Arial', size=10, color=INK2), height=32)
sv.row_dimensions[3].height = 10

TILE_BG = PatternFill('solid', fgColor='F7F7F5')
tiles = [
    ('A', 'B', 'Действуют', STATUS['Действует'], f'=COUNTIF({A},"Действует")',
     f'=TEXT(COUNTIF({A},"Действует")/COUNTA({A}),"0%")&" от всех"'),
    ('C', 'D', 'Закрываются', STATUS['Закрывается'], f'=COUNTIF({A},"Закрывается")',
     '="ликвидация, банкротство"'),
    ('E', 'F', 'Не существуют', STATUS['Не существует'], f'=COUNTIF({A},"Не существует")',
     '="уже закрыты"'),
    ('G', 'H', 'Действующих с почтой', '2A78D6', f'=COUNTIFS({A},"Действует",{E},"?*")',
     '="адреса — лист «Почты»"'),
]
for c1, c2, label, color, value, sub in tiles:
    merged(f'{c1}4:{c2}4', None, F, fill=PatternFill('solid', fgColor=color))
    merged(f'{c1}5:{c2}5', label, Font(name='Arial', size=10, bold=True, color=INK2), fill=TILE_BG,
           align=Alignment(horizontal='left', vertical='center', indent=1))
    merged(f'{c1}6:{c2}6', value, Font(name='Arial', size=26, bold=True, color=INK), fill=TILE_BG,
           align=Alignment(horizontal='left', vertical='center', indent=1))
    merged(f'{c1}7:{c2}7', sub, Font(name='Arial', size=9, color=INK2), fill=TILE_BG,
           align=Alignment(horizontal='left', vertical='center', indent=1))
sv.row_dimensions[4].height = 5
sv.row_dimensions[5].height = 18
sv.row_dimensions[6].height = 38
sv.row_dimensions[7].height = 16
for col in 'BDF':   # белый зазор между карточками
    for row in range(4, 8):
        sv[f'{col}{row}'].border = Border(right=Side(style='thick', color='FFFFFF'))

MEAN = {
    'Действует': 'Работает',
    'В процессе ликвидации': 'Ликвидируется: решение принято, компания ещё в реестре',
    'Банкротство': 'Идёт банкротство: наблюдение или конкурсное производство',
    'Предстоящее исключение': 'Налоговая объявила, что исключит компанию из реестра',
    'Ликвидирована': 'Закрыта: ликвидирована (в том числе после банкротства)',
    'Исключена ФНС': 'Закрыта: исключена налоговой — недостоверные сведения или не работала',
    'Реорганизована': 'Закрыта: присоединена к другой компании или преобразована',
    'ИП прекратил деятельность': 'ИП закрыт',
    'Не установлено': 'Статус не найден',
    'Ещё не проверялась': 'Ещё не проверена',
}
r = 9
merged(f'A{r}:H{r}', 'Подробно по статусам', Font(name='Arial', size=12, bold=True, color=INK), height=22)
r += 1
for rng, h in ((f'A{r}:B{r}', 'Статус в реестре'), (f'C{r}:F{r}', 'Что это значит'), (f'G{r}:G{r}', 'Компаний'),
               (f'H{r}:H{r}', 'С почтой')):
    c = merged(rng, h, FH, fill=HFILL, align=Alignment(horizontal='center', vertical='center', wrap_text=True))
sv.row_dimensions[r].height = 22
present = collections.Counter(x['status'] for x in recs)
for st in GROUP:
    if not present.get(st) and st not in ('Действует',):
        continue
    r += 1
    merged(f'A{r}:B{r}', st, FB, fill=PatternFill('solid', fgColor=FILL[GROUP[st]]),
           align=Alignment(vertical='center', indent=1))
    merged(f'C{r}:F{r}', MEAN[st], F, align=Alignment(vertical='center', wrap_text=True, indent=1))
    meaning_lines = lines_for(MEAN[st], 4 * 15 - 4)
    sv[f'G{r}'] = f'=COUNTIF({S},A{r})'
    sv[f'H{r}'] = f'=COUNTIFS({S},A{r},{E},"?*")'
    for col in 'GH':
        sv[f'{col}{r}'].font = F
        sv[f'{col}{r}'].alignment = Alignment(horizontal='center', vertical='center')
    for col in 'ABCDEFGH':
        sv[f'{col}{r}'].border = BRD
    sv.row_dimensions[r].height = max(20, 14 * meaning_lines + 6)
r += 1
merged(f'A{r}:F{r}', 'Всего', FB, align=Alignment(horizontal='right', vertical='center', indent=1))
sv[f'G{r}'] = f'=SUM(G11:G{r - 1})'
sv[f'H{r}'] = f'=SUM(H11:H{r - 1})'
for col in 'GH':
    sv[f'{col}{r}'].font = FB
    sv[f'{col}{r}'].alignment = Alignment(horizontal='center', vertical='center')
for col in 'ABCDEFGH':
    sv[f'{col}{r}'].border = BRD

r += 2
merged(f'A{r}:H{r}', 'Как пользоваться', Font(name='Arial', size=12, bold=True, color=INK), height=22)
notes = [
    '«Действующие» — работающие компании: почта, телефоны, сайт, руководитель, адрес. Сверху — те, у кого есть почта.',
    '«Почты» — только действующие компании с почтой: основной адрес и другие. Удобно для рассылки.',
    '«Закрываются» и «Не существуют» — что произошло с компанией и когда.',
    '«Все данные» — все столбцы обоих файлов реестра СРО и полный список найденных адресов.',
    'Телефоны — номер из реестра СРО и номера из Checko без повторов. Почты-опечатки из госзакупок '
    '(ofice@, officce@…) с рабочих листов убраны, на листе «Все данные» они остались.',
    'Руководитель и адрес — из файлов реестра СРО, могли смениться. «Открыть» — карточка компании по ИНН.',
    'Членство в СРО и работа компании — разные вещи: многие вышли из Союза, но работают.',
]
for t in notes:
    r += 1
    merged(f'A{r}:H{r}', f'•  {t}', F, align=Alignment(wrap_text=True, vertical='top'),
           height=14 * lines_for(t, 8 * 15 - 6) + 4)
sv.page_setup.orientation = 'portrait'
sv.page_setup.fitToWidth, sv.page_setup.fitToHeight = 1, 0
sv.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
wb.active = 0

wb.save(OUT)
by_via = collections.Counter(x['via'] for x in recs if x['group'] != 'Не проверялась')
print('Таблица:', OUT, '| компаний:', len(recs), '| с почтой:', sum(1 for x in recs if x['email']))
print(' ', dict(collections.Counter(x['group'] for x in recs)), '| статус из Checko:', by_via.get('Checko', 0),
      '| из поиска:', by_via.get('поиск', 0))
