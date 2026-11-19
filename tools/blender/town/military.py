"""Atlantic Wall pieces: bunker_atlantic (small casemate), searchlight_60cm, wire_fence_5m, minefield_sign.
Text only on signs; no eagles or swastikas anywhere."""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box, bm_box_minmax, bm_cyl, boolean, union
from parts import roff, text
from common import Cols, WFace, cyl_between, face_poly, lathe, tube, sandbag_run
from ihelp import split_by

PI = math.pi


# ==================================================================== bunker
def bunker_atlantic():
    """Small casemate (~8 x 7 m) for an anti-tank gun: 1.5 m board-marked concrete walls, 1.2 m roof,
    stepped embrasure facing -Y under a projecting visor, rear entrance (+Y) with an open steel door,
    camouflage paint outside, earth banked against the sides and back."""
    rng = random.Random(667)
    mb = MB()
    cols = Cols()
    X, Y0, Y1, H = 4.0, -3.5, 3.5, 2.7
    room = (-2.4, -2.0, 0.0, 2.4, 1.9, 1.95)
    outer = bm_box_minmax(-X, Y0, -0.4, X, Y1, H, bevel=0.06, segs=1)
    body = boolean(outer, [bm_box_minmax(*room)])
    # stepped embrasure: throat, then three widening anti-ricochet steps towards the face
    zc = 1.0
    cuts = [bm_box_minmax(-0.55, Y0 - 0.2, zc - 0.28, 0.55, room[1] + 0.1, zc + 0.28)]
    for k, (w, h, dy) in enumerate(((1.9, 0.75, 1.25), (2.6, 0.95, 0.85), (3.3, 1.15, 0.45))):
        cuts.append(bm_box_minmax(-w / 2, Y0 - 0.2, zc - h / 2, w / 2, Y0 + dy, zc + h / 2))
    for c in cuts:
        body = boolean(body, [c])
    # rear entrance corridor (offset to the east), and a vent shaft
    ex = 1.6
    body = boolean(body, [bm_box_minmax(ex - 0.5, room[4] - 0.1, 0.0, ex + 0.5, Y1 + 0.3, 2.0)])
    body = boolean(body, [bm_box_minmax(-1.8, 0.8, room[5] - 0.1, -1.55, 1.05, H + 0.2)])
    rx0, ry0, rz0, rx1, ry1, rz1 = room
    inside = lambda c: (rx0 - 0.02 <= c.x <= rx1 + 0.02 and ry0 - 0.02 <= c.y <= ry1 + 0.02 and c.z <= rz1 + 0.02) or \
        (abs(c.x - ex) <= 0.52 and c.y > ry1 - 0.2 and c.z < 2.02 and abs(abs(c.x - ex) - 0.5) < 0.03 or (abs(c.x - ex) < 0.5 and abs(c.z - 2.0) < 0.03))
    parts_ = split_by(body, lambda f: "in" if inside(f.calc_center_median()) else "out")
    if "out" in parts_:
        mb.add_bm(parts_["out"], "ConcreteCamo", scale=0.15, off=roff(rng))
    if "in" in parts_:
        mb.add_bm(parts_["in"], "Concrete", scale=0.5, off=roff(rng))
    # embrasure visor (Schartendecke) and gun-room floor
    mb.add_bm(bm_box_minmax(-2.3, Y0 - 0.7, zc + 0.75, 2.3, Y0 + 0.2, H - 0.35, bevel=0.05), "ConcreteCamo", scale=0.15, off=roff(rng))
    mb.add_bm(geo.bm_quad((rx0, ry0, 0.02), (rx1, ry0, 0.02), (rx1, ry1, 0.02), (rx0, ry1, 0.02)), "Concrete", scale=0.5)
    mb.add_bm(geo.bm_quad((ex - 0.5, ry1, 0.02), (ex + 0.5, ry1, 0.02), (ex + 0.5, Y1 + 0.3, 0.02), (ex - 0.5, Y1 + 0.3, 0.02)), "Concrete", scale=0.5)
    # gun pedestal (empty mount ring) and ready-ammunition niches
    mb.add_bm(lathe([(0.0, 0.0), (0.55, 0.0), (0.55, 0.35), (0.45, 0.4), (0.0, 0.4)], segs=20), "Concrete", scale=0.5,
              matrix=Matrix.Translation((0, -0.6, 0.02)))
    mb.add_bm(lathe([(0.32, 0.4), (0.36, 0.4), (0.36, 0.48), (0.32, 0.48), (0.32, 0.4)], segs=20, cap_top=False, cap_bottom=False),
              "Metal_grey", scale=2.0, matrix=Matrix.Translation((0, -0.6, 0.02)))
    for x in (-2.38, 2.38):
        mb.add_bm(bm_box_minmax(x - 0.03, 0.2, 0.5, x + 0.03, 1.4, 1.2), "Void")
    # steel door, swung open against the corridor wall, on a frame
    dy = room[4] + 0.15
    mb.add_bm(bm_box_minmax(ex - 0.5, dy - 0.06, 0.0, ex - 0.43, dy + 0.06, 1.95), "Metal_grey", scale=2.0)
    mb.add_bm(bm_box_minmax(ex + 0.43, dy - 0.06, 0.0, ex + 0.5, dy + 0.06, 1.95), "Metal_grey", scale=2.0)
    leaf = bm_box_minmax(0.0, -0.035, 0.03, 0.86, 0.035, 1.9)
    mb.add_bm(leaf, "Metal_grey", scale=1.0, matrix=Matrix.Translation((ex - 0.47, dy + 0.06, 0)) @ Matrix.Rotation(math.radians(-100), 4, "Z"))
    for zz in (0.35, 1.55):
        mb.add_bm(bm_box_minmax(0.05, -0.05, zz - 0.04, 0.8, -0.035, zz + 0.04), "Metal_grey", scale=1.0,
                  matrix=Matrix.Translation((ex - 0.47, dy + 0.06, 0)) @ Matrix.Rotation(math.radians(-100), 4, "Z"))
    # vent pipe cowl on the roof, a few sandbags on the roof edge
    mb.add_bm(lathe([(0.0, H), (0.14, H), (0.14, H + 0.45), (0.22, H + 0.5), (0.22, H + 0.62), (0.0, H + 0.64)], segs=12), "Metal_grey",
              scale=2.0, matrix=Matrix.Translation((-1.675, 0.925, 0)))
    roof_mb = MB()
    sandbag_run(roof_mb, Cols(), (-3.2, Y0 + 0.5, H), (-1.6, Y0 + 0.5, H), 2, rng, double=False)
    sandbag_run(roof_mb, Cols(), (1.6, Y0 + 0.5, H), (3.2, Y0 + 0.5, H), 2, rng, double=False)
    from common import mb_merge
    mb_merge(mb, roof_mb)
    # banked earth: a heightfield round the block, clear in front of the embrasure and at the entrance
    step = 0.5
    xs = [-7.5 + i * step for i in range(31)]
    ys = [-5.0 + j * step for j in range(24)]

    def h(x, y):
        dx = max(0.0, abs(x) - X)
        dyb = max(0.0, y - Y1)
        d = math.hypot(dx, dyb)
        front = min(1.0, max(0.0, (y - Y0 + 0.3) / 2.2))
        hh = (2.3 - 0.62 * d) * front
        if y > Y1 - 0.01 and abs(x - ex) < 0.8 + dyb * 0.3:
            hh = min(hh, 0.0 + max(0.0, (abs(x - ex) - 0.8 - dyb * 0.3) * 2.0))
        n = 0.12 * math.sin(x * 1.7 + y * 0.9) * math.sin(y * 1.3 - x * 0.5) + 0.05 * math.sin(x * 4.1 + y * 3.3)
        return max(0.0, hh + (n if hh > 0.05 else 0.0))

    em = bmesh.new()
    V = {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            V[i, j] = (x, y, h(x, y))
    hull_pts = {"W": [], "E": [], "N": []}
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            q = [V[i, j], V[i + 1, j], V[i + 1, j + 1], V[i, j + 1]]
            if all(p[2] <= 0.001 for p in q):
                continue
            cx = sum(p[0] for p in q) / 4
            cy = sum(p[1] for p in q) / 4
            if abs(cx) < X and Y0 < cy < Y1:
                continue
            em.faces.new([em.verts.new((p[0], p[1], p[2] - 0.02)) for p in q])
            key = "N" if (abs(cx) < X and cy > Y1) else ("W" if cx < 0 else "E")
            hull_pts[key] += [Vector(p) for p in q]
    bmesh.ops.remove_doubles(em, verts=em.verts, dist=1e-4)
    mb.add_bm(em, "Mud", uv=lambda co, n: (co.x * 0.5, co.y * 0.5), smooth=True, smooth_angle=60)
    for k, pts in hull_pts.items():
        if pts:
            pts = pts + [Vector((p.x, p.y, 0.0)) for p in pts]
            cols.hull(f"Earth{k}", pts)
    # collision: walls (the room and corridor stay open), roof, visor
    cols.box("WallFront", -X, Y0, -0.4, X, room[1], H)
    cols.box("WallW", -X, room[1], -0.4, room[0], Y1, H)
    cols.box("WallE", room[3], room[1], -0.4, X, room[4], H)
    cols.box("WallBackW", room[0], room[4], -0.4, ex - 0.5, Y1, H)
    cols.box("WallBackE", ex + 0.5, room[4], -0.4, X, Y1, H)
    cols.box("Roof", room[0], room[1], room[5], room[3], room[4], H)
    cols.box("CorridorRoof", ex - 0.5, room[4], 2.0, ex + 0.5, Y1, H)
    cols.box("Visor", -2.3, Y0 - 0.7, zc + 0.75, 2.3, Y0, H - 0.35)
    cols.box("Pedestal", -0.55, -1.15, 0, 0.55, -0.05, 0.42)
    ob = mb.build("BunkerAtlantic")
    pv = [dict(elev=14.0, azim=-30.0, dist_mul=0.75, ground="grass_winter"),
          dict(suffix="_rear", elev=20.0, azim=150.0, dist_mul=0.7, ground="grass_winter")]
    return dict(visual=[ob], cols=cols.build(), tris=mb.tri_count(), pv=pv, note="embrasure -Y, entrance +Y (x=+1.6)")


# =============================================================== searchlight
def searchlight_60cm():
    """Flakscheinwerfer-style 60 cm searchlight: tripod, turntable, U-fork, mirror drum with front glass,
    rear lamp housing. Lens aims along -Y. Empty LightMount at the lens centre."""
    rng = random.Random(60)
    mb = MB()
    P = "Metal_grey"
    zc = 1.3                      # trunnion height
    r = 0.36
    yl, yr = -0.42, 0.38          # drum front / back
    # tripod
    for k in range(3):
        a = PI / 2 + 2 * PI * k / 3
        foot = Vector((math.cos(a) * 0.85, math.sin(a) * 0.85, 0.0))
        mb.add_bm(cyl_between(Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.72)), foot + Vector((0, 0, 0.04)), 0.032, 8), P, scale=2.0)
        mb.add_bm(bm_box(foot.x, foot.y, 0.02, 0.16, 0.16, 0.04), P, scale=2.0)
        mid = foot * 0.45 + Vector((0, 0, 0.36))
        mb.add_bm(cyl_between(mid, Vector((0, 0, 0.35)), 0.016, 6), P, scale=2.0)
    mb.add_bm(lathe([(0.0, 0.3), (0.06, 0.3), (0.06, 0.75), (0.1, 0.78), (0.1, 0.85), (0.0, 0.85)], segs=12), P, scale=2.0)
    # turntable and fork
    mb.add_bm(lathe([(0.0, 0.85), (0.3, 0.85), (0.3, 0.92), (0.26, 0.96), (0.0, 0.96)], segs=24), P, scale=2.0)
    for s in (-1, 1):
        x = s * (r + 0.07)
        mb.add_bm(bm_box_minmax(x - 0.035, -0.09, 0.95, x + 0.035, 0.09, zc + 0.06), P, scale=2.0)
        mb.add_bm(bm_box_minmax(min(0, x), -0.09, 0.93, max(0, x), 0.09, 1.0), P, scale=2.0)
        mb.add_bm(cyl_between(Vector((x - s * 0.05, 0, zc)), Vector((x + s * 0.06, 0, zc)), 0.06, 12), P, scale=2.0)
        mb.add_bm(cyl_between(Vector((x + s * 0.06, 0, zc)), Vector((x + s * 0.09, 0, zc)), 0.075, 12), P, scale=2.0)   # clamp wheel
        for k in range(6):
            a = 2 * PI * k / 6
            mb.add_bm(cyl_between(Vector((x + s * 0.09, 0, zc)), Vector((x + s * 0.09, math.cos(a) * 0.12, zc + math.sin(a) * 0.12)),
                                  0.008, 4), P, scale=2.0)
    # elevation handwheel on the left of the fork
    hx = -(r + 0.07) - 0.2
    mb.add_bm(cyl_between(Vector((-(r + 0.1), 0.05, 1.05)), Vector((hx, 0.05, 1.05)), 0.015, 6), P, scale=2.0)
    ring = [Vector((hx, 0.05 + 0.1 * math.cos(2 * PI * k / 16), 1.05 + 0.1 * math.sin(2 * PI * k / 16))) for k in range(17)]
    mb.add_bm(tube(ring, 0.012, 5), P, scale=2.0)
    # drum (along Y), front bezel, glass with vertical strips, rear cover, lamp housing, chimney, handles
    drum = lathe([(r, 0.0), (r, yr - yl)], segs=36, cap_top=False, cap_bottom=False)
    M = Matrix.Translation((0, yl, zc)) @ Matrix.Rotation(-PI / 2, 4, "X")
    mb.add_bm(drum, P, scale=2.0, matrix=M, smooth=True, smooth_angle=30)
    inner = lathe([(r - 0.012, 0.0), (r - 0.012, 0.15)], segs=36, cap_top=False, cap_bottom=False)
    bmesh.ops.reverse_faces(inner, faces=inner.faces)
    mb.add_bm(inner, "Reflector", scale=2.0, matrix=M, smooth=True)
    bez = lathe([(r - 0.03, 0.0), (r + 0.035, 0.0), (r + 0.035, 0.06), (r - 0.03, 0.06), (r - 0.03, 0.0)], segs=36, cap_top=False,
                cap_bottom=False)
    mb.add_bm(bez, P, scale=2.0, matrix=Matrix.Translation((0, yl - 0.03, zc)) @ Matrix.Rotation(-PI / 2, 4, "X"), smooth=True)
    glass = geo.bm_cyl(r - 0.02, r - 0.02, 0.004, segs=36)
    mb.add_bm(glass, "Lens", matrix=Matrix.Translation((0, yl + 0.0, zc)) @ Matrix.Rotation(PI / 2, 4, "X"))
    for k in range(-6, 7):
        x = k * 0.05
        hz = math.sqrt(max((r - 0.03) ** 2 - x * x, 0.0))
        mb.add_bm(bm_box_minmax(x - 0.004, yl - 0.012, zc - hz, x + 0.004, yl - 0.004, zc + hz), P, scale=2.0)
    mirror = lathe([(0.0, 0.0), (r * 0.6, 0.03), (r - 0.02, 0.1), (r - 0.02, 0.105), (0.0, 0.105)], segs=32)
    mb.add_bm(mirror, "Reflector", smooth=True, matrix=Matrix.Translation((0, yr - 0.05, zc)) @ Matrix.Rotation(PI / 2, 4, "X"))
    back = lathe([(r + 0.01, 0.0), (r + 0.01, 0.04), (r * 0.8, 0.14), (r * 0.35, 0.2), (0.0, 0.21)], segs=36)
    mb.add_bm(back, P, scale=2.0, smooth=True, smooth_angle=40, matrix=Matrix.Translation((0, yr, zc)) @ Matrix.Rotation(-PI / 2, 4, "X"))
    mb.add_bm(bm_box_minmax(-0.12, -0.15, zc + r - 0.02, 0.12, 0.15, zc + r + 0.12, bevel=0.01), P, scale=2.0)
    mb.add_bm(lathe([(0.0, 0.0), (0.07, 0.0), (0.07, 0.12), (0.11, 0.14), (0.11, 0.2), (0.0, 0.21)], segs=12), P, scale=2.0,
              matrix=Matrix.Translation((0, 0.0, zc + r + 0.12)))
    mb.add_bm(lathe([(0.0, 0.0), (0.09, 0.0), (0.09, 0.28), (0.0, 0.3)], segs=14), P, scale=2.0,
              matrix=Matrix.Translation((0, yr + 0.2, zc)) @ Matrix.Rotation(-PI / 2, 4, "X"))
    for s in (-1, 1):
        mb.add_bm(tube([Vector((s * 0.2, yr + 0.15, zc + 0.32)), Vector((s * 0.2, yr + 0.32, zc + 0.3)),
                        Vector((s * 0.2, yr + 0.32, zc + 0.12)), Vector((s * 0.2, yr + 0.15, zc + 0.12))], 0.012, 5), P, scale=2.0)
    for ang in (0.6, 2.5):
        mb.add_bm(bm_box_minmax(-0.03, yl + 0.05, zc - 0.03, 0.03, yl + 0.1, zc + 0.03), P, scale=2.0,
                  matrix=Matrix.Translation((0, 0, zc)) @ Matrix.Rotation(ang, 4, "Y") @ Matrix.Translation((0, 0, -zc)) @
                  Matrix.Translation((r + 0.01, 0, 0)))
    # cable to the generator, coiled on the ground
    pts = [Vector((0.0, 0.1, 0.9)), Vector((0.1, 0.3, 0.6)), Vector((0.3, 0.6, 0.2)), Vector((0.6, 0.9, 0.03))]
    for k in range(20):
        a = k * 0.6
        pts.append(Vector((0.9 + 0.3 * math.cos(a), 1.1 + 0.3 * math.sin(a), 0.03 + 0.012 * (k % 3))))
    mb.add_bm(tube(pts, 0.012, 5), "BlackPaint", scale=2.0)
    ob = mb.build("Searchlight60cm")
    lm = geo.empty("LightMount", (0.0, yl - 0.01, zc))
    cols = Cols()
    cols.box("Drum", -r - 0.18, yl - 0.05, zc - r - 0.05, r + 0.18, yr + 0.5, zc + r + 0.35)
    cols.box("Stand", -0.3, -0.3, 0.0, 0.3, 0.3, 0.95)
    pv = [dict(elev=10.0, azim=-35.0, dist_mul=0.9, ground="grass_winter"), dict(suffix="_rear", elev=15.0, azim=140.0, dist_mul=0.9,
                                                                             ground="grass_winter")]
    return dict(visual=[ob], cols=cols.build(), empties=[lm], tris=mb.tri_count(), pv=pv,
                note=f"LightMount at (0, {yl - 0.01:.2f}, {zc}) aiming -Y")


# ================================================================= wire fence
def _angle_iron(mb, x, y, z0, z1, rng, lean=0.0, mat="Iron"):
    """L-section picket (45 x 45 x 6 mm) with its heel at (x, y)."""
    s, t = 0.045, 0.006
    M = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(lean, 4, "X") @ Matrix.Rotation(PI / 4, 4, "Z")
    mb.add_bm(bm_box_minmax(-s / 2, -s / 2, z0, s / 2, -s / 2 + t, z1), mat, scale=2.0, matrix=M)
    mb.add_bm(bm_box_minmax(-s / 2, -s / 2 + t, z0, -s / 2 + t, s / 2, z1), mat, scale=2.0, matrix=M)


def wire_fence_5m():
    """5 m of barbed-wire fence on angle-iron pickets, tiling along X (ends at x = +-2.5)."""
    rng = random.Random(5)
    mb = MB()
    from props import _barbed
    posts = (-1.25, 1.25)
    H = 1.45
    for px in posts:
        _angle_iron(mb, px, 0.0, -0.35, H + 0.05, rng, lean=rng.uniform(-0.03, 0.03))
        for zz in (0.18, 0.48, 0.78, 1.08, 1.38):
            mb.add_bm(tube([(px - 0.03, -0.03, zz), (px + 0.03, 0.03, zz + 0.02), (px - 0.03, 0.03, zz + 0.01)], 0.0018, 3), "Iron",
                      scale=4.0)
    for k, zz in enumerate((0.18, 0.48, 0.78, 1.08, 1.38)):
        pts = []
        n = 21
        for i in range(n):
            x = -2.5 + 5.0 * i / (n - 1)
            dpost = min(abs(x - p) for p in posts + (-3.75, 3.75))
            sag = 0.035 * (1 - (dpost / 1.25 - 1) ** 2) if dpost < 1.25 else 0.0
            sag = 0.035 * math.sin(PI * ((x + 2.5) % 2.5) / 2.5 + PI / 2) ** 2 * 0 + 0.03 * (math.cos(2 * PI * (x - 1.25) / 2.5) * -0.5 + 0.5)
            pts.append((x, 0.02 * math.sin(x * 2 + k), zz - sag))
        _barbed(pts, rng, mb, barb_step=0.13)
    # diagonal strand in each bay (tiles: one bay centred, halves at the ends)
    _barbed([(-1.25, 0.01, 0.2), (0.0, 0.0, 0.8), (1.25, 0.01, 1.35)], rng, mb, barb_step=0.15)
    ob = mb.build("WireFence5m")
    cols = Cols()
    cols.box("Fence", -2.5, -0.06, 0.0, 2.5, 0.06, H)
    pv = [dict(elev=10.0, azim=-25.0, dist_mul=0.7, ground="mud")]
    return dict(visual=[ob], cols=cols.build(), tris=mb.tri_count(), pv=pv, note="tiles along X, posts at x=+-1.25")


# =============================================================== mine sign
def _skull(mb, F, a, z, d, s=1.0):
    """Painted skull and crossbones: black shapes with white sockets/nose/teeth, flat on the board."""
    circ = lambda ca, cz, r, n=20: [(ca + r * math.cos(2 * PI * i / n), cz + r * math.sin(2 * PI * i / n)) for i in range(n)]
    # crossbones behind
    for sg in (-1, 1):
        ang = sg * math.radians(35)
        ca, sa = math.cos(ang), math.sin(ang)
        L, w = 0.11 * s, 0.012 * s
        poly = [(a + ca * (-L) - sa * (-w), z - 0.02 * s + sa * (-L) + ca * (-w)), (a + ca * L - sa * (-w), z - 0.02 * s + sa * L + ca * (-w)),
                (a + ca * L - sa * w, z - 0.02 * s + sa * L + ca * w), (a + ca * (-L) - sa * w, z - 0.02 * s + sa * (-L) + ca * w)]
        mb.add_bm(face_poly(F, poly, d), "SignBlack")
        for e in (-1, 1):
            for o in (-1, 1):
                ex = a + ca * e * L - sa * o * w * 1.2
                ez = z - 0.02 * s + sa * e * L + ca * o * w * 1.2
                mb.add_bm(face_poly(F, circ(ex, ez, 0.014 * s, 10), d), "SignBlack")
    d2 = d + 0.0015
    mb.add_bm(face_poly(F, circ(a, z + 0.02 * s, 0.055 * s, 24), d2), "SignBlack")             # cranium
    mb.add_bm(face_poly(F, [(a - 0.035 * s, z - 0.035 * s), (a + 0.035 * s, z - 0.035 * s), (a + 0.03 * s, z + 0.0),
                           (a - 0.03 * s, z + 0.0)], d2), "SignBlack")                          # jaw
    d3 = d2 + 0.0015
    for e in (-1, 1):
        mb.add_bm(face_poly(F, circ(a + e * 0.022 * s, z + 0.018 * s, 0.014 * s, 14), d3), "SignWhite")
    mb.add_bm(face_poly(F, [(a, z + 0.006 * s), (a + 0.008 * s, z - 0.008 * s), (a - 0.008 * s, z - 0.008 * s)], d3), "SignWhite")
    for k in range(-2, 3):
        mb.add_bm(face_poly(F, [(a + k * 0.012 * s - 0.0025 * s, z - 0.032 * s), (a + k * 0.012 * s + 0.0025 * s, z - 0.032 * s),
                               (a + k * 0.012 * s + 0.0025 * s, z - 0.018 * s), (a + k * 0.012 * s - 0.0025 * s, z - 0.018 * s)], d3),
                  "SignWhite")


def minefield_sign():
    """'ACHTUNG MINEN' on a weathered white board on a stake, with a painted skull (no other insignia)."""
    rng = random.Random(13)
    mb = MB()
    lean = math.radians(4)
    M = Matrix.Rotation(lean, 4, "Y")
    sub = MB()
    sub.add_bm(bm_box_minmax(-0.035, -0.035, -0.45, 0.035, 0.035, 1.05), "Wood_grey", scale=1.0)
    sub.add_bm(bm_box_minmax(-0.3, -0.055, 0.62, 0.3, -0.035, 1.04, bevel=0.004), "Paint_cream", scale=1.0)
    for z in (0.7, 0.96):
        sub.add_bm(bm_box_minmax(-0.012, -0.06, z - 0.012, 0.012, -0.055, z + 0.012), "Iron", scale=2.0)
    F = WFace((0, -0.055, 0), (0, -1, 0))
    text(sub, F, "ACHTUNG", 0.0, 0.975, 0.0, 0.075, "SignBlack", extrude=0.0008, spacing=1.1)
    _skull(sub, F, 0.0, 0.85, 0.0008, s=1.0)
    text(sub, F, "MINEN", 0.0, 0.69, 0.0, 0.085, "SignBlack", extrude=0.0008, spacing=1.15)
    from common import mb_merge
    mb_merge(mb, sub, M)
    ob = mb.build("MinefieldSign")
    cols = Cols()
    cols.box("Stake", -0.05, -0.05, 0.0, 0.05, 0.05, 0.62)
    cols.box("Board", -0.3, -0.08, 0.62, 0.32, 0.0, 1.06)
    pv = [dict(elev=6.0, azim=-15.0, dist_mul=1.2, ground="mud", target=(0.0, 0.0, 0.75))]
    return dict(visual=[ob], cols=cols.build(), tris=mb.tri_count(), pv=pv)
