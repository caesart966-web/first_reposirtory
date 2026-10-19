"""Сборка комплекта И05.09.26-ОВ: пересборка всех листов, единый PDF с оглавлением, DXF для DWG-робота.

python3 assemble_rd.py [--no-build] [--repo /home/user/first_reposirtory]
"""
import os
import shutil
import subprocess
import sys

import pymupdf as fitz

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rdbase import SHEET_LIST  # noqa: E402

OUT = os.path.join(HERE, 'out')
# номер листа -> базовое имя выхода скрипта
SHEETS = {1: 'ov_od1', 2: 'ov_od2', 3: 'ov_heat1', 4: 'ov_ufh1', 5: 'ov_heat2', 6: 'ov_scheme',
          7: 'ov_boiler_plan', 8: 'ov_boiler_scheme', 9: 'ov_vent1', 10: 'ov_vent2', 11: 'ov_vent_schemes',
          12: 'ov_bath', 13: 'ov_bath_scheme', 14: 'ov_site', 15: 'ov_nodes'}
# порядок пересборки (зависимости: heat1 -> boiler_scheme -> scheme, nodes; vent1 -> vent2, schemes; bath -> bath_scheme)
BUILD = ['ov_heat2', 'ov_heat1', 'ov_ufh1', 'ov_boiler_scheme', 'ov_scheme', 'ov_boiler_plan', 'ov_vent1',
         'ov_vent2', 'ov_vent_schemes', 'ov_bath', 'ov_bath_scheme', 'ov_site', 'ov_nodes', 'ov_od',
         'tz_ar', 'tz_eom', 'tz_vk', 'tz_gsv']
# задания смежникам: код -> (скрипт, базовые имена выходов)
TZ = {1: ('tz_ar', 'Задание АР и КР (отверстия, шахты, ниши, приямки)'), 2: ('tz_eom', 'Задание ЭОМ'),
      3: ('tz_vk', 'Задание ВК'), 4: ('tz_gsv', 'Задание ГСВ')}


def build():
    for name in BUILD:
        script = os.path.join(HERE, 'sheets', name + '.py')
        if not os.path.exists(script):
            print(f'{name}: нет скрипта — пропуск')
            continue
        r = subprocess.run([sys.executable, script], cwd=HERE, capture_output=True, text=True)
        tail = [l for l in (r.stdout + r.stderr).splitlines() if 'warning' not in l.lower()][-2:]
        print(f'{name}: {"OK" if r.returncode == 0 else "ОШИБКА"} {" | ".join(tail)[:200]}')
        if r.returncode:
            raise SystemExit(r.stderr[-3000:])
    r = subprocess.run([sys.executable, os.path.join(HERE, 'spec', 'make_spec.py')], cwd=HERE, capture_output=True,
                       text=True)
    print('spec:', 'OK' if r.returncode == 0 else 'ОШИБКА ' + r.stderr[-1500:])


def pdf_of(base):
    p = os.path.join(OUT, base + '_Лист.pdf')
    if not os.path.exists(p):
        raise SystemExit(f'нет {p}')
    return p


def volume(path):
    doc = fitz.open()
    toc = []
    for no in sorted(SHEETS):
        src = fitz.open(pdf_of(SHEETS[no]))
        toc.append([1, f'Лист {no}. {SHEET_LIST[no]}', len(doc) + 1])
        doc.insert_pdf(src)
    doc.set_toc(toc)
    doc.set_metadata({'title': 'И05.09.26-ОВ. Отопление, вентиляция и кондиционирование. Рабочая документация',
                      'subject': 'Двухэтажный индивидуальный жилой дом с баней, Московская область'})
    doc.save(path, garbage=3, deflate=True)
    return len(doc)


def main():
    if '--no-build' not in sys.argv:
        build()
    repo = sys.argv[sys.argv.index('--repo') + 1] if '--repo' in sys.argv else None
    rel = os.path.join(HERE, 'release')
    os.makedirs(rel, exist_ok=True)
    vol = os.path.join(rel, 'И05.09.26-ОВ РД ОВиК (дом и баня).pdf')
    n = volume(vol)
    print('том:', vol, n, 'листов', os.path.getsize(vol))
    dxf_dir = os.path.join(rel, 'dxf')
    os.makedirs(dxf_dir, exist_ok=True)
    for no, base in SHEETS.items():
        shutil.copy(os.path.join(OUT, base + '.dxf'), os.path.join(dxf_dir, f'I05-09-26-OV-{no:02d}.dxf'))
    tz_pdf = []
    for n, (base, title) in TZ.items():
        dxf, pdf = os.path.join(OUT, base + '.dxf'), os.path.join(OUT, base + '.pdf')
        if os.path.exists(dxf) and os.path.exists(pdf):
            shutil.copy(dxf, os.path.join(dxf_dir, f'I05-09-26-OV-TZ{n}.dxf'))
            dst = os.path.join(rel, f'И05.09.26-ОВ.ТЗ-{n} {title}.pdf')
            shutil.copy(pdf, dst)
            tz_pdf.append(dst)
        else:
            print('нет задания', base)
    for ext in ('pdf', 'xlsx'):
        p = os.path.join(OUT, f'И05.09.26-ОВ.СО Спецификация.{ext}')
        if os.path.exists(p):
            shutil.copy(p, os.path.join(rel, f'И05.09.26-ОВ.СО Спецификация оборудования, изделий и материалов.{ext}'))
    if repo:
        d = os.path.join(repo, 'cad', 'ovk-i05-09-26', 'dxf')
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(dxf_dir):
            shutil.copy(os.path.join(dxf_dir, f), os.path.join(d, f))
        r = os.path.join(repo, 'ovk-dom-banya', 'release-rd')
        os.makedirs(r, exist_ok=True)
        for f in os.listdir(rel):
            if f.endswith(('.pdf', '.xlsx')):
                shutil.copy(os.path.join(rel, f), r)
        print('в репозиторий:', d, r)


if __name__ == '__main__':
    main()
