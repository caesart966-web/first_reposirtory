"""Трассы смежного раздела ВК в техническом подвале — в координатах модели (мм, система DWG АР).

Источник: ОПР-01/24/2024-ДП1-ВК, файл «2_Док павильон ВК2 - Тех этаж оси 1-9.dwg» (листы 2–7 К1,
планы В1 подвала). DWG сохранён в формате AutoCAD 2018, его сначала выгружает vk_dump.mjs:
    node vk_dump.mjs "<файл>.dwg" ents.jsonl
    python3 vk_extract.py ents.jsonl ../src/vk_nets.json

Виды на листах ВК вставлены в масштабе 0,063 (1:15,9); привязка каждого плана — по линиям осей
(ось 1 или 10 и ось В), значения сняты с осей самого файла. Берутся осевые линии труб (слой
P-PIPE-CNTR), стояки К1 — по концам горизонтальных отводов, стояки В1 — по разрезу 1-1 В1.
Отметки в файле не подписаны, они сняты с разрезов ВК и записаны ниже руками (LEVELS)."""
import json, sys

K = 0.063
VIEWS = {   # система: [(рамка вида на листе ВК), (x оси на листе, X оси), (y оси на листе, Y оси)]
    'К1': [((197800, 21000, 202200, 24100), (198593.60, 0), (22307.09, 12000)),        # оси 1–9
           ((197800, 17500, 202200, 20700), (198606.66, 52000), (18801.07, 12000))],    # оси 10–18
    'В1': [((197800, 12500, 202200, 15600), (198636.58, 0), (13930.29, 12000)),
           ((197800, 8500, 202200, 11600), (198744.83, 52000), (9840.31, 12000))],
}
# стояки В1 к приборам 1 этажа — по разрезу 1-1 В1 (листы 4, 9 ДП1-ВК), x, мм
B1_RISERS_X = [4334, 10132, 16134, 22139, 28139, 34134, 40134, 57866, 63866, 69861, 75861, 81866, 87866, 93666]
LEVELS = {
    'К1_магистраль': 'ПВХ 110 вдоль внутренних стен коридоров; ось −1,57 у оси 1, около −0,77 у оси 9 '
                     '(разрез 1-1 ДП1-ВК, уклон ~0,018); у оси 18 — зеркально',
    'К1_отвод': [-1.05, -0.88],      # поперёк коридора (разрезы 2-2, 5-5)
    'К1_ветка': -0.60,               # вдоль коридора под перекрытием, к стояку на 1 этаж (разрез 1-1)
    'В1_низ': -2.10, 'В1_верх': -1.60,   # вдоль наружных стен коридоров (разрез 1-1 В1)
}


def segs(path):
    """Осевые линии из выгрузки, уже в координатах модели."""
    out = {s: [] for s in VIEWS}
    for line in open(path, encoding='utf-8'):
        if '"P-PIPE-CNTR"' not in line or '"LINE"' not in line[:20]:
            continue
        e = json.loads(line)
        a, b = e['startPoint'], e['endPoint']
        for sysn, views in VIEWS.items():
            for (x0, y0, x1, y1), (xs, Xs), (ys, Ys) in views:
                if all(x0 <= p['x'] <= x1 and y0 <= p['y'] <= y1 for p in (a, b)):
                    out[sysn].append([((p['x'] - xs) / K + Xs, (p['y'] - ys) / K + Ys) for p in (a, b)])
    return out


def merge(lines, gap=400, minlen=300):
    """Горизонтальные и вертикальные отрезки — в непрерывные трассы (разрывы на фасонине ≤ gap)."""
    hz, vt = {}, {}
    for (xa, ya), (xb, yb) in lines:
        if abs(ya - yb) < 5 and abs(xa - xb) > 20:
            hz.setdefault(round((ya + yb) / 2 / 10) * 10, []).append(sorted((xa, xb)))
        elif abs(xa - xb) < 5 and abs(ya - yb) > 20:
            vt.setdefault(round((xa + xb) / 2 / 10) * 10, []).append(sorted((ya, yb)))
    runs = []
    for key, store, horiz in ((None, hz, True), (None, vt, False)):
        for c, iv in store.items():
            iv.sort(); cur = list(iv[0])
            for a, b in iv[1:] + [[1e12, 1e12]]:
                if a <= cur[1] + gap:
                    cur[1] = max(cur[1], b)
                else:
                    if cur[1] - cur[0] >= minlen:
                        runs.append([round(cur[0]), c, round(cur[1]), c] if horiz else [c, round(cur[0]), c, round(cur[1])])
                    cur = [a, b]
    return sorted(runs)


def k1_risers(runs):
    """Стояк К1 — на дальнем от отвода конце горизонтальной ветки (ветки y 26230 и 13770):
    осевая линия ветки доходит до оси стояка."""
    ns = [r for r in runs if r[0] == r[2]]
    res = []
    for x0, y, x1, _ in (r for r in runs if r[1] == r[3] and r[1] in (13770, 26230)):
        near = [b[0] for b in ns if min(abs(b[0] - x0), abs(b[0] - x1)) < 1200 and b[1] <= y + 200 and b[3] >= y - 200]
        if not near:
            continue
        bx = min(near, key=lambda v: min(abs(v - x0), abs(v - x1)))
        res.append([x0, y] if abs(bx - x1) < abs(bx - x0) else [x1, y])
    return sorted(set(map(tuple, res)))


def main(src, dst):
    S = segs(src)
    k1 = merge(S['К1']); b1 = merge(S['В1'])
    data = {
        'source': 'ОПР-01/24/2024-ДП1-ВК (ООО ТЕХНОЛОГИЯ, 15.01), «2_Док павильон ВК2 - Тех этаж оси 1-9.dwg»',
        'levels': LEVELS,
        'К1': {'runs': k1, 'risers': [list(p) for p in k1_risers(k1)]},
        'В1': {'runs': b1, 'risers': [[x, y] for x in B1_RISERS_X for y in (27503, 12497)]},
    }
    json.dump(data, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('К1 трасс', len(k1), 'стояков', len(data['К1']['risers']), '| В1 трасс', len(b1))


if __name__ == '__main__':
    main(*sys.argv[1:3])
