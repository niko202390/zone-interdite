"""Generic granite/rendered building block on the kit's house parts (tools/blender/env/parts.py):
walls with raised gables, cut openings with dressed surrounds, windows, shutters, slate roof with
dormers, chimneys, string courses, weathering decals. Used by the hotel, mairie and watermill."""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box_minmax, bm_prism, boolean, union
from parts import (FACES, Face, Opening, Roof, body_profile, chimney, cutter, door, dormer_geom, dormer_roof,
                   gable_coping, gable_profile, hay_door, main_roof, quoins, roff, shutters, string_course, surround,
                   window)
import houses
from common import Cols


def band(mb, W, D, z, h, rng, proud=0.06, mat="Granite", faces=("front", "back", "left", "right")):
    """Projecting string course around the walls."""
    for name in faces:
        F = Face(name, W, D)
        half = F.length / 2 + proud
        mb.add_bm(F.box(-half, half, -0.05, proud, z, z + h, bevel=0.012, segs=1), mat, off=roff(rng))


def split_mat_by_z(bm, z, lower, upper):
    """Bisect a body bmesh at z and return [(bm_lower, mat), (bm_upper, mat)]."""
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1))
    from ihelp import split_by
    parts = split_by(bm, lambda f: "lo" if f.calc_center_median().z < z else "hi")
    return [(parts.get("lo"), lower), (parts.get("hi"), upper)]


def ridge_chimney(mb, R, x, rng, w=1.1, d=0.7, h=1.4, mat="Granite"):
    z0, z1 = R.Hr - 1.2, R.Hr + R.rise + h
    nc = int(round((z1 - z0) / 0.32))
    for i in range(nc):
        za = z0 + (z1 - z0) * i / nc
        zb = z0 + (z1 - z0) * (i + 1) / nc
        mb.add_bm(bm_box_minmax(x - w / 2, -d / 2, za + 0.002, x + w / 2, d / 2, zb - 0.002, bevel=0.01), mat, off=roff(rng))
    mb.add_bm(bm_box_minmax(x - w / 2 - 0.06, -d / 2 - 0.06, z1, x + w / 2 + 0.06, d / 2 + 0.06, z1 + 0.12, bevel=0.015, segs=2),
              mat, off=roff(rng))
    for k in range(3):
        cx = x - w / 2 + w * (k + 0.5) / 3
        mb.add_bm(geo.bm_cyl(0.09, 0.075, 0.35, segs=10), "Clay", scale=1.0, matrix=Matrix.Translation((cx, 0, z1 + 0.12)))
    return (x - w / 2 - 0.06, -d / 2 - 0.06, z0, x + w / 2 + 0.06, d / 2 + 0.06, z1 + 0.47)


class single_seg_bevels:
    """Context: force 1-segment (chamfer) bevels in parts.* boxes; halves the dressed-stone triangles on
    large facades while keeping the lit arris."""

    def __enter__(self):
        import parts
        self._orig = parts.bm_box_minmax

        def bb(x0, y0, z0, x1, y1, z1, bevel=0.0, segs=1):
            return self._orig(x0, y0, z0, x1, y1, z1, bevel, 1)
        parts.bm_box_minmax = bb
        return self

    def __exit__(self, *a):
        import parts
        parts.bm_box_minmax = self._orig


def build_block(spec):
    if spec.get("chamfer", True):
        with single_seg_bevels():
            return _build_block(spec)
    return _build_block(spec)


def _build_block(spec):
    """spec: W, D, He, pitch, wall, seed, openings, dormers, chimneys (gable sides), ridge_chimneys (x list),
    cornice, bands [(z, h)], lower=(z, mat) for a different ground-storey facing, extra_cuts [bmesh],
    quoins (bool). Returns dict with mb, R, faces, ops, rng, cols (Cols with Roof/Chimney/Dormer added)."""
    rng = random.Random(spec["seed"])
    W, D, He = spec["W"], spec["D"], spec["He"]
    R = Roof(W, D, He, spec["pitch"])
    faces = {k: Face(k, W, D) for k in FACES}
    mb = spec.get("mb") or MB()
    ops = list(spec["openings"])
    dms = []
    for d in spec.get("dormers", []):
        dm = dormer_geom(R, d["a"], d["wd"], He + d["zd"])
        dm.update(d)
        dms.append(dm)
        ops.append(Opening("front", d["a"], He + d["z0"], d["w"], d["h"], kind=d.get("kind", "window"),
                           shutters="none", glow=d.get("glow", False), rows=d.get("rows", 2),
                           paint=d.get("paint", "Wood_grey"), frame=d.get("frame", "Paint_cream")))
    tg = R.tg
    bodies = [bm_prism(body_profile(R), -W / 2, W / 2),
              bm_prism(gable_profile(R), -W / 2, -W / 2 + tg),
              bm_prism(gable_profile(R), W / 2 - tg, W / 2)]
    for dm in dms:
        bodies += dm["bodies"]
    body = union(bodies)
    cutters = [cutter(faces[op.face], op) for op in ops if op.kind != "skip"]
    body = boolean(body, cutters)
    for extra in spec.get("extra_cuts", []):       # separate passes: overlapping cutters break EXACT
        body = boolean(body, [extra])
    lower = spec.get("lower")
    if lower:
        for bm, mat in split_mat_by_z(body, lower[0], lower[1], spec["wall"]):
            if bm is not None:
                mb.add_bm(bm, mat, off=roff(rng))
    else:
        mb.add_bm(body, spec["wall"], off=roff(rng))
    if spec.get("quoins", True):
        quoins(mb, W, D, He, rng)
    if spec.get("cornice"):
        string_course(mb, W, D, He + 0.02, rng)
    for (z, h) in spec.get("bands", []):
        band(mb, W, D, z, h, rng)
    for op in ops:
        F = faces[op.face]
        if op.kind == "skip":
            continue
        surround(mb, F, op, rng, lintel_h=0.3 if op.w < 1.2 else 0.36)
        if op.kind == "window":
            window(mb, F, op)
            shutters(mb, F, op, rng)
        elif op.kind in ("door", "byre"):
            door(mb, F, op, rng)
        elif op.kind == "hay":
            hay_door(mb, F, op, rng)
    main_roof(mb, R, rng, dormers=[dict(a0=dm["a0"], a1=dm["a1"], z_top=dm["z_top"]) for dm in dms])
    for dm in dms:
        dormer_roof(mb, R, dm, rng)
    gable_coping(mb, R, rng)
    cols = Cols()
    for sx in spec.get("chimneys", []):
        cols.box("Chimney", *chimney(mb, R, sx, rng))
    for x in spec.get("ridge_chimneys", []):
        cols.box("Chimney", *ridge_chimney(mb, R, x, rng))
    houses._damp(mb, faces, W, D, ops, rng, extra_skip=spec.get("damp_skip"))
    for F in faces.values():
        houses._streaks(mb, F, ops, rng)
    prof = [(-D / 2 - R.ov, R.z_eave - 0.05), (D / 2 + R.ov, R.z_eave - 0.05), (0.0, R.Hr + R.rise)]
    cols.prism("Roof", prof, -W / 2, W / 2)
    for dm in dms:
        cols.box("Dormer", dm["a0"] + 0.1, -D / 2 - 0.05, He - 0.4, dm["a1"] - 0.1, -D / 2 + dm["depth"], dm["z_top"])
    return dict(mb=mb, R=R, faces=faces, ops=ops, rng=rng, cols=cols, dms=dms)


def step_cols(cols, faces, ops):
    for op in [o for o in ops if o.z0 < 0.05 and o.kind != "skip"]:
        F = faces[op.face]
        cols.fbox("Step", F, op.a0 - 0.12, op.a1 + 0.12, -0.25, 0.32, -0.12, 0.13)
