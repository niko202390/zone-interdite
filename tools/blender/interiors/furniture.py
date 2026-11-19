"""Period furniture for 1944 Breton interiors. Every builder takes a Put (placement + collision
collector) and works in local space: origin at floor level in the centre of the footprint, front
facing -Y. Collision is added as simple boxes through P.col()."""
import math

import bmesh
from mathutils import Matrix, Vector

from geo import bm_box, bm_box_minmax, bm_cyl, bm_prism
from ihelp import cyl_x, cyl_y, lathe, tube

PI = math.pi
W_DARK = "Furn_chestnut"
W_OAK = "Furn_oak"


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def Rz(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Z")


def Rx(deg):
    return Matrix.Rotation(math.radians(deg), 4, "X")


def Ry(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Y")


# ------------------------------------------------------------------ carving helpers
def rosette(P, cx, y, cz, r, mat=W_DARK, petals=6, depth=0.012):
    """Breton 'rouelle' / compass rosette on a front face at plane y (facing -Y)."""
    M = T(cx, y, cz) @ Rx(90)                       # local +Z -> world -Y
    P.bm(lathe([(r, 0.0), (r, depth * 0.4), (r * 0.9, depth * 0.5), (0.0, depth * 0.5)], segs=16), mat, matrix=M,
         scale=1.0)
    P.bm(lathe([(r * 0.86, depth * 0.5), (r * 0.86, depth * 0.8), (r * 0.78, depth * 0.8), (r * 0.78, depth * 0.5)],
               segs=16, cap_top=False, cap_bottom=False), mat, matrix=M, scale=1.0)
    for k in range(petals):                         # radial petals (chip-carved lozenges)
        a = 2 * PI * k / petals
        bm = bm_box(0, r * 0.4, depth * 0.75, r * 0.14, r * 0.62, depth * 0.5, rot=(0, 0, 0))
        bmesh.ops.scale(bm, vec=(1, 1, 1), verts=bm.verts)
        for v in bm.verts:                          # taper into a lozenge
            t = (v.co.y - r * 0.09) / (r * 0.62)
            v.co.x *= max(0.15, 1.0 - abs(t - 0.5) * 1.6)
        P.bm(bm, mat, matrix=M @ Matrix.Rotation(a, 4, "Z"), scale=1.0)
    P.bm(lathe([(r * 0.12, depth * 0.5), (r * 0.1, depth * 1.0), (0.0, depth * 1.1)], segs=10), mat, matrix=M, scale=1.0)


def spindle(P, x, y, z0, z1, r=0.012, mat=W_DARK, segs=6):
    h = z1 - z0
    prof = [(r * 0.8, 0.0), (r * 0.8, h * 0.12), (r * 1.25, h * 0.22), (r * 0.65, h * 0.4), (r * 1.3, h * 0.5),
            (r * 0.65, h * 0.6), (r * 1.25, h * 0.78), (r * 0.8, h * 0.88), (r * 0.8, h)]
    P.bm(lathe(prof, segs=segs, cap_top=False, cap_bottom=False), mat, matrix=T(x, y, z0), scale=1.0, smooth=True)


def raised_panel(P, x0, x1, z0, z1, y, mat=W_DARK, depth=0.012, border=0.035):
    """Fielded panel on a front plane y (facing -Y): frame moulding + raised field."""
    P.box(x0, y - depth * 0.4, z0, x1, y, z1, mat)
    P.box(x0 + border, y - depth, z0 + border, x1 - border, y - depth * 0.4, z1 - border, mat, bevel=0.006)


def knob(P, x, y, z, mat="Brass", r=0.014):
    P.bm(lathe([(r * 0.5, 0), (r * 0.5, r), (r, r * 1.5), (r, r * 2.2), (0, r * 2.4)], segs=8), mat,
         matrix=T(x, y, z) @ Rx(90), scale=2.0, smooth=True)


def escutcheon(P, x, y, z, mat="Brass"):
    """Pierced brass key plate (entrée de serrure), Breton furniture signature."""
    bm = bmesh.new()
    pts = []
    for i in range(12):
        a = 2 * PI * i / 12
        rr = 0.035 if i % 2 == 0 else 0.022
        pts.append(bm.verts.new((math.cos(a) * rr * 0.8, 0.0, math.sin(a) * rr * 1.3)))
    bm.faces.new(pts)
    bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    for v in bm.verts[12:]:
        v.co.y -= 0.002
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    P.bm(bm, mat, matrix=T(x, y, z), scale=2.0)
    P.box(x - 0.003, y - 0.0025, z - 0.012, x + 0.003, y - 0.002, z + 0.006, "BlackPaint")


# ======================================================================= LIT CLOS
def lit_clos(P, L=1.85, D=0.82, H=2.0, bench=True, open_frac=0.55):
    """Breton box-bed: closed cupboard bed with two sliding doors, spindle galleries (claire-voie),
    carved rosettes and frieze; a chest-bench (banc-coffre) in front."""
    yf = -D / 2
    # feet + plinth
    for x in (-L / 2 + 0.05, L / 2 - 0.05):
        for y in (yf + 0.05, D / 2 - 0.05):
            P.box(x - 0.05, y - 0.05, 0.0, x + 0.05, y + 0.05, 0.08, W_DARK)
    # carcass
    P.box(-L / 2, yf + 0.02, 0.08, -L / 2 + 0.05, D / 2, H - 0.14, W_DARK)            # ends
    P.box(L / 2 - 0.05, yf + 0.02, 0.08, L / 2, D / 2, H - 0.14, W_DARK)
    P.box(-L / 2, D / 2 - 0.03, 0.08, L / 2, D / 2, H - 0.14, W_DARK)                 # back
    P.box(-L / 2, yf + 0.02, H - 0.17, L / 2, D / 2, H - 0.14, W_DARK)                # roof board
    P.box(-L / 2 + 0.05, yf + 0.06, 0.42, L / 2 - 0.05, D / 2 - 0.03, 0.47, W_DARK)   # bed base
    # bedding inside
    P.box(-L / 2 + 0.06, yf + 0.1, 0.47, L / 2 - 0.06, D / 2 - 0.04, 0.62, "Linen", bevel=0.04, segs=2)
    P.box(-L / 2 + 0.06, yf + 0.1, 0.62, L / 2 - 0.4, D / 2 - 0.04, 0.68, "Blanket", bevel=0.025, segs=2)
    P.box(L / 2 - 0.42, yf + 0.18, 0.62, L / 2 - 0.08, D / 2 - 0.08, 0.76, "Linen", bevel=0.05, segs=2)  # bolster
    # cornice (two stepped mouldings)
    P.box(-L / 2 - 0.04, yf - 0.04, H - 0.14, L / 2 + 0.04, D / 2, H - 0.06, W_DARK, bevel=0.012, segs=2)
    P.box(-L / 2 - 0.07, yf - 0.07, H - 0.06, L / 2 + 0.07, D / 2, H, W_DARK, bevel=0.015, segs=2)
    # front frame: stiles + rails
    fz0, fz1 = 0.47, H - 0.42                        # bed opening (behind the sliding doors)
    for (x0, x1) in ((-L / 2, -L / 2 + 0.09), (-0.045, 0.045), (L / 2 - 0.09, L / 2)):
        P.box(x0, yf, 0.08, x1, yf + 0.04, H - 0.14, W_DARK)
    P.box(-L / 2, yf, 0.08, L / 2, yf + 0.04, 0.12, W_DARK)
    P.box(-L / 2, yf, fz0 - 0.06, L / 2, yf + 0.04, fz0, W_DARK)
    P.box(-L / 2, yf, fz1, L / 2, yf + 0.04, fz1 + 0.06, W_DARK)
    P.box(-L / 2, yf, H - 0.2, L / 2, yf + 0.04, H - 0.14, W_DARK)
    # lower front panels with rosettes
    for (x0, x1) in ((-L / 2 + 0.09, -0.045), (0.045, L / 2 - 0.09)):
        raised_panel(P, x0, x1, 0.12, fz0 - 0.06, yf + 0.02)
        rosette(P, (x0 + x1) / 2, yf + 0.008, (0.12 + fz0 - 0.06) / 2, 0.1)
    # frieze between fz1+0.06 and H-0.2: three roundels and chip-carved diamonds
    fzc = (fz1 + 0.06 + H - 0.2) / 2
    fh = (H - 0.2) - (fz1 + 0.06)
    P.box(-L / 2 + 0.09, yf + 0.015, fz1 + 0.06, L / 2 - 0.09, yf + 0.03, H - 0.2, W_DARK)
    for i, x in enumerate((-0.6, 0.0, 0.6)):
        rosette(P, x, yf + 0.015, fzc, min(0.12, fh * 0.42), petals=8 if i == 1 else 6)
    for x in (-0.3, 0.3, -0.82, 0.82):
        if abs(x) > L / 2 - 0.12:
            continue
        bm = bm_box(0, 0, 0, 0.07, 0.012, 0.07, rot=(0, math.radians(45), 0))
        P.bm(bm, W_DARK, matrix=T(x, yf + 0.009, fzc), scale=1.0)
    # sliding doors (two leaves in a track), the left one slid partly behind the right
    dw = L / 2 - 0.09 + 0.02
    dh = fz1 - fz0
    pos = [(-L / 2 + 0.09 - 0.01) + (dw * open_frac), 0.045 - 0.01]   # left edge of each leaf
    for k, xl in enumerate(pos):
        yd = yf - 0.015 - 0.03 * k                    # two tracks
        P.box(xl, yd, fz0, xl + dw, yd + 0.025, fz0 + 0.06, W_DARK)
        P.box(xl, yd, fz1 - 0.06, xl + dw, yd + 0.025, fz1, W_DARK)
        P.box(xl, yd, fz0, xl + 0.06, yd + 0.025, fz1, W_DARK)
        P.box(xl + dw - 0.06, yd, fz0, xl + dw, yd + 0.025, fz1, W_DARK)
        zmid0, zmid1 = fz0 + dh * 0.38, fz0 + dh * 0.44
        P.box(xl, yd, zmid0, xl + dw, yd + 0.025, zmid1, W_DARK)
        raised_panel(P, xl + 0.06, xl + dw - 0.06, fz0 + 0.06, zmid0, yd + 0.01)
        rosette(P, xl + dw / 2, yd + 0.0, (fz0 + 0.06 + zmid0) / 2, 0.075)
        # claire-voie: turned spindles in the upper part (ventilation of the bed)
        n = 9
        for i in range(n):
            x = xl + 0.06 + (dw - 0.12) * (i + 0.5) / n
            spindle(P, x, yd + 0.0125, zmid1, fz1 - 0.06, r=0.011)
        P.box(xl + 0.06, yd + 0.005, zmid1 + (fz1 - 0.06 - zmid1) * 0.5 - 0.012, xl + dw - 0.06, yd + 0.02,
              zmid1 + (fz1 - 0.06 - zmid1) * 0.5 + 0.012, W_DARK)
        knob(P, xl + (0.1 if k == 0 else dw - 0.1), yd, (fz0 + fz1) / 2, mat=W_DARK, r=0.016)
    # dark gap behind spindles: back of bed interior is the carcass back
    P.col("LitClos", -L / 2 - 0.07, yf - 0.07, 0.0, L / 2 + 0.07, D / 2, H)
    if bench:
        banc_coffre(P.sub(T(0, yf - 0.27, 0)), L=min(1.6, L - 0.1))


def banc_coffre(P, L=1.6, D=0.42, H=0.5):
    """Chest-bench in front of a lit clos: hinged lid, panelled front."""
    P.box(-L / 2, -D / 2, 0.0, L / 2, D / 2, 0.06, W_DARK)
    P.box(-L / 2 + 0.01, -D / 2 + 0.01, 0.06, L / 2 - 0.01, D / 2 - 0.01, H - 0.04, W_DARK)
    P.box(-L / 2 - 0.02, -D / 2 - 0.03, H - 0.04, L / 2 + 0.02, D / 2 + 0.01, H, W_DARK, bevel=0.01, segs=2)
    n = 3
    for i in range(n):
        x0 = -L / 2 + 0.05 + (L - 0.1) * i / n + 0.02
        x1 = -L / 2 + 0.05 + (L - 0.1) * (i + 1) / n - 0.02
        raised_panel(P, x0, x1, 0.09, H - 0.08, -D / 2 + 0.01)
    escutcheon(P, 0.0, -D / 2 - 0.004, H - 0.12)
    P.col("Bench", -L / 2 - 0.02, -D / 2 - 0.03, 0.0, L / 2 + 0.02, D / 2 + 0.01, H)


# =================================================================== TABLE + BENCH
def table(P, L=2.0, W=0.82, H=0.76, mat=W_OAK, drawer=True, name="Table"):
    tt = 0.06
    P.box(-L / 2, -W / 2, H - tt, L / 2, W / 2, H, mat, bevel=0.008, segs=2)
    lx, ly = L / 2 - 0.12, W / 2 - 0.08
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * lx, sy * ly
            P.box(x - 0.045, y - 0.045, 0.0, x + 0.045, y + 0.045, H - tt, mat, bevel=0.006)
    # aprons
    P.box(-lx, -ly - 0.02, H - tt - 0.12, lx, -ly + 0.0, H - tt, mat)
    P.box(-lx, ly, H - tt - 0.12, lx, ly + 0.02, H - tt, mat)
    for sx in (-1, 1):
        P.box(sx * lx - 0.01, -ly, H - tt - 0.12, sx * lx + 0.01, ly, H - tt, mat)
    # low stretchers (H-frame) - used as a footrest, worn
    for sx in (-1, 1):
        P.box(sx * lx - 0.025, -ly, 0.08, sx * lx + 0.025, ly, 0.14, mat)
    P.box(-lx, -0.025, 0.1, lx, 0.025, 0.15, mat)
    if drawer:
        P.box(L / 2 - 0.13 - 0.01, -0.22, H - tt - 0.11, L / 2 - 0.115, 0.22, H - tt - 0.01, mat)
        knob(P.sub(T(0, 0, 0) @ Rz(90)), 0.0, -(L / 2 - 0.115), H - tt - 0.06, mat=W_DARK, r=0.014)
    P.col(name, -L / 2, -W / 2, 0.0, L / 2, W / 2, H)


def bench(P, L=1.9, W=0.3, H=0.46, mat=W_OAK, name="Bench"):
    P.box(-L / 2, -W / 2, H - 0.05, L / 2, W / 2, H, mat, bevel=0.006, segs=2)
    for sx in (-1, 1):
        x = sx * (L / 2 - 0.18)
        P.box(x - 0.03, -W / 2 + 0.02, 0.0, x + 0.03, W / 2 - 0.02, H - 0.05, mat)
        P.box(x - 0.03, -W / 2 + 0.06, 0.0, x + 0.03, W / 2 - 0.06, 0.02, mat)  # foot pads
    P.box(-L / 2 + 0.18, -0.025, 0.12, L / 2 - 0.18, 0.025, 0.18, mat)
    P.col(name, -L / 2, -W / 2, 0.0, L / 2, W / 2, H)


def table_bench(P, L=2.0, W=0.82, bench_gap=0.62, mat=W_OAK):
    table(P, L=L, W=W, mat=mat)
    for sy in (-1, 1):
        bench(P.sub(T(0, sy * bench_gap, 0)), L=L - 0.1, mat=mat)


# ============================================================== DRESSER (vaisselier)
def plate(P, x, y, z, r=0.115, tilt=-14.0):
    """Faience plate leaning back against the rack (front faces -Y)."""
    prof = [(r * 0.55, 0.0), (r, 0.016), (r * 0.98, 0.021), (r * 0.6, 0.009), (0.0, 0.009)]
    bm = lathe(prof, segs=20, cap_top=False, cap_bottom=True, uv_keep=True)
    P.bm(bm, "Faience", uv="keep", matrix=T(x, y, z + r) @ Rx(90 + tilt))


def bowl(P, x, y, z, r=0.07, mat="Faience", h=0.06):
    """Bolée / bowl, upright."""
    prof = [(r * 0.5, 0.0), (r * 0.55, 0.008), (r * 0.9, h * 0.5), (r, h), (r * 0.94, h), (r * 0.84, h * 0.55),
            (r * 0.45, 0.012), (0.0, 0.012)]
    P.bm(lathe(prof, segs=14, cap_bottom=True, cap_top=False, uv_keep=True), mat, uv="keep", matrix=T(x, y, z),
         smooth=True)


def jug(P, x, y, z, h=0.22, mat="Pewter", rot=0.0):
    r = h * 0.3
    prof = [(r * 0.75, 0.0), (r * 0.95, h * 0.1), (r, h * 0.4), (r * 0.7, h * 0.75), (r * 0.62, h * 0.85),
            (r * 0.8, h), (r * 0.74, h), (r * 0.55, h * 0.84), (0.0, h * 0.8)]
    S = P.sub(T(x, y, z) @ Rz(rot))
    S.bm(lathe(prof, segs=14, cap_bottom=True, cap_top=False), mat, smooth=True, scale=2.0)
    S.bm(tube([(r * 0.95, 0, h * 0.75), (r * 1.6, 0, h * 0.68), (r * 1.55, 0, h * 0.35), (r * 0.95, 0, h * 0.25)],
              0.008, 5), mat, smooth=True, scale=2.0)


def dresser(P, W=1.4, D=0.52, H=2.1, plates=True):
    """Vaisselier: buffet with two panelled doors and two drawers below, open plate rack above."""
    hb = 0.92
    # lower buffet
    P.box(-W / 2, -D / 2 + 0.03, 0.0, W / 2, D / 2, 0.1, W_DARK)                       # plinth
    P.box(-W / 2 + 0.01, -D / 2 + 0.03, 0.1, W / 2 - 0.01, D / 2, hb - 0.04, W_DARK)
    P.box(-W / 2 - 0.03, -D / 2 - 0.01, hb - 0.04, W / 2 + 0.03, D / 2 + 0.01, hb, W_DARK, bevel=0.01, segs=2)
    yfr = -D / 2 + 0.03
    for (x0, x1) in ((-W / 2 + 0.06, -0.01), (0.01, W / 2 - 0.06)):
        # drawer
        P.box(x0, yfr - 0.015, hb - 0.2, x1, yfr, hb - 0.07, W_DARK, bevel=0.004)
        knob(P, (x0 + x1) / 2, yfr - 0.015, hb - 0.135)
        # door
        raised_panel(P, x0, x1, 0.14, hb - 0.24, yfr, depth=0.016, border=0.05)
        rosette(P, (x0 + x1) / 2, yfr - 0.016, (0.14 + hb - 0.24) / 2, 0.075)
    escutcheon(P, -0.06, yfr - 0.017, hb - 0.42)
    escutcheon(P, 0.06, yfr - 0.017, hb - 0.42)
    # upper rack
    Dr = 0.26
    yb = D / 2 - Dr
    P.box(-W / 2 + 0.02, D / 2 - 0.02, hb, W / 2 - 0.02, D / 2, H - 0.12, W_DARK)       # back boards
    for sx in (-1, 1):
        P.box(sx * (W / 2 - 0.02) - 0.02, yb, hb, sx * (W / 2 - 0.02) + 0.02, D / 2, H - 0.12, W_DARK)
    shelves = [hb + 0.36, hb + 0.70]
    for zs in shelves + [H - 0.16]:
        P.box(-W / 2 + 0.02, yb, zs - 0.025, W / 2 - 0.02, D / 2 - 0.02, zs, W_DARK)
    for zs in [hb] + shelves:                                                        # plate rails
        P.box(-W / 2 + 0.02, yb - 0.005, zs + 0.06, W / 2 - 0.02, yb + 0.012, zs + 0.08, W_DARK)
    # cornice with scalloped (chantourné) apron
    P.box(-W / 2 - 0.04, yb - 0.04, H - 0.12, W / 2 + 0.04, D / 2 + 0.01, H - 0.04, W_DARK, bevel=0.01, segs=2)
    P.box(-W / 2 - 0.06, yb - 0.06, H - 0.04, W / 2 + 0.06, D / 2 + 0.01, H, W_DARK, bevel=0.012, segs=2)
    n = 7
    for i in range(n):
        x = -W / 2 + 0.05 + (W - 0.1) * (i + 0.5) / n
        P.bm(cyl_y(0.06, 0.0, 0.02, segs=12), W_DARK, matrix=T(x, yb - 0.02, H - 0.16) @ Matrix.Diagonal((1, 1, 0.6, 1)),
             scale=1.0)
    if plates:
        for zs in [hb] + shelves:
            k = 4
            for i in range(k):
                x = -W / 2 + 0.08 + (W - 0.16) * (i + 0.5) / k
                plate(P, x, yb + 0.07, zs + 0.004, r=0.115 if zs > hb else 0.13, tilt=-12)
        for i, x in enumerate((-0.45, -0.15, 0.15, 0.45)):     # bolées hanging under the top shelf
            bowl(P.sub(T(x, yb + 0.1, H - 0.31) @ Rx(180) @ T(0, 0, -0.06)), 0, 0, 0, r=0.055, h=0.05)
        jug(P, 0.48, -0.05, hb, h=0.24, mat="Faience", rot=200)
    P.col("Dresser", -W / 2 - 0.03, -D / 2 - 0.01, 0.0, W / 2 + 0.03, D / 2 + 0.01, hb)
    P.col("DresserRack", -W / 2 - 0.06, yb - 0.06, hb, W / 2 + 0.06, D / 2 + 0.01, H)


# ======================================================================== FIREPLACE
def marmite(P, x, y, z, r=0.17):
    """Cast-iron three-legged pot with bail handle. z = bottom of the belly."""
    h = r * 1.15
    prof = [(0.0, 0.0), (r * 0.6, 0.0), (r * 0.92, h * 0.25), (r, h * 0.5), (r * 0.93, h * 0.82), (r * 0.86, h * 0.92),
            (r * 0.92, h), (r * 0.86, h), (r * 0.8, h * 0.88), (r * 0.8, h * 0.4)]
    S = P.sub(T(x, y, z))
    S.bm(lathe(prof, segs=18, cap_top=False), "Iron", smooth=True, scale=2.0, smooth_angle=50)
    S.bm(lathe([(r * 0.8, h * 0.82), (0.0, h * 0.82)], segs=18, cap_top=False, cap_bottom=False), "Ash", scale=2.0)
    for k in range(3):
        a = 2 * PI * k / 3
        S.bm(tube([(math.cos(a) * r * 0.55, math.sin(a) * r * 0.55, r * 0.05),
                   (math.cos(a) * r * 0.62, math.sin(a) * r * 0.62, -0.06)], 0.014, 5), "Iron", scale=2.0)
    for sx in (-1, 1):
        S.box(sx * r * 0.98 - 0.015, -0.02, h * 0.85, sx * r * 0.98 + 0.015, 0.02, h * 0.95, "Iron", scale=2.0)
    pts = [(-r * 0.98, 0, h * 0.92)]
    for i in range(1, 12):
        a = PI * i / 12
        pts.append((-math.cos(a) * r * 0.98, 0, h * 0.92 + math.sin(a) * r * 0.9))
    pts.append((r * 0.98, 0, h * 0.92))
    S.bm(tube(pts, 0.007, 5), "Iron", scale=2.0)
    return z + h * 0.92 + r * 0.9       # top of the bail


def fireplace(P, Wf=1.6, Dp=0.62, Hj=1.3, hood_top=2.6, crane=True, fire=True, back_inset=0.0, name="Fireplace"):
    """Granite Breton fireplace against a wall (wall plane at y=+Dp/2): jambs with corbels, monolithic
    lintel, oak mantel shelf, limewashed hood up to the ceiling, hearth, firedogs, logs, crane + pot."""
    yb = Dp / 2                    # wall plane
    yf = -Dp / 2
    jw = 0.32
    xo = Wf / 2 + jw               # outer half width
    # hearth stone + inner hearth
    P.box(-xo - 0.05, yf - 0.32, 0.0, xo + 0.05, yb, 0.05, "Granite", bevel=0.01, segs=2, scale=0.5)
    # back (soot-blackened stones) and inner side faces
    P.box(-Wf / 2, yb - 0.04, 0.05, Wf / 2, yb, hood_top, "Soot", scale=0.5)
    # jambs: two stacked blocks + corbel (console) at the top
    for sx in (-1, 1):
        xa, xb = sorted((sx * Wf / 2, sx * xo))
        P.box(xa, yf, 0.05, xb, yb, 0.62, "GraniteSoot", bevel=0.012, segs=2, scale=0.5)
        P.box(xa, yf + 0.01, 0.62, xb, yb, Hj - 0.22, "GraniteSoot", bevel=0.012, segs=2, scale=0.5)
        P.box(xa + 0.01 * sx, yf, Hj - 0.22, xb, yb, Hj - 0.16, "Granite", bevel=0.01, segs=2, scale=0.5)
        # corbel: block stepping out toward the opening (quarter-round console)
        cx0 = sx * Wf / 2
        bmc = bmesh.new()
        n = 6
        pts = [(0.0, 0.0)] + [(0.14 * (1 - math.cos(PI / 2 * i / n)), 0.16 * math.sin(PI / 2 * i / n)) for i in range(1, n + 1)]
        pts += [(0.0, 0.16)]
        vs_a = [bmc.verts.new((cx0 - sx * u, yf, Hj - 0.32 + z)) for (u, z) in pts]
        vs_b = [bmc.verts.new((cx0 - sx * u, yb - 0.04, Hj - 0.32 + z)) for (u, z) in pts]
        bmc.faces.new(vs_a)
        bmc.faces.new(list(reversed(vs_b)))
        m = len(pts)
        for i in range(m):
            j = (i + 1) % m
            try:
                bmc.faces.new((vs_a[i], vs_a[j], vs_b[j], vs_b[i]))
            except ValueError:
                pass
        bmesh.ops.remove_doubles(bmc, verts=bmc.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bmc, faces=bmc.faces)
        P.bm(bmc, "Granite", scale=0.5)
    # lintel (manteau): one big granite beam with a chamfered lower edge
    lz0, lz1 = Hj - 0.16, Hj + 0.24
    prof = [(yf + 0.05, lz0), (yb - 0.04, lz0), (yb - 0.04, lz1), (yf - 0.02, lz1), (yf - 0.02, lz0 + 0.07)]
    P.bm(bm_prism(prof, -xo - 0.04, xo + 0.04), "Granite", scale=0.5)
    # oak mantel shelf
    P.box(-xo - 0.1, yf - 0.1, lz1, xo + 0.1, yb, lz1 + 0.06, "Wood_dark", bevel=0.008, segs=2, scale=1.0)
    # hood (hotte): limewashed, tapering in depth up to the ceiling
    hz0 = lz1 + 0.06
    hd0, hd1 = (yb - yf) - 0.04, 0.32
    prof = [(yb, hz0), (yb, hood_top), (yb - hd1, hood_top), (yb - hd0, hz0)]
    P.bm(bm_prism(prof, -xo, xo), "PlasterSoot", scale=0.5)
    # firedogs (chenets)
    for sx in (-1, 1):
        x = sx * 0.32
        P.box(x - 0.015, yf + 0.12, 0.05, x + 0.015, yf + 0.16, 0.42, "Iron", scale=2.0)
        P.bm(lathe([(0.03, 0), (0.03, 0.02), (0.0, 0.045)], segs=8), "Brass", matrix=T(x, yf + 0.14, 0.42), scale=2.0)
        P.box(x - 0.012, yf + 0.14, 0.12, x + 0.012, yb - 0.1, 0.15, "Iron", scale=2.0)
        P.box(x - 0.05, yf + 0.12, 0.05, x + 0.05, yf + 0.16, 0.07, "Iron", scale=2.0)
    if fire:
        # ash bed, embers, logs
        P.box(-Wf / 2 + 0.1, yf + 0.1, 0.05, Wf / 2 - 0.1, yb - 0.06, 0.07, "Ash", scale=1.0)
        for i, (x, y, r) in enumerate(((-0.18, 0.0, 0.07), (0.14, 0.03, 0.065), (0.0, -0.1, 0.12))):
            P.bm(lathe([(r, -0.012), (r * 0.6, 0.015), (0.0, 0.02)], segs=10), "Embers",
                 matrix=T(x, y + (yf + yb) / 2 + 0.03, 0.07), scale=1.0)
        logs = [((-0.5, -0.05, 0.13), 8, 0.055), ((0.48, 0.02, 0.13), -6, 0.06), ((-0.05, 0.05, 0.2), 92, 0.05)]
        for (x, y, z), ang, r in logs:
            bm = cyl_x(r, -0.28, 0.28, segs=8)
            P.bm(bm, "Wood_dark", matrix=T(x, y + (yf + yb) / 2, z) @ Rz(ang) @ Ry(4), scale=1.0)
            for sx in (-1, 1):   # glowing cut end
                P.bm(cyl_x(r * 0.85, -0.002, 0.002, segs=8), "Embers",
                     matrix=T(x, y + (yf + yb) / 2, z) @ Rz(ang) @ Ry(4) @ T(sx * 0.281, 0, 0), scale=1.0)
    top_z = 0.0
    if crane:
        # crane (potence / cremaillere): pivot post pinned in the left jamb, arm swung over the fire
        px, py = -Wf / 2 + 0.05, yb - 0.18
        ang = 35.0
        S = P.sub(T(px, py, 0))
        S.box(-0.015, -0.015, 0.25, 0.015, 0.015, Hj - 0.2, "Iron", scale=2.0)
        for z in (0.3, Hj - 0.26):
            S.box(-0.05, -0.012, z - 0.012, 0.0, 0.012, z + 0.012, "Iron", scale=2.0)   # gudgeons into the jamb
        A = S.sub(Rz(-ang))
        arm = 0.82
        A.box(0.0, -0.014, Hj - 0.3, arm, 0.014, Hj - 0.27, "Iron", scale=2.0)
        A.bm(tube([(0.02, 0, 0.5), (arm * 0.6, 0, Hj - 0.3)], 0.011, 5), "Iron", scale=2.0)
        A.bm(tube([(arm, 0, Hj - 0.27), (arm + 0.04, 0, Hj - 0.22)], 0.01, 5), "Iron", scale=2.0)   # curled end
        # hanging notched bar (cremaillere) + hook, pot below
        hx = arm * 0.72
        A.box(hx - 0.012, -0.004, 0.62, hx + 0.012, 0.004, Hj - 0.3, "Iron", scale=2.0)
        for k in range(8):
            z = 0.7 + k * 0.05
            A.box(hx - 0.02, -0.005, z, hx - 0.012, 0.005, z + 0.015, "Iron", scale=2.0)
        A.bm(tube([(hx, 0, 0.62), (hx, 0, 0.56), (hx + 0.03, 0, 0.54)], 0.006, 5), "Iron", scale=2.0)
        marmite(A, hx, 0.0, 0.2, r=0.16)
    P.col(name, -xo - 0.05, yf, 0.0, xo + 0.05, yb, hood_top)
    P.col(name + "Hearth", -xo - 0.05, yf - 0.32, 0.0, xo + 0.05, yf, 0.05)


# ====================================================================== BAR COUNTER
def bar_counter(P, L=2.7, D=0.62, H=1.06, ret=0.0):
    """Zinc-topped café counter: panelled oak front, black plinth, zinc top with a rolled front edge,
    brass foot rail, open shelves behind (barman side, +Y)."""
    yf, yb = -D / 2, D / 2
    P.box(-L / 2 + 0.02, yf + 0.04, 0.0, L / 2 - 0.02, yf + 0.06, 0.14, "BlackPaint")
    P.box(-L / 2, yf + 0.02, 0.14, L / 2, yf + 0.06, H - 0.06, W_OAK)               # front board
    for sx in (-1, 1):
        P.box(sx * L / 2 - 0.03, yf + 0.02, 0.0, sx * L / 2 + 0.03, yb, H - 0.06, W_OAK)  # end panels
    n = max(2, int(round(L / 0.55)))
    for i in range(n):
        x0 = -L / 2 + 0.06 + (L - 0.12) * i / n + 0.02
        x1 = -L / 2 + 0.06 + (L - 0.12) * (i + 1) / n - 0.02
        P.box(x0 - 0.04, yf, 0.14, x0 - 0.0, yf + 0.02, H - 0.08, W_OAK)            # pilaster strips
        raised_panel(P, x0 + 0.02, x1 - 0.02, 0.24, H - 0.2, yf + 0.02, mat=W_OAK, depth=0.014, border=0.04)
    P.box(-L / 2, yf, 0.14, L / 2, yf + 0.025, 0.2, W_OAK, bevel=0.006)            # skirting moulding
    P.box(-L / 2, yf, H - 0.12, L / 2, yf + 0.025, H - 0.06, W_OAK, bevel=0.006)
    # zinc top with rolled (bull-nose) front edge
    tz = H - 0.04
    prof = [(yb, tz), (yb, H), (yf + 0.03, H)]
    for i in range(1, 8):
        a = PI / 2 * i / 7
        prof.append((yf + 0.03 - math.sin(a) * 0.04, H - 0.04 + math.cos(a) * 0.04 - 0.0))
    prof += [(yf - 0.01, tz - 0.035), (yf + 0.03, tz - 0.035), (yf + 0.03, tz)]
    prof2 = []
    for p in prof:
        if not prof2 or (abs(p[0] - prof2[-1][0]) > 1e-5 or abs(p[1] - prof2[-1][1]) > 1e-5):
            prof2.append(p)
    P.bm(bm_prism(prof2, -L / 2 - 0.04, L / 2 + 0.04), "Zinc", scale=1.0, smooth=True, smooth_angle=30)
    # brass foot rail on brackets
    ry = yf - 0.12
    P.bm(cyl_x(0.022, -L / 2 + 0.05, L / 2 - 0.05, segs=12), "Brass", matrix=T(0, ry, 0.17), smooth=True, scale=2.0)
    for x in (-L / 2 + 0.12, 0.0, L / 2 - 0.12):
        P.bm(tube([(x, yf + 0.02, 0.22), (x, ry + 0.03, 0.2), (x, ry, 0.17)], 0.01, 6), "Brass", scale=2.0)
    # barman side: shelves under the top
    P.box(-L / 2 + 0.03, yb - 0.3, 0.1, L / 2 - 0.03, yb - 0.28, H - 0.06, W_OAK)   # inner carcass wall
    for z in (0.12, 0.5):
        P.box(-L / 2 + 0.03, yf + 0.06, z, L / 2 - 0.03, yb - 0.02, z + 0.025, W_OAK)
    P.col("Counter", -L / 2 - 0.04, yf - 0.02, 0.0, L / 2 + 0.04, yb, H)


# ==================================================================== small items
def bottle(P, x, y, z, kind=0, h=None):
    """Wine / aperitif / liqueur bottles with paper labels."""
    mats = ["BottleGreen", "BottleAmber", "BottleClear", "BottleGreen"]
    if kind == 0:    # wine
        h = h or 0.30
        r = 0.037
        prof = [(r * 0.9, 0), (r, 0.01), (r, h * 0.6), (r * 0.75, h * 0.7), (r * 0.36, h * 0.8), (r * 0.36, h * 0.97),
                (r * 0.45, h), (0.0, h)]
    elif kind == 1:  # squat aperitif
        h = h or 0.26
        r = 0.045
        prof = [(r * 0.9, 0), (r, 0.01), (r, h * 0.55), (r * 0.5, h * 0.72), (r * 0.32, h * 0.78), (r * 0.32, h * 0.97),
                (r * 0.4, h), (0.0, h)]
    elif kind == 2:  # clear eau-de-vie
        h = h or 0.28
        r = 0.035
        prof = [(r * 0.9, 0), (r, 0.01), (r, h * 0.7), (r * 0.4, h * 0.82), (r * 0.3, h * 0.97), (0.0, h)]
    else:            # cider / lambig, stoneware-ish
        h = h or 0.24
        r = 0.04
        prof = [(r * 0.9, 0), (r, 0.01), (r, h * 0.65), (r * 0.4, h * 0.8), (r * 0.3, h), (0.0, h)]
    S = P.sub(T(x, y, z))
    S.bm(lathe(prof, segs=10, cap_bottom=True), mats[kind], smooth=True, smooth_angle=50, scale=2.0)
    lz = h * 0.25
    S.bm(lathe([(r + 0.0015, lz), (r + 0.0015, lz + h * 0.25)], segs=10, cap_top=False, cap_bottom=False), "Paper",
         scale=2.0)
    S.bm(lathe([(r * 0.38, h * 0.97), (r * 0.38, h + 0.012), (0.0, h + 0.012)], segs=8, cap_bottom=False), "Wood_oak" if kind != 2 else "TabacRed", scale=2.0)


def glass(P, x, y, z, h=0.1, r=0.03):
    P.bm(lathe([(r * 0.7, 0), (r * 0.75, 0.006), (r, h), (r * 0.92, h), (r * 0.66, 0.008), (0.0, 0.008)],
               segs=10, cap_bottom=True, cap_top=False), "BottleClear", matrix=T(x, y, z), smooth=True, scale=2.0)


def candle(P, x, y, z):
    P.bm(lathe([(0.05, 0), (0.05, 0.01), (0.02, 0.02), (0.02, 0.03), (0.03, 0.035), (0.0, 0.035)], segs=10), "Brass",
         matrix=T(x, y, z), scale=2.0)
    P.bm(bm_cyl(0.011, 0.011, 0.13, segs=8), "Candle", matrix=T(x, y, z + 0.035), scale=2.0)


def loaf(P, x, y, z, r=0.13):
    """Round 'miche' of bread."""
    prof = [(0.0, 0.0), (r * 0.92, 0.0), (r, r * 0.12), (r * 0.98, r * 0.3), (r * 0.85, r * 0.5), (r * 0.6, r * 0.66),
            (r * 0.3, r * 0.74), (0.0, r * 0.76)]
    P.bm(lathe(prof, segs=20, cap_bottom=False), "Bread", matrix=T(x, y, z), smooth=True, scale=2.0)


def chair_breton(P, mat=W_OAK, name="Chair"):
    """Rush-seated ladder-back chair."""
    sh = 0.44
    w = 0.42
    for sx in (-1, 1):
        P.box(sx * w / 2 - 0.02, -w / 2, 0.0, sx * w / 2 + 0.02, -w / 2 + 0.04, sh, mat)          # front legs
        P.box(sx * w / 2 - 0.02, w / 2 - 0.04, 0.0, sx * w / 2 + 0.02, w / 2, 0.98, mat)          # back posts
        P.bm(lathe([(0.02, 0), (0.025, 0.02), (0.0, 0.04)], segs=6), mat, matrix=T(sx * w / 2, w / 2 - 0.02, 0.98))
    P.box(-w / 2, -w / 2, sh - 0.03, w / 2, w / 2, sh, "Hay", bevel=0.01, scale=2.0)              # rush seat
    for z in (0.62, 0.76, 0.9):
        P.box(-w / 2 + 0.02, w / 2 - 0.035, z - 0.03, w / 2 - 0.02, w / 2 - 0.01, z + 0.03, mat)
    for z in (0.12, 0.25):
        P.box(-w / 2 + 0.01, -w / 2 + 0.01, z - 0.01, w / 2 - 0.01, -w / 2 + 0.03, z + 0.01, mat)
        P.box(-w / 2 + 0.01, w / 2 - 0.03, z - 0.01, w / 2 - 0.01, w / 2 - 0.01, z + 0.01, mat)
    P.col(name, -w / 2 - 0.02, -w / 2, 0.0, w / 2 + 0.02, w / 2, sh)


def bentwood_chair(P, name="Chair"):
    """Thonet No.14-style bistro chair."""
    sh = 0.46
    r = 0.2
    mat = "Furn_black"
    P.bm(lathe([(r, sh - 0.03), (r, sh), (0.0, sh)], segs=18, cap_bottom=False), "Hay", scale=2.0)
    P.bm(lathe([(r + 0.01, sh - 0.05), (r + 0.015, sh - 0.01), (r - 0.01, sh - 0.01), (r - 0.012, sh - 0.05)], segs=18,
               cap_top=False, cap_bottom=False), mat, scale=1.0, smooth=True)
    for k in range(4):
        a = 2 * PI * k / 4 + PI / 4
        top = Vector((math.cos(a) * r * 0.85, math.sin(a) * r * 0.85, sh - 0.04))
        bot = Vector((math.cos(a) * r * 1.05, math.sin(a) * r * 1.05, 0.0))
        P.bm(tube([bot, (bot + top) / 2, top], 0.014, 6), mat, smooth=True)
    P.bm(lathe([(r * 0.82, 0.18), (r * 0.82, 0.2), (r * 0.79, 0.2), (r * 0.79, 0.18)], segs=16, cap_top=False,
               cap_bottom=False), mat, smooth=True)
    pts = []                                        # back loop
    for i in range(13):
        t = i / 12
        a = PI * t
        pts.append((math.cos(a) * r * 0.85, r * 0.8 + math.sin(a) * 0.03, sh + math.sin(a) * 0.42))
    P.bm(tube(pts, 0.013, 6), mat, smooth=True)
    P.bm(tube([(-r * 0.6, r * 0.82, sh), (-r * 0.5, r * 0.88, sh + 0.25), (r * 0.5, r * 0.88, sh + 0.25), (r * 0.6, r * 0.82, sh)],
              0.01, 5), mat, smooth=True)
    P.col(name, -r, -r, 0.0, r, r, sh)


def bistro_table(P, r=0.32, H=0.74, name="BistroTable"):
    """Round wooden top on a cast-iron pedestal."""
    P.bm(lathe([(r, H - 0.03), (r, H), (0.0, H)], segs=24, cap_bottom=True), W_OAK, scale=1.0)
    P.bm(lathe([(0.06, 0.0), (0.06, 0.02), (0.03, 0.08), (0.025, H - 0.06), (0.06, H - 0.03)], segs=10), "Iron",
         smooth=True, scale=2.0)
    for k in range(3):
        a = 2 * PI * k / 3
        P.bm(tube([(0, 0, 0.06), (math.cos(a) * 0.18, math.sin(a) * 0.18, 0.03), (math.cos(a) * 0.24, math.sin(a) * 0.24, 0.0)],
                  0.018, 5), "Iron", smooth=True, scale=2.0)
    P.col(name, -r, -r, 0.0, r, r, H)


def stool(P, name="Stool"):
    P.bm(lathe([(0.17, 0.42), (0.17, 0.46), (0.0, 0.46)], segs=14), W_OAK)
    for k in range(3):
        a = 2 * PI * k / 3
        P.bm(tube([(math.cos(a) * 0.1, math.sin(a) * 0.1, 0.43), (math.cos(a) * 0.17, math.sin(a) * 0.17, 0.0)], 0.017, 5),
             W_OAK)
    P.col(name, -0.17, -0.17, 0.0, 0.17, 0.17, 0.46)


def stove(P, flue_to=None, name="Stove"):
    """Round cast-iron 'Godin'-style stove on legs with a flue pipe. flue_to: (dy, z) where the pipe
    turns into the wall (local +Y)."""
    r = 0.2
    S = P
    S.bm(lathe([(0.0, 0.12), (r, 0.12), (r, 0.16), (r * 0.95, 0.18), (r * 0.95, 0.78), (r, 0.8), (r, 0.84),
                (r * 0.6, 0.9), (0.07, 0.92), (0.0, 0.92)], segs=20), "Iron", smooth=True, smooth_angle=40, scale=2.0)
    for k in range(4):
        a = 2 * PI * k / 4 + PI / 4
        S.bm(tube([(math.cos(a) * r * 0.8, math.sin(a) * r * 0.8, 0.13), (math.cos(a) * r * 1.0, math.sin(a) * r * 1.0, 0.0)],
                  0.016, 5), "Iron", scale=2.0)
    for z in (0.3, 0.6):     # decorative ribs
        S.bm(lathe([(r * 0.96, z), (r * 1.0, z + 0.01), (r * 1.0, z + 0.03), (r * 0.96, z + 0.04)], segs=20,
                   cap_top=False, cap_bottom=False), "Iron", scale=2.0)
    S.box(-0.08, -r - 0.01, 0.3, 0.08, -r + 0.02, 0.45, "Iron", scale=2.0)              # fire door
    S.bm(lathe([(0.012, 0), (0.012, 0.03), (0, 0.035)], segs=6), "Brass", matrix=T(0.05, -r - 0.01, 0.38) @ Rx(90))
    S.box(-0.05, -r - 0.012, 0.335, 0.03, -r - 0.008, 0.345, "Embers", scale=2.0)       # glow in the vent slit
    # flue pipe
    fz = flue_to[1] if flue_to else 1.8
    fy = flue_to[0] if flue_to else 0.0
    S.bm(bm_cyl(0.065, 0.065, fz - 0.92, segs=12), "Iron", matrix=T(0, 0, 0.92), smooth=True, scale=2.0)
    if flue_to:
        S.bm(cyl_y(0.065, 0.0, fy, segs=12), "Iron", matrix=T(0, 0, fz), smooth=True, scale=2.0)
        S.bm(cyl_y(0.11, fy - 0.01, fy, segs=12), "Iron", matrix=T(0, 0, fz), scale=2.0)  # wall rosette
    S.box(-0.03, -0.03, fz - 0.25, 0.03, 0.03, fz - 0.24, "Iron")                          # damper key
    P.col(name, -r, -r, 0.0, r, r, 0.92)


def churn(P, name="Churn"):
    """Upright staved butter churn (baratte) with plunger and iron hoops."""
    prof = [(0.0, 0.0), (0.2, 0.0), (0.2, 0.02), (0.165, 0.85), (0.06, 0.86), (0.0, 0.86)]
    P.bm(lathe(prof, segs=16), "Wood_oak", scale=1.0, smooth=True, smooth_angle=45)
    for z in (0.1, 0.45, 0.78):
        rr = 0.2 - 0.035 * z / 0.85 + 0.004
        P.bm(lathe([(rr, z), (rr, z + 0.035)], segs=16, cap_top=False, cap_bottom=False), "Iron", scale=2.0)
    P.bm(bm_cyl(0.016, 0.016, 0.5, segs=6), "Wood_oak", matrix=T(0, 0, 0.86), scale=1.0)
    P.box(-0.06, -0.012, 1.34, 0.06, 0.012, 1.37, "Wood_oak")
    P.col(name, -0.2, -0.2, 0.0, 0.2, 0.2, 0.9)


def ladder(P, H=2.6, W=0.48, lean=12.0, name="Ladder"):
    """Hay-loft ladder: two rails with round rungs, leaning towards +Y by `lean` degrees."""
    L = H / math.cos(math.radians(lean))
    S = P.sub(Rx(-lean))
    for sx in (-1, 1):
        S.box(sx * W / 2 - 0.03, -0.035, 0.0, sx * W / 2 + 0.03, 0.035, L, "Wood_grey")
    n = int(L / 0.28)
    for i in range(1, n + 1):
        z = i * 0.28
        S.bm(cyl_x(0.017, -W / 2, W / 2, segs=6), "Wood_grey", matrix=T(0, 0, z))
    top_y = L * math.sin(math.radians(lean))
    P.col(name, -W / 2 - 0.03, -0.04, 0.0, W / 2 + 0.03, max(0.04, top_y), 0.3)
    return top_y


def armoire(P, W=1.3, D=0.6, H=2.1, name="Armoire"):
    """Breton wardrobe: two panelled doors with rosettes and brass escutcheons, cornice."""
    yf = -D / 2
    P.box(-W / 2, yf + 0.02, 0.0, W / 2, D / 2, 0.12, W_DARK)
    P.box(-W / 2 + 0.01, yf + 0.02, 0.12, W / 2 - 0.01, D / 2, H - 0.12, W_DARK)
    P.box(-W / 2 - 0.05, yf - 0.03, H - 0.12, W / 2 + 0.05, D / 2 + 0.01, H, W_DARK, bevel=0.014, segs=2)
    for (x0, x1) in ((-W / 2 + 0.05, -0.01), (0.01, W / 2 - 0.05)):
        raised_panel(P, x0, x1, 0.16, 0.95, yf + 0.02, depth=0.016, border=0.05)
        raised_panel(P, x0, x1, 1.0, H - 0.18, yf + 0.02, depth=0.016, border=0.05)
        rosette(P, (x0 + x1) / 2, yf + 0.004, 1.45, 0.09)
        rosette(P, (x0 + x1) / 2, yf + 0.004, 0.55, 0.07)
    escutcheon(P, -0.05, yf - 0.0, 1.1)
    escutcheon(P, 0.05, yf - 0.0, 1.1)
    P.col(name, -W / 2 - 0.05, yf - 0.03, 0.0, W / 2 + 0.05, D / 2 + 0.01, H)


def bed(P, L=1.95, W=1.25, name="Bed"):
    """Simple wooden bed with high headboard, feather quilt (edredon)."""
    for sx in (-1, 1):
        for (y, h) in ((-L / 2, 0.75), (L / 2, 1.2)):
            P.box(sx * W / 2 - 0.035, y - 0.035, 0.0, sx * W / 2 + 0.035, y + 0.035, h, W_DARK, bevel=0.006)
    P.box(-W / 2, L / 2 - 0.02, 0.3, W / 2, L / 2 + 0.02, 1.1, W_DARK)
    P.box(-W / 2, -L / 2 - 0.02, 0.3, W / 2, -L / 2 + 0.02, 0.68, W_DARK)
    for sx in (-1, 1):
        P.box(sx * W / 2 - 0.025, -L / 2, 0.28, sx * W / 2 + 0.025, L / 2, 0.42, W_DARK)
    P.box(-W / 2 + 0.03, -L / 2 + 0.03, 0.36, W / 2 - 0.03, L / 2 - 0.03, 0.55, "Linen", bevel=0.05, segs=2)
    P.box(-W / 2 + 0.01, -L / 2 + 0.05, 0.53, W / 2 - 0.01, L / 2 - 0.45, 0.68, "Blanket", bevel=0.07, segs=2)
    P.box(-W / 2 + 0.08, L / 2 - 0.42, 0.55, W / 2 - 0.08, L / 2 - 0.06, 0.68, "Linen", bevel=0.06, segs=2)
    P.col(name, -W / 2 - 0.04, -L / 2 - 0.04, 0.0, W / 2 + 0.04, L / 2 + 0.04, 0.68)


def chest(P, L=1.0, D=0.5, H=0.6, name="Chest"):
    banc_coffre(P, L=L, D=D, H=H)
    P.cols[-1] = (name, P.cols[-1][1])


def washstand(P, name="Washstand"):
    W, D, H = 0.6, 0.42, 0.78
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box(sx * (W / 2 - 0.03) - 0.02, sy * (D / 2 - 0.03) - 0.02, 0.0, sx * (W / 2 - 0.03) + 0.02,
                  sy * (D / 2 - 0.03) + 0.02, H, W_OAK)
    P.box(-W / 2, -D / 2, H - 0.03, W / 2, D / 2, H, W_OAK)
    P.box(-W / 2 + 0.03, -D / 2 + 0.03, 0.12, W / 2 - 0.03, D / 2 - 0.03, 0.14, W_OAK)
    P.box(-W / 2, D / 2 - 0.02, H, W / 2, D / 2, H + 0.18, W_OAK)
    bowl(P, 0.0, -0.02, H, r=0.17, mat="EnamelWhite", h=0.09)
    jug(P, 0.0, -0.02, H + 0.012, h=0.26, mat="EnamelWhite", rot=30)
    P.col(name, -W / 2, -D / 2, 0.0, W / 2, D / 2, H)


def longcase_clock(P, name="Clock"):
    """Breton 'horloge' with a waisted case, glazed pendulum window and painted dial."""
    W, D, H = 0.5, 0.34, 2.15
    P.box(-W / 2, -D / 2, 0.0, W / 2, D / 2, 0.42, W_DARK)
    prof = []
    P.box(-W / 2 + 0.06, -D / 2 + 0.02, 0.42, W / 2 - 0.06, D / 2, 1.6, W_DARK)
    P.box(-W / 2 + 0.01, -D / 2 - 0.01, 1.6, W / 2 - 0.01, D / 2, 2.0, W_DARK)
    P.box(-W / 2 - 0.03, -D / 2 - 0.03, 2.0, W / 2 + 0.03, D / 2, H, W_DARK, bevel=0.012, segs=2)
    # waist: lenticle with brass pendulum
    P.box(-0.1, -D / 2 + 0.01, 0.6, 0.1, -D / 2 + 0.02, 1.5, "BlackPaint")
    P.bm(bm_cyl(0.008, 0.008, 0.55, segs=6), "Brass", matrix=T(0, -D / 2 + 0.005, 0.85))
    P.bm(cyl_y(0.07, -0.006, 0.0, segs=16), "Brass", matrix=T(0, -D / 2 + 0.005, 0.85))
    P.bm(bm_box(0, 0, 0, 0.2, 0.002, 0.9), "WindowGlass", matrix=T(0, -D / 2 + 0.002, 1.05))
    # dial
    P.bm(cyl_y(0.15, -0.012, 0.0, segs=24), "EnamelWhite", matrix=T(0, -D / 2 - 0.0, 1.8), scale=3.0)
    for k in range(12):
        a = 2 * PI * k / 12
        P.box(math.cos(a) * 0.125 - 0.006, -D / 2 - 0.0135, 1.8 + math.sin(a) * 0.125 - 0.006,
              math.cos(a) * 0.125 + 0.006, -D / 2 - 0.0115, 1.8 + math.sin(a) * 0.125 + 0.006, "BlackPaint")
    P.bm(cyl_y(0.165, -0.008, 0.0, segs=24), "Brass", matrix=T(0, -D / 2 + 0.003, 1.8), scale=2.0)
    P.box(-0.005, -D / 2 - 0.016, 1.8, 0.005, -D / 2 - 0.012, 1.92, "BlackPaint")
    P.bm(bm_box(0, 0, 0, 0.008, 0.004, 0.09, rot=(0, math.radians(60), 0)), "BlackPaint",
         matrix=T(0.04, -D / 2 - 0.016, 1.78))
    P.col(name, -W / 2 - 0.03, -D / 2 - 0.03, 0.0, W / 2 + 0.03, D / 2, H)


def bottle_shelf(P, L=2.2, levels=(1.25, 1.6, 1.95), D=0.24, rng=None, name="Shelf"):
    """Wall shelves (back at y=+D/2) full of bottles, with a mirror strip behind."""
    yb = D / 2
    P.box(-L / 2, yb - 0.02, levels[0] - 0.15, L / 2, yb, levels[-1] + 0.3, W_OAK)
    P.box(-L / 2 + 0.1, yb - 0.025, levels[0] - 0.12, L / 2 - 0.1, yb - 0.02, levels[0] + 0.25, "Mirror")
    for z in levels:
        P.box(-L / 2, -D / 2, z - 0.025, L / 2, yb, z, W_OAK, bevel=0.004)
        for sx in (-1, 1):
            P.box(sx * L / 2 - 0.02, -D / 2 + 0.02, z - 0.16, sx * L / 2, yb, z, W_OAK)
        x = -L / 2 + 0.08
        k = 0
        while x < L / 2 - 0.08:
            kind = rng.choice([0, 0, 1, 1, 2, 3]) if rng else k % 4
            if z == levels[0] and rng and rng.random() < 0.3:
                glass(P, x, -0.03, z, h=0.09)
                x += 0.08
                continue
            bottle(P, x, rng.uniform(-0.04, 0.03) if rng else 0.0, z, kind=kind,
                   h=None if not rng else None)
            x += 0.085 + (rng.uniform(0, 0.04) if rng else 0.02)
            k += 1
    P.box(-L / 2 - 0.02, -D / 2, levels[-1] + 0.25, L / 2 + 0.02, yb, levels[-1] + 0.3, W_OAK, bevel=0.006)


def poster(P, x, z, w, h, mat, y=0.0, rot=0.0):
    """Paper poster glued to the wall plane y (facing -Y), slight curl."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new((x - w / 2, y, z)), bm.verts.new((x + w / 2, y, z)), bm.verts.new((x + w / 2, y, z + h)),
          bm.verts.new((x - w / 2, y, z + h))]
    f = bm.faces.new(vs)
    for l, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l[uvl].uv = uv
    P.bm(bm, mat, uv="keep", matrix=T(x, 0, z + h / 2) @ Ry(rot) @ T(-x, 0, -z - h / 2))


def hay_pile(P, L=2.0, W=1.4, H=0.8, rng=None):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in bm.verts:
        c = v.co
        n = (math.sin(c.x * 5.1 + 1.3) * math.sin(c.y * 4.3) * 0.12 + math.sin(c.z * 7 + c.x * 3) * 0.06)
        z = max(c.z, -0.05)
        v.co = Vector((c.x * L / 2 * (1 + n), c.y * W / 2 * (1 + n), max(0.0, z) * H * (1 + n)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    P.bm(bm, "Hay", scale=1.0, smooth=True, smooth_angle=80)
    P.col("Hay", -L / 2 * 0.8, -W / 2 * 0.8, 0.0, L / 2 * 0.8, W / 2 * 0.8, H * 0.6)


def settle(P, L=1.4, name="Settle"):
    """High-backed fireside bench (banc a dossier)."""
    D, sh, bh = 0.45, 0.44, 1.15
    P.box(-L / 2, -D / 2, sh - 0.05, L / 2, D / 2 - 0.05, sh, W_DARK, bevel=0.006)
    P.box(-L / 2, D / 2 - 0.05, 0.0, L / 2, D / 2, bh, W_DARK)
    for sx in (-1, 1):
        P.box(sx * L / 2 - 0.03, -D / 2, 0.0, sx * L / 2 + 0.03, D / 2, 0.7, W_DARK)
    n = 3
    for i in range(n):
        x0 = -L / 2 + 0.05 + (L - 0.1) * i / n + 0.02
        x1 = -L / 2 + 0.05 + (L - 0.1) * (i + 1) / n - 0.02
        raised_panel(P, x0, x1, sh + 0.12, bh - 0.08, D / 2 - 0.05, depth=0.012)
    P.col(name, -L / 2 - 0.03, -D / 2, 0.0, L / 2 + 0.03, D / 2, sh)
    P.col(name + "Back", -L / 2 - 0.03, D / 2 - 0.06, 0.0, L / 2 + 0.03, D / 2, bh)


def kneading_trough(P, name="Maie"):
    """Maie: bread-kneading trough on legs."""
    L, D, H = 1.2, 0.55, 0.82
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box(sx * (L / 2 - 0.06) - 0.03, sy * (D / 2 - 0.06) - 0.03, 0.0, sx * (L / 2 - 0.06) + 0.03,
                  sy * (D / 2 - 0.06) + 0.03, H - 0.3, W_DARK)
    prof = [(-D / 2 + 0.06, H - 0.3), (D / 2 - 0.06, H - 0.3), (D / 2, H - 0.05), (-D / 2, H - 0.05)]
    P.bm(bm_prism(prof, -L / 2, L / 2), W_DARK, scale=1.0)
    P.box(-L / 2 - 0.02, -D / 2 - 0.02, H - 0.05, L / 2 + 0.02, D / 2 + 0.02, H, W_DARK, bevel=0.008)
    P.col(name, -L / 2 - 0.02, -D / 2 - 0.02, 0.0, L / 2 + 0.02, D / 2 + 0.02, H)
