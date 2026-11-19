"""Kar98k (third-person / world model). Bore along Blender +Y (= Godot -Z), origin at the grip
(the wrist of the stock where the right hand holds it), bore axis 45 mm above the origin.

Objects: Stock, Barrel (barrel, receiver, bands, rear sight, trigger group), Bolt, FrontSight, Sling.
Empties: Muzzle, SightRear, SightFront.
"""
import math
import os
from math import cos, pi, sin, sqrt

import bpy
from mathutils import Matrix, Vector

import cmats
import cpreview
from cgeo import (Mesh, V, catmull, frames_along, interp_table, lathe, resample, rounded_box, sstep,
                  tri_count, torus)

BORE_Z = 0.045
BUTT_Y = -0.270
MUZZLE_Y = 0.840

#       y       hw     top     bottom
STOCK = [(-0.2705, 0.0205, 0.004, -0.118),
         (-0.262, 0.0215, 0.006, -0.116),
         (-0.220, 0.0220, 0.009, -0.106),
         (-0.150, 0.0212, 0.013, -0.086),
         (-0.085, 0.0190, 0.018, -0.061),
         (-0.035, 0.0160, 0.022, -0.033),
         (0.000, 0.0150, 0.024, -0.022),
         (0.030, 0.0165, 0.029, -0.026),
         (0.065, 0.0190, 0.032, -0.031),
         (0.120, 0.0198, 0.033, -0.034),
         (0.200, 0.0198, 0.033, -0.032),
         (0.235, 0.0190, 0.036, -0.012),
         (0.290, 0.0172, 0.040, 0.002),
         (0.400, 0.0160, 0.041, 0.010),
         (0.500, 0.0150, 0.042, 0.014),
         (0.585, 0.0140, 0.042, 0.019)]


def stock_ring(y, n=28, grow=0.0):
    hw, top, bot = interp_table(STOCK, y)
    hw += grow
    top += grow
    bot -= grow
    zc, hh = (top + bot) * 0.5, (top - bot) * 0.5
    pts = []
    for i in range(n):
        th = 2 * pi * i / n
        c, s = cos(th), sin(th)
        e = 2 / 2.6
        x = (abs(c) ** e) * (1 if c >= 0 else -1) * hw
        z = (abs(s) ** e) * (1 if s >= 0 else -1) * hh
        pts.append(V(x, y, zc + z))
    return pts


def build_stock():
    m = Mesh("Stock")
    ys = [-0.2705 + i * 0.012 for i in range(int((0.585 + 0.2705) / 0.012) + 1)] + [0.585]
    rings = [stock_ring(y) for y in ys]
    # rings advance along +Y; ring order: x=+hw at th=0 -> z up -> CCW about +Y? (x, z) with y = x cross z?  recalc handles it
    m.grid(rings, 'wood_stock', closed=True, cap0=True, cap1=True)
    # handguard over the barrel from the rear sight to the lower band
    hg = []
    for y in [0.30 + i * 0.02 for i in range(10)] + [0.488]:
        ring = []
        for i in range(13):
            a = pi * i / 12
            r = 0.0155
            ring.append(V(r * cos(a), y, BORE_Z + r * sin(a) * 0.95))
        hg.append(ring)
    m.grid(hg, 'wood_stock', closed=False, cap0=False)
    # butt plate
    bp0 = stock_ring(-0.2705, 28, 0.0006)
    bp1 = [V(p.x, -0.2745, p.z) for p in bp0]
    m.grid([bp1, bp0], 'blued', closed=True, cap0=True)
    # butt disc (right side)
    lathe(m, [(0.0, 0.0012), (0.0125, 0.0010), (0.0130, 0.0)], V(0.0205, -0.165, -0.040), V(0, 1, 0), V(0, 0, 1),
          V(1, 0, 0), 20, 'blued')
    ob = m.to_object()
    return ob


def build_barrel():
    m = Mesh("Barrel")
    ax_u, ax_v, ax_w = V(1, 0, 0), V(0, 0, 1), V(0, 1, 0)
    c0 = V(0, 0.0, BORE_Z)
    # receiver
    # receiver: rear bridge and front ring are full rings, the middle is open on top (bolt visible)
    lathe(m, [(0.0, 0.018), (0.0150, 0.018), (0.0160, 0.026), (0.0160, 0.062), (0.0, 0.062)],
          c0, ax_u, ax_v, ax_w, 28, 'blued')
    lathe(m, [(0.0, 0.165), (0.0165, 0.165), (0.0165, 0.245), (0.0155, 0.255), (0.0145, 0.26)],
          c0, ax_u, ax_v, ax_w, 28, 'blued')
    sec = []
    for i in range(15):
        a = math.radians(125 + (415 - 125) * i / 14)
        sec.append((0.0165 * math.cos(a), 0.0165 * math.sin(a)))
    for i in range(15):
        a = math.radians(415 - (415 - 125) * i / 14)
        sec.append((0.0103 * math.cos(a), 0.0103 * math.sin(a)))
    rings = [[V(x, y, BORE_Z + z) for x, z in sec] for y in (0.060, 0.167)]
    m.grid(rings, 'blued', closed=True)
    # barrel: stepped profile toward the muzzle
    prof = [(0.0145, 0.26), (0.0145, 0.33), (0.0130, 0.34), (0.0125, 0.48), (0.0115, 0.49), (0.0108, 0.60),
            (0.0102, 0.80), (0.0102, MUZZLE_Y - 0.002), (0.0085, MUZZLE_Y), (0.0042, MUZZLE_Y), (0.0042, MUZZLE_Y - 0.03)]
    lathe(m, prof, c0, ax_u, ax_v, ax_w, 24, 'blued')
    # rear sight base and leaf
    rounded_box(m, (0, 0.268, BORE_Z + 0.0135), (0.020, 0.050, 0.008), 0.002, 'blued', 1)
    rounded_box(m, (0, 0.262, BORE_Z + 0.0195), (0.016, 0.044, 0.003), 0.0008, 'blued', 1)
    rounded_box(m, (0, 0.243, BORE_Z + 0.0205), (0.018, 0.004, 0.006), 0.0008, 'blued', 1)
    # lower band with sling swivel on the left, and the nose cap with bayonet lug
    for y, L, r in ((0.400, 0.012, 0.0), (0.585, 0.030, 0.0)):
        ring_rings = []
        for yy in (y - L / 2, y + L / 2):
            pts = stock_ring(min(yy, 0.585), 28, 0.0012)
            top = [V(p.x, yy, p.z) for p in pts]
            ring_rings.append(top)
        m.grid(ring_rings, 'blued', closed=True)
    torus(m, V(-0.024, 0.400, 0.018), V(1, 0, 0), 0.0075, 0.0015, 14, 6, 'blued')
    rounded_box(m, (0, 0.590, BORE_Z - 0.0175), (0.012, 0.028, 0.009), 0.002, 'blued', 1)
    lathe(m, [(0.0, 0.0), (0.0035, 0.0), (0.0035, 0.028), (0.0045, 0.03), (0.0, 0.034)], V(0, 0.595, BORE_Z - 0.026),
          ax_u, ax_v, ax_w, 10, 'rifle_steel_bright')
    # trigger guard + floorplate + trigger
    path = catmull([V(0, 0.015, -0.020), V(0, 0.022, -0.050), V(0, 0.055, -0.058), V(0, 0.085, -0.050),
                    V(0, 0.095, -0.033)], 5)
    fr = frames_along(path, V(1, 0, 0))
    rings = []
    for p, (T, N, B) in zip(path, fr):
        rings.append([p + N * (0.0045 * cos(2 * pi * i / 8)) + B * (0.0022 * sin(2 * pi * i / 8)) for i in range(8)])
    m.grid(rings, 'blued', closed=True, cap0=True, cap1=True)
    rounded_box(m, (0, 0.150, -0.0345), (0.026, 0.115, 0.004), 0.0015, 'blued', 1)
    rounded_box(m, (0, 0.045, -0.040), (0.004, 0.006, 0.020), 0.0012, 'blued', 1, Matrix.Rotation(-0.35, 4, 'X'))
    # sling eyelet in the butt (left side)
    torus(m, V(-0.0205, -0.165, -0.075), V(1, 0, 0), 0.010, 0.0016, 16, 6, 'blued')
    return m.to_object()


def build_bolt():
    m = Mesh("Bolt")
    c0 = V(0, 0.0, BORE_Z)
    lathe(m, [(0.0, -0.040), (0.010, -0.040), (0.0125, -0.030), (0.0125, -0.002), (0.0095, 0.0), (0.0095, 0.13),
              (0.0, 0.13)], c0, V(1, 0, 0), V(0, 0, 1), V(0, 1, 0), 22, 'rifle_steel_bright')
    # safety wing on the shroud
    rounded_box(m, (0, -0.028, BORE_Z + 0.016), (0.004, 0.012, 0.010), 0.0012, 'blued', 1)
    # bent bolt handle with ball knob, on the right (+X)
    path = catmull([V(0.008, 0.055, BORE_Z), V(0.028, 0.058, BORE_Z - 0.006), V(0.042, 0.060, BORE_Z - 0.020),
                    V(0.048, 0.060, BORE_Z - 0.032)], 5)
    fr = frames_along(path, V(0, 1, 0))
    rings = []
    for k, (p, (T, N, B)) in enumerate(zip(path, fr)):
        r = 0.0055 - 0.0012 * k / len(path)
        rings.append([p + N * (r * cos(2 * pi * i / 10)) + B * (r * sin(2 * pi * i / 10)) for i in range(10)])
    m.grid(rings, 'rifle_steel_bright', closed=True, cap0=True)
    knob = V(0.050, 0.060, BORE_Z - 0.040)
    lathe(m, [(0.0, -0.0095), (0.006, -0.008), (0.0095, -0.002), (0.0095, 0.002), (0.006, 0.008), (0.0, 0.0095)],
          knob, V(1, 0, 0), V(0, 1, 0), V(0, 0, 1), 16, 'rifle_steel_bright')
    return m.to_object()


def build_front_sight():
    m = Mesh("FrontSight")
    y0 = 0.812
    rounded_box(m, (0, y0, BORE_Z + 0.0125), (0.012, 0.022, 0.006), 0.0015, 'blued', 1)
    rounded_box(m, (0, y0 + 0.002, BORE_Z + 0.0195), (0.0022, 0.004, 0.011), 0.0005, 'blued', 1)
    # hood
    rings = []
    for y in (y0 - 0.011, y0 + 0.011):
        ring = []
        for i in range(15):
            a = pi * i / 14
            ring.append(V(0.0125 * cos(a), y, BORE_Z + 0.013 + 0.0125 * sin(a)))
        rings.append(ring)
    m.grid(rings, 'blued', closed=False)
    ob = m.to_object(recalc=False)
    md = ob.modifiers.new("s", 'SOLIDIFY')
    md.thickness = 0.0012
    from cgeo import apply_modifiers
    apply_modifiers(ob)
    return ob


def build_sling():
    m = Mesh("Sling")
    a = V(-0.026, 0.400, 0.016)
    b = V(-0.026, -0.165, -0.075)
    pts = []
    n = 40
    for k in range(n + 1):
        t = k / n
        p = a.lerp(b, t)
        sag = 0.035 * 4 * t * (1 - t)
        pts.append(p + V(-0.006 * 4 * t * (1 - t), 0, -sag))
    pts = [a + V(0, 0.012, 0.004)] + pts + [b + V(0, -0.012, 0.0)]
    fr = frames_along(pts, V(1, 0, 0))
    rings = []
    hw, ht = 0.0125, 0.0016
    for p, (T, N, B) in zip(pts, fr):
        sec = [(ht, hw), (-ht, hw), (-ht, -hw), (ht, -hw)]
        rings.append([p + N * x + B * y for x, y in sec])
    m.grid(rings, 'sling', closed=True, cap0=True, cap1=True)
    # buckle / keeper
    p = pts[len(pts) // 3]
    T, N, B = fr[len(pts) // 3]
    X = Matrix((N, B, T)).transposed().to_4x4()
    rounded_box(m, (0, 0, 0), (0.007, 0.030, 0.012), 0.0015, 'blued', 1, Matrix.Translation(p) @ X)
    return m.to_object()


def build(path, res, bake, previews, samples, prev_dir, tex_dir, cpu, export_glb, inspect_glb, log):
    log("=== kar98k")
    M = cmats.build_rifle_mats()
    obs = [build_stock(), build_barrel(), build_bolt(), build_front_sight(), build_sling()]
    for o in obs:
        log(f"  {o.name}: {tri_count(o)} tris")
    log(f"  TOTAL {sum(tri_count(o) for o in obs)} tris")
    empties = {}
    for nm, p in (("Muzzle", (0, MUZZLE_Y, BORE_Z)), ("SightRear", (0, 0.243, BORE_Z + 0.0235)),
                  ("SightFront", (0, 0.814, BORE_Z + 0.025))):
        e = bpy.data.objects.new(nm, None)
        bpy.context.scene.collection.objects.link(e)
        e.empty_display_size = 0.02
        e.location = p
        empties[nm] = e
    if bake:
        cmats.select_only(obs, obs[0])
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
        bpy.ops.object.mode_set(mode='OBJECT')
        imgs = cmats.bake_atlas(obs, list(M.values()), "kar98k", res, ['color', 'rough', 'metal', 'normal', 'ao'],
                                tex_dir, ao_samples=48, force_cpu=cpu)
        cmats.combine_ao(imgs['color'], imgs['ao'], 0.6)
        fm = cmats.final_material("Kar98k", imgs)
        cmats.replace_materials(obs, fm)
        export_glb(path, obs + list(empties.values()), False)
        info = inspect_glb(path)
        log(f"  GLB {os.path.basename(path)}: {info['size']/1e6:.1f} MB tris {info['tris']} ICC left {info['icc']}")
        log(f"  nodes: {info['names']}")
    if previews:
        cpreview.render_dusk("kar98k", prev_dir, samples, views=[
            ("side_r", (1.9, 0.28, 0.05), (0, 0.28, 0.0), 35), ("side_l", (-1.9, 0.28, 0.05), (0, 0.28, 0.0), 35),
            ("action", (0.30, -0.12, 0.20), (0, 0.10, 0.03), 40), ("muzzle", (0.18, 1.05, 0.14), (0, 0.8, 0.05), 40)],
            res=(1400, 800), ground_z=-0.4)
    log("=== kar98k done")
