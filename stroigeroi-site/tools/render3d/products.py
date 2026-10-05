"""Предметная съёмка для плиток разделов и карточек: студийный свет, тень на прозрачном."""
import sys, math, time
sys.path.insert(0, '.')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from b3d import reset, node, principled, assign, render, look_at
from parts import box, strut, to_object, bevel

ARGS = dict(a.split('=') for a in sys.argv[sys.argv.index('--') + 1:]) if '--' in sys.argv else {}
NAME = ARGS.get('name', 'bricks')
RES = int(ARGS.get('res', 512))
SAMPLES = int(ARGS.get('s', 64))
OUT = ARGS.get('out', f'out/prod-{NAME}.png')
rng = np.random.default_rng(5)

sc = reset(samples=SAMPLES, res=(RES, RES), transparent=True, view='AgX', look=ARGS.get('look', 'AgX - Punchy'),
           exposure=float(ARGS.get('exp', 0.0)))
sc.cycles.max_bounces = 10
sc.cycles.glossy_bounces = 6


# ---------- свет ----------
def studio(world_strength=0.4):
    w = bpy.data.worlds.new('Studio'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    tc = node(nt, 'ShaderNodeTexCoord', (-900, 0))
    sep = node(nt, 'ShaderNodeSeparateXYZ', (-700, 0)); nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    r = node(nt, 'ShaderNodeValToRGB', (-500, 0))
    r.color_ramp.elements[0].position = 0.40; r.color_ramp.elements[0].color = (0.02, 0.02, 0.025, 1)
    r.color_ramp.elements[1].position = 0.92; r.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    e = r.color_ramp.elements.new(0.56); e.color = (0.10, 0.105, 0.115, 1)
    mr = node(nt, 'ShaderNodeMapRange', (-600, -150)); nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    mr.inputs['From Min'].default_value = -1; mr.inputs['From Max'].default_value = 1
    nt.links.new(mr.outputs['Result'], r.inputs['Fac'])
    nt.links.new(r.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = world_strength

    def area(name, loc, target, size, energy, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'AREA'); d.size = size; d.energy = energy; d.color = color
        d.shape = 'DISK'
        o = bpy.data.objects.new(name, d); o.location = loc; sc.collection.objects.link(o)
        look_at(o, target)
        return o
    s = float(ARGS.get('light', 1.0))
    area('Key', (-1.1, -1.3, 2.9), (0, 0, 0.05), 1.6, 130 * s, (1.0, 0.97, 0.93))
    area('Fill', (2.2, -1.2, 1.0), (0, 0, 0.05), 2.0, 35 * s, (0.92, 0.95, 1.0))
    area('Rim', (0.8, 2.2, 1.8), (0, 0, 0.05), 1.2, 90 * s, (1.0, 1.0, 1.0))
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    g = bpy.context.object; g.is_shadow_catcher = True; g.name = 'ShadowCatcher'


def frame_camera(elev=24.0, azim=-32.0, lens=85.0, margin=1.2, target_z=None, shift=(0.0, 0.0), fill=None):
    """Камера смотрит на предметы под углом и подбирает расстояние и сдвиг так,
    чтобы проекция занимала долю кадра fill по большей стороне."""
    from bpy_extras.object_utils import world_to_camera_view
    fill = float(ARGS.get('fill', fill or 0.84))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for ob in sc.objects:
        if ob.type == 'MESH' and ob.name != 'ShadowCatcher' and not ob.hide_render:
            eo = ob.evaluated_get(dg)
            for c in eo.bound_box:
                pts.append(eo.matrix_world @ Vector(c))
    P = np.array([[p.x, p.y, p.z] for p in pts])
    lo, hi = P.min(0), P.max(0)
    ctr = Vector(((lo + hi) / 2).tolist())
    rad = float(np.linalg.norm(hi - lo) / 2)
    cd = bpy.data.cameras.new('Cam'); cd.lens = lens; cd.sensor_width = 36
    cd.clip_start = 0.001; cd.clip_end = 100
    cam = bpy.data.objects.new('Cam', cd)
    sc.collection.objects.link(cam); sc.camera = cam
    e, a = math.radians(elev), math.radians(azim)
    dirv = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    fov = 2 * math.atan(18 / lens)
    dist = rad * margin / math.sin(fov / 2)
    for _ in range(6):
        cam.location = ctr + dirv * dist
        look_at(cam, ctr)
        bpy.context.view_layer.update()
        uv = np.array([world_to_camera_view(sc, cam, p)[:2] for p in pts])
        umin, vmin = uv.min(0); umax, vmax = uv.max(0)
        size = max(umax - umin, vmax - vmin)
        cd.shift_x += ((umin + umax) / 2 - 0.5)
        cd.shift_y += ((vmin + vmax) / 2 - 0.5) + float(ARGS.get('lift', 0.0))
        dist *= size / fill
    return cam


# ---------- материалы ----------
def mat_var(name, base, var, scale, rough, bump=0.0, bump_scale=200.0, metal=0.0, coat=0.0):
    m = principled(name, base, rough, metal)
    t = m.node_tree; p = t.nodes['Principled BSDF']
    if coat:
        p.inputs['Coat Weight'].default_value = coat
    tc = node(t, 'ShaderNodeTexCoord', (-900, 0))
    nz = node(t, 'ShaderNodeTexNoise', (-700, 0)); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 5
    t.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    r = node(t, 'ShaderNodeValToRGB', (-450, 0))
    r.color_ramp.elements[0].color = (*base, 1); r.color_ramp.elements[1].color = (*var, 1)
    t.links.new(nz.outputs['Fac'], r.inputs['Fac']); t.links.new(r.outputs['Color'], p.inputs['Base Color'])
    if bump:
        nb = node(t, 'ShaderNodeTexNoise', (-700, -300)); nb.inputs['Scale'].default_value = bump_scale; nb.inputs['Detail'].default_value = 8
        t.links.new(tc.outputs['Object'], nb.inputs['Vector'])
        b = node(t, 'ShaderNodeBump', (-300, -300)); b.inputs['Strength'].default_value = bump
        t.links.new(nb.outputs['Fac'], b.inputs['Height']); t.links.new(b.outputs['Normal'], p.inputs['Normal'])
    return m


def mat_wood(name, base=(0.55, 0.36, 0.18), dark=(0.36, 0.21, 0.09), scale=6.0, rough=0.6, axis='X'):
    m = principled(name, base, rough)
    t = m.node_tree; p = t.nodes['Principled BSDF']
    tc = node(t, 'ShaderNodeTexCoord', (-1000, 0))
    mp = node(t, 'ShaderNodeMapping', (-850, 0))
    if axis == 'X':
        mp.inputs['Scale'].default_value = (0.15, 1.0, 1.0)
    elif axis == 'Y':
        mp.inputs['Scale'].default_value = (1.0, 0.15, 1.0)
    else:
        mp.inputs['Scale'].default_value = (1.0, 1.0, 0.15)
    t.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    wv = node(t, 'ShaderNodeTexWave', (-650, 0)); wv.wave_type = 'RINGS'
    wv.inputs['Scale'].default_value = scale; wv.inputs['Distortion'].default_value = 6; wv.inputs['Detail'].default_value = 3
    t.links.new(mp.outputs['Vector'], wv.inputs['Vector'])
    r = node(t, 'ShaderNodeValToRGB', (-400, 0))
    r.color_ramp.elements[0].color = (*dark, 1); r.color_ramp.elements[1].color = (*base, 1)
    r.color_ramp.elements[0].position = 0.25
    t.links.new(wv.outputs['Fac'], r.inputs['Fac']); t.links.new(r.outputs['Color'], p.inputs['Base Color'])
    return m


def obj_from_bm(bm, name, mats, smooth=False, bev=None, subsurf=0):
    ob = to_object(bm, name, mats)
    if smooth:
        for pl in ob.data.polygons:
            pl.use_smooth = True
    if bev:
        bevel(ob, *bev)
    if subsurf:
        md = ob.modifiers.new('Sub', 'SUBSURF'); md.levels = subsurf; md.render_levels = subsurf
    return ob


def cyl(bm, center, r, depth, segs=48, axis='Z', mat_index=0, r2=None):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r,
                                radius2=r if r2 is None else r2, depth=depth)
    rot = {'Z': Matrix.Identity(4), 'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Y': Matrix.Rotation(math.pi / 2, 4, 'X')}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ rot, verts=res['verts'])
    for f in {f for v in res['verts'] for f in v.link_faces}:
        f.material_index = mat_index
    return res['verts']


# ---------- предметы ----------
def model_bricks():
    """Стопка кирпичей пирамидкой."""
    BW, BD, BH = 0.25, 0.12, 0.065
    cols = [(0.52, 0.17, 0.08), (0.58, 0.20, 0.09), (0.47, 0.14, 0.07), (0.55, 0.22, 0.11)]
    mats = [mat_var(f'Brick{i}', c, tuple(min(1, x * 1.18) for x in c), 18, 0.88, 0.5, 90) for i, c in enumerate(cols)]
    bm = bmesh.new()
    gap = 0.004
    layout = [  # (слой, x, y, поворот)
        *[(0, (i - 1) * (BW + gap), (j - 0.5) * (BD * 2 + gap) / 2 * 1.0, 0.0) for i in range(3) for j in range(2)],
        *[(1, (i - 0.5) * (BW + gap), (j - 0.5) * (BD + gap), 0.0) for i in range(2) for j in range(2)],
        *[(2, 0.0, (j - 0.5) * (BD + gap), 0.0) for j in range(2)],
    ]
    for k, (layer, x, y, rot) in enumerate(layout):
        z = layer * (BH + gap) + BH / 2
        box(bm, (x, y, z), (BW, BD, BH), rot, int(rng.integers(len(mats))))
    # один кирпич лежит рядом под углом
    box(bm, (0.30, -0.20, BH / 2), (BW, BD, BH), 0.5, 1)
    ob = obj_from_bm(bm, 'Bricks', mats, bev=(0.006, 3))
    frame_camera(elev=26, azim=-30, lens=85, margin=1.15)


def model_socket():
    """Розетка и лампочка."""
    white = mat_var('PlasticWhite', (0.88, 0.88, 0.86), (0.92, 0.92, 0.90), 40, 0.32, coat=0.2)
    metal = principled('Contact', (0.85, 0.85, 0.86), 0.25, 1.0)
    dark = principled('Hole', (0.005, 0.005, 0.005), 0.8)
    # рамка
    bm = bmesh.new()
    box(bm, (0, 0, 0.006), (0.086, 0.086, 0.012), 0, 0)
    plate = obj_from_bm(bm, 'Plate', [white], bev=(0.006, 6))
    # гнездо: цилиндр с вырезом
    bm = bmesh.new()
    cyl(bm, (0, 0, 0.0135), 0.024, 0.003, 64, 'Z', 0)
    well = obj_from_bm(bm, 'Rim', [white], smooth=True, bev=(0.0012, 3))
    bm = bmesh.new()
    cyl(bm, (0, 0, 0.0128), 0.0215, 0.003, 64, 'Z', 0)
    face = obj_from_bm(bm, 'Face', [white], smooth=True)
    bm = bmesh.new()
    for dx in (-0.0095, 0.0095):
        cyl(bm, (dx, 0, 0.0142), 0.0022, 0.0012, 24, 'Z', 0)
    holes = obj_from_bm(bm, 'Holes', [dark], smooth=True)
    bm = bmesh.new()
    for dy in (-0.0195, 0.0195):
        box(bm, (0, dy, 0.0145), (0.008, 0.0028, 0.0016), 0, 0)
    clips = obj_from_bm(bm, 'Clips', [metal], bev=(0.0005, 2))
    for o in (plate, well, face, holes, clips):
        o.rotation_euler = (math.radians(78), 0, 0)
        o.location.z += 0.05
        o.location.y += 0.006
    # лампочка рядом
    glass = principled('Frosted', (0.97, 0.97, 0.96), 0.38, 0.0, **{'Transmission Weight': 0.25, 'IOR': 1.45, 'Coat Weight': 0.4})
    base_w = mat_var('BaseWhite', (0.9, 0.9, 0.88), (0.93, 0.93, 0.91), 30, 0.35)
    alu = principled('Alu', (0.80, 0.80, 0.80), 0.3, 1.0)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=0.03)
    bulb = obj_from_bm(bm, 'Bulb', [glass], smooth=True)
    bulb.location = (0.065, -0.035, 0.068)
    bm = bmesh.new()
    cyl(bm, (0, 0, 0), 0.019, 0.03, 48, 'Z', 0, r2=0.017)
    neck = obj_from_bm(bm, 'Neck', [base_w], smooth=True, bev=(0.002, 2))
    neck.location = (0.065, -0.035, 0.03)
    bm = bmesh.new()
    for i in range(5):
        cyl(bm, (0, 0, i * 0.0042), 0.0135 if i % 2 == 0 else 0.0125, 0.0042, 40, 'Z', 0)
    screw = obj_from_bm(bm, 'Screw', [alu], smooth=True)
    screw.location = (0.065, -0.035, -0.006)
    frame_camera(elev=22, azim=-26, lens=85, margin=1.08)


def model_bolts():
    """Болты, гайка и шайба."""
    steel = principled('Zinc', (0.78, 0.80, 0.84), 0.22, 1.0)
    t = steel.node_tree; p = t.nodes['Principled BSDF']
    tc = node(t, 'ShaderNodeTexCoord', (-900, -300))
    wv = node(t, 'ShaderNodeTexWave', (-700, -300)); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'
    wv.inputs['Scale'].default_value = 0.0; wv.inputs['Distortion'].default_value = 0
    nz = node(t, 'ShaderNodeTexNoise', (-700, -50)); nz.inputs['Scale'].default_value = 300
    b = node(t, 'ShaderNodeBump', (-300, -200)); b.inputs['Strength'].default_value = 0.08
    t.links.new(tc.outputs['Object'], nz.inputs['Vector']); t.links.new(nz.outputs['Fac'], b.inputs['Height'])
    t.links.new(b.outputs['Normal'], p.inputs['Normal'])
    thread = principled('Thread', (0.74, 0.76, 0.80), 0.28, 1.0)
    tt = thread.node_tree; tp = tt.nodes['Principled BSDF']
    ttc = node(tt, 'ShaderNodeTexCoord', (-900, -300))
    twv = node(tt, 'ShaderNodeTexWave', (-700, -300)); twv.wave_type = 'BANDS'; twv.bands_direction = 'Z'
    twv.inputs['Scale'].default_value = 1.0; twv.inputs['Distortion'].default_value = 0
    tmp = node(tt, 'ShaderNodeMapping', (-850, -300)); tmp.inputs['Scale'].default_value = (1, 1, 600)
    tt.links.new(ttc.outputs['Object'], tmp.inputs['Vector']); tt.links.new(tmp.outputs['Vector'], twv.inputs['Vector'])
    tb = node(tt, 'ShaderNodeBump', (-300, -300)); tb.inputs['Strength'].default_value = 0.9
    tt.links.new(twv.outputs['Fac'], tb.inputs['Height']); tt.links.new(tb.outputs['Normal'], tp.inputs['Normal'])

    def bolt(name, loc, rot, length=0.07):
        bm = bmesh.new()
        cyl(bm, (0, 0, 0.0045), 0.0125, 0.009, 6, 'Z', 0)
        head = obj_from_bm(bm, name + 'Head', [steel], bev=(0.0012, 2))
        bm = bmesh.new()
        cyl(bm, (0, 0, -length / 2), 0.0062, length, 40, 'Z', 0)
        sh = obj_from_bm(bm, name + 'Shank', [thread], smooth=True, bev=(0.0008, 2))
        for o in (head, sh):
            o.rotation_euler = rot
            o.location = loc
        return head, sh
    bolt('B1', (-0.02, 0.0, 0.012), (math.radians(90), 0, math.radians(20)))
    bolt('B2', (0.03, 0.03, 0.013), (math.radians(90), 0, math.radians(-35)), 0.055)
    # гайка
    bm = bmesh.new()
    cyl(bm, (0, 0, 0.005), 0.0115, 0.01, 6, 'Z', 0)
    nut = obj_from_bm(bm, 'Nut', [steel], bev=(0.001, 2))
    bm = bmesh.new(); cyl(bm, (0, 0, 0.005), 0.0062, 0.03, 40, 'Z', 0)
    hole = obj_from_bm(bm, 'NutHole', [steel]); hole.hide_render = True
    bo = nut.modifiers.new('Hole', 'BOOLEAN'); bo.object = hole; bo.operation = 'DIFFERENCE'
    nut.location = (0.045, -0.04, 0.0)
    # шайба
    bm = bmesh.new(); cyl(bm, (0, 0, 0.0008), 0.0125, 0.0016, 64, 'Z', 0)
    wsh = obj_from_bm(bm, 'Washer', [steel], smooth=True)
    bm = bmesh.new(); cyl(bm, (0, 0, 0.0008), 0.0065, 0.01, 40, 'Z', 0)
    wh = obj_from_bm(bm, 'WasherHole', [steel]); wh.hide_render = True
    bo = wsh.modifiers.new('Hole', 'BOOLEAN'); bo.object = wh; bo.operation = 'DIFFERENCE'
    wsh.location = (0.012, -0.055, 0.0); wh.location = wsh.location
    hole.location = nut.location
    frame_camera(elev=30, azim=-24, lens=85, margin=1.1)



def rounded_box(bm, center, size, rot=(0, 0, 0), mat_index=0):
    res = bmesh.ops.create_cube(bm, size=1.0)
    R = (Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X'))
    m = Matrix.Translation(Vector(center)) @ R @ Matrix.Diagonal((*size, 1.0))
    bmesh.ops.transform(bm, matrix=m, verts=res['verts'])
    for f in {f for v in res['verts'] for f in v.link_faces}:
        f.material_index = mat_index


def model_drill():
    """Аккумуляторная дрель-шуруповёрт: корпус синий, резина чёрная."""
    blue = mat_var('DrillBlue', (0.025, 0.11, 0.55), (0.03, 0.13, 0.62), 30, 0.38, coat=0.3)
    black = mat_var('Rubber', (0.018, 0.018, 0.02), (0.03, 0.03, 0.035), 60, 0.62, 0.15, 400)
    steel = principled('BitSteel', (0.62, 0.63, 0.65), 0.22, 1.0)
    grey = principled('Chuck', (0.06, 0.06, 0.065), 0.35, 0.6)
    # корпус двигателя
    bm = bmesh.new(); cyl(bm, (0.012, 0, 0.215), 0.036, 0.17, 48, 'X', 0)
    body = obj_from_bm(bm, 'Body', [blue], smooth=True, bev=(0.012, 6))
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=0.036)
    back = obj_from_bm(bm, 'Back', [black], smooth=True); back.location = (-0.07, 0, 0.215); back.scale = (0.55, 1, 1)
    bm = bmesh.new(); cyl(bm, (0.11, 0, 0.215), 0.032, 0.03, 36, 'X', 0)
    clutch = obj_from_bm(bm, 'Clutch', [black], smooth=True, bev=(0.004, 3))
    bm = bmesh.new(); cyl(bm, (0.15, 0, 0.215), 0.024, 0.05, 40, 'X', 0, r2=0.018)
    chuck = obj_from_bm(bm, 'Chuck', [grey], smooth=True, bev=(0.003, 3))
    bm = bmesh.new(); cyl(bm, (0.205, 0, 0.215), 0.0035, 0.06, 16, 'X', 0)
    bit = obj_from_bm(bm, 'Bit', [steel], smooth=True)
    # рукоять с резиновой накладкой
    bm = bmesh.new(); rounded_box(bm, (-0.012, 0, 0.11), (0.036, 0.042, 0.17), (0, math.radians(-12), 0), 0)
    handle = obj_from_bm(bm, 'Handle', [blue], bev=(0.014, 6), smooth=True)
    bm = bmesh.new(); rounded_box(bm, (-0.03, 0, 0.11), (0.016, 0.044, 0.15), (0, math.radians(-12), 0), 0)
    grip = obj_from_bm(bm, 'Grip', [black], bev=(0.007, 4), smooth=True)
    bm = bmesh.new(); rounded_box(bm, (0.018, 0, 0.165), (0.012, 0.016, 0.03), (0, math.radians(-12), 0), 0)
    trig = obj_from_bm(bm, 'Trigger', [black], bev=(0.004, 3), smooth=True)
    # аккумулятор
    bm = bmesh.new(); rounded_box(bm, (-0.005, 0, 0.03), (0.115, 0.08, 0.06), (0, 0, 0), 0)
    bat = obj_from_bm(bm, 'Battery', [black], bev=(0.01, 5), smooth=True)
    bm = bmesh.new(); rounded_box(bm, (-0.005, 0, 0.066), (0.1, 0.07, 0.016), (0, 0, 0), 0)
    bat2 = obj_from_bm(bm, 'BatteryTop', [blue], bev=(0.006, 4), smooth=True)
    frame_camera(elev=16, azim=-38, lens=85, margin=1.12)


def model_hammer():
    """Молоток стоит на головке, рядом рулетка."""
    wood = mat_wood('Ash', (0.72, 0.52, 0.30), (0.54, 0.36, 0.18), 8.0, 0.45, 'Z')
    steel = mat_var('HeadSteel', (0.22, 0.23, 0.25), (0.28, 0.29, 0.31), 80, 0.26, 0.05, 500, metal=1.0)
    face = principled('Polished', (0.85, 0.85, 0.87), 0.1, 1.0)
    yellow = mat_var('TapeYellow', (0.95, 0.62, 0.02), (0.98, 0.70, 0.05), 30, 0.35, coat=0.3)
    black = mat_var('TapeRubber', (0.02, 0.02, 0.022), (0.04, 0.04, 0.045), 60, 0.6)
    tape = principled('TapeBlade', (0.95, 0.80, 0.10), 0.3, 0.4)
    H = 0.034
    hp = []
    bm = bmesh.new(); rounded_box(bm, (0, 0.006, H / 2), (0.034, 0.074, H), (0, 0, 0), 0)
    hp.append(obj_from_bm(bm, 'Head', [steel], bev=(0.007, 4), smooth=True))
    bm = bmesh.new(); cyl(bm, (0, -0.05, H / 2), 0.0175, 0.034, 48, 'Y', 0)
    hp.append(obj_from_bm(bm, 'Poll', [steel], smooth=True, bev=(0.003, 3)))
    bm = bmesh.new(); cyl(bm, (0, -0.069, H / 2), 0.0168, 0.005, 48, 'Y', 0)
    hp.append(obj_from_bm(bm, 'Face', [face], smooth=True, bev=(0.0016, 2)))
    # гвоздодёр: два зуба по дуге, сечение сплющено
    for side in (-1, 1):
        cu = bpy.data.curves.new('ClawCurve', 'CURVE'); cu.dimensions = '3D'
        cu.bevel_depth = 0.0075; cu.bevel_resolution = 4; cu.use_fill_caps = True
        sp_ = cu.splines.new('POLY')
        arc = []
        for i in range(14):
            t = i / 13
            ang = t * 1.25
            r = 0.055
            arc.append(Vector((side * 0.0068, 0.04 + r * math.sin(ang), H / 2 + r * (1 - math.cos(ang)))))
        sp_.points.add(len(arc) - 1)
        for p, q in zip(sp_.points, arc):
            p.co = (q.x, q.y, q.z, 1)
        for k, p in enumerate(sp_.points):
            p.radius = 1.0 - 0.55 * (k / 13)
        co = bpy.data.objects.new('ClawC', cu); sc.collection.objects.link(co)
        co.scale = (1.0, 1.0, 1.0)
        cu.materials.append(steel)
        bpy.context.view_layer.update()
        me = bpy.data.meshes.new_from_object(co.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        bpy.data.objects.remove(co)
        cm_ = bpy.data.objects.new('Claw', me); sc.collection.objects.link(cm_)
        for p in me.polygons:
            p.use_smooth = True
        hp.append(cm_)
    bm = bmesh.new(); rounded_box(bm, (0, 0.004, H + 0.135), (0.028, 0.032, 0.27), (0, 0, 0), 0)
    hp.append(obj_from_bm(bm, 'Handle', [wood], bev=(0.011, 6), smooth=True))
    for o in hp:
        o.rotation_euler = (0, 0, math.radians(58))
    tp = []
    bm = bmesh.new(); rounded_box(bm, (0, 0, 0.021), (0.074, 0.074, 0.042), (0, 0, 0), 0)
    tp.append(obj_from_bm(bm, 'Case', [yellow], bev=(0.016, 6), smooth=True))
    bm = bmesh.new(); cyl(bm, (0, 0, 0.022), 0.026, 0.046, 48, 'Z', 0)
    tp.append(obj_from_bm(bm, 'Side', [black], smooth=True, bev=(0.003, 3)))
    bm = bmesh.new(); rounded_box(bm, (-0.075, 0, 0.004), (0.08, 0.019, 0.0016), (0, 0, 0), 0)
    tp.append(obj_from_bm(bm, 'Blade', [tape], bev=(0.0006, 2)))
    bm = bmesh.new(); rounded_box(bm, (-0.115, 0, 0.008), (0.002, 0.021, 0.012), (0, 0, 0), 0)
    tp.append(obj_from_bm(bm, 'Hook', [face], bev=(0.0005, 2)))
    for o in tp:
        o.location = (-0.115, -0.06, 0)
        o.rotation_euler = (0, 0, math.radians(-25))
    frame_camera(elev=20, azim=-30, lens=85)


def model_faucet():
    """Однорычажный смеситель, хром."""
    chrome = principled('Chrome', (0.96, 0.96, 0.97), 0.035, 1.0)
    dark = principled('Aerator', (0.05, 0.05, 0.05), 0.5, 0.5)
    bm = bmesh.new(); cyl(bm, (0, 0, 0.005), 0.03, 0.01, 64, 'Z', 0)
    base = obj_from_bm(bm, 'Base', [chrome], smooth=True, bev=(0.003, 4))
    bm = bmesh.new(); cyl(bm, (0, 0, 0.075), 0.024, 0.13, 64, 'Z', 0)
    body = obj_from_bm(bm, 'Body', [chrome], smooth=True, bev=(0.006, 5))
    bm = bmesh.new(); cyl(bm, (0, 0, 0.152), 0.021, 0.024, 64, 'Z', 0)
    cap = obj_from_bm(bm, 'Cap', [chrome], smooth=True, bev=(0.006, 5))
    # излив — изогнутая трубка
    cu = bpy.data.curves.new('SpoutCurve', 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = 0.0115; cu.bevel_resolution = 8; cu.use_fill_caps = True
    sp_ = cu.splines.new('POLY')
    P0, P1, P2 = Vector((0.012, 0, 0.116)), Vector((0.11, 0, 0.124)), Vector((0.128, 0, 0.084))
    pts = [P0 * (1 - t) ** 2 + P1 * (2 * (1 - t) * t) + P2 * (t * t) for t in [i / 23 for i in range(24)]]
    sp_.points.add(len(pts) - 1)
    for p, q in zip(sp_.points, pts):
        p.co = (q.x, q.y, q.z, 1)
    spo = bpy.data.objects.new('SpoutCurve', cu); sc.collection.objects.link(spo)
    cu.materials.append(chrome)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(spo.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(spo)
    spm = bpy.data.objects.new('Spout', me); sc.collection.objects.link(spm)
    for p in me.polygons:
        p.use_smooth = True
    bm = bmesh.new(); cyl(bm, (0.128, 0, 0.08), 0.0118, 0.012, 40, 'Z', 0)
    aer = obj_from_bm(bm, 'AeratorBody', [chrome], smooth=True, bev=(0.002, 3))
    bm = bmesh.new(); cyl(bm, (0.128, 0, 0.0736), 0.009, 0.0012, 32, 'Z', 0)
    aer2 = obj_from_bm(bm, 'Aerator', [dark], smooth=True)
    # рычаг
    bm = bmesh.new(); rounded_box(bm, (-0.03, 0, 0.172), (0.09, 0.016, 0.011), (0, math.radians(14), 0), 0)
    lev = obj_from_bm(bm, 'Lever', [chrome], bev=(0.005, 5), smooth=True)
    frame_camera(elev=18, azim=-40, lens=85, margin=1.1)


def model_radiator():
    """Алюминиевый секционный радиатор."""
    enamel = mat_var('Enamel', (0.86, 0.87, 0.88), (0.90, 0.91, 0.92), 20, 0.18, coat=0.5)
    chrome = principled('Valve', (0.92, 0.92, 0.93), 0.05, 1.0)
    shadow = principled('Inner', (0.30, 0.31, 0.32), 0.5)
    N, SW, gap = 7, 0.078, 0.004
    bm = bmesh.new()
    for i in range(N):
        x = (i - (N - 1) / 2) * (SW + gap)
        rounded_box(bm, (x, -0.035, 0.31), (SW, 0.012, 0.56), (0, 0, 0), 0)
        rounded_box(bm, (x, 0.0, 0.31), (SW * 0.55, 0.075, 0.54), (0, 0, 0), 0)
        rounded_box(bm, (x, 0.0, 0.07), (SW, 0.07, 0.05), (0, 0, 0), 0)
        rounded_box(bm, (x, 0.0, 0.55), (SW, 0.07, 0.05), (0, 0, 0), 0)
    rad = obj_from_bm(bm, 'Radiator', [enamel], bev=(0.006, 4), smooth=True)
    bm = bmesh.new()
    rounded_box(bm, (0, 0.004, 0.31), ((N - 1) * (SW + gap), 0.05, 0.5), (0, 0, 0), 0)
    inner = obj_from_bm(bm, 'Inner', [shadow])
    xr = (N / 2) * (SW + gap)
    bm = bmesh.new(); cyl(bm, (xr + 0.012, 0, 0.07), 0.014, 0.024, 32, 'X', 0)
    cyl(bm, (xr + 0.034, 0, 0.07), 0.011, 0.02, 6, 'X', 0)
    cyl(bm, (xr + 0.012, 0, 0.55), 0.012, 0.024, 32, 'X', 0)
    v = obj_from_bm(bm, 'Valves', [chrome], smooth=True, bev=(0.002, 2))
    bm = bmesh.new(); cyl(bm, (-xr - 0.01, 0, 0.55), 0.012, 0.02, 32, 'X', 0)
    cyl(bm, (-xr - 0.01, 0, 0.07), 0.012, 0.02, 32, 'X', 0)
    v2 = obj_from_bm(bm, 'Plugs', [chrome], smooth=True, bev=(0.002, 2))
    frame_camera(elev=14, azim=-34, lens=85, margin=1.06)


def model_wheelbarrow():
    """Садовая тачка."""
    green = mat_var('Green', (0.03, 0.30, 0.07), (0.04, 0.36, 0.09), 20, 0.3, metal=0.15, coat=0.3)
    rubber = mat_var('Tyre', (0.02, 0.02, 0.022), (0.035, 0.035, 0.04), 80, 0.7, 0.3, 300)
    steel = principled('Frame', (0.55, 0.56, 0.58), 0.3, 1.0)
    rim = principled('Rim', (0.75, 0.75, 0.76), 0.25, 1.0)
    # корыто: усечённая пирамида без крышки
    bm = bmesh.new()
    top = [(-0.45, -0.31), (0.47, -0.31), (0.47, 0.31), (-0.45, 0.31)]
    bot = [(-0.25, -0.19), (0.30, -0.19), (0.30, 0.19), (-0.25, 0.19)]
    zt, zb = 0.66, 0.40
    vt = [bm.verts.new((x, y, zt)) for x, y in top]
    vb = [bm.verts.new((x, y, zb)) for x, y in bot]
    bm.faces.new(vb[::-1])
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([vb[i], vb[j], vt[j], vt[i]])
    tray = obj_from_bm(bm, 'Tray', [green])
    so = tray.modifiers.new('Solid', 'SOLIDIFY'); so.thickness = 0.012
    bevel(tray, 0.05, 6)
    sub = tray.modifiers.new('Sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    for p in tray.data.polygons:
        p.use_smooth = True
    # колесо
    bpy.ops.mesh.primitive_torus_add(major_radius=0.155, minor_radius=0.05, major_segments=64, minor_segments=24,
                                     location=(0.58, 0, 0.205), rotation=(math.pi / 2, 0, 0))
    tyre = bpy.context.object; assign(tyre, rubber)
    for p in tyre.data.polygons:
        p.use_smooth = True
    bm = bmesh.new(); cyl(bm, (0.58, 0, 0.205), 0.11, 0.07, 48, 'Y', 0)
    rm = obj_from_bm(bm, 'Rim', [rim], smooth=True, bev=(0.01, 3))
    # рама и ручки
    bm = bmesh.new()
    for s_ in (-1, 1):
        strut(bm, (0.58, s_ * 0.06, 0.205), (0.30, s_ * 0.2, 0.38), 0.026, 0)
        strut(bm, (0.30, s_ * 0.2, 0.38), (-0.55, s_ * 0.27, 0.47), 0.026, 0)
        strut(bm, (-0.55, s_ * 0.27, 0.47), (-0.82, s_ * 0.29, 0.52), 0.026, 0)
        strut(bm, (-0.22, s_ * 0.24, 0.42), (-0.30, s_ * 0.24, 0.0), 0.024, 0)
        strut(bm, (-0.30, s_ * 0.24, 0.012), (-0.18, s_ * 0.24, 0.012), 0.024, 0)
    strut(bm, (0.58, -0.07, 0.205), (0.58, 0.07, 0.205), 0.018, 0)
    fr = obj_from_bm(bm, 'FrameTubes', [steel], bev=(0.01, 3), smooth=True)
    for s_ in (-1, 1):
        bm2 = bmesh.new(); cyl(bm2, (0, 0, 0), 0.021, 0.15, 24, 'X', 0)
        g = obj_from_bm(bm2, f'Grip{s_}', [rubber], smooth=True, bev=(0.008, 3))
        g.location = (-0.76, s_ * 0.285, 0.505); g.rotation_euler = (0, math.radians(-10), math.radians(s_ * -4))
    frame_camera(elev=22, azim=-38, lens=85, margin=1.08)


def model_hardhat():
    """Строительная каска."""
    orange = mat_var('HatOrange', (0.92, 0.36, 0.015), (0.95, 0.42, 0.03), 25, 0.28, coat=0.4)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=1.0)
    for v in bm.verts:
        if v.co.z < -0.02:
            v.co.z = -0.02
    # сделать чуть вытянутой вперёд
    for v in bm.verts:
        v.co.x *= 0.13; v.co.y *= 0.108; v.co.z *= 0.128
    shell = obj_from_bm(bm, 'Shell', [orange], smooth=True)
    so = shell.modifiers.new('Solid', 'SOLIDIFY'); so.thickness = 0.004
    shell.location.z = 0.012
    # поля: кольцо, спереди шире — козырёк
    bm = bmesh.new()
    n = 96
    inner, outer = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        ext = 0.012 + 0.036 * max(0.0, ca) ** 3
        inner.append(bm.verts.new((0.128 * ca, 0.106 * sa, 0.014)))
        outer.append(bm.verts.new(((0.128 + ext) * ca, (0.106 + ext * 0.8) * sa, 0.014 - 0.01 * max(0.0, ca) - 0.003)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([inner[i], inner[j], outer[j], outer[i]])
    brim = obj_from_bm(bm, 'Brim', [orange], smooth=True)
    so = brim.modifiers.new('Solid', 'SOLIDIFY'); so.thickness = 0.005
    bevel(brim, 0.002, 2)
    # гребень
    bm = bmesh.new()
    for k in range(9):
        a = (k - 4) / 4 * 1.0
        x = 0.13 * math.sin(a) * 0.99
        z = 0.012 + 0.128 * math.cos(a) * 0.99
        rounded_box(bm, (x, 0, z), (0.035, 0.022, 0.016), (0, a, 0), 0)
    ridge = obj_from_bm(bm, 'Ridge', [orange], bev=(0.006, 4), smooth=True)
    for o in (shell, brim, ridge):
        o.rotation_euler = (0, 0, math.radians(-25))
    frame_camera(elev=20, azim=-30, lens=85, margin=1.12)


def model_calculator():
    """Калькулятор, карандаш и чертёж."""
    from PIL import Image, ImageDraw
    W, H = 1200, 900
    img = Image.new('RGB', (W, H), (26, 66, 150))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 30):
        d.line([(x, 0), (x, H)], fill=(44, 86, 168), width=1)
    for y in range(0, H, 30):
        d.line([(0, y), (W, y)], fill=(44, 86, 168), width=1)
    wl = (225, 235, 250)
    d.rectangle([120, 120, 1080, 780], outline=wl, width=10)
    d.line([(560, 120), (560, 520)], fill=wl, width=8)
    d.line([(120, 520), (860, 520)], fill=wl, width=8)
    d.line([(860, 520), (860, 780)], fill=wl, width=8)
    d.arc([560, 420, 760, 620], 180, 270, fill=wl, width=4)
    d.arc([300, 420, 500, 620], 270, 360, fill=wl, width=4)
    for y in (80,):
        d.line([(120, y), (1080, y)], fill=wl, width=3)
        d.line([(120, y - 15), (120, y + 15)], fill=wl, width=3); d.line([(1080, y - 15), (1080, y + 15)], fill=wl, width=3)
    d.line([(1130, 120), (1130, 780)], fill=wl, width=3)
    img.save('out/blueprint.png')
    paper = principled('Blueprint', (0.2, 0.3, 0.6), 0.7)
    t = paper.node_tree; p = t.nodes['Principled BSDF']
    it = node(t, 'ShaderNodeTexImage', (-500, 0)); it.image = bpy.data.images.load('out/blueprint.png')
    t.links.new(it.outputs['Color'], p.inputs['Base Color'])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.0005))
    pl = bpy.context.object; pl.scale = (0.32, 0.24, 1); pl.rotation_euler = (0, 0, math.radians(8)); assign(pl, paper)
    # калькулятор
    shell = mat_var('CalcBody', (0.62, 0.64, 0.67), (0.66, 0.68, 0.71), 40, 0.35, coat=0.2)
    keyd = mat_var('KeyDark', (0.05, 0.055, 0.065), (0.07, 0.075, 0.085), 60, 0.4)
    keyo = mat_var('KeyOrange', (0.95, 0.38, 0.02), (0.98, 0.45, 0.04), 60, 0.35)
    keyr = mat_var('KeyRed', (0.70, 0.04, 0.04), (0.75, 0.06, 0.05), 60, 0.35)
    lcd = principled('LCD', (0.42, 0.47, 0.40), 0.25)
    frame = principled('LCDFrame', (0.04, 0.04, 0.045), 0.3)
    rot = math.radians(-18)
    def place(o):
        o.rotation_euler = (0, 0, rot)
        o.location = (0.02, 0.01, 0.0)
    bm = bmesh.new(); rounded_box(bm, (0, 0, 0.008), (0.09, 0.15, 0.014), (0, 0, 0), 0)
    body = obj_from_bm(bm, 'Calc', [shell], bev=(0.006, 5), smooth=True); place(body)
    bm = bmesh.new(); rounded_box(bm, (0, 0.047, 0.0152), (0.076, 0.036, 0.0012), (0, 0, 0), 0)
    fr = obj_from_bm(bm, 'Frame', [frame], bev=(0.002, 2)); place(fr)
    bm = bmesh.new(); rounded_box(bm, (0, 0.047, 0.0158), (0.066, 0.026, 0.0008), (0, 0, 0), 0)
    sc_ = obj_from_bm(bm, 'Screen', [lcd], bev=(0.001, 2)); place(sc_)
    bm = bmesh.new(); kb = bmesh.new(); ko = bmesh.new(); kr = bmesh.new()
    for r in range(5):
        for c in range(4):
            x = (c - 1.5) * 0.019; y = 0.012 - r * 0.0185
            target = kb
            if r == 4 and c == 3: target = ko
            if r == 0 and c == 0: target = kr
            rounded_box(target, (x, y, 0.017), (0.015, 0.013, 0.004), (0, 0, 0), 0)
    for b_, m_, nm in ((kb, keyd, 'Keys'), (ko, keyo, 'KeyEq'), (kr, keyr, 'KeyC')):
        o = obj_from_bm(b_, nm, [m_], bev=(0.0018, 3), smooth=True); place(o)
    bm.free()
    # цифры на экране
    bpy.ops.object.text_add(location=(0, 0, 0))
    tx = bpy.context.object; tx.data.body = '1 250'; tx.data.size = 0.018; tx.data.align_x = 'RIGHT'; tx.data.align_y = 'CENTER'
    tx.data.extrude = 0.0002
    digit = principled('Digits', (0.03, 0.035, 0.03), 0.4)
    tx.data.materials.append(digit)
    tx.location = (0.031, 0.047, 0.0168)
    tx.parent = body; tx.location = (0.031, 0.047, 0.0168); tx.rotation_euler = (0, 0, 0)
    # карандаш
    yel = mat_var('PencilPaint', (0.95, 0.66, 0.03), (0.98, 0.72, 0.06), 30, 0.3, coat=0.4)
    wood = principled('PencilWood', (0.82, 0.62, 0.40), 0.6)
    graph = principled('Graphite', (0.08, 0.08, 0.09), 0.35, 0.5)
    pink = principled('Eraser', (0.85, 0.35, 0.40), 0.6)
    ferr = principled('Ferrule', (0.8, 0.8, 0.8), 0.25, 1.0)
    bm = bmesh.new(); cyl(bm, (0, 0, 0), 0.0042, 0.15, 6, 'X', 0)
    pen = obj_from_bm(bm, 'Pencil', [yel], bev=(0.0008, 2))
    bm = bmesh.new(); cyl(bm, (0.087, 0, 0), 0.0042, 0.024, 24, 'X', 0, r2=0.0012)
    cone = obj_from_bm(bm, 'Cone', [wood], smooth=True)
    bm = bmesh.new(); cyl(bm, (0.1, 0, 0), 0.0012, 0.004, 16, 'X', 0, r2=0.0002)
    lead = obj_from_bm(bm, 'Lead', [graph], smooth=True)
    bm = bmesh.new(); cyl(bm, (-0.081, 0, 0), 0.0045, 0.012, 24, 'X', 0)
    fe = obj_from_bm(bm, 'Ferrule', [ferr], smooth=True)
    bm = bmesh.new(); cyl(bm, (-0.093, 0, 0), 0.0042, 0.012, 24, 'X', 0)
    er = obj_from_bm(bm, 'Eraser', [pink], smooth=True, bev=(0.002, 2))
    for o in (pen, cone, lead, fe, er):
        o.rotation_euler = (0, 0, math.radians(36))
        o.location = (-0.07, -0.02, 0.0045)
    frame_camera(elev=42, azim=-20, lens=85, margin=1.0)


def model_paint():
    """Ведро краски и валик."""
    white = mat_var('BucketWhite', (0.90, 0.90, 0.89), (0.93, 0.93, 0.92), 30, 0.32, coat=0.3)
    blue = mat_var('LabelBlue', (0.01, 0.05, 0.42), (0.015, 0.07, 0.48), 30, 0.3, coat=0.3)
    red = mat_var('LabelRed', (0.75, 0.04, 0.04), (0.8, 0.06, 0.05), 30, 0.3, coat=0.3)
    steel = principled('Wire', (0.7, 0.7, 0.72), 0.3, 1.0)
    yel = mat_var('RollerHandle', (0.95, 0.62, 0.02), (0.98, 0.70, 0.05), 30, 0.35, coat=0.3)
    fluff = mat_var('Nap', (0.92, 0.88, 0.78), (0.86, 0.80, 0.68), 120, 0.9, 0.6, 900)
    bm = bmesh.new(); cyl(bm, (0, 0, 0.1), 0.112, 0.2, 64, 'Z', 0, r2=0.118)
    b = obj_from_bm(bm, 'Bucket', [white], smooth=True, bev=(0.006, 3))
    bm = bmesh.new(); cyl(bm, (0, 0, 0.098), 0.1175, 0.12, 64, 'Z', 0, r2=0.1205)
    lab = obj_from_bm(bm, 'Label', [blue], smooth=True)
    bm = bmesh.new(); cyl(bm, (0, 0, 0.162), 0.1205, 0.014, 64, 'Z', 0, r2=0.1212)
    lab2 = obj_from_bm(bm, 'Stripe', [red], smooth=True)
    bm = bmesh.new(); cyl(bm, (0, 0, 0.206), 0.124, 0.014, 64, 'Z', 0)
    lid = obj_from_bm(bm, 'Lid', [white], smooth=True, bev=(0.004, 3))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.118, minor_radius=0.0035, major_segments=64, minor_segments=12,
                                     location=(0, 0, 0.2), rotation=(math.pi / 2, 0, math.radians(20)))
    hd = bpy.context.object; assign(hd, steel)
    for p in hd.data.polygons:
        p.use_smooth = True
    # валик: лежит перед ведром
    rp = []
    bm = bmesh.new(); cyl(bm, (0, 0, 0.026), 0.026, 0.18, 48, 'X', 0)
    rp.append(obj_from_bm(bm, 'Roller', [fluff], smooth=True, bev=(0.008, 3)))
    bm = bmesh.new()
    path = [(0.09, 0, 0.026), (0.112, 0, 0.026), (0.112, -0.02, 0.06), (0.15, -0.06, 0.072)]
    for p0, p1 in zip(path[:-1], path[1:]):
        strut(bm, p0, p1, 0.005, 0)
    rp.append(obj_from_bm(bm, 'RollerWire', [steel], bev=(0.002, 2), smooth=True))
    d = Vector((0.55, -0.82, 0.12)).normalized()
    bm = bmesh.new(); cyl(bm, (0, 0, 0), 0.015, 0.13, 32, 'Z', 0)
    hd2 = obj_from_bm(bm, 'RollerHandle', [yel], smooth=True, bev=(0.007, 3))
    hd2.location = Vector((0.15, -0.06, 0.072)) + d * 0.065
    hd2.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    rp.append(hd2)
    bpy.context.view_layer.update()
    R = Matrix.Translation((0.0, -0.21, 0.0)) @ Matrix.Rotation(math.radians(-12), 4, 'Z')
    for o in rp:
        o.matrix_world = R @ o.matrix_world
    frame_camera(elev=22, azim=-30, lens=85, margin=1.08)


MODELS = {k[6:]: v for k, v in globals().items() if k.startswith('model_')}

if __name__ == '__main__':
    studio()
    MODELS[NAME]()
    t0 = time.time()
    render(OUT)
    print('render', NAME, time.time() - t0)
