"""Furniture and fittings for the Hôtel de la Plage interior (Kriegsmarine signals post, February 1944).

Same conventions as tools/blender/interiors/furniture.py: every builder takes a Put (placement + collision
collector), works in local space with the origin at floor level in the centre of the footprint and the front
facing -Y, and adds simple collision boxes through P.col(). Nothing carries insignia or maker's marks."""
import math
import os

import bmesh
from mathutils import Matrix, Vector

from geo import bm_box, bm_box_minmax, bm_cyl, bm_prism
from ihelp import cyl_x, cyl_y, lathe, tube
import furniture as fu
from furniture import T, Rx, Ry, Rz

PI = math.pi
OAK, CHESTNUT, BLACKWOOD = "Furn_oak", "Furn_chestnut", "Furn_black"
STEEL = "Metal_grey"
SAFE = "Metal_olive"


# ============================================================ materials / textures
def chart_texture(folder):
    """Procedural naval chart (pale sea with depth contours, buff land, graticule, a pencilled track).
    Deterministic; written once to <folder>/chart_albedo.png (1024 x 768)."""
    path = os.path.join(folder, "chart_albedo.png")
    if os.path.exists(path):
        return path
    import numpy as np
    from texlib import F, fbm, grid, mix, rgb, sstep, write_png
    h, w = 768, 1024
    X, Y = grid(h, w)
    coast = fbm(X, Y, 4, 5, 9301) * 0.55 + (X - 0.62) * 1.6 + 0.25 * np.sin(Y * 6.283 * 2.0) * 0.2
    land = coast > 0.0
    depth = -coast
    sea = mix(rgb((0.80, 0.84, 0.83), X.shape), rgb((0.66, 0.74, 0.77), X.shape), sstep(0.0, 0.7, depth)[..., None])
    buff = rgb((0.86, 0.80, 0.63), X.shape) * (0.95 + 0.05 * fbm(X, Y, 16, 3, 9302))[..., None]
    img = np.where(land[..., None], buff, sea)
    # depth contours (thin blue-grey lines) and the coastline (dark)
    for lvl in (0.08, 0.2, 0.36, 0.55):
        line = np.abs(depth - lvl) < 0.004
        img = np.where(line[..., None], rgb((0.36, 0.45, 0.52), X.shape), img)
    cl = np.abs(coast) < 0.006
    img = np.where(cl[..., None], rgb((0.16, 0.14, 0.12), X.shape), img)
    # graticule
    gx = (np.abs(((X * 8.0) % 1.0) - 0.5) > 0.4985) | (np.abs(((Y * 6.0) % 1.0) - 0.5) > 0.498)
    img = np.where(gx[..., None], img * 0.55, img)
    # border
    b = (X < 0.02) | (X > 0.98) | (Y < 0.026) | (Y > 0.974)
    b2 = ((X > 0.024) & (X < 0.027)) | ((X > 0.973) & (X < 0.976)) | ((Y > 0.031) & (Y < 0.035)) | ((Y > 0.965) & (Y < 0.969))
    img = np.where(b[..., None], rgb((0.90, 0.88, 0.80), X.shape), img)
    img = np.where(b2[..., None], rgb((0.15, 0.14, 0.13), X.shape), img)
    # soundings: scattered dark specks in the sea
    sp = (fbm(X, Y, 120, 1, 9303) > 0.42) & ~land
    img = np.where(sp[..., None], img * 0.5, img)
    # a pencilled track with position crosses, red crayon convoy route
    t = np.linspace(0, 1, 400)
    px = 0.1 + 0.5 * t
    py = 0.75 - 0.5 * t + 0.06 * np.sin(t * 9.0)
    for (cx, cy) in zip(px, py):
        ix, iy = int(cx * w), int((1 - cy) * h)
        img[max(0, iy - 1):iy + 2, max(0, ix - 1):ix + 2] = (0.62, 0.12, 0.08)
    for k in range(6):
        cx, cy = px[k * 70], py[k * 70]
        ix, iy = int(cx * w), int((1 - cy) * h)
        img[iy - 6:iy + 7, ix:ix + 1] = (0.1, 0.1, 0.1)
        img[iy:iy + 1, ix - 6:ix + 7] = (0.1, 0.1, 0.1)
    # paper ageing
    age = sstep(0.2, 0.9, fbm(X, Y, 3, 4, 9304))
    img = mix(img, img * rgb((0.88, 0.82, 0.68), X.shape), age[..., None] * 0.5)
    write_png(path, img.astype(F))
    return path


def install_materials():
    """Materials only this building uses (after geo.clear_mat_cache)."""
    import geo
    import textures as envtex
    import ttex
    tm = geo.tex_mat
    E = envtex.TEX_DIR
    chart_texture(ttex.TEX_DIR)
    tm("Blackout", "burlap_albedo.png", "burlap_normal.png", "burlap_orm.png", folder=E, tint=(0.11, 0.105, 0.12),
       nstrength=0.6)
    tm("Wool_navy", "burlap_albedo.png", "burlap_normal.png", "burlap_orm.png", folder=E, tint=(0.075, 0.085, 0.14),
       nstrength=0.35)
    tm("Chart", "chart_albedo.png", folder=ttex.TEX_DIR, rough=0.85)
    tm("Felt", "burlap_albedo.png", "burlap_normal.png", "burlap_orm.png", folder=E, tint=(0.16, 0.24, 0.16),
       nstrength=0.3)
    geo.flat_mat("Bakelite", (0.035, 0.028, 0.022), rough=0.35)
    geo.flat_mat("DialFace", (0.72, 0.68, 0.55), rough=0.4)
    geo.flat_mat("LampRed", (0.35, 0.05, 0.03), rough=0.2)
    geo.flat_mat("Lampboard", (0.55, 0.50, 0.36), rough=0.15)
    geo.flat_mat("Chalk", (0.62, 0.62, 0.58), rough=0.9)


# ================================================================== lamps
def pendant(P, drop=0.6, shade="EnamelGreen"):
    """Enamelled conical shade on a flex from the ceiling rose. Origin = bulb."""
    P.bm(tube([(0, 0, 0.06), (0, 0, drop)], 0.004, 4), "BlackPaint", scale=2.0)
    P.bm(lathe([(0.0, drop), (0.05, drop - 0.01), (0.05, drop - 0.03), (0.0, drop - 0.035)], segs=10), "Bakelite")
    P.bm(lathe([(0.03, 0.09), (0.04, 0.06), (0.15, -0.03), (0.18, -0.06)], segs=16, cap_top=False, cap_bottom=False),
         shade, smooth=True)
    P.bm(lathe([(0.177, -0.058), (0.147, -0.028), (0.037, 0.057), (0.027, 0.087)], segs=16, cap_top=False,
               cap_bottom=False), "EnamelWhite", smooth=True)
    P.bm(lathe([(0.0, -0.05), (0.022, -0.045), (0.028, -0.02), (0.016, 0.0), (0.012, 0.03), (0.0, 0.03)], segs=10),
         "LampGlow", smooth=True)


def bare_bulb(P, drop=0.5):
    """Cellar bulb on a flex. Origin = bulb."""
    P.bm(tube([(0, 0, 0.05), (0, 0, drop)], 0.004, 4), "BlackPaint", scale=2.0)
    P.bm(bm_cyl(0.016, 0.016, 0.05, segs=8), "Bakelite", matrix=T(0, 0, 0.02))
    P.bm(lathe([(0.0, -0.05), (0.025, -0.04), (0.03, -0.01), (0.014, 0.02), (0.0, 0.02)], segs=10), "LampGlow",
         smooth=True)


def desk_lamp(P, shade="EnamelGreen"):
    """Adjustable office lamp standing on a desk. Origin = base centre on the desk top; bulb at (0,-0.12,0.38)."""
    P.bm(lathe([(0.0, 0.0), (0.075, 0.0), (0.07, 0.02), (0.03, 0.035), (0.0, 0.035)], segs=14), "Bakelite", smooth=True)
    P.bm(tube([(0, 0, 0.03), (0, 0.02, 0.3), (0, -0.1, 0.42)], 0.008, 5), "Brass", scale=2.0)
    M = T(0, -0.13, 0.4) @ Rx(-35)
    P.bm(lathe([(0.02, 0.06), (0.03, 0.04), (0.09, -0.03), (0.1, -0.05)], segs=14, cap_top=True, cap_bottom=False), shade,
         smooth=True, matrix=M)
    P.bm(lathe([(0.0, -0.04), (0.02, -0.035), (0.022, -0.01), (0.0, 0.0)], segs=8), "LampGlow", matrix=M)
    return (0.0, -0.13, 0.37)


# ============================================================== furniture
def desk(P, L=1.4, D=0.75, H=0.76, mat=OAK, name="Desk", pedestals=True):
    """Office desk: top with a moulded edge, one or two drawer pedestals, modesty panel at the back."""
    P.box(-L / 2, -D / 2, H - 0.035, L / 2, D / 2, H, mat, bevel=0.008, segs=2)
    pw = 0.42
    for sx in ((-1, 1) if pedestals else (1,)):
        x0, x1 = sorted((sx * (L / 2 - 0.02), sx * (L / 2 - 0.02 - pw)))
        P.box(x0, -D / 2 + 0.03, 0.0, x1, D / 2 - 0.02, H - 0.035, mat)
        for k in range(3):
            z0, z1 = 0.06 + k * 0.215, 0.06 + (k + 1) * 0.215 - 0.015
            P.box(x0 + 0.02, -D / 2 + 0.015, z0, x1 - 0.02, -D / 2 + 0.03, z1, mat, bevel=0.004)
            fu.knob(P, (x0 + x1) / 2, -D / 2 + 0.015, (z0 + z1) / 2, mat="Brass", r=0.011)
    if not pedestals:
        for y in (-D / 2 + 0.05, D / 2 - 0.05):
            P.box(-L / 2 + 0.03, y - 0.025, 0.0, -L / 2 + 0.08, y + 0.025, H - 0.035, mat)
    P.box(-L / 2 + 0.03, D / 2 - 0.03, 0.25, L / 2 - 0.03, D / 2 - 0.01, H - 0.035, mat)
    P.box(-L / 2 + pw, -D / 2 + 0.04, H - 0.13, L / 2 - pw, -D / 2 + 0.06, H - 0.035, mat)   # centre drawer front
    P.col(name, -L / 2, -D / 2, 0.0, L / 2, D / 2, H)


def office_chair(P, name="Chair"):
    """Plain oak office chair with a curved back rail (sitter faces -Y)."""
    sh, w = 0.46, 0.44
    for sx in (-1, 1):
        P.box(sx * w / 2 - 0.022, -w / 2, 0.0, sx * w / 2 + 0.022, -w / 2 + 0.044, sh, OAK)
        P.box(sx * w / 2 - 0.022, w / 2 - 0.05, 0.0, sx * w / 2 + 0.022, w / 2 - 0.006, 0.86, OAK)
    P.box(-w / 2, -w / 2, sh - 0.035, w / 2, w / 2, sh, OAK, bevel=0.01)
    for z in (0.62, 0.8):
        P.box(-w / 2 + 0.01, w / 2 - 0.04, z - 0.035, w / 2 - 0.01, w / 2 - 0.012, z + 0.035, OAK)
    P.box(-w / 2 + 0.02, -w / 2 + 0.01, 0.15, w / 2 - 0.02, -w / 2 + 0.03, 0.18, OAK)
    P.col(name, -w / 2 - 0.02, -w / 2, 0.0, w / 2 + 0.02, w / 2, sh)


def papers(P, x, y, z, n=3, rng=None, w=0.21, h=0.297, rot=0.0):
    for k in range(n):
        a = rot + ((rng.uniform(-8, 8)) if rng else k * 4.0)
        dx = rng.uniform(-0.03, 0.03) if rng else 0.0
        S = P.sub(T(x + dx, y, z + 0.002 + k * 0.0015) @ Rz(a))
        S.box(-w / 2, -h / 2, 0.0, w / 2, h / 2, 0.001, "Paper", scale=2.0)


def book(P, x, y, z, w=0.17, d=0.24, h=0.035, rot=0.0, mat=CHESTNUT, open_=False):
    S = P.sub(T(x, y, z) @ Rz(rot))
    if open_:
        for s in (-1, 1):
            S.box(min(0, s * w), -d / 2, 0.0, max(0, s * w), d / 2, 0.006, mat)
            S.bm(bm_box_minmax(min(0, s * (w - 0.01)), -d / 2 + 0.01, 0.006, max(0, s * (w - 0.01)), d / 2 - 0.01, 0.018),
                 "Paper", scale=2.0)
    else:
        S.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, mat, bevel=0.003)
        S.box(-w / 2 + 0.008, -d / 2 - 0.001, 0.004, w / 2 + 0.001, d / 2 - 0.006, h - 0.004, "Paper", scale=2.0)


def telephone(P, x, y, z, rot=0.0):
    """Field/desk telephone: bakelite base with a crank-less dial plate, handset on the cradle."""
    S = P.sub(T(x, y, z) @ Rz(rot))
    S.box(-0.09, -0.11, 0.0, 0.09, 0.09, 0.07, "Bakelite", bevel=0.015, segs=2)
    S.bm(cyl_y(0.045, -0.115, -0.105, segs=14), "DialFace", matrix=T(0, 0, 0.04) @ Rx(-25))
    for sx in (-1, 1):
        S.box(sx * 0.06 - 0.012, -0.02, 0.07, sx * 0.06 + 0.012, 0.02, 0.1, "Bakelite")
    S.bm(cyl_x(0.016, -0.09, 0.09, segs=8), "Bakelite", matrix=T(0, 0, 0.11))
    for sx in (-1, 1):
        S.bm(bm_cyl(0.026, 0.03, 0.035, segs=10), "Bakelite", matrix=T(sx * 0.09, 0, 0.09) @ Ry(sx * 90))
    S.bm(tube([(0.09, 0.09, 0.02), (0.15, 0.14, 0.0), (0.12, 0.25, -0.0)], 0.004, 4), "Bakelite")


def typewriter(P):
    """Standard office typewriter (four key rows, segment shift, platen with a sheet in). Front -Y; origin base."""
    P.box(-0.21, -0.17, 0.0, 0.21, 0.17, 0.045, "Bakelite", bevel=0.01, segs=1)
    prof = [(-0.17, 0.045), (0.12, 0.045), (0.12, 0.16), (0.02, 0.16), (-0.17, 0.075)]
    P.bm(bm_prism(prof, -0.2, 0.2), "Bakelite", scale=2.0)
    for r in range(4):
        n = 11 if r < 3 else 10
        y = -0.14 + r * 0.04
        z = 0.08 + r * 0.02
        for k in range(n):
            x = (k - (n - 1) / 2) * 0.031 + (r % 2) * 0.008
            P.bm(tube([(x, y, z - 0.02), (x, y + 0.004, z)], 0.0035, 4), "Iron", scale=4.0)
            P.bm(bm_cyl(0.0095, 0.0095, 0.006, segs=8), "Bakelite", matrix=T(x, y, z))
            P.bm(bm_cyl(0.0075, 0.0075, 0.0008, segs=8), "DialFace", matrix=T(x, y, z + 0.006))
    P.box(-0.1, -0.165, 0.065, 0.1, -0.135, 0.075, "Iron")                       # space bar
    P.bm(lathe([(0.0, 0.0), (0.12, 0.0), (0.13, 0.02), (0.0, 0.025)], segs=16, cap_top=True), "Iron",
         matrix=T(0, 0.02, 0.16) @ Matrix.Diagonal((1.0, 0.6, 0.2, 1.0)))           # type-bar basket
    P.bm(cyl_x(0.032, -0.24, 0.24, segs=14), "Bakelite", matrix=T(0, 0.11, 0.2), smooth=True)   # platen
    for sx in (-1, 1):
        P.bm(cyl_x(0.04, -0.012, 0.012, segs=12), "Bakelite", matrix=T(sx * 0.255, 0.11, 0.2))  # knobs
        P.box(sx * 0.2 - 0.01, 0.06, 0.16, sx * 0.2 + 0.01, 0.16, 0.21, "Iron")
    P.bm(tube([(-0.25, 0.08, 0.22), (-0.3, 0.02, 0.24), (-0.32, -0.02, 0.24)], 0.004, 4), "Iron")   # return lever
    sheet = bm_box_minmax(-0.105, 0.13, 0.2, 0.105, 0.132, 0.44)
    P.bm(sheet, "Paper", scale=2.0, matrix=T(0, 0.0, 0.0) @ T(0, 0.13, 0.2) @ Rx(-12) @ T(0, -0.13, -0.2))
    P.col("Typewriter", -0.26, -0.18, 0.0, 0.26, 0.18, 0.22)


def cipher_machine(P):
    """Naval rotor cipher machine of the 1943 four-wheel type, unbranded: oak box with the lid hinged up at
    the back, steel deck with 26 keys (9/8/9), a 26-window lampboard, four rotor thumbwheels through the cover,
    plugboard in the front flap. Front -Y; origin at the base centre."""
    W, D, H = 0.34, 0.30, 0.15
    # wooden case
    P.box(-W / 2, -D / 2, 0.0, W / 2, D / 2, H, OAK, bevel=0.006, segs=1)
    P.box(-W / 2 - 0.004, -D / 2 - 0.004, 0.0, W / 2 + 0.004, D / 2 + 0.004, 0.012, OAK)
    for sx in (-1, 1):
        P.box(sx * (W / 2 + 0.002) - 0.006, -0.03, 0.05, sx * (W / 2 + 0.002) + 0.006, 0.03, 0.11, "Iron", scale=4.0)   # catches
    # lid: hinged at the back top edge, opened past vertical
    S = P.sub(T(0, D / 2, H) @ Rx(80))
    S.box(-W / 2, 0.0, 0.0, W / 2, D - 0.02, 0.012, OAK, bevel=0.003)
    S.box(-W / 2 + 0.02, 0.02, 0.012, W / 2 - 0.02, D - 0.04, 0.016, "Paper", scale=2.0)     # instructions sheet
    # steel deck
    P.box(-W / 2 + 0.012, -D / 2 + 0.07, H - 0.012, W / 2 - 0.012, D / 2 - 0.012, H - 0.002, "Bakelite")
    # keyboard (front of the deck), round caps on stems
    rows = [9, 8, 9]
    for r, n in enumerate(rows):
        y = -D / 2 + 0.085 + r * 0.03
        for k in range(n):
            x = (k - (n - 1) / 2) * 0.034 + (0.0 if r != 1 else 0.0)
            P.bm(bm_cyl(0.0035, 0.0035, 0.02, segs=4), "Iron", matrix=T(x, y, H - 0.002))
            P.bm(lathe([(0.0, 0.0), (0.012, 0.0), (0.012, 0.006), (0.0, 0.007)], segs=8), "Bakelite",
                 matrix=T(x, y, H + 0.018))
            P.bm(bm_cyl(0.0095, 0.0095, 0.0006, segs=8), "DialFace", matrix=T(x, y, H + 0.0245))
    # lampboard: raised plate with 26 round windows
    yl0 = -D / 2 + 0.185
    P.box(-W / 2 + 0.02, yl0 - 0.012, H, W / 2 - 0.02, yl0 + 0.068, H + 0.012, "Bakelite")
    for r, n in enumerate(rows):
        y = yl0 + r * 0.022
        for k in range(n):
            x = (k - (n - 1) / 2) * 0.034
            P.bm(bm_cyl(0.0095, 0.0095, 0.003, segs=10), "Lampboard", matrix=T(x, y, H + 0.012))
    # rotor cover with four thumbwheels poking through and their letter windows
    yc = D / 2 - 0.05
    P.box(-W / 2 + 0.03, yc - 0.035, H, W / 2 - 0.03, yc + 0.035, H + 0.03, STEEL, bevel=0.004, scale=4.0)
    for k in range(4):
        x = -0.06 + k * 0.04
        P.bm(cyl_x(0.03, -0.006, 0.006, segs=16), "Iron", matrix=T(x + 0.012, yc + 0.005, H + 0.02), smooth=True,
             scale=4.0)
        P.box(x - 0.008, yc - 0.03, H + 0.03, x + 0.008, yc - 0.012, H + 0.031, "DialFace")
    P.bm(cyl_x(0.012, -0.014, 0.014, segs=10), "Iron", matrix=T(W / 2 - 0.045, yc, H + 0.036))     # release lever
    # front flap down: plugboard with 26 socket pairs and two patch cables
    Fp = P.sub(T(0, -D / 2, 0.012) @ Rx(80))
    Fp.box(-W / 2 + 0.005, -0.004, 0.0, W / 2 - 0.005, 0.004, 0.1, OAK)
    Fp.box(-W / 2 + 0.02, -0.006, 0.01, W / 2 - 0.02, -0.004, 0.09, "Bakelite")
    for r in range(3):
        n = rows[r]
        for k in range(n):
            x = (k - (n - 1) / 2) * 0.032
            for dz in (0.0, 0.009):
                Fp.box(x - 0.0025, -0.0065, 0.022 + r * 0.025 + dz, x + 0.0025, -0.006, 0.027 + r * 0.025 + dz, "DialFace")
    for (xa, xb) in ((-0.08, 0.05), (0.02, -0.11)):
        a = Fp.pt(xa, -0.01, 0.05)
        b = Fp.pt(xb, -0.01, 0.025)
        mid = (a + b) / 2 + Vector((0, -0.04, -0.03))
        P.mb.add_bm(tube([a, mid, b], 0.0025, 4), "LampRed", scale=4.0)
    P.col("CipherCol", -W / 2 - 0.01, -D / 2 - 0.1, 0.0, W / 2 + 0.01, D / 2 + 0.02, H + 0.04)


def radio_set(P, W=0.5, D=0.36, H=0.3, dials=1, knobs=4, meter=True, mat=STEEL, name="Radio"):
    """Naval radio receiver/transmitter: grey steel case, black front panel with a big tuning dial, knobs,
    a moving-coil meter, carrying handles, ventilation louvres. Front -Y; origin at the base centre."""
    P.box(-W / 2, -D / 2 + 0.02, 0.0, W / 2, D / 2, H, mat, bevel=0.008, scale=2.0)
    P.box(-W / 2 + 0.01, -D / 2, 0.01, W / 2 - 0.01, -D / 2 + 0.02, H - 0.01, "BlackPaint")
    yf = -D / 2
    for k in range(dials):
        x = -W / 2 + 0.11 + k * 0.2
        z = H * 0.58
        P.bm(cyl_y(0.075, yf - 0.004, yf, segs=20), "DialFace", matrix=T(x, 0, z), scale=4.0)
        P.bm(cyl_y(0.082, yf - 0.002, yf, segs=20), "Iron", matrix=T(x, 0, z), scale=4.0)
        P.box(x - 0.002, yf - 0.006, z - 0.002, x + 0.06, yf - 0.005, z + 0.002, "LampRed")       # pointer
        P.bm(cyl_y(0.022, yf - 0.03, yf - 0.004, segs=12), "Bakelite", matrix=T(x, 0, H * 0.18), smooth=True)
    for k in range(knobs):
        x = W / 2 - 0.05 - (k % 2) * 0.075
        z = H * (0.25 if k < 2 else 0.6) if dials else H * (0.3 + 0.25 * (k // 2))
        P.bm(cyl_y(0.016, yf - 0.025, yf, segs=10), "Bakelite", matrix=T(x, 0, z))
        P.bm(cyl_y(0.019, yf - 0.006, yf, segs=10), "Bakelite", matrix=T(x, 0, z))
    if meter:
        x = W / 2 - 0.09 if dials else 0.0
        P.box(x - 0.045, yf - 0.004, H - 0.1, x + 0.045, yf, H - 0.03, "DialFace")
        P.box(x - 0.05, yf - 0.006, H - 0.104, x + 0.05, yf - 0.002, H - 0.098, "Iron")
        P.box(x - 0.001, yf - 0.006, H - 0.095, x + 0.025, yf - 0.005, H - 0.035, "BlackPaint")
    for k in range(5):                                               # louvres on the top
        y = -D / 2 + 0.07 + k * 0.05
        P.box(-W / 2 + 0.06, y - 0.008, H, W / 2 - 0.06, y + 0.008, H + 0.004, "BlackPaint")
    for sx in (-1, 1):                                               # handles
        x = sx * (W / 2 - 0.05)
        P.bm(tube([(x, yf, H * 0.25), (x, yf - 0.04, H * 0.3), (x, yf - 0.04, H * 0.7), (x, yf, H * 0.75)], 0.006, 5),
             "Iron", scale=4.0)
    P.col(name, -W / 2, -D / 2 - 0.05, 0.0, W / 2, D / 2, H)


def headphones(P, x, y, z, rot=0.0):
    S = P.sub(T(x, y, z) @ Rz(rot))
    for sx in (-1, 1):
        S.bm(cyl_x(0.04, -0.012, 0.012, segs=12), "Bakelite", matrix=T(sx * 0.07, 0, 0.04) @ Ry(90) @ Rx(90))
    pts = [(math.cos(a) * 0.075, 0.0, 0.04 + math.sin(a) * 0.08) for a in [i * PI / 10 for i in range(11)]]
    S.bm(tube(pts, 0.004, 4), "Iron")
    S.bm(tube([(0.07, 0, 0.02), (0.15, 0.05, 0.0), (0.3, 0.1, 0.0)], 0.003, 4), "Bakelite")


def morse_key(P, x, y, z, rot=0.0):
    S = P.sub(T(x, y, z) @ Rz(rot))
    S.box(-0.05, -0.09, 0.0, 0.05, 0.07, 0.015, "Bakelite", bevel=0.004)
    S.box(-0.006, -0.06, 0.015, 0.006, 0.06, 0.03, "Brass", scale=4.0)
    S.bm(bm_cyl(0.022, 0.02, 0.012, segs=12), "Bakelite", matrix=T(0, -0.075, 0.03))
    S.bm(bm_cyl(0.004, 0.004, 0.03, segs=6), "Brass", matrix=T(0.0, 0.04, 0.015))


def radio_bench(P, L=3.6, D=0.75, H=0.78, rng=None):
    """Operators' bench along a wall: oak top on steel trestles, shelf over, three sets, a transmitter
    with its power unit under the bench, headphones, morse keys, log books, a desk lamp."""
    P.box(-L / 2, -D / 2, H - 0.04, L / 2, D / 2, H, OAK, bevel=0.006)
    for x in (-L / 2 + 0.08, 0.0, L / 2 - 0.08):
        P.box(x - 0.03, -D / 2 + 0.05, 0.0, x + 0.03, D / 2 - 0.03, H - 0.04, STEEL, scale=2.0)
        P.box(x - 0.03, -D / 2 + 0.05, 0.08, x + 0.03, D / 2 - 0.03, 0.12, STEEL, scale=2.0)
    P.box(-L / 2 + 0.05, D / 2 - 0.05, 0.08, L / 2 - 0.05, D / 2 - 0.03, H - 0.04, STEEL, scale=2.0)
    # shelf on brackets over the back of the bench
    zs = H + 0.48
    P.box(-L / 2 + 0.05, D / 2 - 0.32, zs, L / 2 - 0.05, D / 2, zs + 0.03, OAK)
    for x in (-L / 2 + 0.1, 0.0, L / 2 - 0.1):
        P.box(x - 0.015, D / 2 - 0.3, H, x + 0.015, D / 2 - 0.27, zs, STEEL, scale=2.0)
    # sets: transmitter left, two receivers in the middle (one on the shelf), a direction finder right
    radio_set(P.sub(T(-L / 2 + 0.45, D / 2 - 0.22, H)), W=0.62, D=0.42, H=0.44, dials=2, knobs=4, name="Transmitter")
    radio_set(P.sub(T(-0.25, D / 2 - 0.2, H)), W=0.52, D=0.36, H=0.3, dials=1, knobs=4, name="Receiver")
    radio_set(P.sub(T(-0.25, D / 2 - 0.16, zs + 0.03)), W=0.52, D=0.3, H=0.27, dials=1, knobs=2, name="Receiver2")
    radio_set(P.sub(T(0.55, D / 2 - 0.2, H)), W=0.46, D=0.36, H=0.28, dials=1, knobs=2, meter=False, name="Receiver3")
    radio_set(P.sub(T(1.0, D / 2 - 0.16, zs + 0.03)), W=0.4, D=0.28, H=0.22, dials=0, knobs=4, name="Wavemeter")
    radio_set(P.sub(T(-L / 2 + 0.45, 0.0, 0.12)), W=0.6, D=0.45, H=0.42, dials=0, knobs=2, name="PowerUnit")
    # loose kit on the bench
    headphones(P, -0.25, -0.18, H, rot=10)
    headphones(P, 0.6, -0.15, H, rot=-15)
    morse_key(P, -0.9, -0.2, H, rot=5)
    morse_key(P, 0.95, -0.2, H, rot=-8)
    book(P, 0.15, -0.15, H, open_=True, rot=3)
    book(P, 1.05, -0.12, H, w=0.21, d=0.3, rot=-6, mat="BlackPaint")
    papers(P, -0.6, -0.12, H, n=2, rng=rng, rot=8)
    P.bm(bm_cyl(0.004, 0.004, 0.15, segs=6), "Iron", matrix=T(0.32, -0.2, H + 0.003) @ Ry(88) @ Rx(10))   # pencil
    lamp = desk_lamp(P.sub(T(L / 2 - 0.2, 0.05, H) @ Rz(25)))
    # cables: from the sets up the wall and over the shelf
    for x in (-L / 2 + 0.3, -0.4, 0.4):
        P.bm(tube([(x, D / 2 - 0.02, H + 0.2), (x + 0.05, D / 2 - 0.01, zs + 0.6), (x + 0.1, D / 2 - 0.01, zs + 1.3)],
                  0.007, 4), "Bakelite")
    P.col("RadioBenchCol", -L / 2, -D / 2, 0.0, L / 2, D / 2, H)
    P.col("RadioShelf", -L / 2, D / 2 - 0.32, H, L / 2, D / 2, zs + 0.35)
    return (L / 2 - 0.2, 0.05, H)


def steel_cabinet(P, W=0.82, D=0.62, H=1.6):
    """Panzerschrank: heavy riveted steel key-sheet cabinet with one armoured door, a combination dial, a key
    escutcheon and a T-handle; painted dark green. Front -Y; origin at the centre of the footprint at floor
    level (door face at y = -D/2)."""
    yf = -D / 2
    P.box(-W / 2, yf + 0.01, 0.0, W / 2, D / 2, 0.06, "BlackPaint")                         # plinth
    P.box(-W / 2, yf + 0.03, 0.06, W / 2, D / 2, H, SAFE, bevel=0.012, segs=2, scale=2.0)
    P.box(-W / 2 - 0.01, yf + 0.02, H - 0.05, W / 2 + 0.01, D / 2 + 0.005, H, SAFE, bevel=0.01, scale=2.0)
    # door slab, slightly proud, with a raised frame
    dz0, dz1 = 0.12, H - 0.1
    dx0, dx1 = -W / 2 + 0.05, W / 2 - 0.05
    P.box(dx0, yf, dz0, dx1, yf + 0.03, dz1, SAFE, bevel=0.006, scale=2.0)
    for (a0, a1, b0, b1) in ((dx0, dx1, dz0, dz0 + 0.04), (dx0, dx1, dz1 - 0.04, dz1), (dx0, dx0 + 0.04, dz0, dz1),
                             (dx1 - 0.04, dx1, dz0, dz1)):
        P.box(a0, yf - 0.008, b0, a1, yf, b1, SAFE, scale=2.0)
    for (a, b) in ((dx0 + 0.02, dz0 + 0.02), (dx1 - 0.02, dz0 + 0.02), (dx0 + 0.02, dz1 - 0.02), (dx1 - 0.02, dz1 - 0.02)):
        P.bm(cyl_y(0.008, yf - 0.012, yf - 0.008, segs=6), "Iron", matrix=T(a, 0, b), scale=4.0)       # rivets
    # hinges (left), combination dial, T-handle, key escutcheon
    for z in (dz0 + 0.2, dz1 - 0.2):
        P.bm(bm_cyl(0.022, 0.022, 0.16, segs=10), "Iron", matrix=T(-W / 2 + 0.03, yf - 0.005, z - 0.08), scale=4.0)
    zc = 0.98
    P.bm(cyl_y(0.06, yf - 0.02, yf - 0.008, segs=20), "Iron", matrix=T(0.12, 0, zc), scale=4.0, smooth=True)
    P.bm(cyl_y(0.04, yf - 0.04, yf - 0.02, segs=16), "Iron", matrix=T(0.12, 0, zc), scale=4.0, smooth=True)
    for k in range(12):
        a = 2 * PI * k / 12
        P.box(0.12 + math.cos(a) * 0.052 - 0.002, yf - 0.021, zc + math.sin(a) * 0.052 - 0.002,
              0.12 + math.cos(a) * 0.052 + 0.002, yf - 0.02, zc + math.sin(a) * 0.052 + 0.002, "DialFace")
    P.bm(cyl_y(0.012, yf - 0.07, yf - 0.008, segs=8), "Iron", matrix=T(0.12, 0, zc - 0.2), scale=4.0)
    P.bm(cyl_x(0.012, -0.08, 0.08, segs=8), "Iron", matrix=T(0.12, yf - 0.075, zc - 0.2), scale=4.0, smooth=True)
    P.box(0.1, yf - 0.012, zc + 0.12, 0.14, yf - 0.008, zc + 0.19, "Brass", scale=4.0)
    P.box(0.116, yf - 0.013, zc + 0.14, 0.124, yf - 0.012, zc + 0.17, "BlackPaint")
    P.box(-0.16, yf - 0.012, dz1 - 0.16, 0.0, yf - 0.009, dz1 - 0.08, "Brass", scale=4.0)          # blank plate
    P.col("SafeCol", -W / 2 - 0.01, yf - 0.08, 0.0, W / 2 + 0.01, D / 2, H)


def wall_map(P, w, h, mat="Chart", uv=(0.0, 0.0, 1.0, 1.0), battens=True, pins=True):
    """Chart pinned or battened to a wall; wall plane at local y=0, chart faces -Y. Origin = bottom centre."""
    bm = bmesh.new()
    lay = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(p) for p in ((-w / 2, -0.004, 0.0), (w / 2, -0.004, 0.0), (w / 2, -0.004, h), (-w / 2, -0.004, h))]
    f = bm.faces.new(vs)
    u0, v0, u1, v1 = uv
    for l, t in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
        l[lay].uv = t
    bm.normal_update()
    if f.normal.y > 0:
        bmesh.ops.reverse_faces(bm, faces=[f])
    P.bm(bm, mat, uv="keep")
    if battens:
        for z in (-0.01, h - 0.01):
            P.box(-w / 2 - 0.02, -0.018, z, w / 2 + 0.02, 0.0, z + 0.03, CHESTNUT)
    if pins:
        for (x, z) in ((-w / 2 + 0.03, h - 0.03), (w / 2 - 0.03, h - 0.03), (-w / 2 + 0.03, 0.03), (w / 2 - 0.03, 0.03)):
            P.bm(cyl_y(0.006, -0.008, -0.004, segs=6), "LampRed", matrix=T(x, 0, z))


def wall_clock(P, r=0.17):
    """Round office clock on the wall plane y=0, face -Y. Origin = centre."""
    P.bm(cyl_y(r + 0.015, -0.05, 0.0, segs=24), CHESTNUT, smooth=False)
    P.bm(cyl_y(r, -0.052, -0.05, segs=24), "EnamelWhite", scale=3.0)
    for k in range(12):
        a = 2 * PI * k / 12
        P.box(math.cos(a) * r * 0.82 - 0.005, -0.054, math.sin(a) * r * 0.82 - 0.005, math.cos(a) * r * 0.82 + 0.005,
              -0.052, math.sin(a) * r * 0.82 + 0.005, "BlackPaint")
    P.box(-0.004, -0.056, 0.0, 0.004, -0.054, r * 0.75, "BlackPaint")
    P.bm(bm_box(0, 0, 0, 0.007, 0.002, r * 0.55, rot=(0, math.radians(-70), 0)), "BlackPaint",
         matrix=T(r * 0.25, -0.056, -r * 0.1))


def notice_board(P, w=0.9, h=0.6, rng=None):
    """Cork board on the wall plane y=0 with notices pinned up. Origin = bottom centre."""
    P.box(-w / 2, -0.02, 0.0, w / 2, 0.0, h, CHESTNUT)
    P.box(-w / 2 + 0.03, -0.024, 0.03, w / 2 - 0.03, -0.02, h - 0.03, "Cork")
    k = 0
    for (x, z, sw, sh) in ((-0.25, 0.28, 0.21, 0.28), (0.02, 0.32, 0.15, 0.21), (0.26, 0.2, 0.21, 0.3), (-0.05, 0.07, 0.3, 0.15)):
        if abs(x) + sw / 2 > w / 2 - 0.03:
            continue
        a = rng.uniform(-4, 4) if rng else 0
        S = P.sub(T(x, -0.025, z) @ Ry(a))
        S.box(-sw / 2, -0.001, 0.0, sw / 2, 0.0, sh, "Paper", scale=2.0)
        k += 1


def sideboard(P, L=1.8, D=0.5, H=0.95, mat=CHESTNUT, name="Sideboard"):
    """Hotel dining-room sideboard: plinth, three drawers over panelled cupboards, marble-less oak top."""
    P.box(-L / 2, -D / 2 + 0.03, 0.0, L / 2, D / 2, 0.1, mat)
    P.box(-L / 2 + 0.01, -D / 2 + 0.02, 0.1, L / 2 - 0.01, D / 2, H - 0.04, mat)
    P.box(-L / 2 - 0.03, -D / 2 - 0.02, H - 0.04, L / 2 + 0.03, D / 2 + 0.01, H, mat, bevel=0.01, segs=2)
    n = 3
    for i in range(n):
        x0 = -L / 2 + 0.04 + (L - 0.08) * i / n + 0.01
        x1 = -L / 2 + 0.04 + (L - 0.08) * (i + 1) / n - 0.01
        P.box(x0, -D / 2 + 0.005, H - 0.2, x1, -D / 2 + 0.02, H - 0.07, mat, bevel=0.004)
        fu.knob(P, (x0 + x1) / 2, -D / 2 + 0.005, H - 0.135)
        fu.raised_panel(P, x0, x1, 0.15, H - 0.25, -D / 2 + 0.02, mat=mat, depth=0.014, border=0.045)
    P.col(name, -L / 2 - 0.03, -D / 2 - 0.02, 0.0, L / 2 + 0.03, D / 2 + 0.01, H)


def reception_counter(P, L=2.4, D=0.6, H=1.05, rng=None):
    """Hotel reception counter: panelled oak front facing -Y, chestnut top, a lifting flap at the +X end; bell,
    register, telephone, a stamp rack."""
    yf = -D / 2
    P.box(-L / 2, yf + 0.03, 0.0, L / 2 - 0.6, D / 2, 0.1, "BlackPaint")
    P.box(-L / 2, yf + 0.02, 0.1, L / 2 - 0.6, yf + 0.06, H - 0.05, OAK)
    for sx in (-1,):
        P.box(-L / 2, yf + 0.02, 0.0, -L / 2 + 0.05, D / 2, H - 0.05, OAK)
    n = 3
    for i in range(n):
        x0 = -L / 2 + 0.06 + (L - 0.66) * i / n + 0.02
        x1 = -L / 2 + 0.06 + (L - 0.66) * (i + 1) / n - 0.02
        fu.raised_panel(P, x0, x1, 0.18, H - 0.2, yf + 0.02, mat=OAK, depth=0.016, border=0.05)
    P.box(-L / 2 - 0.03, yf - 0.03, H - 0.05, L / 2 - 0.6, D / 2 + 0.01, H, CHESTNUT, bevel=0.01, segs=2)
    P.box(-L / 2 + 0.05, D / 2 - 0.25, 0.1, L / 2 - 0.62, D / 2 - 0.23, H - 0.05, OAK)          # inner shelf wall
    P.box(-L / 2 + 0.05, yf + 0.06, 0.55, L / 2 - 0.62, D / 2 - 0.25, 0.57, OAK)
    # flap section (raised, so staff can pass at +X)
    P.box(L / 2 - 0.6, yf - 0.03, H - 0.05, L / 2, D / 2 + 0.01, H - 0.01, CHESTNUT)
    P.box(L / 2 - 0.05, yf + 0.02, 0.0, L / 2, yf + 0.08, H - 0.05, OAK)                          # end post
    # things on the top
    P.bm(lathe([(0.0, 0.0), (0.045, 0.0), (0.045, 0.006), (0.036, 0.03), (0.01, 0.045), (0.006, 0.055), (0.0, 0.056)],
               segs=14), "Brass", matrix=T(-0.7, -0.08, H), smooth=True)                          # bell
    book(P, -0.15, 0.0, H, w=0.22, d=0.32, open_=True, rot=-4)                                     # register
    telephone(P, 0.45, 0.05, H, rot=200)
    P.box(-1.05, 0.05, H, -0.85, 0.2, H + 0.1, CHESTNUT)                                           # stamp rack
    papers(P, 0.15, 0.16, H + 0.025, n=2, rng=rng, rot=10)
    P.col("ReceptionCounter", -L / 2 - 0.03, yf - 0.03, 0.0, L / 2 - 0.6, D / 2 + 0.01, H)
    P.col("ReceptionFlap", L / 2 - 0.6, yf - 0.03, 0.0, L / 2, D / 2 + 0.01, H)


def key_board(P, cols=6, rows=4, rng=None):
    """Pigeonholes with room keys on brass tags; wall plane y=0, front -Y. Origin = bottom centre."""
    cw, rh, dp = 0.13, 0.16, 0.16
    W = cols * cw
    H = rows * rh
    P.box(-W / 2 - 0.02, -dp, 0.0, W / 2 + 0.02, 0.0, 0.02, OAK)
    P.box(-W / 2 - 0.02, -dp, H, W / 2 + 0.02, 0.0, H + 0.05, OAK, bevel=0.006)
    P.box(-W / 2, -0.012, 0.0, W / 2, 0.0, H, CHESTNUT)
    for c in range(cols + 1):
        x = -W / 2 + c * cw
        P.box(x - 0.008, -dp, 0.0, x + 0.008, 0.0, H, OAK)
    for r in range(1, rows):
        P.box(-W / 2, -dp, r * rh - 0.008, W / 2, 0.0, r * rh + 0.008, OAK)
    for r in range(rows):
        for c in range(cols):
            if rng and rng.random() < 0.35:
                continue
            x = -W / 2 + (c + 0.5) * cw
            z = r * rh + rh - 0.035
            P.box(x - 0.004, -dp + 0.02, z - 0.06, x + 0.004, -dp + 0.024, z, "Iron", scale=4.0)
            P.bm(bm_cyl(0.018, 0.018, 0.006, segs=10), "Brass", matrix=T(x, -dp + 0.022, z - 0.08) @ Rx(90), scale=4.0)


def range_stove(P, L=1.7, D=0.75, H=0.84, flue_h=2.3, name="Range"):
    """Hotel kitchen range: cast-iron body on a plinth, polished hob with lids, two oven doors and a firebox,
    a brass towel rail and the flue pipe up the wall (local +Y)."""
    yf = -D / 2
    P.box(-L / 2, yf + 0.04, 0.0, L / 2, D / 2, 0.1, "BlackPaint")
    P.box(-L / 2, yf + 0.02, 0.1, L / 2, D / 2, H - 0.04, "Iron", scale=1.0)
    P.box(-L / 2 - 0.03, yf - 0.02, H - 0.04, L / 2 + 0.03, D / 2, H, "Iron", bevel=0.01, scale=1.0)
    for k, x in enumerate((-0.5, -0.12, 0.3)):                            # hob lids
        P.bm(lathe([(0.0, H), (0.13, H), (0.13, H + 0.012), (0.0, H + 0.014)], segs=16), "BlackPaint",
             matrix=T(x, 0.05, 0.0))
        P.bm(bm_cyl(0.012, 0.012, 0.02, segs=6), "Iron", matrix=T(x, 0.05, H + 0.012))
    # firebox door (left), two oven doors, ash drawer
    P.box(-L / 2 + 0.08, yf, 0.45, -L / 2 + 0.42, yf + 0.02, H - 0.12, "Iron", bevel=0.006)
    P.box(-L / 2 + 0.08, yf, 0.15, -L / 2 + 0.42, yf + 0.02, 0.38, "Iron", bevel=0.006)
    for (x0, x1) in ((-L / 2 + 0.5, 0.15), (0.2, L / 2 - 0.08)):
        P.box(x0, yf, 0.18, x1, yf + 0.02, H - 0.12, "Iron", bevel=0.008)
        P.box(x0 + 0.05, yf - 0.006, H - 0.2, x1 - 0.05, yf, H - 0.17, "Brass", scale=4.0)
    P.box(-L / 2 + 0.16, yf - 0.004, 0.55, -L / 2 + 0.34, yf, 0.58, "Embers")           # glow through the vent
    P.bm(cyl_x(0.012, -L / 2, L / 2, segs=8), "Brass", matrix=T(0, yf - 0.06, H - 0.08), scale=4.0, smooth=True)
    for x in (-L / 2 + 0.02, L / 2 - 0.02):
        P.box(x - 0.012, yf - 0.06, H - 0.1, x + 0.012, yf + 0.02, H - 0.06, "Brass", scale=4.0)
    # splashback + flue
    P.box(-L / 2 - 0.03, D / 2 - 0.04, H, L / 2 + 0.03, D / 2, H + 0.5, "Iron", scale=1.0)
    P.box(-L / 2 - 0.05, D / 2 - 0.2, H + 0.48, L / 2 + 0.05, D / 2, H + 0.52, "Iron", scale=1.0)   # plate rack shelf
    P.bm(bm_cyl(0.08, 0.08, flue_h - H - 0.52, segs=12), "Iron", matrix=T(L / 2 - 0.25, D / 2 - 0.12, H + 0.52), smooth=True)
    P.bm(cyl_y(0.08, D / 2 - 0.12, D / 2, segs=12), "Iron", matrix=T(L / 2 - 0.25, 0, flue_h), smooth=True)
    P.col(name, -L / 2 - 0.03, yf - 0.06, 0.0, L / 2 + 0.03, D / 2, H)


def pot(P, x, y, z, r=0.12, h=0.16, mat="Copper", handle=True):
    P.bm(lathe([(r * 0.9, 0.0), (r, 0.01), (r, h), (r * 0.96, h), (r * 0.94, 0.012), (0.0, 0.012)], segs=14,
               cap_top=False), mat, matrix=T(x, y, z), smooth=True, scale=2.0)
    if handle:
        P.bm(tube([(x + r, y, z + h * 0.8), (x + r + 0.15, y, z + h * 0.85)], 0.008, 5), "Iron", scale=2.0)


def sink(P, L=1.2, D=0.6, H=0.8, name="Sink"):
    """Shallow granite sink (évier) on two piers, a brass tap from the wall at +Y."""
    zt = H
    P.box(-L / 2, -D / 2, zt - 0.16, L / 2, D / 2, zt - 0.12, "Granite", scale=0.5)          # basin bottom
    for (a0, b0, a1, b1) in ((-L / 2, -D / 2, L / 2, -D / 2 + 0.07), (-L / 2, D / 2 - 0.07, L / 2, D / 2),
                             (-L / 2, -D / 2, -L / 2 + 0.07, D / 2), (L / 2 - 0.07, -D / 2, L / 2, D / 2)):
        P.box(a0, b0, zt - 0.16, a1, b1, zt, "Granite", bevel=0.01, scale=0.5)
    for x in (-L / 2 + 0.15, L / 2 - 0.15):
        P.box(x - 0.12, -D / 2 + 0.06, 0.0, x + 0.12, D / 2 - 0.02, zt - 0.16, "Rubble", scale=0.5)
    P.bm(tube([(0.25, D / 2, zt + 0.3), (0.25, D / 2 - 0.12, zt + 0.3), (0.25, D / 2 - 0.15, zt + 0.22)], 0.012, 8),
         "Brass", scale=4.0)
    P.box(0.23, D / 2 - 0.13, zt + 0.32, 0.27, D / 2 - 0.09, zt + 0.35, "Brass", scale=4.0)
    pot(P, -0.25, 0.0, zt - 0.12, r=0.14, h=0.12, mat="Pewter", handle=False)
    P.col(name, -L / 2, -D / 2, 0.0, L / 2, D / 2, zt)


def shelves(P, L=2.0, D=0.32, levels=(0.4, 0.9, 1.4, 1.9), mat="Wood_oak", rng=None, items="kitchen", name="Shelves",
            uprights=True):
    """Open shelving against a wall (back at local +Y), loaded with crockery, tins or crates."""
    yb = D / 2
    if uprights:
        for x in (-L / 2 + 0.02, L / 2 - 0.02):
            P.box(x - 0.02, -D / 2, 0.0, x + 0.02, yb, levels[-1] + 0.05, mat, scale=1.0)
    for z in levels:
        P.box(-L / 2, -D / 2, z - 0.025, L / 2, yb, z, mat, scale=1.0)
    for z in levels:
        x = -L / 2 + 0.12
        while x < L / 2 - 0.12:
            r = rng.random() if rng else 0.5
            if items == "kitchen":
                if r < 0.3:
                    fu.bowl(P, x, rng.uniform(-0.05, 0.05), z, r=0.07, h=0.06)
                    x += 0.17
                elif r < 0.55:
                    fu.jug(P, x, 0.0, z, h=0.2, mat="Faience" if r < 0.45 else "EnamelWhite", rot=rng.uniform(0, 360))
                    x += 0.2
                elif r < 0.75:
                    for k in range(4):                                       # stacked plates
                        P.bm(lathe([(0.1, 0.0), (0.12, 0.018), (0.0, 0.018)], segs=14), "Faience",
                             matrix=T(x, 0.0, z + k * 0.02))
                    x += 0.27
                elif r < 0.9:
                    P.bm(bm_cyl(0.05, 0.05, 0.14, segs=10), "Zinc", matrix=T(x, 0.02, z), smooth=True)   # tin
                    x += 0.13
                else:
                    x += 0.15
            elif items == "pantry":
                if r < 0.45:
                    P.box(x - 0.12, -0.1, z, x + 0.12, 0.12, z + 0.22, "Wood_grey", bevel=0.005, scale=1.0)
                    x += 0.3
                elif r < 0.8:
                    for k in range(int(rng.uniform(2, 5))):
                        P.bm(bm_cyl(0.045, 0.045, 0.12, segs=10), "Zinc", matrix=T(x + k * 0.1, 0.02, z), smooth=True)
                    x += 0.5
                else:
                    fu.bottle(P, x, 0.0, z, kind=int(r * 10) % 4)
                    x += 0.12
            else:   # store: spare valves boxes, battery crates, cable coils
                if r < 0.4:
                    P.box(x - 0.15, -0.12, z, x + 0.15, 0.12, z + 0.24, "Wood_grey", bevel=0.005, scale=1.0)
                    x += 0.36
                elif r < 0.65:
                    P.box(x - 0.1, -0.08, z, x + 0.1, 0.08, z + 0.18, "BlackPaint", bevel=0.01)
                    P.box(x - 0.06, -0.03, z + 0.18, x - 0.03, 0.0, z + 0.2, "LampRed")
                    x += 0.25
                elif r < 0.85:
                    P.bm(lathe([(0.06, 0.0), (0.13, 0.0), (0.13, 0.09), (0.06, 0.09)], segs=12, cap_top=False,
                               cap_bottom=False), "Bakelite", matrix=T(x, 0.0, z))
                    x += 0.3
                else:
                    x += 0.2
    P.col(name, -L / 2, -D / 2, 0.0, L / 2, yb, levels[-1] + 0.05)


def crate(P, x, y, z, sx=0.6, sy=0.4, sz=0.4, rot=0.0, mat="Wood_grey", name="Crate", col=True):
    S = P.sub(T(x, y, z) @ Rz(rot))
    S.box(-sx / 2, -sy / 2, 0.0, sx / 2, sy / 2, sz, mat, bevel=0.004)
    for sgn in (-1, 1):
        S.box(-sx / 2 - 0.006, sgn * sy / 2 - 0.012, sz * 0.15, sx / 2 + 0.006, sgn * sy / 2 + 0.012, sz * 0.25, mat)
        S.box(-sx / 2 - 0.006, sgn * sy / 2 - 0.012, sz * 0.75, sx / 2 + 0.006, sgn * sy / 2 + 0.012, sz * 0.85, mat)
    if col:
        S.col(name, -sx / 2, -sy / 2, 0.0, sx / 2, sy / 2, sz)


def sack(P, x, y, z, rng, sx=0.75, sy=0.45, sz=0.3, rot=0.0, name="Sack", col=True):
    from props import _bag
    bm = _bag(sx, sy, sz, rng)
    S = P.sub(T(x, y, z + sz * 0.45) @ Rz(rot))
    S.bm(bm, "Burlap", scale=2.0, smooth=True, smooth_angle=70)
    if col:
        S.col(name, -sx / 2, -sy / 2, -sz * 0.45, sx / 2, sy / 2, sz * 0.5)


def bunk(P, L=1.95, W=0.88, rng=None, name="Bunk"):
    """Two-tier steel bunk (Kriegsmarine pattern): tube posts, angle rails, straw mattresses, grey blankets,
    a folded blanket and pillow on each. Head at local +Y."""
    zl, zu, ht = 0.38, 1.45, 1.85
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (W / 2 - 0.02), sy * (L / 2 - 0.02)
            P.box(x - 0.02, y - 0.02, 0.0, x + 0.02, y + 0.02, ht, STEEL, scale=2.0)
    for z in (zl, zu):
        for sx in (-1, 1):
            P.box(sx * (W / 2 - 0.02) - 0.02, -L / 2, z - 0.05, sx * (W / 2 - 0.02) + 0.02, L / 2, z, STEEL, scale=2.0)
        for sy in (-1, 1):
            P.box(-W / 2, sy * (L / 2 - 0.02) - 0.02, z - 0.05, W / 2, sy * (L / 2 - 0.02) + 0.02, z, STEEL, scale=2.0)
        P.box(-W / 2 + 0.04, -L / 2 + 0.04, z, W / 2 - 0.04, L / 2 - 0.04, z + 0.12, "Linen", bevel=0.03, segs=1)
        P.box(-W / 2 + 0.03, -L / 2 + 0.05, z + 0.1, W / 2 - 0.03, L / 2 - 0.42, z + 0.15, "Blanket", bevel=0.02, segs=1)
        P.box(-W / 2 + 0.12, L / 2 - 0.38, z + 0.11, W / 2 - 0.12, L / 2 - 0.08, z + 0.2, "Linen", bevel=0.04, segs=1)
    for sy in (-1, 1):
        P.box(-W / 2, sy * (L / 2 - 0.02) - 0.015, ht - 0.25, W / 2, sy * (L / 2 - 0.02) + 0.015, ht - 0.2, STEEL, scale=2.0)
    P.col(name, -W / 2, -L / 2, 0.0, W / 2, L / 2, zl + 0.15)
    P.col(name + "Up", -W / 2, -L / 2, zu - 0.05, W / 2, L / 2, ht)


def locker(P, W=0.6, D=0.5, H=1.8, name="Locker"):
    """Grey steel kit locker (Spind), louvred door, a padlock hasp."""
    P.box(-W / 2, -D / 2 + 0.01, 0.0, W / 2, D / 2, H, STEEL, bevel=0.006, scale=2.0)
    P.box(-W / 2 + 0.03, -D / 2, 0.08, W / 2 - 0.03, -D / 2 + 0.01, H - 0.05, STEEL, scale=2.0)
    for k in range(4):
        z = H - 0.25 - k * 0.04
        P.box(-W / 2 + 0.15, -D / 2 - 0.003, z, W / 2 - 0.15, -D / 2, z + 0.015, "BlackPaint")
    P.box(W / 2 - 0.1, -D / 2 - 0.02, 1.0, W / 2 - 0.08, -D / 2, 1.12, "Iron", scale=4.0)
    P.col(name, -W / 2, -D / 2, 0.0, W / 2, D / 2, H)


def wc(P, name="WC"):
    """WC pan with a wooden seat and a high cistern with pull chain (wall at local +Y)."""
    P.bm(lathe([(0.12, 0.0), (0.14, 0.05), (0.2, 0.3), (0.21, 0.38), (0.0, 0.38)], segs=14), "EnamelWhite", smooth=True,
         matrix=T(0, 0.0, 0.0) @ Matrix.Diagonal((0.85, 1.15, 1.0, 1.0)))
    P.box(-0.2, -0.25, 0.38, 0.2, 0.22, 0.41, OAK, bevel=0.02, segs=1)
    P.box(-0.22, 0.2, 1.9, 0.22, 0.42, 2.15, "Iron", bevel=0.01, scale=2.0)
    P.bm(tube([(0.05, 0.3, 1.9), (0.05, 0.3, 0.42)], 0.02, 6), "Iron")
    P.bm(tube([(0.18, 0.2, 1.95), (0.18, 0.16, 1.2)], 0.003, 4), "Iron")
    P.bm(lathe([(0.0, 0.0), (0.015, 0.0), (0.02, 0.04), (0.0, 0.07)], segs=8), "Furn_chestnut", matrix=T(0.18, 0.16, 1.13))
    P.col(name, -0.22, -0.25, 0.0, 0.22, 0.42, 0.41)


def washbasin(P, name="Basin"):
    """Wall-hung enamel basin with brass taps and a mirror over it (wall at local +Y)."""
    P.bm(lathe([(0.04, 0.0), (0.2, 0.12), (0.24, 0.16), (0.22, 0.165), (0.18, 0.13), (0.0, 0.08)], segs=16), "EnamelWhite",
         smooth=True, matrix=T(0, 0.02, 0.68) @ Matrix.Diagonal((1.2, 0.85, 1.0, 1.0)))
    for x in (-0.08, 0.08):
        P.bm(tube([(x, 0.22, 0.95), (x, 0.12, 0.95), (x, 0.1, 0.9)], 0.01, 6), "Brass", scale=4.0)
    P.box(-0.24, 0.19, 1.15, 0.24, 0.22, 1.65, CHESTNUT)
    P.box(-0.21, 0.185, 1.18, 0.21, 0.19, 1.62, "Mirror")
    P.col(name, -0.3, -0.18, 0.0, 0.3, 0.22, 0.85)


def bathtub(P, L=1.6, W=0.72, H=0.58, name="Bath"):
    """Enamelled cast-iron bath on claw feet (feet as simple turned stubs)."""
    P.box(-L / 2, -W / 2, 0.14, L / 2, W / 2, H, "EnamelWhite", bevel=0.06, segs=2)
    P.box(-L / 2 + 0.07, -W / 2 + 0.07, H - 0.3, L / 2 - 0.07, W / 2 - 0.07, H + 0.002, "Iron", scale=2.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.bm(lathe([(0.03, 0.0), (0.05, 0.03), (0.035, 0.15)], segs=8), "Iron",
                 matrix=T(sx * (L / 2 - 0.15), sy * (W / 2 - 0.1), 0.0))
    P.col(name, -L / 2, -W / 2, 0.0, L / 2, W / 2, H)


def coat_and_cap(P):
    """Oberleutnant Brenner's naval greatcoat (Überzieher) and peaked cap on an oak hook rail. Wall plane at local
    y=0, coat hangs in front (-Y). Origin = rail centre at the wall, floor level is z=0 (rail at 1.78)."""
    zr = 1.78
    P.box(-0.35, -0.025, zr - 0.05, 0.35, 0.0, zr + 0.05, OAK, bevel=0.005)
    for x in (-0.2, 0.2):
        P.bm(tube([(x, -0.025, zr), (x, -0.08, zr - 0.01), (x, -0.09, zr + 0.04)], 0.007, 5), "Brass", scale=4.0)
    # coat: lofted rings, narrow at the shoulders/collar, flaring to the hem
    bm = bmesh.new()
    segs = 14
    prof = [(0.0, 0.05, 0.035), (0.06, 0.2, 0.09), (0.16, 0.25, 0.12), (0.45, 0.235, 0.12), (0.8, 0.25, 0.13),
            (1.1, 0.29, 0.14), (1.2, 0.3, 0.14)]
    rings = []
    x0 = -0.2
    for (dz, hw, hd) in prof:
        ring = []
        for k in range(segs):
            a = 2 * PI * k / segs
            wob = 1.0 + 0.04 * math.sin(a * 3 + dz * 9)
            ring.append(bm.verts.new((x0 + math.cos(a) * hw * wob, -0.16 + math.sin(a) * hd, zr - 0.02 - dz)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    P.bm(bm, "Wool_navy", scale=2.0, smooth=True, smooth_angle=60)
    for sx in (-1, 1):                                                       # sleeves
        P.bm(tube([(x0 + sx * 0.23, -0.17, zr - 0.15), (x0 + sx * 0.27, -0.2, zr - 0.45), (x0 + sx * 0.26, -0.22, zr - 0.76)],
                  0.06, 8), "Wool_navy", scale=2.0, smooth=True)
    for k in range(6):                                                       # double row of buttons
        for sx in (-1, 1):
            P.bm(bm_cyl(0.011, 0.011, 0.006, segs=8), "Brass",
                 matrix=T(x0 + sx * 0.085, -0.16 - 0.125 - 0.002, zr - 0.25 - k * 0.12) @ Rx(90), scale=4.0)
    P.box(x0 - 0.12, -0.31, zr - 0.13, x0 + 0.12, -0.27, zr - 0.04, "Wool_navy", scale=2.0)   # collar lapel
    # cap on the right hook
    C = P.sub(T(0.2, -0.17, zr - 0.06))
    C.bm(lathe([(0.0, 0.0), (0.1, 0.0), (0.1, 0.05), (0.14, 0.09), (0.135, 0.105), (0.0, 0.11)], segs=16), "Wool_navy",
         smooth=True, scale=2.0)
    C.bm(lathe([(0.101, 0.0), (0.101, 0.035), (0.0, 0.035)], segs=16, cap_bottom=False), "Bakelite", scale=2.0)
    C.bm(bm_box(0, -0.1, 0.005, 0.15, 0.09, 0.01, rot=(math.radians(-18), 0, 0)), "Bakelite")
    P.col("Coat", -0.5, -0.32, 0.55, 0.35, 0.0, zr + 0.1)


def coal_heap(P, sx, sy, h, rng, seed_phase=0.0, segs=(18, 9)):
    """Slumped coal heap (deformed half-sphere), base at z=0."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0)
    ph = seed_phase
    for v in bm.verts:
        c = v.co
        n = 0.12 * math.sin(c.x * 7.1 + ph) * math.sin(c.y * 6.3) + 0.08 * math.sin(c.z * 11 + c.x * 5 + ph)
        v.co = Vector((c.x * sx * (1 + n), c.y * sy * (1 + n), max(c.z, -0.02) * h * (1 + n)))
    P.bm(bm, "Coal", scale=1.0)


def shovel(P, x, y, z, rot=0.0, lean=20.0):
    S = P.sub(T(x, y, z) @ Rz(rot) @ Rx(lean))
    S.box(-0.13, -0.01, 0.0, 0.13, 0.01, 0.32, "Iron", scale=2.0)
    S.bm(bm_cyl(0.016, 0.016, 0.85, segs=6), "Wood_grey", matrix=T(0, 0, 0.3))
    S.box(-0.07, -0.012, 1.14, 0.07, 0.012, 1.17, "Wood_grey")


def scuttle(P, x, y, z):
    P.bm(lathe([(0.12, 0.0), (0.16, 0.25), (0.14, 0.32), (0.0, 0.0)], segs=12, cap_top=False, cap_bottom=True), "Iron",
         matrix=T(x, y, z), smooth=True)
    coal_heap(P.sub(T(x, y, z + 0.2)), 0.12, 0.12, 0.06, None)


def stool_sq(P, name="Stool"):
    P.box(-0.17, -0.17, 0.43, 0.17, 0.17, 0.46, OAK)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box(sx * 0.13 - 0.02, sy * 0.13 - 0.02, 0.0, sx * 0.13 + 0.02, sy * 0.13 + 0.02, 0.43, OAK)
    P.col(name, -0.17, -0.17, 0.0, 0.17, 0.17, 0.46)


def rug(P, L=2.0, W=1.3, mat="Blanket"):
    P.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, 0.008, mat, scale=1.0)


def filing_cabinet(P, W=0.47, D=0.62, H=1.32, name="Files"):
    P.box(-W / 2, -D / 2 + 0.01, 0.0, W / 2, D / 2, H, OAK, bevel=0.006)
    for k in range(4):
        z0 = 0.04 + k * (H - 0.08) / 4
        z1 = z0 + (H - 0.08) / 4 - 0.015
        P.box(-W / 2 + 0.02, -D / 2, z0, W / 2 - 0.02, -D / 2 + 0.012, z1, OAK, bevel=0.004)
        P.box(-0.06, -D / 2 - 0.012, z1 - 0.07, 0.06, -D / 2, z1 - 0.05, "Brass", scale=4.0)
        P.box(-0.04, -D / 2 - 0.004, z1 - 0.04, 0.04, -D / 2, z1 - 0.015, "Paper", scale=4.0)
    P.col(name, -W / 2, -D / 2, 0.0, W / 2, D / 2, H)


def bookcase(P, W=1.0, D=0.36, H=1.9, rng=None, name="Bookcase"):
    P.box(-W / 2, -D / 2, 0.0, W / 2, D / 2, 0.08, CHESTNUT)
    for x in (-W / 2 + 0.015, W / 2 - 0.015):
        P.box(x - 0.015, -D / 2, 0.0, x + 0.015, D / 2, H, CHESTNUT)
    P.box(-W / 2, D / 2 - 0.015, 0.0, W / 2, D / 2, H, CHESTNUT)
    for z in (0.08, 0.5, 0.92, 1.34, 1.76):
        P.box(-W / 2, -D / 2, z - 0.02, W / 2, D / 2, z, CHESTNUT)
        if z > 1.7:
            continue
        x = -W / 2 + 0.05
        while x < W / 2 - 0.08:
            t = rng.uniform(0.025, 0.05) if rng else 0.035
            h = rng.uniform(0.22, 0.32) if rng else 0.27
            m = rng.choice(["LampRed", "Blanket", "Furn_chestnut", "Linen", "BlackPaint"]) if rng else "BlackPaint"
            P.box(x, -D / 2 + 0.04, z, x + t, D / 2 - 0.03, z + h, m, scale=2.0)
            x += t + 0.004
    P.box(-W / 2 - 0.02, -D / 2 - 0.02, H, W / 2 + 0.02, D / 2, H + 0.04, CHESTNUT, bevel=0.008)
    P.col(name, -W / 2, -D / 2, 0.0, W / 2, D / 2, H + 0.04)


def bedside(P, name="Bedside"):
    P.box(-0.22, -0.2, 0.0, 0.22, 0.2, 0.62, CHESTNUT)
    P.box(-0.24, -0.22, 0.62, 0.24, 0.22, 0.65, CHESTNUT, bevel=0.006)
    P.box(-0.18, -0.205, 0.4, 0.18, -0.2, 0.56, CHESTNUT)
    fu.knob(P, 0.0, -0.205, 0.48)
    P.col(name, -0.24, -0.22, 0.0, 0.24, 0.22, 0.65)


def transmitter_rack(P, W=0.62, D=0.5, H=1.3, name="TransmitterRack"):
    """Floor-standing naval short-wave transmitter in a grey rack: three stacked units (exciter, power amplifier,
    supply), big tuning dials, meters, a lead-out insulator and aerial wire on the top."""
    P.box(-W / 2, -D / 2 + 0.02, 0.0, W / 2, D / 2, 0.08, "BlackPaint")
    hs = [0.08, 0.5, 0.92, H]
    n0 = len(P.cols)
    for k in range(3):
        S = P.sub(T(0, 0, hs[k]))
        radio_set(S, W=W, D=D, H=hs[k + 1] - hs[k] - 0.005, dials=2 if k < 2 else 0, knobs=4 if k != 1 else 2,
                  meter=True, name=f"{name}{k}")
    del P.cols[n0:]
    P.bm(lathe([(0.03, 0.0), (0.035, 0.02), (0.02, 0.03), (0.035, 0.05), (0.02, 0.06), (0.035, 0.08), (0.008, 0.1),
                (0.0, 0.1)], segs=10), "EnamelWhite", matrix=T(0.15, 0.1, H))
    P.bm(tube([(0.15, 0.1, H + 0.1), (0.15, 0.2, H + 0.4), (0.15, 0.25, H + 1.4)], 0.006, 4), "Iron")
    P.col(name, -W / 2, -D / 2 - 0.05, 0.0, W / 2, D / 2, H + 0.1)


def blackboard(P, w=0.75, h=0.55, rng=None):
    """Small blackboard with chalked call signs and frequencies (illegible strokes). Wall plane y=0, face -Y."""
    P.box(-w / 2, -0.025, 0.0, w / 2, 0.0, h, CHESTNUT)
    P.box(-w / 2 + 0.03, -0.028, 0.03, w / 2 - 0.03, -0.025, h - 0.03, "BlackPaint")
    for r in range(5):
        z = h - 0.09 - r * 0.085
        x = -w / 2 + 0.07
        while x < w / 2 - 0.12:
            sw = rng.uniform(0.02, 0.09) if rng else 0.05
            P.box(x, -0.0295, z, x + sw, -0.028, z + 0.012, "Chalk")
            x += sw + (rng.uniform(0.01, 0.05) if rng else 0.02)
    P.box(-w / 2 + 0.03, -0.06, 0.02, w / 2 - 0.03, -0.025, 0.035, CHESTNUT)


def rotor_box(P, x, y, z, rot=0.0):
    """Small oak box for the spare cipher wheels, lid open, three wheels inside."""
    S = P.sub(T(x, y, z) @ Rz(rot))
    S.box(-0.09, -0.06, 0.0, 0.09, 0.06, 0.06, OAK, bevel=0.003)
    S.box(-0.08, -0.05, 0.059, 0.08, 0.05, 0.061, "Felt")
    for k in range(3):
        S.bm(cyl_x(0.035, -0.008, 0.008, segs=14), "Iron", matrix=T(-0.05 + k * 0.05, 0, 0.06), smooth=True, scale=4.0)
    L = S.sub(T(0, 0.06, 0.06) @ Rx(100))
    L.box(-0.09, 0.0, 0.0, 0.09, 0.12, 0.008, OAK)
