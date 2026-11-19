"""Town / harbour / military texture sets (numpy, tileable) and the material names that use them.

Kit textures (tools/blender/env/out/tex) and interior textures (tools/blender/interiors/out/tex) are
reused through geo.std(); this module adds the sets the town pieces need and patches geo.std so
MB.build() resolves the new names. Output: tools/blender/town/out/tex/.
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.abspath(os.path.join(HERE, "..", "env"))
INT = os.path.abspath(os.path.join(HERE, "..", "interiors"))
for p in (ENV, INT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import textures as envtex  # noqa: E402
from texlib import (F, blur, cavity_ao, cell_rand, fbm, grid, height_to_normal, lichen_mask, mix, orm,  # noqa: E402
                    perlin, rgb, save_set, sstep, voronoi, write_png)

TEX_DIR = os.path.join(HERE, "out", "tex")
ENV_TEX = envtex.TEX_DIR
GROUND_DIR = envtex.GROUND_DIR


# ------------------------------------------------------------------ ashlar
def tex_ashlar(granite, res=2048, seed=701):
    """Coursed granite ashlar (pierre de taille): 6 courses per 2 m tile, thin lime joints."""
    g_alb, _, g_orm, g_h = granite
    X, Y = grid(res)
    px = 2.0 / res
    U = X % 1.0
    V = (1.0 - Y) % 1.0
    r, cid, lx, ly, hw, hh = envtex._row_cells(V, U, 6, 0.2, 0.42, seed)
    rr = cell_rand(cid, seed + 1, 6)
    lxm, lym = lx * 2.0, ly * 2.0
    hx, hy = hw * 2.0 - 0.006, hh * 2.0 - 0.006
    sdf = envtex._round_rect_sdf(lxm, lym, hx, hy, 0.006) + fbm(X, Y, 50, 3, seed + 2) * 0.002
    inside = -sdf
    stone = inside > 0
    arris = sstep(0.0, 0.01, inside)
    tilt = (rr[..., 0] - 0.5) * 0.004 * (lxm / np.maximum(hx, 0.05)) + (rr[..., 1] - 0.5) * 0.003
    h = np.where(stone, 0.006 + g_h + tilt * 0.3 - (1 - arris) * 0.002, -0.004 + fbm(X, Y, 60, 2, seed + 3) * 0.0008)
    h = h.astype(F)
    tint = 0.86 + rr[..., 2] * 0.22
    warm = rr[..., 3]
    col = g_alb * tint[..., None]
    col = mix(col, col * np.array((1.06, 0.98, 0.9), F), warm * 0.6)
    mort = mix(rgb((0.58, 0.56, 0.50), X.shape), rgb((0.40, 0.39, 0.35), X.shape), sstep(-0.4, 0.4, fbm(X, Y, 20, 3, seed + 4)))
    alb = np.where(stone[..., None], mix(col * 0.85, col, arris), mort)
    alb = mix(alb, alb.mean(axis=2, keepdims=True) * np.array((0.98, 1.0, 1.03), F), 0.4)   # cool grey Breton granite
    rough = np.where(stone, g_orm[..., 1], 0.93)
    ao = cavity_ao(h, px, (0.004, 0.015, 0.05), 1.2)
    return alb, height_to_normal(h, px, 1.0), orm(ao, rough), h


# ---------------------------------------------------------------- concrete
def tex_concrete(res=2048, tile_m=2.0, seed=711, camo=False):
    """Board-marked Atlantic Wall concrete: horizontal shutter boards (~18 cm) with grain imprint,
    seams, tie-rod holes, efflorescence and rust runs. camo=True adds a painted disruptive pattern."""
    X, Y = grid(res)
    px = tile_m / res
    nb = int(round(tile_m / 0.18))
    V = (1.0 - Y) % 1.0
    row = np.floor(V * nb).astype(np.int32)
    fy = V * nb - row
    rr = np.random.default_rng(seed).random((nb, 4)).astype(F)
    # board seams (fins) and per-board offset
    seam = sstep(0.04, 0.0, fy) + sstep(0.96, 1.0, fy)
    board_off = (rr[row, 0] - 0.5) * 0.002
    grain = perlin(X * 1.0, Y, int(14 * tile_m), int(nb * 3), seed + 1) * 0.5
    grain += perlin(X, Y, int(60 * tile_m), int(nb * 10), seed + 2) * 0.3
    grain = np.sin((fy * 6.0 + grain * 2.0 + rr[row, 1] * 10.0) * np.pi) * 0.3 + grain
    # vertical butt joints of boards (every ~1-2 m, staggered)
    bx = (X * tile_m + rr[row, 2] * 3.0) % 1.6
    butt = sstep(0.008, 0.0, np.minimum(bx, 1.6 - bx))
    h = board_off + grain * 0.0006 + seam * 0.0015 - butt * 0.001
    # pores and pits
    f1, _, _, _, _ = voronoi(X, Y, int(120 * tile_m), int(120 * tile_m), seed + 3, 0.95)
    pits = sstep(0.0018, 0.0005, f1) * (perlin(X, Y, int(30 * tile_m), int(30 * tile_m), seed + 4) > 0.1)
    h = h - pits * 0.0015 + fbm(X, Y, int(8 * tile_m), 4, seed + 5) * 0.0015
    # tie-rod holes on a 0.9 m grid
    gx = (X * tile_m / 0.9) % 1.0 - 0.5
    gy = (V * tile_m / 0.9) % 1.0 - 0.5
    tie = sstep(0.02, 0.012, np.sqrt(gx * gx + gy * gy) * 0.9)
    h = (h - tie * 0.008).astype(F)
    base = mix(rgb((0.56, 0.55, 0.52), X.shape), rgb((0.46, 0.46, 0.44), X.shape), sstep(-0.5, 0.5, fbm(X, Y, int(3 * tile_m), 5, seed + 6)))
    base *= (0.94 + 0.08 * (rr[row, 3] - 0.5) + 0.06 * grain)[..., None]
    base = mix(base, base * 0.75, seam[..., None] * 0.5)
    run = sstep(0.1, 0.7, fbm(X, Y, int(3 * tile_m), 5, seed + 7, aniso=(6, 0.4)))
    base = mix(base, base * 0.62, run * 0.5)                                      # rain/grime runs
    eff = sstep(0.4, 0.8, fbm(X, Y, int(4 * tile_m), 4, seed + 8, aniso=(4, 0.7)))
    base = mix(base, rgb((0.72, 0.71, 0.67), X.shape), eff * 0.35)                 # efflorescence
    rust = tie * 1.0 + sstep(0.012, 0.0, np.abs(gx) * 0.9) * sstep(0.0, -0.25, gy) * sstep(-0.5, -0.4, gy) * 0
    base = mix(base, rgb((0.35, 0.20, 0.10), X.shape), np.clip(rust, 0, 1) * 0.7)
    base = mix(base, base * 0.4, pits[..., None] * 0.6)
    rough = 0.9 - 0.05 * eff
    if camo:
        # three-tone disruptive pattern: dunkelgelb ground, red-brown and olive blotches (sharp-ish)
        n1 = fbm(X, Y, int(1.5 * tile_m), 4, seed + 20) + fbm(X, Y, int(6 * tile_m), 2, seed + 21) * 0.15
        n2 = fbm(X, Y, int(1.5 * tile_m), 4, seed + 22) + fbm(X, Y, int(6 * tile_m), 2, seed + 23) * 0.15
        lum = (base.mean(axis=2) / 0.52)[..., None]
        c0 = rgb((0.55, 0.47, 0.32), X.shape)
        c1 = rgb((0.33, 0.22, 0.14), X.shape)
        c2 = rgb((0.27, 0.30, 0.19), X.shape)
        paint = mix(c0, c1, sstep(0.16, 0.2, n1))
        paint = mix(paint, c2, sstep(0.18, 0.22, n2) * (1 - sstep(0.16, 0.2, n1) * 0.5))
        paint *= lum
        worn = sstep(0.45, 0.7, fbm(X, Y, int(10 * tile_m), 4, seed + 24)) + seam * 0.4
        base = mix(paint, base, np.clip(worn, 0, 1) * 0.7)
        base = mix(base, base * 0.62, run[..., None] * 0.4)
        rough = rough - 0.04
    ao = cavity_ao(h, px, (0.003, 0.012, 0.04), 1.2)
    return base.astype(F), height_to_normal(h, px, 1.0), orm(ao, rough), h


# --------------------------------------------------------------- paint metal
METAL_PAINTS = {"grey": (0.20, 0.215, 0.21), "khaki": (0.27, 0.25, 0.16), "olive": (0.22, 0.23, 0.16)}


def tex_paint_metal(res=1024, seed=721):
    """Painted steel: matt paint, chipped to primer and bare/rusty metal, dust. 1 m tile."""
    X, Y = grid(res)
    px = 1.0 / res
    chip_n = fbm(X, Y, 8, 6, seed)
    chip = sstep(0.42, 0.46, chip_n)
    rust = sstep(0.5, 0.56, chip_n) * sstep(0.0, 0.3, fbm(X, Y, 20, 3, seed + 1))
    h = (np.where(chip > 0.5, -0.00015, 0.0) + fbm(X, Y, 40, 3, seed + 2) * 0.00006 - rust * 0.0001).astype(F)
    h = blur(h, 0.8)
    dust = sstep(0.0, 0.7, fbm(X, Y, 3, 5, seed + 3, aniso=(1, 3)))
    out = {}
    for k, c in METAL_PAINTS.items():
        pc = rgb(c, X.shape) * (0.93 + 0.1 * fbm(X, Y, 10, 3, seed + 4))[..., None]
        pc = mix(pc, pc * 1.25 + 0.03, dust * 0.4)
        a = mix(pc, rgb((0.32, 0.31, 0.30), X.shape), chip)
        a = mix(a, rgb((0.30, 0.15, 0.06), X.shape), rust)
        out[k] = a.astype(F)
    rough = 0.72 - chip * 0.25 + rust * 0.2 + dust * 0.1
    metal = chip * (1 - rust) * 0.8
    ao = cavity_ao(h, px, (0.001, 0.004), 1.0)
    return height_to_normal(h, px, 1.0), orm(ao, np.clip(rough, 0, 1), metal), out


# --------------------------------------------------------------------- nets
def tex_net(res=1024, seed=731):
    """Heaped cotton fishing net dyed Concarneau blue, layered meshes over dark voids. 1 m tile."""
    X, Y = grid(res)
    px = 1.0 / res
    acc_h = np.zeros(X.shape, F)
    acc_c = np.zeros(X.shape + (3,), F)
    cov = np.zeros(X.shape, F)
    for layer in range(4):
        wx = X + fbm(X, Y, 3, 3, seed + layer * 10) * 0.08
        wy = Y + fbm(X, Y, 3, 3, seed + layer * 10 + 1) * 0.08
        cells = 40 + layer * 6
        a = np.radians(45 + layer * 17)
        u = (wx * np.cos(a) - wy * np.sin(a)) * cells
        v = (wx * np.sin(a) + wy * np.cos(a)) * cells
        du = np.abs(u - np.round(u))
        dv = np.abs(v - np.round(v))
        line = np.maximum(sstep(0.12, 0.05, du), sstep(0.12, 0.05, dv))
        knot = sstep(0.18, 0.08, np.sqrt(du * du + dv * dv))
        m = np.clip(line + knot, 0, 1) * (1 - cov * 0.8)
        depth = 1.0 - layer * 0.22
        acc_h += m * depth * 0.002
        col = mix(rgb((0.12, 0.20, 0.32), X.shape), rgb((0.20, 0.30, 0.40), X.shape), sstep(-0.4, 0.4, fbm(X, Y, 6, 3, seed + 40 + layer)))
        acc_c += col * (m * depth)[..., None]
        cov = np.clip(cov + m, 0, 1)
    void = rgb((0.02, 0.025, 0.03), X.shape)
    alb = acc_c + void * (1 - np.clip(cov, 0, 1))[..., None]
    salt = sstep(0.5, 0.8, fbm(X, Y, 8, 3, seed + 50))
    alb = mix(alb, alb * 0.6 + 0.12, salt * cov * 0.4)
    h = acc_h.astype(F)
    ao = cavity_ao(h, px, (0.002, 0.008), 1.5)
    rough = 0.9 + 0.0 * h
    return alb.astype(F), height_to_normal(h, px, 1.0), orm(ao, rough), h


def tex_render_pale():
    """The kit's lime render, lime-washed paler (seafront hotel cream), patches of rubble kept."""
    a, n, o, h = envtex.tex_render(envtex.tex_rubble())
    lum = a.mean(axis=2)
    m = sstep(0.5, 0.58, lum)[..., None]
    pale = np.clip(a * np.array((1.12, 1.12, 1.14), F) + np.array((0.08, 0.075, 0.06), F), 0, 1)
    return mix(a, pale, m).astype(F), n, o


# ------------------------------------------------------------------ ensure
def _exists(*names):
    return all(os.path.exists(os.path.join(TEX_DIR, n)) for n in names)


def ensure(force=False, log=print):
    os.makedirs(TEX_DIR, exist_ok=True)
    t0 = time.time()
    if force or not _exists("ashlar_albedo.png", "ashlar_normal.png", "ashlar_orm.png"):
        a, n, o, _ = tex_ashlar(envtex.tex_granite())
        save_set(TEX_DIR, "ashlar", a, n, o)
        log(f"[ttex] ashlar {time.time() - t0:.1f}s")
    if force or not _exists("concrete_albedo.png"):
        a, n, o, _ = tex_concrete()
        save_set(TEX_DIR, "concrete", a, n, o)
        log(f"[ttex] concrete {time.time() - t0:.1f}s")
    if force or not _exists("concrete_camo_albedo.png"):
        a, n, o, _ = tex_concrete(tile_m=4.0, seed=741, camo=True)
        save_set(TEX_DIR, "concrete_camo", a, n, o)
        log(f"[ttex] concrete camo {time.time() - t0:.1f}s")
    if force or not _exists("paint_metal_normal.png", "paint_metal_khaki_albedo.png"):
        n, o, cols = tex_paint_metal()
        write_png(os.path.join(TEX_DIR, "paint_metal_normal.png"), n)
        write_png(os.path.join(TEX_DIR, "paint_metal_orm.png"), o)
        for k, a in cols.items():
            write_png(os.path.join(TEX_DIR, f"paint_metal_{k}_albedo.png"), a)
        log(f"[ttex] paint metal {time.time() - t0:.1f}s")
    if force or not _exists("render_pale_albedo.png"):
        a, n, o = tex_render_pale()
        save_set(TEX_DIR, "render_pale", a, n, o)
        log(f"[ttex] render pale {time.time() - t0:.1f}s")
    if force or not _exists("net_albedo.png"):
        a, n, o, _ = tex_net()
        save_set(TEX_DIR, "net", a, n, o)
        log(f"[ttex] net {time.time() - t0:.1f}s")


# ---------------------------------------------------------------- materials
def install():
    """Patch geo.std (after itex.install) with the town materials."""
    import geo
    if getattr(geo, "_town_patched", False):
        return
    base_std = geo.std
    tm, fm = geo.tex_mat, geo.flat_mat

    def T(s, folder=TEX_DIR):
        return dict(albedo=f"{s}_albedo.png", normal=f"{s}_normal.png", orm=f"{s}_orm.png", folder=folder)

    def std(name):
        if name in geo._MATS:
            return geo._MATS[name]
        if name == "Ashlar":
            return tm("Ashlar", **T("ashlar"))
        if name == "AshlarDark":       # weathered, sea-darkened ashlar
            return tm("AshlarDark", **T("ashlar"), tint=(0.72, 0.71, 0.68))
        if name == "AshlarWet":        # quay face in the tidal range
            return tm("AshlarWet", **T("ashlar"), tint=(0.48, 0.50, 0.47))
        if name == "AshlarWeed":       # bladderwrack / green weed band at the foot of the quay
            return tm("AshlarWeed", **T("ashlar"), tint=(0.20, 0.24, 0.11))
        if name == "GraniteDark":      # incised letters / deep shadowed carving
            return tm("GraniteDark", **T("granite", ENV_TEX), tint=(0.42, 0.41, 0.40))
        if name == "GraniteWet":       # tidal zone of the quay
            return tm("GraniteWet", **T("rubble", ENV_TEX), tint=(0.42, 0.44, 0.38))
        if name == "Weed":             # seaweed / green algae band
            return tm("Weed", **T("rubble", ENV_TEX), tint=(0.16, 0.20, 0.08))
        if name == "RenderPale":
            return tm("RenderPale", **T("render_pale"))
        if name == "Concrete":
            return tm("Concrete", **T("concrete"))
        if name == "ConcreteCamo":
            return tm("ConcreteCamo", **T("concrete_camo"))
        if name.startswith("Metal_"):  # Metal_grey / Metal_khaki / Metal_olive
            c = name.split("_", 1)[1]
            return tm(name, f"paint_metal_{c}_albedo.png", "paint_metal_normal.png", "paint_metal_orm.png", folder=TEX_DIR)
        if name == "Net":
            return tm("Net", **T("net"))
        if name == "Tar":              # tarred hull planking
            return tm("Tar", **T("wood_raw", ENV_TEX) | dict(albedo="wood_raw_dark_albedo.png"), tint=(0.32, 0.31, 0.30),
                      nstrength=0.8)
        if name == "Sail":             # tan-bark dyed canvas
            return tm("Sail", **T("burlap", ENV_TEX), tint=(0.98, 0.52, 0.30), nstrength=0.4)
        if name == "Canvas":           # khaki canvas (parachute pack, bundles)
            return tm("Canvas", **T("burlap", ENV_TEX), tint=(0.85, 0.85, 0.62), nstrength=0.5)
        if name == "Rope":
            return tm("Rope", **T("burlap", ENV_TEX), tint=(0.9, 0.78, 0.6))
        if name == "Mud":
            return tm("Mud", **T("mud", GROUND_DIR))
        if name == "Grass":
            return tm("Grass", **T("grass_winter", GROUND_DIR))
        if name == "Gravel":
            return tm("Gravel", **T("gravel", GROUND_DIR))
        if name == "Coal":
            return tm("Coal", **T("gravel", GROUND_DIR), tint=(0.10, 0.10, 0.11))
        if name == "Cork":
            return fm("Cork", (0.36, 0.25, 0.15), rough=0.9)
        if name == "EnamelBlue":
            return fm("EnamelBlue", (0.03, 0.08, 0.26), rough=0.25)
        if name == "EnamelWhite":
            return fm("EnamelWhite", (0.80, 0.79, 0.74), rough=0.25)
        if name == "SignBlack":
            return fm("SignBlack", (0.03, 0.03, 0.03), rough=0.7)
        if name == "SignWhite":
            return fm("SignWhite", (0.74, 0.72, 0.66), rough=0.75)
        if name == "HotelLetter":      # painted lettering on render (oxide red, faded)
            return fm("HotelLetter", (0.36, 0.10, 0.07), rough=0.8)
        if name == "LeadGlass":        # leaded church glazing, dark with a slight tint
            return fm("LeadGlass", (0.03, 0.035, 0.045), rough=0.15)
        if name == "Lens":             # searchlight front glass
            return fm("Lens", (0.08, 0.09, 0.09), rough=0.05, metal=0.2)
        if name == "Reflector":
            return fm("Reflector", (0.75, 0.75, 0.72), rough=0.12, metal=1.0)
        if name == "Bronze":
            return fm("Bronze", (0.30, 0.22, 0.12), rough=0.45, metal=1.0)
        if name == "Fish":
            return fm("Fish", (0.42, 0.45, 0.47), rough=0.3, metal=0.3)
        if name == "Void":
            return fm("Void", (0.004, 0.004, 0.004), rough=1.0)
        return base_std(name)

    geo.std = std
    geo._town_patched = True


if __name__ == "__main__":
    ensure(force="--force" in sys.argv)
