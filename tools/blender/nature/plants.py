"""Bushes (gorse, bramble, dead bracken), ground-cover cards (grass, rush, dead fern) and reeds.

Every card material uses alpha clip (glTF MASK). Ground cover and reeds share one atlas with the
material name 'GrassCard' (regions in ntex.GRASS_REGIONS) so Godot can batch them in a MultiMesh.
"""
import math

import bmesh
import numpy as np
from mathutils import Vector, noise

import nlib
from nlib import MB, card, mat, tube
from ntex import GRASS_REGIONS

UP = Vector((0, 0, 1))


def _perp(d, roll):
    ref = UP if abs(d.z) < 0.95 else Vector((1, 0, 0))
    a = d.cross(ref).normalized()
    b = d.cross(a).normalized()
    return (a * math.cos(roll) + b * math.sin(roll)).normalized()


def _rect(name, sub=None):
    u0, v0, u1, v1 = GRASS_REGIONS[name]
    return (u0, v0, u1, v1)


# =================================================================== GORSE
def _blob_bm(rx, ry, rz, seed, subdiv=2, flat_base=True):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    off = Vector((seed * 1.31, seed * 0.7, 0))
    for v in bm.verts:
        d = v.co.normalized()
        k = 1.0 + 0.22 * noise.noise(d * 1.6 + off) + 0.08 * noise.noise(d * 4.0 + off)
        v.co = Vector((d.x * rx * k, d.y * ry * k, d.z * rz * k))
        if flat_base and v.co.z < 0:
            v.co.z *= 0.15
        v.co.z += rz * 0.12
    return bm


def gorse(name, rx, ry, rz, seed, ncards, spiky=False):
    rng = np.random.default_rng(seed)
    gc = mat("GorseCard", "gorse", alpha=True)
    core = mat("GorseCore", "gorse", alpha=False, normal=True)
    stem = mat("GorseStem", "bark_ash", tint=(0.8, 0.75, 0.6))
    mb = MB()
    cb = _blob_bm(rx * 0.78, ry * 0.78, rz * 0.8, seed, subdiv=2)
    pts = [v.co.copy() for v in cb.verts]
    mb.add_bm(cb, core, scale=1.8, smooth=True)
    # woody stems visible at the base
    for s in range(9):
        a = rng.uniform(0, 6.28)
        r0 = rng.uniform(0.0, 0.25) * min(rx, ry)
        p0 = Vector((math.cos(a) * r0, math.sin(a) * r0, -0.05))
        d = Vector((math.cos(a) * 0.6, math.sin(a) * 0.6, 1.0)).normalized()
        ln = rz * rng.uniform(0.5, 0.9)
        ps = [p0 + d * ln * t + Vector((0, 0, 0)) * t for t in np.linspace(0, 1, 4)]
        tube(mb, ps, [0.03, 0.025, 0.018, 0.01], stem, 5, tile=0.5)
    # cards: rooted on/inside the core surface, pointing outward
    for i in range(ncards):
        u = rng.normal(0, 1, 3)
        d = Vector(u).normalized()
        if d.z < -0.25:
            d.z = -d.z * 0.3
        d.normalize()
        k = 1.0 + 0.22 * noise.noise(d * 1.6 + Vector((seed * 1.31, seed * 0.7, 0)))
        depth = rng.uniform(0.55, 1.0)
        base = Vector((d.x * rx * k * depth, d.y * ry * k * depth, max(0.02, d.z * rz * k * depth + rz * 0.12)))
        outv = Vector((base.x / rx ** 2, base.y / ry ** 2, (base.z - rz * 0.1) / rz ** 2)).normalized()
        upv = (outv + Vector(rng.normal(0, 0.45 if spiky else 0.35, 3))).normalized()
        if upv.z < -0.1:
            upv.z = abs(upv.z)
            upv.normalize()
        sz = rng.uniform(0.45, 0.7) * (1.25 if spiky else 1.0) * min(1.0, 0.45 + 0.4 * max(rx, rz))
        card(mb, base - upv * sz * 0.25, upv, _perp(upv, rng.uniform(0, 6.28)), sz, sz, (0, 0, 1, 1), gc)
    ob = mb.build(name)
    hull = [Vector((p.x * 1.1, p.y * 1.1, p.z)) for p in pts]
    col = nlib.col_hull("Gorse", [tuple(p) for p in hull])
    return [ob], [col], {"tris": mb.tris(), "dims": tuple(round(v, 2) for v in ob.dimensions)}


# ================================================================= BRAMBLE
def bramble(name, seed, ncanes, spread):
    rng = np.random.default_rng(seed)
    bc = mat("BrambleCard", "bramble", alpha=True)
    cane = mat("BrambleCane", "stem", tint=(0.11, 0.045, 0.05))
    dead = mat("BrambleDeadCane", "stem", tint=(0.24, 0.19, 0.15))
    mb = MB()
    ncards = 0
    for c in range(ncanes):
        a = rng.uniform(0, 6.28)
        r0 = rng.uniform(0, 0.3)
        p0 = Vector((math.cos(a) * r0, math.sin(a) * r0, -0.05))
        reach = spread * rng.uniform(0.6, 1.2)
        top = rng.uniform(0.35, 0.95)
        dirv = Vector((math.cos(a), math.sin(a), 0))
        pts = []
        n = 9
        for i in range(n + 1):
            t = i / n
            # arching cane: rises then bends over and roots at the tip
            hz = top * math.sin(math.pi * min(1.0, t * 1.05)) ** 0.9
            q = p0 + dirv * reach * t + Vector((0, 0, max(hz, 0.0) - 0.05 * t))
            q += Vector((noise.noise(q * 2 + Vector((seed, 0, 0))), noise.noise(q * 2 + Vector((0, seed, 0))), 0)) * 0.08
            pts.append(q)
        isdead = rng.random() < 0.25
        tube(mb, pts, [0.008 * (1 - 0.5 * i / n) for i in range(n + 1)], dead if isdead else cane, 5, tile=0.5)
        if isdead:
            continue
        # leaf cards along the cane (halves of the atlas: two cell variants)
        for i in range(1, n):
            t = i / n
            p = pts[i]
            d = (pts[i + 1] - pts[i - 1]).normalized()
            for k in range(3):
                sz = rng.uniform(0.6, 0.9)
                sd = _perp(d, rng.uniform(0, 6.28))
                upv = (d + sd * rng.uniform(0.4, 1.0) + UP * 0.3).normalized()
                cell = (0.0, 0.0, 0.5, 1.0) if rng.random() < 0.5 else (0.5, 0.0, 1.0, 1.0)
                card(mb, p - upv * 0.05, upv, _perp(upv, rng.uniform(0, 6.28)), sz * 0.5, sz, cell, bc,
                     bend=sz * 0.15, segs=2)
                ncards += 1
    ob = mb.build(name)
    return [ob], [], {"tris": mb.tris(), "cards": ncards, "dims": tuple(round(v, 2) for v in ob.dimensions)}


# ================================================================= BRACKEN
def bracken(name, seed, nfronds, size):
    rng = np.random.default_rng(seed)
    bk = mat("BrackenCard", "bracken", alpha=True)
    mb = MB()
    for f in range(nfronds):
        r = size * math.sqrt(rng.random()) * 0.5
        a = rng.uniform(0, 6.28)
        base = Vector((math.cos(a) * r, math.sin(a) * r, 0.0))
        # most dead fronds are collapsed: lean them hard in a prevailing direction with scatter
        lean = rng.uniform(0.35, 1.35) if rng.random() < 0.75 else rng.uniform(0.05, 0.4)
        az = 0.6 + rng.normal(0, 0.9)
        dirh = Vector((math.cos(az), math.sin(az), 0))
        upv = (UP * math.cos(lean) + dirh * math.sin(lean)).normalized()
        h = rng.uniform(0.5, 1.0)
        side = dirh.cross(UP).normalized() if lean > 0.2 else _perp(upv, rng.uniform(0, 6.28))
        side = (side + Vector(rng.normal(0, 0.25, 3))).normalized()
        cell = (0.0, 0.0, 0.5, 1.0) if rng.random() < 0.5 else (0.5, 0.0, 1.0, 1.0)
        card(mb, base, upv, side, h * 0.5, h, cell, bk, bend=h * 0.35 * math.cos(lean), segs=3)
    ob = mb.build(name)
    return [ob], [], {"tris": mb.tris(), "dims": tuple(round(v, 2) for v in ob.dimensions)}


# ============================================================ GROUND COVER
def clump(name, seed, regions, n, hmin, hmax, aspect, spread, lean, bend, segs=2, radial=False):
    """Card clump: n cards from regions (cycled), height hmin..hmax, width = height*aspect."""
    rng = np.random.default_rng(seed)
    gm = mat("GrassCard", "grasscards", alpha=True)
    mb = MB()
    for i in range(n):
        reg = regions[i % len(regions)]
        h = rng.uniform(hmin, hmax)
        a = (i / n) * 2 * math.pi + rng.normal(0, 0.3)
        r = spread * math.sqrt(rng.random())
        base = Vector((math.cos(a) * r, math.sin(a) * r, -0.01))
        if radial:
            dirh = Vector((math.cos(a), math.sin(a), 0))
        else:
            az = rng.uniform(0, 6.28)
            dirh = Vector((math.cos(az), math.sin(az), 0))
        ln = rng.uniform(*lean)
        upv = (UP * math.cos(ln) + dirh * math.sin(ln)).normalized()
        side = dirh.cross(UP).normalized() if radial else _perp(upv, rng.uniform(0, 6.28))
        if not radial:
            side = Vector((side.x, side.y, side.z * 0.3)).normalized()
        w = h * aspect
        card(mb, base, upv, side, w, h, _rect(reg), gm, bend=h * bend, segs=segs,
             lift=(dirh * 0.6 + Vector((0, 0, -1))).normalized())
    ob = mb.build(name)
    return [ob], [], {"tris": mb.tris(), "dims": tuple(round(v, 2) for v in ob.dimensions)}


BUSHES = {
    "gorse_a": lambda n: gorse(n, 0.8, 0.7, 0.75, 101, 1100),
    "gorse_b": lambda n: gorse(n, 1.3, 1.0, 1.0, 102, 1500),
    "gorse_c": lambda n: gorse(n, 0.55, 0.5, 0.75, 103, 750, spiky=True),
    "bramble_a": lambda n: bramble(n, 201, 34, 1.3),
    "bramble_b": lambda n: bramble(n, 202, 46, 1.9),
    "bracken_a": lambda n: bracken(n, 301, 140, 2.4),
    "bracken_b": lambda n: bracken(n, 302, 220, 3.2),
}
GROUND = {
    "grass_tuft_a": lambda n: clump(n, 401, ["grass_a"], 14, 0.28, 0.45, 0.5, 0.06, (0.05, 0.45), 0.25),
    "grass_tuft_b": lambda n: clump(n, 402, ["grass_b"], 16, 0.35, 0.55, 0.5, 0.08, (0.1, 0.6), 0.3),
    "grass_tuft_c": lambda n: clump(n, 403, ["grass_a", "grass_b"], 26, 0.3, 0.6, 0.5, 0.16, (0.05, 0.6), 0.28),
    "rush_clump_a": lambda n: clump(n, 501, ["rush_a"], 10, 0.75, 1.05, 0.5, 0.1, (0.0, 0.25), 0.08),
    "rush_clump_b": lambda n: clump(n, 502, ["rush_b", "rush_a"], 14, 0.6, 0.95, 0.5, 0.15, (0.05, 0.35), 0.12),
    "fern_dead_a": lambda n: clump(n, 601, ["fern_a"], 9, 0.55, 0.8, 1.0, 0.05, (0.5, 0.95), 0.3, segs=3, radial=True),
    "fern_dead_b": lambda n: clump(n, 602, ["fern_b", "fern_a"], 12, 0.5, 0.75, 1.0, 0.08, (0.6, 1.1), 0.2, segs=3, radial=True),
}
WATER = {
    "reeds_a": lambda n: clump(n, 701, ["reed"], 16, 1.8, 2.4, 0.25, 0.25, (0.0, 0.2), 0.05, segs=3),
    "reeds_b": lambda n: clump(n, 702, ["reed"], 22, 1.5, 2.2, 0.25, 0.45, (0.0, 0.45), 0.08, segs=3),
}
ALL = {**BUSHES, **GROUND, **WATER}


def build(name):
    vis, cols, stats = ALL[name](name)
    big = name in BUSHES
    h = stats["dims"][2]
    pv = dict(elev=12.0 if big else 18.0, azim=-30.0, dist_mul=0.8 if big else 0.9, sun_elev=8.0, fill=0.8,
              target=(0, 0, h * 0.45))
    return vis, cols, stats, pv
