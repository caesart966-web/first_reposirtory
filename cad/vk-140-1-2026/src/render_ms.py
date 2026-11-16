"""render_ms.py in.dxf out.pdf|png [dpi] — модель в рамке листа на формат 1:1 (рамка — внешний контур слоя «Тонкие»)."""
import sys
import ezdxf
from ezdxf import bbox
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, LineweightPolicy

FORMATS = [(841, 594), (594, 420), (420, 297), (297, 210)]


def frame(msp):
    best = None
    for e in msp.query('LWPOLYLINE'):
        b = bbox.extents([e], fast=True)
        if not b.has_data:
            continue
        a = b.size.x * b.size.y
        if best is None or a > best[0]:
            best = (a, b)
    return best[1]


def render(src, out, dpi=None, cfg_kw=None):
    doc = ezdxf.readfile(src)
    msp = doc.modelspace()
    # знак диаметра: контур «Ø» в ISOCPEUR matplotlib заливает — в PDF подменяем на «⌀» (в DXF/DWG остается «Ø»)
    for e in doc.entitydb.values():
        t = e.dxftype()
        if t in ('TEXT', 'ATTRIB', 'ATTDEF'):
            v = e.dxf.get('text', '')
            if 'Ø' in v or '%%c' in v.lower():
                e.dxf.text = v.replace('Ø', '⌀').replace('%%c', '⌀').replace('%%C', '⌀')
        elif t == 'MTEXT':
            v = e.text
            if 'Ø' in v or '%%c' in v.lower() or '\\U+00D8' in v:
                e.text = v.replace('Ø', '⌀').replace('%%c', '⌀').replace('%%C', '⌀').replace('\\U+00D8', '⌀')
    b = frame(msp)
    w, h = b.size.x, b.size.y
    r = w / h
    fw, fh = min(FORMATS, key=lambda f: abs(f[0] / f[1] - r) + (0 if True else 0))
    # формат — по масштабу: ближайший, при котором масштаб «круглый» или 1:1
    k = w / fw
    fig = plt.figure(figsize=(fw / 25.4, fh / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.COLOR,
                        lineweight_policy=LineweightPolicy.ABSOLUTE, min_lineweight=0.1, **(cfg_kw or {}))
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(msp, finalize=False)
    ax.set_xlim(b.extmin.x, b.extmax.x)
    ax.set_ylim(b.extmin.y, b.extmax.y)
    ax.set_aspect('auto')
    ax.axis('off')
    kw = {'dpi': dpi} if dpi else {}
    fig.savefig(out, facecolor='white', **kw)
    plt.close(fig)
    return (fw, fh), k


if __name__ == '__main__':
    print(render(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None))
