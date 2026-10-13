"""Том ПТ одним PDF (проверяющий генпроектировщика принимает раздел только единым томом):
обложка, титульный лист, содержание тома (…ПТ-С), пояснительная записка, основной комплект, прилагаемые документы.
Запускать последним, после build_all, docs, docs_rr, docs_od. Задания смежникам (ПТ.ЗД1, ПТ.ЗД2) в том не входят —
они выдаются разделам КР и ВК отдельно."""
import glob, os
import pymupdf as fitz
from docs import Doc, OUT, SHIFR
from meta import clean_pdf
from build_all import SHEETS
from sh_general import ATT_DOCS
import titles

S = SHIFR.replace('/', '_')
GRAPH = os.path.join(OUT, f'{S}_графическая_часть.pdf')
HEAD = os.path.join(OUT, f'{S}-С_содержание_тома.pdf')
VOLUME = os.path.join(OUT, f'{S}.pdf')


def doc_file(code):
    f = glob.glob(os.path.join(OUT, f'{S}.{code}_*.pdf'))
    if len(f) != 1:
        raise SystemExit(f'нет файла {S}.{code}_*.pdf (или их несколько): {f}')
    return f[0]


def parts():
    """[(обозначение, наименование, файл)] в порядке тома: записка, листы, прилагаемые документы."""
    att = dict(ATT_DOCS)
    out = [(SHIFR + '.ОД', att[SHIFR + '.ОД'], doc_file('ОД')), (SHIFR, 'Основной комплект рабочих чертежей', GRAPH)]
    out += [(code, name, doc_file(code.rsplit('.', 1)[1])) for code, name in ATT_DOCS if not code.endswith('.ОД')]
    return out


def build_head(n_head):
    """Обложка, титул, содержание. n_head — сколько страниц занимает содержание (для номеров страниц)."""
    d = Doc(HEAD, SHIFR + '-С', 'Содержание тома', pagesize='A4')
    d.pages_total = n_head
    titles.page(d.c, d.W, d.H, signatures=False)
    titles.page(d.c, d.W, d.H, signatures=True)
    p = 3 + n_head                       # 1 — обложка, 2 — титул, затем содержание
    rows = [[SHIFR + '-С', 'Содержание тома', 'стр. 3']]
    for code, name, path in parts():
        n = fitz.open(path).page_count
        rows.append([code, name, f'стр. {p}'])
        if path == GRAPH:
            if n != len(SHEETS):
                raise SystemExit(f'в графической части {n} стр., листов {len(SHEETS)}')
            rows += [['', f'Лист {no}. {name}', f'стр. {p + i}'] for i, (no, name, *_) in enumerate(SHEETS)]
        p += n
    d.table([('Обозначение', 60, 'L'), ('Наименование', 100, 'L'), ('Примечание', 25, 'C')], rows,
            header_h=10, font=8, min_h=7)
    d.save()
    return d.page, rows


def main():
    n_head, _ = build_head(1)
    if n_head != 1:
        n_head, _ = build_head(n_head)
    vol = fitz.open()
    toc = []
    for path, title in [(HEAD, None)] + [(p, f'{c}. {n}') for c, n, p in parts()]:
        start = vol.page_count + 1
        src = fitz.open(path)
        vol.insert_pdf(src)
        if title is None:
            toc += [[1, 'Обложка', 1], [1, 'Титульный лист', 2], [1, f'{SHIFR}-С. Содержание тома', 3]]
        else:
            toc.append([1, title, start])
            if path == GRAPH:
                toc += [[2, f'Лист {no}. {name}', start + i] for i, (no, name, *_) in enumerate(SHEETS)]
    vol.set_toc(toc)
    vol.save(VOLUME, garbage=3, deflate=True)
    clean_pdf(VOLUME, f'{SHIFR}. Пожаротушение')
    print('том:', fitz.open(VOLUME).page_count, 'стр.,', round(os.path.getsize(VOLUME) / 2**20, 1), 'МБ')


if __name__ == '__main__':
    main()
