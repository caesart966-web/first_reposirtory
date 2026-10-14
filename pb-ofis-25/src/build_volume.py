"""Сборка тома ПБ-25 целиком: листы 1–6, текстовая часть, графическая часть, единый PDF с закладками,
DXF графической части (zip) и ответы на замечания (DOCX).
Запуск: python3 build_volume.py <pb25.dxf> <лист44.pdf> [--skip-graphics]
  pb25.dxf, лист44.pdf — из folder/ОПР-01_24_2026-ПБ-25.zip и «Схема 1» (план внутриплощадочных дорог)."""
import os, sys, zipfile
import pymupdf
import head, build_tch, situation, answers
import pbdoc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
VOLUME = os.path.join(OUT, 'ОПР-01_24_2026-ПБ-25.pdf')
GCH = [('44', 'Графический лист 44. План внутриплощадочных дорог'),
       ('44.1', 'Графический лист 44.1. Ситуационный план'),
       ('45', 'Графический лист 45. Структурная схема СПС, АУГПТ и УПА ВРУ'),
       ('46', 'Графический лист 46. Структурная схема СОУЭ'),
       ('47', 'Графический лист 47. План 2-го этажа. Пути эвакуации, огнетушители, зона МГН'),
       ('48', 'Графический лист 48. План 1-го этажа. Пути эвакуации, огнетушители'),
       ('48.1', 'Графический лист 48.1. Конференц-зал №36. Схема расстановки мест'),
       ('48.2', 'Графический лист 48.2. Серверная №31. План АУГПТ')]


def main(dxf, gp_pdf, skip_graphics=False):
    os.makedirs(os.path.join(OUT, 'gch'), exist_ok=True)
    tmp = os.path.join(OUT, '_tch.pdf')
    _, last = build_tch.build(7, 99, tmp)
    n_tch = last - 6
    first_g = last + 1
    total = last + len(GCH)
    tch_path, last2 = build_tch.build(7, total, os.path.join(OUT, '_tch.pdf'))
    assert last2 == last
    marks = dict(pbdoc.build.marks)
    gnums = {s: first_g + k for k, (s, _) in enumerate(GCH)}
    print(f'текстовая часть: листы 7–{last}; графическая: {first_g}–{total}; всего {total}')

    import json
    nums_file = os.path.join(OUT, 'gch', 'nums.json')
    if skip_graphics:
        old = json.load(open(nums_file, encoding='utf-8'))
        if old != {**gnums, 'total': total}:
            raise SystemExit(f'номера листов изменились ({old} → {gnums}, всего {total}) – нужна полная сборка')
    if not skip_graphics:
        import graphics
        doc, nums = graphics.build(dxf, first_g, total)
        assert nums == gnums, (nums, gnums)
        graphics.export(doc)
        dxf_out = os.path.join(OUT, 'ПБ-25-ГЧ.dxf')
        doc.saveas(dxf_out)
        with zipfile.ZipFile(os.path.join(OUT, 'ОПР-01_24_2026-ПБ-25-ГЧ_dxf.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(dxf_out, 'ОПР-01_24_2026-ПБ-25-ГЧ.dxf')
        os.remove(dxf_out)
        json.dump({**gnums, 'total': total}, open(nums_file, 'w', encoding='utf-8'))
    situation.build(gp_pdf, gnums['44.1'], total)

    refs = [['ОПР-01/24/2026-ПБ-25-С', 'Содержание тома', 'Лист 03'],
            ['ОПР-01/24/2026-ПБ-25-СП', 'Состав проектной документации', 'Лист 04'],
            ['ОПР-01/24/2026-ПБ-25-ТЧ', 'Текстовая часть. Мероприятия по обеспечению пожарной безопасности',
             f'Листы 05–{last:02d}']]
    for k, (s, name) in enumerate(GCH):
        refs.append([f'ОПР-01/24/2026-ПБ-25-ГЧ{k + 1}', name, f'Лист {gnums[s]:02d}'])
    head_path = os.path.join(OUT, '_head.pdf')
    head.build(head_path, total, refs)

    vol = pymupdf.open()
    toc = []
    hd = pymupdf.open(head_path)
    vol.insert_pdf(hd)
    toc += [[1, 'Обложка', 1], [1, 'Титульный лист', 2], [1, 'Содержание тома', 3],
            [1, 'Состав проектной документации', 4], [1, 'Справка ГИПа', 5], [1, 'Принятые сокращения', 6]]
    tch = pymupdf.open(tch_path)
    vol.insert_pdf(tch)
    import re
    for title, sheet in marks.items():
        m = re.match(r'^(\d+(?:\.\d+)*)\.? ', title)
        level = 1 if title.startswith('Приложение') else (min(len(m.group(1).split('.')), 3) if m else 0)
        if level:
            toc.append([level, title, sheet])
    for s, name in GCH:
        page_no = len(vol) + 1
        vol.insert_pdf(pymupdf.open(os.path.join(OUT, 'gch', f'{s}.pdf')))
        toc.append([1, name, page_no])
    vol.set_toc(toc)
    vol.set_metadata({'title': 'ОПР-01/24/2026-ПБ-25. Мероприятия по обеспечению пожарной безопасности',
                      'author': 'ООО "Технология"', 'creator': '', 'producer': ''})
    vol.save(VOLUME, garbage=3, deflate=True)
    assert len(vol) == total, (len(vol), total)
    for p in (head_path, tch_path):
        os.remove(p)
    answers.build(os.path.join(OUT, 'ОПР-01_24_2026-ПБ-25_ответы_на_замечания.docx'), marks, gnums)
    print(VOLUME, len(vol), 'листов')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], '--skip-graphics' in sys.argv)
