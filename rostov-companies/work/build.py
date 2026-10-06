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

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors='replace')
    except Exception:  # noqa: BLE001
        pass

OUT = sys.argv[1] if len(sys.argv) > 1 else 'result.xlsx'


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
    extra = dict(  # остальные столбцы исходных файлов — переносятся как есть
        full=x.get('Полное наименование', ''), sro_reg=x.get('Регистрационный номер в реестре СРО', ''),
        sro_date=x.get('Дата регистрации в реестре СРО', ''), gos_date=x.get('Дата государственной регистрации', ''),
        kf=x.get('КФ', ''), decision=x.get('Решение', ''), file_email=x.get('электронная почта', ''),
    )
    if inn in rows:  # компания есть в обоих файлах — различающиеся значения через «; »
        rows[inn]['where'] += '; ' + where
        rows[inn]['sro'] += '; ' + m
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
        sro=m, where=where, **extra,
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
F = Font(name='Arial', size=10)
FB = Font(name='Arial', size=10, bold=True)
FL = Font(name='Arial', size=10, color='0563C1', underline='single')
FH = Font(name='Arial', size=10, bold=True, color='FFFFFF')
HFILL = PatternFill('solid', fgColor='404040')
thin = Side(style='thin', color='BFBFBF')
BRD = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical='top')
LINK = 'Открыть'


def table(ws, cols, items, colored=None, freeze='C2'):
    """cols: (заголовок, ширина, поле | None для №, 'LINK' для ссылки на карточку)."""
    ws.append([h for h, _, _ in cols])
    for c in ws[1]:
        c.font, c.fill, c.border = FH, HFILL, BRD
        c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
    for i, r in enumerate(items, 1):
        ws.append([i if k is None else (LINK if k == 'LINK' else r[k]) for _, _, k in cols])
        row = ws.max_row
        for j, (h, _, k) in enumerate(cols, 1):
            c = ws.cell(row, j)
            c.font, c.alignment, c.border = F, WRAP, BRD
            if k == 'LINK':
                c.hyperlink = f'https://www.rusprofile.ru/search?query={r["inn"]}'
                c.font = FL
            elif k in ('inn', 'ogrn'):
                c.number_format = '@'
            elif k == 'recheck' and r['recheck']:
                c.font = Font(name='Arial', size=10, bold=True, color='C00000')
        if colored:
            for k in colored:
                j = next(j for j, (_, _, kk) in enumerate(cols, 1) if kk == k)
                ws.cell(row, j).fill = PatternFill('solid', fgColor=FILL[r['group']])
    for j, (_, w, _) in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = freeze
    ws.auto_filter.ref = f'A1:{get_column_letter(len(cols))}{max(ws.max_row, 2)}'
    ws.row_dimensions[1].height = 30


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
    ('Телефоны', 30, 'all_phones'), ('Сайт', 22, 'site'), ('Руководитель (по файлу)', 32, 'head'),
    ('Адрес (по файлу)', 46, 'addr'), ('Членство в СРО', 16, 'sro'), ('Статус проверен', 16, 'via_h'),
    ('Примечание', 30, 'note'), ('Карточка', 10, 'LINK'),
]
CLOSING = [
    ('№', 6, None), ('Компания', 36, 'name'), ('ИНН', 13, 'inn'), ('Что происходит', 34, 'what'),
    ('С какой даты', 12, 'date'), ('Электронная почта', 30, 'email_main'), ('Телефоны', 28, 'all_phones'),
    ('Руководитель (по файлу)', 30, 'head'), ('Статус проверен', 16, 'via_h'), ('Карточка', 10, 'LINK'),
]
GONE = [
    ('№', 6, None), ('Компания', 36, 'name'), ('ИНН', 13, 'inn'), ('Как прекратила работу', 40, 'what'),
    ('Дата', 12, 'date'), ('Членство в СРО', 16, 'sro'), ('Статус проверен', 16, 'via_h'), ('Карточка', 10, 'LINK'),
]
LEFT = [
    ('№', 6, None), ('Компания', 36, 'name'), ('ИНН', 13, 'inn'), ('Почему нет статуса', 40, 'why'),
    ('Электронная почта', 30, 'email_main'), ('Телефоны', 28, 'all_phones'), ('Карточка', 10, 'LINK'),
]

wb = Workbook()
sv = wb.active
sv.title = 'Сводка'
by = collections.defaultdict(list)
for r in recs:
    by[r['group']].append(r)
table(wb.create_sheet('Действующие'), ACTIVE, by['Действует'])
table(wb.create_sheet('Закрываются'), CLOSING, by['Закрывается'])
table(wb.create_sheet('Не существуют'), GONE, sorted(by['Не существует'], key=lambda r: (r['what'], r['name'].lower())))
table(wb.create_sheet('Не проверены'), LEFT, by['Не найдено'] + by['Не проверялась'])
wa = wb.create_sheet('Все данные')
table(wa, ALL, recs, colored=('group', 'status', 'date'), freeze='I2')

# ---------------------------------------------------------------- «Сводка» — формулы по «Все данные»
COL = {h: j for j, (h, _, _) in enumerate(ALL, 1)}
assert (COL['Итог'], COL['Статус в ЕГРЮЛ / ЕГРИП'], COL['Электронная почта']) == (2, 3, 5)
N = wa.max_row
A = f"'Все данные'!$B$2:$B${N}"
S = f"'Все данные'!$C$2:$C${N}"
E = f"'Все данные'!$E$2:$E${N}"
V = f"'Все данные'!${get_column_letter(COL['Откуда статус'])}$2:${get_column_letter(COL['Откуда статус'])}${N}"

sv['A1'] = 'Строительные компании Ростовской области: работают ли и как с ними связаться'
sv['A1'].font = Font(name='Arial', size=14, bold=True)
sv['A2'] = (f'{len(recs)} компаний из двух выгрузок реестра Союза «Строители Ростовской области». '
            'Статус — по реестру налоговой (ЕГРЮЛ/ЕГРИП) через Checko, у остальных — по поиску в интернете. '
            'Проверка — октябрь 2026.')
sv['A2'].font = F
sv['A2'].alignment = WRAP
sv.merge_cells('A2:E2')
sv.row_dimensions[2].height = 44

for i, h in enumerate(['Итог', 'Что это значит', 'Компаний', 'Из них с почтой', 'Доля'], 1):
    c = sv.cell(4, i, h)
    c.font, c.fill, c.border, c.alignment = FH, HFILL, BRD, WRAP
MEAN = {
    'Действует': 'Работает. Список с почтами и телефонами — лист «Действующие».',
    'Закрывается': 'Ещё в реестре, но ликвидируется, банкротится или налоговая готовит исключение — лист «Закрываются».',
    'Не существует': 'Уже закрыта: ликвидирована, исключена налоговой, присоединена к другой, ИП закрыт — лист «Не существуют».',
    'Не найдено': 'Статус пока не нашёлся — лист «Не проверены». Проверятся через Checko при следующем запуске.',
    'Не проверялась': 'Не хватило лимита Checko — проверится при следующем запуске программы.',
}
r0 = 5
rt = r0 + len(ORDER)
for k, g in enumerate(ORDER):
    r = r0 + k
    sv.cell(r, 1, g).font = FB
    sv.cell(r, 1).fill = PatternFill('solid', fgColor=FILL[g])
    sv.cell(r, 2, MEAN[g])
    sv.cell(r, 3, f'=COUNTIF({A},A{r})')
    sv.cell(r, 4, f'=COUNTIFS({A},A{r},{E},"?*")')
    sv.cell(r, 5, f'=IF($C${rt}=0,0,C{r}/$C${rt})')
    sv.cell(r, 5).number_format = '0%'
    for col in range(1, 6):
        c = sv.cell(r, col)
        c.border, c.alignment = BRD, WRAP
        if col > 1:
            c.font = F
    sv.row_dimensions[r].height = 30
sv.cell(rt, 1, 'Всего').font = FB
for col, f in ((3, f'=SUM(C{r0}:C{rt - 1})'), (4, f'=SUM(D{r0}:D{rt - 1})'), (5, f'=IF(C{rt}=0,0,C{rt}/C{rt})')):
    sv.cell(rt, col, f).font = FB
sv.cell(rt, 5).number_format = '0%'
for col in range(1, 6):
    sv.cell(rt, col).border = BRD

rv = rt + 2
sv.cell(rv, 1, 'Откуда статус').font = Font(name='Arial', size=11, bold=True)
for k, (key, label) in enumerate((('Checko', 'По реестру налоговой (Checko) — надёжно'),
                                  ('поиск', 'По поиску в интернете — стоит перепроверить по ссылке'))):
    r = rv + 1 + k
    sv.cell(r, 1, key).font = F
    sv.cell(r, 2, label).font = F
    sv.cell(r, 3, f'=COUNTIF({V},A{r})').font = F
    for col in range(1, 4):
        sv.cell(r, col).border = BRD

rd = rv + 4
sv.cell(rd, 1, 'Подробно по статусам').font = Font(name='Arial', size=11, bold=True)
for i, h in enumerate(['Статус в реестре', 'Итог', 'Компаний', 'Из них с почтой'], 1):
    c = sv.cell(rd + 1, i, h)
    c.font, c.fill, c.border = FH, HFILL, BRD
for k, st in enumerate(GROUP):
    r = rd + 2 + k
    sv.cell(r, 1, st)
    sv.cell(r, 2, GROUP[st]).fill = PatternFill('solid', fgColor=FILL[GROUP[st]])
    sv.cell(r, 3, f'=COUNTIF({S},A{r})')
    sv.cell(r, 4, f'=COUNTIFS({S},A{r},{E},"?*")')
    for col in range(1, 5):
        sv.cell(r, col).border = BRD
        sv.cell(r, col).font = F

rn = rd + 2 + len(GROUP) + 1
notes = [
    'Как пользоваться:',
    '• Для связи — лист «Действующие»: сверху компании с почтой. В «Телефонах» — номер из реестра СРО и номера из Checko, без повторов.',
    '• Членство в СРО и работа компании — разные вещи: многие вышли из Союза, но работают.',
    '• Руководитель и адрес — из файлов реестра, могли смениться. «Карточка» открывает компанию по ИНН на Rusprofile.',
    '• Почта и телефоны — из ЕГРЮЛ, госзакупок и справочников. Перед рассылкой проверьте выборочно: адреса меняются.',
    '• Все столбцы обоих файлов (номер и дата вступления в СРО, решение, взнос в КФ и др.) — на листе «Все данные».',
]
for k, t in enumerate(notes):
    c = sv.cell(rn + k, 1, t)
    c.font = FB if k == 0 else F
    sv.merge_cells(start_row=rn + k, start_column=1, end_row=rn + k, end_column=5)
    c.alignment = WRAP
    sv.row_dimensions[rn + k].height = 30 if k else 16
for col, w in zip('ABCDE', [24, 74, 12, 15, 9]):
    sv.column_dimensions[col].width = w

wb.save(OUT)
by_via = collections.Counter(r['via'] for r in recs if r['group'] != 'Не проверялась')
print('Таблица:', OUT, '| компаний:', len(recs), '| с почтой:', sum(1 for r in recs if r['email']))
print(' ', dict(collections.Counter(r['group'] for r in recs)), '| статус из Checko:', by_via.get('Checko', 0),
      '| из поиска:', by_via.get('поиск', 0))
