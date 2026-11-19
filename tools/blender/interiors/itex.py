"""Interior texture recipes + material registry for the enterable houses.

Masters go to tools/blender/interiors/out/tex/ (packed into the .glb on export). The exterior
kit textures (tools/blender/env/out/tex/) are reused as-is through geo.std(); this module adds
interior-only sets and patches geo.std so MB.build() resolves the new material names.
"""
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.abspath(os.path.join(HERE, "..", "env"))
for p in (ENV, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from texlib import (F, blur, cavity_ao, cell_rand, fbm, grid, height_to_normal, mix, orm,  # noqa: E402
                    palette_pick, perlin, rgb, ridged, save_set, sstep, voronoi, write_png)
import textures as envtex  # noqa: E402

TEX_DIR = os.path.join(HERE, "out", "tex")
ENV_TEX = envtex.TEX_DIR


# ============================================================== plaster
def tex_plaster(rubble, res=2048, seed=501):
    """Interior lime plaster (enduit a la chaux) + limewash over rubble: wavy hand-trowelled
    surface following the stones beneath, hairline cracks, flaked spots, smoke and damp mottling.
    2 m tile."""
    r_alb, _, r_orm, r_h = rubble
    X, Y = grid(res)
    px = 2.0 / res
    # the plaster "telegraphs" the rubble under it: blurred stone relief
    under = blur(r_h, 22.0)
    under = (under - under.mean()) * 0.35
    trowel = fbm(X, Y, 5, 5, seed) * 0.0025 + fbm(X, Y, 14, 3, seed + 1, aniso=(2, 1)) * 0.0008
    h = 0.012 + under + trowel + perlin(X, Y, 400, 400, seed + 2) * 0.00015
    # limewash colour: warm off-white with yellowed and greyed zones
    base = mix(rgb((0.80, 0.77, 0.69), X.shape), rgb((0.72, 0.68, 0.58), X.shape),
               sstep(-0.5, 0.6, fbm(X, Y, 3, 5, seed + 3)))
    base *= (0.95 + 0.06 * fbm(X, Y, 30, 3, seed + 4))[..., None]
    brush = fbm(X, Y, 20, 3, seed + 5, aniso=(1, 4))           # limewash brush strokes
    base = mix(base, base * 0.92, sstep(0.0, 0.6, brush) * 0.5)
    # smoke / grime: low-frequency greying
    grime = sstep(0.1, 0.8, fbm(X, Y, 2, 4, seed + 6))
    base = mix(base, base * rgb((0.62, 0.58, 0.52), X.shape), grime[..., None] * 0.45)
    # damp mottling: greenish-brown blotches with salt tide rims
    dn = fbm(X, Y, 4, 6, seed + 7)
    damp = sstep(0.28, 0.5, dn)
    rim = sstep(0.24, 0.28, dn) * (1 - sstep(0.28, 0.33, dn))
    dcol = mix(rgb((0.47, 0.45, 0.36), X.shape), rgb((0.36, 0.37, 0.28), X.shape), sstep(0.4, 0.7, dn))
    base = mix(base, dcol, damp[..., None] * 0.55)
    base = mix(base, rgb((0.86, 0.84, 0.78), X.shape), rim[..., None] * 0.35)
    mould = sstep(0.55, 0.8, perlin(X, Y, 160, 160, seed + 8)) * damp
    base = mix(base, rgb((0.16, 0.17, 0.12), X.shape), mould[..., None] * 0.6)
    # hairline cracks
    cr = ridged(X, Y, 6, 4, seed + 9)
    crack = sstep(0.955, 0.985, cr) * sstep(-0.2, 0.3, fbm(X, Y, 4, 3, seed + 10))
    base = mix(base, base * 0.45, crack[..., None] * 0.8)
    h = h - crack * 0.0008
    # flaked spots exposing the rubble/mortar
    fl = fbm(X, Y, 9, 5, seed + 11) + damp * 0.25
    flake = fl > 0.47
    lip = sstep(0.44, 0.47, fl) * (~flake)
    alb = np.where(flake[..., None], r_alb * 0.8, base)
    alb = mix(alb, alb * 0.7, lip[..., None] * 0.6)
    h = np.where(flake, r_h * 0.6 - 0.002, h).astype(F)
    rough = np.where(flake, r_orm[..., 1], 0.9 - damp * 0.12)
    ao = cavity_ao(h, px, (0.004, 0.015, 0.05), 1.1)
    return alb, height_to_normal(h, px, 0.8), orm(ao, rough), h


# ================================================================ flags
def tex_flags(res=2048, seed=511):
    """Granite/schist floor flags (dallage), worn smooth, dirt in the joints. 2 m tile."""
    X, Y = grid(res)
    px = 2.0 / res
    U = (X + fbm(X, Y, 5, 3, seed) * 0.006) % 1.0
    V = (1.0 - Y + fbm(X, Y, 5, 3, seed + 1) * 0.005) % 1.0
    r, cid, lx, ly, hw, hh = envtex._row_cells(V, U, 5, 0.14, 0.32, seed + 2)
    rr = cell_rand(cid, seed + 3, 8)
    lxm, lym = lx * 2.0, ly * 2.0
    gap = 0.002 + rr[..., 1] * 0.003
    hx = hw * 2.0 - gap
    hy = hh * 2.0 - gap - rr[..., 2] * 0.005
    sdf = envtex._round_rect_sdf(lxm, lym, hx, hy, 0.006 + rr[..., 3] * 0.01)
    sdf += fbm(X, Y, 30, 3, seed + 4) * 0.003 + fbm(X, Y, 10, 2, seed + 5) * 0.003
    inside = -sdf
    is_stone = inside > 0
    edge = np.sqrt(np.clip(inside / 0.008, 0, 1))
    wear = fbm(X, Y, 8, 4, seed + 6) * 0.0015 + (rr[..., 4] - 0.5) * 0.004
    h_st = 0.01 * edge + wear + perlin(X, Y, 300, 300, seed + 7) * 0.00015
    h = np.where(is_stone, h_st, -0.003 + fbm(X, Y, 40, 3, seed + 8) * 0.001).astype(F)
    pal = [(0.42, 0.41, 0.39), (0.36, 0.36, 0.36), (0.45, 0.42, 0.37), (0.30, 0.31, 0.32),
           (0.40, 0.37, 0.33), (0.33, 0.33, 0.30)]
    col = palette_pick(rr[..., 5], pal)
    dm, lm = envtex._speckle(X, Y, seed + 9, 0.45, 0.5, 600)
    col = col * (1 - 0.4 * dm[..., None]) + 0.07 * lm[..., None]
    col *= (0.88 + 0.16 * fbm(X, Y, 12, 4, seed + 10))[..., None]
    dirt = 1.0 - sstep(0.0, 0.015, inside)
    col = mix(col, rgb((0.12, 0.10, 0.08), X.shape), dirt[..., None] * 0.55)
    grime = sstep(-0.2, 0.6, fbm(X, Y, 3, 4, seed + 11))
    col = mix(col, col * 0.7, grime[..., None] * 0.4)
    jcol = mix(rgb((0.10, 0.085, 0.07), X.shape), rgb((0.20, 0.17, 0.13), X.shape),
               sstep(-0.3, 0.5, fbm(X, Y, 25, 3, seed + 12)))
    alb = np.where(is_stone[..., None], col, jcol)
    polish = sstep(0.0, 0.7, fbm(X, Y, 3, 3, seed + 13))
    rough = np.where(is_stone, 0.62 - 0.18 * polish + 0.06 * fbm(X, Y, 30, 3, seed + 14), 0.9)
    ao = cavity_ao(h, px, (0.004, 0.015, 0.04), 1.2)
    return alb, height_to_normal(h, px, 1.0), orm(ao, rough), h


# ======================================================= furniture wood
def tex_furn_wood(res=1024, seed=521):
    """Waxed hardwood for Breton furniture (chestnut / oak), fine grain, 1 m tile, no plank seams."""
    X, Y = grid(res)
    px = 1.0 / res
    warp = fbm(X, Y, 2, 3, seed) * 0.1
    rings = np.sin((X * 38.0 + warp * 18.0 + fbm(X, Y, 3, 4, seed + 1, aniso=(5, 1)) * 2.0) * 2 * np.pi)
    fib = perlin(X, Y, 300, 5, seed + 2) * 0.5 + perlin(X, Y, 600, 9, seed + 3) * 0.3
    pores = sstep(0.55, 0.8, perlin(X, Y, 700, 40, seed + 4))
    flecks = sstep(0.6, 0.85, perlin(X, Y, 90, 14, seed + 5)) * 0.5
    g = rings * 0.45 + fib
    L = 0.75 + 0.18 * np.tanh(g) - pores * 0.12 + flecks * 0.08
    L *= (0.92 + 0.1 * fbm(X, Y, 4, 3, seed + 6))
    h = (g * 0.00015 - pores * 0.0002).astype(F)
    rough = 0.48 + 0.12 * pores + 0.06 * fbm(X, Y, 10, 3, seed + 7)
    ao = cavity_ao(h, px, (0.001, 0.003), 0.6)
    tints = {"chestnut": (0.36, 0.21, 0.11), "oak": (0.50, 0.36, 0.22), "black": (0.16, 0.10, 0.06)}
    out = {k: (L[..., None] * np.array(v, F)).astype(F) for k, v in tints.items()}
    return height_to_normal(h, px, 1.0), orm(ao, rough), out


# ============================================================= door paint
DOOR_PAINTS = {
    "bleu": (0.10, 0.25, 0.53),      # bleu breton
    "bottle": (0.06, 0.27, 0.16),    # bottle green
    "oxblood": (0.46, 0.07, 0.06),   # sang de boeuf
}


def tex_door_paint():
    """Saturated door paints on the kit's planked wood: same peel/chalk masks as wood_paint, so the
    exterior keeps its weathering."""
    nrm, o, _, paint, gap, wood = envtex.tex_wood_paint()
    X, Y = grid(paint.shape[0])
    chalk = sstep(-0.3, 0.6, fbm(X, Y, 4, 4, 96))
    grain = fbm(X, Y, 30, 3, 97, aniso=(1, 8))
    out = {}
    for name, pc in DOOR_PAINTS.items():
        pcol = rgb(pc, X.shape)
        pcol = mix(pcol, pcol * 0.8 + 0.1, chalk[..., None] * 0.3)
        pcol *= (0.94 + 0.06 * grain)[..., None]
        a = np.where(paint[..., None], pcol, wood)
        a = np.where(gap[..., None], a * 0.25, a)
        out[name] = a
    return out


# ============================================================ decals etc.
def tex_damp_patch(res=1024, seed=531):
    """Irregular damp stain with a salt tide line, RGBA, transparent border (not tiling)."""
    X, Y = grid(res)
    cx, cy = X - 0.5, Y - 0.5
    rad = np.sqrt(cx * cx + cy * cy * 1.3)
    n = fbm(X, Y, 4, 5, seed) * 0.16 + fbm(X, Y, 12, 3, seed + 1) * 0.04
    d = rad + n - 0.12 * (Y - 0.5)          # heavier towards the bottom (image bottom = ground side)
    a = sstep(0.42, 0.22, d)
    tide = sstep(0.4, 0.43, d) * sstep(0.47, 0.43, d)
    inner = sstep(0.3, 0.0, d)
    col = mix(rgb((0.30, 0.29, 0.22), X.shape), rgb((0.17, 0.19, 0.12), X.shape), inner)
    col = mix(col, rgb((0.78, 0.76, 0.70), X.shape), tide[..., None] * 0.7)
    spots = sstep(0.6, 0.85, perlin(X, Y, 120, 120, seed + 2)) * inner
    col = mix(col, rgb((0.07, 0.08, 0.05), X.shape), spots[..., None])
    alpha = np.clip(a * (0.55 + 0.3 * inner) * (0.85 + 0.15 * fbm(X, Y, 20, 3, seed + 3)) + tide * 0.4, 0, 1)
    return col, alpha.astype(F)


def tex_faience(res=512, seed=541):
    """Quimper-style faience plate (glaze + blue/yellow bands + stylised flower), no text.
    UV: plate disc mapped to the unit square."""
    X, Y = grid(res)
    cx, cy = (X - 0.5) * 2, (Y - 0.5) * 2
    r = np.sqrt(cx * cx + cy * cy)
    ang = np.arctan2(cy, cx)
    glaze = mix(rgb((0.86, 0.83, 0.74), X.shape), rgb((0.80, 0.76, 0.66), X.shape),
                sstep(-0.3, 0.6, fbm(X, Y, 3, 3, seed)))
    blue = rgb((0.10, 0.20, 0.52), X.shape)
    yel = rgb((0.85, 0.62, 0.15), X.shape)
    red = rgb((0.62, 0.15, 0.09), X.shape)
    grn = rgb((0.18, 0.40, 0.20), X.shape)
    c = glaze
    band = lambda r0, r1: sstep(r0 - 0.008, r0, r) * sstep(r1 + 0.008, r1, r)
    c = mix(c, blue, band(0.92, 0.97)[..., None])
    c = mix(c, yel, band(0.86, 0.89)[..., None])
    c = mix(c, blue, band(0.80, 0.815)[..., None])
    # brush-stroke garland in the rim
    garl = band(0.83, 0.86) * sstep(0.2, 0.6, np.sin(ang * 16))
    c = mix(c, red, garl[..., None] * 0.9)
    # central flower: petals + leaves
    pet = sstep(0.35, 0.3, r * (1.0 + 0.45 * np.cos(ang * 5))) * sstep(0.05, 0.08, r)
    c = mix(c, blue, pet[..., None])
    cen = sstep(0.07, 0.05, r)
    c = mix(c, yel, cen[..., None])
    leaf = sstep(0.06, 0.0, np.abs(r - 0.5) + 0.25 * np.abs(np.sin(ang * 3 + 0.4)) - 0.08) * (r < 0.62)
    c = mix(c, grn, leaf[..., None] * 0.9)
    crackle = sstep(0.985, 0.995, ridged(X, Y, 18, 2, seed + 1))
    c = mix(c, c * 0.8, crackle[..., None] * 0.5)
    c = np.where((r > 1.0)[..., None], glaze, c)
    return c


def tex_poster(kind, w=512, h=768, seed=551):
    """Generic aperitif / tobacco posters: flat colour shapes, blank lettering bars (no text)."""
    X, Y = grid(h, w)
    v = 1.0 - Y
    paper = mix(rgb((0.80, 0.74, 0.60), X.shape), rgb((0.68, 0.60, 0.45), X.shape), sstep(-0.2, 0.7, fbm(X, Y, 3, 4, seed)))
    if kind == "a":       # red aperitif poster: sun disc, bottle silhouette, blank title bars
        c = mix(rgb((0.62, 0.10, 0.07), X.shape), rgb((0.50, 0.07, 0.05), X.shape), v[..., None])
        disc = sstep(0.27, 0.26, np.sqrt((X - 0.5) ** 2 + ((v - 0.58) * h / w) ** 2 * 1.0))
        c = mix(c, rgb((0.92, 0.70, 0.18), X.shape), disc[..., None])
        # bottle silhouette
        bx = np.abs(X - 0.5)
        body = (bx < 0.09) & (v > 0.24) & (v < 0.6)
        shoulder = (bx < 0.09 - (v - 0.6) * 0.5) & (v >= 0.6) & (v < 0.72)
        neck = (bx < 0.03) & (v >= 0.66) & (v < 0.82)
        bottle = body | shoulder | neck
        c = np.where(bottle[..., None], rgb((0.06, 0.05, 0.05), X.shape), c)
        lab = (bx < 0.075) & (v > 0.36) & (v < 0.46)
        c = np.where(lab[..., None], rgb((0.90, 0.84, 0.66), X.shape), c)
        bars = ((v > 0.84) & (v < 0.93) & (np.abs(X - 0.5) < 0.4)) | ((v > 0.07) & (v < 0.13) & (np.abs(X - 0.5) < 0.3))
        c = np.where(bars[..., None], rgb((0.95, 0.88, 0.66), X.shape), c)
    else:                 # blue/cream poster: diagonal rays, glass silhouette, blank band
        ray = (np.floor((np.arctan2(v - 0.3, X - 0.5) + 3.2) * 4.0) % 2).astype(F)
        c = mix(rgb((0.12, 0.22, 0.45), X.shape), rgb((0.20, 0.33, 0.58), X.shape), ray[..., None])
        gx = np.abs(X - 0.5)
        bowl = (gx < 0.16 - (0.62 - v) * 0.5) & (v > 0.42) & (v < 0.62)
        stem = (gx < 0.015) & (v > 0.26) & (v <= 0.42)
        foot = (gx < 0.1) & (v > 0.24) & (v < 0.27)
        glass = bowl | stem | foot
        c = np.where(glass[..., None], rgb((0.92, 0.86, 0.70), X.shape), c)
        wine = (gx < 0.13 - (0.58 - v) * 0.45) & (v > 0.46) & (v < 0.56)
        c = np.where(wine[..., None], rgb((0.55, 0.08, 0.10), X.shape), c)
        band = (v > 0.78) & (v < 0.92)
        c = np.where(band[..., None], rgb((0.90, 0.80, 0.25), X.shape), c)
        bars = (v > 0.07) & (v < 0.14) & (np.abs(X - 0.5) < 0.35)
        c = np.where(bars[..., None], rgb((0.92, 0.86, 0.68), X.shape), c)
    margin = (X < 0.035) | (X > 0.965) | (v < 0.03) | (v > 0.97)
    c = np.where(margin[..., None], paper, c)
    # ageing: fading, foxing, creases
    fade = sstep(-0.3, 0.8, fbm(X, Y, 3, 4, seed + 1))
    c = mix(c, c * 0.8 + 0.12, fade[..., None] * 0.35)
    fox = sstep(0.6, 0.8, fbm(X, Y, 12, 3, seed + 2))
    c = mix(c, rgb((0.45, 0.34, 0.20), X.shape), fox[..., None] * 0.4)
    crease = sstep(0.006, 0.0, np.abs(X - 0.5)) + sstep(0.004, 0.0, np.abs(v - 0.5))
    c = mix(c, c * 0.75, np.clip(crease, 0, 1)[..., None] * 0.6)
    return c


def tex_hay(res=1024, seed=561):
    """Loose straw/hay, 1 m tile."""
    X, Y = grid(res)
    px = 1.0 / res
    h = np.zeros_like(X)
    col_acc = np.zeros(X.shape + (3,), F)
    for k in range(6):
        a = k * 0.53
        u = X * math.cos(a) + Y * math.sin(a)
        s = perlin(X, Y, 40 + k * 7, 40 + k * 7, seed + k)
        f = np.abs(np.sin((u * (90 + k * 13) + s * 3.0) * np.pi))
        m = sstep(0.82, 0.97, f) * sstep(-0.2, 0.5, fbm(X, Y, 8, 3, seed + 10 + k))
        h = np.maximum(h, m * (0.004 + 0.002 * k))
    base = mix(rgb((0.45, 0.36, 0.18), X.shape), rgb((0.66, 0.55, 0.30), X.shape), sstep(0.0, 0.01, h))
    base *= (0.8 + 0.25 * fbm(X, Y, 6, 3, seed + 20))[..., None]
    dark = sstep(0.004, 0.0, h)
    base = mix(base, base * 0.45, dark[..., None] * 0.7)
    h = h.astype(F)
    ao = cavity_ao(h, px, (0.002, 0.006), 1.3)
    return base, height_to_normal(h, px, 1.0), orm(ao, 0.92 + 0 * h), h


# =============================================================== driver
def _exists(*names):
    return all(os.path.exists(os.path.join(TEX_DIR, n)) for n in names)


def ensure(force=False, log=print):
    os.makedirs(TEX_DIR, exist_ok=True)
    t0 = time.time()
    if force or not _exists("plaster_albedo.png", "plaster_normal.png", "plaster_orm.png"):
        rub = envtex.tex_rubble()
        a, n, o, _ = tex_plaster(rub)
        save_set(TEX_DIR, "plaster", a, n, o)
        log(f"[itex] plaster {time.time() - t0:.1f}s")
    if force or not _exists("flags_albedo.png"):
        a, n, o, _ = tex_flags()
        save_set(TEX_DIR, "flags", a, n, o)
        log(f"[itex] flags {time.time() - t0:.1f}s")
    if force or not _exists("furn_normal.png", "furn_chestnut_albedo.png"):
        n, o, cols = tex_furn_wood()
        write_png(os.path.join(TEX_DIR, "furn_normal.png"), n)
        write_png(os.path.join(TEX_DIR, "furn_orm.png"), o)
        for k, a in cols.items():
            write_png(os.path.join(TEX_DIR, f"furn_{k}_albedo.png"), a)
        log(f"[itex] furniture wood {time.time() - t0:.1f}s")
    if force or not _exists("door_bleu_albedo.png"):
        for k, a in tex_door_paint().items():
            write_png(os.path.join(TEX_DIR, f"door_{k}_albedo.png"), a)
        log(f"[itex] door paints {time.time() - t0:.1f}s")
    if force or not _exists("decal_damp_patch_albedo.png"):
        c, al = tex_damp_patch()
        write_png(os.path.join(TEX_DIR, "decal_damp_patch_albedo.png"), np.dstack([c, al]))
    if force or not _exists("faience_albedo.png"):
        write_png(os.path.join(TEX_DIR, "faience_albedo.png"), tex_faience())
    if force or not _exists("poster_a_albedo.png", "poster_b_albedo.png"):
        write_png(os.path.join(TEX_DIR, "poster_a_albedo.png"), tex_poster("a"))
        write_png(os.path.join(TEX_DIR, "poster_b_albedo.png"), tex_poster("b", seed=557))
    if force or not _exists("hay_albedo.png"):
        a, n, o, _ = tex_hay()
        save_set(TEX_DIR, "hay", a, n, o)
    if force or not _exists("linen_albedo.png", "blanket_albedo.png"):
        b = envtex.tex_burlap()[0]
        lum = b.mean(axis=2, keepdims=True)
        write_png(os.path.join(TEX_DIR, "linen_albedo.png"), np.clip(0.25 + lum * 1.35, 0, 1) * np.array((0.98, 0.95, 0.86), F))
        write_png(os.path.join(TEX_DIR, "blanket_albedo.png"), np.clip(lum * 1.3, 0, 1) * np.array((0.95, 0.30, 0.20), F))
    log(f"[itex] done {time.time() - t0:.1f}s")


# ============================================================ materials
def install():
    """Patch geo.std so the mesh builder knows the interior materials."""
    import geo
    if getattr(geo, "_interior_patched", False):
        return
    env_std = geo.std
    tm, fm = geo.tex_mat, geo.flat_mat

    def T(s, folder=TEX_DIR):
        return dict(albedo=f"{s}_albedo.png", normal=f"{s}_normal.png", orm=f"{s}_orm.png", folder=folder)

    def std(name):
        if name in geo._MATS:
            return geo._MATS[name]
        if name == "Plaster":
            return tm("Plaster", **T("plaster"))
        if name == "PlasterSoot":
            return tm("PlasterSoot", **T("plaster"), tint=(0.42, 0.39, 0.35))
        if name == "Flags":
            return tm("Flags", **T("flags"))
        if name == "Hay":
            return tm("Hay", **T("hay"))
        if name.startswith("Furn_"):          # Furn_chestnut / Furn_oak / Furn_black
            c = name.split("_", 1)[1]
            return tm(name, f"furn_{c}_albedo.png", "furn_normal.png", "furn_orm.png", folder=TEX_DIR)
        if name.startswith("Door_"):          # Door_bleu / Door_bottle / Door_oxblood
            c = name.split("_", 1)[1]
            return tm(name, f"door_{c}_albedo.png", os.path.join(ENV_TEX, "wood_paint_normal.png"),
                      os.path.join(ENV_TEX, "wood_paint_orm.png"), folder=TEX_DIR)
        if name == "Soot":
            return tm("Soot", "rubble_albedo.png", "rubble_normal.png", "rubble_orm.png", folder=ENV_TEX,
                      tint=(0.16, 0.15, 0.14))
        if name == "GraniteSoot":
            return tm("GraniteSoot", "granite_albedo.png", "granite_normal.png", "granite_orm.png", folder=ENV_TEX,
                      tint=(0.55, 0.52, 0.5))
        if name in ("Linen", "Blanket"):
            return tm(name, f"{name.lower()}_albedo.png", os.path.join(ENV_TEX, "burlap_normal.png"),
                      os.path.join(ENV_TEX, "burlap_orm.png"), folder=TEX_DIR, nstrength=0.5)
        if name == "Faience":
            return tm("Faience", "faience_albedo.png", folder=TEX_DIR, rough=0.22)
        if name in ("Poster_a", "Poster_b"):
            return tm(name, f"poster_{name[-1]}_albedo.png", folder=TEX_DIR, rough=0.85)
        if name == "DecalDampPatch":
            return tm("DecalDampPatch", "decal_damp_patch_albedo.png", folder=TEX_DIR, alpha=True, rough=0.6)
        if name == "Embers":
            return fm("Embers", (0.20, 0.05, 0.02), rough=0.9, emission=(1.0, 0.25, 0.05), estrength=0.9)
        if name == "Ash":
            return fm("Ash", (0.11, 0.105, 0.10), rough=0.95)
        if name == "Brass":
            return fm("Brass", (0.50, 0.37, 0.17), rough=0.38, metal=1.0)
        if name == "BottleGreen":
            return fm("BottleGreen", (0.02, 0.07, 0.03), rough=0.08)
        if name == "BottleAmber":
            return fm("BottleAmber", (0.09, 0.035, 0.01), rough=0.08)
        if name == "BottleClear":
            return fm("BottleClear", (0.16, 0.18, 0.17), rough=0.05)
        if name == "EnamelGreen":
            return fm("EnamelGreen", (0.07, 0.16, 0.10), rough=0.3)
        if name == "EnamelWhite":
            return fm("EnamelWhite", (0.78, 0.76, 0.70), rough=0.3)
        if name == "Pewter":
            return fm("Pewter", (0.40, 0.40, 0.39), rough=0.45, metal=0.9)
        if name == "Copper":
            return fm("Copper", (0.55, 0.27, 0.15), rough=0.4, metal=1.0)
        if name == "Mirror":
            return fm("Mirror", (0.55, 0.55, 0.55), rough=0.08, metal=1.0)
        if name == "Candle":
            return fm("Candle", (0.80, 0.76, 0.62), rough=0.5)
        if name == "LampGlow":     # lamp chimney / bulb: emissive, Godot places the actual light
            return fm("LampGlow", (0.9, 0.7, 0.45), rough=0.2, emission=(1.0, 0.62, 0.30), estrength=6.0)
        if name == "Bread":
            return fm("Bread", (0.42, 0.25, 0.10), rough=0.8)
        return env_std(name)

    geo.std = std
    geo._interior_patched = True


if __name__ == "__main__":
    ensure(force="--force" in sys.argv)
