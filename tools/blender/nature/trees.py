"""Winter trees: oak, beech, sweet chestnut, ash (leafless) and maritime pine (evergreen).

A recursive skeleton (trunk -> limbs -> branches -> branchlets) is grown inside a lobed crown
envelope and meshed as tapered tubes with bark (plus a mossy bark variant on the trunk's north
side and on the tops of big limbs). The fine twigs are alpha-cut cards (material 'TwigCard') hung
on the outer branchlets, each card carrying a drawn twig spray (ntex.tex_twigs / tex_pine).
"""
import math

import numpy as np
from mathutils import Matrix, Vector, noise

import nlib
from nlib import MB, card, mat, tube

UP = Vector((0, 0, 1))


class Br:
    __slots__ = ("pts", "radii", "order", "dead", "kids")

    def __init__(self, pts, radii, order, dead=False):
        self.pts, self.radii, self.order, self.dead, self.kids = pts, radii, order, dead, []

    def at(self, t):
        f = t * (len(self.pts) - 1)
        i = min(int(f), len(self.pts) - 2)
        k = f - i
        p = self.pts[i].lerp(self.pts[i + 1], k)
        r = self.radii[i] + (self.radii[i + 1] - self.radii[i]) * k
        d = (self.pts[i + 1] - self.pts[i]).normalized()
        return p, r, d

    def length(self):
        return sum((self.pts[i + 1] - self.pts[i]).length for i in range(len(self.pts) - 1))


def rand_unit(rng):
    v = Vector(rng.normal(0, 1, 3))
    return v.normalized() if v.length > 1e-6 else Vector((1, 0, 0))


def perp(d, roll):
    ref = UP if abs(d.z) < 0.95 else Vector((1, 0, 0))
    a = d.cross(ref).normalized()
    b = d.cross(a).normalized()
    return (a * math.cos(roll) + b * math.sin(roll)).normalized()


class Tree:
    def __init__(self, P, seed):
        self.P = P
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.branches = []

    # ---------------------------------------------------------- envelope
    def env(self, p):
        """<0 inside crown envelope (lobed ellipsoid)."""
        P = self.P
        c = Vector(P["env_c"]) + getattr(self, "off", Vector())
        r = Vector(P["env_r"])
        q = p - c
        d = q.normalized() if q.length > 1e-6 else UP
        lobe = 1.0 + P.get("env_lobe", 0.22) * noise.noise(d * 1.7 + Vector((self.seed * 0.37, 0, 0)))
        e = (q.x / (r.x * lobe)) ** 2 + (q.y / (r.y * lobe)) ** 2 + (q.z / (r.z * lobe)) ** 2
        return e - 1.0

    def ray(self, p, d, maxd=30.0):
        """Distance from p along d to the envelope surface."""
        if self.env(p) > 0:
            return 0.0
        t = 0.0
        while t < maxd:
            t += 0.3
            if self.env(p + d * t) > 0:
                return t
        return maxd

    # ------------------------------------------------------------- growth
    def grow(self, start, d, length, r0, order, dead=False):
        P, rng = self.P, self.rng
        if not hasattr(self, "off"):
            self.off = Vector()
        o = min(order, len(P["seg"]) - 1)
        seg = P["seg"][o]
        n = max(2, int(math.ceil(length / seg)))
        step = length / n
        pts = [Vector(start)]
        d = Vector(d).normalized()
        wob = P["wobble"][o]
        trop = P["trop"][o]
        for i in range(n):
            t = (i + 1) / n
            tr = trop if not callable(trop) else trop(t)
            jit = rand_unit(rng) * wob
            d = (d + jit + UP * tr).normalized()
            if P.get("wind") is not None and order >= 1:
                d = (d + Vector(P["wind"]) * 0.04).normalized()
            p = pts[-1] + d * step
            if order >= 1 and i >= 1:
                e = self.env(p)
                if e > P.get("env_soft", 0.15) + 0.35:
                    break
                if e > 0.0:     # bend back toward the crown centre instead of a hard cut
                    c = Vector(P["env_c"]) + self.off
                    d = (d + (c - p).normalized() * 0.35 * min(1.0, e * 3)).normalized()
                    p = pts[-1] + d * step
            if p.z - getattr(self, "off", Vector()).z < 0.4 and order >= 1:
                d.z = abs(d.z) + 0.2
                d.normalize()
                p = pts[-1] + d * step
            pts.append(p)
        tip = P["tip"][o]
        m = len(pts)
        Lfrac = (m - 1) / n
        radii = [r0 * (1 - (1 - tip) * (k / (m - 1)) * Lfrac) for k in range(m)]
        b = Br(pts, radii, order, dead)
        self.branches.append(b)
        if order >= P["maxorder"]:
            return b
        # children
        nch = P["nkids"][o]
        L = b.length()
        nch = int(round(nch * min(1.5, max(0.65, L / max(P["lmean"][o], 0.1)))))
        t0, t1 = P["kid_t"][o]
        roll = rng.uniform(0, 2 * math.pi)
        ts = np.sort(rng.uniform(t0, t1, nch)) if nch else []
        for t in ts:
            roll += P.get("phyllo", 2.4) + rng.normal(0, 0.3)
            p, r, pd = b.at(float(t))
            ang = math.radians(P["angle"][o] + rng.normal(0, P.get("angle_sd", 12)))
            side = perp(pd, roll)
            cd = (pd * math.cos(ang) + side * math.sin(ang)).normalized()
            if P.get("outward", 0) and order == 0:
                pass
            # child length: fraction of parent, shaped along the parent, clipped by envelope
            shape = P["kid_shape"](float(t)) if "kid_shape" in P else (1.0 - 0.5 * float(t))
            cl = L * P["lratio"][o] * shape * rng.uniform(0.75, 1.2)
            if order >= 0 and o + 1 <= P["maxorder"]:
                cl = min(cl, self.ray(p, cd) * rng.uniform(0.95, 1.12) + 0.3)
            cl = max(cl, P["lmin"][o])
            cr = min(r * P["rratio"][o] * rng.uniform(0.85, 1.1), r * 0.9)
            if cr < P.get("rmin", 0.0035):
                continue
            kdead = dead or (rng.random() < P.get("dead_p", [0] * 5)[o] and p.z > P.get("dead_z", 0))
            if kdead and not dead:
                cl *= 0.7
            kid = self.grow(p - pd * r * 0.5, cd, cl, cr, order + 1, kdead)
            b.kids.append(kid)
        return b

    # --------------------------------------------------------------- mesh
    def build(self, name, species, names=("Bark", "BarkMoss", "TwigCard"), twig_tex=None, bark_tex=None,
              collide=True, offset=(0, 0, 0)):
        P, rng = self.P, self.rng
        off = Vector(offset)
        self.off = off
        trunk_d = Vector(P.get("trunk_dir", (0, 0, 1))).normalized()
        self.grow(off + Vector((0, 0, P.get("z0", -0.35))), trunk_d, P["trunk_len"], P["trunk_r"], 0)
        bt = bark_tex or f"bark_{species}"
        bark = mat(names[0], bt, tint=P.get("bark_tint"))
        bmoss = mat(names[1], f"{bt}_moss", tint=P.get("bark_tint"))
        twig = mat(names[2], twig_tex or f"twig_{species}", alpha=True)
        bark_mb, card_mb = MB(), MB()
        north = Vector((0.25, 1.0, 0.0)).normalized()
        sd = self.seed * 1.37

        nflare = P.get("roots", 6)
        phase = rng.uniform(0, 6.28)
        burl = P.get("burl", 0.0)

        def trunk_r(i, j, a, p):
            z = max(p.z - off.z, 0.0)
            fl = P.get("flare", 0.4) * math.exp(-z / 0.7)
            lobe = max(0.0, math.cos(nflare * a + phase + noise.noise(Vector((a, 0, 3))) * 1.5)) ** 2
            m = 1.0 + fl * (0.35 + 0.65 * lobe)
            if burl:
                m += burl * max(0.0, noise.noise(p * 1.8 + Vector((sd, 0, 0))) - 0.2) * 1.6
            m += 0.05 * noise.noise(p * 3.0 + Vector((0, sd, 0)))
            return m

        def gnarl_r(i, j, a, p):
            return 1.0 + 0.08 * noise.noise(p * 2.5 + Vector((sd, sd, 0))) + (
                burl * 0.6 * max(0.0, noise.noise(p * 1.5) - 0.3))

        stats = {"tubes": 0, "cards": 0}
        for b in self.branches:
            r0 = b.radii[0]
            segs = 18 if r0 >= 0.35 else 14 if r0 >= 0.18 else 10 if r0 >= 0.09 else 7 if r0 >= 0.045 else 5 if r0 >= 0.02 else 4
            if b.order == 0:
                segs = P.get("trunk_segs", 20)
            pts = b.pts
            radii = b.radii
            if b.order <= 1:
                def mfn(i, j, p, fr, segs=segs, b=b):
                    t, n, bn = fr
                    a = 2 * math.pi * (j + 0.5) / segs
                    nv = n * math.cos(a) + bn * math.sin(a)
                    s = 0.55 * nv.dot(north) + 0.45 * nv.z + 0.5 * noise.noise(p * 0.8 + Vector((sd, 2, 0)))
                    if b.order == 0:
                        s += 0.5 * math.exp(-max(p.z, 0) / 1.2)
                    return bmoss if s > P.get("moss_thr", 0.42) else bark
            else:
                mfn = None
            rf = trunk_r if b.order == 0 else (gnarl_r if b.order == 1 else None)
            tube(bark_mb, pts, radii, bark, segs, tile=1.0, rfun=rf, material_fn=mfn, cap=(b.order >= 1 and b.dead))
        # ----- twig cards
        cells = [(0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0), (0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 1.0, 0.5)]
        cell_w = P.get("cell_w", [0.34, 0.33, 0.33, 0.0])
        cw = np.cumsum(cell_w) / np.sum(cell_w)
        maxo = P["maxorder"]
        for b in self.branches:
            if b.dead:
                continue
            terminal = b.order == maxo or (b.order >= maxo - 1 and not b.kids)
            outer = b.order == maxo - 1
            if not (terminal or outer):
                continue
            L = b.length()
            step = P["card_step"] * (1.0 if terminal else 1.8)
            tstart = 0.25 if terminal else 0.55
            ts = list(np.arange(tstart, 1.0, step / max(L, 0.1))) + ([1.0] if terminal else [])
            for t in ts:
                p, r, d = b.at(min(float(t), 0.999))
                if float(t) >= 0.999:
                    p = b.pts[-1]
                ncross = P.get("cross", 1)
                tip = float(t) >= 0.999
                base_roll = rng.uniform(0, 6.28)
                for c in range(ncross):
                    roll = base_roll + c * math.pi / ncross
                    if tip:
                        ang = math.radians(rng.uniform(0, 15))
                    else:
                        ang = math.radians(rng.uniform(*P.get("card_ang", (25, 60))))
                    sdir = perp(d, rng.uniform(0, 6.28))
                    upv = (d * math.cos(ang) + sdir * math.sin(ang)).normalized()
                    upv = (upv + UP * P.get("card_trop", 0.0)).normalized()
                    side = perp(upv, roll)
                    sz = P["card_size"] * rng.uniform(0.75, 1.2) * (1.0 if terminal else 0.85)
                    k = int(np.searchsorted(cw, rng.random()))
                    card(card_mb, p - upv * 0.03, upv, side, sz, sz, cells[min(k, 3)], twig,
                         bend=sz * P.get("card_droop", 0.1), segs=1 if P.get("card_droop", 0.1) < 0.12 else 2)
                    stats["cards"] += 1
        stats["tubes"] = bark_mb.tris()
        ob_b = bark_mb.build(f"{name}_wood")
        ob_c = card_mb.build(f"{name}_twigs")
        # collision: convex hull of the lower trunk
        trunk = self.branches[0]
        hull = []
        for k in range(len(trunk.pts)):
            p = trunk.pts[k]
            if p.z - off.z > P.get("col_h", 3.5):
                break
            r = trunk.radii[k] * (1.15 if p.z < 0.5 else 1.0)
            for j in range(8):
                a = j * math.pi / 4
                hull.append((p.x + math.cos(a) * r, p.y + math.sin(a) * r, max(p.z, 0.0)))
        col = nlib.col_hull(P.get("col_name", "Trunk"), hull) if collide else None
        stats["cards_tris"] = card_mb.tris()
        stats["dims"] = tuple(round(v, 1) for v in ob_b.dimensions)
        stats["n_by_order"] = [sum(1 for b in self.branches if b.order == o) for o in range(5)]
        return [ob_b, ob_c], ([col] if col else []), stats


# ====================================================================== species
def _oak_a():
    """Broad field oak: short massive trunk, wide elbowed limbs, crown wider than tall."""
    return dict(
        trunk_len=8.0, trunk_r=0.6, trunk_dir=(0.03, 0.02, 1), flare=0.55, roots=6, burl=0.05,
        env_c=(0, 0, 9.4), env_r=(11.0, 10.0, 6.4), env_lobe=0.25,
        maxorder=3, seg=[0.45, 0.4, 0.35, 0.45], wobble=[0.06, 0.28, 0.3, 0.3], trop=[0.0, 0.05, 0.03, 0.05],
        tip=[0.3, 0.12, 0.28, 0.3], nkids=[8, 13, 9], lmean=[7.5, 7.0, 3.0], kid_t=[(0.4, 1.0), (0.12, 1.0), (0.1, 1.0)],
        angle=[64, 48, 52], lratio=[1.15, 0.45, 0.5], lmin=[4.0, 1.2, 0.6], rratio=[0.62, 0.42, 0.5],
        kid_shape=lambda t: 1.0 - 0.45 * t,
        card_size=1.45, card_step=0.36, card_ang=(25, 65), card_trop=0.15, cross=1, card_droop=0.05,
        cell_w=[0.34, 0.33, 0.33, 0.0], col_h=3.5)


def _oak_b():
    """Gnarled hedgerow oak: leaning burred trunk, contorted limbs, dead stag-head tops."""
    P = _oak_a()
    P.update(trunk_len=5.0, trunk_r=0.52, trunk_dir=(0.18, 0.05, 1), burl=0.2, flare=0.6,
             env_c=(1.2, 0, 7.0), env_r=(6.8, 6.0, 4.6), env_lobe=0.35,
             wobble=[0.12, 0.42, 0.4, 0.35], nkids=[7, 12, 10], lmean=[5.0, 4.5, 2.2],
             lratio=[1.2, 0.5, 0.5], lmin=[3.2, 1.4, 0.7], angle=[52, 52, 55],
             dead_p=[0.2, 0.12, 0.0], dead_z=7.0, card_size=1.3, cell_w=[0.33, 0.33, 0.29, 0.05], col_h=3.0)
    return P


def _beech_a():
    """Tall woodland beech: smooth grey bole, ascending co-dominant stems, fine dense spray."""
    return dict(
        trunk_len=8.0, trunk_r=0.42, trunk_dir=(0.0, 0.02, 1), flare=0.45, roots=5, burl=0.0,
        env_c=(0, 0, 11.0), env_r=(7.0, 7.0, 7.4), env_lobe=0.2,
        maxorder=3, seg=[0.5, 0.45, 0.35, 0.45], wobble=[0.03, 0.08, 0.14, 0.16],
        trop=[0.0, 0.04, 0.0, -0.03], tip=[0.35, 0.12, 0.28, 0.3], nkids=[6, 15, 12], lmean=[8.0, 7.0, 2.5],
        kid_t=[(0.55, 1.0), (0.12, 1.0), (0.1, 1.0)], angle=[34, 52, 50], lratio=[1.25, 0.45, 0.5],
        lmin=[6.0, 2.0, 0.8], rratio=[0.66, 0.4, 0.5], kid_shape=lambda t: 1.0 - 0.5 * t,
        card_size=1.4, card_step=0.36, card_ang=(25, 55), card_trop=0.0, card_droop=0.2, cross=1,
        cell_w=[0.34, 0.34, 0.31, 0.01], moss_thr=0.6, col_h=3.5)


def _beech_b():
    """Open-grown beech: low branching, broad dome."""
    P = _beech_a()
    P.update(trunk_len=5.0, trunk_r=0.46, env_c=(0, 0, 8.4), env_r=(8.0, 7.6, 6.6),
             kid_t=[(0.4, 1.0), (0.12, 1.0), (0.1, 1.0)], angle=[48, 52, 50], nkids=[7, 14, 12],
             lmean=[7.0, 6.0, 2.5], lratio=[1.3, 0.45, 0.5], lmin=[5.5, 1.8, 0.8], cell_w=[0.34, 0.34, 0.31, 0.01])
    return P


def _chestnut():
    """Sweet chestnut: stout spiral-barked bole, big ascending limbs, stout twigs."""
    return dict(
        trunk_len=6.0, trunk_r=0.58, trunk_dir=(-0.02, 0.04, 1), flare=0.5, roots=5, burl=0.1,
        env_c=(0, 0, 9.0), env_r=(8.0, 7.6, 6.0), env_lobe=0.25,
        maxorder=3, seg=[0.45, 0.4, 0.35, 0.45], wobble=[0.05, 0.16, 0.2, 0.2], trop=[0.0, 0.04, 0.02, 0.03],
        tip=[0.3, 0.12, 0.28, 0.3], nkids=[7, 13, 10], lmean=[6.0, 6.5, 2.8], kid_t=[(0.5, 1.0), (0.12, 1.0), (0.1, 1.0)],
        angle=[42, 50, 50], lratio=[1.2, 0.45, 0.5], lmin=[5.0, 1.8, 0.8], rratio=[0.62, 0.42, 0.5],
        kid_shape=lambda t: 1.0 - 0.45 * t,
        card_size=1.35, card_step=0.4, card_ang=(25, 60), card_trop=0.1, card_droop=0.05, cross=1,
        cell_w=[0.34, 0.33, 0.33, 0.0], col_h=3.5)


def _ash():
    """Ash: tall straight leader, ascending limbs curving up at the tips, sparse stout twigs."""
    return dict(
        trunk_len=13.0, trunk_r=0.38, trunk_dir=(0.02, -0.02, 1), flare=0.4, roots=5, burl=0.0,
        env_c=(0, 0, 10.5), env_r=(6.5, 6.5, 6.8), env_lobe=0.2,
        maxorder=3, seg=[0.5, 0.45, 0.35, 0.45], wobble=[0.03, 0.1, 0.14, 0.12],
        trop=[0.0, 0.07, 0.1, 0.12], tip=[0.12, 0.12, 0.28, 0.3], nkids=[12, 11, 8], lmean=[13.0, 5.0, 2.5],
        kid_t=[(0.4, 0.95), (0.12, 1.0), (0.15, 1.0)], angle=[52, 45, 42], lratio=[0.5, 0.48, 0.5],
        lmin=[3.5, 1.6, 0.8], rratio=[0.5, 0.42, 0.5], kid_shape=lambda t: 1.15 - 0.7 * t, phyllo=1.9,
        card_size=1.15, card_step=0.75, card_ang=(15, 45), card_trop=0.35, card_droop=0.0, cross=1,
        cell_w=[0.34, 0.33, 0.33, 0.0], col_h=3.5)


def _pine_a():
    """Maritime pine: tall bare bole, flattened irregular crown of upturned needle tufts."""
    return dict(
        trunk_len=16.0, trunk_r=0.36, trunk_dir=(0.06, 0.02, 1), flare=0.3, roots=4, burl=0.0,
        env_c=(0.6, 0, 14.4), env_r=(6.2, 5.8, 3.4), env_lobe=0.35,
        maxorder=3, seg=[0.5, 0.4, 0.3, 0.45], wobble=[0.05, 0.14, 0.16, 0.14],
        trop=[0.0, 0.07, 0.1, 0.12], tip=[0.08, 0.15, 0.28, 0.3], nkids=[17, 10, 7], lmean=[16.0, 4.0, 1.6],
        kid_t=[(0.66, 0.97), (0.2, 1.0), (0.2, 1.0)], angle=[78, 42, 40], lratio=[0.3, 0.5, 0.55],
        lmin=[3.0, 1.2, 0.6], rratio=[0.4, 0.5, 0.55], kid_shape=lambda t: 1.3 - 0.9 * t, phyllo=2.4,
        card_size=0.8, card_step=0.2, card_ang=(10, 35), card_trop=0.45, card_droop=0.0, cross=3,
        cell_w=[0.25, 0.25, 0.25, 0.25], moss_thr=0.7, col_h=4.0, trunk_segs=16)


def _pine_b():
    """Wind-bent coastal maritime pine, crown thrown downwind (+X)."""
    P = _pine_a()
    P.update(trunk_len=11.5, trunk_r=0.32, trunk_dir=(0.32, 0.05, 1), env_c=(3.0, 0.3, 9.6),
             env_r=(5.4, 4.2, 2.8), wind=(1.0, 0.1, 0.0), wobble=[0.07, 0.18, 0.18, 0.14],
             kid_t=[(0.55, 0.97), (0.2, 1.0), (0.2, 1.0)], nkids=[13, 9, 7], lmean=[11.0, 4.0, 1.6],
             lratio=[0.36, 0.5, 0.55], col_h=3.0)
    return P


SPECIES = {
    "tree_oak_a": ("oak", _oak_a, 11),
    "tree_oak_b": ("oak", _oak_b, 23),
    "tree_beech_a": ("beech", _beech_a, 31),
    "tree_beech_b": ("beech", _beech_b, 47),
    "tree_chestnut_a": ("chestnut", _chestnut, 53),
    "tree_ash_a": ("ash", _ash, 61),
    "tree_pine_a": ("pine", _pine_a, 71),
    "tree_pine_b": ("pine", _pine_b, 83),
}


def build(name):
    species, fn, seed = SPECIES[name]
    t = Tree(fn(), seed)
    vis, cols, stats = t.build(name, species)
    h = stats["dims"][2]
    pv = [dict(elev=3.0, azim=-30.0, dist_mul=0.72, sun_elev=5.0, target=(0, 0, h * 0.5)),
          dict(suffix="_bark", elev=8.0, azim=-20.0, dist_mul=0.09, target=(0, 0, 1.6), sun_elev=12.0, fill=0.6)]
    return vis, cols, stats, pv
