"""Harbour pieces: quay_10m (tiling granite quay), fishing_boat_a (Breton sardine chaloupe), dinghy,
fish_hall (la criée)."""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box, bm_box_minmax, bm_cyl
from parts import Frame, roff, text
from common import Cols, WFace, cyl_between, gable_roof, lathe, tube, T, R

PI = math.pi


# ====================================================================== quay
def quay_10m():
    """10 m along Y (tiles end to end at y = +-5), 8 m deep along X. Paved top at z = 0 from the land
    edge (x = -4) to the granite coping; the battered outer face (sea side, +X) drops to the seabed at
    z = -4.5. Ends are left open so tiled segments join without internal faces."""
    rng = random.Random(10)
    mb = MB()
    L, x_land, x_edge = 10.0, -4.0, 4.0
    zb = -4.5
    batter = 0.45                         # the face leans back: foot is 0.45 further out than the top
    cw = 0.65                             # coping width
    # paving (setts, 2 m tile, UVs in world metres so tiles line up across segments)
    top = geo.bm_quad((x_land, -L / 2, 0), (x_edge - cw, -L / 2, 0), (x_edge - cw, L / 2, 0), (x_land, L / 2, 0))
    mb.add_bm(top, "Setts", uv=lambda co, n: (co.x * 0.5, co.y * 0.5))
    # coping: 8 dressed granite blocks, flush with the paving, overhanging the face slightly
    nb = 8
    for k in range(nb):
        y0 = -L / 2 + k * L / nb
        mb.add_bm(bm_box_minmax(x_edge - cw + 0.005, y0 + 0.004, -0.38, x_edge + 0.08, y0 + L / nb - 0.004, 0.0, bevel=0.02, segs=2),
                  "Granite", off=roff(rng))
    # face blocks in coursed rows, following the batter
    rows = [(-0.38, -1.0), (-1.0, -1.6), (-1.6, -2.25), (-2.25, -2.85), (-2.85, -3.45), (-3.45, -4.0), (-4.0, -4.5)]
    xf = lambda z: x_edge + batter * (-z / -zb)     # face line
    for r, (zt, zbot) in enumerate(rows):
        bl = 1.25
        off = (r % 2) * 0.62 + rng.uniform(-0.05, 0.05) * 0
        mat = "Ashlar" if zbot > -1.7 else ("AshlarWet" if zbot > -3.5 else "AshlarWeed")
        k = -1
        while True:
            y0 = -L / 2 + off + k * bl
            y1 = y0 + bl
            k += 1
            if y0 >= L / 2:
                break
            ya, yb = max(y0, -L / 2), min(y1, L / 2)
            if yb - ya < 0.05:
                continue
            proud = rng.uniform(0.0, 0.03)
            xa = xf(zbot) + proud
            xt = xf(zt) + proud
            bm = bmesh.new()
            vs = [bm.verts.new(p) for p in ((xa - 0.6, ya + 0.008, zbot + 0.008), (xa, ya + 0.008, zbot + 0.008), (xt, ya + 0.008, zt - 0.008),
                                             (xt - 0.6, ya + 0.008, zt - 0.008))]
            ws = [bm.verts.new(v.co + Vector((0, yb - ya - 0.016, 0))) for v in vs]
            bm.faces.new(vs)
            bm.faces.new(list(reversed(ws)))
            for i in range(4):
                j = (i + 1) % 4
                bm.faces.new((vs[i], vs[j], ws[j], ws[i]))
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bmesh.ops.bevel(bm, geom=[e for e in bm.edges], offset=0.025, segments=1, affect="EDGES", clamp_overlap=True)
            mb.add_bm(bm, mat, scale=0.5, off=roff(rng))
    # mortar backing plane behind the blocks (closes the joints)
    back = geo.bm_quad((xf(zb) - 0.02, -L / 2, zb), (xf(zb) - 0.02, L / 2, zb), (x_edge - 0.02, L / 2, -0.38), (x_edge - 0.02, -L / 2, -0.38))
    bmesh.ops.recalc_face_normals(back, faces=back.faces)
    f = back.faces[0]
    f.normal_update()
    if f.normal.x < 0:
        bmesh.ops.reverse_faces(back, faces=[f])
    mb.add_bm(back, "GraniteWet", scale=0.5)
    # seabed apron of rubble at the foot
    for k in range(9):
        y = -L / 2 + 0.6 + k * 1.1 + rng.uniform(-0.2, 0.2)
        from props import noisy_stone
        st = noisy_stone(xf(zb) + 0.35 + rng.uniform(0, 0.4), y, zb + 0.08, rng.uniform(0.5, 0.9), rng.uniform(0.5, 0.9),
                         rng.uniform(0.25, 0.45), rng, rough=0.06, rot=0.4)
        mb.add_bm(st, "AshlarWeed", off=roff(rng))
    # cast-iron bollard (bitte d'amarrage)
    bx, by = x_edge - 0.75, -1.2
    prof = [(0.0, 0.0), (0.2, 0.0), (0.2, 0.06), (0.16, 0.1), (0.13, 0.35), (0.12, 0.5), (0.17, 0.56), (0.2, 0.62),
            (0.19, 0.68), (0.0, 0.7)]
    mb.add_bm(lathe(prof, segs=20), "Iron", scale=2.0, smooth=True, smooth_angle=50, matrix=Matrix.Translation((bx, by, 0.0)))
    mb.add_bm(lathe([(0.0, 0.0), (0.32, 0.0), (0.3, 0.04), (0.0, 0.05)], segs=20), "Iron", scale=2.0,
              matrix=Matrix.Translation((bx, by, 0.0)))
    # mooring ring on a staple let into the coping edge, hanging on the face
    ry = 2.5
    mb.add_bm(bm_box_minmax(x_edge - 0.05, ry - 0.06, -0.08, x_edge + 0.1, ry + 0.06, 0.004), "Iron", scale=2.0)
    ring = [(x_edge + 0.11 + 0.0 * math.cos(2 * PI * i / 20), ry + 0.17 * math.sin(2 * PI * i / 20),
             -0.22 + 0.17 * math.cos(2 * PI * i / 20)) for i in range(21)]
    mb.add_bm(tube(ring, 0.02, 6), "Iron", scale=2.0, smooth=True)
    # iron ladder down the face
    ly = -3.5
    for s in (-0.22, 0.22):
        pts = [(xf(z) + 0.12, ly + s, z) for z in (0.05, -1.0, -2.0, -3.0, -4.3)]
        mb.add_bm(tube(pts, 0.025, 6), "Iron", scale=2.0)
    for k in range(14):
        z = -0.25 - k * 0.3
        mb.add_bm(tube([(xf(z) + 0.12, ly - 0.22, z), (xf(z) + 0.12, ly + 0.22, z)], 0.016, 5), "Iron", scale=2.0)
        if k % 4 == 0:
            mb.add_bm(tube([(xf(z) - 0.02, ly - 0.22, z), (xf(z) + 0.12, ly - 0.22, z)], 0.014, 4), "Iron", scale=2.0)
            mb.add_bm(tube([(xf(z) - 0.02, ly + 0.22, z), (xf(z) + 0.12, ly + 0.22, z)], 0.014, 4), "Iron", scale=2.0)
    mb.add_bm(tube([(x_edge - 0.25, ly - 0.22, 0.0), (x_edge - 0.25, ly - 0.22, 0.8), (x_edge + 0.12, ly - 0.22, 0.95),
                    (xf(0.0) + 0.12, ly - 0.22, 0.05)], 0.025, 6), "Iron", scale=2.0)
    mb.add_bm(tube([(x_edge - 0.25, ly + 0.22, 0.0), (x_edge - 0.25, ly + 0.22, 0.8), (x_edge + 0.12, ly + 0.22, 0.95),
                    (xf(0.0) + 0.12, ly + 0.22, 0.05)], 0.025, 6), "Iron", scale=2.0)
    ob = mb.build("Quay10m")
    cols = Cols()
    cols.box("QuayBody", x_land, -L / 2, zb, x_edge + 0.08, L / 2, 0.0)
    cols.hull("QuayFace", [Vector((x_edge, y, 0)) for y in (-L / 2, L / 2)] + [Vector((xf(zb), y, zb)) for y in (-L / 2, L / 2)] +
              [Vector((x_edge - 1, y, 0)) for y in (-L / 2, L / 2)] + [Vector((x_edge - 1, y, zb)) for y in (-L / 2, L / 2)])
    cols.box("Bollard", bx - 0.2, by - 0.2, 0, bx + 0.2, by + 0.2, 0.7)
    pv = [dict(elev=18.0, azim=55.0, dist_mul=0.75, ground=None, target=(1.5, 0.0, -2.0)),
          dict(suffix="_top", elev=30.0, azim=-35.0, dist_mul=0.6, ground=None, target=(1.0, 0.0, -1.0))]
    return dict(visual=[ob], cols=cols.build(), tris=mb.tri_count(), pv=pv, note="sea face at +X")


# ===================================================================== hulls
def _hull_grid(L, B, sheer, keel, hb, nu=36, nv=10, flare=0.7):
    """Right-hand (x >= 0) hull surface grid P[i][j]: i along the length from stern (y=+L/2) to bow (y=-L/2),
    j around the section from keel (0) to sheer (nv)."""
    P = []
    for i in range(nu + 1):
        u = i / nu
        y = L / 2 - u * L
        zk, zs, h = keel(u), sheer(u), max(hb(u), 0.015)
        row = []
        for j in range(nv + 1):
            th = (j / nv) * PI / 2
            half = h * math.sin(th) ** flare
            z = zk + (zs - zk) * (1 - math.cos(th)) ** 0.85
            row.append(Vector((half, y, z)))
        P.append(row)
    return P


def _strip(mb, rows_a, rows_b, mat, flip=False, uv_scale=1.0):
    """Quad strip between two polylines lists over i (rows_a[i] -> rows_b[i])."""
    bm = bmesh.new()
    lay = bm.loops.layers.uv.new("UVMap")
    for i in range(len(rows_a) - 1):
        q = [rows_a[i], rows_a[i + 1], rows_b[i + 1], rows_b[i]]
        if flip:
            q = list(reversed(q))
        f = bm.faces.new([bm.verts.new(p) for p in q])
        for l in f.loops:
            l[lay].uv = (l.vert.co.z * uv_scale + l.vert.co.x * 0.3, l.vert.co.y * uv_scale)
    mb.add_bm(bm, mat, uv="keep")


def _hull_surface(mb, P, strake_from, below_mat, strake_mat, mirror=True):
    """Outer planking both sides. UV: girth (z plus a little x) across the planks, length along them."""
    nu, nv = len(P) - 1, len(P[0]) - 1
    uvf = lambda co, n: (co.z * 0.9 + abs(co.x) * 0.4, co.y * 0.5)
    for side in ((1, -1) if mirror else (1,)):
        for j in range(nv):
            mat = strake_mat if j >= strake_from else below_mat
            a = [Vector((P[i][j].x * side, P[i][j].y, P[i][j].z)) for i in range(nu + 1)]
            b = [Vector((P[i][j + 1].x * side, P[i][j + 1].y, P[i][j + 1].z)) for i in range(nu + 1)]
            bm = bmesh.new()
            for i in range(nu):
                q = [a[i], a[i + 1], b[i + 1], b[i]] if side > 0 else [a[i + 1], a[i], b[i], b[i + 1]]
                try:
                    bm.faces.new([bm.verts.new(p) for p in q])
                except ValueError:
                    pass
            mb.add_bm(bm, mat, uv=uvf)


def boat(L, B, sheer, keel, hb, rng, strake_mat="Paint_blue", decked=True, name="Boat", nu=36, nv=10, bulwark=0.42):
    """Generic clinker/carvel hull. Returns (mb, P, info)."""
    mb = MB()
    P = _hull_grid(L, B, sheer, keel, hb, nu, nv)
    _hull_surface(mb, P, nv - 1, "Tar", strake_mat)
    # rubbing strake under the sheer
    for side in (1, -1):
        pts = [Vector((P[i][nv - 2].x * side * 1.02 + side * 0.02, P[i][nv - 2].y, P[i][nv - 2].z)) for i in range(nu + 1)]
        mb.add_bm(tube(pts, 0.035, 5), "Wood_dark", scale=1.0)
    t = 0.06
    inner_top, inner_bot = [], []
    for i in range(nu + 1):
        s = P[i][nv]
        zd = s.z - bulwark
        # half-breadth at the deck/floor height by interpolation along the section
        col = P[i]
        hx = col[0].x
        for j in range(nv):
            if col[j].z <= zd <= col[j + 1].z:
                f = (zd - col[j].z) / max(col[j + 1].z - col[j].z, 1e-6)
                hx = col[j].x + (col[j + 1].x - col[j].x) * f
                break
        inner_top.append(Vector((max(s.x - t, 0.0), s.y, s.z)))
        inner_bot.append(Vector((max(hx - t, 0.0), s.y, zd)))
    for side in (1, -1):
        sc = lambda v: Vector((v.x * side, v.y, v.z))
        outer = [sc(P[i][nv]) for i in range(nu + 1)]
        it = [sc(v) for v in inner_top]
        ib = [sc(v) for v in inner_bot]
        _strip(mb, outer, it, "Wood_dark", flip=(side < 0))           # gunwale capping
        _strip(mb, it, ib, strake_mat if not decked else "Wood_grey", flip=(side < 0))     # bulwark inside
    # deck / floor
    deck_mat = "Wood_grey"
    _strip(mb, [Vector((-v.x, v.y, v.z)) for v in inner_bot], inner_bot, deck_mat, flip=True)
    # transom
    bm = bmesh.new()
    pts = [P[0][j] for j in range(nv + 1)] + [Vector((-P[0][j].x, P[0][j].y, P[0][j].z)) for j in range(nv, -1, -1)]
    vs = [bm.verts.new(p) for p in pts]
    try:
        f = bm.faces.new(vs)
        f.normal_update()
        if f.normal.y < 0:
            bmesh.ops.reverse_faces(bm, faces=[f])
        mb.add_bm(bm, "Tar", uv=lambda co, n: (co.x * 0.5, co.z * 0.5))
    except ValueError:
        bm.free()
    mb.add_bm(bm_box_minmax(-P[0][nv].x, P[0][nv].y - 0.005, P[0][nv - 2].z, P[0][nv].x, P[0][nv].y + 0.02, P[0][nv].z), strake_mat,
              scale=1.0)
    # keel, stem and stern posts
    keel_pts = [Vector((0, P[i][0].y, P[i][0].z - 0.06)) for i in range(nu + 1)]
    mb.add_bm(tube(keel_pts, 0.07, 4), "Tar", scale=1.0)
    stem = [Vector((0, P[nu][j].y - 0.04, P[nu][j].z)) for j in range(nv + 1)] + [Vector((0, P[nu][nv].y - 0.08, P[nu][nv].z + 0.18))]
    mb.add_bm(tube(stem, 0.06, 4), "Tar", scale=1.0)
    return mb, P, dict(inner_bot=inner_bot, inner_top=inner_top)


def _lump(mb, mat, center, size, rng, segs=(14, 8), squash=1.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0)
    ph = [rng.uniform(0, 6) for _ in range(4)]
    for v in bm.verts:
        c = v.co
        n = 0.12 * math.sin(c.x * 5 + ph[0]) * math.sin(c.y * 4 + ph[1]) + 0.08 * math.sin(c.z * 7 + ph[2])
        v.co = Vector((c.x * size[0] * (1 + n), c.y * size[1] * (1 + n), max(c.z, -0.3) * size[2] * (1 + n)))
    mb.add_bm(bm, mat, scale=1.0, smooth=True, smooth_angle=80, matrix=Matrix.Translation(center), off=roff(rng))


def fishing_boat_a():
    """Breton sardine chaloupe, ~9 m: tarred hull, blue sheer strake, short mainmast with the tan-bark
    lugsail furled on its yard, blue nets with cork floats. Bow towards -Y, origin at the waterline."""
    rng = random.Random(29)
    L, B = 9.0, 3.0

    def sheer(u):
        return 0.95 + 0.42 * (u - 0.45) ** 2 / 0.3 + (0.12 if u > 0.9 else 0) * (u - 0.9) / 0.1

    def keel(u):
        return -1.25 + 0.35 * u - (0.6 * (u - 0.88) / 0.12 if u > 0.88 else 0) * -1 * 0.0 + (
            (u - 0.9) * 6.0 if u > 0.9 else 0.0)

    def hb(u):
        if u > 0.42:
            return B / 2 * max(0.0, 1 - ((u - 0.42) / 0.58) ** 2) ** 0.55
        return B / 2 * (1 - 0.42 * ((0.42 - u) / 0.42) ** 2.0)

    mb, P, info = boat(L, B, sheer, keel, hb, rng, strake_mat="Paint_blue", decked=True)
    ib = info["inner_bot"]
    zdeck = lambda y: min(v.z for v in ib if abs(v.y - y) < 0.3) if any(abs(v.y - y) < 0.3 for v in ib) else 0.6
    # fish-hold hatch and coaming amidships
    zc = zdeck(0.6)
    mb.add_bm(bm_box_minmax(-0.6, 0.0, zc - 0.05, 0.6, 1.3, zc + 0.18), "Wood_dark", scale=1.0)
    mb.add_bm(bm_box_minmax(-0.52, 0.08, zc + 0.18, 0.52, 1.22, zc + 0.2), "Void")
    for k in range(3):
        mb.add_bm(bm_box_minmax(-0.55, 0.1 + k * 0.36, zc + 0.15, 0.55, 0.42 + k * 0.36, zc + 0.22), "Wood_grey", scale=1.0)
    # mast (misaine) with a tabernacle, furled sail on its yard
    my = -2.3
    zm = zdeck(my)
    mb.add_bm(lathe([(0.12, 0.0), (0.11, 2.0), (0.085, 5.6), (0.06, 6.2), (0.0, 6.25)], segs=10), "Wood_oak", scale=1.0,
              smooth=True, matrix=Matrix.Translation((0, my, zm - 0.1)))
    mb.add_bm(bm_box_minmax(-0.18, my - 0.18, zm - 0.05, 0.18, my + 0.18, zm + 0.45), "Wood_dark", scale=1.0)
    ya0, ya1 = Vector((0.05, my + 1.6, zm + 4.6)), Vector((0.05, my - 2.2, zm + 5.9))   # the yard, peaked up
    mb.add_bm(cyl_between(ya0, ya1, 0.05, 8), "Wood_oak", scale=1.0)
    n = 18
    for k in range(n + 1):
        t = k / n
        p = ya0.lerp(ya1, t)
        r = 0.08 + 0.14 * math.sin(PI * min(1.0, t * 1.15)) + rng.uniform(-0.02, 0.02)
        if k < n:
            q = ya0.lerp(ya1, (k + 1) / n)
            r2 = 0.08 + 0.14 * math.sin(PI * min(1.0, (k + 1) / n * 1.15))
            mb.add_bm(cyl_between(p + Vector((0.0, 0, -r * 0.8)), q + Vector((0.0, 0, -r2 * 0.8)), r, 10, r1=r2), "Sail",
                      scale=2.0, smooth=True, off=roff(rng))
        if k % 4 == 2:     # gaskets
            ring = [p + Vector((math.cos(a) * (r + 0.015) * 0.0 + (r + 0.015) * math.cos(a), 0, -r * 0.8 + (r + 0.015) * math.sin(a)))
                    for a in [2 * PI * i / 10 for i in range(11)]]
            mb.add_bm(tube(ring, 0.012, 4), "Rope", scale=2.0)
    # halyard, shrouds and forestay
    top = Vector((0, my, zm + 6.0))
    for p in (Vector((0.0, my + 0.4, zm + 5.2)), ):
        mb.add_bm(tube([top, p], 0.008, 3), "Rope", scale=2.0)
    for s in (-1, 1):
        mb.add_bm(tube([top + Vector((0, 0, -0.3)), Vector((s * 1.25, my + 0.5, zm + 0.35))], 0.007, 3), "Rope", scale=2.0)
    mb.add_bm(tube([top, Vector((0, -L / 2 + 0.05, sheer(1.0) + 0.1))], 0.007, 3), "Rope", scale=2.0)
    # bowsprit
    mb.add_bm(cyl_between(Vector((0, -L / 2 + 1.2, sheer(0.95) - 0.05)), Vector((0, -L / 2 - 1.6, sheer(1.0) + 0.25)), 0.06, 8),
              "Wood_oak", scale=1.0)
    # rudder and tiller at the transom
    sy = L / 2
    rud = bmesh.new()
    rp = [(0.0, sy + 0.02, keel(0.0) - 0.05), (0.0, sy + 0.62, keel(0.0) + 0.15), (0.0, sy + 0.5, sheer(0.0) - 0.15),
          (0.0, sy + 0.1, sheer(0.0) + 0.25), (0.0, sy + 0.02, sheer(0.0) + 0.25)]
    rud.faces.new([rud.verts.new(p) for p in rp])
    bmesh.ops.solidify(rud, geom=list(rud.faces), thickness=0.06)
    bmesh.ops.translate(rud, vec=(0.03, 0, 0), verts=rud.verts)
    mb.add_bm(rud, "Tar", scale=1.0)
    mb.add_bm(cyl_between(Vector((0, sy + 0.08, sheer(0.0) + 0.2)), Vector((0.15, sy - 1.6, sheer(0.0) + 0.05)), 0.035, 6),
              "Wood_oak", scale=1.0)
    # nets heaped aft, cork floats strung along the head rope
    for (cx, cy, s) in ((0.35, 2.3, (0.75, 0.9, 0.35)), (-0.45, 2.9, (0.6, 0.7, 0.3)), (0.1, 3.4, (0.55, 0.45, 0.25))):
        _lump(mb, "Net", (cx, cy, zdeck(cy) + 0.02), s, rng)
    corks = []
    for k in range(26):
        t = k / 25
        a = 5.0 * t
        p = Vector((0.6 * math.cos(a) * (1 - 0.3 * t) - 0.05, 2.75 + 0.75 * math.sin(a) * (1 - 0.3 * t), 0.0))
        p.z = zdeck(p.y) + 0.28 + 0.12 * math.sin(a * 1.7)
        corks.append(p)
        mb.add_bm(cyl_between(p - Vector((0.035, 0, 0)), p + Vector((0.035, 0, 0)), 0.045, 8), "Cork", scale=1.0)
    mb.add_bm(tube(corks, 0.006, 3), "Rope", scale=2.0)
    # fish baskets and a pair of sweeps
    for (bx, by) in ((-0.7, -0.6), (0.75, -0.9)):
        mb.add_bm(lathe([(0.0, 0.0), (0.2, 0.0), (0.26, 0.38), (0.24, 0.4), (0.0, 0.4)], segs=12), "Wood_oak", scale=2.0,
                  matrix=Matrix.Translation((bx, by, zdeck(by))))
    for s in (-1, 1):
        mb.add_bm(cyl_between(Vector((s * 0.95, -3.0, zdeck(-1) + 0.45)), Vector((s * 0.8, 2.4, zdeck(1) + 0.45)), 0.035, 6),
                  "Wood_grey", scale=1.0)
    # registration and name, white paint
    for s in (-1, 1):
        u = 0.74
        i = int(u * (len(P) - 1))
        p = P[i][len(P[0]) - 3]
        fr = WFace((s * (p.x + 0.05), p.y, 0.0), (s, 0, 0))
        text(mb, fr, "PN 417", 0.0, p.z, 0.0, 0.18, "SignWhite", extrude=0.004, spacing=1.05)
    fr = WFace((0.0, L / 2 + 0.03, 0.0), (0, 1, 0))
    text(mb, fr, "MARIE-JOSÉ", 0.0, sheer(0.0) - 0.35, 0.0, 0.13, "SignWhite", extrude=0.003)
    text(mb, fr, "PLOUZENNEC", 0.0, sheer(0.0) - 0.55, 0.0, 0.08, "SignWhite", extrude=0.003)
    ob = mb.build("FishingBoatA")
    cols = Cols()
    hull = [p for row in P for p in (row[0], row[-1])] + [Vector((-p.x, p.y, p.z)) for row in P for p in (row[-1],)]
    cols.hull("Hull", hull)
    cols.box("Mast", -0.12, my - 0.12, zm, 0.12, my + 0.12, zm + 6.0)
    pv = [dict(elev=14.0, azim=-40.0, dist_mul=0.75, ground=None), dict(suffix="_stern", elev=20.0, azim=150.0, dist_mul=0.7, ground=None)]
    return dict(visual=[ob], cols=cols.build(), tris=mb.tri_count(), pv=pv, note="bow -Y, waterline z=0")


def dinghy():
    """3 m clinker rowing boat (annexe): cream topsides, tarred bottom, open with thwarts and oars."""
    rng = random.Random(31)
    L, B = 3.0, 1.3

    def sheer(u):
        return 0.42 + 0.25 * (u - 0.45) ** 2 / 0.3

    def keel(u):
        return -0.2 + 0.06 * u + ((u - 0.88) * 2.5 if u > 0.88 else 0.0)

    def hb(u):
        if u > 0.45:
            return B / 2 * max(0.0, 1 - ((u - 0.45) / 0.55) ** 2) ** 0.55
        return B / 2 * (1 - 0.3 * ((0.45 - u) / 0.45) ** 2.0)

    mb = MB()
    nu, nv = 24, 8
    P = _hull_grid(L, B, sheer, keel, hb, nu, nv, flare=0.6)
    _hull_surface(mb, P, 3, "Tar", "Paint_cream")
    # inside: offset shell (open boat)
    t = 0.025
    Q = [[Vector((max(p.x - t, 0.0), p.y, p.z + t * (1 - j / nv))) for j, p in enumerate(row)] for row in P]
    for side in (1, -1):
        for j in range(nv):
            a = [Vector((Q[i][j].x * side, Q[i][j].y, Q[i][j].z)) for i in range(nu + 1)]
            b = [Vector((Q[i][j + 1].x * side, Q[i][j + 1].y, Q[i][j + 1].z)) for i in range(nu + 1)]
            _strip(mb, a, b, "Wood_grey", flip=(side > 0))
        outer = [Vector((P[i][nv].x * side, P[i][nv].y, P[i][nv].z)) for i in range(nu + 1)]
        inner = [Vector((Q[i][nv].x * side, Q[i][nv].y, Q[i][nv].z)) for i in range(nu + 1)]
        _strip(mb, outer, inner, "Wood_dark", flip=(side < 0))
        mb.add_bm(tube([Vector((P[i][nv].x * side + side * 0.015, P[i][nv].y, P[i][nv].z - 0.03)) for i in range(nu + 1)], 0.022, 4),
                  "Wood_dark", scale=1.0)
    # transom
    bm = bmesh.new()
    pts = [P[0][j] for j in range(nv + 1)] + [Vector((-P[0][j].x, P[0][j].y, P[0][j].z)) for j in range(nv, -1, -1)]
    f = bm.faces.new([bm.verts.new(p) for p in pts])
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.03)
    mb.add_bm(bm, "Paint_cream", scale=1.0)
    mb.add_bm(tube([Vector((0, P[i][0].y, P[i][0].z - 0.03)) for i in range(nu + 1)], 0.03, 4), "Tar", scale=1.0)
    mb.add_bm(tube([Vector((0, P[nu][j].y - 0.02, P[nu][j].z)) for j in range(nv + 1)], 0.03, 4), "Wood_dark", scale=1.0)
    # floorboards, thwarts, knees, rowlocks, oars
    zf = keel(0.5) + 0.1
    mb.add_bm(bm_box_minmax(-0.32, -0.9, zf, 0.32, 1.1, zf + 0.025), "Wood_grey", scale=1.0)
    for (yy, w) in ((-0.55, 0.95), (0.35, 1.12), (1.15, 1.0)):
        u = (L / 2 - yy) / L
        z = sheer(u) - 0.2
        half = hb(u) - 0.05
        mb.add_bm(bm_box_minmax(-half, yy - 0.11, z - 0.03, half, yy + 0.11, z), "Wood_oak", scale=1.0)
    for s in (-1, 1):
        u = (L / 2 - 0.0) / L
        p = Vector((s * (hb(u) - 0.02), -0.05, sheer(u) + 0.0))
        mb.add_bm(bm_box_minmax(p.x - 0.015, p.y - 0.04, p.z, p.x + 0.015, p.y + 0.04, p.z + 0.09), "Iron", scale=2.0)
        z_th = sheer(0.5) - 0.2
        mb.add_bm(cyl_between(Vector((s * 0.32, -0.95, z_th + 0.03)), Vector((s * 0.22, 1.55, sheer(0.0) + 0.04)), 0.022, 6),
                  "Wood_oak", scale=1.0)
        blade = bm_box(0, 0, 0, 0.13, 0.55, 0.014)
        mb.add_bm(blade, "Wood_oak", scale=1.0, matrix=Matrix.Translation((s * 0.21, 1.8, sheer(0.0) + 0.06)) @ Matrix.Rotation(0.05, 4, "X"))
    mb.add_bm(tube([Vector((0, -L / 2 - 0.02, sheer(1.0) - 0.05)), Vector((0.1, -L / 2 + 0.4, zf + 0.12)), Vector((0.3, -L / 2 + 0.6, zf + 0.04))],
                   0.012, 4), "Rope", scale=2.0)
    ob = mb.build("Dinghy")
    cols = Cols()
    cols.hull("Hull", [p for row in P for p in (row[0], row[-1])] + [Vector((-p.x, p.y, p.z)) for row in P for p in (row[-1],)])
    pv = [dict(elev=26.0, azim=-40.0, dist_mul=0.8, ground=None)]
    return dict(visual=[ob], cols=cols.build(), tris=mb.tri_count(), pv=pv, note="bow -Y, waterline z=0")


# ================================================================= fish hall
def _crate(mb, cols, x, y, z, rng, rot=0.0, fish=False):
    w, d, h = 0.62, 0.42, 0.24
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z")
    for (x0, y0, x1, y1) in ((-w / 2, -d / 2, w / 2, -d / 2 + 0.018), (-w / 2, d / 2 - 0.018, w / 2, d / 2),
                             (-w / 2, -d / 2, -w / 2 + 0.02, d / 2), (w / 2 - 0.02, -d / 2, w / 2, d / 2)):
        for k in range(2):
            mb.add_bm(bm_box_minmax(x0, y0, 0.02 + k * 0.11, x1, y1, 0.02 + k * 0.11 + 0.09), "Wood_grey", scale=1.0, matrix=M,
                      off=roff(rng))
    mb.add_bm(bm_box_minmax(-w / 2, -d / 2, 0.0, w / 2, d / 2, 0.02), "Wood_grey", scale=1.0, matrix=M, off=roff(rng))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.add_bm(bm_box_minmax(sx * w / 2 - (0.04 if sx > 0 else 0), sy * d / 2 - (0.04 if sy > 0 else 0), 0.0,
                                    sx * w / 2 + (0.0 if sx > 0 else 0.04), sy * d / 2 + (0.0 if sy > 0 else 0.04), h), "Wood_dark",
                      scale=1.0, matrix=M)
    if fish:
        for k in range(9):
            fx, fy = rng.uniform(-0.22, 0.22), rng.uniform(-0.14, 0.14)
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=4, radius=1.0)
            bmesh.ops.scale(bm, vec=(0.11, 0.03, 0.025), verts=bm.verts)
            mb.add_bm(bm, "Fish", scale=1.0, smooth=True, matrix=M @ Matrix.Translation((fx, fy, h - 0.06)) @ Matrix.Rotation(rng.uniform(0, 3), 4, "Z"))
    return h


def fish_hall():
    """La criée: open-sided 20 x 10 m market hall, granite piers, king-post trusses, slate roof, crates."""
    rng = random.Random(56)
    mb = MB()
    cols = Cols()
    W, D = 20.0, 10.0
    hp = 3.6
    xs = [-9.7, -5.82, -1.94, 1.94, 5.82, 9.7]
    # flagged floor slab with a drainage gutter
    mb.add_bm(bm_box_minmax(-W / 2 - 0.3, -D / 2 - 0.3, -0.25, W / 2 + 0.3, D / 2 + 0.3, 0.12, bevel=0.03), "Granite", off=roff(rng))
    top = geo.bm_quad((-W / 2 - 0.2, -D / 2 - 0.2, 0.121), (W / 2 + 0.2, -D / 2 - 0.2, 0.121), (W / 2 + 0.2, D / 2 + 0.2, 0.121),
                      (-W / 2 - 0.2, D / 2 + 0.2, 0.121))
    mb.add_bm(top, "Flags", uv=lambda co, n: (co.x * 0.5, co.y * 0.5))
    mb.add_bm(bm_box_minmax(-W / 2, -0.12, 0.115, W / 2, 0.12, 0.123), "Void")
    cols.box("Floor", -W / 2 - 0.3, -D / 2 - 0.3, -0.25, W / 2 + 0.3, D / 2 + 0.3, 0.12)
    for x in xs:
        for y in (-D / 2 + 0.3, D / 2 - 0.3):
            mb.add_bm(bm_box_minmax(x - 0.36, y - 0.36, 0.12, x + 0.36, y + 0.36, 0.5, bevel=0.03), "Granite", off=roff(rng))
            nc = 6
            for k in range(nc):
                z0 = 0.5 + k * (hp - 0.75) / nc
                mb.add_bm(bm_box_minmax(x - 0.27, y - 0.27, z0 + 0.004, x + 0.27, y + 0.27, z0 + (hp - 0.75) / nc - 0.004, bevel=0.025),
                          "Ashlar", off=roff(rng))
            mb.add_bm(bm_box_minmax(x - 0.36, y - 0.36, hp - 0.25, x + 0.36, y + 0.36, hp, bevel=0.03), "Granite", off=roff(rng))
            cols.box("Pier", x - 0.36, y - 0.36, 0.12, x + 0.36, y + 0.36, hp)
    # wall plates and trusses
    pitch = 33.0
    hs = D / 2 + 0.1
    zr = hp + 0.3 + hs * math.tan(math.radians(pitch))
    for y in (-D / 2 + 0.3, D / 2 - 0.3):
        mb.add_bm(bm_box_minmax(-W / 2 - 0.1, y - 0.15, hp, W / 2 + 0.1, y + 0.15, hp + 0.3), "Wood_dark", scale=1.0)
    for x in xs:
        mb.add_bm(bm_box_minmax(x - 0.1, -D / 2 + 0.1, hp + 0.05, x + 0.1, D / 2 - 0.1, hp + 0.3), "Wood_dark", scale=1.0)   # tie beam
        mb.add_bm(bm_box_minmax(x - 0.09, -0.09, hp + 0.3, x + 0.09, 0.09, zr - 0.15), "Wood_dark", scale=1.0)              # king post
        for s in (-1, 1):
            mb.add_bm(cyl_between(Vector((x, s * (D / 2 - 0.2), hp + 0.35)), Vector((x, 0, zr - 0.1)), 0.1, 4), "Wood_dark", scale=1.0)
            mb.add_bm(cyl_between(Vector((x, 0, hp + 0.6)), Vector((x, s * D / 4, hp + 0.3 + (D / 4) * math.tan(math.radians(pitch)))),
                                  0.07, 4), "Wood_dark", scale=1.0)
    for k in range(5):        # purlins
        t = (k + 0.5) / 5
        for s in (-1, 1):
            y = s * (D / 2 - 0.2) * (1 - t)
            z = hp + 0.35 + (zr - 0.1 - hp - 0.35) * t + 0.12
            mb.add_bm(bm_box_minmax(-W / 2 - 0.4, y - 0.08, z - 0.08, W / 2 + 0.4, y + 0.08, z + 0.08), "Wood_dark", scale=1.0)
    zeave = hp + 0.35
    zrr = gable_roof(mb, -W / 2 - 0.3, W / 2 + 0.3, 0.0, D / 2 + 0.6, zeave + 0.05 - 0.6 * math.tan(math.radians(pitch)) + 0.1,
                     pitch, rng, ov_end=0.0)
    # weatherboarded gable triangles with a louvre, and the painted name board
    for sx in (-1, 1):
        x = sx * (W / 2 + 0.05)
        hs_r = D / 2 + 0.6
        z_e = zeave + 0.05 - 0.6 * math.tan(math.radians(pitch)) + 0.1 - 0.14
        for k in range(16):
            z0 = hp + 0.3 + k * 0.2
            half = hs_r - (z0 + 0.21 - z_e) / math.tan(math.radians(pitch)) - 0.05
            if half < 0.1:
                break
            mb.add_bm(bm_box_minmax(x - 0.02, -half, z0, x + 0.02, half, z0 + 0.21), "Wood_grey", scale=1.0, off=roff(rng))
        mb.add_bm(bm_box_minmax(x - 0.04 * sx - 0.02, -0.4, hp + 1.3, x + 0.02 - 0.04 * sx + 0.04, 0.4, hp + 2.0), "Void")
    F = WFace((-W / 2 - 0.08, 0, 0), (-1, 0, 0))
    mb.add_bm(F.box(-1.8, 1.8, 0.0, 0.04, hp + 0.4, hp + 0.95), "Paint_cream", scale=1.0)
    text(mb, F, "CRIÉE  MUNICIPALE", 0.0, hp + 0.67, 0.04, 0.3, "SignBlack", extrude=0.002, spacing=1.08)
    cols.prism("Roof", [(-D / 2 - 0.6, zeave - 0.3), (D / 2 + 0.6, zeave - 0.3), (0.0, zrr + 0.1)], -W / 2 - 0.3, W / 2 + 0.3)
    # crates in stacks, an auction table, a beam scale
    z0 = 0.12
    stacks = [(-7.5, -2.5, 4), (-7.5, -1.9, 3), (-6.8, -2.5, 2), (-3.5, 2.6, 5), (-3.5, 3.1, 4), (-2.8, 2.6, 2),
              (4.0, -3.0, 3), (4.7, -3.0, 1), (7.8, 2.8, 4), (7.8, 2.3, 3), (8.5, 2.8, 4), (1.0, 1.2, 1), (1.7, 1.5, 1)]
    for (x, y, n) in stacks:
        rot = rng.uniform(-0.08, 0.08)
        z = z0
        for k in range(n):
            h = _crate(mb, cols, x + rng.uniform(-0.02, 0.02), y + rng.uniform(-0.02, 0.02), z, rng, rot + rng.uniform(-0.03, 0.03),
                       fish=(k == n - 1 and rng.random() < 0.6))
            z += h
        cols.box("Crates", x - 0.33, y - 0.23, z0, x + 0.33, y + 0.23, z)
    # spilled ones on the floor
    for (x, y, r) in ((-0.5, -1.0, 0.4), (0.3, -1.6, -0.3), (5.6, 1.0, 0.9)):
        _crate(mb, cols, x, y, z0, rng, r, fish=True)
        cols.box("Crate", x - 0.35, y - 0.35, z0, x + 0.35, y + 0.35, z0 + 0.24)
    tx0, tx1 = -1.8, 2.2
    mb.add_bm(bm_box_minmax(tx0, -3.6, z0 + 0.85, tx1, -2.8, z0 + 0.92), "Wood_grey", scale=1.0)
    for x in (tx0 + 0.1, tx1 - 0.1):
        for y in (-3.5, -2.9):
            mb.add_bm(bm_box_minmax(x - 0.04, y - 0.04, z0, x + 0.04, y + 0.04, z0 + 0.85), "Wood_dark", scale=1.0)
    cols.box("Table", tx0, -3.6, z0, tx1, -2.8, z0 + 0.92)
    sxp, syp = 3.2, -1.2
    for s in (-1, 1):
        mb.add_bm(cyl_between(Vector((sxp + s * 0.4, syp, z0)), Vector((sxp, syp, z0 + 1.9)), 0.03, 6), "Iron", scale=2.0)
    mb.add_bm(cyl_between(Vector((sxp - 0.5, syp, z0 + 1.85)), Vector((sxp + 0.5, syp, z0 + 1.85)), 0.025, 6), "Iron", scale=2.0)
    mb.add_bm(lathe([(0.0, 0.0), (0.3, 0.02), (0.32, 0.08), (0.0, 0.06)], segs=14), "Zinc", matrix=Matrix.Translation((sxp - 0.45, syp, z0 + 0.9)))
    for k in range(3):
        a = 2 * PI * k / 3
        mb.add_bm(tube([Vector((sxp - 0.45 + 0.3 * math.cos(a), syp + 0.3 * math.sin(a), z0 + 0.98)), Vector((sxp - 0.45, syp, z0 + 1.85))],
                       0.004, 3), "Iron", scale=2.0)
    cols.box("Scale", sxp - 0.8, syp - 0.35, z0, sxp + 0.5, syp + 0.35, z0 + 1.9)
    ob = mb.build("FishHall")
    pv = [dict(elev=12.0, azim=-30.0, dist_mul=0.72, ground="cobble"),
          dict(suffix="_inside", elev=8.0, azim=-60.0, dist_mul=0.3, ground="cobble", target=(0.0, 0.0, 1.0))]
    return dict(visual=[ob], cols=cols.build(), tris=mb.tri_count(), pv=pv)
