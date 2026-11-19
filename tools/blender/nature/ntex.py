"""Nature kit textures (numpy only): bark, twig/needle/foliage card atlases, rock, moss, bank earth.

Bark and rock sets tile seamlessly. Card atlases are RGBA (alpha cut-out) drawn by a small
vector rasteriser (Canvas) that also writes a tangent-space normal map so twigs read as round.

Run standalone with Blender's bundled Python:  python.exe ntex.py [names...] [--force]
"""
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.abspath(os.path.join(HERE, "..", "env"))
for p in (HERE, ENV):
    if p not in sys.path:
        sys.path.insert(0, p)
from texlib import (F, blur, cavity_ao, cell_rand, fbm, grid, height_to_normal,  # noqa: E402
                    lichen_mask, mix, orm, perlin, rgb, ridged, sstep, voronoi, write_png)

TEX_DIR = os.path.join(HERE, "out", "tex")


def save(name, alb, nrm=None, om=None, alpha=None):
    if alpha is not None:
        alb = np.dstack([alb, alpha])
    write_png(os.path.join(TEX_DIR, f"{name}_albedo.png"), alb)
    if nrm is not None:
        write_png(os.path.join(TEX_DIR, f"{name}_normal.png"), nrm)
    if om is not None:
        write_png(os.path.join(TEX_DIR, f"{name}_orm.png"), om)


# =================================================================== BARK
# All bark tiles: 1024^2 covering 1 m x 1 m. u runs around the stem, v (image up) along it.

def _moss_layer(X, Y, seed, cover):
    """Cushion moss: returns (mask, height, albedo)."""
    m = sstep(0.5 - cover, 0.62 - cover, fbm(X, Y, 5, 5, seed) * 0.5 + 0.5 + fbm(X, Y, 40, 3, seed + 1) * 0.12)
    bumps = ridged(X, Y, 90, 3, seed + 2)
    hm = m * (0.004 + 0.003 * bumps)
    g = sstep(-0.5, 0.6, fbm(X, Y, 12, 3, seed + 3))
    col = mix(rgb((0.10, 0.17, 0.035), X.shape), rgb((0.24, 0.32, 0.07), X.shape), g)
    col = mix(col, rgb((0.30, 0.27, 0.12), X.shape), sstep(0.4, 0.9, perlin(X, Y, 70, 70, seed + 4)) * 0.5)
    col *= (0.7 + 0.4 * bumps)[..., None]
    return m.astype(F), hm.astype(F), col


def _finish_bark(alb, h, rough, X, Y, seed, px, moss_cover, lichen=(0.10, 0.08)):
    """Add lichen (always) and moss (cover>0) and produce (alb, nrm, orm)."""
    ly = lichen_mask(X, Y, seed + 50, lichen[0], 10)
    lg = lichen_mask(X, Y, seed + 51, lichen[1], 16)
    alb = mix(alb, rgb((0.55, 0.60, 0.48), X.shape), lg * 0.8)
    alb = mix(alb, rgb((0.62, 0.52, 0.18), X.shape), ly * 0.55)
    h = h + (ly + lg) * 0.0006
    if moss_cover > 0:
        # moss settles in furrows first
        hn = (h - h.min()) / (h.max() - h.min() + 1e-6)
        mm, mh, mc = _moss_layer(X, Y, seed + 60, moss_cover)
        mm = np.clip(mm + sstep(0.45, 0.15, hn) * moss_cover * 1.2 * sstep(0.0, 0.3, fbm(X, Y, 4, 3, seed + 61) + 0.2), 0, 1)
        alb = mix(alb, mc, mm)
        h = h + mh * mm
        rough = mix(rough, np.full_like(rough, 0.95), mm)
    h = h.astype(F)
    ao = cavity_ao(h, px, (0.003, 0.012, 0.03), 1.2)
    alb = alb * (0.55 + 0.45 * ao)[..., None]
    return alb, height_to_normal(h, px, 1.0), orm(ao, rough)


def bark_oak(res=1024, seed=201, moss=0.0):
    """Pedunculate oak: deep vertical fissures between long, broken, blocky ridges."""
    X, Y = grid(res)
    px = 1.0 / res
    w = fbm(X, Y, 3, 4, seed) * 0.05
    Xw = (X + w) % 1.0
    # wide plates separated by narrow vertical fissures (zero crossings of stretched noise)
    n1 = perlin(Xw, Y, 9, 2, seed + 10) * 0.7 + perlin(Xw, Y, 19, 3, seed + 11) * 0.3
    plate_v = sstep(0.03, 0.22, np.abs(n1))
    # irregular horizontal breaks, only on some plates
    nb = perlin(Xw, Y, 4, 11, seed + 12)
    bmask = sstep(0.1, 0.4, perlin(Xw, Y, 14, 6, seed + 13))
    brk = 1.0 - (1.0 - sstep(0.02, 0.09, np.abs(nb))) * bmask
    rr = np.dstack([fbm(X, Y, 9, 2, seed + 3) * 0.5 + 0.5, fbm(X, Y, 7, 2, seed + 4) * 0.5 + 0.5])
    plates = plate_v * (0.3 + 0.7 * brk)
    h = 0.02 * plates + 0.004 * rr[..., 0] * plates
    h += 0.002 * fbm(X, Y, 10, 4, seed + 4, aniso=(5, 1)) + 0.001 * ridged(X, Y, 40, 3, seed + 5)
    hn = (h - h.min()) / (h.max() - h.min())
    alb = mix(rgb((0.06, 0.05, 0.045), X.shape), rgb((0.30, 0.29, 0.26), X.shape), sstep(0.15, 0.7, hn))
    alb = mix(alb, rgb((0.40, 0.39, 0.36), X.shape), sstep(0.8, 1.0, hn) * 0.6)
    alb *= (0.85 + 0.25 * rr[..., 1])[..., None] * (0.9 + 0.15 * fbm(X, Y, 6, 3, seed + 6))[..., None]
    rough = 0.82 + 0.1 * (1 - hn)
    return _finish_bark(alb, h, rough, X, Y, seed, px, moss, (0.12, 0.14))


def bark_beech(res=1024, seed=211, moss=0.0):
    X, Y = grid(res)
    px = 1.0 / res
    h = 0.0012 * fbm(X, Y, 6, 5, seed) + 0.0004 * perlin(X, Y, 120, 60, seed + 1)
    # horizontal 'eyebrow' scars and ring creases
    scar = sstep(0.75, 0.9, perlin(X, Y, 12, 40, seed + 2) * 0.5 + 0.5) * sstep(0.2, 0.6, fbm(X, Y, 5, 3, seed + 3))
    h -= scar * 0.0015
    g = sstep(-0.4, 0.6, fbm(X, Y, 4, 5, seed + 4))
    alb = mix(rgb((0.25, 0.26, 0.25), X.shape), rgb((0.37, 0.37, 0.355), X.shape), g)
    algae = sstep(-0.2, 0.5, fbm(X, Y, 3, 4, seed + 5, aniso=(1, 3)))
    alb = mix(alb, rgb((0.19, 0.25, 0.16), X.shape), algae * 0.6)
    alb = mix(alb, alb * 0.45, scar[..., None] * 0.8)
    # script lichen / white crusts
    wl = lichen_mask(X, Y, seed + 6, 0.25, 9)
    alb = mix(alb, rgb((0.66, 0.67, 0.63), X.shape), wl * 0.6)
    alb *= (0.94 + 0.08 * fbm(X, Y, 40, 2, seed + 7))[..., None]
    rough = 0.58 + 0.15 * algae
    return _finish_bark(alb, h, rough, X, Y, seed, px, moss, (0.03, 0.08))


def bark_chestnut(res=1024, seed=221, moss=0.0):
    X, Y = grid(res)
    px = 1.0 / res
    S = (X + (1.0 - Y)) % 1.0           # spiral: one full turn per metre (tileable shear)
    w = fbm(X, Y, 5, 3, seed) * 0.03
    r1 = ridged((S * 1.0 + w) % 1.0, Y, 9, 1, seed + 1)
    ridge = perlin((S + w) % 1.0, Y, 11, 2, seed + 2)
    ridges = sstep(-0.35, 0.45, ridge) * (0.7 + 0.3 * r1)
    f1, f2, cid, _, _ = voronoi((S + w) % 1.0, Y, 11, 4, seed + 3, 0.8)
    cross = sstep(0.0, 0.012, f2 - f1)
    h = 0.018 * ridges * cross + 0.003 * fbm(X, Y, 20, 4, seed + 4, aniso=(3, 1))
    hn = (h - h.min()) / (h.max() - h.min())
    alb = mix(rgb((0.08, 0.06, 0.05), X.shape), rgb((0.34, 0.27, 0.21), X.shape), sstep(0.15, 0.7, hn))
    alb = mix(alb, rgb((0.40, 0.37, 0.33), X.shape), sstep(0.75, 1.0, hn) * 0.5)
    alb *= (0.9 + 0.15 * fbm(X, Y, 8, 3, seed + 5))[..., None]
    rough = 0.8 + 0.1 * (1 - hn)
    return _finish_bark(alb, h, rough, X, Y, seed, px, moss, (0.08, 0.1))


def bark_ash(res=1024, seed=231, moss=0.0):
    X, Y = grid(res)
    px = 1.0 / res
    w = fbm(X, Y, 4, 3, seed) * 0.02
    a = np.abs(np.sin(((X + w) * 18 + (1 - Y) * 6) * np.pi))
    b = np.abs(np.sin(((X + w) * 18 - (1 - Y) * 6) * np.pi))
    net = np.maximum(a, b) ** 3
    ridges = sstep(0.4, 0.95, net * (0.75 + 0.25 * fbm(X, Y, 16, 3, seed + 1)))
    h = 0.008 * ridges + 0.002 * fbm(X, Y, 24, 4, seed + 2, aniso=(4, 1))
    hn = (h - h.min()) / (h.max() - h.min())
    alb = mix(rgb((0.15, 0.15, 0.14), X.shape), rgb((0.44, 0.44, 0.41), X.shape), sstep(0.15, 0.8, hn))
    alb *= (0.9 + 0.15 * fbm(X, Y, 6, 3, seed + 3))[..., None]
    rough = 0.75 + 0.1 * (1 - hn)
    return _finish_bark(alb, h, rough, X, Y, seed, px, moss, (0.06, 0.16))


def bark_pine(res=1024, seed=241, moss=0.0):
    X, Y = grid(res)
    px = 1.0 / res
    w = fbm(X, Y, 3, 3, seed) * 0.04
    f1, f2, cid, _, _ = voronoi((X + w) % 1.0, Y, 7, 2, seed + 1, 0.9)
    edge = f2 - f1
    rr = cell_rand(cid, seed + 2, 3)
    n1 = perlin((X + w) % 1.0, Y, 8, 2, seed + 9)
    plate = sstep(0.0, 0.03, edge) * sstep(0.02, 0.15, np.abs(n1))
    flake = sstep(0.3, 0.7, fbm(X, Y, 30, 3, seed + 3)) * plate
    h = 0.02 * plate + 0.004 * rr[..., 0] * plate + 0.0015 * flake + 0.0015 * fbm(X, Y, 40, 3, seed + 4)
    hn = (h - h.min()) / (h.max() - h.min())
    red = mix(rgb((0.27, 0.16, 0.11), X.shape), rgb((0.36, 0.23, 0.15), X.shape), rr[..., 1])
    grey = rgb((0.25, 0.23, 0.21), X.shape)
    top = mix(red, grey, sstep(0.55, 0.85, rr[..., 2]) * 0.7)
    top = mix(top, top * 1.25, flake * 0.4)
    alb = mix(rgb((0.06, 0.04, 0.03), X.shape), top, sstep(0.25, 0.6, hn))
    rough = 0.8 + 0.1 * (1 - hn)
    return _finish_bark(alb, h, rough, X, Y, seed, px, moss, (0.04, 0.06))


BARKS = {"oak": bark_oak, "beech": bark_beech, "chestnut": bark_chestnut, "ash": bark_ash, "pine": bark_pine}
MOSS_COVER = {"oak": 0.30, "beech": 0.22, "chestnut": 0.28, "ash": 0.26, "pine": 0.12}


# ================================================================ CANVAS
class Canvas:
    """Tiny anti-aliased vector rasteriser with a depth buffer and round-stem normals.
    Coordinates in pixels, x right, y DOWN (image rows)."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.col = np.empty((h, w, 3), F)
        self.col[:] = bg
        self.a = np.zeros((h, w), F)
        self.z = np.full((h, w), -1e9, F)
        self.n = np.zeros((h, w, 3), F)
        self.n[..., 2] = 1.0

    def _win(self, x0, y0, x1, y1):
        ix0, ix1 = max(0, int(math.floor(x0))), min(self.w, int(math.ceil(x1)) + 1)
        iy0, iy1 = max(0, int(math.floor(y0))), min(self.h, int(math.ceil(y1)) + 1)
        if ix0 >= ix1 or iy0 >= iy1:
            return None
        X, Y = np.meshgrid(np.arange(ix0, ix1, dtype=F) + 0.5, np.arange(iy0, iy1, dtype=F) + 0.5)
        return (slice(iy0, iy1), slice(ix0, ix1)), X, Y

    def _write(self, sl, cov, zz, col, nx, ny, nz):
        m = (cov > 0.0) & (zz > self.z[sl])
        if not m.any():
            return
        c = self.col[sl]
        c[m] = col if np.ndim(col) == 1 else col[m]
        n = self.n[sl]
        n[m, 0] = nx[m]
        n[m, 1] = ny[m]
        n[m, 2] = nz[m]
        self.z[sl] = np.where(m, zz, self.z[sl])
        self.a[sl] = np.maximum(self.a[sl], cov)

    def seg(self, p0, p1, r0, r1, col, zb=0.0):
        x0, y0 = p0
        x1, y1 = p1
        rm = max(r0, r1) + 1.5
        win = self._win(min(x0, x1) - rm, min(y0, y1) - rm, max(x0, x1) + rm, max(y0, y1) + rm)
        if win is None:
            return
        sl, X, Y = win
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy + 1e-9
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0, 1)
        qx = X - (x0 + t * dx)
        qy = Y - (y0 + t * dy)
        dist = np.sqrt(qx * qx + qy * qy)
        r = r0 + (r1 - r0) * t
        cov = np.clip(r - dist + 0.5, 0, 1)
        L = math.sqrt(L2)
        pxv, pyv = -dy / L, dx / L
        sd = np.clip((qx * pxv + qy * pyv) / np.maximum(r, 0.8), -1, 1)
        nz = np.sqrt(1 - sd * sd)
        self._write(sl, cov, zb + nz * r, np.asarray(col, F), pxv * sd, -pyv * sd, nz)

    def leaf(self, base, ang, length, width, col, zb=0.0, serr=0.0, curl=0.0, tipp=1.0):
        """Pointed lens-shaped leaf from base along angle (radians, image space)."""
        ca, sa = math.cos(ang), math.sin(ang)
        cx, cy = base[0] + ca * length / 2, base[1] + sa * length / 2
        rm = length / 2 + 2
        win = self._win(cx - rm, cy - rm, cx + rm, cy + rm)
        if win is None:
            return
        sl, X, Y = win
        u = ((X - cx) * ca + (Y - cy) * sa) / (length / 2)
        v = -(X - cx) * sa + (Y - cy) * ca
        uu = np.clip(u, -1, 1)
        half = width / 2 * np.clip(1 - uu * uu, 0, 1) ** 0.7 * np.where(uu > 0, (1 - uu) ** (0.15 * tipp) + 0.0, 1.0)
        if serr > 0:
            half = half * (1 - serr * (0.5 + 0.5 * np.sin(u * 22)))
        d = half - np.abs(v)
        cov = np.clip(d + 0.5, 0, 1) * (np.abs(u) < 1)
        fold = np.clip(v / (width / 2 + 1e-3), -1, 1)
        nxv = -sa * fold * 0.45 + ca * curl
        nyv = -(ca * fold * 0.45) + sa * curl
        nz = np.sqrt(np.clip(1 - nxv ** 2 - nyv ** 2, 0.05, 1))
        midrib = np.abs(v) < 0.8
        colarr = np.broadcast_to(np.asarray(col, F), X.shape + (3,)).copy()
        colarr[midrib] *= 0.7
        self._write(sl, cov, zb + 2.0 + fold * 0, colarr, nxv, -nyv, nz)

    def dot(self, c, r, col, zb=0.0):
        self.seg(c, (c[0] + 0.01, c[1]), r, r, col, zb)

    def finish(self, noise_seed=0, var=0.15):
        h, w = self.h, self.w
        X, Y = grid(h, w)
        n = fbm(X, Y, 8, 3, noise_seed)
        col = self.col * (1 + var * n)[..., None]
        nrm = self.n * 0.5 + 0.5
        nrm[self.a <= 0] = (0.5, 0.5, 1.0)
        return np.clip(col, 0, 1), nrm.astype(F), self.a


# ============================================================ SPRAY GROWTH
class Spray:
    """2D branching generator in abstract units; collects primitives, then is fitted into a cell."""

    def __init__(self, rng):
        self.rng = rng
        self.segs = []      # (p0, p1, r0, r1, col, z)
        self.leaves = []    # (base, ang, len, wid, col, z, serr)
        self.dots = []      # (c, r, col, z)

    def fit(self, cv, cell, margin=0.02, base_frac=0.5):
        """Scale positions (not radii) to fit cell=(x0,y0,w,h) in pixels, base at bottom centre."""
        x0, y0, cw, ch = cell
        pts = [s[0] for s in self.segs] + [s[1] for s in self.segs] + [l[0] for l in self.leaves]
        for l in self.leaves:
            pts.append((l[0][0] + math.cos(l[1]) * l[2], l[0][1] + math.sin(l[1]) * l[2]))
        P = np.array(pts)
        mxx = max(np.abs(P[:, 0]).max(), 1e-6)
        mny = P[:, 1].min()     # y up in abstract space -> min is lowest; growth goes +y
        mxy = P[:, 1].max()
        s = min((cw * (0.5 - margin)) / mxx, (ch * (1 - 2 * margin)) / max(mxy - min(mny, 0), 1e-6))
        bx = x0 + cw * base_frac
        by = y0 + ch * (1 - margin)

        def T(p):
            return (bx + p[0] * s, by - (p[1] - min(mny, 0)) * s)

        order = sorted(range(len(self.segs)), key=lambda i: self.segs[i][5])
        for i in order:
            p0, p1, r0, r1, col, z = self.segs[i]
            cv.seg(T(p0), T(p1), r0, r1, col, z)
        for (c, r, col, z) in self.dots:
            cv.dot(T(c), r, col, z)
        for (b, ang, ln, wd, col, z, serr) in self.leaves:
            cv.leaf(T(b), -ang, ln * s, wd * s, col, z, serr)
        return s


def grow_twig(sp, p, ang, length, r, depth, P, side=1):
    """Recursive 2D twig. ang in radians (abstract space, y up). P: species params."""
    rng = sp.rng
    n = max(2, int(length / P["internode"]))
    seglen = length / n
    pos = p
    a = ang
    for i in range(n):
        t = (i + 1) / n
        zz = P.get("zigzag", 0.1)
        a += zz * (1 if i % 2 == 0 else -1) + rng.normal(0, P.get("wobble", 0.05)) + P.get("tropism", 0.0) * math.cos(a)
        nxt = (pos[0] + math.cos(a) * seglen, pos[1] + math.sin(a) * seglen)
        ra = r * (1 - (i / n) * P.get("taper", 0.6))
        rb = r * (1 - t * P.get("taper", 0.6))
        sp.segs.append((pos, nxt, max(ra, P["rmin"]), max(rb, P["rmin"]), P["col"], -depth * 3.0 + rng.random()))
        if depth < P["depth"] and i < n - 1 and rng.random() < P["pbranch"] * (0.4 + t):
            sides = (1, -1) if P.get("opposite") else ((1,) if i % 2 == 0 else (-1,))
            for sd in sides:
                ca = a + sd * (P["angle"] + rng.normal(0, 0.15))
                cl = length * (1 - t) * P["ratio"] * rng.uniform(0.7, 1.15) + seglen * 0.5
                grow_twig(sp, nxt, ca, cl, rb * P.get("rratio", 0.7), depth + 1, P)
        elif P.get("bud") and i < n - 1 and rng.random() < 0.6:
            ba = a + (1 if i % 2 == 0 else -1) * 0.7
            sp.leaves.append((nxt, ba, P["bud"][0] * 0.6, P["bud"][1], P["budcol"], 5.0, 0.0))
        if P.get("leafp", 0) and rng.random() < P["leafp"] * t:
            la = a + (1 if rng.random() < 0.5 else -1) * rng.uniform(0.5, 1.4)
            lc = P["leafcols"][rng.integers(len(P["leafcols"]))]
            sp.leaves.append((nxt, la, P["leaf"][0] * rng.uniform(0.8, 1.2), P["leaf"][1] * rng.uniform(0.8, 1.2),
                              np.array(lc, F) * rng.uniform(0.8, 1.15), 4.0 + rng.random(), P.get("serr", 0.0)))
        pos = nxt
    if P.get("bud"):
        sp.leaves.append((pos, a, P["bud"][0], P["bud"][1], P["budcol"], 6.0, 0.0))
    if P.get("cluster") and depth >= 1:
        for k in range(P["cluster"]):
            sp.leaves.append((pos, a + rng.normal(0, 0.9), P["bud"][0] * 0.7, P["bud"][1], P["budcol"], 6.0, 0.0))


TWIG_SPECIES = {
    # internode/length are abstract units ~ metres; rmin etc. in pixels
    "oak": dict(internode=0.045, zigzag=0.22, wobble=0.12, depth=4, pbranch=0.8, angle=0.75, ratio=0.62,
                rratio=0.72, taper=0.55, rmin=1.4, col=(0.17, 0.16, 0.145), bud=(0.010, 0.008),
                budcol=(0.22, 0.16, 0.11), cluster=2, root_r=9.0, length=1.0,
                leafp=0.0, leaf=(0.09, 0.05), leafcols=[(0.32, 0.20, 0.09), (0.27, 0.17, 0.08)]),
    "beech": dict(internode=0.04, zigzag=0.16, wobble=0.05, depth=4, pbranch=0.8, angle=0.62, ratio=0.66,
                  rratio=0.62, taper=0.65, rmin=1.15, col=(0.25, 0.24, 0.23), bud=(0.022, 0.006),
                  budcol=(0.32, 0.22, 0.14), root_r=7.0, length=1.0, tropism=0.03,
                  leafp=0.0, leaf=(0.08, 0.045), leafcols=[(0.36, 0.22, 0.10), (0.30, 0.18, 0.08), (0.40, 0.26, 0.12)],
                  serr=0.08),
    "chestnut": dict(internode=0.06, zigzag=0.14, wobble=0.08, depth=4, pbranch=0.7, angle=0.7, ratio=0.6,
                     rratio=0.72, taper=0.45, rmin=1.8, col=(0.22, 0.17, 0.13), bud=(0.014, 0.011),
                     budcol=(0.30, 0.14, 0.09), root_r=10.0, length=1.0),
    "ash": dict(internode=0.08, zigzag=0.04, wobble=0.06, depth=3, pbranch=0.65, angle=0.68, ratio=0.55,
                rratio=0.7, taper=0.35, rmin=2.2, col=(0.24, 0.24, 0.23), bud=(0.016, 0.014),
                budcol=(0.03, 0.03, 0.03), opposite=True, tropism=0.08, root_r=11.0, length=1.0),
    "hazel": dict(internode=0.05, zigzag=0.12, wobble=0.06, depth=4, pbranch=0.7, angle=0.6, ratio=0.6,
                  rratio=0.7, taper=0.55, rmin=1.4, col=(0.21, 0.16, 0.12), bud=(0.012, 0.009),
                  budcol=(0.28, 0.30, 0.14), root_r=8.0, length=1.0, catkin=True),
    "blackthorn": dict(internode=0.03, zigzag=0.25, wobble=0.25, depth=4, pbranch=0.75, angle=1.05, ratio=0.5,
                       rratio=0.7, taper=0.5, rmin=1.4, col=(0.11, 0.09, 0.08), bud=(0.012, 0.004),
                       budcol=(0.10, 0.08, 0.07), root_r=8.0, length=1.0),
}


def tex_twigs(species, res=2048, seed=300):
    """2x2 atlas of twig sprays for one species. Cell (i,j) -> uv rect, see CARD_CELLS."""
    P = dict(TWIG_SPECIES[species])
    rng = np.random.default_rng(seed + sum(map(ord, species)))
    cv = Canvas(res, res, np.array(P["col"], F) * 1.1)
    cs = res // 2
    for k in range(4):
        cx, cy = (k % 2) * cs, (k // 2) * cs
        sp = Spray(rng)
        Pk = dict(P)
        if species in ("oak", "beech") and k == 3:     # one cell with marcescent dead leaves
            Pk["leafp"] = 0.2 if species == "beech" else 0.18
        root_r = P["root_r"] * rng.uniform(0.9, 1.1)
        grow_twig(sp, (0.0, 0.0), math.pi / 2 + rng.normal(0, 0.08), P["length"], root_r, 0, Pk)
        if P.get("catkin"):
            for (p0, p1, r0, r1, col, z) in list(sp.segs):
                if r1 < 2.0 and rng.random() < 0.05:
                    a = -math.pi / 2 + rng.normal(0, 0.3)
                    sp.leaves.append((p1, a, 0.05, 0.012, (0.52, 0.45, 0.22), 8.0, 0.25))
        sp.fit(cv, (cx, cy, cs, cs))
    col, nrm, a = cv.finish(seed + 7, 0.18)
    return col, nrm, a


def tex_pine(res=2048, seed=400):
    """Maritime pine: 2x2 cells of needle tufts at the end of short shoots (bottom-centre base)."""
    rng = np.random.default_rng(seed)
    cv = Canvas(res, res, np.array((0.13, 0.17, 0.07), F))
    cs = res // 2
    ncols = [(0.07, 0.10, 0.04), (0.09, 0.13, 0.05), (0.11, 0.14, 0.06), (0.06, 0.08, 0.035), (0.13, 0.14, 0.07)]
    for k in range(4):
        sp = Spray(rng)
        # shoot: a main twig with 0-2 side shoots, all bearing needles in the outer part
        shoots = [((0.0, 0.0), math.pi / 2 + rng.normal(0, 0.1), 0.55, 10.0)]
        if k != 0:
            for s in range(rng.integers(1, 3)):
                shoots.append(((0.0, 0.18 + 0.1 * s), math.pi / 2 + (0.6 if s % 2 == 0 else -0.6) + rng.normal(0, 0.1),
                               0.33, 6.5))
        for (base, ang, ln, r) in shoots:
            n = 8
            pos, a = base, ang
            for i in range(n):
                t = (i + 1) / n
                a += rng.normal(0, 0.04)
                nxt = (pos[0] + math.cos(a) * ln / n, pos[1] + math.sin(a) * ln / n)
                sp.segs.append((pos, nxt, r * (1 - 0.4 * (i / n)), r * (1 - 0.4 * t), (0.36, 0.22, 0.12), 0.0))
                # needles in pairs along the outer 70 % of the shoot
                if t > 0.3:
                    for q in range(14):
                        tt = rng.random()
                        bp = (pos[0] + (nxt[0] - pos[0]) * tt, pos[1] + (nxt[1] - pos[1]) * tt)
                        side = 1 if q % 2 == 0 else -1
                        na = a + side * rng.uniform(0.25, 1.1) * (1.15 - 0.5 * t)
                        nl = rng.uniform(0.14, 0.2)
                        ep = (bp[0] + math.cos(na) * nl, bp[1] + math.sin(na) * nl)
                        mid = ((bp[0] + ep[0]) / 2 + rng.normal(0, 0.008), (bp[1] + ep[1]) / 2 - 0.01)
                        c = np.array(ncols[rng.integers(len(ncols))], F) * rng.uniform(0.85, 1.15)
                        z = rng.uniform(-2, 4)
                        sp.segs.append((bp, mid, 1.7, 1.5, c, z))
                        sp.segs.append((mid, ep, 1.5, 0.8, c * 1.05, z))
                pos = nxt
            # terminal bud tuft
            for q in range(26):
                na = a + rng.normal(0, 0.55)
                nl = rng.uniform(0.12, 0.19)
                ep = (pos[0] + math.cos(na) * nl, pos[1] + math.sin(na) * nl)
                c = np.array(ncols[rng.integers(len(ncols))], F) * rng.uniform(0.85, 1.15)
                sp.segs.append((pos, ep, 1.7, 0.8, c, rng.uniform(-2, 4)))
            sp.leaves.append((pos, a, 0.03, 0.012, (0.45, 0.28, 0.14), 6.0, 0.0))
        sp.fit(cv, ((k % 2) * cs, (k // 2) * cs, cs, cs))
    col, nrm, a = cv.finish(seed + 1, 0.12)
    return col, nrm, a


# ============================================================== FOLIAGE
def tex_gorse(res=1024, seed=500):
    """Gorse (ajonc) spray: dense green spines on green stems, a few yellow flowers. 1 cell."""
    rng = np.random.default_rng(seed)
    cv = Canvas(res, res, np.array((0.05, 0.10, 0.03), F))
    sp = Spray(rng)
    scol = [(0.06, 0.13, 0.035), (0.08, 0.16, 0.045), (0.05, 0.10, 0.03), (0.10, 0.17, 0.05)]

    def shoot(p, a, ln, r, d):
        n = max(3, int(ln / 0.025))
        pos = p
        for i in range(n):
            a += rng.normal(0, 0.12)
            nxt = (pos[0] + math.cos(a) * ln / n, pos[1] + math.sin(a) * ln / n)
            sp.segs.append((pos, nxt, r, r * 0.92, (0.15, 0.20, 0.07), d * -2.0))
            r *= 0.96
            for q in range(12):
                tt = rng.random()
                bp = (pos[0] + (nxt[0] - pos[0]) * tt, pos[1] + (nxt[1] - pos[1]) * tt)
                sa = a + rng.choice((-1, 1)) * rng.uniform(0.4, 1.3)
                sl = rng.uniform(0.012, 0.025)
                c = np.array(scol[rng.integers(len(scol))], F) * rng.uniform(0.8, 1.2)
                sp.segs.append((bp, (bp[0] + math.cos(sa) * sl, bp[1] + math.sin(sa) * sl), 1.6, 0.5, c, rng.uniform(-1, 3)))
            if rng.random() < 0.006:
                fa = a + rng.choice((-1, 1)) * rng.uniform(0.3, 1.0)
                for f in range(rng.integers(1, 3)):
                    fc = np.array((0.88, 0.66, 0.06), F) * rng.uniform(0.85, 1.1)
                    sp.leaves.append((nxt, fa + f * 0.5, 0.011, 0.008, fc, 8.0, 0.0))
            if d < 3 and rng.random() < 0.45:
                shoot(nxt, a + rng.choice((-1, 1)) * rng.uniform(0.35, 0.8), ln * (1 - (i / n)) * 0.7, r * 0.8, d + 1)
            pos = nxt

    for s in range(9):
        shoot((rng.normal(0, 0.01), 0.0), math.pi / 2 + rng.normal(0, 0.35), rng.uniform(0.3, 0.42), 4.0, 0)
    sp.fit(cv, (0, 0, res, res), margin=0.01)
    col, nrm, a = cv.finish(seed + 1, 0.2)
    return col, nrm, a


def tex_bramble(res=1024, seed=510):
    """2 cells side by side: arching cane segment with winter leaves (dark green/purple, some dead)."""
    rng = np.random.default_rng(seed)
    cv = Canvas(res, res, np.array((0.14, 0.10, 0.08), F))
    lcols = [(0.09, 0.14, 0.05), (0.12, 0.17, 0.06), (0.24, 0.08, 0.09), (0.30, 0.12, 0.08), (0.36, 0.22, 0.10),
             (0.08, 0.12, 0.05)]
    for k in range(2):
        sp = Spray(rng)
        pos, a = (0.0, 0.0), math.pi / 2 + rng.normal(0, 0.1)
        for i in range(10):
            a += rng.normal(0, 0.08)
            nxt = (pos[0] + math.cos(a) * 0.06, pos[1] + math.sin(a) * 0.06)
            sp.segs.append((pos, nxt, 3.6, 3.4, (0.28, 0.10, 0.12), 0.0))
            sp.dots.append(((pos[0] + 0.004, pos[1] + 0.02), 1.4, (0.55, 0.45, 0.35), 1.0))   # prickles
            if i % 2 == 1:
                side = 1 if (i // 2) % 2 == 0 else -1
                pa = a + side * 0.9
                pe = (nxt[0] + math.cos(pa) * 0.05, nxt[1] + math.sin(pa) * 0.05)
                sp.segs.append((nxt, pe, 1.6, 1.4, (0.25, 0.12, 0.10), 1.0))
                c = np.array(lcols[rng.integers(len(lcols))], F) * rng.uniform(0.85, 1.15)
                for j, off in enumerate((0.0, 0.9, -0.9, 1.7, -1.7)[: rng.choice((3, 5))]):
                    ln = 0.075 if j == 0 else 0.06
                    sp.leaves.append((pe, pa + off * 0.6, ln, ln * 0.6, c * rng.uniform(0.9, 1.1), 3.0 + j * 0.1, 0.22))
            pos = nxt
        sp.fit(cv, (k * res // 2, 0, res // 2, res), margin=0.02)
    col, nrm, a = cv.finish(seed + 1, 0.15)
    return col, nrm, a


def _frond(sp, rng, length, cols, droop=0.0, pinnae=18, rr=4.0, broken=0.0):
    """Fern frond: rachis with alternate pinnae of pinnules (abstract units)."""
    pos, a = (0.0, 0.0), math.pi / 2
    n = pinnae
    for i in range(n):
        t = (i + 1) / n
        a -= droop / n + rng.normal(0, 0.03)
        nxt = (pos[0] + math.cos(a) * length / n, pos[1] + math.sin(a) * length / n)
        sp.segs.append((pos, nxt, rr * (1 - 0.6 * t), rr * (1 - 0.6 * t), (0.30, 0.17, 0.07), 0.0))
        if t > 0.18 and rng.random() > broken:
            for side in (1, -1):
                pl = length * 0.42 * math.sin(math.pi * min(1.0, (t - 0.1) * 1.05)) ** 0.8 * rng.uniform(0.85, 1.1)
                pa = a + side * (1.05 + rng.normal(0, 0.1))
                ppos = nxt
                m = 7
                for j in range(m):
                    tj = (j + 1) / m
                    pa2 = pa - side * 0.05 * j
                    pn = (ppos[0] + math.cos(pa2) * pl / m, ppos[1] + math.sin(pa2) * pl / m)
                    sp.segs.append((ppos, pn, 1.3, 1.1, (0.28, 0.16, 0.07), 0.5))
                    c = np.array(cols[rng.integers(len(cols))], F) * rng.uniform(0.85, 1.15)
                    w = pl / m * 1.5 * (1 - 0.6 * tj)
                    for s2 in (1, -1):
                        sp.leaves.append((pn, pa2 + s2 * 1.1, w, w * 0.45, c, 1.0 + j * 0.01, 0.0))
                    ppos = pn
        pos = nxt


def tex_bracken(res=1024, seed=520):
    """2 cells: dead bracken fronds, rusty orange-brown."""
    rng = np.random.default_rng(seed)
    cv = Canvas(res, res, np.array((0.36, 0.20, 0.09), F))
    cols = [(0.46, 0.25, 0.10), (0.38, 0.20, 0.08), (0.52, 0.31, 0.13), (0.30, 0.17, 0.08), (0.42, 0.28, 0.14)]
    for k in range(2):
        sp = Spray(rng)
        _frond(sp, rng, 1.0, cols, droop=0.5 + 0.3 * k, pinnae=16, rr=3.5, broken=0.12)
        sp.fit(cv, (k * res // 2, 0, res // 2, res), margin=0.02)
    col, nrm, a = cv.finish(seed + 1, 0.15)
    return col, nrm, a


# --- GrassCard atlas (2048^2). Regions in UV space (u0, v0, u1, v1), v up.
GRASS_REGIONS = {
    "grass_a": (0.0, 0.5, 0.25, 1.0),
    "grass_b": (0.25, 0.5, 0.5, 1.0),
    "rush_a": (0.5, 0.5, 0.75, 1.0),
    "reed": (0.75, 0.0, 1.0, 1.0),
    "fern_a": (0.0, 0.0, 0.25, 0.5),
    "fern_b": (0.25, 0.0, 0.5, 0.5),
    "rush_b": (0.5, 0.0, 0.75, 0.5),
}


def tex_grasscards(res=2048, seed=600):
    rng = np.random.default_rng(seed)
    cv = Canvas(res, res, np.array((0.30, 0.26, 0.14), F))

    def cell(name):
        u0, v0, u1, v1 = GRASS_REGIONS[name]
        return (u0 * res, (1 - v1) * res, (u1 - u0) * res, (v1 - v0) * res)

    def blades(name, n, cols, wid, hmin, bend, seedheads=0.0):
        sp = Spray(rng)
        for b in range(n):
            x0 = rng.normal(0, 0.06)
            a = math.pi / 2 + rng.normal(0, 0.28) + x0 * 2
            ln = rng.uniform(hmin, 1.0)
            c = np.array(cols[rng.integers(len(cols))], F) * rng.uniform(0.8, 1.2)
            pos = (x0, 0.0)
            m = 10
            bd = rng.normal(0, bend)
            for i in range(m):
                t = (i + 1) / m
                a += bd / m
                nxt = (pos[0] + math.cos(a) * ln / m, pos[1] + math.sin(a) * ln / m)
                tip = c * (1 + 0.5 * t) if rng.random() < 0.5 else c
                sp.segs.append((pos, nxt, wid * (1 - 0.85 * (i / m)), wid * (1 - 0.85 * t), tip, rng.uniform(0, 4)))
                pos = nxt
            if seedheads and rng.random() < seedheads:
                for q in range(6):
                    sp.leaves.append((pos, a + rng.normal(0, 0.4), 0.05, 0.012, (0.50, 0.42, 0.28), 6.0, 0.0))
        sp.fit(cv, cell(name), margin=0.01)

    green_tan = [(0.32, 0.36, 0.15), (0.26, 0.31, 0.11), (0.48, 0.41, 0.23), (0.55, 0.48, 0.30), (0.40, 0.35, 0.18)]
    tan = [(0.52, 0.44, 0.27), (0.46, 0.38, 0.22), (0.60, 0.52, 0.34), (0.38, 0.33, 0.18), (0.30, 0.33, 0.14)]
    blades("grass_a", 70, green_tan, 4.5, 0.35, 0.9)
    blades("grass_b", 55, tan, 4.0, 0.45, 1.3, seedheads=0.2)
    rush = [(0.12, 0.18, 0.07), (0.15, 0.21, 0.08), (0.10, 0.15, 0.06), (0.20, 0.23, 0.10)]
    for nm in ("rush_a", "rush_b"):
        sp = Spray(rng)
        for b in range(45 if nm == "rush_a" else 35):
            x0 = rng.normal(0, 0.05)
            a = math.pi / 2 + rng.normal(0, 0.12) + x0 * 1.5
            ln = rng.uniform(0.55, 1.0)
            c = np.array(rush[rng.integers(len(rush))], F) * rng.uniform(0.85, 1.15)
            ep = (x0 + math.cos(a) * ln, math.sin(a) * ln)
            mid = ((x0 + ep[0]) / 2, ep[1] / 2)
            sp.segs.append(((x0, 0), mid, 5.0, 4.5, c, rng.uniform(0, 4)))
            dead = rng.random() < (0.25 if nm == "rush_a" else 0.5)
            sp.segs.append((mid, ep, 4.5, 1.0, c if not dead else np.array((0.42, 0.34, 0.18), F), rng.uniform(0, 4)))
            if rng.random() < 0.3:     # lateral flower cluster of soft rush
                fp = (x0 + (ep[0] - x0) * 0.72, ep[1] * 0.72)
                for q in range(7):
                    sp.leaves.append((fp, a + rng.choice((-1, 1)) * rng.uniform(0.2, 0.9), 0.035, 0.012,
                                      (0.36, 0.26, 0.13), 6.0, 0.0))
        sp.fit(cv, cell(nm), margin=0.01)
    # reeds (Phragmites): tall tan stems, alternate dead leaves, feathery plumes
    sp = Spray(rng)
    for b in range(9):
        x0 = rng.normal(0, 0.035)
        a = math.pi / 2 + rng.normal(0, 0.03)
        ln = rng.uniform(0.75, 1.0)
        pos = (x0, 0.0)
        m = 12
        for i in range(m):
            t = (i + 1) / m
            a += rng.normal(0, 0.01)
            nxt = (pos[0] + math.cos(a) * ln / m, pos[1] + math.sin(a) * ln / m)
            sp.segs.append((pos, nxt, 3.6 * (1 - 0.4 * t), 3.6 * (1 - 0.4 * t), (0.58, 0.50, 0.33), 0.0))
            if 0.15 < t < 0.8 and i % 2 == 0:
                la = a + (1 if i % 4 == 0 else -1) * rng.uniform(0.35, 0.7)
                sp.leaves.append((nxt, la, 0.16, 0.012, (0.55, 0.46, 0.30), 2.0, 0.0))
            pos = nxt
        if rng.random() < 0.8:      # plume
            pa = a + rng.normal(0, 0.25) - 0.3
            for q in range(60):
                tq = rng.random()
                bp = (pos[0] + math.cos(pa) * 0.15 * tq, pos[1] + math.sin(pa) * 0.15 * tq)
                fa = pa + rng.normal(0, 0.5) - 0.5
                fl = rng.uniform(0.02, 0.05)
                sp.segs.append((bp, (bp[0] + math.cos(fa) * fl, bp[1] + math.sin(fa) * fl), 1.3, 0.8,
                                np.array((0.50, 0.40, 0.33), F) * rng.uniform(0.8, 1.2), 3.0))
    sp.fit(cv, cell("reed"), margin=0.01)
    # dead ferns
    fcols = [(0.40, 0.22, 0.09), (0.33, 0.18, 0.08), (0.46, 0.28, 0.12), (0.28, 0.17, 0.08)]
    for nm, dr in (("fern_a", 0.9), ("fern_b", 1.4)):
        sp = Spray(rng)
        _frond(sp, rng, 1.0, fcols, droop=dr, pinnae=14, rr=3.0, broken=0.2)
        sp.fit(cv, cell(nm), margin=0.02)
    col, nrm, a = cv.finish(seed + 1, 0.15)
    return col, nrm, a


# ================================================================ ROCK etc.
def tex_rock(res=2048, seed=700):
    """Weathered natural granite (2 m tile): coarse crystals, grus pits, rich lichen."""
    X, Y = grid(res)
    px = 2.0 / res
    base = mix(rgb((0.36, 0.35, 0.33), X.shape), rgb((0.48, 0.46, 0.42), X.shape),
               sstep(-0.5, 0.5, fbm(X, Y, 4, 5, seed)))
    d = perlin(X, Y, 500, 500, seed + 1)
    l = perlin(X, Y, 420, 420, seed + 2)
    base = base * (1 - 0.6 * sstep(0.35, 0.55, d))[..., None] + 0.14 * sstep(0.4, 0.6, l)[..., None]
    feld = sstep(0.55, 0.7, perlin(X, Y, 180, 180, seed + 3))
    base = mix(base, rgb((0.58, 0.48, 0.42), X.shape), feld * 0.45)
    h = fbm(X, Y, 5, 6, seed + 4) * 0.012 + ridged(X, Y, 14, 4, seed + 5) * 0.004
    f1, _, _, _, _ = voronoi(X, Y, 90, 90, seed + 6, 0.95)
    pits = sstep(0.004, 0.001, f1) * sstep(0.2, 0.6, fbm(X, Y, 6, 3, seed + 7))
    h -= pits * 0.003
    streak = sstep(0.0, 0.7, fbm(X, Y, 3, 4, seed + 8, aniso=(4, 1)))
    base = mix(base, base * 0.5, streak * 0.4)
    ly = lichen_mask(X, Y, seed + 9, 0.12, 12)
    lg = lichen_mask(X, Y, seed + 10, 0.22, 9)
    lw = lichen_mask(X, Y, seed + 11, 0.18, 20)
    lb = lichen_mask(X, Y, seed + 12, 0.10, 26)
    alb = mix(base, rgb((0.50, 0.55, 0.42), X.shape), lg * 0.85)
    alb = mix(alb, rgb((0.66, 0.50, 0.14), X.shape), ly * 0.7)
    alb = mix(alb, rgb((0.72, 0.72, 0.68), X.shape), lw * 0.6)
    alb = mix(alb, rgb((0.08, 0.08, 0.07), X.shape), lb * 0.6)
    h = (h + (ly + lg + lw) * 0.0006).astype(F)
    rough = 0.8 + 0.1 * fbm(X, Y, 20, 3, seed + 13)
    ao = cavity_ao(h, px, (0.004, 0.015, 0.05), 1.3)
    alb = alb * (0.6 + 0.4 * ao)[..., None]
    return alb, height_to_normal(h, px, 1.0), orm(ao, rough)


def tex_moss(res=2048, seed=720):
    """Thick cushion moss with litter (2 m tile)."""
    X, Y = grid(res)
    px = 2.0 / res
    f1, f2, cid, _, _ = voronoi(X, Y, 60, 60, seed, 0.9)
    cush = np.sqrt(np.clip(1 - f1 * 60 * 1.1, 0, 1))
    fine = ridged(X, Y, 300, 3, seed + 1)
    h = cush * 0.012 + fine * 0.002 + fbm(X, Y, 6, 4, seed + 2) * 0.01
    rr = cell_rand(cid, seed + 3, 2)
    g = sstep(-0.5, 0.6, fbm(X, Y, 8, 4, seed + 4)) * 0.6 + rr[..., 0] * 0.4
    alb = mix(rgb((0.08, 0.14, 0.03), X.shape), rgb((0.22, 0.31, 0.06), X.shape), g)
    alb = mix(alb, rgb((0.33, 0.30, 0.12), X.shape), sstep(0.7, 0.95, rr[..., 1]) * 0.7)
    alb *= (0.6 + 0.5 * fine)[..., None]
    litter = sstep(0.55, 0.75, perlin(X, Y, 40, 40, seed + 5) * 0.5 + 0.5)
    alb = mix(alb, rgb((0.30, 0.18, 0.08), X.shape), litter * 0.6)
    h = h.astype(F)
    ao = cavity_ao(h, px, (0.003, 0.01, 0.03), 1.4)
    alb *= (0.55 + 0.45 * ao)[..., None]
    rough = np.full_like(h, 0.92)
    return alb, height_to_normal(h, px, 1.3), orm(ao, rough)


def tex_bank(res=2048, seed=740):
    """Talus bank earth: dark soil, oak-leaf litter, moss and roots (2 m tile)."""
    X, Y = grid(res)
    px = 2.0 / res
    h = fbm(X, Y, 6, 6, seed) * 0.01
    alb = mix(rgb((0.07, 0.05, 0.035), X.shape), rgb((0.16, 0.12, 0.08), X.shape), sstep(-0.4, 0.5, fbm(X, Y, 10, 4, seed + 1)))
    f1, f2, cid, cx, cy = voronoi(X, Y, 45, 45, seed + 2, 0.95)
    rr = cell_rand(cid, seed + 3, 4)
    ang = rr[..., 0] * np.pi
    dx, dy = X - cx, Y - cy
    u = (dx * np.cos(ang) + dy * np.sin(ang)) * 45
    v = (-dx * np.sin(ang) + dy * np.cos(ang)) * 45
    lobes = 0.22 + 0.06 * np.sin(u * 18)
    leaf = (np.abs(u) < 0.42) & (np.abs(v) < lobes * np.sqrt(np.clip(1 - (u / 0.42) ** 2, 0, 1))) & (rr[..., 1] < 0.75)
    lc = mix(rgb((0.26, 0.15, 0.07), X.shape), rgb((0.42, 0.27, 0.12), X.shape), rr[..., 2])
    alb = np.where(leaf[..., None], lc, alb)
    h = h + leaf * (0.002 + rr[..., 3] * 0.002)
    mm, mh, mc = _moss_layer(X, Y, seed + 4, 0.08)
    alb = mix(alb, mc, mm)
    h = h + mh * mm * 2
    # roots
    rt = sstep(0.975, 0.995, ridged(X, Y, 5, 2, seed + 5))
    alb = mix(alb, rgb((0.22, 0.16, 0.11), X.shape), rt)
    h = (h + rt * 0.004).astype(F)
    ao = cavity_ao(h, px, (0.003, 0.01, 0.03), 1.4)
    alb *= (0.55 + 0.45 * ao)[..., None]
    rough = np.where(leaf, 0.7, 0.9) * (1 - 0.1 * mm)
    return alb, height_to_normal(h, px, 1.2), orm(ao, rough)


def tex_stem(res=512, seed=760):
    """Generic smooth stem/cane bark (hazel, bramble canes, pollard poles). 0.5 m tile."""
    X, Y = grid(res)
    px = 0.5 / res
    h = 0.0004 * fbm(X, Y, 8, 4, seed, aniso=(1, 4))
    lent = sstep(0.7, 0.85, perlin(X, Y, 40, 20, seed + 1) * 0.5 + 0.5)
    L = 0.85 + 0.15 * fbm(X, Y, 6, 3, seed + 2)
    alb = (L[..., None] * np.ones(3, F)) * (1 - 0.3 * lent[..., None])
    alb = np.clip(alb + lent[..., None] * np.array((0.15, 0.13, 0.10), F), 0, 1)
    h = (h + lent * 0.0003).astype(F)
    ao = cavity_ao(h, px, (0.002, 0.006), 1.0)
    return alb, height_to_normal(h, px, 1.0), orm(ao, np.full_like(h, 0.6))


# ================================================================ ensure
def _all():
    jobs = {}
    for sp, fn in BARKS.items():
        jobs[f"bark_{sp}"] = (lambda fn=fn: fn(moss=0.0))
        jobs[f"bark_{sp}_moss"] = (lambda fn=fn, sp=sp: fn(moss=0.55 + MOSS_COVER[sp]))
    for sp in TWIG_SPECIES:
        jobs[f"twig_{sp}"] = (lambda sp=sp: tex_twigs(sp))
    jobs.update({"twig_pine": tex_pine, "gorse": tex_gorse, "bramble": tex_bramble, "bracken": tex_bracken,
                 "grasscards": tex_grasscards, "rock": tex_rock, "moss": tex_moss, "bank": tex_bank, "stem": tex_stem})
    return jobs


CARD_TEX = {"twig_oak", "twig_beech", "twig_chestnut", "twig_ash", "twig_hazel", "twig_blackthorn", "twig_pine",
            "gorse", "bramble", "bracken", "grasscards"}


def ensure(names=None, force=False, log=print):
    jobs = _all()
    for n in names or list(jobs):
        if not force and os.path.exists(os.path.join(TEX_DIR, f"{n}_albedo.png")):
            continue
        t0 = time.time()
        out = jobs[n]()
        if n in CARD_TEX:
            col, nrm, a = out
            save(n, col, nrm, None, alpha=a)
        else:
            save(n, *out)
        log(f"[tex] {n}: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ensure(args or None, force="--force" in sys.argv)
