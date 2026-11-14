"""Системы координат листа: мировые (модель, м) <-> местные (u вдоль шоссе, v от шоссе) <-> пиксели генплана."""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TH = np.radians(25.165)
U = np.array([np.cos(TH), np.sin(TH)])
V = np.array([-np.sin(TH), np.cos(TH)])
C = np.array([16803.66, 15592.46])           # юго-западный угол участка
S_, ROT, X0, Y0 = json.load(open(os.path.join(HERE, 'georef_im041.json')))['p']


def w2l(xy):
    q = np.atleast_2d(np.asarray(xy, float)) - C
    return np.c_[q @ U, q @ V]


def l2w(uv):
    uv = np.atleast_2d(np.asarray(uv, float))
    return C + uv[:, :1] * U + uv[:, 1:2] * V


def w2p(xy, k=1.0):
    xy = np.atleast_2d(np.asarray(xy, float))
    c, sn = np.cos(ROT), np.sin(ROT)
    dx, dy = xy[:, 0] - X0, xy[:, 1] - Y0
    return np.c_[(c * dx + sn * dy) / S_, -(-sn * dx + c * dy) / S_] * k


def l2p(uv, k=1.0):
    return w2p(l2w(uv), k)
