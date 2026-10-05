"""Стройка для правого края первого экрана: каркас дома, кран, забор, поддоны."""
import sys, math, time
sys.path.insert(0, '.')
import bpy, bmesh
import numpy as np
from mathutils import Vector
from b3d import reset, node, principled, assign, render, look_at
from parts import box, strut, lattice_mast, lattice_jib, to_object, bevel

ARGS = dict(a.split('=') for a in sys.argv[sys.argv.index('--') + 1:]) if '--' in sys.argv else {}
W = int(ARGS.get('w', 400)); H = int(ARGS.get('h', 460))
SAMPLES = int(ARGS.get('s', 16))
OUT = ARGS.get('out', 'out/site.png')
SUN_EL = float(ARGS.get('el', 26)); SUN_AZ = float(ARGS.get('az', 255))
sc = reset(samples=SAMPLES, res=(W, H), transparent=True, view='Standard', look='None')
rng = np.random.default_rng(11)

# --- Свет: то же солнце и небо, что на фоне ---
SKY_STOPS = [(0.00, (0.66, 0.77, 0.92)), (0.06, (0.50, 0.66, 0.90)), (0.22, (0.27, 0.46, 0.84)),
             (0.55, (0.12, 0.29, 0.72)), (1.00, (0.07, 0.20, 0.60))]
world = bpy.data.worlds.new('Sky'); sc.world = world; world.use_nodes = True
nt = world.node_tree; bg = nt.nodes['Background']
tc = node(nt, 'ShaderNodeTexCoord', (-900, 0))
sep = node(nt, 'ShaderNodeSeparateXYZ', (-700, 0)); nt.links.new(tc.outputs['Generated'], sep.inputs[0])
ramp = node(nt, 'ShaderNodeValToRGB', (-500, 0))
el = ramp.color_ramp.elements
el[0].position, el[0].color = 0.0, (*SKY_STOPS[0][1], 1)
el[1].position, el[1].color = 1.0, (*SKY_STOPS[-1][1], 1)
for pos, col in SKY_STOPS[1:-1]:
    e = el.new(pos); e.color = (*col, 1)
nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = float(ARGS.get('sky', 0.5))
az, elv = math.radians(SUN_AZ), math.radians(SUN_EL)
S = Vector((math.sin(az) * math.cos(elv), math.cos(az) * math.cos(elv), math.sin(elv)))
sd = bpy.data.lights.new('Sun', 'SUN'); sd.energy = float(ARGS.get('sun', 5.0)); sd.angle = math.radians(0.8)
sd.color = (1.0, 0.96, 0.9)
sun = bpy.data.objects.new('Sun', sd); sun.rotation_euler = S.to_track_quat('Z', 'Y').to_euler()
sc.collection.objects.link(sun)


# --- Материалы ---
def facade_uv(t, loc=(-1200, -300)):
    """(u, v) по стене: u вдоль стены, v = z."""
    g = node(t, 'ShaderNodeNewGeometry', loc)
    p = node(t, 'ShaderNodeSeparateXYZ', (loc[0] + 200, loc[1])); t.links.new(g.outputs['Position'], p.inputs[0])
    n = node(t, 'ShaderNodeSeparateXYZ', (loc[0] + 200, loc[1] - 200)); t.links.new(g.outputs['Normal'], n.inputs[0])
    ax = node(t, 'ShaderNodeMath', (loc[0] + 400, loc[1] - 200), operation='ABSOLUTE'); t.links.new(n.outputs['X'], ax.inputs[0])
    ay = node(t, 'ShaderNodeMath', (loc[0] + 400, loc[1] - 300), operation='ABSOLUTE'); t.links.new(n.outputs['Y'], ay.inputs[0])
    m1 = node(t, 'ShaderNodeMath', (loc[0] + 550, loc[1]), operation='MULTIPLY'); t.links.new(p.outputs['X'], m1.inputs[0]); t.links.new(ay.outputs[0], m1.inputs[1])
    m2 = node(t, 'ShaderNodeMath', (loc[0] + 550, loc[1] - 150), operation='MULTIPLY'); t.links.new(p.outputs['Y'], m2.inputs[0]); t.links.new(ax.outputs[0], m2.inputs[1])
    u = node(t, 'ShaderNodeMath', (loc[0] + 700, loc[1]), operation='ADD'); t.links.new(m1.outputs[0], u.inputs[0]); t.links.new(m2.outputs[0], u.inputs[1])
    cmb = node(t, 'ShaderNodeCombineXYZ', (loc[0] + 850, loc[1])); t.links.new(u.outputs[0], cmb.inputs['X']); t.links.new(p.outputs['Z'], cmb.inputs['Y'])
    return cmb.outputs['Vector']


def mat_noise(name, base, var, scale=2.0, rough=0.85, bump=0.15, bump_scale=30.0):
    m = principled(name, base, rough)
    t = m.node_tree; p = t.nodes['Principled BSDF']
    tcn = node(t, 'ShaderNodeTexCoord', (-900, 0))
    nz = node(t, 'ShaderNodeTexNoise', (-700, 0)); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 6
    t.links.new(tcn.outputs['Object'], nz.inputs['Vector'])
    r = node(t, 'ShaderNodeValToRGB', (-450, 0))
    r.color_ramp.elements[0].color = (*base, 1); r.color_ramp.elements[1].color = (*var, 1)
    t.links.new(nz.outputs['Fac'], r.inputs['Fac']); t.links.new(r.outputs['Color'], p.inputs['Base Color'])
    if bump:
        nb = node(t, 'ShaderNodeTexNoise', (-700, -300)); nb.inputs['Scale'].default_value = bump_scale; nb.inputs['Detail'].default_value = 8
        t.links.new(tcn.outputs['Object'], nb.inputs['Vector'])
        b = node(t, 'ShaderNodeBump', (-300, -300)); b.inputs['Strength'].default_value = bump
        t.links.new(nb.outputs['Fac'], b.inputs['Height']); t.links.new(b.outputs['Normal'], p.inputs['Normal'])
    return m


def mat_brickwork(name, brick, mortar, bw, bh, mortar_size=0.012, rough=0.85):
    m = principled(name, brick, rough)
    t = m.node_tree; p = t.nodes['Principled BSDF']
    uv = facade_uv(t)
    bt = node(t, 'ShaderNodeTexBrick', (-200, 100))
    bt.inputs['Color1'].default_value = (*brick, 1)
    bt.inputs['Color2'].default_value = (*[c * 0.85 for c in brick], 1)
    bt.inputs['Mortar'].default_value = (*mortar, 1)
    bt.inputs['Scale'].default_value = 1.0
    bt.inputs['Mortar Size'].default_value = mortar_size
    bt.inputs['Brick Width'].default_value = bw
    bt.inputs['Row Height'].default_value = bh
    t.links.new(uv, bt.inputs['Vector'])
    t.links.new(bt.outputs['Color'], p.inputs['Base Color'])
    b = node(t, 'ShaderNodeBump', (0, -200)); b.inputs['Strength'].default_value = 0.3; b.invert = True
    t.links.new(bt.outputs['Fac'], b.inputs['Height']); t.links.new(b.outputs['Normal'], p.inputs['Normal'])
    return m


M_CONC = mat_noise('Concrete', (0.40, 0.40, 0.39), (0.52, 0.51, 0.49), 1.2, 0.9, 0.12, 25)
M_BLOCK = mat_brickwork('Aerated', (0.74, 0.73, 0.70), (0.60, 0.59, 0.57), 0.6, 0.25, 0.006)
M_DARK = principled('Interior', (0.05, 0.05, 0.05), 0.9)
M_CRANE = principled('Crane', (0.80, 0.56, 0.03), 0.42, 0.15)
M_WHITE = principled('Cab', (0.82, 0.83, 0.84), 0.35)
M_GLASS = principled('CabGlass', (0.05, 0.08, 0.12), 0.05)
M_FORM = mat_noise('Formwork', (0.72, 0.50, 0.06), (0.62, 0.40, 0.04), 3, 0.7, 0.05)
M_FENCE = principled('Fence', (0.02, 0.07, 0.42), 0.35, 0.3)
ft = M_FENCE.node_tree; fp = ft.nodes['Principled BSDF']
fw = node(ft, 'ShaderNodeTexWave', (-500, -200)); fw.wave_type = 'BANDS'; fw.bands_direction = 'X'
fw.inputs['Scale'].default_value = 6.0; fw.inputs['Distortion'].default_value = 0
ftc = node(ft, 'ShaderNodeTexCoord', (-700, -200)); ft.links.new(ftc.outputs['Object'], fw.inputs['Vector'])
fb = node(ft, 'ShaderNodeBump', (-250, -200)); fb.inputs['Strength'].default_value = 0.6
ft.links.new(fw.outputs['Fac'], fb.inputs['Height']); ft.links.new(fb.outputs['Normal'], fp.inputs['Normal'])
M_GROUND = mat_noise('Dirt', (0.10, 0.085, 0.07), (0.24, 0.21, 0.17), 0.6, 0.95, 0.5, 6)
M_WOOD = mat_noise('PalletWood', (0.46, 0.34, 0.21), (0.58, 0.45, 0.30), 6, 0.8, 0.1, 40)
M_LUMBER = mat_noise('Lumber', (0.66, 0.50, 0.31), (0.78, 0.62, 0.42), 4, 0.75, 0.06, 60)
M_BRICK = mat_brickwork('Brick', (0.48, 0.13, 0.06), (0.62, 0.58, 0.52), 0.25, 0.075, 0.010)
M_BAG = mat_noise('Bag', (0.64, 0.62, 0.57), (0.72, 0.70, 0.66), 8, 0.9, 0.2, 30)
M_FILM = principled('Film', (0.9, 0.92, 0.95), 0.18, 0.0, **{'Transmission Weight': 0.85, 'IOR': 1.35})
M_STEEL = principled('Steel', (0.35, 0.33, 0.30), 0.5, 0.8)

# --- Земля ---
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
gnd = bpy.context.object; gnd.scale = (400, 400, 1); assign(gnd, M_GROUND)

# --- Каркас дома ---
BW, BD, FL, NF = 26.0, 14.0, 3.0, 8
xs = [-13.0, -6.5, 0.0, 6.5, 13.0]; ys = [-7.0, 0.0, 7.0]
bm = bmesh.new()
MATS = [M_CONC, M_BLOCK, M_DARK, M_FORM, M_STEEL]
for k in range(NF):
    z0 = k * FL
    full = k < 7
    # колонны этажа
    if k < NF - 1:
        for x in xs:
            for y in ys:
                box(bm, (x, y, z0 + FL / 2), (0.45, 0.45, FL), 0, 0)
    else:  # верх: недостроенные колонны с арматурой и опалубкой
        for x in xs[:3]:
            for y in ys:
                box(bm, (x, y, z0 + 0.6), (0.45, 0.45, 1.2), 0, 0)
                for dx in (-0.15, 0.15):
                    for dy in (-0.15, 0.15):
                        strut(bm, (x + dx, y + dy, z0 + 1.2), (x + dx, y + dy, z0 + 2.6), 0.03, 4)
        for x in xs[3:]:
            for y in ys[:2]:
                box(bm, (x, y, z0 + FL / 2), (0.75, 0.75, FL), 0, 3)  # опалубка колонн
    # перекрытие над этажом
    if k < NF - 1:
        span = BW if k < 6 else BW * 0.62
        cx = 0 if k < 6 else -BW / 2 + span / 2
        box(bm, (cx, 0, z0 + FL), (span + 0.6, BD + 0.6, 0.24), 0, 0)
    # стены из газоблока с проёмами — нижние пять этажей, шестой начат
    if k < 4:
        for side in ('front', 'left'):
            bays = list(zip(xs[:-1], xs[1:])) if side == 'front' else list(zip(ys[:-1], ys[1:]))
            if k == 3:
                bays = bays[:2] if side == 'front' else bays[:1]
            for a, b in bays:
                L = b - a - 0.45
                mid = (a + b) / 2
                win = 2.4 if side == 'front' else 2.0
                pier = (L - win) / 2
                pieces = [  # (смещение вдоль стены, ширина, z низа, высота)
                    (0, L, 0.24, 0.66),
                    (0, L, 2.45, FL - 2.45),
                    (-(win / 2 + pier / 2), pier, 0.9, 1.55),
                    ((win / 2 + pier / 2), pier, 0.9, 1.55),
                ]
                for off, wdt, zb, hh in pieces:
                    if hh <= 0:
                        continue
                    if side == 'front':
                        box(bm, (mid + off, -7.0, z0 + zb + hh / 2), (wdt, 0.3, hh), 0, 1)
                    else:
                        box(bm, (-13.0, mid + off, z0 + zb + hh / 2), (0.3, wdt, hh), 0, 1)
        # тёмная глубина за проёмами
        box(bm, (0, 0.5, z0 + 1.6), (BW - 1.6, BD - 2.6, FL - 0.4), 0, 2)
bld = to_object(bm, 'Building', MATS)

# леса у левого угла
bm = bmesh.new()
for i, x in enumerate(np.arange(-13.5, -2, 2.0)):
    strut(bm, (x, -8.6, 0), (x, -8.6, 13.5), 0.05, 0)
    strut(bm, (x, -9.8, 0), (x, -9.8, 13.5), 0.05, 0)
for z in np.arange(1.0, 13.6, 2.0):
    strut(bm, (-13.6, -8.6, z), (-2.0, -8.6, z), 0.045, 0)
    strut(bm, (-13.6, -9.8, z), (-2.0, -9.8, z), 0.045, 0)
    box(bm, (-7.8, -9.2, z + 0.03), (11.6, 1.2, 0.05), 0, 1)
scaf = to_object(bm, 'Scaffold', [M_STEEL, M_WOOD])

# --- Кран: башня слева от дома, стрела развёрнута над крышей ---
MX, MY, MH = -21.0, 9.0, 46.0
SLEW = math.radians(float(ARGS.get('slew', 24)))   # куда смотрит стрела: от +X к +Y
bm = bmesh.new()
lattice_mast(bm, (MX, MY, 0), 1.7, MH, 1.7, 0.16, 0.07, 0)
crane = to_object(bm, 'Mast', [M_CRANE, M_WHITE, M_GLASS, M_STEEL, M_CONC])
# поворотная часть строится вокруг оси башни и поворачивается целиком
bm = bmesh.new()
box(bm, (0, 0, MH + 0.6), (2.2, 2.2, 1.2), 0, 0)
lattice_jib(bm, (1.1, 0, MH + 1.2), 40.0, +1, 1.3, 1.6, 2.0, 0.11, 0.05, 0)
lattice_jib(bm, (-1.1, 0, MH + 1.2), 13.0, -1, 1.6, 0.9, 2.0, 0.12, 0.05, 0)
apex = (0, 0, MH + 7.0)
for c in ((-0.8, -0.8), (0.8, -0.8), (0.8, 0.8), (-0.8, 0.8)):
    strut(bm, (c[0], c[1], MH + 1.2), apex, 0.1, 0)
strut(bm, apex, (28.0, 0, MH + 2.8), 0.035, 3)
strut(bm, apex, (-13.0, 0, MH + 2.1), 0.035, 3)
box(bm, (1.6, -1.2, MH - 0.6), (2.0, 1.6, 2.2), 0, 1)        # кабина
box(bm, (2.62, -1.2, MH - 0.4), (0.04, 1.4, 1.2), 0, 2)
for i in range(4):                                            # противовесы
    box(bm, (-9.0 - i * 1.0, 0, MH + 0.2), (0.9, 2.2, 2.2), 0, 4)
TX = 22.0                                                     # каретка, трос, груз
box(bm, (TX, 0, MH + 0.9), (1.2, 1.4, 0.5), 0, 0)
strut(bm, (TX, -0.15, MH + 0.7), (TX, -0.15, 26.0), 0.025, 3)
strut(bm, (TX, 0.15, MH + 0.7), (TX, 0.15, 26.0), 0.025, 3)
box(bm, (TX, 0, 25.6), (0.5, 0.6, 0.8), 0, 0)
for dx in (-0.55, 0.55):
    for dy in (-0.5, 0.5):
        strut(bm, (TX, 0, 25.2), (TX + dx, dy, 23.3), 0.015, 3)
top = to_object(bm, 'CraneTop', [M_CRANE, M_WHITE, M_GLASS, M_STEEL, M_CONC])
top.location = (MX, MY, 0); top.rotation_euler = (0, 0, SLEW)
bm = bmesh.new()
box(bm, (TX, 0, 22.4), (1.2, 1.0, 1.0), 0, 0)
box(bm, (TX, 0, 21.83), (1.2, 1.0, 0.14), 0, 1)
load = to_object(bm, 'Load', [M_BRICK, M_WOOD])
load.location = (MX, MY, 0); load.rotation_euler = (0, 0, SLEW)

# --- Забор из профлиста ---
bm = bmesh.new()
box(bm, (-4.0, -15.0, 1.25), (54.0, 0.06, 2.5), 0, 0)
for x in np.arange(-31.0, 23.5, 3.0):
    box(bm, (x, -15.1, 1.3), (0.08, 0.08, 2.6), 0, 1)
fence = to_object(bm, 'Fence', [M_FENCE, M_STEEL])

# --- Поддоны на переднем плане ---
def pallet(bm, cx, cy, rot=0.0):
    for i in range(3):
        box(bm, (cx, cy + (i - 1) * 0.45, 0.05), (1.2, 0.1, 0.1), rot, 0)
    for i in range(5):
        box(bm, (cx + (i - 2) * 0.27, cy, 0.125), (0.1, 1.0, 0.025), rot, 0)

bm = bmesh.new(); pallet(bm, -15.0, -33.0); pallet(bm, -12.6, -34.4); pallet(bm, -17.4, -31.0); pallet(bm, -10.0, -32.4)
pal = to_object(bm, 'Pallets', [M_WOOD])
bm = bmesh.new()
box(bm, (-15.0, -33.0, 0.14 + 0.6), (1.2, 1.0, 1.2), 0, 0)
box(bm, (-17.4, -31.0, 0.14 + 0.6), (1.2, 1.0, 1.2), 0, 0)
blocks = to_object(bm, 'Blocks', [M_BLOCK]); bevel(blocks, 0.01)
bm = bmesh.new(); box(bm, (-15.0, -33.0, 0.14 + 0.62), (1.24, 1.04, 1.25), 0, 0)
film = to_object(bm, 'Film', [M_FILM]); bevel(film, 0.05, 3)
bm = bmesh.new(); box(bm, (-12.6, -34.4, 0.14 + 0.5), (1.0, 0.98, 1.0), 0, 0)
bricks = to_object(bm, 'Bricks', [M_BRICK]); bevel(bricks, 0.005)
bm = bmesh.new()
for row in range(3):
    for i in range(3):
        box(bm, (-10.0 + (i - 1) * 0.38, -32.4, 0.14 + 0.07 + row * 0.13), (0.36, 0.58, 0.12), 0.0, 0)
bags = to_object(bm, 'Bags', [M_BAG]); bevel(bags, 0.04, 3)
bm = bmesh.new()
for layer in range(5):
    z = 0.12 + layer * 0.17
    for yy in (-2.2, 0.0, 2.2):
        box(bm, (0.0, yy, z - 0.07), (1.3, 0.08, 0.06), 0, 1)
    for i in range(7):
        box(bm, ((i - 3) * 0.17, 0.0, z), (0.15, 6.0, 0.05), (rng.random() - 0.5) * 0.01, 0)
lumber = to_object(bm, 'Lumber', [M_LUMBER, M_WOOD])
lumber.location = (-6.0, -30.0, 0.0); lumber.rotation_euler = (0, 0, 1.15)

# --- Ближние поддоны: правый нижний угол кадра ---
bm = bmesh.new(); pallet(bm, -22.6, -40.2, 0.35); pallet(bm, -21.2, -38.8, 0.35); pallet(bm, -23.9, -38.6, 0.35)
pal2 = to_object(bm, 'Pallets2', [M_WOOD])
bm = bmesh.new(); box(bm, (-22.6, -40.2, 0.14 + 0.5), (1.0, 0.98, 1.0), 0.35, 0)
bricks2 = to_object(bm, 'Bricks2', [M_BRICK]); bevel(bricks2, 0.005)
bm = bmesh.new(); box(bm, (-21.2, -38.8, 0.14 + 0.6), (1.2, 1.0, 1.2), 0.35, 0)
blocks2 = to_object(bm, 'Blocks2', [M_BLOCK]); bevel(blocks2, 0.01)
bm = bmesh.new(); box(bm, (-21.2, -38.8, 0.14 + 0.62), (1.24, 1.04, 1.25), 0.35, 0)
film2 = to_object(bm, 'Film2', [M_FILM]); bevel(film2, 0.05, 3)
bm = bmesh.new()
for row in range(4):
    for i in range(2):
        for j in range(2):
            ox, oy = (i - 0.5) * 0.6, (j - 0.5) * 0.38
            ca, sa = math.cos(0.35), math.sin(0.35)
            box(bm, (-23.9 + ox * ca - oy * sa, -38.6 + ox * sa + oy * ca, 0.14 + 0.07 + row * 0.13), (0.58, 0.36, 0.12), 0.35, 0)
bags2 = to_object(bm, 'Bags2', [M_BAG]); bevel(bags2, 0.045, 3)

# --- Камера ---
cd = bpy.data.cameras.new('Cam'); cd.sensor_width = 36; cd.lens = float(ARGS.get('lens', 26))
cd.sensor_fit = 'AUTO'; cd.clip_end = 2000
cam = bpy.data.objects.new('Cam', cd)
cam.location = (float(ARGS.get('cx', -28)), float(ARGS.get('cy', -46)), float(ARGS.get('cz', 1.7)))
sc.collection.objects.link(cam); sc.camera = cam
look_at(cam, (float(ARGS.get('tx', -8)), 0, float(ARGS.get('tz', 19))))

t0 = time.time()
render(OUT)
print('render', time.time() - t0)
