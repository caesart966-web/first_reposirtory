"""Растровый просмотр DXF (ezdxf + matplotlib) для проверки."""
import sys
import ezdxf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy

def render(src, out, size=(16, 11), dpi=150):
    doc = ezdxf.readfile(src)
    fig = plt.figure(figsize=size)
    ax = fig.add_axes([0, 0, 1, 1])
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.COLOR_NEGATIVE)
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace())
    fig.savefig(out, dpi=dpi, facecolor='white')

if __name__ == '__main__':
    render(sys.argv[1], sys.argv[2])
