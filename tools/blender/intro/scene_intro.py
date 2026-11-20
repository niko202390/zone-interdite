"""Scene construction for the Zone Interdite opening film (Blender 5.3, Cycles).

Shots are built separately (shot 1, shot 2, shots 3+4) on a shared 14 s timeline.
frame f  <->  time t = (f - 1) / FPS.   Everything is seeded and deterministic.
"""
import math
import os
import bmesh
import bpy
import numpy as np
from mathutils import Vector, Matrix

import lettering as LT
import textures as TX

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'previews', 'cache')

FPS = 24
DURATION = 14.0
FRAMES = int(DURATION * FPS)  # 336

CUES = {
    'pen_start': 0.40,
    'pen_end': 4.20,
    'lid_open': 4.85,
    'strike': 5.55,
    'flame_on': 5.60,
    'flame_under_paper': 7.00,
    'lid_close': 12.25,
    'flame_off': 12.29,
    'end': DURATION,
}
SHOTS = {1: (1, 108), 2: (109, 168), 3: (169, 288), 4: (289, 336)}

PW, PH = 0.30, 0.22          # paper sheet, metres
Z_HELD = 0.12                # paper height when held over the flame
CASE_W, CASE_D, CASE_H, LID_H = 0.038, 0.013, 0.0365, 0.0195
LIGHTER_POS = Vector((0.27, 0.05, 0.0))


def t_of(f):
    return (f - 1) / FPS


def f_of(t):
    return int(round(t * FPS)) + 1


def smoothstep(a, b, x):
    u = min(1.0, max(0.0, (x - a) / (b - a)))
    return u * u * (3 - 2 * u)


# --------------------------------------------------------------------------- utils

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = FRAMES
    return sc


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, mat=None, smooth=True, uvs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    return link(ob)


def recalc_normals(ob, flip=False):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if flip:
        for f in bm.faces:
            f.normal_flip()
    bm.to_mesh(ob.data)
    bm.free()


def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.empty_display_size = 0.01
    return link(e)


def key(obj, path, f, val=None, index=-1):
    if val is not None:
        setattr(obj, path, val)
    obj.keyframe_insert(path, frame=f, index=index)


def revolve(profile, segs=48):
    """profile: list of (r, z) along +Z. Returns verts, faces."""
    verts, faces = [], []
    n = len(profile)
    for (r, z) in profile:
        for k in range(segs):
            a = 2 * math.pi * k / segs
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(n - 1):
        for k in range(segs):
            a, b = i * segs + k, i * segs + (k + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    # caps
    c0 = len(verts); verts.append((0, 0, profile[0][1]))
    c1 = len(verts); verts.append((0, 0, profile[-1][1]))
    for k in range(segs):
        faces.append((c0, (k + 1) % segs, k))
        faces.append((c1, (n - 1) * segs + k, (n - 1) * segs + (k + 1) % segs))
    return verts, faces


def mod_solidify(ob, t, offset=-1.0):
    m = ob.modifiers.new('Solidify', 'SOLIDIFY')
    m.thickness = t
    m.offset = offset
    m.use_even_offset = True
    return m


def mod_bevel(ob, w, seg=3, angle=40):
    m = ob.modifiers.new('Bevel', 'BEVEL')
    m.width = w
    m.segments = seg
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    return m


# --------------------------------------------------------------------------- node builder

class NB:
    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        try:
            self.mat.use_nodes = True
        except Exception:
            pass
        self.nt = self.mat.node_tree
        self.nodes = self.nt.nodes
        self.nodes.clear()
        self.out = self.nodes.new('ShaderNodeOutputMaterial')

    def _in(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
        elif v is not None:
            if isinstance(v, tuple) and len(v) == 3 and sock.type == 'RGBA':
                v = (*v, 1.0)
            sock.default_value = v

    def n(self, t, **kw):
        nd = self.nodes.new(t)
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def math(self, op, a, b=0.0, c=0.0, clamp=False):
        nd = self.n('ShaderNodeMath', operation=op, use_clamp=clamp)
        self._in(nd.inputs[0], a); self._in(nd.inputs[1], b); self._in(nd.inputs[2], c)
        return nd.outputs[0]

    def add(self, a, b): return self.math('ADD', a, b)
    def sub(self, a, b): return self.math('SUBTRACT', a, b)
    def mul(self, a, b): return self.math('MULTIPLY', a, b)
    def clamp(self, a): return self.math('ADD', a, 0.0, clamp=True)
    def madd(self, a, b, c): return self.math('MULTIPLY_ADD', a, b, c)

    def maprange(self, x, a, b, lo=0.0, hi=1.0, smooth=True):
        nd = self.n('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP' if smooth else 'LINEAR')
        nd.clamp = True
        self._in(nd.inputs['Value'], x)
        nd.inputs['From Min'].default_value = a
        nd.inputs['From Max'].default_value = b
        nd.inputs['To Min'].default_value = lo
        nd.inputs['To Max'].default_value = hi
        return nd.outputs['Result']

    def vmath(self, op, a, b=None, scale=None):
        nd = self.n('ShaderNodeVectorMath', operation=op)
        self._in(nd.inputs[0], a)
        if b is not None:
            self._in(nd.inputs[1], b)
        if scale is not None:
            self._in(nd.inputs['Scale'], scale)
        return nd.outputs[0] if op not in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else nd.outputs['Value']

    def sep(self, v):
        nd = self.n('ShaderNodeSeparateXYZ')
        self._in(nd.inputs[0], v)
        return nd.outputs[0], nd.outputs[1], nd.outputs[2]

    def comb(self, x, y, z=0.0):
        nd = self.n('ShaderNodeCombineXYZ')
        self._in(nd.inputs[0], x); self._in(nd.inputs[1], y); self._in(nd.inputs[2], z)
        return nd.outputs[0]

    def sepc(self, c):
        nd = self.n('ShaderNodeSeparateColor')
        self._in(nd.inputs[0], c)
        return nd.outputs[0], nd.outputs[1], nd.outputs[2]

    def noise(self, vec, scale, detail=4.0, rough=0.55, distortion=0.0, w=None, lac=2.0):
        nd = self.n('ShaderNodeTexNoise')
        if w is not None:
            nd.noise_dimensions = '4D'
            self._in(nd.inputs['W'], w)
        self._in(nd.inputs['Vector'], vec)
        nd.inputs['Scale'].default_value = scale
        nd.inputs['Detail'].default_value = detail
        nd.inputs['Roughness'].default_value = rough
        nd.inputs['Distortion'].default_value = distortion
        nd.inputs['Lacunarity'].default_value = lac
        return nd.outputs['Fac']

    def voronoi(self, vec, scale, feature='F1', rand=1.0):
        nd = self.n('ShaderNodeTexVoronoi', feature=feature)
        self._in(nd.inputs['Vector'], vec)
        nd.inputs['Scale'].default_value = scale
        nd.inputs['Randomness'].default_value = rand
        return nd

    def image(self, img, vec, ext='REPEAT', interp='Linear'):
        nd = self.n('ShaderNodeTexImage', image=img, extension=ext, interpolation=interp)
        self._in(nd.inputs['Vector'], vec)
        return nd

    def mix(self, fac, a, b):
        nd = self.n('ShaderNodeMix', data_type='RGBA')
        ins = {s.identifier: s for s in nd.inputs}
        self._in(ins['Factor_Float'], fac)
        self._in(ins['A_Color'], a)
        self._in(ins['B_Color'], b)
        return [s for s in nd.outputs if s.identifier == 'Result_Color'][0]

    def ramp(self, fac, stops):
        nd = self.n('ShaderNodeValToRGB')
        self._in(nd.inputs['Fac'], fac)
        els = nd.color_ramp.elements
        while len(els) < len(stops):
            els.new(0.5)
        for el, (p, c) in zip(els, stops):
            el.position = p
            el.color = (c[0], c[1], c[2], 1.0)
        return nd.outputs['Color']

    def bump(self, h, strength, dist, normal=None):
        nd = self.n('ShaderNodeBump')
        self._in(nd.inputs['Height'], h)
        nd.inputs['Strength'].default_value = strength
        nd.inputs['Distance'].default_value = dist
        if normal is not None:
            self._in(nd.inputs['Normal'], normal)
        return nd.outputs['Normal']

    def principled(self, **kw):
        nd = self.n('ShaderNodeBsdfPrincipled')
        for k, v in kw.items():
            self._in(nd.inputs[k], v)
        return nd

    def coord(self, kind='Object'):
        return self.n('ShaderNodeTexCoord').outputs[kind]

    def value(self, v=0.0, name=None):
        nd = self.n('ShaderNodeValue')
        nd.outputs[0].default_value = v
        if name:
            nd.name = name; nd.label = name
        return nd

    def time_value(self):
        nd = self.value(0.0, 'Time')
        fc = nd.outputs[0].driver_add('default_value')
        fc.driver.type = 'SCRIPTED'
        fc.driver.expression = '(frame - 1) / %d' % FPS
        return nd.outputs[0]

    def surface(self, sock):
        self.nt.links.new(sock, self.out.inputs['Surface'])
        return self.mat

    def volume(self, sock):
        self.nt.links.new(sock, self.out.inputs['Volume'])
        return self.mat


# --------------------------------------------------------------------------- images

def np_to_image(name, arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=True)
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.filepath_raw = path
    img.file_format = 'OPEN_EXR'
    img.save()
    bpy.data.images.remove(img)
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = 'Non-Color'
    img.alpha_mode = 'CHANNEL_PACKED'
    return img


_TEXT = {}
FIB_TILE = 0.075


def text_data():
    if not _TEXT:
        st = LT.build_strokes()
        tm, sp = LT.time_strokes(st, CUES['pen_start'], CUES['pen_end'])
        _TEXT.update(strokes=st, times=tm, speeds=sp)
    return _TEXT


def ink_image():
    d = text_data()
    path = os.path.join(CACHE, 'ink_map.exr')
    rgba, box = LT.rasterize(d['strokes'], d['times'], d['speeds'])
    d['box'] = box
    return np_to_image('InkMap', rgba, path), box


def fibre_image():
    path = os.path.join(CACHE, 'paper_fibre.exr')
    return np_to_image('Fibre', TX.fibre_texture(tile=FIB_TILE), path)


# --------------------------------------------------------------------------- materials

def mat_paper(ink_img, box, fib_img):
    B = NB('Paper')
    uv = B.n('ShaderNodeUVMap').outputs['UV']
    u, v, _ = B.sep(uv)
    f1 = B.image(fib_img, B.vmath('SCALE', uv, scale=1 / FIB_TILE))
    mp = B.n('ShaderNodeMapping')
    B._in(mp.inputs['Vector'], uv)
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(37))
    mp.inputs['Scale'].default_value = (1 / (FIB_TILE * 1.57), 1 / (FIB_TILE * 1.57), 1)
    mp.inputs['Location'].default_value = (0.31, 0.17, 0)
    f2 = B.image(fib_img, mp.outputs[0])
    r1, g1, b1 = B.sepc(f1.outputs['Color'])
    r2, g2, b2 = B.sepc(f2.outputs['Color'])
    fh = B.madd(r1, 0.6, B.mul(r2, 0.4))
    tint = B.mul(B.add(g1, g2), 0.5)
    form = B.mul(B.add(b1, b2), 0.5)
    uv3 = B.comb(u, v, 0.0)
    cloud = B.noise(uv3, 55.0, 5.0, 0.6)
    # laid and chain lines (wire marks of the mould)
    jit = B.noise(uv3, 400.0, 2.0)
    laid_ph = B.mul(B.madd(jit, 0.00012, v), 2 * math.pi / 0.00094)
    laid = B.math('POWER', B.madd(B.math('SINE', laid_ph), 0.5, 0.5), 3.0)
    cf = B.sub(B.math('FRACT', B.madd(u, 1 / 0.026, 0.5)), 0.5)
    chain = B.math('EXPONENT', B.mul(B.math('POWER', B.mul(cf, 0.026 / 0.00040), 2.0), -1.0))
    # edge distance + deckle
    dx = B.math('MINIMUM', B.add(u, PW / 2), B.sub(PW / 2, u))
    dy = B.math('MINIMUM', B.add(v, PH / 2), B.sub(PH / 2, v))
    dedge = B.math('MINIMUM', dx, dy)
    dn = B.noise(uv3, 650.0, 6.0, 0.7)
    dn2 = B.noise(uv3, 90.0, 3.0, 0.5)
    thr = B.add(B.madd(dn, 0.0018, B.mul(dn2, 0.0016)), B.mul(fh, 0.0005))
    deck = B.maprange(B.sub(dedge, thr), 0.0003, 0.0011)
    edge_tone = B.maprange(dedge, 0.022, 0.0, 0.0, 1.0)
    # ink map
    x0, y0, w, h = box
    iu = B.mul(B.sub(u, x0), 1 / w)
    iv = B.mul(B.sub(v, y0), 1 / h)
    ink = B.image(ink_img, B.comb(iu, iv, 0.0), ext='CLIP')
    imask, ibead, iamt = B.sepc(ink.outputs['Color'])
    itw = ink.outputs['Alpha']
    T = B.time_value()
    age = B.sub(T, itw)
    wet = B.mul(B.math('GREATER_THAN', age, 0.0), B.maprange(age, 1.05, 0.0, 0.0, 1.0))
    wet = B.mul(wet, B.maprange(ibead, 0.15, 0.75))
    # scorch, driven by the flame x position
    fxn = B.value(-1.0, 'FlameX')
    fxn_s = fxn.outputs[0]
    hn = B.noise(uv3, 120.0, 3.0)
    heat = B.maprange(B.add(B.sub(fxn_s, u), B.mul(B.sub(hn, 0.5), 0.016)), -0.004, 0.022)
    feather = B.maprange(B.add(B.madd(ibead, 0.55, B.mul(imask, 0.55)), B.mul(B.sub(fh, 0.5), 0.6)), 0.35, 0.85)
    pn = B.noise(uv3, 260.0, 4.0, 0.6)
    pn2 = B.noise(uv3, 40.0, 2.0)
    patch = B.maprange(B.add(pn, B.mul(pn2, 0.6)), 0.40, 1.05, 0.12, 1.05, smooth=False)
    big = B.maprange(B.noise(uv3, 70.0, 2.0, 0.5), 0.35, 0.68, 0.45, 1.25)
    scorch = B.clamp(B.mul(B.mul(B.mul(B.mul(heat, feather), B.math('POWER', iamt, 1.3)), patch), big))
    # faint toasting of the paper itself along the flame path
    toast = B.mul(B.mul(heat, B.maprange(B.math('ABSOLUTE', B.sub(v, LT.BASELINE_Y + 0.008)), 0.03, 0.0)),
                  B.mul(hn, 0.10))
    # colour
    paper_a = (0.66, 0.54, 0.35)
    paper_b = (0.77, 0.66, 0.47)
    col = B.mix(B.clamp(B.madd(cloud, 0.6, B.mul(tint, 0.5))), paper_a, paper_b)
    col = B.mix(B.mul(edge_tone, 0.45), col, (0.42, 0.29, 0.14))
    fox = B.maprange(B.noise(uv3, 180.0, 3.0, 0.6), 0.70, 0.78)
    col = B.mix(B.mul(fox, 0.35), col, (0.36, 0.22, 0.09))
    col = B.mix(B.madd(fh, -0.12, 0.06), col, (0.0, 0.0, 0.0))
    col = B.mix(toast, col, (0.30, 0.17, 0.06))
    scol = B.ramp(scorch, [(0.0, (0.50, 0.36, 0.20)), (0.3, (0.42, 0.24, 0.09)),
                           (0.65, (0.22, 0.095, 0.03)), (1.0, (0.08, 0.032, 0.010))])
    col = B.mix(B.maprange(scorch, 0.0, 0.35), col, scol)
    col = B.mix(B.mul(wet, 0.22), col, (0.0, 0.0, 0.0))
    rough = B.add(B.madd(fh, 0.12, 0.66), B.mul(scorch, -0.08))
    grain = B.noise(uv3, 2600.0, 4.0, 0.6)
    hgt = B.add(B.madd(fh, 0.75, B.mul(laid, 0.12)), B.madd(cloud, 0.35, B.mul(scorch, -0.15)))
    hgt = B.madd(grain, 0.45, hgt)
    nrm = B.bump(hgt, 0.55, 0.00006)
    cnrm = B.bump(B.mul(ibead, wet), 1.0, 0.00025)
    bsdf = B.principled(**{'Base Color': col, 'Roughness': rough, 'Normal': nrm,
                           'Coat Weight': B.mul(wet, 1.0), 'Coat Roughness': 0.025,
                           'Coat IOR': 1.36, 'Coat Normal': cnrm,
                           'Sheen Weight': 0.25, 'Sheen Roughness': 0.6})
    # translucency: thinner at laid/chain wires, cloudy formation, scorch blocks light
    thin = B.mul(B.madd(laid, 0.16, B.madd(chain, 0.14, 1.0)),
                 B.madd(B.add(form, cloud), -0.35, 1.4))
    thin = B.mul(thin, B.madd(fh, -0.3, 1.1))
    thin = B.mul(thin, B.madd(B.maprange(dedge, 0.004, 0.0), 0.6, 1.0))
    tfac = B.clamp(B.mul(B.mul(thin, 0.30), B.madd(B.clamp(B.mul(scorch, 1.6)), -0.88, 1.0)))
    tcol = B.mix(B.clamp(B.mul(scorch, 1.5)), (0.80, 0.60, 0.36), (0.12, 0.04, 0.01))
    tr = B.n('ShaderNodeBsdfTranslucent')
    B._in(tr.inputs['Color'], tcol)
    B._in(tr.inputs['Normal'], nrm)
    m1 = B.n('ShaderNodeMixShader')
    B._in(m1.inputs[0], tfac); B._in(m1.inputs[1], bsdf.outputs[0]); B._in(m1.inputs[2], tr.outputs[0])
    tp = B.n('ShaderNodeBsdfTransparent')
    m2 = B.n('ShaderNodeMixShader')
    B._in(m2.inputs[0], deck); B._in(m2.inputs[1], tp.outputs[0]); B._in(m2.inputs[2], m1.outputs[0])
    mat = B.surface(m2.outputs[0])
    return mat, fxn


def mat_wood():
    B = NB('DeskWood')
    p = B.coord('Object')
    pa = B.vmath('MULTIPLY', p, (5.0, 55.0, 55.0))
    n1 = B.noise(pa, 1.0, 5.0, 0.55)
    x, y, z = B.sep(p)
    ph = B.add(B.mul(y, 2 * math.pi / 0.0045), B.mul(n1, 16.0))
    g = B.math('POWER', B.madd(B.math('SINE', ph), 0.5, 0.5), 2.2)
    big = B.noise(B.vmath('MULTIPLY', p, (1.5, 9.0, 9.0)), 1.0, 3.0)
    pores = B.maprange(B.noise(B.vmath('MULTIPLY', p, (90.0, 2600.0, 2600.0)), 1.0, 2.0, 0.5), 0.62, 0.75)
    col = B.mix(B.clamp(B.madd(g, 0.7, B.mul(big, 0.5))), (0.030, 0.014, 0.007), (0.085, 0.042, 0.018))
    col = B.mix(B.mul(pores, 0.6), col, (0.008, 0.004, 0.002))
    smudge = B.noise(p, 9.0, 4.0, 0.6)
    scr = B.maprange(B.noise(B.vmath('MULTIPLY', p, (30.0, 1.0, 30.0)), 40.0, 2.0), 0.7, 0.74)
    crough = B.add(B.maprange(smudge, 0.35, 0.75, 0.04, 0.22), B.mul(scr, 0.1))
    hgt = B.add(B.mul(pores, -0.6), B.mul(g, 0.15))
    nrm = B.bump(hgt, 0.25, 0.0002)
    bsdf = B.principled(**{'Base Color': col, 'Roughness': 0.5, 'Normal': nrm,
                           'Coat Weight': 1.0, 'Coat Roughness': crough, 'Coat IOR': 1.5})
    return B.surface(bsdf.outputs[0])


def mat_metal(name, base, rough, rough_var=0.12, scale=600.0, tarnish=None, aniso_stretch=None):
    B = NB(name)
    p = B.coord('Object')
    if aniso_stretch:
        p = B.vmath('MULTIPLY', p, aniso_stretch)
    n = B.noise(p, scale, 5.0, 0.6)
    n2 = B.noise(p, scale * 0.15, 3.0)
    r = B.maprange(B.add(n, B.mul(n2, 0.5)), 0.3, 1.2, rough - rough_var * 0.5, rough + rough_var)
    col = base
    if tarnish:
        col = B.mix(B.maprange(n2, 0.45, 0.8, 0.0, 0.6), base, tarnish)
    nrm = B.bump(n, 0.08, 0.00002)
    bsdf = B.principled(**{'Base Color': col, 'Metallic': 1.0, 'Roughness': r, 'Normal': nrm})
    return B.surface(bsdf.outputs[0])


def mat_ebonite():
    B = NB('Ebonite')
    p = B.coord('Object')
    n = B.noise(p, 900.0, 4.0)
    nrm = B.bump(n, 0.05, 0.00003)
    bsdf = B.principled(**{'Base Color': (0.010, 0.009, 0.008), 'Roughness': 0.3, 'Normal': nrm,
                           'Coat Weight': 0.8, 'Coat Roughness': B.maprange(B.noise(p, 120.0), 0.3, 0.7, 0.04, 0.12)})
    return B.surface(bsdf.outputs[0])


def mat_crackle():
    B = NB('BlackCrackle')
    p = B.coord('Object')
    vo = B.voronoi(p, 1700.0, 'DISTANCE_TO_EDGE')
    edge = vo.outputs['Distance']
    vo2 = B.voronoi(p, 4200.0, 'DISTANCE_TO_EDGE')
    cell = B.maprange(edge, 0.0, 0.12)
    cell2 = B.maprange(vo2.outputs['Distance'], 0.0, 0.15)
    fine = B.noise(p, 9000.0, 3.0)
    hgt = B.add(B.madd(cell, 0.7, B.mul(cell2, 0.3)), B.mul(fine, 0.15))
    rn = B.noise(p, 300.0, 3.0)
    rough = B.add(B.maprange(rn, 0.3, 0.7, 0.30, 0.45), B.mul(B.sub(1.0, cell), 0.15))
    nrm = B.bump(hgt, 0.55, 0.00012)
    col = B.mix(B.mul(rn, 0.4), (0.010, 0.010, 0.011), (0.022, 0.020, 0.019))
    bsdf = B.principled(**{'Base Color': col, 'Roughness': rough, 'Normal': nrm,
                           'Specular IOR Level': 0.55})
    return B.surface(bsdf.outputs[0])


def mat_emit(name, color, strength, use_objcolor=False):
    B = NB(name)
    em = B.n('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1)
    if use_objcolor:
        oi = B.n('ShaderNodeObjectInfo')
        r, g, b = B.sepc(oi.outputs['Color'])
        B._in(em.inputs['Strength'], B.mul(r, strength))
    else:
        em.inputs['Strength'].default_value = strength
    return B.surface(em.outputs[0])


def mat_wick():
    B = NB('Wick')
    p = B.coord('Object')
    x, y, z = B.sep(p)
    char = B.maprange(z, 0.0035, 0.0055)
    n = B.noise(B.vmath('MULTIPLY', p, (1.0, 1.0, 0.2)), 3000.0, 3.0)
    col = B.mix(char, B.mix(n, (0.45, 0.40, 0.32), (0.62, 0.56, 0.45)), (0.02, 0.016, 0.012))
    bsdf = B.principled(**{'Base Color': col, 'Roughness': 0.9,
                           'Normal': B.bump(n, 0.6, 0.0002)})
    return B.surface(bsdf.outputs[0])


def mat_flame(length):
    B = NB('Flame')
    p = B.coord('Object')
    x, y, z = B.sep(p)
    s = B.mul(z, 1.0 / length)
    T = B.time_value()
    n = B.noise(B.vmath('MULTIPLY', p, (1.0, 1.0, 0.6)), 260.0, 3.0, 0.5, w=B.mul(T, 4.0))
    col = B.ramp(s, [(0.0, (0.05, 0.15, 1.0)), (0.09, (0.25, 0.30, 0.9)), (0.18, (1.0, 0.62, 0.22)),
                     (0.5, (1.0, 0.46, 0.10)), (1.0, (0.8, 0.16, 0.02))])
    bright = B.ramp(s, [(0.0, (0.10, 0.10, 0.10)), (0.12, (0.25, 0.25, 0.25)), (0.25, (1.0, 1.0, 1.0)),
                        (0.6, (0.75, 0.75, 0.75)), (1.0, (0.0, 0.0, 0.0))])
    br, _, _ = B.sepc(bright)
    strength_node = B.value(1.0, 'FlameStrength')
    up = B.comb(x, y, B.sub(z, B.mul(T, 0.25)))
    n2 = B.noise(B.vmath('MULTIPLY', up, (1.0, 1.0, 0.5)), 180.0, 4.0, 0.6, distortion=0.6)
    brk = B.maprange(n2, 0.30, 0.70, 0.25, 1.15)
    st = B.mul(B.mul(B.mul(br, B.madd(n, 0.7, 0.6)), brk), B.mul(strength_node.outputs[0], 800.0))
    em = B.n('ShaderNodeEmission')
    B._in(em.inputs['Color'], col)
    B._in(em.inputs['Strength'], st)
    return B.volume(em.outputs[0]), strength_node


def mat_smoke(Tz, fxn_name='SmokeX'):
    B = NB('Smoke')
    p = B.n('ShaderNodeNewGeometry').outputs['Position']
    x, y, z = B.sep(p)
    T = B.time_value()
    hgt = B.sub(z, Tz)
    fx = B.value(-1.0, fxn_name)
    adv = B.comb(x, y, B.sub(z, B.mul(T, 0.035)))
    n = B.noise(adv, 70.0, 4.0, 0.55, distortion=2.2, w=B.mul(T, 0.35))
    wisp = B.maprange(n, 0.56, 0.72)
    cx = B.sub(fx.outputs[0], B.madd(hgt, 0.5, 0.018))
    envx = B.math('EXPONENT', B.mul(B.math('POWER', B.mul(B.sub(x, cx), 1 / 0.028), 2.0), -1.0))
    envy = B.math('EXPONENT', B.mul(B.math('POWER', B.mul(B.sub(y, LT.BASELINE_Y + 0.008), 1 / 0.014), 2.0), -1.0))
    envz = B.mul(B.math('EXPONENT', B.mul(hgt, -1 / 0.028)), B.maprange(hgt, 0.0, 0.004))
    dens = B.mul(B.mul(B.mul(wisp, envx), B.mul(envy, envz)), 140.0)
    dn = B.value(1.0, 'SmokeAmount')
    dens = B.mul(dens, dn.outputs[0])
    vol = B.n('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.55, 0.53, 0.5, 1)
    vol.inputs['Anisotropy'].default_value = 0.45
    B._in(vol.inputs['Density'], dens)
    return B.volume(vol.outputs[0]), fx, dn


# --------------------------------------------------------------------------- props

def build_desk(mat):
    s = 2.4
    me = mesh_obj('Desk', [(-s / 2, -0.6, 0), (s / 2, -0.6, 0), (s / 2, 1.6, 0), (-s / 2, 1.6, 0)],
                  [(0, 1, 2, 3)], mat, smooth=False)
    return me


def build_paper(mat, mode='flat'):
    nx, ny = 241, 177
    xs = np.linspace(-PW / 2, PW / 2, nx)
    ys = np.linspace(-PH / 2, PH / 2, ny)
    X, Y = np.meshgrid(xs, ys)
    rng = np.random.default_rng(3)
    # low-frequency cockle
    Z = np.zeros_like(X)
    for _ in range(6):
        kx, ky = rng.normal(0, 30, 2)
        Z += rng.uniform(0.00004, 0.00012) * np.sin(kx * X + ky * Y + rng.uniform(0, 6.28))
    de = np.minimum(np.minimum(X + PW / 2, PW / 2 - X), np.minimum(Y + PH / 2, PH / 2 - Y))
    if mode == 'flat':
        Z = 0.00016 + np.abs(Z) + 0.0009 * np.exp(-de / 0.006)
    else:
        # held up over the flame: gentle sag along x and a slight curl at the far edge
        Z = Z_HELD + Z * 3 - 0.010 * (X / (PW / 2)) ** 2 + 0.006 * np.clip((Y - 0.04) / 0.07, 0, 1) ** 2 \
            + 0.002 * np.sin(X * 9.0 + 0.5) * (Y / PH)
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    uvs = [(float(x), float(y)) for x, y in zip(X.ravel(), Y.ravel())]
    ob = mesh_obj('Paper', verts, faces, mat, smooth=True, uvs=uvs)
    return ob


def build_lamp(pos, mats, shade_open_dir=(0, -1)):
    """Desk lamp seen only as out-of-focus bokeh: brass base and stem, metal shade, glowing bulb."""
    brass, shade_mat, bulb_mat = mats
    objs = []
    v, f = revolve([(0.075, 0.0), (0.075, 0.012), (0.06, 0.02), (0.012, 0.024), (0.012, 0.0)], 48)
    b = mesh_obj('LampBase', v, f, brass); b.location = pos; objs.append(b)
    v, f = revolve([(0.008, 0.0), (0.008, 0.33)], 24)
    st = mesh_obj('LampStem', v, f, brass); st.location = pos; objs.append(st)
    # shade: open cone facing down, slightly tilted toward the desk
    prof = [(0.03, 0.0), (0.10, -0.12)]
    v, f = revolve(prof, 64)
    f = f[:64 * (len(prof) - 1)]
    sh = mesh_obj('LampShade', v, f, shade_mat)
    mod_solidify(sh, 0.0015, 0.0)
    sh.location = Vector(pos) + Vector((0, 0, 0.36))
    objs.append(sh)
    v, f = revolve([(0.0, -0.03), (0.022, -0.045), (0.026, -0.065), (0.02, -0.085), (0.0, -0.09)], 32)
    bu = mesh_obj('LampBulb', v, f, bulb_mat)
    bu.location = sh.location
    bu.visible_shadow = False
    objs.append(bu)
    return objs, sh.location + Vector((0, 0, -0.065))


def build_inkwell(pos, brass, glass):
    v, f = revolve([(0.0, 0.0), (0.032, 0.0), (0.034, 0.004), (0.034, 0.040), (0.03, 0.046), (0.012, 0.050),
                    (0.012, 0.056), (0.0, 0.056)], 64)
    body = mesh_obj('Inkwell', v, f, glass); body.location = pos
    v, f = revolve([(0.0, 0.054), (0.016, 0.054), (0.017, 0.058), (0.016, 0.074), (0.012, 0.078), (0.0, 0.079)], 48)
    cap = mesh_obj('InkwellCap', v, f, brass); cap.location = pos
    v, f = revolve([(0.0, -0.001), (0.045, -0.001), (0.047, 0.003), (0.045, 0.006), (0.0, 0.006)], 64)
    tray = mesh_obj('InkTray', v, f, brass); tray.location = pos
    return [body, cap, tray]


def mat_glass():
    B = NB('InkGlass')
    bsdf = B.principled(**{'Base Color': (0.05, 0.06, 0.09), 'Roughness': 0.04, 'Transmission Weight': 0.6,
                           'IOR': 1.5})
    return B.surface(bsdf.outputs[0])


def build_pen(gold, ebon):
    """Fountain pen, local frame: tip at origin, axis +Z, nib top faces +Y."""
    parts = []
    NL = 0.018
    nu, nv = 60, 28
    verts = []
    for i in range(nu):
        u = i / (nu - 1)
        z = NL * u
        hw = 0.00075 + (0.0034 - 0.00075) * min(1.0, (u / 0.82)) ** 0.85
        if u > 0.82:
            hw = 0.0034 - 0.0003 * (u - 0.82) / 0.18
        rc = 0.0033 + 0.006 * (1 - u) ** 2
        ytop = 0.0031 * u ** 0.8
        phi_max = math.asin(min(0.99, hw / rc))
        for j in range(nv):
            ph = -phi_max + 2 * phi_max * j / (nv - 1)
            verts.append((rc * math.sin(ph), rc * math.cos(ph) - rc + ytop, z))
    faces = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = i * nv + j
            faces.append((a, a + nv, a + nv + 1, a + 1))
    nib = mesh_obj('Nib', verts, faces, gold)
    recalc_normals(nib)
    mod_solidify(nib, 0.00028, -1.0)
    mod_bevel(nib, 0.00006, 2, 50)
    # slit + breather hole cutter
    hz = NL * 0.55
    v, f = revolve([(0.0005, -0.004), (0.0005, 0.004)], 24)
    hole = mesh_obj('NibHoleCutter', v, f, None)
    hole.rotation_euler = (math.radians(90), 0, 0)
    hole.location = (0, 0.0031 * 0.55 ** 0.8, hz)
    slit = mesh_obj('NibSlitCutter', [(-0.00003, -0.004, -0.001), (0.00003, -0.004, -0.001), (0.00003, 0.006, -0.001),
                                      (-0.00003, 0.006, -0.001), (-0.00003, -0.004, hz), (0.00003, -0.004, hz),
                                      (0.00003, 0.006, hz), (-0.00003, 0.006, hz)],
                    [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], None,
                    smooth=False)
    for c in (hole, slit):
        c.hide_render = True
        c.display_type = 'WIRE'
        m = nib.modifiers.new('Cut' + c.name, 'BOOLEAN')
        m.operation = 'DIFFERENCE'
        m.object = c
        m.solver = 'EXACT'
        c.parent = nib
    parts.append(nib)
    # feed under the nib
    v, f = revolve([(0.0003, 0.0035), (0.0018, 0.008), (0.0026, 0.014), (0.0030, 0.022)], 32)
    feed = mesh_obj('Feed', v, f, ebon)
    feed.scale = (1.0, 0.8, 1.0)
    feed.location = (0, -0.0006, 0)
    parts.append(feed)
    # section, band, barrel
    prof = [(0.0036, 0.0155), (0.0040, 0.0165), (0.0041, 0.024), (0.0044, 0.036), (0.0050, 0.040), (0.0052, 0.042)]
    v, f = revolve(prof, 64)
    sec = mesh_obj('Section', v, f, ebon); parts.append(sec)
    v, f = revolve([(0.0058, 0.042), (0.0060, 0.043), (0.0060, 0.047), (0.0058, 0.048)], 64)
    band = mesh_obj('Band', v, f, gold); parts.append(band)
    v, f = revolve([(0.0059, 0.048), (0.0062, 0.05), (0.0062, 0.15), (0.0055, 0.158), (0.0, 0.16)], 64)
    bar = mesh_obj('Barrel', v, f, ebon); parts.append(bar)
    root = empty('Pen')
    for p in parts:
        p.parent = root
    return root, nib


def rounded_loop(hx, hy, r, nc=8, nsx=8, nsy=3):
    pts = []
    corners = [(hx - r, hy - r, 0), (-hx + r, hy - r, 90), (-hx + r, -hy + r, 180), (hx - r, -hy + r, 270)]
    for ci, (cx, cy, a0) in enumerate(corners):
        for k in range(nc):
            a = math.radians(a0 + 90 * k / nc)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        a = math.radians(a0 + 90)
        ex, ey = cx + r * math.cos(a), cy + r * math.sin(a)
        nx_, ny_, _ = corners[(ci + 1) % 4]
        a1 = math.radians(corners[(ci + 1) % 4][2])
        sx, sy = nx_ + r * math.cos(a1), ny_ + r * math.sin(a1)
        ns = nsx if ci % 2 == 0 else nsy
        for k in range(ns):
            t = k / ns
            pts.append((ex + (sx - ex) * t, ey + (sy - ey) * t))
    return pts


def shell(name, hx, hy, r, h, er, mat, closed='bottom', ring_z=10):
    rings = []
    for k in range(6):
        th = math.radians(90 * k / 5)
        rings.append((er * (1 - math.sin(th)), er * (1 - math.cos(th))))
    for z in np.linspace(er, h, ring_z)[1:]:
        rings.append((0.0, float(z)))
    if closed == 'top':
        rings = [(i, h - z) for (i, z) in reversed(rings)]
    verts, faces = [], []
    m = None
    for (ins, z) in rings:
        loop = rounded_loop(hx - ins, hy - ins, max(r - ins, 0.0004))
        m = len(loop)
        verts += [(x, y, z) for x, y in loop]
    for i in range(len(rings) - 1):
        for k in range(m):
            a, b = i * m + k, i * m + (k + 1) % m
            faces.append((a, b, b + m, a + m))
    cidx = len(verts)
    if closed == 'bottom':
        verts.append((0, 0, 0))
        for k in range(m):
            faces.append((cidx, (k + 1) % m, k))
    else:
        verts.append((0, 0, h))
        base = (len(rings) - 1) * m
        for k in range(m):
            faces.append((cidx, base + k, base + (k + 1) % m))
    ob = mesh_obj(name, verts, faces, mat)
    return ob


def tube(name, hx, hy, r, z0, z1, mat, nz=6):
    loop = rounded_loop(hx, hy, r, 8, 10, 3)
    m = len(loop)
    verts, faces = [], []
    for z in np.linspace(z0, z1, nz):
        verts += [(x, y, float(z)) for x, y in loop]
    for i in range(nz - 1):
        for k in range(m):
            a, b = i * m + k, i * m + (k + 1) % m
            faces.append((a, b, b + m, a + m))
    return mesh_obj(name, verts, faces, mat)


def build_lighter(mats):
    crackle, brass, steel, wickm, flame_mat, spark_mat = mats
    root = empty('Lighter', LIGHTER_POS)
    hx, hy = CASE_W / 2, CASE_D / 2
    case = shell('Case', hx, hy, 0.0034, CASE_H, 0.0012, crackle, 'bottom')
    recalc_normals(case)
    mod_solidify(case, 0.00045, -1.0)
    case.parent = root
    hinge = empty('Hinge', (hx - 0.0008, 0, CASE_H))
    hinge.parent = root
    lid = shell('Lid', hx, hy, 0.0034, LID_H, 0.0012, crackle, 'top')
    recalc_normals(lid)
    mod_solidify(lid, 0.00045, -1.0)
    lid.parent = hinge
    lid.location = (-(hx - 0.0008), 0, 0.0002)
    v, f = revolve([(0.0011, -0.0024), (0.0011, 0.0024)], 24)
    barrel = mesh_obj('HingeBarrel', v, f, crackle)
    barrel.rotation_euler = (math.radians(90), 0, 0)
    barrel.location = (hx - 0.0008, hy + 0.0011, CASE_H)
    barrel.parent = root
    # insert top plate
    loop = rounded_loop(hx - 0.0006, hy - 0.0006, 0.0028)
    verts = [(x, y, CASE_H - 0.0004) for x, y in loop] + [(0, 0, CASE_H - 0.0004)]
    c = len(loop)
    plate = mesh_obj('InsertPlate', verts, [(c, k, (k + 1) % c) for k in range(c)], brass, smooth=False)
    plate.parent = root
    # chimney
    chx, chy = 0.0117, 0.0055
    ccx = -hx + 0.0006 + 0.0012 + chx  # chimney centre x
    ch = tube('Chimney', chx, chy, 0.0016, CASE_H - 0.0004, CASE_H + 0.0145, brass)
    ch.location = (ccx, 0, 0)
    recalc_normals(ch)
    mod_solidify(ch, 0.0004, -1.0)
    ch.parent = root
    cv, cf = [], []
    for row, zz in enumerate((CASE_H + 0.0072, CASE_H + 0.0106)):
        for col in range(4):
            xx = ccx + (-1.5 + col) * 0.0047 + (0.0 if row == 0 else 0.0)
            v, f = revolve([(0.0011, -0.012), (0.0011, 0.012)], 20)
            R = Matrix.Translation((xx, 0, zz)) @ Matrix.Rotation(math.radians(90), 4, 'X')
            off = len(cv)
            cv += [tuple(R @ Vector(p)) for p in v]
            cf += [tuple(i + off for i in fc) for fc in f]
    cutter = mesh_obj('HoleCutter', cv, cf, None, smooth=False)
    cutter.hide_render = True
    cutter.display_type = 'WIRE'
    m = ch.modifiers.new('Holes', 'BOOLEAN')
    m.operation = 'DIFFERENCE'; m.object = cutter; m.solver = 'EXACT'
    cutter.location = (-ccx, 0, 0)
    cutter.parent = ch
    cutter.parent = root
    cutter.location = (0, 0, 0)
    # wheel supports
    wx = ccx + chx + 0.0050
    wz = CASE_H + 0.0098
    for sy in (-1, 1):
        y0 = sy * 0.0021
        er_ = 0.0027
        pts = [(wx - er_, CASE_H - 0.0004), (wx + er_, CASE_H - 0.0004), (wx + er_, wz)]
        for k in range(13):
            a = math.radians(180 * k / 12)
            pts.append((wx + er_ * math.cos(a), wz + er_ * math.sin(a)))
        pts.append((wx - er_, wz))
        n = len(pts)
        verts = [(x, y0 - 0.0002, z) for x, z in pts] + [(x, y0 + 0.0002, z) for x, z in pts]
        faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
        for k in range(n):
            faces.append((k, (k + 1) % n, n + (k + 1) % n, n + k))
        sp = mesh_obj('WheelSupport', verts, faces, brass, smooth=False)
        recalc_normals(sp)
        mod_bevel(sp, 0.00012, 2, 30)
        sp.parent = root
    # knurled flint wheel
    wpiv = empty('WheelPivot', (wx, 0, wz))
    wpiv.parent = root
    R0, Wd = 0.0040, 0.0017
    na, ny_ = 144, 14
    verts = []
    for j in range(ny_ + 1):
        yy = -Wd + 2 * Wd * j / ny_
        for i in range(na):
            a = 2 * math.pi * i / na
            k1 = abs(((a * 36 / (2 * math.pi) + yy / 0.0011) % 1) - 0.5)
            k2 = abs(((a * 36 / (2 * math.pi) - yy / 0.0011) % 1) - 0.5)
            rr = R0 - 0.0003 + 0.0006 * max(k1, k2)
            if j in (0, ny_):
                rr = R0 - 0.00035
            verts.append((rr * math.cos(a), yy, rr * math.sin(a)))
    faces = []
    for j in range(ny_):
        for i in range(na):
            a, b = j * na + i, j * na + (i + 1) % na
            faces.append((a, a + na, b + na, b))
    c0 = len(verts); verts.append((0, -Wd, 0))
    c1 = len(verts); verts.append((0, Wd, 0))
    for i in range(na):
        faces.append((c0, (i + 1) % na, i))
        faces.append((c1, ny_ * na + i, ny_ * na + (i + 1) % na))
    wheel = mesh_obj('FlintWheel', verts, faces, steel, smooth=False)
    wheel.parent = wpiv
    v, f = revolve([(0.0007, -0.0026), (0.0007, 0.0026)], 16)
    axle = mesh_obj('Axle', v, f, steel)
    axle.rotation_euler = (math.radians(90), 0, 0)
    axle.location = (wx, 0, wz)
    axle.parent = root
    # wick
    v, f = revolve([(0.0013, 0.0), (0.0013, 0.0045), (0.0011, 0.0055), (0.0, 0.0058)], 24)
    wick = mesh_obj('Wick', v, f, wickm)
    wick.location = (ccx - 0.001, 0, CASE_H + 0.0045)
    wick.parent = root
    # flame
    L = 0.034
    prof = []
    for k in range(41):
        s = k / 40
        r = (s ** 0.42) * (1 - s) ** 1.3
        prof.append((max(r, 1e-5), s * L))
    rmax = max(p[0] for p in prof)
    prof = [(0.0047 * r / rmax, z) for r, z in prof]
    v, f = revolve(prof, 40)
    flame = mesh_obj('Flame', v, f, flame_mat)
    flame.scale = (1.3, 0.85, 1.0)
    fpiv = empty('FlamePivot', (ccx - 0.001, 0, CASE_H + 0.0088))
    fpiv.parent = root
    flame.parent = fpiv
    for a in ('visible_diffuse', 'visible_shadow', 'visible_volume_scatter', 'visible_transmission'):
        setattr(flame, a, False)
    sub = flame.modifiers.new('Sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 1
    tex = bpy.data.textures.new('FlameTurb', 'CLOUDS')
    tex.noise_scale = 0.35
    disp = flame.modifiers.new('Turb', 'DISPLACE')
    disp.texture = tex
    disp.texture_coords = 'OBJECT'
    flow = empty('FlameFlow', (0, 0, 0))
    flow.scale = (0.025, 0.025, 0.025)  # texture coords = p * 40
    disp.texture_coords_object = flow
    disp.strength = 0.0030
    disp.mid_level = 0.5
    return dict(root=root, lid_hinge=hinge, wheel=wpiv, flame=flame, flame_pivot=fpiv, flow=flow,
                flame_base=Vector((ccx - 0.001, 0, CASE_H + 0.0088)) + LIGHTER_POS,
                wheel_pos=Vector((wx, 0, wz)) + LIGHTER_POS, chimney_cx=ccx, spark_mat=spark_mat)


# --------------------------------------------------------------------------- camera, lights, render

def camera(name, lens, fstop, focus_obj=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36.0
    cd.sensor_fit = 'HORIZONTAL'
    cd.clip_start = 0.005
    cd.clip_end = 20
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_blades = 0
    if focus_obj is not None:
        cd.dof.focus_object = focus_obj
    ob = bpy.data.objects.new(name, cd)
    link(ob)
    bpy.context.scene.camera = ob
    return ob


def track(ob, target):
    c = ob.constraints.new('TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return c


def light(name, kind, loc, energy, color, size=0.05, rot=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind in ('POINT', 'SPOT'):
        ld.shadow_soft_size = size
    elif kind == 'AREA':
        ld.size = size
        ld.shape = 'DISK'
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    if rot is not None:
        ob.rotation_euler = rot
    return link(ob)


def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def world(strength=1.0, color=(0.0018, 0.0016, 0.0014)):
    w = bpy.data.worlds.new('World')
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = w.node_tree.nodes.get('Background')
    if bg is None:
        bg = w.node_tree.nodes.new('ShaderNodeBackground')
        out = w.node_tree.nodes.new('ShaderNodeOutputWorld')
        w.node_tree.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs['Color'].default_value = (*color, 1)
    bg.inputs['Strength'].default_value = strength


def _try(obj, attr, val):
    try:
        setattr(obj, attr, val)
        return True
    except Exception as e:
        print('  (skip %s.%s: %s)' % (type(obj).__name__, attr, e))
        return False


def render_settings(samples=96, pct=100, device='GPU', threshold=0.02):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    if device == 'GPU':
        prefs = bpy.context.preferences.addons['cycles'].preferences
        try:
            prefs.compute_device_type = 'ONEAPI'
            prefs.refresh_devices()
            ok = False
            for d in prefs.devices:
                d.use = d.type == 'ONEAPI'
                ok = ok or d.use
            cy.device = 'GPU' if ok else 'CPU'
        except Exception as e:
            print('GPU unavailable, CPU fallback:', e)
            cy.device = 'CPU'
    else:
        cy.device = 'CPU'
    print('Cycles device:', cy.device)
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = threshold
    cy.adaptive_min_samples = 0
    cy.use_denoising = True
    _try(cy, 'denoiser', 'OPENIMAGEDENOISE')
    _try(cy, 'denoising_use_gpu', True)
    _try(cy, 'denoising_input_passes', 'RGB_ALBEDO_NORMAL')
    _try(cy, 'max_bounces', 8)
    _try(cy, 'diffuse_bounces', 3)
    _try(cy, 'glossy_bounces', 4)
    _try(cy, 'transmission_bounces', 6)
    _try(cy, 'volume_bounces', 1)
    _try(cy, 'transparent_max_bounces', 12)
    _try(cy, 'caustics_reflective', False)
    _try(cy, 'caustics_refractive', False)
    _try(cy, 'blur_glossy', 1.0)
    _try(cy, 'sample_clamp_indirect', 6.0)
    _try(cy, 'sample_clamp_direct', 0.0)
    _try(cy, 'use_light_tree', True)
    _try(cy, 'volume_step_rate', 2.0)
    _try(cy, 'volume_max_steps', 256)
    _try(cy, 'seed', 1944)
    _try(cy, 'use_animated_seed', True)
    _try(cy, 'film_exposure', 1.0)
    _try(sc.render, 'filter_size', 1.5)
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = pct
    sc.render.use_persistent_data = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    vs = sc.view_settings
    vs.view_transform = 'AgX'
    for look in ('AgX - Medium High Contrast', 'Medium High Contrast', 'AgX - Base Contrast', 'None'):
        if _try(vs, 'look', look):
            break
    sc.display_settings.display_device = 'sRGB'
    setup_compositor(sc)


def setup_compositor(sc, vignette=0.62):
    """Gentle bloom, a whisper of lateral chromatic aberration, lens vignette."""
    try:
        ng = bpy.data.node_groups.new('IntroComp', 'CompositorNodeTree')
        ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        sc.compositing_node_group = ng
        N, Lk = ng.nodes, ng.links
        rl = N.new('CompositorNodeRLayers')
        out = N.new('NodeGroupOutput')
        gl = N.new('CompositorNodeGlare')
        gl.inputs['Type'].default_value = 'Bloom'
        gl.inputs['Quality'].default_value = 'High'
        gl.inputs['Threshold'].default_value = 1.0
        gl.inputs['Strength'].default_value = 0.22
        gl.inputs['Size'].default_value = 0.7
        ld = N.new('CompositorNodeLensdist')
        ld.inputs['Dispersion'].default_value = 0.010
        Lk.new(rl.outputs['Image'], gl.inputs['Image'])
        Lk.new(gl.outputs['Image'], ld.inputs['Image'])
        em = N.new('CompositorNodeEllipseMask')
        em.inputs['Size'].default_value = (0.95, 0.92)
        em.inputs['Mask'].default_value = 0.0
        em.inputs['Value'].default_value = 1.0
        bl = N.new('CompositorNodeBlur')
        bl.inputs['Size'].default_value = (420, 420)
        Lk.new(em.outputs[0], bl.inputs['Image'])
        mr = N.new('ShaderNodeMapRange')
        Lk.new(bl.outputs[0], mr.inputs['Value'])
        mr.inputs['To Min'].default_value = vignette
        mx = N.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.blend_type = 'MULTIPLY'
        ins = {s.identifier: s for s in mx.inputs}
        ins['Factor_Float'].default_value = 1.0
        Lk.new(ld.outputs['Image'], ins['A_Color'])
        Lk.new(mr.outputs['Result'], ins['B_Color'])
        res = [s for s in mx.outputs if s.identifier == 'Result_Color'][0]
        Lk.new(res, out.inputs[0])
        print('Compositor ok')
    except Exception as e:
        import traceback; traceback.print_exc()
        print('Compositor setup failed (rendering without):', e)
        try:
            sc.compositing_node_group = None
        except Exception:
            pass
