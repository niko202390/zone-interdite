"""Texture recipes for the Breton village kit.

Run standalone with Blender's bundled Python (numpy):
    python.exe textures.py [names...] [--force]
or import and call ensure([...]) from build_env.py.

Ground sets go to game/assets/textures/ground/ (2 m tile, 2048^2).
Building/prop masters go to tools/blender/env/out/tex/ (packed into .glb).
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from texlib import (F, blur, cavity_ao, cell_rand, fbm, grid, height_to_normal,  # noqa: E402
                    lichen_mask, mix, orm, palette_pick, perlin, rgb, ridged,
                    save_set, sstep, voronoi, write_png)

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GROUND_DIR = os.path.join(ROOT, "game", "assets", "textures", "ground")
TEX_DIR = os.path.join(HERE, "out", "tex")


def _speckle(X, Y, seed, dark=0.5, light=0.5, scale=700):
    """Granite crystal speckle: returns (dark_mask, light_mask)."""
    d = perlin(X, Y, scale, scale, seed)
    l = perlin(X, Y, int(scale * 0.8), int(scale * 0.8), seed + 1)
    dm = sstep(dark * 0.9, dark * 1.25, d)
    lm = sstep(light * 0.9, light * 1.2, l)
    return dm, lm


def _row_cells(V, U, rows, wmin, wmax, seed, stagger=None):
    """Running-bond rows of variable-width cells, tileable.
    Returns row index, cell id, local x/y (tile units), half width, half height."""
    rng = np.random.default_rng(seed)
    max_st = int(np.ceil(1.0 / wmin)) + 2
    bounds = np.full((rows, max_st + 1), 2.0, F)
    offs = rng.random(rows).astype(F) if stagger is None else np.array(
        [(i % 2) * stagger + rng.uniform(-0.02, 0.02) for i in range(rows)], F)
    for i in range(rows):
        ws = []
        while sum(ws) < 1.0:
            ws.append(rng.uniform(wmin, wmax))
        ws = np.array(ws, F)
        ws /= ws.sum()
        b = np.concatenate([[0.0], np.cumsum(ws)])
        b[-1] = 1.0
        bounds[i, :len(b)] = b
    r = np.floor(V * rows).astype(np.int32) % rows
    ux = (U + offs[r]) % 1.0
    flat = (bounds + (np.arange(rows, dtype=F)[:, None] * 10.0)).ravel()
    idx = np.searchsorted(flat, ux + r * 10.0, side="right") - 1
    left = flat[idx] - r * 10.0
    right = flat[idx + 1] - r * 10.0
    col = idx - r * (max_st + 1)
    cid = r * max_st + col
    lx = ux - (left + right) * 0.5
    hw = (right - left) * 0.5
    ly = (V * rows - np.floor(V * rows) - 0.5) / rows
    hh = np.full_like(lx, 0.5 / rows)
    return r, cid, lx, ly, hw, hh


def _round_rect_sdf(lx, ly, hx, hy, rad):
    qx = np.abs(lx) - (hx - rad)
    qy = np.abs(ly) - (hy - rad)
    out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2)
    inn = np.minimum(np.maximum(qx, qy), 0)
    return out + inn - rad


# =============================================================== GROUND SETS
def tex_cobble(res=2048, seed=11):
    """Wet granite setts (pavés) with muddy joints and puddles. 2 m tile."""
    X, Y = grid(res)
    px = 2.0 / res
    U = (X + fbm(X, Y, 6, 3, seed + 1) * 0.005) % 1.0
    V = (1.0 - Y + fbm(X, Y, 6, 3, seed + 2) * 0.004) % 1.0
    r, cid, lx, ly, hw, hh = _row_cells(V, U, 15, 0.052, 0.085, seed)
    rr = cell_rand(cid, seed + 3, 8)
    # small per-stone rotation
    a = (rr[..., 0] - 0.5) * 0.08
    lxm, lym = lx * 2.0, ly * 2.0                     # metres
    rx = lxm * np.cos(a) - lym * np.sin(a)
    ry = lxm * np.sin(a) + lym * np.cos(a)
    gap = 0.005 + rr[..., 1] * 0.006
    hx = hw * 2.0 - gap
    hy = hh * 2.0 - gap - rr[..., 2] * 0.008
    sdf = _round_rect_sdf(rx, ry, hx, hy, 0.022 + rr[..., 3] * 0.02)
    sdf += fbm(X, Y, 40, 3, seed + 4) * 0.007 + fbm(X, Y, 14, 2, seed + 14) * 0.006
    inside = -sdf
    nxp = rx / np.maximum(hx, 1e-3)
    nyp = ry / np.maximum(hy, 1e-3)
    crown = (0.004 + rr[..., 4] * 0.012) * (1.0 - 0.7 * (nxp ** 2 + nyp ** 2))
    tilt = (rr[..., 5] - 0.5) * 0.01 * nxp + (rr[..., 6] - 0.5) * 0.008 * nyp
    edge = np.sqrt(np.clip(inside / 0.02, 0, 1))
    micro = fbm(X, Y, 90, 4, seed + 5) * 0.0012 + ridged(X, Y, 30, 3, seed + 6) * 0.0008
    h_stone = 0.016 * edge + crown + tilt + micro
    h_joint = -0.004 + fbm(X, Y, 24, 4, seed + 7) * 0.003
    is_stone = inside > 0
    h = np.where(is_stone, np.maximum(h_stone, h_joint), h_joint).astype(F)

    # wetness/puddles: low frequency mask
    wet = sstep(-0.1, 0.35, fbm(X, Y, 3, 4, seed + 8))
    water_lvl = -0.002 + 0.006 * wet
    water = (h < water_lvl) & (wet > 0.15)
    h_final = np.where(water, water_lvl, h).astype(F)

    # albedo
    stone_cols = [(0.44, 0.43, 0.42), (0.37, 0.37, 0.38), (0.47, 0.44, 0.40),
                  (0.42, 0.38, 0.36), (0.31, 0.31, 0.32), (0.51, 0.48, 0.44), (0.40, 0.39, 0.34)]
    base = palette_pick(rr[..., 7], stone_cols)
    dm, lm = _speckle(X, Y, seed + 9, 0.45, 0.5, 650)
    base = base * (1.0 - 0.55 * dm[..., None]) + 0.12 * lm[..., None]
    base *= (0.9 + 0.12 * fbm(X, Y, 10, 4, seed + 10))[..., None]
    dirt_edge = 1.0 - sstep(0.0, 0.025, inside)
    base = mix(base, rgb((0.16, 0.13, 0.10), X.shape), np.clip(dirt_edge * 0.6, 0, 1))
    joint_col = mix(rgb((0.12, 0.10, 0.08), X.shape), rgb((0.26, 0.22, 0.17), X.shape),
                    sstep(-0.4, 0.6, fbm(X, Y, 30, 3, seed + 11)))
    moss = sstep(0.3, 0.6, fbm(X, Y, 12, 4, seed + 12)) * 0.7
    joint_col = mix(joint_col, rgb((0.10, 0.14, 0.06), X.shape), moss)
    alb = np.where(is_stone[..., None], base, joint_col)
    wet_dark = 0.72 + 0.06 * (1.0 - wet)
    alb = alb * wet_dark[..., None]
    alb = np.where(water[..., None], alb * 0.55, alb)

    rough = np.where(is_stone, 0.40 - 0.06 * wet + 0.08 * fbm(X, Y, 20, 3, seed + 13), 0.55 - 0.1 * wet)
    rough = np.where(water, 0.04, rough)
    ao = cavity_ao(h_final, px, (0.006, 0.02, 0.05), 1.2)
    nrm = height_to_normal(h_final, px, 1.0)
    return alb, nrm, orm(ao, rough), h_final


def tex_mud(res=2048, seed=21):
    """Wet rutted track: churned mud, hoof/boot prints, stones, puddles."""
    X, Y = grid(res)
    px = 2.0 / res
    h = fbm(X, Y, 4, 8, seed) * 0.022
    h += fbm(X, Y, 3, 5, seed + 1, aniso=(5, 1)) * 0.012           # rut streaks along v
    h += ridged(X, Y, 8, 4, seed + 2) * 0.009
    h += ridged(X, Y, 26, 3, seed + 22) * 0.003
    rng = np.random.default_rng(seed + 3)
    # prints
    pw = fbm(X, Y, 30, 3, seed + 23)
    for i in range(30):
        cx, cy = rng.random(2)
        ang = rng.uniform(0, np.pi)
        sx, sy = rng.uniform(0.05, 0.08), rng.uniform(0.035, 0.055)  # metres half-size
        dx = ((X - cx + 0.5) % 1.0 - 0.5) * 2.0
        dy = ((Y - cy + 0.5) % 1.0 - 0.5) * 2.0
        u = dx * np.cos(ang) + dy * np.sin(ang)
        v = -dx * np.sin(ang) + dy * np.cos(ang)
        if i % 3 == 0:   # horse-shoe: open at the heel
            d = np.sqrt((u / sx) ** 2 + (v / sy) ** 2) + pw * 0.35
            depth = sstep(1.0, 0.6, d) * sstep(-0.9, -0.2, u / sx)
        else:            # boot/hoof scuff, soft and irregular
            d = np.sqrt((u / sx) ** 2 + (v / sy) ** 2) + pw * 0.45
            depth = sstep(1.0, 0.35, d)
        h += -0.010 * depth + 0.0025 * sstep(1.4, 1.0, d) * sstep(0.85, 1.1, d)
    # embedded stones
    f1, f2, cid, _, _ = voronoi(X, Y, 70, 70, seed + 4, 0.9)
    rs = cell_rand(cid, seed + 5, 3)
    st = (rs[..., 0] < 0.06)
    st_in = (f2 - f1) * 1.0 - 0.003
    h_st = 0.006 * np.sqrt(np.clip(st_in / 0.01, 0, 1))
    stone = st & (st_in > 0)
    h = np.where(stone, np.maximum(h, h_st + 0.002), h).astype(F)
    water_lvl = -0.011
    water = h < water_lvl
    h_final = np.where(water, water_lvl, h).astype(F)
    hn = (h - h.min()) / (h.max() - h.min())
    alb = mix(rgb((0.12, 0.095, 0.07), X.shape), rgb((0.25, 0.20, 0.145), X.shape), sstep(0.35, 0.8, hn))
    alb *= (0.9 + 0.15 * fbm(X, Y, 16, 3, seed + 6))[..., None]
    alb = np.where(stone[..., None], palette_pick(rs[..., 1], [(0.35, 0.34, 0.32), (0.42, 0.38, 0.33), (0.28, 0.27, 0.26)]), alb)
    alb = np.where(water[..., None], rgb((0.10, 0.08, 0.06), X.shape), alb)
    rough = 0.38 + 0.3 * sstep(0.4, 0.9, hn)
    rough = np.where(stone, 0.55, rough)
    rough = np.where(water, 0.03, rough)
    ao = cavity_ao(h_final, px, (0.01, 0.04), 1.0)
    return alb, height_to_normal(h_final, px, 1.0), orm(ao, rough), h_final


def _splat_blades(res, specs, seed, flow_seed):
    """Rasterise many short curved blades into a height + id buffer.
    specs: list of dicts n, length(m range), width_px range, base_h, colors, arch, offsets."""
    rng = np.random.default_rng(seed)
    keybuf = np.full(res * res, -1, np.int64)
    blade_cols = []
    gid = 0
    for spec in specs:
        n = spec["n"]
        root = rng.random((n, 2))
        # flow field direction from low-frequency noise sampled at roots
        fl = perlin(root[:, 0].astype(F), root[:, 1].astype(F), 3, 3, flow_seed)
        ang = fl * np.pi * 1.3 + rng.normal(0, spec.get("spread", 0.55), n)
        L = rng.uniform(*spec["length"], n) / 2.0                     # tile units
        curv = rng.normal(0, 0.9, n)
        wpx = rng.uniform(*spec["width_px"], n)
        cols = np.array(spec["colors"], F)[rng.integers(0, len(spec["colors"]), n)]
        cols *= rng.uniform(0.8, 1.15, (n, 1)).astype(F)
        blade_cols.append(cols)
        S = spec.get("steps", 90)
        t = np.linspace(0, 1, S, dtype=F)
        dirx, diry = np.cos(ang)[:, None], np.sin(ang)[:, None]
        perx, pery = -diry, dirx
        bend = (curv * L)[:, None] * (t[None, :] ** 2) * 0.35
        bx = root[:, 0:1] + dirx * L[:, None] * t + perx * bend
        by = root[:, 1:2] + diry * L[:, None] * t + pery * bend
        offs = np.linspace(-0.5, 0.5, spec.get("offsets", 3), dtype=F)
        taper = (1.0 - 0.75 * t ** 1.5)[None, :]
        hrand = rng.uniform(0, 0.002, (n, 1))
        for o in offs:
            w = (wpx[:, None] * taper * o) / res
            qx = ((bx + perx * w) % 1.0 * res).astype(np.int64) % res
            qy = ((by + pery * w) % 1.0 * res).astype(np.int64) % res
            hgt = spec["base_h"] + spec.get("arch", 0.004) * np.sin(np.pi * np.clip(t * 0.9, 0, 1))[None, :] \
                + 0.0008 * (1 - 4 * o * o) + hrand
            hq = np.clip((hgt * 1e5).astype(np.int64), 0, (1 << 22) - 1)
            tq = (np.broadcast_to(t[None, :], hq.shape) * 255).astype(np.int64)
            ids = np.broadcast_to((gid + np.arange(n))[:, None], hq.shape).astype(np.int64)
            keys = (hq << 40) | (ids << 8) | tq
            np.maximum.at(keybuf, (qy * res + qx).ravel(), keys.ravel())
        gid += n
    allcols = np.concatenate(blade_cols, 0)
    has = keybuf >= 0
    hq = np.where(has, keybuf >> 40, 0)
    ids = np.where(has, (keybuf >> 8) & ((1 << 32) - 1), 0)
    tq = np.where(has, keybuf & 255, 0)
    hgt = (hq / 1e5).astype(F).reshape(res, res)
    col = allcols[ids].reshape(res, res, 3)
    tt = (tq / 255.0).astype(F).reshape(res, res)
    return has.reshape(res, res), hgt, col, tt


def tex_grass_winter(res=2048, seed=31):
    """Matted dormant winter grass over damp soil."""
    X, Y = grid(res)
    px = 2.0 / res
    soil_h = fbm(X, Y, 8, 6, seed) * 0.003
    soil = mix(rgb((0.09, 0.07, 0.05), X.shape), rgb((0.17, 0.13, 0.09), X.shape), sstep(-0.3, 0.5, fbm(X, Y, 12, 4, seed + 1)))
    specs = [
        dict(n=26000, length=(0.05, 0.12), width_px=(2.0, 3.5), base_h=0.0005, arch=0.002,
             colors=[(0.20, 0.15, 0.09), (0.25, 0.19, 0.11), (0.17, 0.14, 0.08)]),
        dict(n=24000, length=(0.07, 0.16), width_px=(2.0, 4.0), base_h=0.003, arch=0.004,
             colors=[(0.46, 0.38, 0.22), (0.40, 0.32, 0.18), (0.52, 0.44, 0.28), (0.33, 0.27, 0.15)]),
        dict(n=16000, length=(0.07, 0.18), width_px=(2.0, 4.0), base_h=0.006, arch=0.005,
             colors=[(0.26, 0.33, 0.14), (0.21, 0.29, 0.11), (0.30, 0.36, 0.16), (0.55, 0.48, 0.30), (0.42, 0.38, 0.20), (0.24, 0.31, 0.15)]),
        dict(n=900, length=(0.03, 0.05), width_px=(12.0, 20.0), base_h=0.0085, arch=0.001, offsets=9, steps=40,
             spread=2.5, colors=[(0.30, 0.17, 0.08), (0.36, 0.22, 0.10), (0.22, 0.13, 0.07)]),
    ]
    has, bh, bcol, bt = _splat_blades(res, specs, seed + 2, seed + 3)
    shade = (0.7 + 0.45 * bt)[..., None]
    alb = np.where(has[..., None], bcol * shade, soil)
    h = np.where(has, bh, soil_h).astype(F)
    h = blur(h, 0.6)
    rough = np.where(has, 0.62 - 0.15 * sstep(0.3, 0.7, fbm(X, Y, 6, 3, seed + 4)), 0.8)
    ao = cavity_ao(h, px, (0.003, 0.01, 0.03), 1.4)
    alb *= (0.55 + 0.45 * ao)[..., None]
    return alb, height_to_normal(h, px, 1.6), orm(ao, rough), h


def tex_gravel(res=2048, seed=41):
    """Damp road gravel: mixed pebbles in fine grit."""
    X, Y = grid(res)
    px = 2.0 / res
    gw = fbm(X, Y, 60, 2, seed + 30) * 0.0022
    f1, f2, cid, _, _ = voronoi(X + gw, Y - gw, 100, 100, seed, 0.8)
    r = cell_rand(cid, seed + 1, 4)
    R = (0.42 / 100) * (0.65 + 0.5 * r[..., 0])                       # tile units
    rnd = np.sqrt(np.clip(1 - (f1 / R) ** 2, 0, 1))
    poly = np.sqrt(np.clip(((f2 - f1) - 0.0006) / 0.004, 0, 1))
    shape = np.minimum(rnd, poly)
    inside = shape - 0.02
    h = 0.006 * shape * (0.6 + 0.8 * r[..., 1])
    h += fbm(X, Y, 120, 3, seed + 2) * 0.0006
    pal = [(0.42, 0.41, 0.39), (0.50, 0.46, 0.40), (0.34, 0.33, 0.32), (0.58, 0.56, 0.52),
           (0.45, 0.33, 0.24), (0.25, 0.25, 0.26), (0.66, 0.64, 0.60)]
    col = palette_pick(r[..., 2], pal, [3, 3, 2, 1, 1, 1, 0.5])
    gw2 = fbm(X, Y, 18, 2, seed + 31) * 0.006
    f1b, f2b, cidb, _, _ = voronoi(X + gw2, Y + gw2, 26, 26, seed + 3, 0.8)
    rb = cell_rand(cidb, seed + 4, 3)
    Rb = (0.40 / 26) * (0.6 + 0.5 * rb[..., 2])
    shb = np.minimum(np.sqrt(np.clip(1 - (f1b / Rb) ** 2, 0, 1)), np.sqrt(np.clip(((f2b - f1b) - 0.001) / 0.01, 0, 1)))
    inb = shb - 0.02
    big = (rb[..., 0] < 0.3) & (inb > 0)
    hb = 0.013 * shb + 0.003
    h = np.where(big, np.maximum(h, hb), h)
    col = np.where(big[..., None], palette_pick(rb[..., 1], pal), col)
    grit = inside <= 0
    grit_col = mix(rgb((0.22, 0.19, 0.15), X.shape), rgb((0.32, 0.28, 0.23), X.shape), sstep(-0.5, 0.5, perlin(X, Y, 300, 300, seed + 5)))
    alb = np.where((grit & ~big)[..., None], grit_col, col)
    dm, lm = _speckle(X, Y, seed + 6, 0.5, 0.55, 900)
    alb = alb * (1 - 0.3 * dm[..., None]) + 0.06 * lm[..., None]
    damp = sstep(-0.2, 0.5, fbm(X, Y, 3, 4, seed + 7))
    alb *= (0.72 + 0.2 * (1 - damp))[..., None]
    h = h.astype(F)
    rough = np.where(grit & ~big, 0.85, 0.62 - 0.2 * damp)
    ao = cavity_ao(h, px, (0.003, 0.01, 0.03), 1.3)
    return alb, height_to_normal(h, px, 1.0), orm(ao, rough), h


# ============================================================ BUILDING SETS
def _var_rows(V, U, hmin, hmax, wmin, wmax, seed):
    """Courses of variable height, each split into variable-width stones (tileable)."""
    rng = np.random.default_rng(seed)
    hs = []
    while sum(hs) < 1.0:
        hs.append(rng.uniform(hmin, hmax))
    hs = np.array(hs, F)
    hs /= hs.sum()
    rb = np.concatenate([[0.0], np.cumsum(hs)]).astype(F)
    rb[-1] = 1.0
    rows = len(hs)
    r = np.clip(np.searchsorted(rb, V, side="right") - 1, 0, rows - 1)
    max_st = int(np.ceil(1.0 / wmin)) + 2
    bounds = np.full((rows, max_st + 1), 2.0, F)
    offs = rng.random(rows).astype(F)
    for i in range(rows):
        ws = []
        while sum(ws) < 1.0:
            ws.append(rng.uniform(wmin, wmax))
        ws = np.array(ws, F)
        ws /= ws.sum()
        bb = np.concatenate([[0.0], np.cumsum(ws)])
        bb[-1] = 1.0
        bounds[i, :len(bb)] = bb
    ux = (U + offs[r]) % 1.0
    flat = (bounds + (np.arange(rows, dtype=F)[:, None] * 10.0)).ravel()
    idx = np.searchsorted(flat, ux + r * 10.0, side="right") - 1
    left = flat[idx] - r * 10.0
    right = flat[idx + 1] - r * 10.0
    cid = r * max_st + (idx - r * (max_st + 1))
    lx = ux - (left + right) * 0.5
    hw = (right - left) * 0.5
    ly = V - (rb[r] + rb[r + 1]) * 0.5
    hh = (rb[r + 1] - rb[r]) * 0.5
    return cid, lx, ly, hw, hh


def tex_rubble(res=2048, seed=51):
    """Breton granite rubble (moellons), roughly coursed, irregular, in recessed lime mortar. 2 m tile."""
    X, Y = grid(res)
    px = 2.0 / res
    U = (X + fbm(X, Y, 7, 3, seed) * 0.008) % 1.0
    V = (1.0 - Y + fbm(X, Y, 7, 3, seed + 1) * 0.006) % 1.0
    cid, lx, ly, hw, hh = _var_rows(V, U, 0.055, 0.11, 0.07, 0.21, seed + 2)
    r = cell_rand(cid, seed + 3, 10)
    a = (r[..., 0] - 0.5) * 0.12
    lxm, lym = lx * 2.0, ly * 2.0
    rx = lxm * np.cos(a) - lym * np.sin(a)
    ry = lxm * np.sin(a) + lym * np.cos(a)
    gap = 0.006 + r[..., 1] * 0.009
    hx = hw * 2.0 - gap - r[..., 2] * 0.015
    hy = hh * 2.0 - gap - r[..., 3] * 0.01
    rad = 0.008 + r[..., 4] * 0.03
    sdf = _round_rect_sdf(rx, ry, np.maximum(hx, 0.03), np.maximum(hy, 0.03), np.minimum(rad, np.minimum(hx, hy) * 0.9))
    sdf += fbm(X, Y, 20, 4, seed + 4) * 0.012 + fbm(X, Y, 60, 2, seed + 5) * 0.003
    inside = -sdf
    is_stone = inside > 0
    edge = sstep(0.0, 0.014, inside)
    face = fbm(X, Y, 14, 5, seed + 6) * 0.004 + ridged(X, Y, 9, 3, seed + 7) * 0.003 + perlin(X, Y, 300, 300, seed + 8) * 0.0004
    nxp = rx / np.maximum(hx, 1e-3)
    nyp = ry / np.maximum(hy, 1e-3)
    dome = (1.0 - 0.5 * np.clip(nxp * nxp + nyp * nyp, 0, 1)) * (0.002 + 0.004 * r[..., 5])
    plane = (r[..., 6] - 0.5) * 0.012 + (r[..., 7] - 0.5) * 0.006 * nxp
    h_stone = 0.014 + plane + dome + face
    h_mort = -0.006 + fbm(X, Y, 40, 4, seed + 9) * 0.003 + perlin(X, Y, 400, 400, seed + 10) * 0.0005
    h = np.where(is_stone, h_mort + (h_stone - h_mort) * edge, h_mort).astype(F)

    pal = [(0.47, 0.46, 0.44), (0.52, 0.48, 0.41), (0.49, 0.45, 0.42), (0.36, 0.36, 0.35),
           (0.43, 0.39, 0.34), (0.57, 0.56, 0.53), (0.50, 0.45, 0.37), (0.40, 0.41, 0.40)]
    col = palette_pick(r[..., 8], pal, [3.5, 2.5, 1.2, 1.0, 1.0, 1.0, 1.5, 1.5])
    dm, lm = _speckle(X, Y, seed + 11, 0.42, 0.48, 520)
    col = col * (1 - 0.45 * dm[..., None]) + 0.09 * lm[..., None]
    col *= (0.86 + 0.2 * fbm(X, Y, 9, 4, seed + 12))[..., None]
    iron = sstep(0.5, 0.8, fbm(X, Y, 10, 3, seed + 13)) * (r[..., 9] > 0.8)
    col = mix(col, rgb((0.50, 0.34, 0.20), X.shape), iron * 0.4)
    mort_col = mix(rgb((0.46, 0.44, 0.39), X.shape), rgb((0.33, 0.32, 0.29), X.shape),
                   sstep(-0.4, 0.4, fbm(X, Y, 20, 4, seed + 14)))
    mort_col *= (0.9 + 0.12 * perlin(X, Y, 500, 500, seed + 15))[..., None]
    alb = np.where(is_stone[..., None], mix(col * 0.82, col, edge), mort_col)
    lich_y = lichen_mask(X, Y, seed + 16, 0.07, 16) * is_stone
    lich_g = lichen_mask(X, Y, seed + 17, 0.09, 11) * is_stone
    lich_w = lichen_mask(X, Y, seed + 18, 0.07, 20) * is_stone
    alb = mix(alb, rgb((0.62, 0.50, 0.22), X.shape), lich_y * 0.7)
    alb = mix(alb, rgb((0.52, 0.56, 0.48), X.shape), lich_g * 0.6)
    alb = mix(alb, rgb((0.70, 0.70, 0.66), X.shape), lich_w * 0.5)
    h = h + (lich_y + lich_g) * 0.0005
    rough = np.where(is_stone, 0.80 + 0.1 * fbm(X, Y, 25, 3, seed + 19), 0.93)
    rough = np.clip(rough + (lich_y + lich_g) * 0.05, 0, 1)
    ao = cavity_ao(h, px, (0.006, 0.02, 0.05), 1.2)
    return alb, height_to_normal(h, px, 1.0), orm(ao, rough), h


def tex_granite(res=2048, seed=61):
    """Dressed granite (pierre de taille): bush-hammered, speckled, lichened."""
    X, Y = grid(res)
    px = 2.0 / res
    base = mix(rgb((0.47, 0.47, 0.46), X.shape), rgb((0.53, 0.50, 0.45), X.shape),
               sstep(-0.4, 0.5, fbm(X, Y, 4, 5, seed)))
    dm, lm = _speckle(X, Y, seed + 1, 0.38, 0.42, 480)
    base = base * (1 - 0.7 * dm[..., None]) + 0.17 * lm[..., None]
    pinks = sstep(0.5, 0.7, perlin(X, Y, 500, 500, seed + 2))
    base = mix(base, rgb((0.64, 0.50, 0.45), X.shape), pinks * 0.4)
    f1, _, _, _, _ = voronoi(X, Y, 260, 260, seed + 3, 0.95)
    pits = sstep(0.0014, 0.0004, f1)
    h = fbm(X, Y, 6, 5, seed + 4) * 0.002 - pits * 0.0012 + perlin(X, Y, 400, 400, seed + 5) * 0.0004
    grime = sstep(-0.1, 0.6, fbm(X, Y, 3, 5, seed + 6, aniso=(3, 1)))
    base = mix(base, base * 0.55, grime * 0.45)
    lich_y = lichen_mask(X, Y, seed + 7, 0.06, 14)
    lich_w = lichen_mask(X, Y, seed + 8, 0.08, 18)
    alb = mix(base, rgb((0.62, 0.50, 0.22), X.shape), lich_y * 0.7)
    alb = mix(alb, rgb((0.70, 0.70, 0.66), X.shape), lich_w * 0.5)
    h = (h + (lich_y + lich_w) * 0.0005).astype(F)
    rough = 0.78 + 0.08 * fbm(X, Y, 30, 3, seed + 9)
    ao = cavity_ao(h, px, (0.002, 0.008), 1.0)
    return alb, height_to_normal(h, px, 1.0), orm(ao, rough), h


SLATE_ROWS = 16   # rows per 2 m tile -> 12.5 cm exposure (geometry matches this)


def tex_slate(res=2048, seed=71):
    """Natural slate roof (ardoise): staggered rows, lichen, moss. v runs up-slope."""
    X, Y = grid(res)
    px = 2.0 / res
    U = (X + fbm(X, Y, 8, 2, seed) * 0.0015) % 1.0
    V = (1.0 - Y) % 1.0
    r, cid, lx, ly, hw, hh = _row_cells(V, U, SLATE_ROWS, 0.10, 0.15, seed + 1, stagger=None)
    rr = cell_rand(cid, seed + 2, 8)
    s = ly / (2 * hh) + 0.5                  # 0 = bottom (exposed edge), 1 = top
    # chipped/irregular bottom edge and side gaps
    chip = np.abs(fbm(X, Y, 60, 3, seed + 3)) * 0.12 + rr[..., 0] * 0.05
    gapw = (0.0018 + rr[..., 1] * 0.0018) / 2.0   # tile units
    in_side = (hw - np.abs(lx)) > gapw
    corner = (hw - np.abs(lx)) * 2.0 < (0.012 - s * 0.1)           # clipped corners at bottom
    exposed = (s > chip) & in_side & ~corner
    T = 0.006
    h_sl = T * (1 - s) + fbm(X, Y, 30, 4, seed + 4, aniso=(1, 3)) * 0.0004
    h_sl += (rr[..., 2] - 0.5) * 0.0015
    edge_round = sstep(0.0, 0.04, s - chip)
    h = np.where(exposed, h_sl * (0.6 + 0.4 * edge_round), -0.002).astype(F)
    pal = [(0.20, 0.22, 0.25), (0.23, 0.21, 0.24), (0.20, 0.23, 0.22), (0.28, 0.29, 0.31),
           (0.17, 0.18, 0.20), (0.25, 0.26, 0.28)]
    col = palette_pick(rr[..., 3], pal, [4, 1.5, 1.5, 1.2, 1.5, 2])
    col *= (0.9 + 0.15 * fbm(X, Y, 40, 3, seed + 5, aniso=(1, 2)))[..., None]
    col = mix(col, col * 1.25 + 0.03, sstep(0.0, 0.03, s - chip) * (1 - sstep(0.03, 0.1, s - chip)) * 0.4)
    lich_y = lichen_mask(X, Y, seed + 6, 0.10, 18) * exposed
    lich_w = lichen_mask(X, Y, seed + 7, 0.12, 24) * exposed
    alb = mix(col, rgb((0.62, 0.48, 0.18), X.shape), lich_y * 0.75)
    alb = mix(alb, rgb((0.60, 0.61, 0.58), X.shape), lich_w * 0.5)
    gap_col = rgb((0.04, 0.045, 0.05), X.shape)
    moss = sstep(0.55, 0.75, fbm(X, Y, 10, 4, seed + 8)) * (1 - s) * 1.2
    alb = np.where(exposed[..., None], alb, gap_col)
    alb = mix(alb, rgb((0.10, 0.14, 0.05), X.shape), np.clip(moss, 0, 1) * 0.8)
    h = h + np.clip(moss, 0, 1) * 0.002
    rough = np.where(exposed, 0.46 + 0.12 * fbm(X, Y, 12, 3, seed + 9), 0.9)
    rough = np.clip(rough + (lich_y + lich_w) * 0.35 + np.clip(moss, 0, 1) * 0.4, 0, 1)
    h = h.astype(F)
    ao = cavity_ao(h, px, (0.003, 0.01), 1.4)
    return alb, height_to_normal(h, px, 1.0), orm(ao, rough), h


def tex_render(rubble, res=2048, seed=81):
    """Lime render (enduit) peeling off rubble, algae and grime streaks."""
    r_alb, _, r_orm, r_h = rubble
    X, Y = grid(res)
    px = 2.0 / res
    col = mix(rgb((0.74, 0.70, 0.61), X.shape), rgb((0.66, 0.60, 0.48), X.shape),
              sstep(-0.4, 0.5, fbm(X, Y, 3, 5, seed)))
    streak = sstep(-0.1, 0.6, fbm(X, Y, 4, 5, seed + 1, aniso=(4, 0.5)))
    col = mix(col, col * 0.7, streak * 0.4)
    algae = sstep(0.2, 0.7, fbm(X, Y, 5, 5, seed + 2))
    col = mix(col, rgb((0.43, 0.47, 0.36), X.shape), algae * 0.4)
    col *= (0.93 + 0.08 * perlin(X, Y, 200, 200, seed + 3))[..., None]
    m = fbm(X, Y, 6, 6, seed + 4) + 0.3 * fbm(X, Y, 18, 3, seed + 5)
    exposed = m > 0.36
    lip = sstep(0.36, 0.3, m) * (~exposed)
    h_rend = 0.016 + fbm(X, Y, 30, 4, seed + 6) * 0.0012 + perlin(X, Y, 300, 300, seed + 7) * 0.0002
    h = np.where(exposed, r_h, h_rend).astype(F)
    alb = np.where(exposed[..., None], r_alb * 0.92, col)
    alb = mix(alb, alb * 0.6, lip * 0.5)
    rough = np.where(exposed, r_orm[..., 1], 0.9)
    ao = cavity_ao(h, px, (0.004, 0.015, 0.05), 1.2)
    return alb, height_to_normal(h, px, 1.0), orm(ao, rough), h


# =================================================================== WOOD
PAINTS = {
    "blue": (0.36, 0.44, 0.50),
    "green": (0.25, 0.36, 0.29),
    "oxblood": (0.40, 0.13, 0.10),
    "cream": (0.80, 0.76, 0.66),
}


def _wood_grain(X, Y, seed, planks=7):
    rng = np.random.default_rng(seed)
    ws = rng.uniform(0.8, 1.2, planks)
    b = np.concatenate([[0], np.cumsum(ws / ws.sum())])
    b[-1] = 1.0
    pid = np.clip(np.searchsorted(b, X, side="right") - 1, 0, planks - 1)
    left, right = b[pid], b[pid + 1]
    dist_edge = np.minimum(X - left, right - X)
    poff = (pid * 0.137) % 1.0
    warp = fbm(X, Y, 2, 3, seed + 1) * 0.08
    rings = np.sin((X * 45.0 + warp * 20.0 + poff * 10.0 + fbm(X, Y, 3, 4, seed + 2, aniso=(6, 1)) * 2.5) * 2 * np.pi)
    fibres = perlin(X, Y, 260, 6, seed + 3) * 0.5 + perlin(X, Y, 520, 10, seed + 4) * 0.3
    grain = rings * 0.5 + fibres
    return pid, dist_edge, grain


def tex_wood_paint(res=1024, seed=91):
    """Vertical planks with peeling paint. 1 m tile. Returns normal, orm, {colour: albedo}."""
    X, Y = grid(res)
    px = 1.0 / res
    pid, de, grain = _wood_grain(X, Y, seed)
    gap = de < 0.0016
    bevel = sstep(0.0016, 0.006, de)
    wood = mix(rgb((0.36, 0.34, 0.31), X.shape), rgb((0.52, 0.49, 0.44), X.shape), sstep(-0.6, 0.8, grain))
    peel_n = fbm(X, Y, 5, 6, seed + 5) + grain * 0.18
    paint = peel_n > -0.32
    chalk = sstep(-0.3, 0.6, fbm(X, Y, 4, 4, seed + 6))
    h = bevel * 0.002 + grain * 0.00025 + np.where(paint, 0.0004, 0.0) - gap * 0.002
    h = h.astype(F)
    rough = np.where(paint, 0.62 + 0.15 * chalk, 0.86)
    ao = cavity_ao(h, px, (0.002, 0.006), 1.0)
    out = {}
    edge = sstep(-0.32, -0.27, peel_n) * (1 - sstep(-0.27, -0.2, peel_n))
    for name, pc in PAINTS.items():
        pcol = rgb(pc, X.shape)
        pcol = mix(pcol, pcol * 0.7 + 0.18, chalk * 0.35)
        pcol *= (0.94 + 0.06 * grain)[..., None]
        a = np.where(paint[..., None], pcol, wood)
        a = mix(a, a * 1.15 + 0.05, edge * 0.5)
        a = np.where(gap[..., None], a * 0.25, a)
        out[name] = a
    return height_to_normal(h, px, 1.0), orm(ao, rough), out, paint, gap, wood


def tex_wood_raw(res=1024, seed=101):
    """Weathered bare timber with checks and knots. Albedo variants: grey, dark (creosote), oak."""
    X, Y = grid(res)
    px = 1.0 / res
    pid, de, grain = _wood_grain(X, Y, seed, planks=5)
    cracks = sstep(0.93, 0.98, ridged(X, Y, 3, 2, seed + 7) * (0.6 + 0.4 * perlin(X, Y, 40, 2, seed + 8)))
    L = 0.58 + 0.11 * np.tanh(grain * 1.2) + 0.08 * fbm(X, Y, 6, 3, seed + 9)
    L = L * (1 - 0.7 * cracks)
    h = (grain * 0.0005 - cracks * 0.0015 + sstep(0.0, 0.004, de) * 0.0008).astype(F)
    ao = cavity_ao(h, px, (0.001, 0.004), 1.0)
    rough = 0.82 + 0.08 * fbm(X, Y, 12, 3, seed + 10)
    tints = {"grey": (0.62, 0.59, 0.55), "dark": (0.20, 0.15, 0.11), "oak": (0.58, 0.44, 0.30)}
    out = {k: (L[..., None] * np.array(v, F)).astype(F) for k, v in tints.items()}
    return height_to_normal(h, px, 1.0), orm(ao, rough), out


# ================================================================ METAL ETC
def tex_iron(res=1024, seed=111):
    """Black-painted iron flaking to rust, with worn bare spots."""
    X, Y = grid(res)
    px = 1.0 / res
    rust_n = fbm(X, Y, 6, 6, seed)
    rust = sstep(0.0, 0.25, rust_n)
    pits = sstep(0.55, 0.75, perlin(X, Y, 180, 180, seed + 1)) * rust
    bare = sstep(0.6, 0.75, fbm(X, Y, 12, 3, seed + 2)) * (1 - rust)
    paint_col = rgb((0.055, 0.055, 0.058), X.shape)
    rust_col = mix(rgb((0.36, 0.17, 0.07), X.shape), rgb((0.22, 0.11, 0.06), X.shape),
                   sstep(-0.5, 0.5, fbm(X, Y, 30, 3, seed + 3)))
    alb = mix(paint_col, rust_col, rust)
    alb = mix(alb, rgb((0.45, 0.45, 0.46), X.shape), bare)
    h = (rust * 0.0004 + pits * -0.0004 + fbm(X, Y, 60, 3, seed + 4) * 0.0001 * rust).astype(F)
    rough = 0.5 + 0.38 * rust - 0.15 * bare
    metal = bare * 0.9
    ao = cavity_ao(h, px, (0.001, 0.004), 1.0)
    return alb, height_to_normal(h, px, 1.0), orm(ao, rough, metal), h


def tex_clay(res=1024, seed=121):
    """Terracotta ridge tiles, weathered."""
    X, Y = grid(res)
    px = 1.0 / res
    col = mix(rgb((0.52, 0.28, 0.17), X.shape), rgb((0.44, 0.24, 0.16), X.shape), sstep(-0.4, 0.5, fbm(X, Y, 6, 5, seed)))
    col = mix(col, col * 0.5, sstep(0.0, 0.7, fbm(X, Y, 4, 4, seed + 1, aniso=(1, 3))) * 0.6)
    ly = lichen_mask(X, Y, seed + 2, 0.08, 10)
    lw = lichen_mask(X, Y, seed + 3, 0.08, 14)
    col = mix(col, rgb((0.70, 0.52, 0.16), X.shape), ly * 0.8)
    col = mix(col, rgb((0.68, 0.68, 0.64), X.shape), lw * 0.6)
    h = (fbm(X, Y, 20, 4, seed + 4) * 0.0006 + (ly + lw) * 0.0004).astype(F)
    rough = 0.8 + 0.1 * (ly + lw)
    ao = cavity_ao(h, px, (0.002, 0.006), 1.0)
    return col, height_to_normal(h, px, 1.0), orm(ao, rough), h


def tex_burlap(res=1024, seed=131):
    """Hessian sacking (0.5 m tile): plain weave, stains, damp."""
    X, Y = grid(res)
    px = 0.5 / res
    p = 85  # threads per tile across -> ~6 mm pitch
    wx = fbm(X, Y, 6, 3, seed) * 0.002
    tx = (X + wx) * p
    ty = (Y + fbm(X, Y, 6, 3, seed + 1) * 0.002) * p
    ix = np.floor(tx).astype(np.int32)
    iy = np.floor(ty).astype(np.int32)
    fx = tx - ix
    fy = ty - iy
    warp_prof = np.sin(np.pi * fx) ** 0.7
    weft_prof = np.sin(np.pi * fy) ** 0.7
    over = ((ix + iy) % 2) == 0
    h = np.where(over, warp_prof * (0.6 + 0.4 * np.sin(np.pi * fy)), weft_prof * (0.6 + 0.4 * np.sin(np.pi * fx)))
    h = h * 0.0012 + perlin(X, Y, 340, 340, seed + 2) * 0.0002
    col = mix(rgb((0.33, 0.30, 0.24), X.shape), rgb((0.42, 0.38, 0.30), X.shape), sstep(0.2, 1.0, h / 0.0012))
    col *= (0.9 + 0.12 * perlin(X, Y, 85, 85, seed + 3))[..., None]
    stain = sstep(0.1, 0.6, fbm(X, Y, 4, 5, seed + 4))
    col = mix(col, col * 0.55, stain * 0.6)
    h = h.astype(F)
    rough = 0.92 - stain * 0.1
    ao = cavity_ao(h, px, (0.001, 0.003), 1.4)
    return col, height_to_normal(h, px, 1.0), orm(ao, rough), h


def tex_stripes(wood_paint_set, res=1024):
    """Schilderhaus diagonal black-white-red stripes over the planked wood pattern."""
    nrm, o, _, paint, gap, wood = wood_paint_set
    X, Y = grid(res)
    band = np.floor(((X + (1.0 - Y)) % 1.0) * 3).astype(np.int32)
    cols = np.array([(0.035, 0.035, 0.035), (0.80, 0.79, 0.74), (0.55, 0.06, 0.05)], F)
    pc = cols[band] * (0.9 + 0.12 * fbm(X, Y, 6, 3, 171))[..., None]
    alb = np.where(paint[..., None], pc, wood)
    alb = np.where(gap[..., None], alb * 0.25, alb)
    return alb, nrm, o


def tex_paper(res=1024, seed=141):
    X, Y = grid(res)
    px = 1.0 / res
    col = mix(rgb((0.80, 0.77, 0.68), X.shape), rgb((0.70, 0.66, 0.55), X.shape), sstep(-0.2, 0.7, fbm(X, Y, 3, 5, seed)))
    stains = sstep(0.4, 0.7, fbm(X, Y, 5, 5, seed + 1))
    col = mix(col, rgb((0.55, 0.48, 0.36), X.shape), stains * 0.35)
    h = (fbm(X, Y, 4, 4, seed + 2) * 0.0015 + perlin(X, Y, 300, 300, seed + 3) * 0.00005).astype(F)
    rough = 0.88 + 0.0 * h
    ao = np.ones_like(h)
    return col, height_to_normal(h, px, 1.0), orm(ao, rough), h


def tex_decal_streak(w=512, hgt=1024, seed=151):
    """Grime/rain streaks running down from a sill. 0.5 m wide x 1 m tall, RGBA."""
    X, Y = grid(hgt, w)
    n = fbm(X * 1.0, Y, 6, 5, seed, aniso=(1, 0.15))
    streaks = sstep(-0.05, 0.45, perlin(X, Y * 0.0 + 0.5, 18, 1, seed + 1) * 0.7 + n * 0.5)
    fade = (1.0 - Y) ** 0.0 * sstep(1.0, 0.25, Y) * sstep(0.0, 0.04, Y)
    side = sstep(0.0, 0.18, X) * sstep(1.0, 0.82, X)
    alpha = np.clip(streaks * fade * side * (0.75 + 0.25 * perlin(X, Y, 40, 40, seed + 2)), 0, 1) * 0.85
    col = mix(rgb((0.035, 0.033, 0.028), X.shape), rgb((0.05, 0.07, 0.035), X.shape), sstep(0.0, 0.7, n))
    return col, (alpha * 0.8).astype(F)


def tex_decal_damp(w=1024, hgt=512, seed=161):
    """Rising damp along a wall base: 2 m wide (tiles horizontally) x 1 m tall, RGBA.
    Bottom of the image = ground."""
    X, Y = grid(hgt, w)
    up = 1.0 - Y                       # 0 at ground, 1 at 1 m
    line = 0.45 + 0.25 * fbm(X, np.zeros_like(X) + 0.3, 3, 4, seed) + 0.08 * fbm(X, Y, 10, 3, seed + 1)
    a = sstep(line, line - 0.25, up)
    tide = sstep(line - 0.04, line, up) * sstep(line + 0.03, line, up)
    alpha = np.clip(a * 0.78 + tide * 0.35, 0, 1) * (0.85 + 0.15 * fbm(X, Y, 20, 3, seed + 2))
    col = mix(rgb((0.06, 0.06, 0.045), X.shape), rgb((0.05, 0.075, 0.035), X.shape), sstep(0.3, 0.0, up))
    col = mix(col, rgb((0.45, 0.43, 0.37), X.shape), tide * 0.6)   # salt tide line
    return col, (np.clip(alpha, 0, 1) * 0.88).astype(F)


# ================================================================== DRIVER
GROUND = {
    "cobble": tex_cobble,
    "mud": tex_mud,
    "grass_winter": tex_grass_winter,
    "gravel": tex_gravel,
}
BUILD = ["rubble", "granite", "slate", "render", "wood_paint", "wood_raw", "iron", "clay",
         "burlap", "stripes", "paper", "decal_streak", "decal_damp"]


def _exists(folder, name, suffixes=("albedo", "normal", "orm")):
    return all(os.path.exists(os.path.join(folder, f"{name}_{s}.png")) for s in suffixes)


def ensure(names=None, force=False, log=print):
    names = names or (list(GROUND) + BUILD)
    cache = {}

    def get_rubble():
        if "rubble" not in cache:
            cache["rubble"] = tex_rubble()
        return cache["rubble"]

    def get_wood_paint():
        if "wood_paint" not in cache:
            cache["wood_paint"] = tex_wood_paint()
        return cache["wood_paint"]

    for n in names:
        t0 = time.time()
        if n in GROUND:
            if force or not _exists(GROUND_DIR, n):
                a, nm, o, _ = GROUND[n]()
                save_set(GROUND_DIR, n, a, nm, o)
                if n == "cobble":   # street mesh also embeds the setts
                    save_set(TEX_DIR, n, a, nm, o)
            elif n == "cobble" and not _exists(TEX_DIR, n):
                import shutil
                for s in ("albedo", "normal", "orm"):
                    shutil.copy(os.path.join(GROUND_DIR, f"cobble_{s}.png"), os.path.join(TEX_DIR, f"cobble_{s}.png"))
        elif n == "rubble":
            if force or not _exists(TEX_DIR, n):
                a, nm, o, _ = get_rubble()
                save_set(TEX_DIR, n, a, nm, o)
        elif n == "render":
            if force or not _exists(TEX_DIR, n):
                a, nm, o, _ = tex_render(get_rubble())
                save_set(TEX_DIR, n, a, nm, o)
        elif n == "wood_paint":
            if force or not _exists(TEX_DIR, "wood_paint", ("normal", "orm")):
                nm, o, cols = get_wood_paint()[:3]
                write_png(os.path.join(TEX_DIR, "wood_paint_normal.png"), nm)
                write_png(os.path.join(TEX_DIR, "wood_paint_orm.png"), o)
                for c, a in cols.items():
                    write_png(os.path.join(TEX_DIR, f"wood_paint_{c}_albedo.png"), a)
        elif n == "wood_raw":
            if force or not _exists(TEX_DIR, "wood_raw", ("normal", "orm")):
                nm, o, cols = tex_wood_raw()
                write_png(os.path.join(TEX_DIR, "wood_raw_normal.png"), nm)
                write_png(os.path.join(TEX_DIR, "wood_raw_orm.png"), o)
                for c, a in cols.items():
                    write_png(os.path.join(TEX_DIR, f"wood_raw_{c}_albedo.png"), a)
        elif n == "stripes":
            if force or not _exists(TEX_DIR, n):
                a, nm, o = tex_stripes(get_wood_paint())
                save_set(TEX_DIR, n, a, nm, o)
        elif n in ("decal_streak", "decal_damp"):
            p = os.path.join(TEX_DIR, f"{n}_albedo.png")
            if force or not os.path.exists(p):
                col, alpha = (tex_decal_streak if n == "decal_streak" else tex_decal_damp)()
                write_png(p, np.dstack([col, alpha]))
        else:
            fn = {"granite": tex_granite, "slate": tex_slate, "iron": tex_iron, "clay": tex_clay,
                  "burlap": tex_burlap, "paper": tex_paper}[n]
            if force or not _exists(TEX_DIR, n):
                a, nm, o, _ = fn()
                save_set(TEX_DIR, n, a, nm, o)
        log(f"[tex] {n}: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ensure(args or None, force="--force" in sys.argv)
