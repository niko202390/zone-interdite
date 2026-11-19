"""Procedural materials (baked to Principled image maps before export) and the Cycles bake helpers.
Pattern follows tools/blender/weapons/build_p38.py: each material wires a Principled BSDF for viewing
and normal bakes, plus an Emission node used to bake colour / roughness / metallic."""
import os
import time

import bpy
import numpy as np


def log(*a):
    print("[mats]", *a, flush=True)


class NB:
    def __init__(self, mat):
        self.nt = mat.node_tree
        self.N = self.nt.nodes
        self.L = self.nt.links

    def new(self, t, **kw):
        nd = self.N.new(t)
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def put(self, sock, val):
        if val is None:
            return
        if isinstance(val, bpy.types.NodeSocket):
            self.L.new(val, sock)
        else:
            sock.default_value = val

    def math(self, op, a, b=None, c=None, clamp=False):
        nd = self.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, x in enumerate((a, b, c)):
            self.put(nd.inputs[i], x)
        return nd.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        nd = self.new('ShaderNodeVectorMath', operation=op)
        self.put(nd.inputs[0], a)
        if b is not None:
            self.put(nd.inputs[1], b)
        if scale is not None:
            self.put(nd.inputs[3], scale)
        return nd.outputs[1] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else nd.outputs[0]

    def mix(self, t, a, b):
        nd = self.new('ShaderNodeMix', data_type='RGBA', clamp_factor=True)
        ins = {s.identifier: s for s in nd.inputs}
        self.put(ins['Factor_Float'], t)
        self.put(ins['A_Color'], a)
        self.put(ins['B_Color'], b)
        return {s.identifier: s for s in nd.outputs}['Result_Color']

    def mixf(self, t, a, b):
        nd = self.new('ShaderNodeMix', data_type='FLOAT', clamp_factor=True)
        ins = {s.identifier: s for s in nd.inputs}
        self.put(ins['Factor_Float'], t)
        self.put(ins['A_Float'], a)
        self.put(ins['B_Float'], b)
        return {s.identifier: s for s in nd.outputs}['Result_Float']

    def maprange(self, x, a, b, c=0.0, d=1.0, smooth=False):
        nd = self.new('ShaderNodeMapRange', clamp=True)
        if smooth:
            nd.interpolation_type = 'SMOOTHSTEP'
        self.put(nd.inputs[0], x)
        nd.inputs[1].default_value = a
        nd.inputs[2].default_value = b
        nd.inputs[3].default_value = c
        nd.inputs[4].default_value = d
        return nd.outputs[0]

    def noise(self, vec, scale, detail=4.0, rough=0.55, dist=0.0, out='Fac'):
        nd = self.new('ShaderNodeTexNoise')
        self.put(nd.inputs['Vector'], vec)
        nd.inputs['Scale'].default_value = scale
        nd.inputs['Detail'].default_value = detail
        nd.inputs['Roughness'].default_value = rough
        nd.inputs['Distortion'].default_value = dist
        return nd.outputs[out]

    def voronoi(self, vec, scale, rand=1.0, out='Distance', feature='F1'):
        nd = self.new('ShaderNodeTexVoronoi', feature=feature)
        self.put(nd.inputs['Vector'], vec)
        nd.inputs['Scale'].default_value = scale
        nd.inputs['Randomness'].default_value = rand
        return nd.outputs[out]

    def wave(self, vec, scale, kind='BANDS', direction='X', dist=0.0, detail=0.0, profile='SIN'):
        nd = self.new('ShaderNodeTexWave', wave_type=kind)
        if kind == 'BANDS':
            nd.bands_direction = direction
        else:
            nd.rings_direction = direction
        nd.wave_profile = profile
        self.put(nd.inputs['Vector'], vec)
        nd.inputs['Scale'].default_value = scale
        nd.inputs['Distortion'].default_value = dist
        nd.inputs['Detail'].default_value = detail
        return nd.outputs['Fac']

    def mapping(self, vec, scale=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0)):
        nd = self.new('ShaderNodeMapping')
        self.put(nd.inputs['Vector'], vec)
        nd.inputs['Scale'].default_value = scale
        nd.inputs['Location'].default_value = loc
        nd.inputs['Rotation'].default_value = rot
        return nd.outputs[0]

    def value(self, v):
        nd = self.new('ShaderNodeValue')
        nd.outputs[0].default_value = v
        return nd.outputs[0]

    def rgb(self, c):
        nd = self.new('ShaderNodeRGB')
        nd.outputs[0].default_value = (c[0], c[1], c[2], 1.0)
        return nd.outputs[0]

    def attr(self, name):
        nd = self.new('ShaderNodeAttribute', attribute_name=name, attribute_type='GEOMETRY')
        return nd.outputs['Fac']

    def sep(self, vec):
        nd = self.new('ShaderNodeSeparateXYZ')
        self.put(nd.inputs[0], vec)
        return nd.outputs

    def bump(self, height, dist, strength=1.0, normal=None):
        nd = self.new('ShaderNodeBump')
        self.put(nd.inputs['Height'], height)
        nd.inputs['Distance'].default_value = dist
        nd.inputs['Strength'].default_value = strength
        if normal is not None:
            self.put(nd.inputs['Normal'], normal)
        return nd.outputs['Normal']


def new_material(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return mat


def finish(mat, nb, color, rough, metal, normal):
    out = nb.new('ShaderNodeOutputMaterial')
    bsdf = nb.new('ShaderNodeBsdfPrincipled')
    nb.put(bsdf.inputs['Base Color'], color)
    nb.put(bsdf.inputs['Roughness'], rough)
    nb.put(bsdf.inputs['Metallic'], metal)
    if normal is not None:
        nb.put(bsdf.inputs['Normal'], normal)
    nb.L.new(bsdf.outputs[0], out.inputs['Surface'])
    emit = nb.new('ShaderNodeEmission')
    img = nb.new('ShaderNodeTexImage')
    if not isinstance(metal, bpy.types.NodeSocket):
        metal = nb.value(metal)
    if not isinstance(rough, bpy.types.NodeSocket):
        rough = nb.value(rough)
    return dict(mat=mat, nb=nb, out=out, bsdf=bsdf, emit=emit, img=img,
                sock=dict(color=color, rough=rough, metal=metal))


def _common(nb):
    tc = nb.new('ShaderNodeTexCoord').outputs['Object']
    geo = nb.new('ShaderNodeNewGeometry')
    z = nb.sep(tc)['Z']
    return tc, geo, z


def _stitch(nb, tc, edge_d, d0=0.004, d1=0.0065, pitch=0.004):
    """Row of stitches running parallel to a mesh border, using the edge_d attribute (metres)."""
    win = nb.math('MULTIPLY', nb.maprange(edge_d, d0, d0 + 0.0008),
                  nb.math('SUBTRACT', 1.0, nb.maprange(edge_d, d1 - 0.0008, d1)))
    s = nb.sep(tc)
    ph = nb.math('ADD', nb.math('ADD', s['X'], s['Y']), s['Z'])
    dash = nb.math('LESS_THAN', nb.math('FRACT', nb.math('DIVIDE', ph, pitch)), 0.62)
    return nb.math('MULTIPLY', win, dash)


# ------------------------------------------------------------------------------------- wool
def mat_wool(name, base_a, base_b, mud=True, inner=False, knit=False):
    mat = new_material(name)
    nb = NB(mat)
    tc, geo, z = _common(nb)
    n_big = nb.noise(tc, 3.0, 4.0, 0.55)
    n_mid = nb.noise(tc, 22.0, 5.0, 0.6)
    heather = nb.noise(tc, 420.0, 4.0, 0.7)
    fuzz = nb.noise(nb.mapping(tc, (1.0, 1.0, 1.6)), 1500.0, 3.0, 0.6)
    base = nb.mix(nb.maprange(n_big, 0.35, 0.65), nb.rgb(base_a), nb.rgb(base_b))
    base = nb.mix(nb.math('MULTIPLY', nb.maprange(heather, 0.3, 0.7), 0.35), base,
                  nb.rgb(tuple(c * 1.45 for c in base_b)))
    base = nb.mix(nb.math('MULTIPLY', nb.maprange(fuzz, 0.55, 0.75), 0.35), base,
                  nb.rgb(tuple(c * 0.6 for c in base_a)))
    # wear: convex edges a touch lighter and smoother (pilled, rubbed)
    # mottled fading and grime blotches (long service, rain, campfire smoke)
    mott = nb.maprange(n_mid, 0.30, 0.70)
    base = nb.mix(nb.math('MULTIPLY', mott, 0.55), base, nb.rgb(tuple(c * 1.30 for c in base_b)))
    grime = nb.maprange(nb.noise(tc, 7.0, 6.0, 0.65, dist=0.6), 0.55, 0.72)
    base = nb.mix(nb.math('MULTIPLY', grime, 0.6), base, nb.rgb(tuple(c * 0.55 for c in base_a)))
    convex = nb.maprange(geo.outputs['Pointiness'], 0.52, 0.6, smooth=True)
    worn = nb.math('MULTIPLY', convex, nb.maprange(n_mid, 0.4, 0.65, 0.2, 1.0))
    col = nb.mix(nb.math('MULTIPLY', worn, 0.6), base, nb.rgb(tuple(c * 1.5 + 0.012 for c in base_b)))
    rough = nb.math('ADD', 0.88, nb.math('MULTIPLY', fuzz, 0.08))
    edge_d = nb.attr("edge_d")
    if not inner and not knit:
        st = _stitch(nb, tc, edge_d)
        col = nb.mix(nb.math('MULTIPLY', st, 0.6), col, nb.rgb(tuple(c * 0.55 for c in base_a)))
    if mud:
        # dust and splashed mud toward the hem / boots, damp darkening right at the bottom
        lowz = nb.maprange(z, 0.62, 0.25)
        splash = nb.maprange(nb.noise(tc, 38.0, 6.0, 0.7), 0.42, 0.62)
        m = nb.math('MULTIPLY', lowz, splash, clamp=True)
        col = nb.mix(nb.math('MULTIPLY', m, 0.75), col, nb.rgb((0.055, 0.045, 0.032)))
        damp = nb.math('MULTIPLY', nb.maprange(z, 0.46, 0.34), nb.maprange(n_mid, 0.3, 0.7, 0.4, 1.0))
        col = nb.mix(nb.math('MULTIPLY', damp, 0.45), col, nb.rgb(tuple(c * 0.55 for c in base_a)))
    if inner:
        col = nb.mix(0.0, nb.rgb(tuple(c * 0.55 for c in base_a)), col)
    felt = nb.noise(tc, 3200.0, 3.0, 0.7)
    h = nb.math('ADD', nb.math('MULTIPLY', fuzz, 0.5), nb.math('MULTIPLY', heather, 0.3))
    h = nb.math('ADD', h, nb.math('MULTIPLY', felt, 0.35))
    # soft creases (stretched noise, mostly vertical on the coat)
    cr = nb.noise(nb.mapping(tc, (1, 1, 0.22)), 7.0, 4.0, 0.55, dist=0.4)
    h = nb.math('ADD', h, nb.math('MULTIPLY', nb.maprange(cr, 0.3, 0.7), 3.0))
    if knit:
        rib = nb.wave(tc, 260.0, 'BANDS', 'Z', dist=1.5, detail=1.0)
        h = nb.math('ADD', h, nb.math('MULTIPLY', rib, 0.9))
    nrm = nb.bump(h, 0.0007, 0.75)
    return finish(mat, nb, col, rough, 0.0, nrm)


# ------------------------------------------------------------------------------------- leather
def mat_leather(name, boot=False):
    mat = new_material(name)
    nb = NB(mat)
    tc, geo, z = _common(nb)
    n_mid = nb.noise(tc, 30.0, 5.0, 0.6)
    grain = nb.maprange(nb.voronoi(tc, 900.0, 1.0), 0.0, 0.9)
    pores = nb.noise(tc, 2600.0, 2.0, 0.5)
    convex = nb.maprange(geo.outputs['Pointiness'], 0.51, 0.58, smooth=True)
    base = nb.mix(nb.maprange(n_mid, 0.35, 0.65), nb.rgb((0.0085, 0.0078, 0.0070)), nb.rgb((0.016, 0.014, 0.012)))
    worn = nb.math('MULTIPLY', convex, nb.maprange(n_mid, 0.35, 0.7, 0.3, 1.0))
    col = nb.mix(worn, base, nb.rgb((0.045, 0.034, 0.025)))
    dust = nb.maprange(nb.noise(tc, 12.0, 4.0, 0.6), 0.5, 0.7)
    col = nb.mix(nb.math('MULTIPLY', dust, 0.35), col, nb.rgb((0.05, 0.048, 0.044)))
    rough = nb.math('ADD', 0.5, nb.math('MULTIPLY', grain, 0.12))
    rough = nb.mixf(worn, rough, 0.36)
    rough = nb.mixf(nb.math('MULTIPLY', dust, 0.6), rough, 0.8)
    edge_d = nb.attr("edge_d")
    st = _stitch(nb, tc, edge_d, 0.0025, 0.0045, 0.0035)
    col = nb.mix(nb.math('MULTIPLY', st, 0.8), col, nb.rgb((0.03, 0.026, 0.02)))
    if boot:
        mud = nb.math('MULTIPLY', nb.maprange(z, 0.16, 0.03), nb.maprange(nb.noise(tc, 25.0, 6.0, 0.7), 0.35, 0.6))
        mud = nb.math('ADD', mud, nb.math('MULTIPLY', nb.maprange(z, 0.05, 0.0), 0.8), clamp=True)
        col = nb.mix(mud, col, nb.rgb((0.05, 0.04, 0.028)))
        rough = nb.mixf(mud, rough, 0.9)
        crease = nb.maprange(nb.wave(nb.mapping(tc, (1, 1, 1)), 55.0, 'BANDS', 'Z', dist=6.0, detail=2.0), 0.75, 1.0)
        crease = nb.math('MULTIPLY', crease, nb.math('MULTIPLY', nb.maprange(z, 0.10, 0.16),
                                                    nb.maprange(z, 0.30, 0.20)))
        h_extra = nb.math('MULTIPLY', crease, -1.5)
    else:
        h_extra = 0.0
    h = nb.math('ADD', nb.math('MULTIPLY', grain, 0.15), nb.math('MULTIPLY', pores, 0.05))
    h = nb.math('ADD', h, h_extra)
    h = nb.math('ADD', h, nb.math('MULTIPLY', st, 0.25))
    nrm = nb.bump(h, 0.0004, 0.8)
    return finish(mat, nb, col, rough, 0.0, nrm)


# ------------------------------------------------------------------------------------- painted steel
def mat_paint(name, color, rough_base=0.72, sand=1.0, chip_attr=None, chip=0.4, metal_under=(0.03, 0.03, 0.03)):
    """Matt painted steel (helmet, canister, buttons). chip_attr: float attribute (1 at edges)."""
    mat = new_material(name)
    nb = NB(mat)
    tc, geo, z = _common(nb)
    n_big = nb.noise(tc, 9.0, 4.0, 0.6)
    n_mid = nb.noise(tc, 80.0, 5.0, 0.6)
    sandn = nb.noise(tc, 2200.0, 2.0, 0.6)
    base = nb.mix(nb.maprange(n_big, 0.35, 0.65), nb.rgb(tuple(c * 0.85 for c in color)), nb.rgb(tuple(c * 1.15 for c in color)))
    base = nb.mix(nb.math('MULTIPLY', nb.maprange(sandn, 0.4, 0.7), 0.3), base, nb.rgb(tuple(c * 1.4 for c in color)))
    convex = nb.maprange(geo.outputs['Pointiness'], 0.52, 0.62, smooth=True)
    edge = convex
    if chip_attr:
        edge = nb.math('MAXIMUM', convex, nb.attr(chip_attr))
    chipm = nb.math('MULTIPLY', edge, nb.maprange(n_mid, 0.5 - chip * 0.3, 0.75 - chip * 0.3))
    chipm = nb.maprange(chipm, 0.45, 0.6)
    scuff = nb.math('MULTIPLY', nb.maprange(nb.noise(nb.mapping(tc, (40, 40, 400)), 1.0, 2.0, 0.5), 0.68, 0.74),
                    nb.maprange(n_big, 0.5, 0.7))
    col = nb.mix(nb.math('MULTIPLY', scuff, 0.4), base, nb.rgb(tuple(c * 1.6 for c in color)))
    rust = nb.mix(nb.maprange(n_mid, 0.4, 0.7), nb.rgb(metal_under), nb.rgb((0.05, 0.022, 0.010)))
    col = nb.mix(chipm, col, rust)
    rough = nb.math('ADD', rough_base, nb.math('MULTIPLY', sandn, 0.1))
    rough = nb.mixf(chipm, rough, 0.45)
    metal = nb.mixf(chipm, 0.0, 0.75)
    h = nb.math('MULTIPLY', sandn, 0.3 * sand)
    h = nb.math('SUBTRACT', h, nb.math('MULTIPLY', chipm, 0.6))
    nrm = nb.bump(h, 0.00025, 1.0)
    return finish(mat, nb, col, rough, metal, nrm)


def mat_metal(name, color, rough=0.4, metal=1.0, noise_amt=0.15):
    mat = new_material(name)
    nb = NB(mat)
    tc, geo, z = _common(nb)
    n = nb.noise(tc, 300.0, 4.0, 0.6)
    col = nb.mix(n, nb.rgb(tuple(c * (1 - noise_amt) for c in color)), nb.rgb(tuple(c * (1 + noise_amt) for c in color)))
    r = nb.math('ADD', rough, nb.math('MULTIPLY', n, 0.1))
    nrm = nb.bump(nb.noise(tc, 3000.0, 2.0), 0.00005)
    return finish(mat, nb, col, r, metal, nrm)


def mat_canvas(name, color, felt=False):
    mat = new_material(name)
    nb = NB(mat)
    tc, geo, z = _common(nb)
    n_big = nb.noise(tc, 8.0, 4.0, 0.6)
    fine = nb.noise(tc, 1800.0, 3.0, 0.6)
    base = nb.mix(nb.maprange(n_big, 0.3, 0.7), nb.rgb(tuple(c * 0.8 for c in color)), nb.rgb(tuple(c * 1.15 for c in color)))
    convex = nb.maprange(geo.outputs['Pointiness'], 0.52, 0.6, smooth=True)
    col = nb.mix(nb.math('MULTIPLY', convex, 0.5), base, nb.rgb(tuple(c * 1.5 for c in color)))
    dirt = nb.maprange(nb.noise(tc, 20.0, 5.0, 0.7), 0.5, 0.7)
    col = nb.mix(nb.math('MULTIPLY', dirt, 0.5), col, nb.rgb((0.05, 0.042, 0.03)))
    if felt:
        h = nb.math('MULTIPLY', fine, 0.6)
    else:
        w1 = nb.wave(nb.mapping(tc, (1, 1, 1), rot=(0, 0, 0.6)), 700.0, 'BANDS', 'X')
        w2 = nb.wave(nb.mapping(tc, (1, 1, 1), rot=(0, 0, 0.6)), 700.0, 'BANDS', 'Y')
        h = nb.math('ADD', nb.math('MULTIPLY', w1, 0.4), nb.math('MULTIPLY', w2, 0.4))
        h = nb.math('ADD', h, nb.math('MULTIPLY', fine, 0.3))
        st = _stitch(nb, tc, nb.attr("edge_d"), 0.004, 0.006, 0.004)
        col = nb.mix(nb.math('MULTIPLY', st, 0.6), col, nb.rgb(tuple(c * 0.6 for c in color)))
    rough = nb.math('ADD', 0.88, nb.math('MULTIPLY', fine, 0.08))
    nrm = nb.bump(h, 0.0004, 0.7)
    return finish(mat, nb, col, rough, 0.0, nrm)


def mat_wood(name, color):
    mat = new_material(name)
    nb = NB(mat)
    tc, geo, z = _common(nb)
    grain = nb.wave(nb.mapping(tc, (1, 1, 1)), 30.0, 'RINGS', 'Y', dist=8.0, detail=3.0)
    fine = nb.noise(nb.mapping(tc, (60, 4, 60)), 20.0, 4.0, 0.6)
    t = nb.math('ADD', nb.math('MULTIPLY', grain, 0.6), nb.math('MULTIPLY', fine, 0.4))
    col = nb.mix(t, nb.rgb(tuple(c * 0.65 for c in color)), nb.rgb(tuple(c * 1.25 for c in color)))
    rough = nb.math('ADD', 0.45, nb.math('MULTIPLY', fine, 0.15))
    nrm = nb.bump(t, 0.0002, 0.6)
    return finish(mat, nb, col, rough, 0.0, nrm)


def mat_skin(name):
    """Deliberately dark and simple: faces are never seen (dusk, helmet brim shadow)."""
    mat = new_material(name)
    nb = NB(mat)
    tc, geo, z = _common(nb)
    s = nb.sep(tc)
    n = nb.noise(tc, 60.0, 4.0, 0.6)
    skin = nb.mix(n, nb.rgb((0.075, 0.042, 0.030)), nb.rgb((0.10, 0.058, 0.040)))
    # stubble on the jaw, dark cropped hair above the ears and on the back of the head
    jaw = nb.math('MULTIPLY', nb.maprange(s['Z'], 1.62, 1.585), nb.maprange(s['Y'], 0.02, -0.05))
    skin = nb.mix(nb.math('MULTIPLY', jaw, 0.5), skin, nb.rgb((0.035, 0.025, 0.02)))
    hair = nb.math('MAXIMUM', nb.maprange(s['Z'], 1.69, 1.70),
                   nb.math('MULTIPLY', nb.maprange(s['Y'], 0.0, 0.04), nb.maprange(s['Z'], 1.62, 1.64)))
    col = nb.mix(hair, skin, nb.rgb((0.012, 0.010, 0.008)))
    # sockets in shadow
    eye = nb.math('MULTIPLY', nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', s['Z'], 1.663)), 0.014, 0.004),
                  nb.maprange(nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('ABSOLUTE', s['X']), 0.032)), 0.02, 0.008))
    col = nb.mix(nb.math('MULTIPLY', eye, 0.8), col, nb.rgb((0.02, 0.012, 0.01)))
    rough = nb.mixf(hair, 0.55, 0.8)
    nrm = nb.bump(nb.noise(tc, 1500.0, 2.0), 0.0002)
    return finish(mat, nb, col, rough, 0.0, nrm)


def build_soldier_mats(variant):
    piping = (0.55, 0.55, 0.52) if variant == "rifleman" else (0.70, 0.19, 0.02)
    feld = ((0.060, 0.066, 0.054), (0.085, 0.090, 0.074))
    M = {}
    M['wool_coat'] = mat_wool("wool_coat", *feld)
    M['wool_coat_in'] = mat_wool("wool_coat_in", (0.03, 0.032, 0.028), (0.04, 0.042, 0.036), mud=False, inner=True)
    M['wool_trouser'] = mat_wool("wool_trouser", (0.052, 0.056, 0.048), (0.07, 0.074, 0.063))
    M['wool_tunic'] = mat_wool("wool_tunic", (0.04, 0.05, 0.04), (0.055, 0.065, 0.052), mud=False)
    M['glove'] = mat_wool("glove", (0.036, 0.038, 0.034), (0.05, 0.052, 0.046), mud=False, knit=True)
    M['leather'] = mat_leather("leather")
    M['leather_boot'] = mat_leather("leather_boot", boot=True)
    M['helmet'] = mat_paint("helmet", (0.052, 0.058, 0.050), 0.78, 1.4, chip_attr="rim", chip=0.3)
    M['helmet_in'] = mat_paint("helmet_in", (0.03, 0.03, 0.027), 0.7, 0.5, chip=0.0)
    M['liner'] = mat_leather("liner")
    M['button'] = mat_paint("button", (0.07, 0.072, 0.064), 0.5, 2.0, chip=0.3, metal_under=(0.3, 0.3, 0.3))
    M['canister'] = mat_paint("canister", (0.050, 0.058, 0.046), 0.52, 0.6, chip=0.35)
    M['cup'] = mat_paint("cup", (0.012, 0.012, 0.012), 0.45, 0.4, chip=0.4)
    M['canvas'] = mat_canvas("canvas", (0.05, 0.054, 0.038))
    M['felt'] = mat_canvas("felt", (0.07, 0.046, 0.028), felt=True)
    M['wood'] = mat_wood("wood", (0.10, 0.06, 0.03))
    M['steel'] = mat_metal("steel", (0.04, 0.04, 0.042), 0.45)
    M['steel_bright'] = mat_metal("steel_bright", (0.30, 0.30, 0.30), 0.38)
    M['skin'] = mat_skin("skin")
    M['piping'] = mat_metal("piping", piping, 0.85, 0.0, 0.08)
    M['sole'] = mat_leather("sole", boot=True)
    if variant == "feldgendarm":
        M['gorget'] = mat_paint("gorget", (0.14, 0.145, 0.14), 0.5, 0.4, chip=0.3, metal_under=(0.4, 0.4, 0.4))
        M['gorget_bright'] = mat_metal("gorget_bright", (0.50, 0.50, 0.48), 0.32)
        M['gorget_dark'] = mat_paint("gorget_dark", (0.018, 0.018, 0.018), 0.55, 0.3, chip=0.0)
        M['lumi'] = mat_metal("lumi", (0.40, 0.43, 0.32), 0.6, 0.0)
    viewport_colors(M, piping)
    return M


def build_rifle_mats():
    M = {}
    M['wood_stock'] = mat_wood("wood_stock", (0.085, 0.040, 0.018))
    M['blued'] = mat_paint("blued", (0.016, 0.017, 0.020), 0.5, 0.2, chip=0.45, metal_under=(0.25, 0.25, 0.25))
    for k in ('blued',):
        # blued steel is metal, not paint
        M[k]['bsdf'].inputs['Metallic'].default_value = 0.0
    M['steel_bright'] = mat_metal("rifle_steel_bright", (0.32, 0.32, 0.32), 0.42)
    M['sling'] = mat_leather("sling")
    return M


# ------------------------------------------------------------------------------------- baking
def setup_cycles(samples, force_cpu=False):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.device = 'CPU'
    if force_cpu:
        return
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for dev_type in ('OPTIX', 'CUDA', 'ONEAPI'):
            try:
                prefs.compute_device_type = dev_type
            except Exception:
                continue
            prefs.get_devices()
            got = False
            for d in prefs.devices:
                d.use = (d.type == dev_type)
                got = got or d.use
            if got:
                sc.cycles.device = 'GPU'
                return
    except Exception as e:
        log("GPU setup failed, CPU:", e)


def select_only(objs, active=None):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def bake_atlas(objs, infos, prefix, res, channels, tex_dir, ao_samples=48, force_cpu=False):
    sc = bpy.context.scene
    setup_cycles(8, force_cpu)
    sc.render.bake.margin = 16
    sc.render.bake.margin_type = 'EXTEND'
    sc.render.bake.use_clear = True
    sc.render.bake.normal_space = 'TANGENT'
    sc.render.bake.normal_r = 'POS_X'
    sc.render.bake.normal_g = 'POS_Y'
    sc.render.bake.normal_b = 'POS_Z'
    os.makedirs(tex_dir, exist_ok=True)
    results = {}
    for ch in channels:
        img = bpy.data.images.new(f"{prefix}_{ch}", res, res, alpha=False, float_buffer=(ch == 'normal'))
        img.colorspace_settings.name = 'sRGB' if ch == 'color' else 'Non-Color'
        for inf in infos:
            nb = inf['nb']
            inf['img'].image = img
            nb.nt.nodes.active = inf['img']
            for l in list(inf['out'].inputs['Surface'].links):
                nb.L.remove(l)
            if ch in ('color', 'rough', 'metal'):
                for l in list(inf['emit'].inputs['Color'].links):
                    nb.L.remove(l)
                nb.put(inf['emit'].inputs['Color'], inf['sock'][ch])
                nb.L.new(inf['emit'].outputs[0], inf['out'].inputs['Surface'])
            else:
                nb.L.new(inf['bsdf'].outputs[0], inf['out'].inputs['Surface'])
        btype = {'color': 'EMIT', 'rough': 'EMIT', 'metal': 'EMIT', 'normal': 'NORMAL', 'ao': 'AO'}[ch]
        sc.cycles.samples = ao_samples if ch == 'ao' else (4 if ch == 'normal' else 2)
        sc.cycles.use_denoising = False
        if sc.world:
            sc.world.light_settings.distance = 0.035   # local crevice AO only (limbs move)
        select_only(objs)
        t = time.time()
        bpy.ops.object.bake(type=btype, margin=16, use_clear=True)
        log(f"baked {prefix}_{ch} ({btype}) in {time.time()-t:.1f}s")
        path = os.path.join(tex_dir, f"{prefix}_{ch}.png")
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
        results[ch] = img
    for inf in infos:
        nb = inf['nb']
        for l in list(inf['out'].inputs['Surface'].links):
            nb.L.remove(l)
        nb.L.new(inf['bsdf'].outputs[0], inf['out'].inputs['Surface'])
    return results


def combine_ao(color_img, ao_img, strength):
    n = color_img.size[0] * color_img.size[1] * 4
    c = np.empty(n, np.float32)
    color_img.pixels.foreach_get(c)
    a = np.empty(n, np.float32)
    ao_img.pixels.foreach_get(a)
    c = c.reshape(-1, 4)
    a = a.reshape(-1, 4)
    c[:, :3] *= 1.0 - strength * (1.0 - a[:, :1])
    color_img.pixels.foreach_set(c.ravel())
    color_img.update()
    color_img.save()


def final_material(name, imgs):
    mat = new_material(name)
    nb = NB(mat)
    out = nb.new('ShaderNodeOutputMaterial')
    bsdf = nb.new('ShaderNodeBsdfPrincipled')
    nb.L.new(bsdf.outputs[0], out.inputs['Surface'])

    def tex(img, noncolor):
        t = nb.new('ShaderNodeTexImage')
        t.image = img
        img.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
        return t
    nb.L.new(tex(imgs['color'], False).outputs['Color'], bsdf.inputs['Base Color'])
    nb.L.new(tex(imgs['rough'], True).outputs['Color'], bsdf.inputs['Roughness'])
    if 'metal' in imgs:
        nb.L.new(tex(imgs['metal'], True).outputs['Color'], bsdf.inputs['Metallic'])
    else:
        bsdf.inputs['Metallic'].default_value = 0.0
    nm = nb.new('ShaderNodeNormalMap')
    nb.L.new(tex(imgs['normal'], True).outputs['Color'], nm.inputs['Color'])
    nb.L.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def replace_materials(objs, mat):
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(mat)
        o.data.polygons.foreach_set("material_index", [0] * len(o.data.polygons))


def unwrap_pack(ob, smart_mask=None, scale_mats=None, margin=0.002):
    """smart_mask: per-polygon bools to smart-project (others keep their metric UVs).
    scale_mats: {material name: uv scale} for hidden faces."""
    select_only([ob])
    me = ob.data
    if smart_mask is not None and any(smart_mask):
        me.polygons.foreach_set("select", smart_mask)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.uv.smart_project(angle_limit=1.1, island_margin=0.002, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode='OBJECT')
    if scale_mats:
        uv = me.uv_layers.active.data
        for p in me.polygons:
            mname = me.materials[p.material_index].name
            if mname in scale_mats:
                k = scale_mats[mname]
                for li in p.loop_indices:
                    uv[li].uv = uv[li].uv * k
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def viewport_colors(M, piping):
    cols = {'wool_coat': (0.30, 0.32, 0.27), 'wool_trouser': (0.25, 0.27, 0.23), 'leather': (0.05, 0.05, 0.05),
            'leather_boot': (0.06, 0.06, 0.06), 'helmet': (0.25, 0.28, 0.24), 'skin': (0.4, 0.28, 0.22),
            'canvas': (0.28, 0.29, 0.2), 'felt': (0.35, 0.25, 0.15), 'canister': (0.27, 0.30, 0.25),
            'piping': piping, 'glove': (0.2, 0.2, 0.2), 'button': (0.4, 0.4, 0.4), 'wood': (0.4, 0.25, 0.1),
            'steel': (0.2, 0.2, 0.2), 'gorget': (0.6, 0.6, 0.6), 'gorget_bright': (0.9, 0.9, 0.9),
            'gorget_dark': (0.1, 0.1, 0.1), 'wool_coat_in': (0.15, 0.16, 0.14), 'helmet_in': (0.15, 0.15, 0.14),
            'liner': (0.1, 0.07, 0.05), 'sole': (0.05, 0.05, 0.05), 'wool_tunic': (0.2, 0.25, 0.2),
            'cup': (0.03, 0.03, 0.03), 'steel_bright': (0.6, 0.6, 0.6), 'lumi': (0.8, 0.8, 0.6)}
    for k, v in cols.items():
        if k in M:
            M[k]['mat'].diffuse_color = (v[0], v[1], v[2], 1.0)
