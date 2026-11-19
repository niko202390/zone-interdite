"""Mairie de Plouzennec: two-storey granite ashlar town hall, 16 x 10 m, with the PTT telephone exchange
inside. "MAIRIE" inscribed on a granite tablet over the door, blue enamel PTT plaque, clock dormer,
telephone line bracket on the east gable. Separate node: Door (origin on the hinge)."""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import geo
from geo import MB, bm_box_minmax
from parts import Face, Opening, roff, text
from common import Cols, WFace, cyl_between, door_node, lathe, tube
import block

W, D, He = 16.0, 10.0, 7.4


def _openings():
    o = []
    sh = "Paint_cream"
    for a in (-6.0, -3.0, 3.0, 6.0):
        o.append(Opening("front", a, 0.85, 1.1, 2.0, shutters="none", rows=4, glow=(a == 3.0)))
    o.append(Opening("front", 0.0, 0.0, 1.3, 2.75, kind="entry"))
    for a in (-6.0, -3.0, 0.0, 3.0, 6.0):
        o.append(Opening("front", a, 4.35, 1.1, 1.95, shutters="open" if a != 0 else "none", paint="Paint_blue", rows=4))
    for a in (-5.0, -1.5, 1.5, 5.0):
        o.append(Opening("back", a, 0.95, 1.0, 1.7, shutters="closed", paint="Paint_blue"))
        o.append(Opening("back", a, 4.35, 1.0, 1.8, shutters="open" if a < 0 else "closed", paint="Paint_blue"))
    o.append(Opening("back", 3.3, 0.0, 1.0, 2.1, kind="door", paint="Paint_green", leaves=1))
    for f in ("left", "right"):
        o.append(Opening(f, -2.0, 0.95, 0.9, 1.6, shutters="closed", paint="Paint_blue"))
        o.append(Opening(f, 2.0, 4.4, 0.9, 1.6, shutters="none"))
    return o


def _tablet(mb, F, rng):
    """Granite inscription tablet with moulded frame and incised MAIRIE."""
    z0, z1 = 3.18, 3.72
    mb.add_bm(F.box(-1.3, 1.3, -0.05, 0.05, z0, z1, bevel=0.01), "Granite", off=roff(rng))
    mb.add_bm(F.box(-1.42, 1.42, -0.05, 0.1, z0 - 0.08, z0, bevel=0.015), "Granite", off=roff(rng))
    mb.add_bm(F.box(-1.42, 1.42, -0.05, 0.1, z1, z1 + 0.1, bevel=0.015), "Granite", off=roff(rng))
    text(mb, F, "MAIRIE", 0.0, (z0 + z1) / 2, 0.048, 0.34, "GraniteDark", extrude=0.003, spacing=1.35)


def _ptt_plaque(mb, F, rng):
    a, z = 1.55, 1.75
    w, h = 0.94, 0.3
    mb.add_bm(F.box(a - w / 2, a + w / 2, 0.0, 0.012, z, z + h, bevel=0.004), "EnamelBlue", scale=1.0)
    for (a0, a1, z0_, z1_) in ((a - w / 2 + 0.015, a + w / 2 - 0.015, z + 0.015, z + 0.022),
                               (a - w / 2 + 0.015, a + w / 2 - 0.015, z + h - 0.022, z + h - 0.015),
                               (a - w / 2 + 0.015, a - w / 2 + 0.022, z + 0.015, z + h - 0.015),
                               (a + w / 2 - 0.022, a + w / 2 - 0.015, z + 0.015, z + h - 0.015)):
        mb.add_bm(F.box(a0, a1, 0.012, 0.0135, z0_, z1_), "EnamelWhite")
    text(mb, F, "POSTES", a, z + 0.235, 0.0125, 0.06, "EnamelWhite", extrude=0.0008, spacing=1.2)
    text(mb, F, "TÉLÉGRAPHES", a, z + 0.15, 0.0125, 0.055, "EnamelWhite", extrude=0.0008, spacing=1.05)
    text(mb, F, "TÉLÉPHONES", a, z + 0.065, 0.0125, 0.055, "EnamelWhite", extrude=0.0008, spacing=1.05)
    for aa in (a - w / 2 + 0.035, a + w / 2 - 0.035):
        for zz in (z + 0.035, z + h - 0.035):
            mb.add_bm(F.box(aa - 0.007, aa + 0.007, 0.012, 0.018, zz - 0.007, zz + 0.007), "Zinc", scale=2.0)


def _clock(mb, B, rng):
    """Clock face in the central dormer gable."""
    dm = [d for d in B["dms"] if abs(d["a"]) < 0.01][0]
    F = Face("front", W, D)
    zc = He + 0.95
    r = 0.42
    disc = geo.bm_cyl(r + 0.06, r + 0.06, 0.05, segs=28)
    M = Matrix.Translation(F.p(0.0, 0.0, zc)) @ Matrix.Rotation(math.pi / 2, 4, "X")
    mb.add_bm(disc, "Granite", matrix=M, off=roff(rng))
    face = geo.bm_cyl(r, r, 0.02, segs=28)
    mb.add_bm(face, "EnamelWhite", matrix=Matrix.Translation(F.p(0.0, 0.05, zc)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    for k in range(12):
        ang = 2 * math.pi * k / 12
        a, z = math.sin(ang) * r * 0.82, zc + math.cos(ang) * r * 0.82
        mb.add_bm(F.box(a - 0.012, a + 0.012, 0.07, 0.075, z - 0.035, z + 0.035), "SignBlack")
    for (ang, L, t) in ((math.radians(-60), 0.24, 0.018), (math.radians(165), 0.34, 0.012)):   # ~ ten to six
        p0 = F.p(0.0, 0.08, zc)
        p1 = F.p(math.sin(ang) * L, 0.08, zc + math.cos(ang) * L)
        mb.add_bm(tube([p0, p1], t, 4), "SignBlack")


def _phone_bracket(mb, rng):
    """Iron bracket with cross-arms and insulators on the east gable: the PTT exchange lines."""
    x = W / 2 + 0.05
    z0 = 6.2
    mb.add_bm(bm_box_minmax(x, -0.06, z0 - 0.4, x + 0.02, 0.06, z0 + 1.4), "Iron", scale=2.0)
    for zz in (z0 + 0.3, z0 + 1.0):
        mb.add_bm(bm_box_minmax(x + 0.02, -0.9, zz - 0.04, x + 0.1, 0.9, zz + 0.04), "Iron", scale=2.0)
        mb.add_bm(tube([(x + 0.02, -0.6, zz - 0.4), (x + 0.06, -0.85, zz - 0.04)], 0.012, 4), "Iron", scale=2.0)
        mb.add_bm(tube([(x + 0.02, 0.6, zz - 0.4), (x + 0.06, 0.85, zz - 0.04)], 0.012, 4), "Iron", scale=2.0)
        for k in range(5):
            y = -0.75 + k * 0.375
            ins = lathe([(0.0, 0.0), (0.035, 0.0), (0.04, 0.06), (0.025, 0.09), (0.03, 0.12), (0.0, 0.14)], segs=8)
            mb.add_bm(ins, "InsulatorGlass", smooth=True, matrix=Matrix.Translation((x + 0.06, y, zz + 0.04)))
            # the line wires, drooping off into the street (2 m stubs; the street kit carries them on)
            mb.add_bm(tube([(x + 0.06, y, zz + 0.12), (x + 1.0, y, zz - 0.05), (x + 2.0, y * 1.1, zz - 0.06)], 0.0025, 3), "Iron",
                      scale=4.0)
        # leads into the wall
        mb.add_bm(tube([(x + 0.06, -0.75, zz + 0.1), (x + 0.02, -0.2, zz - 0.3), (x, 0.0, zz - 0.45)], 0.004, 3), "Iron", scale=4.0)


def build():
    rng = random.Random(1880)
    mb = MB()
    Ff = Face("front", W, D)
    vest = Ff.box(-0.68, 0.68, -1.6, 0.3, -0.3, 2.77)
    dormers = [dict(a=0.0, wd=1.7, zd=1.7, z0=0.0, w=0.9, h=1.0, kind="skip"),
               dict(a=-4.5, wd=1.5, zd=1.35, z0=0.05, w=0.8, h=1.0),
               dict(a=4.5, wd=1.5, zd=1.35, z0=0.05, w=0.8, h=1.0)]
    spec = dict(W=W, D=D, He=He, pitch=45.0, wall="Ashlar", seed=1880, openings=_openings(), dormers=dormers,
                chimneys=[-1, 1], cornice=True, bands=[(3.85, 0.2)], extra_cuts=[vest], mb=mb,
                damp_skip={"front": [(-1.6, 1.6)]}, quoins=True)
    B = block.build_block(spec)
    cols = B["cols"]
    F = B["faces"]["front"]
    # granite steps, door frame, fanlight, vestibule
    mb.add_bm(F.box(-1.6, 1.6, -0.2, 0.9, -0.2, 0.0, bevel=0.015), "Granite", off=roff(rng))
    mb.add_bm(F.box(-1.3, 1.3, -0.2, 0.5, 0.0, 0.16, bevel=0.015), "Granite", off=roff(rng))
    for (a0, a1, z0, z1) in ((-0.65, -0.59, 0.16, 2.75), (0.59, 0.65, 0.16, 2.75), (-0.65, 0.65, 2.3, 2.38), (-0.65, 0.65, 2.69, 2.75)):
        mb.add_bm(F.box(a0, a1, -0.3, -0.17, z0, z1), "Paint_green", scale=1.0)
    mb.add_bm(F.quad(-0.59, 0.59, 2.38, 2.69, -0.24), "WindowGlass")
    for k in range(1, 4):
        mb.add_bm(F.box(-0.59 + 1.18 * k / 4 - 0.01, -0.59 + 1.18 * k / 4 + 0.01, -0.25, -0.2, 2.38, 2.69), "Iron", scale=2.0)
    mb.add_bm(F.quad(-0.65, 0.65, 0.16, 2.3, -1.53), "Interior")
    mb.add_bm(geo.bm_quad(F.p(-0.65, -0.3, 0.161), F.p(0.65, -0.3, 0.161), F.p(0.65, -1.55, 0.161), F.p(-0.65, -1.55, 0.161)), "Flags")
    mb.add_bm(F.box(-0.7, 0.7, -1.6, -0.3, -0.3, 0.16), "Granite", off=roff(rng))
    _tablet(mb, F, rng)
    _ptt_plaque(mb, F, rng)
    _clock(mb, B, rng)
    _phone_bracket(mb, rng)
    # notice-board frames either side of the door (affichage municipal)
    for a in (-1.85,):
        mb.add_bm(F.box(a - 0.45, a + 0.45, 0.0, 0.05, 1.0, 2.1), "Paint_green", scale=1.0)
        mb.add_bm(F.box(a - 0.39, a + 0.39, 0.05, 0.052, 1.06, 2.04), "Paper", scale=1.0)
        mb.add_bm(F.box(a - 0.5, a + 0.5, 0.0, 0.1, 2.1, 2.16), "Zinc", scale=1.0)
    cols.box("Body", -W / 2, -D / 2 + 1.6, -0.3, W / 2, D / 2, He)
    cols.box("FrontW", -W / 2, -D / 2, -0.3, -0.68, -D / 2 + 1.6, He)
    cols.box("FrontE", 0.68, -D / 2, -0.3, W / 2, -D / 2 + 1.6, He)
    cols.box("FrontTop", -0.68, -D / 2, 2.77, 0.68, -D / 2 + 1.6, He)
    cols.box("Steps", -1.6, -D / 2 - 0.9, -0.2, 1.6, -D / 2, 0.0)
    cols.box("Steps2", -1.3, -D / 2 - 0.5, 0.0, 1.3, -D / 2, 0.16)
    block.step_cols(cols, B["faces"], [o for o in B["ops"] if o.kind != "entry"])
    ob = mb.build("Mairie")
    tris = mb.tri_count()
    door_objs, dtris, hinge = door_node("Door", F, -0.59, 0.59, -0.26, -0.2, 0.16, 2.3, "Door_bottle", rng,
                                        kind="panel", glazed_top=False)
    note = f"Door hinge {tuple(round(v, 3) for v in hinge)}"
    pv = [dict(elev=9.0, azim=-30.0, dist_mul=0.7, ground="cobble"),
          dict(suffix="_detail", elev=4.0, azim=-12.0, dist_mul=0.24, ground="cobble", target=(0.6, -5.0, 2.4))]
    return dict(visual=[ob, door_objs[0]], cols=cols.build() + door_objs[1:], tris=tris + dtris, pv=pv, note=note)
