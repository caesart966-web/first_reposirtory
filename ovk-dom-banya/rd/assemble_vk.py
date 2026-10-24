"""Сборка раздела И05.09.26-ВК (дом и баня): проверка модели, расчёты П1–П4, листы 1–14, ВК.СО, ВОР, ТЗ-1, ТЗ-2,
3D-модель (просмотр, DWG через DXF, IFC, виды), том PDF, DXF для перевода в DWG.

python3 assemble_vk.py [--no-build] [--repo /home/user/first_reposirtory]
"""
import os
import shutil
import subprocess
import sys

import pymupdf as fitz

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vk_draw import VK_LIST  # noqa: E402

OUT = os.path.join(HERE, 'out')
VKO = os.path.join(OUT, 'vk')
SHEETS = {1: 'vk_od_1', 2: 'vk_od_2', 3: 'vk_plan1_3', 4: 'vk_frag_4', 5: 'vk_frag_5', 6: 'vk_plan1_6',
          7: 'vk_node', 8: 'vk_bath_8', 9: 'vk_bath_9', 10: 'vk_axo_10', 11: 'vk_axo_11', 12: 'vk_axo_12',
          13: 'vk_coll', 14: 'vk_nodes'}
BUILD = [('vk_check.py', []), ('vk_calc.py', []), ('spec/make_calc_vk.py', []),
         ('sheets/vk_plan1.py', ['3']), ('sheets/vk_plan1.py', ['6']), ('sheets/vk_frag.py', ['4']),
         ('sheets/vk_frag.py', ['5']), ('sheets/vk_node.py', []), ('sheets/vk_bath.py', ['8']),
         ('sheets/vk_bath.py', ['9']), ('sheets/vk_axo.py', ['10']), ('sheets/vk_axo.py', ['11']),
         ('sheets/vk_axo.py', ['12']), ('sheets/vk_coll.py', []), ('sheets/vk_nodes.py', []), ('sheets/vk_od.py', []),
         ('spec/make_spec_vk.py', ['--pdf']), ('spec/make_vor_vk.py', [os.path.join(HERE, '..', 'in6', 'vor_form.xlsx')]),
         ('sheets/tz_vk_ar.py', []), ('sheets/tz_vk_eom.py', []), ('vk_3d.py', [])]
WEB = os.path.join(HERE, '..', 'm3d', 'web')
SHOTS = os.path.join(OUT, 'vk3d', 'shots')
VIEWS3D = [('iso', 'Общий вид (дом и баня): ввод, коллекторы, К1 под плитой'), ('gar', 'Под потолком гаража: ШВК-2, магистрали, К1'),
           ('topo', 'Топочная 1.6: ввод из приямка, водомерный узел, гребёнка КХ'), ('bath', 'Баня: ШВК-Б, Б2, К1 под плитой')]
CALC = ['И05.09.26-ВК.П1 Баланс водопотребления и водоотведения', 'И05.09.26-ВК.П2 Расчёт сетей водопровода. '
        'Требуемый напор на вводе', 'И05.09.26-ВК.П3 Расчёт системы канализации К1',
        'И05.09.26-ВК.П4 Расчёт циркуляции горячей воды']


def run(script, args=()):
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *args], cwd=HERE, capture_output=True, text=True)
    tail = [l for l in (r.stdout + r.stderr).splitlines() if 'warning' not in l.lower()][-1:]
    print(f'{script} {" ".join(a for a in args if len(a) < 6)}: {"OK" if r.returncode == 0 else "ОШИБКА"} '
          f'{" | ".join(tail)[:160]}')
    if r.returncode:
        raise SystemExit(r.stderr[-3000:])


def shots():
    html = os.path.join(OUT, 'vk3d', 'view.html')
    subprocess.run(['node', 'build.mjs', os.path.join(OUT, 'vk3d', 'model.json'), html], cwd=WEB, check=True,
                   capture_output=True)
    os.makedirs(SHOTS, exist_ok=True)
    env = dict(os.environ, SHOT_W='1200', SHOT_H='750', SHOT_DPR='2')
    subprocess.run(['node', 'shot.mjs', html, SHOTS, *[f'{v}?view={v}&ui=0' for v, _ in VIEWS3D]], cwd=WEB,
                   check=True, capture_output=True, env=env)


def views_pdf(path):
    """Виды 3D-модели на одном листе А3 (для наглядности)."""
    mm = 72 / 25.4
    FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
    doc = fitz.open()
    pg = doc.new_page(width=420 * mm, height=297 * mm)
    pg.insert_font(fontname='ls', fontfile=FONT)
    pg.insert_text((20 * mm, 14 * mm), 'И05.09.26-ВК. 3D-модель систем водопровода и канализации — виды',
                   fontsize=14, fontname='ls')
    W, H = 185.0, 115.6
    pos = [(20, 22), (215, 22), (20, 160), (215, 160)]
    for (name, cap), (x, y) in zip(VIEWS3D, pos):
        r = fitz.Rect(x * mm, (y + 6) * mm, (x + W) * mm, (y + 6 + H) * mm)
        from PIL import Image
        jpg = os.path.join(SHOTS, name + '.jpg')
        Image.open(os.path.join(SHOTS, name + '.png')).convert('RGB').save(jpg, quality=85, optimize=True)
        pg.insert_image(r, filename=jpg)
        pg.draw_rect(r, color=(0.6, 0.6, 0.6), width=0.5)
        pg.insert_text((x * mm, (y + 4.5) * mm), cap, fontsize=10, fontname='ls')
    pg.insert_textbox(fitz.Rect(20 * mm, 284 * mm, 400 * mm, 295 * mm),
                      'Виды — снимки просмотрщика модели (файл «просмотр в браузере»). Листы ВК и ВК.СО получены из этой '
                      'модели. Стены — по АР, баня — на своём месте по генплану ГП01; трубы котельной ТМ — серым.',
                      fontsize=8, fontname='ls')
    doc.save(path)


def main():
    if '--no-build' not in sys.argv:
        for s, a in BUILD:
            run(s, a)
        shots()
    repo = sys.argv[sys.argv.index('--repo') + 1] if '--repo' in sys.argv else None
    rel = os.path.join(HERE, 'release-vk')
    if os.path.exists(rel):
        shutil.rmtree(rel)
    os.makedirs(rel)
    # ---- том: листы 1–14 и ВК.СО
    doc, toc = fitz.open(), []
    for no, base in SHEETS.items():
        src = fitz.open(os.path.join(OUT, base + '_Лист.pdf'))
        toc.append([1, f'Лист {no}. {VK_LIST[no]}', len(doc) + 1])
        doc.insert_pdf(src)
    so = fitz.open(os.path.join(VKO, 'И05.09.26-ВК.СО Спецификация.pdf'))
    toc.append([1, 'И05.09.26-ВК.СО. Спецификация оборудования, изделий и материалов', len(doc) + 1])
    doc.insert_pdf(so)
    doc.set_toc(toc)
    doc.set_metadata({'title': 'И05.09.26-ВК. Водопровод и канализация. Рабочая документация',
                      'subject': 'Двухэтажный индивидуальный жилой дом с баней, Московская область'})
    vol = os.path.join(rel, 'И05.09.26-ВК Водопровод и канализация.pdf')
    doc.save(vol, garbage=3, deflate=True)
    print('том:', vol, len(doc), 'стр.')
    for ext in ('pdf', 'xlsx'):
        shutil.copy(os.path.join(VKO, f'И05.09.26-ВК.СО Спецификация.{ext}'),
                    os.path.join(rel, f'И05.09.26-ВК.СО Спецификация оборудования, изделий и материалов.{ext}'))
    shutil.copy(os.path.join(VKO, 'И05.09.26-ВК.ВОР Ведомость объёмов работ.xlsx'),
                os.path.join(rel, 'И05.09.26-ВК.ВОР Ведомость объёмов работ (форма Заказчика).xlsx'))
    calc = os.path.join(rel, 'Расчёты')
    os.makedirs(calc)
    for nm in CALC:
        shutil.copy(os.path.join(VKO, nm + '.pdf'), os.path.join(calc, nm + '.pdf'))
    tz = os.path.join(rel, 'Задания смежникам')
    os.makedirs(tz)
    shutil.copy(os.path.join(OUT, 'tz_vk_ar.pdf'), os.path.join(tz, 'И05.09.26-ВК.ТЗ-1 Задание АР и КР.pdf'))
    shutil.copy(os.path.join(OUT, 'tz_vk_eom_Лист.pdf'), os.path.join(tz, 'И05.09.26-ВК.ТЗ-2 Задание ЭОМ.pdf'))
    d3 = os.path.join(rel, '3d')
    os.makedirs(d3)
    shutil.copy(os.path.join(OUT, 'vk3d', 'view.html'), os.path.join(d3, 'И05.09.26-ВК 3D (просмотр в браузере).html'))
    shutil.copy(os.path.join(OUT, 'vk3d', 'I05-09-26-VK-3D.ifc'), os.path.join(d3, 'И05.09.26-ВК 3D.ifc'))
    views_pdf(os.path.join(d3, 'И05.09.26-ВК 3D виды.pdf'))
    with open(os.path.join(d3, 'Как открыть 3D.txt'), 'w') as fh:
        fh.write('3D-модель систем водопровода и канализации дома и бани, раздел И05.09.26-ВК\n\n'
                 '1. «И05.09.26-ВК 3D (просмотр в браузере).html» — открыть двойным щелчком (Chrome, Edge, '
                 'Яндекс Браузер), интернет не нужен; вращение — '
                 'левая кнопка мыши, сдвиг — правая, масштаб — колесо; кнопки видов вверху, системы и этажи — слева; '
                 'нажатие на трубу показывает её название, типоразмер и отметку.\n'
                 '2. DWG (папка DWG, файл I05-09-26-VK-3D.dwg) — 3D-сети в AutoCAD (мм, начало — '
                 'пересечение осей 1/А дома; баня — на своём месте по генплану ГП01 «Привязка дома и бани на участке»); '
                 'вид — «3D-орбита».\n'
                 '3. IFC — для Revit, Renga, BIMcollab, Solibri: в координатах выгрузки Revit, как модели ОВ и ТМ.\n'
                 'Листы ВК и ВК.СО получены из этой модели; пересечений труб между собой, с ТМ и с ОВ нет.\n')
    dxf_dir = os.path.join(rel, 'dxf')
    os.makedirs(dxf_dir)
    for no, base in SHEETS.items():
        shutil.copy(os.path.join(OUT, base + '.dxf'), os.path.join(dxf_dir, f'I05-09-26-VK-{no:02d}.dxf'))
    shutil.copy(os.path.join(OUT, 'tz_vk_ar.dxf'), os.path.join(dxf_dir, 'I05-09-26-VK-TZ1.dxf'))
    shutil.copy(os.path.join(OUT, 'tz_vk_eom.dxf'), os.path.join(dxf_dir, 'I05-09-26-VK-TZ2.dxf'))
    shutil.copy(os.path.join(OUT, 'vk3d', 'I05-09-26-VK-3D.dxf'), os.path.join(dxf_dir, 'I05-09-26-VK-3D.dxf'))
    print('выпуск:', rel)
    for root, _, files in os.walk(rel):
        for f in sorted(files):
            print('  ', os.path.relpath(os.path.join(root, f), rel), os.path.getsize(os.path.join(root, f)) // 1024, 'КБ')
    if repo:
        d = os.path.join(repo, 'cad', 'ovk-i05-09-26', 'dxf')
        for f in os.listdir(dxf_dir):
            shutil.copy(os.path.join(dxf_dir, f), os.path.join(d, f))
        r = os.path.join(repo, 'ovk-dom-banya', 'release-vk')
        if os.path.exists(r):
            shutil.rmtree(r)
        shutil.copytree(rel, r, ignore=shutil.ignore_patterns('dxf'))
        print('в репозиторий:', d, r)


if __name__ == '__main__':
    main()
