"""Village props. Each builder returns (visual_objects, collision_objects, empties, tri_count, preview_kwargs).
Origins at ground centre (wall_lantern: wall mounting point), front faces Blender -Y."""
import math
import random
import textwrap

import bmesh
from mathutils import Matrix, Vector

from geo import (MB, bm_box, bm_box_minmax, bm_cyl, bm_prism, bm_quad, collision_bm, collision_box, empty,
                 text_bm)

PI = math.pi


def roff(rng):
    return (rng.random(), rng.random())


# ---------------------------------------------------------------- helpers
def lathe(profile, segs=16, cap_top=True, cap_bottom=True):
    """Revolve [(r, z), ...] (bottom to top) around Z."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(segs):
            a = 2 * PI * i / segs
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    if cap_bottom and profile[0][0] > 1e-4:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and profile[-1][0] > 1e-4:
        bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def tube(points, r, segs=5):
    """Polyline tube."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    rings = []
    for k, p in enumerate(pts):
        if k == 0:
            d = (pts[1] - pts[0])
        elif k == len(pts) - 1:
            d = (pts[-1] - pts[-2])
        else:
            d = (pts[k + 1] - pts[k - 1])
        d.normalize()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(up).normalized()
        v = d.cross(u).normalized()
        ring = [bm.verts.new(p + (u * math.cos(2 * PI * i / segs) + v * math.sin(2 * PI * i / segs)) * r) for i in range(segs)]
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def cyl_uv(radius_scale=1.0, scale=1.0):
    def f(co, n):
        ang = math.atan2(co.y, co.x)
        r = math.hypot(co.x, co.y)
        if abs(n.z) > 0.7:
            return (co.x * scale, co.y * scale)
        return (ang * max(r, 0.05) * scale * radius_scale, co.z * scale)
    return f


def noisy_stone(cx, cy, cz, sx, sy, sz, rng, rough=0.012, rot=0.05):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=2, use_grid_fill=True)
    ph = [rng.uniform(0, 10) for _ in range(6)]
    for v in bm.verts:
        co = v.co.copy()
        # round the box a little, then add lumpy noise
        lim = Vector((abs(co.x) * 2, abs(co.y) * 2, abs(co.z) * 2))
        corner = (lim.x > 0.99) + (lim.y > 0.99) + (lim.z > 0.99)
        shrink = 1.0 - 0.07 * max(0, corner - 1)
        co *= shrink
        co.x *= sx
        co.y *= sy
        co.z *= sz
        nse = (math.sin(co.x * 13 + ph[0]) * math.sin(co.y * 11 + ph[1]) * math.sin(co.z * 17 + ph[2])
               + 0.5 * math.sin(co.x * 29 + ph[3]) * math.sin(co.z * 23 + ph[4]))
        v.co = co + co.normalized() * nse * rough
    rm = Matrix.Rotation(rng.uniform(-rot, rot), 4, "Z") @ Matrix.Rotation(rng.uniform(-rot, rot), 4, "X")
    bmesh.ops.transform(bm, matrix=Matrix.Translation((cx, cy, cz)) @ rm, verts=bm.verts)
    return bm


# ================================================================ props
def telegraph_pole():
    rng = random.Random(1)
    mb = MB()
    H = 7.5
    pole = lathe([(0.135, -0.6), (0.13, 0.0), (0.115, 3.0), (0.095, H - 0.1), (0.09, H), (0.0, H + 0.05)], segs=14)
    mb.add_bm(pole, "Wood_dark", uv=cyl_uv(scale=1.0), smooth=True, smooth_angle=50)
    empties = []
    xs = (-0.55, -0.2, 0.2, 0.55)
    for k, za in enumerate((H - 0.35, H - 0.85)):
        mb.add_bm(bm_box(0.0, -0.13, za, 1.4, 0.09, 0.11, bevel=0.008, segs=1), "Wood_dark", scale=1.0, off=roff(rng))
        # braces
        for sx in (-1, 1):
            mb.add_bm(tube([(sx * 0.45, -0.13, za - 0.05), (0.0, -0.1, za - 0.55)], 0.012, 5), "Iron", scale=2.0)
        for i, x in enumerate(xs if k == 0 else (-0.55, 0.55)):
            mb.add_bm(bm_cyl(0.008, 0.008, 0.11, segs=6), "Iron", matrix=Matrix.Translation((x, -0.13, za + 0.055)), scale=2.0)
            ins = lathe([(0.0, 0.0), (0.042, 0.002), (0.045, 0.03), (0.03, 0.04), (0.028, 0.06), (0.036, 0.07),
                         (0.03, 0.09), (0.0, 0.1)], segs=10)
            mb.add_bm(ins, "InsulatorGlass", matrix=Matrix.Translation((x, -0.13, za + 0.095)), smooth=True, smooth_angle=60)
            if k == 0:
                empties.append(empty(f"WireAttach_{i}", (x, -0.13, za + 0.155)))
    # pole step bolts and an enamel PTT plate
    for i in range(6):
        z = 2.4 + i * 0.4
        ang = PI / 2 * (i % 2) + PI / 4
        mb.add_bm(tube([(0.1 * math.cos(ang), 0.1 * math.sin(ang), z), (0.28 * math.cos(ang), 0.28 * math.sin(ang), z + 0.02)], 0.01, 5), "Iron", scale=2.0)
    mb.add_bm(bm_box(0.0, -0.13, 2.2, 0.09, 0.006, 0.13), "BlackPaint", scale=2.0)
    ob = mb.build("telegraph_pole")
    col = collision_bm("Pole", lathe([(0.14, -0.6), (0.1, H)], segs=8), suffix="-convcolonly")
    return [ob], [col], empties, mb.tri_count(), dict(elev=4, azim=-30, dist_mul=0.5, ground="grass_winter", target=(0, 0, 6.6))


def wayside_cross():
    rng = random.Random(2)
    mb = MB()
    z = 0.0
    for (s, h) in ((1.7, 0.24), (1.3, 0.24), (0.9, 0.22)):
        mb.add_bm(noisy_stone(0, 0, z + h / 2, s, s, h, rng, rough=0.01, rot=0.01), "Granite", off=roff(rng), smooth=True, smooth_angle=40)
        z += h
    mb.add_bm(bm_box(0, 0, z + 0.25, 0.55, 0.55, 0.5, bevel=0.03, segs=2), "Granite", off=roff(rng))
    z += 0.5
    shaft = lathe([(0.17, z - 0.02), (0.15, z + 2.0), (0.14, z + 2.1)], segs=8)
    mb.add_bm(shaft, "Granite", uv=cyl_uv(scale=0.5), off=roff(rng))
    z += 2.0
    # cross head with chamfered, slightly flared arms
    mb.add_bm(bm_box(0, 0, z + 0.42, 0.17, 0.15, 0.95, bevel=0.025, segs=2), "Granite", off=roff(rng))
    mb.add_bm(bm_box(0, 0, z + 0.55, 0.78, 0.15, 0.17, bevel=0.025, segs=2), "Granite", off=roff(rng))
    for sx in (-1, 1):
        mb.add_bm(bm_box(sx * 0.36, 0, z + 0.55, 0.08, 0.17, 0.22, bevel=0.02, segs=2), "Granite", off=roff(rng))
    mb.add_bm(bm_box(0, 0, z + 0.87, 0.21, 0.17, 0.08, bevel=0.02, segs=2), "Granite", off=roff(rng))
    ob = mb.build("wayside_cross")
    cols = [collision_box("Steps", -0.85, -0.85, 0, 0.85, 0.85, 0.7),
            collision_box("Shaft", -0.28, -0.28, 0.7, 0.28, 0.28, z + 0.95)]
    return [ob], cols, [], mb.tri_count(), dict(elev=8, azim=-28, dist_mul=1.15, ground="grass_winter")


def sentry_box():
    rng = random.Random(3)
    mb = MB()
    W, D, H = 1.0, 1.0, 2.25
    t = 0.04
    S = "Stripes"
    uvs = dict(scale=1.0)
    # floor plinth
    mb.add_bm(bm_box_minmax(-W / 2 - 0.03, -D / 2 - 0.03, 0.0, W / 2 + 0.03, D / 2 + 0.03, 0.12), "Wood_dark", scale=1.0)
    # back + sides (striped outside, dark inside via a thin inner skin)
    mb.add_bm(bm_box_minmax(-W / 2, D / 2 - t, 0.12, W / 2, D / 2, H), S, **uvs)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * W / 2, sx * (W / 2 - t)))
        mb.add_bm(bm_box_minmax(x0, -D / 2, 0.12, x1, D / 2, H), S, **uvs)
        xa, xb = sorted((sx * (W / 2 - t), sx * (W / 2 - t - 0.005)))
        mb.add_bm(bm_box_minmax(xa, -D / 2 + 0.02, 0.12, xb, D / 2 - t, H), "Wood_dark", scale=1.0)
        # front posts
        pa, pb = sorted((sx * W / 2, sx * (W / 2 - 0.13)))
        mb.add_bm(bm_box_minmax(pa, -D / 2 - 0.01, 0.12, pb, -D / 2 + 0.04, H), S, **uvs)
    mb.add_bm(bm_box_minmax(-W / 2 + t, D / 2 - t - 0.005, 0.12, W / 2 - t, D / 2 - t, H), "Wood_dark", scale=1.0)
    mb.add_bm(bm_box_minmax(-W / 2, -D / 2 - 0.01, H - 0.22, W / 2, -D / 2 + 0.04, H), S, **uvs)
    # seat ledge inside
    mb.add_bm(bm_box_minmax(-W / 2 + t, 0.15, 0.62, W / 2 - t, D / 2 - t, 0.66), "Wood_dark", scale=1.0)
    # pyramid roof with overhang, and a finial
    ov = 0.09
    apex = Vector((0, 0, H + 0.48))
    c = [Vector((-W / 2 - ov, -D / 2 - ov, H)), Vector((W / 2 + ov, -D / 2 - ov, H)),
         Vector((W / 2 + ov, D / 2 + ov, H)), Vector((-W / 2 - ov, D / 2 + ov, H))]
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in c]
    va = bm.verts.new(apex)
    vlow = [bm.verts.new(p - Vector((0, 0, 0.04))) for p in c]
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((vs[i], vs[j], va))
        bm.faces.new((vlow[i], vlow[j], vs[j], vs[i]))
    bm.faces.new(list(reversed(vlow)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mb.add_bm(bm, S, **uvs)
    mb.add_bm(lathe([(0.03, H + 0.44), (0.03, H + 0.56), (0.05, H + 0.6), (0.0, H + 0.66)], segs=8), "BlackPaint")
    ob = mb.build("sentry_box")
    cols = [collision_box("Back", -W / 2, D / 2 - t, 0, W / 2, D / 2, H + 0.4)]
    for sx in (-1, 1):
        x0, x1 = sorted((sx * W / 2, sx * (W / 2 - t)))
        cols.append(collision_box(f"Side{sx + 1}", x0, -D / 2, 0, x1, D / 2, H + 0.4))
    cols.append(collision_box("Roof", -W / 2 - ov, -D / 2 - ov, H - 0.22, W / 2 + ov, D / 2 + ov, H + 0.48))
    return [ob], cols, [], mb.tri_count(), dict(elev=8, azim=-30, dist_mul=0.8, ground="gravel")


def _bag(sx, sy, sz, rng):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=4, use_grid_fill=True)
    ph = rng.uniform(0, 6.28)
    for v in bm.verts:
        co = v.co * 2.0                          # -1..1
        r = co.length
        sph = co.normalized() * 0.92 if r > 0 else co
        co = co.lerp(sph, 0.45)
        co.z *= 0.75 + 0.25 * (1 - co.x * co.x)  # pillow: thinner at the tied ends
        co.y *= 0.85 + 0.15 * (1 - co.x * co.x)
        co.z += 0.06 * math.sin(co.x * 3 + ph)
        v.co = Vector((co.x * sx / 2, co.y * sy / 2, co.z * sz / 2))
    return bm


def sandbag_wall_2m():
    rng = random.Random(4)
    mb = MB()
    L, rows = 2.0, 7
    bl, bw, bh = 0.56, 0.32, 0.15
    z = bh / 2 - 0.02
    for r in range(rows):
        depth_rows = 2 if r < rows - 1 else 1
        for dr in range(depth_rows):
            y = (dr - 0.5) * bw * 0.95 if depth_rows == 2 else 0.0
            x = -L / 2 + bl / 2 - (bl / 2 if r % 2 else 0.0)
            while x - bl / 2 < L / 2 - 0.05:
                xa, xb = max(x - bl / 2, -L / 2), min(x + bl / 2, L / 2)
                if xb - xa > 0.16:
                    bm = _bag((xb - xa) * rng.uniform(0.96, 1.0), bw * rng.uniform(0.95, 1.05), bh * rng.uniform(0.9, 1.1), rng)
                    M = (Matrix.Translation(((xa + xb) / 2 + rng.uniform(-0.01, 0.01), y + rng.uniform(-0.02, 0.02), z))
                         @ Matrix.Rotation(rng.uniform(-0.06, 0.06), 4, "Z") @ Matrix.Rotation(rng.uniform(-0.04, 0.04), 4, "X"))
                    mb.add_bm(bm, "Burlap", scale=2.0, off=roff(rng), smooth=True, smooth_angle=70, matrix=M)
                x += bl * 0.98
        z += bh * 0.82
    ob = mb.build("sandbag_wall_2m")
    cols = [collision_box("Bags", -L / 2, -bw, 0, L / 2, bw, z + 0.03)]
    return [ob], cols, [], mb.tri_count(), dict(elev=14, azim=-25, dist_mul=0.8, ground="mud")


def _barbed(points, rng, mb, barb_step=0.11):
    """Barbed wire strand along a polyline: twisted wire + 4-point barbs."""
    pts = [Vector(p) for p in points]
    mb.add_bm(tube(pts, 0.0022, 4), "Iron", scale=4.0)
    total = sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))
    s = barb_step * 0.5
    seg = 0
    acc = 0.0
    while s < total:
        while seg < len(pts) - 2 and acc + (pts[seg + 1] - pts[seg]).length < s:
            acc += (pts[seg + 1] - pts[seg]).length
            seg += 1
        a, b = pts[seg], pts[seg + 1]
        d = (b - a).normalized()
        p = a + d * (s - acc)
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(up).normalized()
        v = d.cross(u).normalized()
        ang = rng.uniform(0, PI)
        for q in (u * math.cos(ang) + v * math.sin(ang), u * math.cos(ang + PI / 2) + v * math.sin(ang + PI / 2)):
            mb.add_bm(tube([p - q * 0.013 - d * 0.004, p + q * 0.013 + d * 0.004], 0.0014, 3), "Iron", scale=4.0)
        s += barb_step


def knife_rest_roadblock():
    """Spanischer Reiter: a 3 m beam with X-frames, wrapped in barbed wire."""
    rng = random.Random(5)
    mb = MB()
    L = 3.0
    leg = 1.7
    hb = 0.62                                          # beam height
    mb.add_bm(bm_box(0, 0, hb, L, 0.12, 0.12, bevel=0.01), "Wood_grey", scale=1.0, off=roff(rng))
    tips = []
    for x in (-L / 2 + 0.15, 0.0, L / 2 - 0.15):
        for sgn in (-1, 1):
            ang = sgn * math.radians(40)
            d = Vector((0, math.sin(ang), math.cos(ang)))
            a = Vector((x, 0, hb)) - d * leg / 2
            b = Vector((x, 0, hb)) + d * leg / 2
            mb.add_bm(tube([a, b], 0.055, 6), "Wood_grey", uv=lambda co, n: (co.y * 1.0 + co.x, co.z * 1.0), smooth=True)
            tips.append((x, a, b))
    # wire strands along the frame tips and spirals around
    tip_lines = {}
    for (x, a, b) in tips:
        for key, p in (("lo" + ("+" if a.y > 0 else "-"), a), ("hi" + ("+" if b.y > 0 else "-"), b)):
            tip_lines.setdefault(key, []).append(p)
    for key, pts in tip_lines.items():
        pts = sorted(pts, key=lambda p: p.x)
        sag = []
        for i in range(len(pts) - 1):
            for k in range(6):
                t = k / 6
                q = pts[i].lerp(pts[i + 1], t)
                q.z -= 0.06 * math.sin(PI * t)
                sag.append(q)
        sag.append(pts[-1])
        _barbed(sag, rng, mb)
    # loose helical coil around the beam
    coil = []
    turns = 9
    for i in range(turns * 16 + 1):
        t = i / (turns * 16)
        ang = t * turns * 2 * PI
        r = 0.55 + 0.05 * math.sin(ang * 3.0)
        coil.append((-L / 2 + 0.1 + t * (L - 0.2), r * math.cos(ang) * 0.95, hb + r * math.sin(ang) * 0.8))
    _barbed(coil, rng, mb, barb_step=0.14)
    ob = mb.build("knife_rest_roadblock")
    cols = [collision_box("Frame", -L / 2 - 0.1, -0.65, 0, L / 2 + 0.1, 0.65, 1.3)]
    return [ob], cols, [], mb.tri_count(), dict(elev=14, azim=-30, dist_mul=0.8, ground="mud")


def barrel_wood():
    rng = random.Random(6)
    mb = MB()
    H, rm, re = 0.9, 0.31, 0.265
    prof = []
    for i in range(11):
        t = i / 10
        z = t * H
        r = re + (rm - re) * math.sin(PI * t)
        prof.append((r, z))
    body = lathe(prof, segs=24, cap_top=False, cap_bottom=False)
    mb.add_bm(body, "Wood_oak", uv=cyl_uv(scale=1.0), off=roff(rng), smooth=True, smooth_angle=40)
    for zz in (0.06, 0.24, H - 0.24, H - 0.06):
        t = zz / H
        r = re + (rm - re) * math.sin(PI * t) + 0.004
        hoop = lathe([(r, zz - 0.022), (r + 0.003, zz - 0.02), (r + 0.003, zz + 0.02), (r, zz + 0.022)], segs=24,
                     cap_top=False, cap_bottom=False)
        mb.add_bm(hoop, "Iron", uv=cyl_uv(scale=2.0), smooth=True, smooth_angle=40)
    for zz, flip in ((0.025, True), (H - 0.025, False)):   # recessed heads inside the chime
        bm = bmesh.new()
        vs = [bm.verts.new(((re - 0.004) * math.cos(2 * PI * i / 24), (re - 0.004) * math.sin(2 * PI * i / 24), zz)) for i in range(24)]
        bm.faces.new(list(reversed(vs)) if flip else vs)
        mb.add_bm(bm, "Wood_oak", scale=1.0, off=roff(rng))
        z0, z1 = (0.0, 0.025) if flip else (H - 0.025, H)
        inner = lathe([(re - 0.004, z0), (re - 0.004, z1)], segs=24, cap_top=False, cap_bottom=False)
        bmesh.ops.reverse_faces(inner, faces=inner.faces)
        mb.add_bm(inner, "Wood_oak", uv=cyl_uv(scale=1.0))
        ze = 0.0 if flip else H
        rim = bmesh.new()
        ro = [rim.verts.new((re * math.cos(2 * PI * i / 24), re * math.sin(2 * PI * i / 24), ze)) for i in range(24)]
        ri = [rim.verts.new(((re - 0.004) * math.cos(2 * PI * i / 24), (re - 0.004) * math.sin(2 * PI * i / 24), ze)) for i in range(24)]
        for i in range(24):
            j = (i + 1) % 24
            q = (ro[i], ro[j], ri[j], ri[i])
            rim.faces.new(tuple(reversed(q)) if flip else q)
        mb.add_bm(rim, "Wood_oak", scale=1.0)
    mb.add_bm(bm_cyl(0.022, 0.022, 0.012, segs=10), "Wood_dark", matrix=Matrix.Translation((0.1, 0.05, H - 0.025)))  # bung
    ob = mb.build("barrel_wood")
    col = collision_bm("Barrel", lathe([(re, 0), (rm, H / 2), (re, H)], segs=10))
    return [ob], [col], [], mb.tri_count(), dict(elev=20, azim=-30, dist_mul=0.9, ground="cobble")


def crate_wood():
    rng = random.Random(7)
    mb = MB()
    W, D, H = 0.8, 0.6, 0.6
    mb.add_bm(bm_box_minmax(-W / 2 + 0.02, -D / 2 + 0.02, 0.02, W / 2 - 0.02, D / 2 - 0.02, H - 0.02), "Wood_grey",
              scale=1.0, off=roff(rng))
    # planks on faces (slightly proud, with gaps)
    nb = 4
    for i in range(nb):
        z0 = 0.02 + (H - 0.04) * i / nb + 0.004
        z1 = 0.02 + (H - 0.04) * (i + 1) / nb - 0.004
        mb.add_bm(bm_box_minmax(-W / 2, -D / 2, z0, W / 2, -D / 2 + 0.022, z1), "Wood_grey", scale=1.0, off=roff(rng))
        mb.add_bm(bm_box_minmax(-W / 2, D / 2 - 0.022, z0, W / 2, D / 2, z1), "Wood_grey", scale=1.0, off=roff(rng))
        mb.add_bm(bm_box_minmax(-W / 2, -D / 2, z0, -W / 2 + 0.022, D / 2, z1), "Wood_grey", scale=1.0, off=roff(rng))
        mb.add_bm(bm_box_minmax(W / 2 - 0.022, -D / 2, z0, W / 2, D / 2, z1), "Wood_grey", scale=1.0, off=roff(rng))
    for i in range(5):
        x0 = -W / 2 + W * i / 5 + 0.003
        x1 = -W / 2 + W * (i + 1) / 5 - 0.003
        mb.add_bm(bm_box_minmax(x0, -D / 2, H - 0.022, x1, D / 2, H), "Wood_grey", scale=1.0, off=roff(rng))
    # corner battens
    for sx in (-1, 1):
        for sy in (-1, 1):
            xa, xb = sorted((sx * (W / 2 + 0.01), sx * (W / 2 - 0.06)))
            ya, yb = sorted((sy * (D / 2 + 0.01), sy * (D / 2 - 0.06)))
            mb.add_bm(bm_box_minmax(xa, ya, 0.0, xb, yb, H + 0.005, bevel=0.004), "Wood_grey", scale=1.0, off=roff(rng))
    # stencilled marking on the front
    tb = text_bm("N° 43", 0.11)
    M = Matrix(((1, 0, 0, -0.12), (0, 0, -1, -D / 2 - 0.0015), (0, 1, 0, H * 0.5), (0, 0, 0, 1)))
    mb.add_bm(tb, "BlackPaint", matrix=M, scale=2.0)
    ob = mb.build("crate_wood")
    cols = [collision_box("Crate", -W / 2 - 0.01, -D / 2 - 0.01, 0, W / 2 + 0.01, D / 2 + 0.01, H)]
    return [ob], cols, [], mb.tri_count(), dict(elev=20, azim=-30, dist_mul=0.9, ground="cobble")


def _wheel(mb, cx, rng, R=0.72, spokes=12):
    """Wheel in the YZ plane at x=cx, hub centre at z=R."""
    zc = R
    M = Matrix.Translation((cx, 0, zc)) @ Matrix.Rotation(PI / 2, 4, "Y")
    # iron tyre and wooden felloe as lathed rings (local Z = axle direction)
    tyre = lathe([(R, -0.04), (R + 0.012, -0.035), (R + 0.012, 0.035), (R, 0.04)], segs=36, cap_top=False, cap_bottom=False)
    mb.add_bm(tyre, "Iron", uv=cyl_uv(scale=2.0), matrix=M, smooth=True, smooth_angle=30)
    fel = lathe([(R - 0.09, -0.04), (R, -0.04), (R, 0.04), (R - 0.09, 0.04), (R - 0.09, -0.04)], segs=36,
                cap_top=False, cap_bottom=False)
    mb.add_bm(fel, "Wood_grey", uv=cyl_uv(scale=1.0), matrix=M, smooth=True, smooth_angle=30)
    hub = lathe([(0.0, -0.22), (0.07, -0.22), (0.1, -0.15), (0.12, -0.05), (0.12, 0.05), (0.1, 0.12), (0.06, 0.18), (0.0, 0.18)], segs=16)
    mb.add_bm(hub, "Wood_grey", uv=cyl_uv(scale=1.0), matrix=M, smooth=True, smooth_angle=40)
    for zz in (-0.12, 0.08):
        mb.add_bm(lathe([(0.125, zz - 0.015), (0.125, zz + 0.015)], segs=16, cap_top=False, cap_bottom=False), "Iron",
                  uv=cyl_uv(scale=2.0), matrix=M, smooth=True)
    for i in range(spokes):
        a = 2 * PI * (i + 0.5) / spokes
        d = Vector((math.cos(a), math.sin(a), 0))
        p0 = d * 0.1 + Vector((0, 0, 0.02))
        p1 = d * (R - 0.08) + Vector((0, 0, -0.01))
        sp = tube([p0, p1], 0.022, 6)
        mb.add_bm(sp, "Wood_grey", uv=lambda co, n: (co.x + co.z, co.y), matrix=M, smooth=True, smooth_angle=50)


def cart_charrette():
    rng = random.Random(8)
    mb = MB()
    R = 0.72
    bed_z, bl, bw = 0.86, 2.3, 1.15
    # axle
    mb.add_bm(bm_box(0, 0.1, R, 1.75, 0.1, 0.1, bevel=0.01), "Wood_dark", scale=1.0)
    for sx in (-1, 1):
        _wheel(mb, sx * 0.86, rng, R)
    # bed frame and floor
    y0, y1 = -bl / 2 + 0.1, bl / 2 + 0.1
    for sx in (-1, 1):
        mb.add_bm(bm_box(sx * (bw / 2 - 0.05), (y0 + y1) / 2, bed_z, 0.1, bl, 0.12, bevel=0.008), "Wood_grey", scale=1.0, off=roff(rng))
    nb = 9
    for i in range(nb):
        ya = y0 + bl * i / nb + 0.004
        yb = y0 + bl * (i + 1) / nb - 0.004
        mb.add_bm(bm_box_minmax(-bw / 2, ya, bed_z + 0.06, bw / 2, yb, bed_z + 0.09), "Wood_grey", scale=1.0, off=roff(rng))
    # sides (ridelles): rails with uprights
    for sx in (-1, 1):
        x = sx * (bw / 2 - 0.02)
        for zz in (bed_z + 0.32, bed_z + 0.52):
            mb.add_bm(bm_box(x, (y0 + y1) / 2, zz, 0.05, bl, 0.07, bevel=0.006), "Wood_grey", scale=1.0, off=roff(rng))
        for k in range(7):
            yy = y0 + 0.08 + (bl - 0.16) * k / 6
            mb.add_bm(bm_box(x, yy, bed_z + 0.33, 0.04, 0.05, 0.52), "Wood_grey", scale=1.0, off=roff(rng))
    # tailboard
    mb.add_bm(bm_box(0, y1 - 0.02, bed_z + 0.3, bw - 0.05, 0.04, 0.42), "Wood_grey", scale=1.0, off=roff(rng))
    # shafts (brancards) running forward, resting on a prop stick
    tip_y = y0 - 1.9
    for sx in (-1, 1):
        a = Vector((sx * 0.48, y1 - 0.1, bed_z - 0.02))
        b = Vector((sx * 0.36, tip_y, bed_z - 0.08))
        mb.add_bm(tube([a, b], 0.045, 6), "Wood_grey", uv=lambda co, n: (co.x + co.z, co.y), smooth=True)
    yb = y0 - 1.2
    mb.add_bm(bm_box(0, yb, bed_z - 0.1, 0.78, 0.06, 0.06), "Wood_grey", scale=1.0)
    mb.add_bm(tube([(0.0, yb, bed_z - 0.13), (0.0, yb + 0.12, 0.0)], 0.035, 6), "Wood_grey",
              uv=lambda co, n: (co.x + co.y, co.z), smooth=True)
    ob = mb.build("cart_charrette")
    cols = [collision_box("Bed", -bw / 2, y0, bed_z - 0.1, bw / 2, y1, bed_z + 0.6),
            collision_box("WheelL", -0.95, -R, 0, -0.78, R, 2 * R),
            collision_box("WheelR", 0.78, -R, 0, 0.95, R, 2 * R),
            collision_box("Shafts", -0.55, tip_y, 0, 0.55, y0, bed_z)]
    return [ob], cols, [], mb.tri_count(), dict(elev=14, azim=-35, dist_mul=0.8, ground="mud")


def stone_wall_low_4m():
    """Breton dry granite field wall: irregular stones, through-stones, edge-set coping."""
    rng = random.Random(9)
    mb = MB()
    L, Dp, H = 4.0, 0.62, 1.0
    z = -0.06
    while z < H - 0.2:
        x = -L / 2 + rng.uniform(-0.12, 0.0)
        row_h = rng.uniform(0.14, 0.26)
        while x < L / 2:
            sl = rng.uniform(0.18, 0.6)
            ch = row_h * rng.uniform(0.7, 1.15)
            sx = min(sl, L / 2 - x + 0.02)
            if sx > 0.07:
                through = rng.random() < 0.3
                faces = ((-Dp / 2, Dp / 2),) if through else ((-Dp / 2, -0.02), (0.02, Dp / 2))
                for (y0, y1) in faces:
                    dy = rng.uniform(-0.035, 0.035)
                    bm = noisy_stone(x + sx / 2, (y0 + y1) / 2 + dy, z + ch / 2, sx - 0.025, (y1 - y0) - 0.02, ch - 0.015, rng,
                                     rough=0.022, rot=0.09)
                    mb.add_bm(bm, "FieldStone", off=roff(rng), smooth=True, smooth_angle=40)
                # small pinning stones in the gaps
                if rng.random() < 0.5:
                    for sy in (-1, 1):
                        bm = noisy_stone(x + sl - 0.02, sy * (Dp / 2 - 0.05), z + rng.uniform(0.03, ch - 0.03), 0.07, 0.08, 0.05, rng,
                                         rough=0.01, rot=0.4)
                        mb.add_bm(bm, "FieldStone", off=roff(rng), smooth=True, smooth_angle=40)
            x += sl
        z += row_h * 0.95
    x = -L / 2
    while x < L / 2:                                   # coping: stones set on edge
        w = rng.uniform(0.12, 0.26)
        sx = min(w, L / 2 - x)
        if sx > 0.05:
            hh = rng.uniform(0.2, 0.34)
            bm = noisy_stone(x + sx / 2, rng.uniform(-0.03, 0.03), z + hh / 2 - 0.04, sx - 0.02, Dp * rng.uniform(0.7, 0.9), hh, rng,
                             rough=0.02, rot=0.15)
            mb.add_bm(bm, "FieldStone", off=roff(rng), smooth=True, smooth_angle=40)
        x += w
    ob = mb.build("stone_wall_low_4m")
    cols = [collision_box("Wall", -L / 2, -Dp / 2, -0.05, L / 2, Dp / 2, z + 0.25)]
    return [ob], cols, [], mb.tri_count(), dict(elev=14, azim=-25, dist_mul=0.75, ground="grass_winter")


NOTICE_DE = ("Mit sofortiger Wirkung ist es der Zivilbevölkerung verboten, sich in der Zeit von "
             "22 Uhr bis 5 Uhr ausserhalb der Wohnungen aufzuhalten. Zuwiderhandlungen werden streng bestraft. "
             "Wachen und Streifen haben Befehl, auf Personen, die auf Anruf nicht stehen bleiben, zu schiessen.")
NOTICE_FR = ("À dater de ce jour, il est interdit à la population civile de circuler entre 22 heures et "
             "5 heures. Toute infraction sera sévèrement punie. Les sentinelles et les patrouilles ont "
             "l'ordre de faire feu sur toute personne qui ne s'arrêtera pas à la première sommation.")


def notice_board():
    rng = random.Random(10)
    mb = MB()
    BW, BH, bz = 1.25, 1.1, 0.95                      # board width/height, bottom
    for sx in (-1, 1):
        mb.add_bm(bm_box(sx * (BW / 2 + 0.03), 0.0, 1.1, 0.09, 0.09, 2.3, bevel=0.006), "Wood_grey", scale=1.0, off=roff(rng))
    mb.add_bm(bm_box_minmax(-BW / 2, -0.015, bz, BW / 2, 0.025, bz + BH), "Wood_grey", scale=1.0, off=roff(rng))
    for zz in (bz, bz + BH):
        mb.add_bm(bm_box_minmax(-BW / 2 - 0.02, -0.04, zz - 0.03, BW / 2 + 0.02, 0.03, zz + 0.03), "Wood_grey", scale=1.0)
    # small pent roof
    prof = [(-0.2, 2.17), (0.16, 2.3), (0.16, 2.33), (-0.2, 2.2)]
    mb.add_bm(bm_prism(prof, -BW / 2 - 0.12, BW / 2 + 0.12), "Wood_dark", scale=1.0)
    # the poster: paper + text (German top, French bottom), slightly askew, pinned
    pw, ph = 0.6, 0.86
    px0, pz0 = -0.28, bz + 0.12
    yp = -0.0165
    rot = Matrix.Rotation(math.radians(-1.2), 4, "Y")
    paper = bm_quad((px0 - pw / 2, yp, pz0), (px0 + pw / 2, yp, pz0), (px0 + pw / 2, yp, pz0 + ph), (px0 - pw / 2, yp, pz0 + ph),
                    uvs=[(0, 0), (pw, 0), (pw, ph), (0, ph)])
    for f in paper.faces:
        f.normal_update()
    mb.add_bm(paper, "Paper", uv="keep", matrix=Matrix.Translation((px0, 0, pz0 + ph / 2)) @ rot @ Matrix.Translation((-px0, 0, -pz0 - ph / 2)))
    lines = [("BEKANNTMACHUNG", 0.042, 1.0)]
    lines += [(l, 0.0175, 1.0) for l in textwrap.wrap(NOTICE_DE, 46)]
    lines += [("", 0.012, 1.0), ("Der Feldkommandant", 0.019, 1.0), ("", 0.02, 1.0), ("AVIS", 0.042, 1.0)]
    lines += [(l, 0.0175, 1.0) for l in textwrap.wrap(NOTICE_FR, 46)]
    lines += [("", 0.012, 1.0), ("Le Feldkommandant", 0.019, 1.0)]
    zt = pz0 + ph - 0.07
    for (txt, size, _) in lines:
        if txt:
            tb = text_bm(txt, size)
            M = (Matrix.Translation((px0, 0, pz0 + ph / 2)) @ rot @ Matrix.Translation((-px0, 0, -pz0 - ph / 2))
                 @ Matrix(((1, 0, 0, px0), (0, 0, -1, yp - 0.0008), (0, 1, 0, zt), (0, 0, 0, 1))))
            mb.add_bm(tb, "Ink", matrix=M, scale=2.0)
        zt -= size * 1.35 + 0.004
    # a second, older torn notice and drawing pins
    p2 = bm_quad((0.12, yp + 0.0003, bz + 0.5), (0.52, yp + 0.0003, bz + 0.47), (0.53, yp + 0.0003, bz + 0.95), (0.13, yp + 0.0003, bz + 0.98),
                 uvs=[(0.3, 0.1), (0.7, 0.1), (0.7, 0.6), (0.3, 0.6)])
    mb.add_bm(p2, "Paper", uv="keep")
    for (x, zz) in ((px0 - pw / 2 + 0.02, pz0 + ph - 0.02), (px0 + pw / 2 - 0.02, pz0 + ph - 0.02), (px0 - pw / 2 + 0.02, pz0 + 0.02),
                    (px0 + pw / 2 - 0.02, pz0 + 0.02), (0.15, bz + 0.95), (0.5, bz + 0.92)):
        mb.add_bm(bm_cyl(0.006, 0.006, 0.004, segs=6), "Iron", matrix=Matrix.Translation((x, yp - 0.004, zz)) @ Matrix.Rotation(PI / 2, 4, "X"))
    ob = mb.build("notice_board")
    cols = [collision_box("Board", -BW / 2 - 0.08, -0.05, 0, BW / 2 + 0.08, 0.05, 2.3)]
    return [ob], cols, [], mb.tri_count(), dict(elev=4, azim=-12, dist_mul=0.55, ground="cobble", target=(0, 0, 1.4))


def wall_lantern():
    """Wall-mounted street lantern. Origin = centre of the wall plate (on the wall surface);
    the arm projects toward -Y (Godot +Z). Place on a facade at ~3.2 m."""
    rng = random.Random(11)
    mb = MB()
    mb.add_bm(bm_box_minmax(-0.08, -0.012, -0.18, 0.08, 0.0, 0.18), "Iron", scale=2.0)
    arm_y = -0.62
    mb.add_bm(tube([(0, -0.01, 0.12), (0, -0.3, 0.14), (0, arm_y, 0.14)], 0.014, 6), "Iron", scale=2.0, smooth=True)
    curl = [(0, -0.01, -0.12)]
    for i in range(14):
        t = i / 13
        ang = t * PI * 1.2
        curl.append((0, -0.05 - t * 0.33, -0.12 + 0.24 * math.sin(ang * 0.5) + 0.03 * math.sin(ang * 3)))
    mb.add_bm(tube(curl, 0.009, 5), "Iron", scale=2.0, smooth=True)
    # lantern hangs from the arm end
    cx, cy, top = 0.0, arm_y, 0.08
    mb.add_bm(tube([(cx, cy, 0.14), (cx, cy, top + 0.05)], 0.008, 5), "Iron", scale=2.0)
    roof = lathe([(0.17, top - 0.02), (0.17, top), (0.04, top + 0.1), (0.02, top + 0.14), (0.0, top + 0.15)], segs=4)
    bmesh.ops.rotate(roof, verts=roof.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(PI / 4, 3, "Z"))
    mb.add_bm(roof, "Iron", scale=2.0, matrix=Matrix.Translation((cx, cy, 0)))
    body_top, body_bot = top - 0.02, top - 0.34
    glass = lathe([(0.105, body_bot), (0.13, body_top)], segs=4, cap_top=False, cap_bottom=True)
    bmesh.ops.rotate(glass, verts=glass.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(PI / 4, 3, "Z"))
    mb.add_bm(glass, "LampGlass", matrix=Matrix.Translation((cx, cy, 0)))
    for i in range(4):     # corner frame bars
        a = PI / 2 * i
        p0 = Vector((math.cos(a) * 0.108, math.sin(a) * 0.108, body_bot)) * 1.0
        p1 = Vector((math.cos(a) * 0.133, math.sin(a) * 0.133, body_top))
        p0 = Vector((p0.x * 0.707 - p0.y * 0.707, p0.x * 0.707 + p0.y * 0.707, body_bot))
        p1 = Vector((p1.x * 0.707 - p1.y * 0.707, p1.x * 0.707 + p1.y * 0.707, body_top))
        mb.add_bm(tube([p0 + Vector((cx, cy, 0)), p1 + Vector((cx, cy, 0))], 0.007, 4), "Iron", scale=2.0)
    base = lathe([(0.0, body_bot - 0.06), (0.03, body_bot - 0.06), (0.11, body_bot - 0.005), (0.11, body_bot)], segs=4)
    bmesh.ops.rotate(base, verts=base.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(PI / 4, 3, "Z"))
    mb.add_bm(base, "Iron", scale=2.0, matrix=Matrix.Translation((cx, cy, 0)))
    ob = mb.build("wall_lantern")
    cols = [collision_box("Lantern", -0.16, cy - 0.16, body_bot - 0.07, 0.16, 0.0, 0.2, suffix="-convcolonly")]

    def backdrop():
        import bpy
        from geo import obj_from_bm, std
        w = obj_from_bm("PV_wall", bm_box_minmax(-1.0, 0.0, -1.5, 1.0, 0.3, 1.0))
        w.data.materials.append(std("Rubble"))
        uv = w.data.uv_layers.new(name="UVMap")
        for loop in w.data.loops:
            co = w.data.vertices[loop.vertex_index].co
            uv.data[loop.index].uv = (co.x * 0.5, co.z * 0.5)
        return [w]
    return [ob], cols, [], mb.tri_count(), dict(elev=6, azim=-40, dist_mul=0.9, ground=None, extra=backdrop)


PROPS = {
    "telegraph_pole": telegraph_pole,
    "wayside_cross": wayside_cross,
    "sentry_box": sentry_box,
    "sandbag_wall_2m": sandbag_wall_2m,
    "knife_rest_roadblock": knife_rest_roadblock,
    "barrel_wood": barrel_wood,
    "crate_wood": crate_wood,
    "cart_charrette": cart_charrette,
    "stone_wall_low_4m": stone_wall_low_4m,
    "notice_board": notice_board,
    "wall_lantern": wall_lantern,
}


def build(name):
    return PROPS[name]()
