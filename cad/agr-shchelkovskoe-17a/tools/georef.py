"""Привязка карт из письма ДГП (767x767, север вверху) к координатам модели по контуру участка."""
import json
import numpy as np
from PIL import Image
from scipy.optimize import minimize
from shapely.geometry import Polygon, Point, LineString


def site_poly(areas='agr_work/out_ifc/areas.json'):
    a = json.load(open(areas))
    return Polygon(np.array(a['site_world']) / 1000)


def purple_mask(a):
    a = a.astype(int)
    return (abs(a[:, :, 0] - 153) < 60) & (a[:, :, 1] < 80) & (a[:, :, 2] > 180)


def fit(img_path, site):
    a = np.asarray(Image.open(img_path).convert('RGB'))
    ys, xs = np.nonzero(purple_mask(a))
    pts = np.c_[xs + 0.5, ys + 0.5]
    ring = site.exterior
    bx0, by0, bx1, by1 = site.bounds
    s0 = (bx1 - bx0) / (xs.max() - xs.min())
    p0 = [s0, bx0 - xs.min() * s0, by1 + ys.min() * s0]

    def cost(p):
        s, X0, Y0 = p
        X = X0 + pts[:, 0] * s
        Y = Y0 - pts[:, 1] * s
        d = np.array([ring.distance(Point(x, y)) for x, y in zip(X, Y)])
        return float(np.mean(np.minimum(d, 3.0) ** 2))
    r = minimize(cost, p0, method='Nelder-Mead', options={'xatol': 1e-4, 'fatol': 1e-7, 'maxiter': 4000})
    return r.x, np.sqrt(r.fun), a


def to_px(xy, p):
    s, X0, Y0 = p
    xy = np.asarray(xy, float)
    return np.c_[(xy[:, 0] - X0) / s, (Y0 - xy[:, 1]) / s]
