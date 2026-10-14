"""Вывод листов из пространства модели в PDF в натуральную величину (matplotlib, вектор)."""
import os, shutil, tempfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['path.simplify'] = False
matplotlib.rcParams['agg.path.chunksize'] = 0
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, LineweightPolicy
from ezdxf.fonts import fonts as ezfonts

# стиль GOST в DXF ссылается на isocpeui.ttf (есть в AutoCAD); для PDF его заменяет osifont того же начертания
_FD = tempfile.mkdtemp(prefix='pbfonts_')
_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fonts', 'osifont-lgpl3fe.ttf')
for name in ('isocpeui.ttf', 'isocpeur.ttf'):
    shutil.copy(_SRC, os.path.join(_FD, name))
ezdxf.options.support_dirs = list(ezdxf.options.support_dirs) + [_FD]
ezfonts.font_manager.clear()
ezfonts.font_manager.build()


def sheet_pdf(doc, ox, oy, W, H, path, index=None):
    """index — функция (x0, y0, x1, y1) → сущности; без неё перебирается всё пространство модели."""
    msp = doc.modelspace()
    box = (ox - 1, oy - 1, ox + W + 1, oy + H + 1)
    keep = None
    if index is not None:
        keep = {id(e) for e in index(*box)}

    def inside(e):
        if keep is not None:
            return id(e) in keep
        return True
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.COLOR,
                        lineweight_policy=LineweightPolicy.ABSOLUTE,
                        lineweight_scaling=72 / 25.4, min_lineweight=0.10 * 72 / 25.4)
    be = MatplotlibBackend(ax, adjust_figure=False)
    fe = Frontend(RenderContext(doc), be, config=cfg)
    fe.draw_layout(msp, finalize=True, filter_func=inside)
    ax.set_xlim(ox, ox + W); ax.set_ylim(oy, oy + H)
    ax.set_aspect('equal', adjustable='box')
    fig.savefig(path, format='pdf')
    plt.close(fig)
