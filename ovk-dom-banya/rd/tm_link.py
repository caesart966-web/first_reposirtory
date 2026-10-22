"""Связь листов ОВ с 3D-моделью котельной (tm_model): расстановка, магистрали в топочной, длины.

Листы ОВ (3, 4, 7, ТЗ) берут положение оборудования и трубы в топочной отсюда — одна точка правды с ТМ.
"""
import math
import tm_model as TM

_built = False


def _ensure():
    global _built
    if not _built:
        TM.build()
        _built = True


def E(eid):
    _ensure()
    return next(e for e in TM.EQUIP if e.id == eid)


def P(pid):
    _ensure()
    return next(p for p in TM.PIPES if p.id == pid)


def rect(eid):
    b = E(eid).bbox()
    return (round(b[0], 3), round(b[1], 3), round(b[3], 3), round(b[4], 3))


def circ(eid):
    x, y, r, _, _ = E(eid).g
    return (x, y, r)


def rk_rect():
    """ГС + РК с группами (план)."""
    hs = rect('ГС')
    rk = rect('РК')
    gr = [rect(n) for n, _ in TM.GROUPS]
    return (min(hs[0], rk[0]), min(r[1] for r in gr), max(rk[2], max(r[2] for r in gr)), max(r[3] for r in gr))


def plan(pid, zmin=None):
    """Ломаная трубы в плане (без вертикальных участков)."""
    out = []
    for x, y, z in P(pid).pts:
        q = (round(x, 4), round(y, 4))
        if not out or math.dist(out[-1], q) > 1e-6:
            out.append(q)
    return out


def length(pid):
    return P(pid).length()


def length_to_x(pid, x_stop):
    """Длина подачи от РК до сечения x = x_stop (точка ответвления)."""
    pts = P(pid).pts
    L = 0.0
    for a, b in zip(pts, pts[1:]):
        if (a[0] - x_stop) * (b[0] - x_stop) <= 0 and abs(b[0] - a[0]) > 1e-9:
            t = (x_stop - a[0]) / (b[0] - a[0])
            return L + math.dist(a, b) * t
        L += math.dist(a, b)
    return L


def wall_end(pid):
    """Точка выхода трубы из топочной (конец у западной стены), план."""
    x, y, z = P(pid).pts[-1] if P(pid).pts[-1][0] < P(pid).pts[0][0] else P(pid).pts[0]
    return (x, y, z)


# магистрали ОВ в топочной: шкаф -> (трубы ТМ подача/обратка, длина в топочной в одну сторону)
def inroom():
    _ensure()
    kx = P('КШ-3-П').pts[0][0]
    return {
        'КШ-2': (('Н3-П', 'Н3-О'), length('Н3-П')),
        'КШ-1': (('Н4-П', 'Н4-О'), length('Н4-П')),
        'КШ-3': (('КШ-3-П', 'КШ-3-О'), length_to_x('Н4-П', kx) + length('КШ-3-П')),
        'КШ-4': (('Н2-П', 'Н2-О'), length('Н2-П')),
        'П1': (('Н5-П', 'Н5-О'), length('Н5-П')),
    }


ECO_UP = TM.ECO
