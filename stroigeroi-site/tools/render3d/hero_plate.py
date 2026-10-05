"""Фон первого экрана: небо, Корякский и Авачинский, сопки, бухта."""
import sys, math, time
sys.path.insert(0, '.')
import bpy
import numpy as np
from mathutils import Vector
from b3d import reset, mesh_from_grid, node, principled, assign, render
import terrain

ARGS = dict(a.split('=') for a in sys.argv[sys.argv.index('--') + 1:]) if '--' in sys.argv else {}
W = int(ARGS.get('w', 960)); H = int(ARGS.get('h', 400))
SAMPLES = int(ARGS.get('s', 24))
GRID = ARGS.get('grid', 'lo')
OUT = ARGS.get('out', 'out/plate.png')
SUN_EL = float(ARGS.get('el', 26)); SUN_AZ = float(ARGS.get('az', 255))
EXPO = float(ARGS.get('exp', 0.0))
FOG_D = float(ARGS.get('fog', 90000))

sc = reset(samples=SAMPLES, res=(W, H), exposure=EXPO, view=ARGS.get('view', 'Standard'), look=ARGS.get('look', 'None'))

# --- Небо: свой градиент, чтобы цвет держать в руках ---
SKY_STOPS = [
    (0.00, (0.66, 0.77, 0.92)),
    (0.06, (0.50, 0.66, 0.90)),
    (0.22, (0.27, 0.46, 0.84)),
    (0.55, (0.12, 0.29, 0.72)),
    (1.00, (0.07, 0.20, 0.60)),
]

def sky_color(nt, dir_socket, loc=(-600, 0)):
    """Цвет неба по направлению взгляда: вход — вектор, выход — сокет Color."""
    x0, y0 = loc
    nrm = node(nt, 'ShaderNodeVectorMath', (x0, y0), operation='NORMALIZE')
    nt.links.new(dir_socket, nrm.inputs[0])
    sep = node(nt, 'ShaderNodeSeparateXYZ', (x0 + 150, y0))
    nt.links.new(nrm.outputs['Vector'], sep.inputs[0])
    ramp = node(nt, 'ShaderNodeValToRGB', (x0 + 300, y0))
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = SKY_STOPS[0][0], (*SKY_STOPS[0][1], 1)
    el[1].position, el[1].color = SKY_STOPS[-1][0], (*SKY_STOPS[-1][1], 1)
    for pos, col in SKY_STOPS[1:-1]:
        e = el.new(pos); e.color = (*col, 1)
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    return ramp.outputs['Color']

world = bpy.data.worlds.new('Sky'); sc.world = world
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes['Background']
tc = node(nt, 'ShaderNodeTexCoord', (-900, 0))
nt.links.new(sky_color(nt, tc.outputs['Generated']), bg.inputs['Color'])
SKY_STRENGTH = float(ARGS.get('sky', 1.0))
SKY_LIGHT = float(ARGS.get('skylight', 0.45))
lp = node(nt, 'ShaderNodeLightPath', (-400, -300))
mixs = node(nt, 'ShaderNodeMix', (-200, -200), data_type='FLOAT')
mixs.inputs[2].default_value = SKY_STRENGTH * SKY_LIGHT
mixs.inputs[3].default_value = SKY_STRENGTH
nt.links.new(lp.outputs['Is Camera Ray'], mixs.inputs['Factor'])
nt.links.new(mixs.outputs[0], bg.inputs['Strength'])

# --- Солнце ---
az, el = math.radians(SUN_AZ), math.radians(SUN_EL)
S = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
sun_data = bpy.data.lights.new('Sun', 'SUN')
sun_data.energy = float(ARGS.get('sun', 5.0))
sun_data.angle = math.radians(0.6)
sun_data.color = (1.0, 0.96, 0.9)
sun = bpy.data.objects.new('Sun', sun_data)
sun.rotation_euler = S.to_track_quat('Z', 'Y').to_euler()
sc.collection.objects.link(sun)

# --- Дымка в шейдере: цвет неба за предметом ---
def add_fog(mat, surface_out_socket, fog_d=FOG_D, strength=1.0):
    t = mat.node_tree
    out = t.nodes['Material Output']
    cam = node(t, 'ShaderNodeCameraData', (-900, -500))
    geo = node(t, 'ShaderNodeNewGeometry', (-900, -700))
    neg = node(t, 'ShaderNodeVectorMath', (-700, -700), operation='SCALE')
    neg.inputs['Scale'].default_value = -1.0
    t.links.new(geo.outputs['Incoming'], neg.inputs[0])
    em = node(t, 'ShaderNodeEmission', (-250, -700))
    em.inputs['Strength'].default_value = SKY_STRENGTH
    t.links.new(sky_color(t, neg.outputs['Vector'], (-650, -900)), em.inputs['Color'])
    # f = 1 - exp(-d/D)
    div = node(t, 'ShaderNodeMath', (-700, -500), operation='DIVIDE')
    t.links.new(cam.outputs['View Distance'], div.inputs[0]); div.inputs[1].default_value = fog_d
    ex = node(t, 'ShaderNodeMath', (-550, -500), operation='EXPONENT')
    ng = node(t, 'ShaderNodeMath', (-650, -420), operation='MULTIPLY')
    t.links.new(div.outputs[0], ng.inputs[0]); ng.inputs[1].default_value = -1
    t.links.new(ng.outputs[0], ex.inputs[0])
    one = node(t, 'ShaderNodeMath', (-400, -500), operation='SUBTRACT')
    one.inputs[0].default_value = 1.0
    t.links.new(ex.outputs[0], one.inputs[1])
    mulf = node(t, 'ShaderNodeMath', (-300, -500), operation='MULTIPLY', use_clamp=True)
    t.links.new(one.outputs[0], mulf.inputs[0]); mulf.inputs[1].default_value = strength
    mix = node(t, 'ShaderNodeMixShader', (200, 0))
    t.links.new(mulf.outputs[0], mix.inputs['Fac'])
    t.links.new(surface_out_socket, mix.inputs[1])
    t.links.new(em.outputs['Emission'], mix.inputs[2])
    t.links.new(mix.outputs['Shader'], out.inputs['Surface'])

# --- Рельеф ---
t0 = time.time()
nx, ny = (1500, 1500) if GRID == 'hi' else (700, 700)
xs, ys, h, snow = terrain.main_terrain(nx, ny)
X, Y = np.meshgrid(xs, ys)
terr = mesh_from_grid('Terrain', X, Y, h, attrs={'snow': snow})
print('terrain', time.time() - t0)

m = bpy.data.materials.new('TerrainMat'); m.use_nodes = True
t = m.node_tree
p = t.nodes['Principled BSDF']
attr = node(t, 'ShaderNodeAttribute', (-1100, 300), attribute_name='snow')
geo = node(t, 'ShaderNodeNewGeometry', (-1100, 0))
sep = node(t, 'ShaderNodeSeparateXYZ', (-900, 0))
t.links.new(geo.outputs['Position'], sep.inputs[0])
sepn = node(t, 'ShaderNodeSeparateXYZ', (-900, -150))
t.links.new(geo.outputs['Normal'], sepn.inputs[0])
tex = node(t, 'ShaderNodeTexCoord', (-1300, -300))
nz = node(t, 'ShaderNodeTexNoise', (-1100, -300))
nz.inputs['Scale'].default_value = 0.0035
nz.inputs['Detail'].default_value = 8
nz.inputs['Roughness'].default_value = 0.6
t.links.new(tex.outputs['Object'], nz.inputs['Vector'])
# снег: маска + шум, на крутых склонах меньше
snow_fac = node(t, 'ShaderNodeMath', (-850, 300), operation='MULTIPLY_ADD')
t.links.new(attr.outputs['Fac'], snow_fac.inputs[0]); snow_fac.inputs[1].default_value = 1.15
nzc = node(t, 'ShaderNodeMath', (-900, 200), operation='SUBTRACT')
t.links.new(nz.outputs['Fac'], nzc.inputs[0]); nzc.inputs[1].default_value = 0.5
nzs = node(t, 'ShaderNodeMath', (-850, 150), operation='MULTIPLY')
t.links.new(nzc.outputs[0], nzs.inputs[0]); nzs.inputs[1].default_value = 0.7
t.links.new(nzs.outputs[0], snow_fac.inputs[2])
slope = node(t, 'ShaderNodeMapRange', (-700, -150))
t.links.new(sepn.outputs['Z'], slope.inputs['Value'])
slope.inputs['From Min'].default_value = 0.45; slope.inputs['From Max'].default_value = 0.75
sm = node(t, 'ShaderNodeMath', (-600, 250), operation='MULTIPLY')
t.links.new(snow_fac.outputs[0], sm.inputs[0]); t.links.new(slope.outputs['Result'], sm.inputs[1])
ramp = node(t, 'ShaderNodeValToRGB', (-450, 250))
ramp.color_ramp.elements[0].position = 0.42; ramp.color_ramp.elements[1].position = 0.58
t.links.new(sm.outputs[0], ramp.inputs['Fac'])
# земля: лес внизу, пепел и камень выше
low = node(t, 'ShaderNodeMapRange', (-700, -400))
t.links.new(sep.outputs['Z'], low.inputs['Value'])
low.inputs['From Min'].default_value = 700; low.inputs['From Max'].default_value = 1500
groundmix = node(t, 'ShaderNodeMix', (-450, -100), data_type='RGBA')
groundmix.inputs[6].default_value = (0.030, 0.050, 0.022, 1)   # A: лес
groundmix.inputs[7].default_value = (0.055, 0.047, 0.042, 1)   # B: камень/пепел
nzm = node(t, 'ShaderNodeMath', (-550, -350), operation='MULTIPLY_ADD')
t.links.new(nzc.outputs[0], nzm.inputs[0]); nzm.inputs[1].default_value = 0.6
t.links.new(low.outputs['Result'], nzm.inputs[2])
t.links.new(nzm.outputs[0], groundmix.inputs['Factor'])
colmix = node(t, 'ShaderNodeMix', (-200, 100), data_type='RGBA')
t.links.new(ramp.outputs['Color'], colmix.inputs['Factor'])
t.links.new(groundmix.outputs[2], colmix.inputs[6])
colmix.inputs[7].default_value = (0.80, 0.84, 0.90, 1)
t.links.new(colmix.outputs[2], p.inputs['Base Color'])
rmix = node(t, 'ShaderNodeMapRange', (-200, -100))
t.links.new(ramp.outputs['Color'], rmix.inputs['Value'])
rmix.inputs['To Min'].default_value = 0.92; rmix.inputs['To Max'].default_value = 0.55
t.links.new(rmix.outputs['Result'], p.inputs['Roughness'])
bump = node(t, 'ShaderNodeBump', (-200, -300))
bump.inputs['Strength'].default_value = 0.35
nzb = node(t, 'ShaderNodeTexNoise', (-450, -500))
nzb.inputs['Scale'].default_value = 0.02; nzb.inputs['Detail'].default_value = 10
t.links.new(tex.outputs['Object'], nzb.inputs['Vector'])
t.links.new(nzb.outputs['Fac'], bump.inputs['Height'])
t.links.new(bump.outputs['Normal'], p.inputs['Normal'])
add_fog(m, p.outputs['BSDF'])
assign(terr, m)

# --- Вода ---
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 6000, 0))
water = bpy.context.object; water.scale = (90000, 12000, 1)
wm = principled('Water', (0.010, 0.022, 0.035), 0.06, IOR=1.33)
wt = wm.node_tree; wp = wt.nodes['Principled BSDF']
wb = node(wt, 'ShaderNodeBump', (-300, -300)); wb.inputs['Strength'].default_value = 0.12
wn = node(wt, 'ShaderNodeTexNoise', (-500, -300)); wn.inputs['Scale'].default_value = 0.004; wn.inputs['Detail'].default_value = 6
wtc = node(wt, 'ShaderNodeTexCoord', (-700, -300))
wmap = node(wt, 'ShaderNodeMapping', (-600, -300)); wmap.inputs['Scale'].default_value = (90000, 3000, 1)
wt.links.new(wtc.outputs['Object'], wmap.inputs['Vector']); wt.links.new(wmap.outputs['Vector'], wn.inputs['Vector'])
wt.links.new(wn.outputs['Fac'], wb.inputs['Height']); wt.links.new(wb.outputs['Normal'], wp.inputs['Normal'])
add_fog(wm, wp.outputs['BSDF'])
assign(water, wm)

# --- Дальний берег: склон, дома, деревья ---
import city
if ARGS.get('city', '1') == '1':
    GX, GY, GZ = city.build_ground()
    gob = mesh_from_grid('Shore', GX, GY, GZ)
    gm = bpy.data.materials.new('ShoreMat'); gm.use_nodes = True
    gt = gm.node_tree; gp = gt.nodes['Principled BSDF']
    gtc = node(gt, 'ShaderNodeTexCoord', (-900, 0))
    gn = node(gt, 'ShaderNodeTexNoise', (-700, 0)); gn.inputs['Scale'].default_value = 0.004; gn.inputs['Detail'].default_value = 6
    gt.links.new(gtc.outputs['Object'], gn.inputs['Vector'])
    gr = node(gt, 'ShaderNodeValToRGB', (-450, 0))
    gr.color_ramp.elements[0].position = 0.4; gr.color_ramp.elements[0].color = (0.030, 0.045, 0.022, 1)
    gr.color_ramp.elements[1].position = 0.65; gr.color_ramp.elements[1].color = (0.075, 0.085, 0.060, 1)
    gt.links.new(gn.outputs['Fac'], gr.inputs['Fac'])
    gt.links.new(gr.outputs['Color'], gp.inputs['Base Color'])
    gp.inputs['Roughness'].default_value = 0.9
    add_fog(gm, gp.outputs['BSDF'])
    assign(gob, gm)

    cob = city.build_city()
    cm = bpy.data.materials.new('CityMat'); cm.use_nodes = True
    ct = cm.node_tree; cp = ct.nodes['Principled BSDF']
    ca = node(ct, 'ShaderNodeAttribute', (-1100, 300), attribute_name='bcol')
    cr = node(ct, 'ShaderNodeAttribute', (-1100, 100), attribute_name='roof')
    cg = node(ct, 'ShaderNodeNewGeometry', (-1300, -200))
    cpos = node(ct, 'ShaderNodeSeparateXYZ', (-1100, -200)); ct.links.new(cg.outputs['Position'], cpos.inputs[0])
    cnrm = node(ct, 'ShaderNodeSeparateXYZ', (-1100, -400)); ct.links.new(cg.outputs['Normal'], cnrm.inputs[0])
    # u = x*|ny| + y*|nx| — горизонтальная координата по фасаду
    anx = node(ct, 'ShaderNodeMath', (-900, -400), operation='ABSOLUTE'); ct.links.new(cnrm.outputs['X'], anx.inputs[0])
    any_ = node(ct, 'ShaderNodeMath', (-900, -500), operation='ABSOLUTE'); ct.links.new(cnrm.outputs['Y'], any_.inputs[0])
    m1 = node(ct, 'ShaderNodeMath', (-750, -300), operation='MULTIPLY'); ct.links.new(cpos.outputs['X'], m1.inputs[0]); ct.links.new(any_.outputs[0], m1.inputs[1])
    m2 = node(ct, 'ShaderNodeMath', (-750, -450), operation='MULTIPLY'); ct.links.new(cpos.outputs['Y'], m2.inputs[0]); ct.links.new(anx.outputs[0], m2.inputs[1])
    u = node(ct, 'ShaderNodeMath', (-600, -350), operation='ADD'); ct.links.new(m1.outputs[0], u.inputs[0]); ct.links.new(m2.outputs[0], u.inputs[1])
    def band(src, period, lo, hi, loc):
        md = node(ct, 'ShaderNodeMath', loc, operation='FLOORED_MODULO'); ct.links.new(src, md.inputs[0]); md.inputs[1].default_value = period
        g1 = node(ct, 'ShaderNodeMath', (loc[0] + 150, loc[1]), operation='GREATER_THAN'); ct.links.new(md.outputs[0], g1.inputs[0]); g1.inputs[1].default_value = lo
        l1 = node(ct, 'ShaderNodeMath', (loc[0] + 150, loc[1] - 100), operation='LESS_THAN'); ct.links.new(md.outputs[0], l1.inputs[0]); l1.inputs[1].default_value = hi
        mm = node(ct, 'ShaderNodeMath', (loc[0] + 300, loc[1]), operation='MULTIPLY'); ct.links.new(g1.outputs[0], mm.inputs[0]); ct.links.new(l1.outputs[0], mm.inputs[1])
        return mm.outputs[0]
    wu = band(u.outputs[0], 3.3, 0.9, 2.5, (-450, -300))
    wz = band(cpos.outputs['Z'], 2.9, 0.9, 2.3, (-450, -550))
    win = node(ct, 'ShaderNodeMath', (0, -400), operation='MULTIPLY'); ct.links.new(wu, win.inputs[0]); ct.links.new(wz, win.inputs[1])
    vert = node(ct, 'ShaderNodeMath', (0, -550), operation='LESS_THAN'); ct.links.new(cr.outputs['Fac'], vert.inputs[0]); vert.inputs[1].default_value = 0.5
    winm = node(ct, 'ShaderNodeMath', (150, -450), operation='MULTIPLY'); ct.links.new(win.outputs[0], winm.inputs[0]); ct.links.new(vert.outputs[0], winm.inputs[1])
    wall = node(ct, 'ShaderNodeMix', (-300, 200), data_type='RGBA')
    ct.links.new(cr.outputs['Fac'], wall.inputs['Factor'])
    ct.links.new(ca.outputs['Color'], wall.inputs[6])
    wall.inputs[7].default_value = (0.10, 0.10, 0.11, 1)
    facade = node(ct, 'ShaderNodeMix', (0, 200), data_type='RGBA')
    ct.links.new(winm.outputs[0], facade.inputs['Factor'])
    ct.links.new(wall.outputs[2], facade.inputs[6])
    facade.inputs[7].default_value = (0.035, 0.05, 0.075, 1)
    ct.links.new(facade.outputs[2], cp.inputs['Base Color'])
    rough = node(ct, 'ShaderNodeMapRange', (200, -200)); ct.links.new(winm.outputs[0], rough.inputs['Value'])
    rough.inputs['To Min'].default_value = 0.85; rough.inputs['To Max'].default_value = 0.12
    ct.links.new(rough.outputs['Result'], cp.inputs['Roughness'])
    add_fog(cm, cp.outputs['BSDF'])
    assign(cob, cm)

    tob = city.build_trees()
    tm = bpy.data.materials.new('TreeMat'); tm.use_nodes = True
    tt = tm.node_tree; tp = tt.nodes['Principled BSDF']
    ttc = node(tt, 'ShaderNodeTexCoord', (-900, 0))
    tn = node(tt, 'ShaderNodeTexNoise', (-700, 0)); tn.inputs['Scale'].default_value = 0.01
    tt.links.new(ttc.outputs['Object'], tn.inputs['Vector'])
    trr = node(tt, 'ShaderNodeValToRGB', (-450, 0))
    trr.color_ramp.elements[0].color = (0.018, 0.035, 0.014, 1)
    trr.color_ramp.elements[1].color = (0.05, 0.075, 0.025, 1)
    tt.links.new(tn.outputs['Fac'], trr.inputs['Fac'])
    tt.links.new(trr.outputs['Color'], tp.inputs['Base Color'])
    tp.inputs['Roughness'].default_value = 0.85
    add_fog(tm, tp.outputs['BSDF'])
    assign(tob, tm)

# --- Камера ---
cam_data = bpy.data.cameras.new('Cam')
cam_data.sensor_width = 36
cam_data.lens = float(ARGS.get('lens', 52))
cam_data.shift_y = float(ARGS.get('shift', 0.106))
cam_data.clip_start = 1; cam_data.clip_end = 200000
cam = bpy.data.objects.new('Cam', cam_data)
cam.location = (float(ARGS.get('cx', 0)), 0, float(ARGS.get('cz', 25)))
cam.rotation_euler = (math.radians(90), 0, 0)
sc.collection.objects.link(cam); sc.camera = cam

if ARGS.get('mode') == 'mask':
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = 'RGBA'
    sc.cycles.samples = 1
    sc.cycles.use_denoising = False
    sc.cycles.use_adaptive_sampling = False
    em = bpy.data.materials.new('MaskMat'); em.use_nodes = True
    et = em.node_tree
    for nd in list(et.nodes):
        if nd.type != 'OUTPUT_MATERIAL':
            et.nodes.remove(nd)
    e = node(et, 'ShaderNodeEmission', (0, 0))
    et.links.new(e.outputs[0], et.nodes['Material Output'].inputs['Surface'])
    for ob in sc.objects:
        if ob.type == 'MESH':
            ob.data.materials.clear(); ob.data.materials.append(em)
t0 = time.time()
render(OUT)
print('render', time.time() - t0)
