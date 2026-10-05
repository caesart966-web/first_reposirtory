"""Ближний берег: склон к бухте, жилые дома, деревья — одним мешем каждое."""
import bpy, bmesh, math
import numpy as np
from noise import fbm


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


SHORE_Y = 3500.0


def shore_y(x):
    return SHORE_Y + fbm(x / 1400, np.full_like(x, 4.0), octaves=4) * 420


def ground_h(x, y):
    """Дальний берег бухты: от воды склон поднимается к сопкам."""
    sh = shore_y(x)
    rise = smoothstep(sh, sh + 2600, y) * 230 + smoothstep(sh + 2200, sh + 6000, y) * 180
    rise += fbm(x / 800, y / 800, octaves=4) * 22 * smoothstep(sh, sh + 600, y)
    return rise * smoothstep(sh - 30, sh + 160, y) + 3 * smoothstep(sh - 60, sh + 60, y) - 10 * (1 - smoothstep(sh - 80, sh + 40, y))


def build_ground(nx=1100, ny=420):
    xs = np.linspace(-9000, 9000, nx)
    ys = np.linspace(2600, 10500, ny)
    X, Y = np.meshgrid(xs, ys)
    return X, Y, ground_h(X, Y)


PALETTE = [
    (0.70, 0.64, 0.52), (0.76, 0.72, 0.64), (0.62, 0.52, 0.42), (0.68, 0.70, 0.72),
    (0.58, 0.66, 0.74), (0.74, 0.58, 0.46), (0.56, 0.58, 0.60), (0.80, 0.78, 0.72),
    (0.64, 0.46, 0.38), (0.70, 0.68, 0.56), (0.80, 0.62, 0.40), (0.52, 0.62, 0.66),
]


def build_city(seed=3, x_range=(-7400, 7400), y_range=(3500, 7400)):
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    col_layer = bm.faces.layers.float_color.new('bcol')
    roof_layer = bm.faces.layers.int.new('roof')
    y = y_range[0]
    n = 0
    while y < y_range[1]:
        row_dy = rng.uniform(95, 170)
        x = x_range[0] + rng.uniform(0, 60)
        while x < x_range[1]:
            kind = rng.random()
            if kind < 0.55:   # пятиэтажка/девятиэтажка-«пластина»
                w, d = rng.uniform(45, 95), rng.uniform(11, 14)
                floors = rng.choice([5, 5, 5, 9, 9, 12])
            elif kind < 0.8:  # точечный дом
                w, d = rng.uniform(16, 24), rng.uniform(16, 22)
                floors = rng.choice([9, 12, 14, 16])
            else:             # низкие постройки
                w, d = rng.uniform(15, 40), rng.uniform(12, 25)
                floors = rng.choice([1, 2, 3])
            gap = rng.uniform(30, 90)
            if rng.random() < 0.38 + 0.25 * fbm(np.array([x / 900]), np.array([y / 900]), octaves=3)[0]:  # двор, сквер, сопка
                x += w + gap
                continue
            cx = x + w / 2
            cy = y + rng.uniform(-15, 15)
            gz = float(ground_h(np.array([cx]), np.array([cy]))[0])
            if gz < 2.5:
                x += w + gap
                continue
            hgt = floors * 2.9 + 0.8
            ang = rng.choice([0.0, 0.0, rng.uniform(-0.35, 0.35)])
            if rng.random() < 0.3:
                ang += math.pi / 2
            colr = PALETTE[rng.integers(len(PALETTE))]
            res = bmesh.ops.create_cube(bm, size=1.0)
            verts = res['verts']
            ca, sa = math.cos(ang), math.sin(ang)
            for v in verts:
                lx, ly, lz = v.co.x * w, v.co.y * d, (v.co.z + 0.5) * hgt
                v.co.x = cx + lx * ca - ly * sa
                v.co.y = cy + lx * sa + ly * ca
                v.co.z = gz - 3 + lz + 3 * (v.co.z > 0)
            faces = {f for v in verts for f in v.link_faces}
            for f in faces:
                f[col_layer] = (*colr, 1.0)
                f[roof_layer] = 1 if f.normal.z > 0.5 else 0
            n += 1
            x += w + gap
        y += row_dy
    me = bpy.data.meshes.new('City')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new('City', me)
    bpy.context.scene.collection.objects.link(ob)
    print('buildings', n)
    return ob


def build_trees(seed=5, count=16000, x_range=(-8000, 8000), y_range=(3450, 8600)):
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    base = bmesh.new()
    bmesh.ops.create_icosphere(base, subdivisions=1, radius=1.0)
    proto = [v.co.copy() for v in base.verts]
    proto_faces = [[v.index for v in f.verts] for f in base.faces]
    base.free()
    xs = rng.uniform(*x_range, count)
    ys = rng.uniform(*y_range, count)
    keep = fbm(xs / 450, ys / 450, octaves=3) > -0.12
    xs, ys = xs[keep], ys[keep]
    gz = ground_h(xs, ys)
    m = 0
    for x, y, z in zip(xs, ys, gz):
        if z < 3:
            continue
        r = rng.uniform(5.5, 10.0)
        hz = r * rng.uniform(1.1, 1.8)
        vs = [bm.verts.new((x + p.x * r, y + p.y * r, z + hz * 0.55 + p.z * hz)) for p in proto]
        for f in proto_faces:
            bm.faces.new([vs[i] for i in f])
        m += 1
    me = bpy.data.meshes.new('Trees')
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new('Trees', me)
    bpy.context.scene.collection.objects.link(ob)
    print('trees', m)
    return ob
