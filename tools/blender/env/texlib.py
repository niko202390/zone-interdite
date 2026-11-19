"""Tileable procedural texture toolkit (numpy only).

All generators work on normalised tile coordinates (x, y) in [0, 1) and
wrap seamlessly at the edges. Image row 0 is the TOP of the image
(v = 1). Height maps are in metres.
"""
import os
import struct
import zlib

import numpy as np

F = np.float32


# --------------------------------------------------------------------------- io
def write_png(path, arr):
    """Write HxW (grey), HxWx3 (RGB) or HxWx4 (RGBA) array; floats are 0..1."""
    if arr.dtype != np.uint8:
        arr = (np.clip(arr, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    if arr.ndim == 2:
        arr = arr[:, :, None]
    h, w, c = arr.shape
    ctype = {1: 0, 3: 2, 4: 6}[c]
    a = arr.reshape(h, w * c).astype(np.int16)
    sub = a.copy()
    sub[:, c:] = (a[:, c:] - a[:, :-c]) % 256  # PNG "Sub" filter
    raw = np.empty((h, w * c + 1), np.uint8)
    raw[:, 0] = 1
    raw[:, 1:] = sub.astype(np.uint8)
    comp = zlib.compress(raw.tobytes(), 6)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    data = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def save_set(folder, name, albedo, normal, orm, alpha=None):
    if alpha is not None:
        albedo = np.dstack([albedo, alpha])
    write_png(os.path.join(folder, f"{name}_albedo.png"), albedo)
    write_png(os.path.join(folder, f"{name}_normal.png"), normal)
    write_png(os.path.join(folder, f"{name}_orm.png"), orm)


# ----------------------------------------------------------------------- grids
def grid(h, w=None):
    w = w or h
    x = (np.arange(w, dtype=F) + 0.5) / w
    y = (np.arange(h, dtype=F) + 0.5) / h
    X, Y = np.meshgrid(x, y)
    return X, Y


# ----------------------------------------------------------------------- noise
def _fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def perlin(x, y, px, py, seed):
    """Periodic gradient noise, approx [-1, 1]. px/py = lattice cells per tile."""
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 2 * np.pi, (py, px)).astype(F)
    gx, gy = np.cos(ang), np.sin(ang)
    X = (x % 1.0) * px
    Y = (y % 1.0) * py
    x0 = np.floor(X).astype(np.int32)
    y0 = np.floor(Y).astype(np.int32)
    fx = (X - x0).astype(F)
    fy = (Y - y0).astype(F)
    x0 %= px
    y0 %= py
    x1 = (x0 + 1) % px
    y1 = (y0 + 1) % py
    n00 = gx[y0, x0] * fx + gy[y0, x0] * fy
    n10 = gx[y0, x1] * (fx - 1) + gy[y0, x1] * fy
    n01 = gx[y1, x0] * fx + gy[y1, x0] * (fy - 1)
    n11 = gx[y1, x1] * (fx - 1) + gy[y1, x1] * (fy - 1)
    u = _fade(fx)
    v = _fade(fy)
    a = n00 + u * (n10 - n00)
    b = n01 + u * (n11 - n01)
    return (a + v * (b - a)) * F(1.41)


def fbm(x, y, period, octaves, seed, gain=0.5, lac=2, aniso=(1, 1)):
    """Fractal sum, normalised to approx [-1, 1]."""
    total = np.zeros_like(x, dtype=F)
    amp, norm = 1.0, 0.0
    p = period
    for o in range(octaves):
        total += F(amp) * perlin(x, y, max(1, int(p * aniso[0])), max(1, int(p * aniso[1])), seed + o * 101)
        norm += amp
        amp *= gain
        p *= lac
    return total / F(norm)


def ridged(x, y, period, octaves, seed, gain=0.5):
    total = np.zeros_like(x, dtype=F)
    amp, norm, p = 1.0, 0.0, period
    for o in range(octaves):
        total += F(amp) * (1.0 - np.abs(perlin(x, y, p, p, seed + o * 77)))
        norm += amp
        amp *= gain
        p *= 2
    return total / F(norm)


def voronoi(x, y, nx, ny, seed, jitter=0.85):
    """Periodic Worley noise in tile units. Returns F1, F2, cell id, (cx, cy) of nearest point."""
    rng = np.random.default_rng(seed)
    pts = rng.uniform(0.5 - jitter / 2, 0.5 + jitter / 2, (ny, nx, 2)).astype(F)
    X = (x % 1.0) * nx
    Y = (y % 1.0) * ny
    cx = np.floor(X).astype(np.int32)
    cy = np.floor(Y).astype(np.int32)
    f1 = np.full(x.shape, 1e9, F)
    f2 = np.full(x.shape, 1e9, F)
    cid = np.zeros(x.shape, np.int32)
    ncx = np.zeros(x.shape, F)
    ncy = np.zeros(x.shape, F)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ix = cx + dx
            iy = cy + dy
            wx = ix % nx
            wy = iy % ny
            pxx = ix + pts[wy, wx, 0]
            pyy = iy + pts[wy, wx, 1]
            ddx = (pxx - X) / nx
            ddy = (pyy - Y) / ny
            d = np.sqrt(ddx * ddx + ddy * ddy)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            cid = np.where(closer, wy * nx + wx, cid)
            ncx = np.where(closer, pxx / nx, ncx)
            ncy = np.where(closer, pyy / ny, ncy)
            f1 = np.where(closer, d, f1)
    return f1, f2, cid, ncx, ncy


def cell_rand(cid, seed, n=1):
    """Deterministic per-cell random values in [0,1)."""
    rng = np.random.default_rng(seed)
    table = rng.random((int(cid.max()) + 1, n)).astype(F)
    out = table[cid]
    return out[..., 0] if n == 1 else out


# --------------------------------------------------------------------- filters
def blur(img, sigma_px):
    """Tileable gaussian blur via FFT (2D arrays or HxWxC)."""
    if img.ndim == 3:
        return np.dstack([blur(img[..., i], sigma_px) for i in range(img.shape[2])])
    h, w = img.shape
    ky = np.fft.fftfreq(h)[:, None]
    kx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi ** 2) * (sigma_px ** 2) * (kx ** 2 + ky ** 2))
    return np.fft.irfft2(np.fft.rfft2(img) * g, s=(h, w)).astype(F)


def height_to_normal(h, px_m, strength=1.0):
    """OpenGL-convention (+Y up) tangent-space normal map from height in metres."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px_m)
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * px_m)
    nx = -dx * strength
    ny = dy * strength          # image rows go down; v goes up
    nz = np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([nx * inv, ny * inv, nz * inv]) * 0.5 + 0.5


def cavity_ao(h, px_m, radii_m=(0.005, 0.02, 0.06), strength=1.0):
    """Cheap ambient occlusion: how far a texel sits below its blurred neighbourhood."""
    ao = np.zeros_like(h)
    for r in radii_m:
        d = blur(h, max(1.0, r / px_m)) - h
        ao += np.clip(d / (r * 0.6), 0, 1)
    ao = 1.0 - np.clip(ao / len(radii_m) * strength, 0, 0.85)
    return ao.astype(F)


# ---------------------------------------------------------------------- colour
def mix(a, b, t):
    t = t[..., None] if (np.ndim(t) == np.ndim(a) - 1) else t
    return a + (b - a) * t


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def rgb(c, shape):
    return np.broadcast_to(np.array(c, F), shape + (3,)).copy()


def palette_pick(cid_rand, colors, weights=None):
    """Pick a colour per cell from a palette using a [0,1) per-cell random."""
    colors = np.array(colors, F)
    if weights is None:
        weights = np.ones(len(colors))
    cw = np.cumsum(weights) / np.sum(weights)
    idx = np.searchsorted(cw, cid_rand.ravel()).reshape(cid_rand.shape)
    return colors[np.clip(idx, 0, len(colors) - 1)]


def orm(ao, rough, metal=None):
    if metal is None:
        metal = np.zeros_like(rough)
    return np.dstack([ao, rough, metal])


def lichen_mask(x, y, seed, density=0.3, scale=14):
    """Lichen colonies: small irregular crusts, clustered into patches."""
    f1, _, cid, _, _ = voronoi(x, y, scale, scale, seed, jitter=0.95)
    rr = cell_rand(cid, seed + 1, 2)
    radius = (0.004 + rr[..., 0] * 0.016) * (14.0 / scale)
    clust = sstep(0.0, 0.6, fbm(x, y, 3, 3, seed + 5))
    present = rr[..., 1] < density * clust * 2.0
    edge = fbm(x, y, 48, 3, seed + 7) * radius * 0.9
    m = sstep(radius + edge, radius * 0.4 + edge, f1) * present
    m = m * (0.6 + 0.4 * sstep(-0.3, 0.3, perlin(x, y, 260, 260, seed + 9)))
    return m.astype(F)
