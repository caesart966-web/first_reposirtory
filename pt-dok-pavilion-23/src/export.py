"""Вывод листов из пространства модели в PDF в точном масштабе (matplotlib, вектор).
Упрощение путей matplotlib отключено: на листах А0 оно искажало часть линий."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['path.simplify'] = False
matplotlib.rcParams['agg.path.chunksize'] = 0
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, LineweightPolicy
from ezdxf import bbox as ezbbox
from dxfkit import FORMATS

def sheet_pdf(doc, ox, oy, fmt, k, path, mono=False):
    W, H = FORMATS[fmt]
    msp = doc.modelspace()
    box = (ox - 1, oy - 1, ox + W * k + 1, oy + H * k + 1)
    def inside(e):
        try:
            b = ezbbox.extents([e], fast=True)
        except Exception:
            return True
        if not b.has_data:
            return True
        return not (b.extmax.x < box[0] or b.extmin.x > box[2] or b.extmax.y < box[1] or b.extmin.y > box[3])
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                        color_policy=ColorPolicy.BLACK if mono else ColorPolicy.COLOR,
                        lineweight_policy=LineweightPolicy.ABSOLUTE,
                        lineweight_scaling=72 / 25.4, min_lineweight=0.13 * 72 / 25.4)  # мм -> пт (бэкенд берёт мм как пт)
    be = MatplotlibBackend(ax, adjust_figure=False)
    Frontend(RenderContext(doc), be, config=cfg).draw_layout(msp, finalize=True, filter_func=inside)
    ax.set_xlim(ox, ox + W * k); ax.set_ylim(oy, oy + H * k)
    ax.set_aspect('equal', adjustable='box')
    fig.savefig(path, format='pdf')
    plt.close(fig)
