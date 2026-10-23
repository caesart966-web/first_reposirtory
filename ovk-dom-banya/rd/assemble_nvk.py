"""Сборка раздела И05.09.26-НВК (наружные сети водопровода и канализации с ливнёвкой и дренажом): модель, расчёты
П1–П4, листы 1–8, НВК.СО, ВОР, том PDF, DXF для перевода в DWG.

python3 assemble_nvk.py [--no-build] [--repo /home/user/first_reposirtory]
"""
import os
import shutil
import subprocess
import sys

import pymupdf as fitz

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nvk_draw import NVK_LIST  # noqa: E402

OUT = os.path.join(HERE, 'out')
NO = os.path.join(OUT, 'nvk')
SHEETS = {1: 'nvk_od_1', 2: 'nvk_od_2', 3: 'nvk_plan', 4: 'nvk_prof_4', 5: 'nvk_prof_5', 6: 'nvk_prof_6',
          7: 'nvk_prof_7', 8: 'nvk_nodes'}
BUILD = [('nvk_model.py', []), ('nvk_calc.py', []), ('spec/make_calc_nvk.py', []), ('sheets/nvk_plan.py', []),
         ('sheets/nvk_prof.py', ['4']), ('sheets/nvk_prof.py', ['5']), ('sheets/nvk_prof.py', ['6']),
         ('sheets/nvk_prof.py', ['7']), ('sheets/nvk_nodes.py', []), ('sheets/nvk_od.py', []),
         ('spec/make_spec_nvk.py', ['--pdf']),
         ('spec/make_vor_nvk.py', [os.path.join(HERE, '..', 'in6', 'vor_form.xlsx')])]
CALC = ['И05.09.26-НВК.П1 Расчёт бытовой канализации К1', 'И05.09.26-НВК.П2 Расчёт ливневой канализации К2 и колодца КЛ-1',
        'И05.09.26-НВК.П3 Расчёт дренажа Др', 'И05.09.26-НВК.П4 Расчёт ввода В1']


def run(script, args=()):
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *args], cwd=HERE, capture_output=True, text=True)
    tail = [l for l in (r.stdout + r.stderr).splitlines() if 'warning' not in l.lower()][-1:]
    print(f'{script} {" ".join(a for a in args if len(a) < 6)}: {"OK" if r.returncode == 0 else "ОШИБКА"} '
          f'{" | ".join(tail)[:160]}')
    if r.returncode:
        raise SystemExit(r.stderr[-3000:])


def main():
    if '--no-build' not in sys.argv:
        for s, a in BUILD:
            run(s, a)
    repo = sys.argv[sys.argv.index('--repo') + 1] if '--repo' in sys.argv else None
    rel = os.path.join(HERE, 'release-nvk')
    if os.path.exists(rel):
        shutil.rmtree(rel)
    os.makedirs(rel)
    doc, toc = fitz.open(), []
    for no, base in SHEETS.items():
        src = fitz.open(os.path.join(OUT, base + '_Лист.pdf'))
        toc.append([1, f'Лист {no}. {NVK_LIST[no]}', len(doc) + 1])
        doc.insert_pdf(src)
    so = fitz.open(os.path.join(NO, 'И05.09.26-НВК.СО Спецификация.pdf'))
    toc.append([1, 'И05.09.26-НВК.СО. Спецификация оборудования, изделий и материалов', len(doc) + 1])
    doc.insert_pdf(so)
    doc.set_toc(toc)
    doc.set_metadata({'title': 'И05.09.26-НВК. Наружные сети водопровода и канализации. Рабочая документация',
                      'subject': 'Двухэтажный индивидуальный жилой дом с баней, Московская область'})
    vol = os.path.join(rel, 'И05.09.26-НВК Наружные сети водопровода и канализации.pdf')
    doc.save(vol, garbage=3, deflate=True)
    print('том:', vol, len(doc), 'стр.')
    for ext in ('pdf', 'xlsx'):
        shutil.copy(os.path.join(NO, f'И05.09.26-НВК.СО Спецификация.{ext}'),
                    os.path.join(rel, f'И05.09.26-НВК.СО Спецификация оборудования, изделий и материалов.{ext}'))
    shutil.copy(os.path.join(NO, 'И05.09.26-НВК.ВОР Ведомость объёмов работ.xlsx'),
                os.path.join(rel, 'И05.09.26-НВК.ВОР Ведомость объёмов работ (форма Заказчика).xlsx'))
    calc = os.path.join(rel, 'Расчёты')
    os.makedirs(calc)
    for nm in CALC:
        shutil.copy(os.path.join(NO, nm + '.pdf'), os.path.join(calc, nm + '.pdf'))
    dxf_dir = os.path.join(rel, 'dxf')
    os.makedirs(dxf_dir)
    for no, base in SHEETS.items():
        shutil.copy(os.path.join(OUT, base + '.dxf'), os.path.join(dxf_dir, f'I05-09-26-NVK-{no:02d}.dxf'))
    print('выпуск:', rel)
    for root, _, files in os.walk(rel):
        for f in sorted(files):
            print('  ', os.path.relpath(os.path.join(root, f), rel), os.path.getsize(os.path.join(root, f)) // 1024, 'КБ')
    if repo:
        d = os.path.join(repo, 'cad', 'ovk-i05-09-26', 'dxf')
        for f in os.listdir(dxf_dir):
            shutil.copy(os.path.join(dxf_dir, f), os.path.join(d, f))
        r = os.path.join(repo, 'ovk-dom-banya', 'release-nvk')
        if os.path.exists(r):
            shutil.rmtree(r)
        shutil.copytree(rel, r, ignore=shutil.ignore_patterns('dxf'))
        print('в репозиторий:', d, r)


if __name__ == '__main__':
    main()
