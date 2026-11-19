"""street_pave_10m: 10 m (along Blender Y = Godot Z) x 7 m granite-sett village street.
Cambered carriageway of setts, granite gutter channels each side, sett margins to the house line.
Tiles end to end: UVs are world-scaled (2 m per texture tile) so 10 m = 5 whole tiles."""
import math
import random

import bmesh

from geo import MB, collision_bm

L = 10.0
WIDTH = 7.0


LIFT = 0.045   # whole profile sits above z=0 so it can lie on flat terrain without burying the gutters


def _profile_z(x):
    """Cross-section height at x (metres from centreline)."""
    ax = abs(x)
    if ax <= 2.75:                       # cambered carriageway
        return LIFT + 0.05 * (1 - (ax / 2.75) ** 2)
    if ax <= 3.15:                       # gutter channel (caniveau), dips 4 cm
        t = (ax - 2.75) / 0.4
        return LIFT - 0.04 * math.sin(math.pi * t)
    return LIFT + (ax - 3.15) * 0.06     # margin rises gently to the walls


def build():
    rng = random.Random(77)
    mb = MB()
    # surface: grid across x, along y (enough rows for the camber / gutter curve)
    xs = [-3.5 + 7.0 * i / 56 for i in range(57)]
    ys = [-L / 2 + L * j / 20 for j in range(21)]
    bm = bmesh.new()
    grid = [[bm.verts.new((x, y, _profile_z(x))) for x in xs] for y in ys]
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    # skirt down to -0.3 so the slab is closed at the sides
    edge_l = [grid[j][0] for j in range(len(ys))]
    edge_r = [grid[j][-1] for j in range(len(ys))]
    for edge, flip in ((edge_l, True), (edge_r, False)):
        low = [bm.verts.new((v.co.x, v.co.y, -0.3)) for v in edge]
        for j in range(len(edge) - 1):
            f = (edge[j], edge[j + 1], low[j + 1], low[j]) if flip else (edge[j + 1], edge[j], low[j], low[j + 1])
            bm.faces.new(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    # setts everywhere except the gutter channels, which use dressed granite
    def uv_setts(co, n):
        return (co.x * 0.5, co.y * 0.5)

    gut = bmesh.new()
    sett = bmesh.new()
    # split faces by material: rebuild via two bmeshes
    for f in bm.faces:
        cx = sum(v.co.x for v in f.verts) / len(f.verts)
        target = gut if 2.75 <= abs(cx) <= 3.15 and f.normal.z > 0.5 else sett
        vs = [target.verts.new(v.co) for v in f.verts]
        target.faces.new(vs)
    bm.free()
    mb.add_bm(sett, "Setts", uv=uv_setts, smooth=True, smooth_angle=60)
    mb.add_bm(gut, "Granite", uv=lambda co, n: (co.x * 0.5 + 0.3, co.y * 0.5), smooth=True, smooth_angle=60)
    ob = mb.build("street_pave_10m")

    # collision: convex slab per cross-section band (carriageway, gutters, margins)
    cols = []
    for k, (x0, x1) in enumerate(((-3.5, -3.15), (-3.15, -2.75), (-2.75, 2.75), (2.75, 3.15), (3.15, 3.5))):
        b = bmesh.new()
        top = []
        n = 8
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            top.append((x, _profile_z(x)))
        prof = [(x0, -0.3)] + top + [(x1, -0.3)]
        a = [b.verts.new((x, -L / 2, z)) for (x, z) in prof]
        c = [b.verts.new((x, L / 2, z)) for (x, z) in prof]
        b.faces.new(a)
        b.faces.new(list(reversed(c)))
        for i in range(len(prof)):
            j = (i + 1) % len(prof)
            b.faces.new((a[i], a[j], c[j], c[i]))
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        cols.append(collision_bm(f"Street{k}", b, suffix="-colonly"))
    return [ob], cols, mb.tri_count()
