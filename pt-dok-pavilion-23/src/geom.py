"""Геометрия здания (из DWG АР) и правила защиты помещений."""
import json, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, 'rooms.json')))
FRZ = json.load(open(os.path.join(HERE, 'freezers.json')))

AX_X = {'1':0,'2':4000,'3':10000,'4':16000,'5':22000,'6':28000,'7':34000,'8':40000,'9':46000,
        '10':52000,'11':58000,'12':64000,'13':70000,'14':76000,'15':82000,'16':88000,'17':94000,'18':98000}
AX_Y = {'А':0,'Б':6000,'В':12000,'Г':18000,'Д':22000,'Е':28000,'Ж':34000,'И':40000}

def bb(poly):
    xs=[p[0] for p in poly]; ys=[p[1] for p in poly]
    return [min(xs),min(ys),max(xs),max(ys)]

def pip(x,y,poly):
    c=False; n=len(poly)
    for i in range(n):
        x1,y1=poly[i]; x2,y2=poly[(i+1)%n]
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: c=not c
    return c

def rooms(floor):
    out={}
    for r in R[floor]['rooms']:
        out[r['num']]=dict(r)
    if floor=='f1':   # исправление: у СУ М в DWG взят контур тамбура
        out['99']['poly']=[[93875,22225],[98125,22225],[98125,28125],[93875,28125]]
    return out

FREEZERS=[f['bb'] for f in FRZ]

# Отметки (м) — по разрезам АР
Z_F1_CEIL = 3.365      # низ плиты по профлисту над 1 этажом
Z_F2_FLOOR = 3.700
def z_roof_ceiling(y):
    """низ профлиста покрытия: 7.60 у наружных стен, 7.36 по оси здания (у=20 м)"""
    return 7.36 + 0.24*abs(y-20000)/20000

# Группы помещений (принято, см. ведомость решений) и параметры по СП 485 (табл. 6.1/6.2)
GROUPS = {
    2: dict(q=0.12, S=120, t=60, Qmin=30.0, smax=4.0, Amax=12.0),
    5: dict(q=0.16, S=150, t=60, Qmin=None, smax=3.0, Amax=9.0),   # h складирования до 2 м
}
