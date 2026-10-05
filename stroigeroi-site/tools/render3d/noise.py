"""Векторный шум Перлина на numpy: 2D, fbm, ridged."""
import numpy as np

_rng = np.random.default_rng(7)
_perm = np.concatenate([_rng.permutation(256)] * 2)
_ang = _rng.random(256) * 2 * np.pi
_gx, _gy = np.cos(_ang), np.sin(_ang)


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def perlin(x, y, period_x=None):
    """Шум в [-1,1] (примерно). period_x — период по x (для полярных координат)."""
    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    xf = x - xi
    yf = y - yi
    if period_x:
        xi0 = np.mod(xi, period_x)
        xi1 = np.mod(xi + 1, period_x)
    else:
        xi0, xi1 = xi, xi + 1
    def g(ix, iy, dx, dy):
        h = _perm[(_perm[np.mod(ix, 256)] + np.mod(iy, 256))]
        return _gx[h] * dx + _gy[h] * dy
    n00 = g(xi0, yi, xf, yf)
    n10 = g(xi1, yi, xf - 1, yf)
    n01 = g(xi0, yi + 1, xf, yf - 1)
    n11 = g(xi1, yi + 1, xf - 1, yf - 1)
    u, v = _fade(xf), _fade(yf)
    nx0 = n00 + u * (n10 - n00)
    nx1 = n01 + u * (n11 - n01)
    return (nx0 + v * (nx1 - nx0)) * 1.41


def fbm(x, y, octaves=6, lac=2.0, gain=0.5, period_x=None):
    s = np.zeros_like(x, dtype=np.float64)
    a, f, norm = 1.0, 1.0, 0.0
    for i in range(octaves):
        px = int(period_x * f) if period_x else None
        s += a * perlin(x * f + i * 17.1, y * f + i * 31.7, px)
        norm += a
        a *= gain
        f *= lac
    return s / norm


def ridged(x, y, octaves=6, lac=2.0, gain=0.5, period_x=None):
    """Хребты: 1 на гребне, 0 в ложбине."""
    s = np.zeros_like(x, dtype=np.float64)
    a, f, norm = 1.0, 1.0, 0.0
    w = np.ones_like(x, dtype=np.float64)
    for i in range(octaves):
        px = int(period_x * f) if period_x else None
        n = 1.0 - np.abs(perlin(x * f + i * 11.3, y * f + i * 5.9, px))
        n = n * n
        n *= w
        w = np.clip(n * 1.6, 0, 1)
        s += a * n
        norm += a
        a *= gain
        f *= lac
    return s / norm
