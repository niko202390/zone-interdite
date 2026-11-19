"""Soldier geometry: M40 greatcoat, M35 helmet, leather equipment, field kit, boots, gloves, head.

Every part is a separate mesh object tagged with a skinning rule (ob["skin"]); build_soldier.py
weights them on the armature and joins them into one skinned mesh. Coordinates: metres, Z up,
facing -Y, the man's left = +X, standing on the origin.
"""
import math
from math import asin, atan2, cos, exp, pi, radians, sin, sqrt

import bmesh
import bpy
from mathutils import Matrix, Vector

import crig
from cgeo import (Mesh, Surface, V, catmull, ellipsoid, frames_along, interp_table, lathe, lerp, orient_outward,
                  merge_by_distance, resample, rounded_box, solidify, sstep, strap, superellipse_pt, torus)

PARTS = []


def part(ob, skin, **kw):
    ob["skin"] = skin
    for k, v in kw.items():
        ob[k] = v
    PARTS.append(ob)
    return ob


# ===================================================================================== greatcoat
#        z      a      bf     bb     yc      n
TORSO = [(1.030, 0.168, 0.128, 0.120, 0.000, 2.6),
         (1.100, 0.168, 0.131, 0.121, 0.000, 2.6),
         (1.180, 0.172, 0.137, 0.124, -0.002, 2.6),
         (1.260, 0.178, 0.144, 0.128, -0.004, 2.5),
         (1.330, 0.180, 0.146, 0.131, -0.004, 2.5),
         (1.390, 0.180, 0.140, 0.133, -0.002, 2.6),
         (1.425, 0.181, 0.124, 0.124, 0.002, 2.8),
         (1.452, 0.172, 0.104, 0.106, 0.004, 2.8),
         (1.474, 0.148, 0.090, 0.094, 0.004, 2.6),
         (1.490, 0.112, 0.078, 0.080, 0.002, 2.3),
         (1.502, 0.082, 0.070, 0.068, 0.000, 2.1),
         (1.508, 0.074, 0.065, 0.061, 0.000, 2.0)]

SKIRT = [(0.360, 0.252, 0.200, 0.192, 0.000, 2.3),
         (0.520, 0.242, 0.190, 0.182, 0.000, 2.3),
         (0.660, 0.229, 0.177, 0.170, 0.004, 2.3),
         (0.780, 0.215, 0.163, 0.160, 0.006, 2.4),
         (0.880, 0.203, 0.150, 0.152, 0.006, 2.4),
         (0.960, 0.190, 0.140, 0.141, 0.004, 2.5),
         (1.020, 0.176, 0.133, 0.126, 0.000, 2.6),
         (1.078, 0.171, 0.132, 0.122, 0.000, 2.6)]
HEM_Z = 0.360
FLAP_OUT = 0.0045


def edge_x(z):
    """x of the outer (left-over-right) front edge of the double-breasted coat."""
    return -(0.070 + max(0.0, z - 1.03) * 0.10)


def theta_for_x(x, a, n):
    return asin(min(0.97, (abs(x) / a) ** (n / 2.0)))


def sec_point(sec, th, z, extra=0.0):
    a, bf, bb, yc, n = sec
    x, y = superellipse_pt(th, a, a, bf, bb, n)
    r = sqrt(x * x + y * y) or 1.0
    k = (r + extra) / r
    return V(x * k, yc + y * k, z)


def folds(th, z, amp):
    return amp * sin(13 * th + 0.7 * sin(3 * th) + 2.2 * z)


def build_torso(mats):
    m = Mesh("coat_torso")
    rings = []
    zs = [1.030 + i * 0.02 for i in range(24)] + [1.508]
    N = 84
    eds = []
    for z in zs:
        sec = interp_table(TORSO, z)
        a, n = sec[0], sec[4]
        the = theta_for_x(edge_x(z), a, n)
        ths = [-the + 2 * pi * i / N for i in range(N)] + [2 * pi - the - 0.004]
        ring, ed = [], []
        for k, th in enumerate(ths):
            u = th + the            # 0 at the edge
            out = FLAP_OUT * (1 - sstep(1.0, 1.9, u)) if k < N else 0.0
            if k == 0:
                out = FLAP_OUT
            blouse = 0.004 * sin(18 * th + 1.3) * sstep(1.13, 1.04, z)
            ring.append(sec_point(sec, th, z, out + blouse))
            ed.append(u * a if u < 0.6 else 1.0)
        rings.append(ring)
        eds.append(ed)
    m.grid(rings, 'wool_coat', closed=True, attrs=lambda j, i: {"edge_d": eds[j][i]})
    ob = m.to_object()
    return part(ob, "torso")


def build_skirt(mats):
    m = Mesh("coat_skirt")
    N = 100
    zs = [HEM_Z + (1.078 - HEM_Z) * (i / 27) ** 1.0 for i in range(28)]
    rings, attrs = [], []
    for z in zs:
        sec = interp_table(SKIRT, z)
        a, n = sec[0], sec[4]
        the = theta_for_x(edge_x(min(z, 1.03)) * (1.0 + (1.03 - min(z, 1.03)) * 0.25), a, n)
        thu = theta_for_x(0.075, a, n)
        t0, t1 = -the, 2 * pi + thu
        ring, at = [], []
        amp = 0.011 * sstep(0.97, 0.55, z)
        for i in range(N):
            th = t0 + (t1 - t0) * i / (N - 1)
            u = th - t0
            out = FLAP_OUT * (1 - sstep(1.0, 1.9, u))
            inn = -0.0075 * sstep(2 * pi - the - 0.5, 2 * pi - the - 0.1, th)
            vent = -0.007 * exp(-((th - pi) / 0.05) ** 2) * sstep(0.97, 0.86, z)
            ring.append(sec_point(sec, th, z, out + inn + folds(th, z, amp) + vent))
            ed = min(z - HEM_Z, u * a, (t1 - th) * a)
            at.append({"edge_d": ed, "sk_th": math.degrees(th)})
        rings.append(ring)
        attrs.append(at)
    m.grid(rings, 'wool_coat', closed=False, attrs=lambda j, i: attrs[j][i])
    ob = m.to_object(recalc=False)
    orient_outward(ob)
    ob.data.materials.append(bpy.data.materials["wool_coat_in"])
    solidify(ob, 0.006, offset=-1.0, inner_mat_offset=1)
    return part(ob, "skirt")


def build_collar(mats, surf):
    m = Mesh("coat_collar")
    thc = 0.30
    N = 60
    rings_by_prof = []
    eds = []
    neck = interp_table(TORSO, 1.505)
    for i in range(N):
        th = thc + (2 * pi - 2 * thc) * i / (N - 1)
        tw = min(th, 2 * pi - th)          # 0 at front, pi at back
        back = sstep(1.2, 2.6, tw)
        front = 1.0 - sstep(0.30, 1.1, tw)
        p0 = sec_point(neck, th, 1.500, 0.003)
        c = V(0, neck[3], 0)
        r = (V(p0.x, p0.y, 0) - c)
        r.normalize()
        stand = 0.040 + 0.014 * back - 0.012 * front
        fall = 0.062 + 0.010 * back + 0.030 * front
        pts = [p0,
               p0 + r * 0.005 + V(0, 0, stand * 0.6),
               p0 + r * 0.008 + V(0, 0, stand),
               p0 + r * 0.020 + V(0, 0, stand + 0.006),
               p0 + r * 0.032 + V(0, 0, stand - 0.004)]
        top = pts[-1]
        for k, f in enumerate((0.35, 0.68, 1.0)):
            q = top + r * (fall * f * 0.85) + V(0, 0, -fall * f * 0.9 - 0.012 * front * f)
            q, nn = surf.project(q, 0.0055 + 0.002 * (1 - f))
            pts.append(q)
        L = [0.0]
        for k in range(1, len(pts)):
            L.append(L[-1] + (pts[k] - pts[k - 1]).length)
        rings_by_prof.append(pts)
        eds.append([min(L[-1] - x, abs(i - 0) * 0.01 + 1, abs(N - 1 - i) * 0.01 + 1) for x in L])
    # rows = profile index, columns = around
    rows = [[rings_by_prof[i][k] for i in range(N)] for k in range(len(rings_by_prof[0]))]
    m.grid(rows, 'wool_coat', closed=False, attrs=lambda j, i: {"edge_d": eds[i][j]})
    ob = m.to_object(recalc=False)
    orient_outward(ob)
    ob.data.materials.append(bpy.data.materials["wool_coat_in"])
    solidify(ob, 0.004, offset=-1.0, inner_mat_offset=1)
    return part(ob, "copy")


def build_sleeves(mats):
    J = crig.joints()
    obs = []
    for side, s in (("L", 1), ("R", -1)):
        sh, el, wr = J['sh' + side], J['el' + side], J['wr' + side]
        d_ua, d_fa, palm = crig.arm_dirs(side)
        start = V(0.125 * s, 0.004, 1.447)
        ctrl = [start, sh + V(0.004 * s, 0, 0.004), sh.lerp(el, 0.5), el, el.lerp(wr, 0.5), wr + d_fa * 0.012]
        path = resample(catmull(ctrl, 6), 0.014)
        L = [0.0]
        for k in range(1, len(path)):
            L.append(L[-1] + (path[k] - path[k - 1]).length)
        Lt = L[-1]
        cuff0 = Lt - 0.095
        Ls_j = (sh - start).length
        L_el = Ls_j + UA()
        prof = [(0.0, 0.050), (Ls_j, 0.066), (Ls_j + 0.07, 0.064), (Ls_j + 0.16, 0.059), (L_el, 0.056),
                (L_el + 0.10, 0.054), (cuff0 - 0.003, 0.051), (cuff0, 0.0575), (Lt, 0.0565)]

        def rad(l):
            for q in range(len(prof) - 1):
                if prof[q][0] <= l <= prof[q + 1][0]:
                    t = (l - prof[q][0]) / max(1e-6, prof[q + 1][0] - prof[q][0])
                    return lerp(prof[q][1], prof[q + 1][1], t)
            return prof[-1][1]
        # insert exact rings at the cuff step
        fr = frames_along(path, V(0, -1, 0))
        n_around = 30
        rings, eds = [], []
        for k, (p, (T, Nn, B)) in enumerate(zip(path, fr)):
            l = L[k]
            r = rad(l)
            if abs(l - cuff0) < 0.008:
                r = rad(cuff0 - 0.004) if l < cuff0 else 0.0575
            elbow_k = exp(-((l - L_el) / 0.05) ** 2)
            ring = []
            for i in range(n_around):
                th = 2 * pi * i / n_around
                # elbow creases on the inside of the elbow
                crease = 0.0025 * elbow_k * sin(th * 3 + l * 90) * (0.5 + 0.5 * cos(th))
                rr = r + crease
                ring.append(p + Nn * (rr * cos(th)) + B * (rr * 0.93 * sin(th)))
            rings.append(ring)
            eds.append(min(Lt - l, abs(l - cuff0)))
        m = Mesh("sleeve_" + side)
        m.grid(rings, 'wool_coat', closed=True, attrs=lambda j, i: {"edge_d": eds[j]})
        # lining turned in at the cuff end
        pe, (T, Nn, B) = path[-1], fr[-1]
        inner = []
        for (off, rr) in ((0.0, 0.0565), (-0.004, 0.0525), (-0.045, 0.049)):
            inner.append([pe + T * off + Nn * (rr * cos(2 * pi * i / n_around)) + B * (rr * 0.93 * sin(2 * pi * i / n_around))
                          for i in range(n_around)])
        m.grid(inner, 'wool_coat_in', closed=True, flip=True)
        ob = m.to_object(recalc=False)
        merge_by_distance(ob, 1e-6)
        obs.append(part(ob, "arm", side=side))
    return obs


def UA():
    return crig.UA_LEN


def surf_front(surf, x, z, offset=0.0, back=False):
    o = V(x, 0.6 if back else -0.6, z)
    p, n = surf.ray(o, V(0, -1 if back else 1, 0), offset)
    return p, n


def build_buttons(mats, surf):
    m = Mesh("coat_buttons")
    pos = []
    for k in range(6):
        z = 1.455 - k * 0.072
        xr = 0.052 + (z - 1.03) * 0.11
        for s in (1, -1):
            p, n = surf_front(surf, s * xr, z)
            pos.append((p, n))
            prof = [(0.0, -0.001), (0.0095, -0.001), (0.0098, 0.0015), (0.008, 0.0032), (0.0045, 0.0042), (0.0, 0.0045)]
            u = n.orthogonal().normalized()
            lathe(m, prof, p, u, n.cross(u), n, 14, 'button', cap0=True)
    ob = m.to_object(recalc=False)
    return part(ob, "copy_rigid_each"), pos


def build_shoulder_straps(mats, surf, variant):
    obs = []
    for s in (1, -1):
        m = Mesh("shoulder_strap")
        ctrl = [V(0.080 * s, 0.006, 1.512), V(0.130 * s, 0.006, 1.485), V(0.183 * s, 0.008, 1.458)]
        strap(m, surf, ctrl, 0.046, 0.004, 0.0035, 'wool_coat', step=0.008)
        strap(m, surf, ctrl, 0.052, 0.003, 0.0018, 'piping', step=0.008)
        ob = m.to_object()
        obs.append(part(ob, "copy"))
    return obs


def build_pocket_flaps(mats, surf):
    m = Mesh("pocket_flaps")
    for s in (1, -1):
        th = s * 1.30
        z = 0.925
        sec = interp_table(SKIRT, z)
        p = sec_point(sec, th, z, 0.0)
        q, n = surf.project(p, 0.004)
        n = V(n.x, n.y, 0).normalized()
        up = V(0, 0, 1)
        t = up.cross(n).normalized()
        R = Matrix((t, n, up)).transposed().to_4x4() @ Matrix.Rotation(-0.25 * s, 4, 'Y')
        X = Matrix.Translation(q) @ R
        rounded_box(m, (0, 0, 0), (0.17, 0.006, 0.062), 0.0025, 'wool_coat', 2, X)
    ob = m.to_object()
    return part(ob, "copy")


# ===================================================================================== legs, boots
def build_legs(mats):
    J = crig.joints()
    obs = []
    for side, s in (("L", 1), ("R", -1)):
        hip, knee, ank = J['hip' + side], J['knee' + side], J['ankle' + side]
        top = V(0.075 * s, 0.0, 1.02)
        shin_end = knee.lerp(ank, 0.55)
        path = resample(catmull([top, hip, hip.lerp(knee, 0.5), knee, knee.lerp(ank, 0.3), shin_end], 6), 0.018)
        n = len(path)
        fr = frames_along(path, V(0, -1, 0))
        rings = []
        for k, (p, (T, Nn, B)) in enumerate(zip(path, fr)):
            z = p.z
            r = interp_table([(0.28, 0.050), (0.40, 0.055), (0.50, 0.058), (0.56, 0.062), (0.75, 0.076),
                              (0.93, 0.088), (1.02, 0.088)], z)[0]
            ring = []
            for i in range(24):
                th = 2 * pi * i / 24
                wr = 0.004 * sin(th * 4 + z * 60) * sstep(0.62, 0.52, z) * sstep(0.40, 0.46, z)
                ring.append(p + Nn * ((r + wr) * 1.04 * cos(th)) + B * ((r + wr) * sin(th)))
            rings.append(ring)
        m = Mesh("leg_" + side)
        m.grid(rings, 'wool_trouser', closed=True, cap0=True, cap1=True)
        obs.append(part(m.to_object(), "leg", side=side))
    return obs


FOOT = [  # y, half width, z top, z bottom
    (0.088, 0.028, 0.088, 0.032), (0.078, 0.037, 0.115, 0.028), (0.055, 0.042, 0.135, 0.026),
    (0.020, 0.044, 0.142, 0.026), (-0.020, 0.045, 0.124, 0.022), (-0.060, 0.046, 0.098, 0.017),
    (-0.100, 0.0475, 0.078, 0.015), (-0.140, 0.047, 0.066, 0.015), (-0.175, 0.043, 0.058, 0.017),
    (-0.203, 0.035, 0.052, 0.020), (-0.220, 0.024, 0.045, 0.024), (-0.227, 0.011, 0.039, 0.030)]


def foot_ring(cx, y, hw, zt, zb, n=24):
    zc = (zt + zb) * 0.5
    hh = (zt - zb) * 0.5
    pts = []
    for i in range(n):
        th = 2 * pi * i / n
        c, s_ = cos(th), sin(th)
        e = 2 / (2.3 if s_ > 0 else 5.0)
        x = math.copysign(abs(c) ** (2 / 2.6), c) * hw
        z = math.copysign(abs(s_) ** e, s_) * hh
        pts.append(V(cx + x, y, zc + z))
    return pts


def build_boots(mats):
    J = crig.joints()
    obs = []
    for side, s in (("L", 1), ("R", -1)):
        m = Mesh("boot_" + side)
        knee, ank = J['knee' + side], J['ankle' + side]
        cx = ank.x
        # shaft (Schaft) from just below the coat hem down into the foot
        shaft = []
        axis = (knee - ank).normalized()
        for z, r in ((0.405, 0.0635), (0.385, 0.062), (0.34, 0.059), (0.29, 0.056), (0.24, 0.053),
                     (0.19, 0.0505), (0.15, 0.049), (0.12, 0.050), (0.095, 0.052)):
            t = (z - ank.z) / axis.z
            c = ank + axis * t
            ring = []
            for i in range(26):
                th = 2 * pi * i / 26
                wr = 0.0018 * sin(th * 5 + z * 80) * sstep(0.10, 0.14, z) * sstep(0.26, 0.20, z)
                ring.append(c + V((r + wr) * sin(th), -(r + wr) * 1.08 * cos(th), 0))
            shaft.append(ring)
        shaft = shaft[::-1]   # bottom to top, CCW about +Z -> outward
        m.grid(shaft, 'leather_boot', closed=True)
        # turned lip inside the shaft top
        top = shaft[-1]
        c = sum(top, Vector()) / len(top)
        inner = [c + (p - c) * 0.93 + V(0, 0, -0.004) for p in top]
        inner2 = [c + (p - c) * 0.92 + V(0, 0, -0.05) for p in top]
        m.grid([top, inner, inner2], 'leather_boot', closed=True)
        # foot
        rings = [foot_ring(cx, y, hw, zt, zb) for (y, hw, zt, zb) in FOOT]
        m.grid(rings, 'leather_boot', closed=True, cap0=True, cap1=True)
        # sole + heel block
        srings = []
        for (y, hw, zt, zb) in FOOT[1:]:
            bot = 0.0 if y > -0.19 else (0.006 if y > -0.215 else 0.014)
            tp = (0.030 if y > 0.015 else 0.016) if y > -0.19 else zb + 0.004
            srings.append(foot_ring(cx, y, hw + 0.0045, tp, bot, 20))
        m.grid(srings, 'sole', closed=True, cap0=True, cap1=True)
        ob = m.to_object(recalc=False)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(ob.data)
        bm.free()
        obs.append(part(ob, "foot", side=side))
        # hobnails and heel iron
        h = Mesh("hobnails_" + side)
        for y in [-0.185 + 0.017 * k for k in range(9)]:
            hw = interp_table([(r[0], r[1]) for r in FOOT[::-1]], y)[0]
            nx = int((hw * 2 - 0.016) / 0.016) + 1
            for q in range(nx):
                x = cx - (nx - 1) * 0.008 + q * 0.016
                lathe(h, [(0.0036, 0.0008), (0.003, -0.0012), (0.0, -0.0022)], V(x, y, 0.0),
                      V(1, 0, 0), V(0, 1, 0), V(0, 0, 1), 6, 'steel')
        for k in range(13):
            a = pi * k / 12
            x = cx + cos(a) * 0.032
            y = 0.045 + sin(a) * 0.040
            lathe(h, [(0.006, 0.0008), (0.005, -0.0016), (0.0, -0.0022)], V(x, y, 0.0),
                  V(1, 0, 0), V(0, 1, 0), V(0, 0, 1), 6, 'steel')
        obs.append(part(h.to_object(recalc=False), "foot", side=side))
    return obs


# ===================================================================================== hands
def build_gloves(mats):
    J = crig.joints()
    obs = []
    for side, s in (("L", 1), ("R", -1)):
        F, d, n, ts = crig.hand_layout(side, J)
        wr = J['wr' + side]
        m = Mesh("glove_" + side)
        X = ts           # across the palm, thumb side +
        rings = []
        for t, hw, hh in ((-0.035, 0.035, 0.024), (0.0, 0.034, 0.020), (0.03, 0.040, 0.017), (0.06, 0.045, 0.016),
                          (0.085, 0.046, 0.014), (0.098, 0.040, 0.012)):
            c = wr + d * t - n * 0.002
            ring = []
            for i in range(18):
                th = 2 * pi * i / 18
                ring.append(c + X * (hw * cos(th)) + n.cross(X).normalized() * 0 + (-n) * (hh * sin(th)))
            rings.append(ring)
        m.grid(rings, 'glove', closed=True, cap0=True, cap1=True)
        for f, pts in F.items():
            r0 = 0.0125 if f == "Thumb" else 0.0102
            r1 = 0.0098 if f == "Thumb" else 0.0082
            start = pts[0] - (pts[1] - pts[0]).normalized() * (0.02 if f == "Thumb" else 0.006)
            path = resample([start] + pts, 0.007)
            Lp = len(path)
            fr = frames_along(path, n)
            frings = []
            for k, (p, (T, Nn, B)) in enumerate(zip(path, fr)):
                t = k / (Lp - 1)
                r = lerp(r0, r1, t)
                if k == Lp - 1:
                    r *= 0.75
                frings.append([p + Nn * (r * 0.9 * cos(2 * pi * i / 10)) + B * (r * sin(2 * pi * i / 10)) for i in range(10)])
            tip = path[-1] + fr[-1][0] * 0.006
            base = m.grid(frings, 'glove', closed=True, cap0=True)
            last = list(range(base + (Lp - 1) * 10, base + Lp * 10))
            ti = m.add_v(tip)
            for i in range(10):
                m.add_f((last[i], last[(i + 1) % 10], ti), ((0, 0), (0.005, 0), (0.0025, 0.005)), 'glove')
            ob = None
        # knitted wrist band
        cuff = []
        for t, r in ((-0.075, 0.037), (-0.02, 0.036), (0.008, 0.033)):
            c = wr + d * t
            u = X
            w = d.cross(u).normalized()
            cuff.append([c + u * (r * cos(2 * pi * i / 20)) + w * (r * 0.85 * sin(2 * pi * i / 20)) for i in range(20)])
        m.grid(cuff, 'glove', closed=True)
        ob = m.to_object()
        obs.append(part(ob, "hand", side=side))
    return obs


# ===================================================================================== head
HEAD_C = V(0, -0.012, 1.672)


def build_head(mats):
    m = Mesh("head")

    def shape(th, ph, p):
        zl = p.z
        jaw = sstep(-0.02, -0.10, zl)
        p.x *= 1.0 - 0.28 * jaw
        if p.y < 0:
            p.y *= 1.0 - 0.10 * jaw
            p.y -= 0.012 * jaw * sstep(0.05, 0.0, abs(p.x))   # chin
        # nose and brow
        p.y -= 0.017 * exp(-((p.x / 0.011) ** 2 + ((zl + 0.012) / 0.020) ** 2)) * (1 if p.y < 0 else 0)
        p.y -= 0.006 * exp(-((p.x / 0.045) ** 2 + ((zl - 0.012) / 0.010) ** 2)) * (1 if p.y < 0 else 0)
        # eye sockets
        p.y += 0.006 * exp(-(((abs(p.x) - 0.032) / 0.014) ** 2 + ((zl + 0.004) / 0.010) ** 2)) * (1 if p.y < 0 else 0)
        return p
    ellipsoid(m, HEAD_C, 0.076, 0.097, 0.112, 36, 26, 'skin', shape)
    for s in (1, -1):
        ellipsoid(m, V(0.073 * s, 0.006, 1.657), 0.010, 0.020, 0.030, 10, 8, 'skin')
    # neck
    rings = []
    for z, r in ((1.42, 0.060), (1.50, 0.058), (1.56, 0.056), (1.625, 0.054)):
        rings.append([V(r * sin(2 * pi * i / 24), 0.004 - r * 0.95 * cos(2 * pi * i / 24), z) for i in range(24)])
    m.grid(rings, 'skin', closed=True)
    ob = m.to_object()
    # tunic collar showing at the throat
    t = Mesh("tunic_collar")
    rings = []
    for z, r in ((1.49, 0.066), (1.52, 0.065), (1.548, 0.063), (1.551, 0.060)):
        rings.append([V(r * sin(2 * pi * i / 28), 0.004 - r * 0.95 * cos(2 * pi * i / 28), z) for i in range(28)])
    t.grid(rings, 'wool_tunic', closed=True)
    return [part(ob, "head"), part(t.to_object(), "head")]


# ===================================================================================== helmet M35
HELM_O = V(0, -0.004, 1.690)


def helm_params(phi):
    a = abs(math.remainder(phi, 2 * pi))
    wf = 1.0 - sstep(0.52, 0.95, a)
    wb = sstep(2.15, 2.75, a)
    ws = max(0.0, 1.0 - wf - wb)
    A = 0.126 if a < pi / 2 else 0.127
    B = 0.107
    rho_e = 1.0 / sqrt((cos(phi) / A) ** 2 + (sin(phi) / B) ** 2)
    zs = wf * 0.0 + ws * -0.024 + wb * -0.032
    f = wf * 0.028 + ws * 0.022 + wb * 0.034
    zr = wf * -0.012 + ws * -0.052 + wb * -0.080
    return rho_e, zs, f, zr


def build_helmet(mats):
    m = Mesh("helmet")
    NPHI = 72
    rows = []
    rimv = []
    n_dome = 14
    for j in range(n_dome + 1 + 3 + 7):
        rows.append([])
        rimv.append([])
    for i in range(NPHI):
        phi = 2 * pi * i / NPHI
        rho_e, zs, f, zr = helm_params(phi)
        col = []
        H = 0.112
        for j in range(1, n_dome + 1):
            al = (pi / 2) * j / n_dome
            rho = rho_e * sin(al) ** (2 / 2.25)
            z = H * cos(al) ** (2 / 2.25)
            col.append((rho, z))
        for j in range(1, 4):
            t = j / 3
            col.append((rho_e * (1 + 0.012 * t), zs * t))
        rs = rho_e * 1.012
        for j in range(1, 8):
            t = j / 7
            col.append((rs + f * t ** 1.5, zs + (zr - zs) * t))
        for j, (rho, z) in enumerate(col):
            p = HELM_O + V(rho * sin(phi), -rho * cos(phi), z)
            rows[j].append(p)
            rimv[j].append(sstep(0.016, 0.0, (z - zr)) if z - zr < 0.03 else 0.0)
    rows = [r for r in rows if r]
    rimv = rimv[:len(rows)]
    # rows go top -> rim (downward). CCW phi + going down gives inward normals -> flip
    base = m.grid(rows, 'helmet', closed=True, flip=True, attrs=lambda j, i: {"rim": rimv[j][i]})
    top = list(range(base, base + NPHI))
    ci = m.add_v(HELM_O + V(0, 0, 0.1125), rim=0.0)
    for i in range(NPHI):
        m.add_f((top[(i + 1) % NPHI], top[i], ci), ((0, 0), (0.01, 0), (0.005, 0.01)), 'helmet')
    ob = m.to_object(recalc=False)
    orient_outward(ob, HELM_O)
    ob.data.materials.append(bpy.data.materials["helmet_in"])
    solidify(ob, 0.0024, offset=-1.0, inner_mat_offset=1)
    out = [part(ob, "rigid", bone="Head")]
    # details: vent grommets, liner rivets, leather liner band, chin strap
    d = Mesh("helmet_details")
    for s in (1, -1):
        phi = s * 1.72
        rho_e, zs, f, zr = helm_params(phi)
        al = radians(66)
        rho = rho_e * sin(al) ** (2 / 2.25)
        z = 0.112 * cos(al) ** (2 / 2.25)
        p = HELM_O + V(rho * sin(phi), -rho * cos(phi), z)
        nrm = V(sin(phi), -cos(phi), 0.45).normalized()
        torus(d, p + nrm * 0.0005, nrm, 0.0042, 0.0016, 12, 6, 'helmet')
    for phi in (0.0, 1.95, -1.95):
        rho_e, zs, f, zr = helm_params(phi)
        p = HELM_O + V((rho_e + 0.0012) * sin(phi), -(rho_e + 0.0012) * cos(phi), -0.004 if phi == 0 else zs * 0.4)
        nrm = V(sin(phi), -cos(phi), 0).normalized()
        u = nrm.orthogonal().normalized()
        lathe(d, [(0.0, 0.0028), (0.0035, 0.0018), (0.0045, 0.0)], p, u, nrm.cross(u), nrm, 10, 'helmet')
    # liner band
    rings = []
    for z, k in ((-0.022, 0.915), (0.012, 0.925), (0.03, 0.915)):
        ring = []
        for i in range(NPHI):
            phi = 2 * pi * i / NPHI
            rho_e = helm_params(phi)[0]
            ring.append(HELM_O + V(rho_e * k * sin(phi), -rho_e * k * cos(phi), z))
        rings.append(ring)
    d.grid(rings, 'liner', closed=True, flip=True)
    hs = Mesh("_headsurf")
    ellipsoid(hs, HEAD_C, 0.079, 0.100, 0.115, 24, 16, 'skin')
    hso = hs.to_object()
    surf = Surface([hso])
    for s in (1, -1):
        ctrl = [V(0.088 * s, 0.006, 1.672), V(0.080 * s, -0.010, 1.62), V(0.060 * s, -0.045, 1.575),
                V(0.030 * s, -0.070, 1.553), V(0.0, -0.076, 1.548)]
        strap(d, surf, ctrl, 0.015, 0.002, 0.0015, 'liner', step=0.01)
    bpy.data.objects.remove(hso, do_unlink=True)
    out.append(part(d.to_object(), "rigid", bone="Head"))
    return out


# ===================================================================================== belt & kit
BELT_Z = 1.055


def build_belt(mats, surf):
    m = Mesh("belt")
    ctrl = []
    for i in range(32):
        th = 2 * pi * i / 32
        sec = interp_table(SKIRT, BELT_Z)
        ctrl.append(sec_point(sec, th, BELT_Z, 0.02))
    P, Nn = strap(m, surf, ctrl, 0.046, 0.0042, 0.0068, 'leather', step=0.01, closed=True)
    ob = m.to_object()
    merge_by_distance(ob, 1e-5)
    part(ob, "copy")
    # buckle (plain stamped plate, no insignia)
    p, n = surf_front(surf, 0.0, BELT_Z, 0.0115)
    n = V(n.x, n.y, 0).normalized()
    up = V(0, 0, 1)
    t = up.cross(n).normalized()
    X = Matrix.Translation(p) @ Matrix((t, n, up)).transposed().to_4x4()
    b = Mesh("buckle")
    rounded_box(b, (0, 0.0, 0), (0.064, 0.005, 0.050), 0.004, 'button', 2, X)
    rounded_box(b, (0, 0.0028, 0), (0.058, 0.0015, 0.044), 0.0015, 'button', 1, X)
    lathe(b, [(0.0, 0.0045), (0.016, 0.0040), (0.0175, 0.0030), (0.0175, 0.0)], X @ V(0, 0.0005, 0), t, up, n, 24, 'button')
    torus(b, X @ V(0, 0.0045, 0), n, 0.0135, 0.0009, 24, 4, 'button')
    part(b.to_object(), "copy_rigid")
    return P, Nn


def belt_frame(P, Nn, s_target, side):
    """Point on the belt path at arc length s from the front centre toward +X (side=1) or -X."""
    # find front index (max -y)
    i0 = min(range(len(P)), key=lambda i: P[i].y if abs(P[i].x) < 0.05 else 9)
    L = 0.0
    n = len(P)
    i = i0
    while True:
        j = (i + side) % n
        seg = (P[j] - P[i]).length
        if L + seg >= s_target:
            t = (s_target - L) / seg
            p = P[i].lerp(P[j], t)
            nrm = Nn[i].lerp(Nn[j], t).normalized()
            tang = (P[j] - P[i]).normalized() * side
            return p, nrm, tang
        L += seg
        i = j


def frame_X(p, n, tang=None):
    n = V(n.x, n.y, n.z * 0.3).normalized()
    up = V(0, 0, 1)
    t = up.cross(n).normalized() if tang is None else (tang - n * tang.dot(n)).normalized()
    up = n.cross(t)
    return Matrix.Translation(p) @ Matrix((t, n, up)).transposed().to_4x4()


def build_pouches(mats, P, Nn):
    obs = []
    tops = {}
    for side in (1, -1):
        m = Mesh("pouches")
        for k in range(3):
            s = 0.050 + 0.028 + k * 0.059
            p, n, tang = belt_frame(P, Nn, s, side)
            X = frame_X(p, n, tang * side)
            # tilt the outer pouches slightly
            X = X @ Matrix.Rotation(-0.05 * side * k, 4, 'Y')
            rounded_box(m, (0, 0.019, -0.022), (0.055, 0.034, 0.088), 0.007, 'leather', 2, X)
            rounded_box(m, (0, 0.0215, 0.012), (0.058, 0.0385, 0.030), 0.006, 'leather', 2, X)
            rounded_box(m, (0, 0.0385, -0.006), (0.020, 0.004, 0.034), 0.0018, 'leather', 1, X)
            lathe(m, [(0.0, 0.0022), (0.003, 0.0016), (0.0034, 0.0)], X @ V(0, 0.0395, -0.019),
                  X.to_3x3() @ V(1, 0, 0), X.to_3x3() @ V(0, 0, 1), X.to_3x3() @ V(0, 1, 0), 8, 'button')
            if k == 1:
                tops[side] = X @ V(0, 0.004, 0.03)
        obs.append(part(m.to_object(), "copy_rigid_each"))
    return tops


def build_ystraps(mats, surf, tops):
    m = Mesh("ystraps")
    for s in (1, -1):
        f = tops[s]
        ctrl = [f, V(0.112 * s, -0.12, 1.16), V(0.118 * s, -0.13, 1.30), V(0.122 * s, -0.08, 1.43),
                V(0.125 * s, 0.0, 1.49), V(0.110 * s, 0.09, 1.43), V(0.06 * s, 0.12, 1.355), V(0.012 * s, 0.13, 1.315)]
        strap(m, surf, ctrl, 0.040, 0.0035, 0.0045, 'leather', step=0.012)
    ctrl = [V(0, 0.13, 1.30), V(0, 0.13, 1.20), V(0, 0.13, 1.09)]
    strap(m, surf, ctrl, 0.042, 0.0035, 0.0045, 'leather', step=0.012)
    p, n = surf_front(surf, 0.0, 1.31, 0.009, back=True)
    torus(m, p, n, 0.017, 0.0028, 24, 6, 'steel')
    return part(m.to_object(), "copy")


def superellipsoid(m, c, hx, hy, hz, e, X, mat, nu=24, nv=14, deform=None):
    def fn(th, ph, p):
        s, co = sin(th), cos(th)
        cp, sp = cos(ph), sin(ph)
        sg = lambda v, ex: math.copysign(abs(v) ** ex, v)
        q = V(hx * sg(cp, e) * sg(s, e), -hy * sg(cp, e) * sg(co, e), hz * sg(sp, e))
        if deform:
            q = deform(q)
        return q
    base = len(m.v)
    ellipsoid(m, V(0, 0, 0), 1, 1, 1, nu, nv, mat, fn)
    M = X @ Matrix.Translation(c)
    for i in range(base, len(m.v)):
        m.v[i] = M @ m.v[i]


def hang_frame(surf, th, z, out, tilt=0.0):
    sec = interp_table(SKIRT, z)
    p = sec_point(sec, th, z, 0.0)
    q, n = surf.project(p)
    n = V(n.x, n.y, 0).normalized()
    up = V(0, 0, 1)
    t = up.cross(n).normalized()
    X = Matrix.Translation(q + n * out) @ Matrix((t, n, up)).transposed().to_4x4() @ Matrix.Rotation(tilt, 4, 'Y')
    return X, q, n


def build_breadbag(mats, surf):
    m = Mesh("breadbag")
    X, q, n = hang_frame(surf, -2.22, 0.965, 0.042, tilt=0.06)
    # lean the bag out at the bottom so it rides on the flaring skirt
    X = X @ Matrix.Rotation(-0.14, 4, 'X')
    puff = lambda p: V(p.x, p.y * (1 + 0.35 * (1 - (p.x / 0.13) ** 2) * (1 - (p.z / 0.1) ** 2)), p.z)
    superellipsoid(m, V(0, 0, 0), 0.128, 0.030, 0.098, 0.35, X, 'canvas', 26, 14, puff)
    superellipsoid(m, V(0, 0.034, 0.03), 0.129, 0.006, 0.072, 0.25, X, 'canvas', 22, 10)
    for xo in (-0.07, 0.07):
        rounded_box(m, (xo, 0.042, 0.0), (0.018, 0.003, 0.09), 0.0012, 'leather', 1, X)
        rounded_box(m, (xo, -0.032, 0.105), (0.03, 0.006, 0.06), 0.002, 'leather', 1, X)
    obs = [part(m.to_object(), "rigid", bone="Hips")]
    # canteen M31 hooked on the bag
    c = Mesh("canteen")
    Xc = X @ Matrix.Translation(V(-0.055, 0.075, -0.035)) @ Matrix.Rotation(0.05, 4, 'Y')
    kid = lambda p: V(p.x, p.y + 0.014 * (p.x / 0.065) ** 2, p.z)
    superellipsoid(c, V(0, 0, 0), 0.064, 0.034, 0.083, 0.75, Xc, 'felt', 24, 14, kid)
    superellipsoid(c, V(0, 0.002, 0.103), 0.050, 0.034, 0.030, 0.45, Xc, 'cup', 20, 10, kid)
    rounded_box(c, (0, 0.040, 0.0), (0.016, 0.003, 0.20), 0.0012, 'leather', 1, Xc)
    rounded_box(c, (0, 0.0, 0.0), (0.135, 0.071, 0.014), 0.003, 'leather', 1, Xc)
    obs.append(part(c.to_object(), "rigid", bone="Hips"))
    return obs


def build_canister(mats, surf):
    m = Mesh("gasmask_canister")
    X, q, n = hang_frame(surf, pi - 0.30, 0.90, 0.066, tilt=0.20)
    X = X @ Matrix.Rotation(-0.10, 4, 'X')
    prof = [(0.0, 0.0), (0.040, 0.0), (0.052, 0.003), (0.056, 0.010)]
    h = 0.018
    while h < 0.205:
        prof.append((0.0565 + 0.0028 * (0.5 + 0.5 * cos(2 * pi * (h - 0.018) / 0.0175)), h))
        h += 0.0035
    prof += [(0.0565, 0.208), (0.0595, 0.212), (0.0598, 0.250), (0.054, 0.256), (0.03, 0.259), (0.0, 0.259)]
    base = X @ V(0, 0, -0.13)
    R = X.to_3x3()
    lathe(m, prof, base, R @ V(1, 0, 0), R @ V(0, 1, 0), R @ V(0, 0, 1), 30, 'canister')
    rounded_box(m, (0, 0.058, 0.105), (0.020, 0.010, 0.026), 0.003, 'canister', 1, X)
    rounded_box(m, (0, -0.058, 0.105), (0.03, 0.008, 0.02), 0.003, 'canister', 1, X)
    obs = [part(m.to_object(), "rigid", bone="Hips")]
    s = Mesh("canister_strap")
    p_top = X @ V(0, -0.02, 0.135)
    strap(s, surf, [p_top + V(0, 0.01, 0.0), V(0.04, 0.14, 1.06), V(0.05, 0.135, 1.09)], 0.022, 0.003, 0.012, 'canvas', step=0.01)
    obs.append(part(s.to_object(), "rigid", bone="Hips"))
    return obs


def build_shovel(mats, surf):
    m = Mesh("shovel")
    X, q, n = hang_frame(surf, 2.02, 0.955, 0.020, tilt=-0.35)
    rounded_box(m, (0, 0, 0), (0.165, 0.030, 0.205), 0.012, 'leather', 2, X)
    rounded_box(m, (0, 0.016, 0.045), (0.168, 0.006, 0.07), 0.004, 'leather', 1, X)
    # wooden handle out of the bottom of the carrier
    R = X.to_3x3()
    p0 = X @ V(0.0, 0.0, -0.09)
    p1 = X @ V(0.0, 0.0, -0.42)
    lathe(m, [(0.0, 0.0), (0.015, 0.002), (0.016, 0.03), (0.0165, 0.3), (0.018, 0.325), (0.012, 0.335), (0.0, 0.336)],
          p0, R @ V(1, 0, 0), R @ V(0, 1, 0), R @ V(0, 0, -1), 14, 'wood')
    # bayonet in its frog, outside the carrier
    Xb = X @ Matrix.Translation(V(0.035, 0.032, 0.0)) @ Matrix.Rotation(0.08, 4, 'Y')
    Rb = Xb.to_3x3()
    sc = [(0.0, 0.0), (0.006, 0.004), (0.011, 0.02), (0.0135, 0.27), (0.016, 0.285), (0.016, 0.295), (0.0, 0.296)]
    sb = Mesh("_tmp")
    lathe(m, sc, Xb @ V(0, 0, -0.22), Rb @ V(1, 0, 0), Rb @ V(0, 1, 0) * 0.55, Rb @ V(0, 0, 1), 14, 'steel')
    rounded_box(m, (0, 0, 0.115), (0.022, 0.016, 0.105), 0.006, 'wood', 2, Xb)
    lathe(m, [(0.0, 0.0), (0.0125, 0.0), (0.0125, 0.012), (0.0, 0.016)], Xb @ V(0, 0, 0.168),
          Rb @ V(1, 0, 0), Rb @ V(0, 1, 0), Rb @ V(0, 0, 1), 12, 'steel')
    rounded_box(m, (0, 0, 0.065), (0.045, 0.006, 0.015), 0.002, 'steel', 1, Xb)
    rounded_box(m, (0, -0.002, 0.03), (0.040, 0.03, 0.05), 0.004, 'leather', 1, Xb)
    return [part(m.to_object(), "rigid", bone="Hips")]


# ===================================================================================== gorget
def build_gorget(mats, surf, collar_surf):
    obs = []
    zc = 1.385
    # crescent outline (x, z) in metres, CCW
    pts = []
    n_out = 28
    for i in range(n_out + 1):
        a = pi + pi * i / n_out
        pts.append((0.084 * cos(a), -0.012 + 0.058 * sin(a)))
    for i in range(1, 14):
        t = i / 14
        x = 0.084 - 0.168 * t
        pts.append((x, 0.022 - 0.024 * (1 - (x / 0.084) ** 2) ** 0.8 + (0.004 if abs(x) > 0.07 else 0)))

    def place(x, z, off):
        p, n = surf.ray(V(x, -0.6, zc + z), V(0, 1, 0))
        if p is None:
            p, n = V(x, -0.15, zc + z), V(0, -1, 0)
        return p + V(0, -1, 0) * (0.012 + off)

    m = Mesh("gorget")

    def plate(outline, off0, off1, mat, cap=True):
        top = [place(x, z, off1) for x, z in outline]
        bot = [place(x, z, off0) for x, z in outline]
        cxz = (sum(p[0] for p in outline) / len(outline), sum(p[1] for p in outline) / len(outline))
        base = m.grid([bot, top], mat, closed=True)
        n = len(outline)
        if cap:
            # triangulate the crescent by fanning from strip pairs (outline is star-shaped about a low centre)
            for ring, flip, off in ((top, False, off1), (bot, True, off0)):
                ci = m.add_v(place(cxz[0], cxz[1] - 0.02, off))
                idx0 = base + (n if ring is top else 0)
                for k in range(n):
                    a, b = idx0 + k, idx0 + (k + 1) % n
                    f = (a, b, ci) if not flip else (b, a, ci)
                    m.add_f(f, ((0, 0), (0.01, 0), (0.005, 0.01)), mat)
    plate(pts, 0.0, 0.0016, 'gorget')
    # raised rim
    inner = []
    for x, z in pts:
        inner.append((x * 0.94, -0.012 + (z + 0.012) * 0.90))
    rim_out = [place(x, z, 0.0027) for x, z in pts]
    rim_in = [place(x, z, 0.0027) for x, z in inner]
    rim_in0 = [place(x, z, 0.0012) for x, z in inner]
    m.grid([[place(x, z, 0.0012) for x, z in pts], rim_out, rim_in, rim_in0], 'gorget_bright', closed=True)
    # scroll banner
    scroll = []
    for i in range(13):
        x = -0.066 + 0.132 * i / 12
        scroll.append((x, -0.040 + 0.006 * (x / 0.066) ** 2))
    for i in range(13):
        x = 0.066 - 0.132 * i / 12
        scroll.append((x, -0.024 + 0.006 * (x / 0.066) ** 2))
    plate(scroll[::-1], 0.0015, 0.0026, 'gorget_dark')
    # bosses (luminous-painted buttons) at the horns
    for s in (1, -1):
        p = place(0.066 * s, 0.003, 0.0016)
        lathe(m, [(0.0, 0.0055), (0.0055, 0.0045), (0.0075, 0.0018), (0.0078, 0.0)], p, V(1, 0, 0), V(0, 0, 1),
              V(0, -1, 0), 16, 'lumi')
    gob = m.to_object()
    obs.append(part(gob, "copy_rigid"))
    # lettering
    bpy.ops.object.text_add(location=(0, 0, 0))
    txt = bpy.context.active_object
    txt.data.body = "FELDGENDARMERIE"
    txt.data.align_x = 'CENTER'
    txt.data.align_y = 'CENTER'
    txt.data.size = 0.0102
    txt.data.extrude = 0.0
    txt.data.resolution_u = 2
    txt.data.space_character = 1.05
    bpy.ops.object.convert(target='MESH')
    tme = txt.data
    tm = Mesh("gorget_text")
    tb = bmesh.new()
    tb.from_mesh(tme)
    bmesh.ops.triangulate(tb, faces=tb.faces)
    ext = bmesh.ops.extrude_face_region(tb, geom=list(tb.faces))
    for v in [e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)]:
        v.co.z += 0.0006
    tb.verts.index_update()
    for v in tb.verts:
        x, y = v.co.x, v.co.y
        zz = -0.032 + y + 0.006 * (x / 0.066) ** 2
        tm.add_v(place(x, zz, 0.0026 + v.co.z))
    for f in tb.faces:
        tm.add_f([v.index for v in f.verts], [(v.co.x, v.co.y) for v in f.verts], 'gorget_bright')
    tb.free()
    bpy.data.objects.remove(txt, do_unlink=True)
    tob = tm.to_object()
    obs.append(part(tob, "copy_rigid"))
    # chain round the neck, over the collar
    ch = Mesh("gorget_chain")
    ctrl = [V(0.066, -0.16, zc + 0.006), V(0.080, -0.10, 1.47), V(0.095, -0.03, 1.535), V(0.07, 0.06, 1.555),
            V(0.0, 0.085, 1.56), V(-0.07, 0.06, 1.555), V(-0.095, -0.03, 1.535), V(-0.080, -0.10, 1.47),
            V(-0.066, -0.16, zc + 0.006)]
    path = resample(catmull(ctrl, 8), 0.0095)
    fr = frames_along(path, V(0, 0, 1))
    for k, (p, (T, Nn, B)) in enumerate(zip(path, fr)):
        q, nn = collar_surf.project(p, 0.004)
        if k == 0 or k == len(path) - 1:
            q = place(0.066 * (1 if k == 0 else -1), 0.006, 0.006)
        ax = nn if k % 2 == 0 else T.cross(nn).normalized()
        u = T
        w = ax.cross(u).normalized()
        rings = []
        R, r = 0.0058, 0.0013
        for i in range(8):
            a = 2 * pi * i / 8
            d = u * (cos(a) * 1.0) + w * (sin(a) * 0.62)
            ctr = q + d * R
            rings.append([ctr + d.normalized() * (r * cos(2 * pi * j / 4)) + ax * (r * sin(2 * pi * j / 4)) for j in range(4)])
        rings.append(rings[0])
        ch.grid(rings, 'steel_bright', closed=True)
    obs.append(part(ch.to_object(), "copy"))
    return obs


# ===================================================================================== assemble
def build_all(mats, variant):
    PARTS.clear()
    torso = build_torso(mats)
    skirt = build_skirt(mats)
    surf = Surface([torso, skirt])
    collar = build_collar(mats, Surface([torso]))
    build_sleeves(mats)
    _, buttons = build_buttons(mats, Surface([torso]))
    build_shoulder_straps(mats, Surface([torso]), variant)
    build_pocket_flaps(mats, Surface([skirt]))
    build_legs(mats)
    build_boots(mats)
    build_gloves(mats)
    build_head(mats)
    build_helmet(mats)
    P, Nn = build_belt(mats, surf)
    tops = build_pouches(mats, P, Nn)
    build_ystraps(mats, Surface([torso]), tops)
    build_breadbag(mats, Surface([skirt]))
    build_canister(mats, Surface([skirt]))
    build_shovel(mats, Surface([skirt]))
    if variant == "feldgendarm":
        build_gorget(mats, Surface([torso]), Surface([torso, collar]))
    # torch mount: on the 3rd button of the left row (button-on torch)
    tb = [p for p in buttons if p[0].x > 0][2]
    torch = tb[0] + tb[1] * 0.012 + V(0, 0, -0.045)
    return list(PARTS), torch
