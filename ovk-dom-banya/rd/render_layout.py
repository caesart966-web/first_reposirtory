"""render_layout.py file.dxf out.pdf [layout] — печать листа в PDF 1:1.

Пространство листа рисуется без видовых экранов, а модель — отдельно в рамку каждого видового экрана
с его масштабом: так в PDF видны типы линий (ezdxf внутри видовых экранов рисует их сплошными).
"""
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                         # noqa: E402
from ezdxf import recover                                               # noqa: E402
from ezdxf.addons.drawing import RenderContext, Frontend                # noqa: E402
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend           # noqa: E402
from ezdxf.addons.drawing.config import (Configuration, BackgroundPolicy, ColorPolicy,  # noqa: E402
                                         LineweightPolicy)

src, out = sys.argv[1], sys.argv[2]
doc, _ = recover.readfile(src)
lay = doc.layouts.get(sys.argv[3]) if len(sys.argv) > 3 else [l for l in doc.layouts if l.name != 'Model'][-1]
W, H = lay.dxf.paper_width, lay.dxf.paper_height
mono = 'mono' in sys.argv[4:]
cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                    color_policy=ColorPolicy.BLACK if mono else ColorPolicy.COLOR,
                    lineweight_policy=LineweightPolicy.ABSOLUTE, min_lineweight=0.1)

# знак диаметра: контур «Ø» в ISOCPEUR matplotlib заливает — в PDF подменяем на «⌀» (в DXF/DWG остаётся «Ø»)
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

vps = [e for e in lay.query('VIEWPORT') if e.dxf.status >= 2]
for v in vps:
    v.dxf.status = 0                         # пространство листа — без видовых экранов

fig = plt.figure(figsize=(W / 25.4, H / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect('equal')
ax.axis('off')
for v in vps:
    cx, cy = v.dxf.center[0], v.dxf.center[1]
    w, h = v.dxf.width, v.dxf.height
    k = v.dxf.view_height / h                # единиц модели на мм листа
    mx, my = v.dxf.view_center_point[0], v.dxf.view_center_point[1]
    axv = fig.add_axes([(cx - w / 2) / W, (cy - h / 2) / H, w / W, h / H])
    axv.set_facecolor('none')
    Frontend(RenderContext(doc), MatplotlibBackend(axv), config=cfg).draw_layout(doc.modelspace(), finalize=False)
    axv.set_xlim(mx - w / 2 * k, mx + w / 2 * k)
    axv.set_ylim(my - h / 2 * k, my + h / 2 * k)
    axv.set_aspect('auto')
    axv.axis('off')
Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(lay, finalize=False)
ax.set_xlim(0, W)
ax.set_ylim(0, H)
fig.savefig(out, facecolor='white')
