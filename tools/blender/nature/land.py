"""Land forms: granite boulders and a mossy outcrop, the Breton talus hedgerow bank (plain and
gateway variants), a small stone arch footbridge and a stream-bank edge piece.

Tiling pieces (talus_*_10m, stream_bank_4m) run along Blender Y and use noise sampled on a
circle in Y, so the cross-section at y = -L/2 is identical to the one at y = +L/2.
"""
import math

import bmesh
import numpy as np
from mathutils import Euler, Matrix, Vector, noise

import geo
import nlib
import trees
from nlib import ENVTEX, GROUND, MB, card, mat, tube
from ntex import GRASS_REGIONS

UP = Vector((0, 0, 1))


def pnoise(x, y, z, period, scale, seed=0.0):
    """3D noise, periodic in y with the given period."""
    a = 2 * math.pi * y / period
    R = period * scale / (2 * math.pi)
    return noise.noise(Vector((x * scale + seed, R * math.cos(a) + z * scale * 0.7, R * math.sin(a) + seed * 0.3)))


def _mats():
    return dict(
        granite=mat("Granite", "rock"),
        moss=mat("Moss", "moss"),
        dressed=mat("DressedGranite", "granite", folder=ENVTEX),
        rubble=mat("Rubble", "rubble", folder=ENVTEX),
        grass=mat("BankGrass", "grass_winter", folder=GROUND),
        earth=mat("BankEarth", "bank"),
        mud=mat("Mud", "mud", folder=GROUND),
        gravel=mat("Gravel", "gravel", folder=GROUND),
    )


# =================================================================== ROCKS
def rock_bm(sx, sy, sz, seed, subdiv, sink=0.18, planes=5, rough=1.0):
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    off = Vector(rng.uniform(-50, 50, 3))
    cuts = []
    for k in range(planes):
        n = Vector(rng.normal(0, 1, 3))
        if k < 2:
            n.z = abs(n.z) * 2 + 0.5            # flattened tops are typical of granite boulders
        n.normalize()
        cuts.append((n, rng.uniform(0.62, 0.85)))
    for v in bm.verts:
        d = v.co.normalized()
        k = 1.0 + 0.16 * noise.noise(d * 1.1 + off) + 0.07 * rough * noise.noise(d * 2.8 + off) \
            + 0.025 * rough * noise.noise(d * 7.0 + off)
        p = d * k
        for n, c in cuts:
            e = p.dot(n) - c
            if e > 0:
                p -= n * e * 0.8
        v.co = Vector((p.x * sx, p.y * sy, p.z * sz))
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin + sink * sz * 2
    return bm


def _moss_fn(M, thr, seed, zmin=0.0):
    def f(face):
        n = face.normal
        c = face.calc_center_median()
        s = n.z + 0.35 * noise.noise(c * 1.3 + Vector((seed, 0, 0))) + 0.15 * n.y
        return M["moss"] if (s > thr and c.z > zmin) else M["granite"]
    return f


def _hull_of(bm_verts, name, step=3):
    pts = [tuple(v) for i, v in enumerate(bm_verts) if i % step == 0 and v.z > -0.3]
    return nlib.col_hull(name, pts)


def boulder(name, sx, sy, sz, seed, subdiv, moss_thr):
    M = _mats()
    mb = MB()
    bm = rock_bm(sx, sy, sz, seed, subdiv)
    pts = [v.co.copy() for v in bm.verts]
    bm.normal_update()
    mb.add_bm(bm, _moss_fn(M, moss_thr, seed), scale=0.5, smooth=True)
    ob = mb.build(name)
    return [ob], [_hull_of(pts, "Rock")], {"tris": mb.tris(), "dims": tuple(round(v, 2) for v in ob.dimensions)}


def outcrop(name, seed=9):
    """Moss-covered granite outcrop (chaos de granit): a few fused rounded blocks + tufts."""
    rng = np.random.default_rng(seed)
    M = _mats()
    mb = MB()
    cols = []
    blocks = [((0.0, 0.0), (1.9, 1.4, 1.0)), ((1.7, 0.5), (1.2, 1.0, 0.75)), ((-1.6, -0.3), (1.1, 1.2, 0.8)),
              ((0.5, -1.3), (0.9, 0.7, 0.5))]
    for k, ((x, y), (sx, sy, sz)) in enumerate(blocks):
        bm = rock_bm(sx, sy, sz, seed + k * 7, 4 if k < 3 else 3, sink=0.12)
        rot = Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z")
        bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y, 0)) @ rot, verts=bm.verts)
        pts = [v.co.copy() for v in bm.verts]
        bm.normal_update()
        mb.add_bm(bm, _moss_fn(M, 0.25, seed + k), scale=0.5, smooth=True)
        cols.append(_hull_of(pts, f"Outcrop{k}"))
    ob = mb.build(name)
    # grass and fern tufts around the foot and in the joints
    gm = mat("GrassCard", "grasscards", alpha=True)
    cm = MB()
    regs = ["grass_a", "grass_b", "fern_a"]
    for t in range(26):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(1.7, 2.6)
        base = Vector((math.cos(a) * r * 1.1, math.sin(a) * r * 0.8, -0.02))
        for c in range(3):
            az = rng.uniform(0, 6.28)
            dirh = Vector((math.cos(az), math.sin(az), 0))
            h = rng.uniform(0.3, 0.55)
            upv = (UP + dirh * rng.uniform(0.1, 0.6)).normalized()
            card(cm, base, upv, dirh.cross(UP), h * 0.5, h, GRASS_REGIONS[regs[(t + c) % 3]], gm, bend=h * 0.25, segs=2)
    obc = cm.build(name + "_tufts")
    return [ob, obc], cols, {"tris": mb.tris() + cm.tris(), "dims": tuple(round(v, 2) for v in ob.dimensions)}


ROCKS = {
    "rock_small": lambda n: boulder(n, 0.32, 0.26, 0.22, 3, 4, 0.75),
    "rock_medium": lambda n: boulder(n, 0.75, 0.6, 0.5, 5, 5, 0.6),
    "rock_large": lambda n: boulder(n, 1.5, 1.2, 0.95, 7, 5, 0.5),
    "rock_outcrop_moss": lambda n: outcrop(n),
}


# =============================================================== TALUS BANK
TALUS_L = 10.0
PROF = [(-1.10, -0.15), (-1.0, 0.0), (-0.95, 0.16), (-0.90, 0.36), (-0.84, 0.56), (-0.76, 0.73), (-0.66, 0.86),
        (-0.52, 0.94), (-0.36, 0.985), (-0.18, 1.0), (0.0, 1.01), (0.18, 1.0), (0.36, 0.985), (0.52, 0.94),
        (0.66, 0.86), (0.76, 0.73), (0.84, 0.56), (0.90, 0.36), (0.95, 0.16), (1.0, 0.0), (1.10, -0.15)]


def bank_H(y):
    return 1.5 + 0.2 * pnoise(0.0, y, 0.0, TALUS_L, 0.35, 3.0) + 0.06 * pnoise(0.0, y, 1.0, TALUS_L, 1.2, 5.0)


def bank_W(y):
    return 1.55 + 0.12 * pnoise(1.0, y, 0.0, TALUS_L, 0.4, 7.0)


def bank_S(u, y, k=None):
    """Surface point for profile parameter u in [0, len(PROF)-1] (float) at y."""
    i = min(int(u), len(PROF) - 2)
    f = u - i
    px = PROF[i][0] + (PROF[i + 1][0] - PROF[i][0]) * f
    pz = PROF[i][1] + (PROF[i + 1][1] - PROF[i][1]) * f
    W, H = bank_W(y), bank_H(y)
    x, z = px * W, pz * H
    lump = 0.07 * pnoise(x, y, z, TALUS_L, 1.1, 11.0) + 0.03 * pnoise(x, y, z, TALUS_L, 3.0, 13.0)
    side = 1 if px > 0 else -1
    if pz > 0:
        x += side * lump * (1 - abs(px) * 0.2)
        z += lump * 0.6 * max(0.0, 1 - abs(px))
    return Vector((x, y, z))


def bank_N(u, y):
    e = 0.05
    a = bank_S(min(u + e, len(PROF) - 1), y) - bank_S(max(u - e, 0), y)
    b = bank_S(u, y + e) - bank_S(u, y - e)
    n = b.cross(a).normalized()
    return n


def bank_mesh(mb, M, y0, y1, rows_per_m=5, cols_per_seg=2, endcap=None):
    nr = max(2, int(round((y1 - y0) * rows_per_m)))
    nc = (len(PROF) - 1) * cols_per_seg
    us = [i / cols_per_seg for i in range(nc + 1)]
    grid = []
    for r in range(nr + 1):
        y = y0 + (y1 - y0) * r / nr
        grid.append(mb.add_verts([bank_S(u, y) for u in us]))
    for r in range(nr):
        ya = y0 + (y1 - y0) * r / nr
        yb = y0 + (y1 - y0) * (r + 1) / nr
        for c in range(nc):
            a, b = grid[r] + c, grid[r] + c + 1
            cc, d = grid[r + 1] + c + 1, grid[r + 1] + c
            pa, pb = mb.verts[a], mb.verts[b]
            pc = mb.verts[cc]
            n = (pb - pa).cross(pc - pa)
            n = n.normalized() if n.length > 1e-9 else UP
            ctr = (pa + pc) * 0.5
            slope = n.z
            e = pnoise(ctr.x, ctr.y, ctr.z, TALUS_L, 0.9, 21.0)
            mt = M["earth"] if (slope < 0.55 + 0.25 * e) else M["grass"]
            # UVs: along-bank y, across = arc length approximated by x,z
            uvs = [((mb.verts[i].x * 0.5 + mb.verts[i].z * 0.5 * (1 if mb.verts[i].x >= 0 else -1)), mb.verts[i].y * 0.5)
                   for i in (a, b, cc, d)]
            mb.face((a, d, cc, b), [uvs[0], uvs[3], uvs[2], uvs[1]], mt)
    if endcap is not None:
        # close the bank end (gateway): end face polygon, pointing along endcap sign
        r = 0 if endcap < 0 else nr
        ring = [grid[r] + c for c in range(nc + 1)]
        ring = ring[1:-1]
        idx = ring if endcap > 0 else list(reversed(ring))
        uvs = [(mb.verts[i].x * 0.5, mb.verts[i].z * 0.5) for i in idx]
        mb.face(idx, uvs, M["earth"], smooth=False)


def stone_bm(sx, sy, sz, seed):
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    off = Vector(rng.uniform(-40, 40, 3))
    for v in bm.verts:
        d = v.co.normalized()
        k = 1.0 + 0.18 * noise.noise(d * 1.4 + off)
        p = d * k
        # boxy: push towards a rounded cube
        p = Vector([math.copysign(abs(c) ** 0.6, c) for c in p])
        v.co = Vector((p.x * sx, p.y * sy, p.z * sz))
    return bm


def place_stones(mb, M, spots, seed):
    """spots: list of (centre, normal, along, size(w,h,d))."""
    rng = np.random.default_rng(seed)
    n = 0
    for (c, nrm, along, (w, h, d)) in spots:
        bm = stone_bm(w / 2, h / 2, d / 2, seed + n)
        zax = nrm.normalized()
        xax = (along - zax * along.dot(zax)).normalized()
        yax = zax.cross(xax)
        rot = Matrix((xax, yax, zax)).transposed().to_4x4()
        tilt = Euler(rng.normal(0, 0.08, 3)).to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=Matrix.Translation(c - zax * d * 0.18) @ rot @ tilt, verts=bm.verts)
        bm.normal_update()
        mb.add_bm(bm, M["dressed_field"], scale=0.5, smooth=True)
        n += 1
    return n


def facing_spots(y0, y1, seed, dens=1.0, end_margin=0.0):
    """Stone-facing on the lower flanks of the bank, in noise-defined patches (periodic)."""
    rng = np.random.default_rng(seed)
    spots = []
    for side in (-1, 1):
        y = y0 + end_margin
        while y < y1 - end_margin:
            w = rng.uniform(0.28, 0.55)
            patch = pnoise(side * 3.0, y, 0.0, TALUS_L, 0.45, 31.0 + side)
            if patch > 0.05 / dens - 0.25:
                rows = 3 if patch > 0.25 else 2
                zf = 0.0
                for r in range(rows):
                    h = rng.uniform(0.18, 0.3)
                    # profile param from bottom: side -1 starts at u=1, side +1 at u=len-2
                    u = 1.0 + zf * 4.0 if side < 0 else (len(PROF) - 2) - zf * 4.0
                    yy = y + w / 2 + rng.normal(0, 0.03)
                    if not (y0 + 0.15 < yy < y1 - 0.15):
                        break
                    c = bank_S(u, yy)
                    n = bank_N(u, yy)
                    if side < 0:
                        n = -n if n.x > 0 else n
                    else:
                        n = -n if n.x < 0 else n
                    spots.append((c, n, Vector((0, 1, 0)), (w, h, rng.uniform(0.22, 0.32))))
                    zf += h / 1.6 + 0.02
            y += w + rng.uniform(0.0, 0.05)
    return spots


def _grass_on_bank(cm, gm, bk, rng, y0, y1, n, avoid=()):
    for t in range(n):
        y = rng.uniform(y0 + 0.2, y1 - 0.2)
        if any(a0 < y < a1 for a0, a1 in avoid):
            continue
        u = rng.uniform(0.8, len(PROF) - 1.8)
        p = bank_S(u, y)
        nrm = bank_N(u, y)
        if nrm.z < 0:
            nrm = -nrm
        top = abs(u - (len(PROF) - 1) / 2) < 4
        regs = ["grass_a", "grass_b"] if (top or rng.random() < 0.6) else ["fern_a", "fern_b"]
        for c in range(3):
            az = rng.uniform(0, 6.28)
            dirh = Vector((math.cos(az), math.sin(az), 0))
            h = rng.uniform(0.3, 0.6)
            upv = (UP * 0.7 + nrm * 0.5 + dirh * rng.uniform(0.0, 0.4)).normalized()
            card(cm, p - upv * 0.03, upv, dirh.cross(UP).normalized(), h * (0.5 if "grass" in regs[0] else 1.0), h,
                 GRASS_REGIONS[regs[c % 2]], gm, bend=h * 0.25, segs=2)
        if not top and rng.random() < 0.35:     # dead bracken on the flanks
            for c in range(3):
                az = rng.uniform(0, 6.28)
                dirh = Vector((math.cos(az), math.sin(az), 0))
                h = rng.uniform(0.5, 0.85)
                upv = (UP * 0.5 + nrm * 0.6 + dirh * 0.3).normalized()
                cell = (0.0, 0.0, 0.5, 1.0) if c % 2 else (0.5, 0.0, 1.0, 1.0)
                card(cm, p, upv, dirh.cross(UP).normalized(), h * 0.5, h, cell, bk, bend=h * 0.35, segs=3)


def _hazel(seed):
    return dict(
        trunk_len=0.35, trunk_r=0.14, z0=-0.15, flare=0.3, roots=4, burl=0.25,
        env_c=(0, 0, 2.3), env_r=(2.2, 2.0, 2.4), env_lobe=0.25, env_soft=0.3,
        maxorder=2, seg=[0.15, 0.4, 0.3], wobble=[0.02, 0.05, 0.12], trop=[0.0, 0.015, 0.02],
        tip=[0.9, 0.22, 0.3], nkids=[10, 7], lmean=[0.35, 3.0], kid_t=[(0.3, 1.0), (0.25, 1.0)],
        angle=[20, 42], lratio=[9.0, 0.4], lmin=[2.4, 0.6], rratio=[0.32, 0.4], kid_shape=lambda t: 1.0,
        angle_sd=10, card_size=1.0, card_step=0.32, card_ang=(25, 55), card_trop=0.1, card_droop=0.15, cross=1,
        cell_w=[0.34, 0.33, 0.33, 0.0], moss_thr=0.3, bark_tint=(0.75, 0.62, 0.52), rmin=0.003)


def _blackthorn(seed):
    return dict(
        trunk_len=0.25, trunk_r=0.09, z0=-0.1, flare=0.2, roots=3, burl=0.0,
        env_c=(0, 0, 1.1), env_r=(1.7, 1.4, 1.25), env_lobe=0.3, env_soft=0.3,
        maxorder=3, seg=[0.12, 0.3, 0.25, 0.3], wobble=[0.05, 0.22, 0.3, 0.3], trop=[0.0, 0.02, 0.0, 0.0],
        tip=[0.9, 0.3, 0.3, 0.3], nkids=[7, 8, 5], lmean=[0.25, 1.5, 0.6], kid_t=[(0.2, 1.0), (0.15, 1.0), (0.15, 1.0)],
        angle=[38, 58, 62], lratio=[6.0, 0.45, 0.5], lmin=[1.2, 0.45, 0.25], rratio=[0.45, 0.45, 0.5],
        kid_shape=lambda t: 1.0 - 0.4 * t, card_size=0.75, card_step=0.25, card_ang=(35, 75), card_trop=0.0,
        card_droop=0.05, cross=1, cell_w=[0.34, 0.33, 0.33, 0.0], moss_thr=0.4, bark_tint=(0.35, 0.32, 0.32),
        rmin=0.003)


def _pollard(seed):
    """Pollarded oak: squat trunk with a swollen knuckle head and a crown of straight poles."""
    return dict(
        trunk_len=2.9, trunk_r=0.42, z0=-0.3, flare=0.5, roots=5, burl=0.35, trunk_dir=(0.05, 0.03, 1),
        env_c=(0, 0, 6.6), env_r=(3.6, 3.6, 4.2), env_lobe=0.3, env_soft=0.3,
        maxorder=2, seg=[0.3, 0.45, 0.35], wobble=[0.05, 0.035, 0.15], trop=[0.0, 0.03, 0.04],
        tip=[1.25, 0.25, 0.3], nkids=[12, 8], lmean=[2.9, 4.0], kid_t=[(0.86, 1.0), (0.3, 1.0)],
        angle=[30, 45], lratio=[1.5, 0.38], lmin=[3.0, 0.9], rratio=[0.17, 0.42], kid_shape=lambda t: 1.0,
        angle_sd=14, card_size=1.25, card_step=0.32, card_ang=(25, 60), card_trop=0.15, card_droop=0.05, cross=1,
        cell_w=[0.34, 0.33, 0.33, 0.0], moss_thr=0.25, col_h=2.6, col_name="Pollard", rmin=0.003)


def _shrub(kind, seed, pos, objs, cols):
    if kind == "hazel":
        t = trees.Tree(_hazel(seed), seed)
        v, c, s = t.build(f"Hazel{seed}", "hazel", names=("HazelBark", "HazelBarkMoss", "TwigCard_hazel"),
                          bark_tex="bark_beech", twig_tex="twig_hazel", collide=False, offset=pos)
    elif kind == "blackthorn":
        t = trees.Tree(_blackthorn(seed), seed)
        v, c, s = t.build(f"Blackthorn{seed}", "blackthorn",
                          names=("BlackthornBark", "BlackthornBarkMoss", "TwigCard_blackthorn"),
                          bark_tex="bark_ash", twig_tex="twig_blackthorn", collide=False, offset=pos)
    else:
        t = trees.Tree(_pollard(seed), seed)
        v, c, s = t.build(f"PollardOak{seed}", "oak", collide=True, offset=pos)
    objs += v
    cols += c
    return s["tubes"] + s["cards_tris"]


def talus(name, gate=False, seed=40):
    rng = np.random.default_rng(seed)
    M = _mats()
    M["dressed_field"] = mat("FieldStone", "rock", tint=(0.8, 0.78, 0.74))
    gm = mat("GrassCard", "grasscards", alpha=True)
    bk = mat("BrackenCard", "bracken", alpha=True)
    half = TALUS_L / 2
    gap = 1.95
    spans = [(-half, -gap, 1), (gap, half, -1)] if gate else [(-half, half, None)]
    mb, sb, cm = MB(), MB(), MB()
    cols = []
    for (y0, y1, cap) in spans:
        bank_mesh(mb, M, y0, y1, endcap=(cap if cap is not None else None))
        spots = facing_spots(y0, y1, seed + int(abs(y0) * 10 + (7 if y0 < 0 else 0)), end_margin=0.0)
        if cap is not None:
            # stone-faced bank end at the gateway
            yend = y1 if cap > 0 else y0
            for row in range(5):
                z = 0.12 + row * 0.27
                xs = np.arange(-1.3, 1.31, 0.42)
                for x in xs:
                    u = (x / bank_W(yend) + 1.1) / 2.2 * (len(PROF) - 1)
                    if bank_S(u, yend).z < z + 0.1:
                        continue
                    jit = Vector((rng.normal(0, 0.04) + (0.2 if row % 2 else 0.0), 0, rng.normal(0, 0.02)))
                    c = Vector((x, yend, z)) + jit
                    spots.append((c, Vector((0, cap, 0)), Vector((1, 0, 0)),
                                  (rng.uniform(0.32, 0.45), rng.uniform(0.2, 0.28), 0.3)))
        place_stones(sb, M, spots, seed + 100 + int(abs(y0) * 3))
        # collision: convex slices along the bank
        nseg = max(1, int(round((y1 - y0) / 2.0)))
        for k in range(nseg):
            ya = y0 + (y1 - y0) * k / nseg
            yb = y0 + (y1 - y0) * (k + 1) / nseg
            hull = []
            for yy in (ya, yb):
                for u in range(1, len(PROF) - 1):
                    p = bank_S(float(u), yy)
                    hull.append((p.x, yy, max(p.z, -0.1)))
            cols.append(nlib.col_hull(f"Bank{len(cols)}", hull))
    bank = mb.build(name + "_bank")
    stones = sb.build(name + "_stones")
    objs = [bank, stones]
    tris = mb.tris() + sb.tris()
    # hedge on top
    ztop = lambda y: bank_S((len(PROF) - 1) / 2, y).z - 0.05
    if gate:
        plan = [("pollard", -3.6, 0.1), ("hazel", 3.5, -0.15), ("blackthorn", -2.6, 0.25), ("blackthorn", 4.4, 0.2),
                ("hazel", -4.6, -0.2)]
    else:
        plan = [("pollard", -0.6, 0.1), ("hazel", 2.9, -0.15), ("hazel", -3.6, 0.15), ("blackthorn", 1.3, 0.25),
                ("blackthorn", 4.3, -0.2), ("blackthorn", -2.2, -0.25)]
    for k, (kind, y, x) in enumerate(plan):
        tris += _shrub(kind, seed + k * 13, (x, y, ztop(y)), objs, cols)
    avoid = [(-gap, gap)] if gate else []
    _grass_on_bank(cm, gm, bk, rng, -half, half, 70, avoid)
    tris += cm.tris()
    objs.append(cm.build(name + "_grass"))
    if gate:
        tris += gateway(objs, cols, M, gap)
    return objs, cols, {"tris": tris}


def gateway(objs, cols, M, gap):
    """Granite gateposts and a wooden five-bar field gate (separate 'Gate' object, origin on the hinge)."""
    wood = mat("GateWood", "wood_raw_grey", folder=ENVTEX, ntex="wood_raw", otex="wood_raw")
    iron = mat("GateIron", "iron", folder=ENVTEX)
    pb = MB()
    post_y = gap - 0.2
    for k, sgn in enumerate((-1, 1)):
        bm = geo.bm_box(0.0, sgn * post_y, 0.62, 0.34, 0.32, 1.54, bevel=0.03, segs=1,
                        rot=(0.02 * sgn, 0.03, 0.05 * sgn))
        pb.add_bm(bm, M["dressed"], scale=0.5)
        cols.append(nlib.col_hull(f"GatePost{k}", [(x, sgn * post_y + y, z) for x in (-0.18, 0.18)
                                                     for y in (-0.17, 0.17) for z in (0.0, 1.4)]))
    objs.append(pb.build("GatePosts"))
    # gate in local coords: hinge at origin, gate extends along +Y
    hinge = Vector((0.0, -post_y + 0.2, 0.0))
    width = 2 * post_y - 0.42
    g = MB()

    def bar(y0, z0, y1, z1, t, h, mt=wood):
        a, b = Vector((0, y0, z0)), Vector((0, y1, z1))
        d = b - a
        L = d.length
        bm = geo.bm_box(0, L / 2, 0, t, L, h)
        ang = math.atan2(d.z, d.y)
        m = Matrix.Translation(a) @ Matrix.Rotation(ang, 4, "X")
        g.add_bm(bm, mt, scale=1.0, matrix=m)

    bar(0.0, 0.08, 0.0, 1.30, 0.09, 0.11)                    # hanging stile (vertical)
    g.add_bm(geo.bm_box(0, 0.0, 0.69, 0.10, 0.12, 1.24), wood, scale=1.0)
    g.add_bm(geo.bm_box(0, width, 0.66, 0.075, 0.09, 1.16), wood, scale=1.0)   # latch stile
    for k, z in enumerate((0.22, 0.44, 0.66, 0.88, 1.16)):
        g.add_bm(geo.bm_box(0, width / 2, z, 0.045 if k < 4 else 0.07, width, 0.09 if k < 4 else 0.11), wood, scale=1.0)
    bar(0.08, 0.2, width - 0.1, 1.12, 0.045, 0.09)           # diagonal brace
    for z in (0.3, 1.1):                                      # strap hinges + pins
        g.add_bm(geo.bm_box(0.03, 0.25, z, 0.012, 0.5, 0.04), iron, scale=2.0)
        g.add_bm(geo.bm_box(0.0, -0.09, z, 0.03, 0.06, 0.06), iron, scale=2.0)
    g.add_bm(geo.bm_box(0.04, width - 0.02, 0.95, 0.02, 0.16, 0.03), iron, scale=2.0)   # latch
    gate = g.build("Gate")
    gate.location = hinge
    objs.append(gate)
    cols.append(nlib.col_hull("Gate", [(x, hinge.y + y, z) for x in (-0.05, 0.05) for y in (0.0, width)
                                        for z in (0.08, 1.25)]))
    return pb.tris() + g.tris()


TALUS = {
    "talus_bank_10m": lambda n: talus(n, False, 40),
    "talus_gate_10m": lambda n: talus(n, True, 41),
}


# ================================================================ FOOTBRIDGE
def footbridge(name):
    """Single-arch granite and rubble footbridge, 4.4 m along Y, over a stream running along X."""
    M = _mats()
    rng = np.random.default_rng(77)
    L2, W2 = 2.2, 0.8
    span2, spring, rise = 1.2, -0.85, 0.72
    deck_c = 0.32

    def top(y):
        return deck_c * (1 - (y / L2) ** 2)

    def bot(y):
        if abs(y) < span2:
            return spring + rise * math.sqrt(max(0.0, 1 - (y / span2) ** 2))
        return -1.0

    ys = sorted(set([round(-L2 + 4.4 * i / 44, 4) for i in range(45)] + [-span2, span2, -span2 - 0.01, span2 + 0.01]))
    bot_v = [bot(y) if abs(y) != span2 + 0.01 else -1.0 for y in ys]
    for i, y in enumerate(ys):
        if abs(abs(y) - span2) < 1e-6:
            bot_v[i] = spring
    mb = MB()
    side_mat, deck_mat = M["rubble"], mat("Deck", "gravel", folder=GROUND)
    for sx in (-W2, W2):
        idx_b = mb.add_verts([Vector((sx, y, bz)) for y, bz in zip(ys, bot_v)])
        idx_t = mb.add_verts([Vector((sx, y, top(y) + 0.58)) for y in ys])     # wall continues up as parapet outer face
        for i in range(len(ys) - 1):
            a, b, c, d = idx_b + i, idx_b + i + 1, idx_t + i + 1, idx_t + i
            q = (a, b, c, d) if sx > 0 else (a, d, c, b)
            mb.face(q, [(mb.verts[k].y * 0.5 * (1 if sx > 0 else -1), mb.verts[k].z * 0.5) for k in q], side_mat, smooth=False)
    # deck between the parapets
    PW = 0.5
    dl = mb.add_verts([Vector((-PW, y, top(y))) for y in ys])
    dr = mb.add_verts([Vector((PW, y, top(y))) for y in ys])
    for i in range(len(ys) - 1):
        q = (dl + i, dr + i, dr + i + 1, dl + i + 1)
        mb.face(q, [(mb.verts[k].x * 0.5, mb.verts[k].y * 0.5) for k in q], deck_mat, smooth=False)
    # parapet inner faces and tops
    for sgn in (-1, 1):
        x_in = sgn * PW
        ib = mb.add_verts([Vector((x_in, y, top(y))) for y in ys])
        it = mb.add_verts([Vector((x_in, y, top(y) + 0.58)) for y in ys])
        ot = mb.add_verts([Vector((sgn * W2, y, top(y) + 0.58)) for y in ys])
        for i in range(len(ys) - 1):
            q = (ib + i, ib + i + 1, it + i + 1, it + i) if sgn < 0 else (ib + i, it + i, it + i + 1, ib + i + 1)
            mb.face(q, [(mb.verts[k].y * 0.5, mb.verts[k].z * 0.5) for k in q], side_mat, smooth=False)
            q = (it + i, it + i + 1, ot + i + 1, ot + i) if sgn > 0 else (it + i, ot + i, ot + i + 1, it + i + 1)
            mb.face(q, [(mb.verts[k].x * 0.5, mb.verts[k].y * 0.5) for k in q], side_mat, smooth=False)
        # parapet ends
        for e, y in ((0, ys[0]), (len(ys) - 1, ys[-1])):
            q = [ib + e, it + e, ot + e, mb.add_verts([Vector((sgn * W2, y, top(y)))])]
            if (sgn > 0) == (e == 0):
                q = list(reversed(q))
            mb.face(q, [(mb.verts[k].x * 0.5, mb.verts[k].z * 0.5) for k in q], side_mat, smooth=False)
    # intrados (arch soffit)
    arch_i = [i for i, y in enumerate(ys) if abs(y) <= span2 + 1e-6]
    al = mb.add_verts([Vector((-W2, ys[i], bot_v[i])) for i in arch_i])
    ar = mb.add_verts([Vector((W2, ys[i], bot_v[i])) for i in arch_i])
    for k in range(len(arch_i) - 1):
        q = (al + k, al + k + 1, ar + k + 1, ar + k)
        mb.face(q, [(mb.verts[j].x * 0.5, mb.verts[j].y * 0.5 + mb.verts[j].z * 0.5) for j in q], side_mat, smooth=False)
    # granite voussoirs on both faces + coping
    sb = MB()
    nv = 15
    for sgn in (-1, 1):
        for k in range(nv):
            a0 = math.pi * k / nv + 0.012
            a1 = math.pi * (k + 1) / nv - 0.012
            ext = 0.33 if k != nv // 2 else 0.4
            pts = []
            for a in (a0, a1):
                ci, si = math.cos(a), math.sin(a)
                pts.append(Vector((0, span2 * ci, spring + rise * si)))
                pts.append(Vector((0, (span2 + ext) * ci, spring + (rise + ext) * si)))
            bm = bmesh.new()
            vv = []
            for xo in (sgn * (W2 - 0.04), sgn * (W2 + 0.03)):
                vv.append([bm.verts.new(Vector((xo, p.y, p.z))) for p in pts])
            A, B = vv
            for f in ((A[0], A[1], A[3], A[2]), (B[0], B[2], B[3], B[1]), (A[0], A[2], B[2], B[0]),
                      (A[1], B[1], B[3], A[3]), (A[0], B[0], B[1], A[1]), (A[2], A[3], B[3], B[2])):
                try:
                    bm.faces.new(f)
                except ValueError:
                    pass
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            sb.add_bm(bm, M["dressed"], scale=0.5)
    for sgn in (-1, 1):
        y = -L2
        while y < L2 - 0.05:
            ln = min(rng.uniform(0.5, 0.7), L2 - y)
            yc = y + ln / 2
            slope = math.atan(-2 * deck_c * yc / L2 ** 2)
            bm = geo.bm_box(0, 0, 0, 0.38, ln - 0.015, 0.12, bevel=0.015, segs=1)
            m = Matrix.Translation((sgn * (W2 + PW) / 2, yc, top(yc) + 0.58 + 0.06)) @ Matrix.Rotation(slope, 4, "X")
            sb.add_bm(bm, M["dressed"], scale=0.5, matrix=m)
            y += ln
    deck = mb.build(name)
    stones = sb.build(name + "_dressed")
    cols = []
    nseg = 6
    for k in range(nseg):
        ya, yb = -L2 + 4.4 * k / nseg, -L2 + 4.4 * (k + 1) / nseg
        cols.append(nlib.col_hull(f"Deck{k}", [(x, y, z) for x in (-W2, W2) for y in (ya, yb)
                                               for z in (top(y), top(y) - 0.35)]))
        for sgn in (-1, 1):
            cols.append(nlib.col_hull(f"Parapet{k}_{'L' if sgn < 0 else 'R'}",
                                      [(x, y, z) for x in (sgn * PW, sgn * W2) for y in (ya, yb)
                                       for z in (top(y), top(y) + 0.7)]))
    return [deck, stones], cols, {"tris": mb.tris() + sb.tris()}


# ============================================================== STREAM BANK
SB_L = 4.0
SB_PROF = [(-2.0, 0.0), (-1.3, 0.0), (-0.8, 0.0), (-0.55, -0.01), (-0.42, -0.06), (-0.33, -0.2), (-0.24, -0.38),
           (-0.12, -0.55), (0.02, -0.68), (0.2, -0.76), (0.5, -0.82), (0.9, -0.85), (1.4, -0.86)]


def sb_S(i, y):
    x, z = SB_PROF[i]
    k = 1.0 if -0.6 < x < 0.4 else 0.35
    dx = 0.18 * pnoise(0.0, y, 0.0, SB_L, 0.8, 41.0) * k
    dz = (0.04 * pnoise(x, y, 0.0, SB_L, 2.0, 43.0) + 0.02 * pnoise(x, y, 1.0, SB_L, 5.0, 47.0))
    return Vector((x + dx, y, z + dz * (0.3 if x < -0.7 else 1.0)))


def stream_bank(name, seed=51):
    rng = np.random.default_rng(seed)
    M = _mats()
    gm = mat("GrassCard", "grasscards", alpha=True)
    mb = MB()
    nr = int(SB_L * 6)
    rows = []
    for r in range(nr + 1):
        y = -SB_L / 2 + SB_L * r / nr
        rows.append(mb.add_verts([sb_S(i, y) for i in range(len(SB_PROF))]))
    for r in range(nr):
        for c in range(len(SB_PROF) - 1):
            a, b = rows[r] + c, rows[r] + c + 1
            cc, d = rows[r + 1] + c + 1, rows[r + 1] + c
            ctr = (mb.verts[a] + mb.verts[cc]) * 0.5
            x0 = SB_PROF[c][0]
            e = pnoise(ctr.x, ctr.y, 0, SB_L, 1.5, 53.0)
            if x0 < -0.5 + 0.08 * e:
                mt = M["grass"]
            elif x0 < -0.15:
                mt = M["earth"]
            elif x0 < 0.15 + 0.1 * e:
                mt = M["mud"]
            else:
                mt = M["gravel"]
            q = (a, d, cc, b)
            mb.face(q, [(mb.verts[k].x * 0.5, mb.verts[k].y * 0.5) for k in q], mt)
    sb = MB()
    spots = []
    for k in range(9):
        y = rng.uniform(-SB_L / 2 + 0.3, SB_L / 2 - 0.3)
        i = int(rng.integers(6, 10))
        p = sb_S(i, y)
        s = rng.uniform(0.12, 0.3)
        bm = rock_bm(s, s * 0.8, s * 0.55, seed + k, 3, sink=0.25, rough=0.6)
        bmesh.ops.translate(bm, vec=p, verts=bm.verts)
        bm.normal_update()
        sb.add_bm(bm, M["granite"], scale=0.5, smooth=True)
    cm = MB()
    for t in range(34):
        y = rng.uniform(-SB_L / 2 + 0.15, SB_L / 2 - 0.15)
        i = int(rng.integers(2, 5)) if t < 24 else int(rng.integers(7, 9))
        p = sb_S(i, y)
        regs = ["grass_a", "grass_b"] if t < 24 else ["rush_a", "rush_b"]
        for c in range(3):
            az = rng.uniform(0, 6.28)
            dirh = Vector((math.cos(az), math.sin(az), 0))
            lean = Vector((0.6, 0, 0)) if t < 24 else Vector()       # overhang toward the water
            h = rng.uniform(0.3, 0.55) if t < 24 else rng.uniform(0.6, 0.9)
            upv = (UP + lean + dirh * 0.25).normalized()
            card(cm, p, upv, dirh.cross(UP).normalized(), h * 0.5, h, GRASS_REGIONS[regs[c % 2]], gm,
                 bend=h * 0.3, segs=2)
    ob = mb.build(name)
    obs = sb.build(name + "_stones")
    obc = cm.build(name + "_grass")
    cols = []
    for k in range(4):
        ya, yb = -SB_L / 2 + k, -SB_L / 2 + k + 1
        cols.append(nlib.col_hull(f"Bank{k}", [(p.x, yy, z) for yy in (ya, yb) for i in range(len(SB_PROF))
                                               for p in [sb_S(i, yy)] for z in (p.z, -1.1)]))
    return [ob, obs, obc], cols, {"tris": mb.tris() + sb.tris() + cm.tris()}


WATER = {
    "footbridge_stone": footbridge,
    "stream_bank_4m": stream_bank,
}

ALL = {**ROCKS, **TALUS, **WATER}


def build(name):
    vis, cols, stats = ALL[name](name)
    ob = vis[0]
    stats["dims"] = tuple(round(v, 2) for v in ob.dimensions)
    if name in TALUS:
        pv = [dict(elev=14.0, azim=-55.0, dist_mul=0.55, sun_elev=10.0, fill=0.8, target=(0, 0, 2.0)),
              dict(suffix="_end", elev=8.0, azim=-10.0, dist_mul=0.42, sun_elev=10.0, fill=0.8, target=(0, -2.0, 1.2))]
    elif name == "footbridge_stone":
        pv = [dict(elev=12.0, azim=-62.0, dist_mul=0.7, sun_elev=10.0, fill=0.8, ground=None),
              dict(suffix="_arch", elev=2.0, azim=-90.0, dist_mul=0.62, sun_elev=10.0, fill=0.8, ground=None)]
    elif name == "stream_bank_4m":
        pv = dict(elev=18.0, azim=60.0, dist_mul=0.6, sun_elev=10.0, fill=0.8, ground=None)
    else:
        pv = dict(elev=16.0, azim=-30.0, dist_mul=0.75, sun_elev=10.0, fill=0.8)
    return vis, cols, stats, pv
