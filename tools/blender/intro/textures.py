"""Procedural paper-fibre texture (pure numpy, tileable, seeded)."""
import math
import numpy as np


def _blur_fft(img, sigma):
    n = img.shape[0]
    f = np.fft.fftfreq(n)
    g = np.exp(-2 * (math.pi * sigma) ** 2 * (f[:, None] ** 2 + f[None, :] ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * g))


def fibre_texture(N=2048, tile=0.03, seed=11):
    """Returns (N,N,4) float32: R height, G tint, B formation, A 1.  One tile = `tile` metres."""
    rng = np.random.default_rng(seed)
    ppm = N / tile
    layers = []
    for count, (lmin, lmax), wsig, gain in ((14000, (0.0004, 0.0026), 0.9, 1.0),
                                             (5000, (0.0008, 0.0035), 1.7, 0.7),
                                             (30000, (0.00008, 0.0004), 0.6, 0.6)):
        h = np.zeros((N, N), np.float64)
        tint = np.zeros((N, N), np.float64)
        L = rng.uniform(lmin, lmax, count) * ppm
        start = rng.uniform(0, N, (count, 2))
        ang = rng.uniform(0, 2 * math.pi, count)
        curv = rng.normal(0, 0.012, count)
        bright = rng.uniform(0.4, 1.0, count)
        tn = rng.normal(0, 1, count)
        xs, ys, ws, ts = [], [], [], []
        for i in range(count):
            n = max(2, int(L[i] / 0.7))
            k = np.arange(n)
            a = ang[i] + curv[i] * k + 0.05 * np.sin(k * 0.05 + i)
            dx = np.cumsum(np.cos(a)) * 0.7
            dy = np.cumsum(np.sin(a)) * 0.7
            xs.append(start[i, 0] + dx)
            ys.append(start[i, 1] + dy)
            taper = np.sin(np.linspace(0.15, math.pi - 0.15, n)) ** 0.5
            ws.append(bright[i] * taper)
            ts.append(np.full(n, tn[i]) * taper)
        x = np.concatenate(xs); y = np.concatenate(ys)
        w = np.concatenate(ws); t = np.concatenate(ts)
        x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
        fx = x - x0; fy = y - y0
        for ox, oy, wt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                           (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(h, ((y0 + oy) % N, (x0 + ox) % N), w * wt)
            np.add.at(tint, ((y0 + oy) % N, (x0 + ox) % N), t * wt)
        layers.append((_blur_fft(h, wsig) * gain, _blur_fft(tint, wsig * 1.5) * gain))
    hsum = sum(l[0] for l in layers)
    tsum = sum(l[1] for l in layers)
    hgt = 1 - np.exp(-hsum * 1.2)
    hgt = (hgt - hgt.min()) / (hgt.max() - hgt.min())
    tsum = 0.5 + 0.5 * tsum / (np.abs(tsum).max() + 1e-9) * 2.0
    form = _blur_fft(rng.normal(0, 1, (N, N)), 40.0)
    form = (form - form.min()) / (form.max() - form.min())
    out = np.stack([hgt, np.clip(tsum, 0, 1), form, np.ones_like(hgt)], -1).astype(np.float32)
    return out
