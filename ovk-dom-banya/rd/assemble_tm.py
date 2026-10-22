"""Сборка раздела И05.09.26-ТМ (котельная): 3D-модель (DXF 3D, IFC, просмотр, виды), листы 1–6, ТМ.СО, том PDF.

python3 assemble_tm.py [--no-build] [--repo /home/user/first_reposirtory]
"""
import os
import shutil
import subprocess
import sys

import pymupdf as fitz

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tm_draw import TM_LIST  # noqa: E402

OUT = os.path.join(HERE, 'out')
SHEETS = {1: 'tm_od', 2: 'tm_plans', 3: 'tm_sec12', 4: 'tm_sec34', 5: 'tm_axo', 6: 'tm_3d'}
BUILD = [('tm_model.py', []), ('sheets/tm_od.py', []), ('sheets/tm_plans.py', []), ('sheets/tm_sections.py', []),
         ('sheets/tm_axo.py', []), ('sheets/tm_3d.py', []), ('spec/make_spec_tm.py', [])]
WEB = os.path.join(HERE, '..', 'm3d', 'web')          # рабочая папка; в репозитории — rd/viewer3d
if not os.path.isdir(WEB):
    WEB = os.path.join(HERE, 'viewer3d')
from tm_3d_shots import SHOTS  # noqa: E402


def run(script, args=(), cwd=HERE):
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *args], cwd=cwd, capture_output=True, text=True)
    tail = [l for l in (r.stdout + r.stderr).splitlines() if 'warning' not in l.lower()][-2:]
    print(f'{script}: {"OK" if r.returncode == 0 else "ОШИБКА"} {" | ".join(tail)[:200]}')
    if r.returncode:
        raise SystemExit(r.stderr[-3000:])


def build():
    run('tm_model.py')
    subprocess.run(['node', 'build.mjs', os.path.join(OUT, 'tm', 'model.json'), os.path.join(OUT, 'tm', 'view.html')],
                   cwd=WEB, check=True, capture_output=True)
    env = dict(os.environ, SHOT_W='1200', SHOT_H='750', SHOT_DPR='2')
    subprocess.run(['node', 'shot.mjs', os.path.join(OUT, 'tm', 'view.html'), SHOTS,
                    'sw?view=sw&ui=0', 'sw0?view=sw&ui=0&OV=0', 'nw?view=nw&ui=0&OV=0', 'rk?view=rk&ui=0&OV=0'], cwd=WEB, check=True, capture_output=True, env=env)
    for s, a in BUILD[1:]:
        run(s, a)


def main():
    if '--no-build' not in sys.argv:
        build()
    repo = sys.argv[sys.argv.index('--repo') + 1] if '--repo' in sys.argv else None
    rel = os.path.join(HERE, 'release-tm')
    os.makedirs(rel, exist_ok=True)
    doc, toc = fitz.open(), []
    for no, base in SHEETS.items():
        src = fitz.open(os.path.join(OUT, base + '_Лист.pdf'))
        toc.append([1, f'Лист {no}. {TM_LIST[no]}', len(doc) + 1])
        doc.insert_pdf(src)
    doc.set_toc(toc)
    doc.set_metadata({'title': 'И05.09.26-ТМ. Тепломеханические решения котельной. Рабочая документация',
                      'subject': 'Двухэтажный индивидуальный жилой дом с баней, Московская область'})
    vol = os.path.join(rel, 'И05.09.26-ТМ РД Котельная (тепломеханические решения).pdf')
    doc.save(vol, garbage=3, deflate=True)
    print('том:', vol, len(doc), 'листов')
    for ext in ('pdf', 'xlsx'):
        shutil.copy(os.path.join(OUT, f'И05.09.26-ТМ.СО Спецификация.{ext}'),
                    os.path.join(rel, f'И05.09.26-ТМ.СО Спецификация оборудования, изделий и материалов.{ext}'))
    d3 = os.path.join(rel, '3d')
    os.makedirs(d3, exist_ok=True)
    shutil.copy(os.path.join(OUT, 'tm', 'view.html'), os.path.join(d3, 'И05.09.26-ТМ 3D котельной (просмотр в браузере).html'))
    shutil.copy(os.path.join(OUT, 'tm', 'I05-09-26-TM-3D.ifc'), os.path.join(d3, 'И05.09.26-ТМ 3D котельной.ifc'))
    shutil.copy(os.path.join(OUT, 'tm_3d_Лист.pdf'), os.path.join(d3, 'И05.09.26-ТМ 3D виды котельной.pdf'))
    with open(os.path.join(d3, 'Как открыть 3D.txt'), 'w') as fh:
        fh.write('3D-модель котельной (топочная 1.6), раздел И05.09.26-ТМ\n\n'
                 '1. «просмотр в браузере».html — открыть двойным щелчком (Chrome, Edge, Яндекс Браузер); вращение — '
                 'левая кнопка мыши, сдвиг — правая, масштаб — колесо; кнопки видов вверху, системы — слева '
                 '(сети ОВ в топочной можно выключить).\n'
                 '2. DWG — 3D-сеть в AutoCAD (мм, начало — пересечение осей 1/А, как на листах); вид — «3D-орбита».\n'
                 '3. IFC — для Revit, Renga, BIMcollab, Solibri: в координатах выгрузки Revit, как модель ОВ.\n'
                 'Листы ТМ (планы, разрезы, аксонометрия) и ТМ.СО получены из этой модели.\n')
    dxf_dir = os.path.join(rel, 'dxf')
    os.makedirs(dxf_dir, exist_ok=True)
    for no, base in SHEETS.items():
        shutil.copy(os.path.join(OUT, base + '.dxf'), os.path.join(dxf_dir, f'I05-09-26-TM-{no:02d}.dxf'))
    shutil.copy(os.path.join(OUT, 'tm', 'I05-09-26-TM-3D.dxf'), os.path.join(dxf_dir, 'I05-09-26-TM-3D.dxf'))
    for f in os.listdir(OUT):
        if f.startswith('tm3d_') and f.endswith('.png'):
            shutil.copy(os.path.join(OUT, f), os.path.join(rel, f))
    if repo:
        d = os.path.join(repo, 'cad', 'ovk-i05-09-26', 'dxf')
        for f in os.listdir(dxf_dir):
            shutil.copy(os.path.join(dxf_dir, f), os.path.join(d, f))
        r = os.path.join(repo, 'ovk-dom-banya', 'release-tm')
        if os.path.exists(r):
            shutil.rmtree(r)
        shutil.copytree(rel, r, ignore=shutil.ignore_patterns('dxf'))
        print('в репозиторий:', d, r)


if __name__ == '__main__':
    main()
