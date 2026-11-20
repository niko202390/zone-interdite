"""Hand-printed broad-nib lettering for the intro film (pure numpy, no bpy).

Builds the stroke paths of "ZONE INTERDITE" as a field agent would print it,
times the nib along them, and rasterises an ink map:
  R = ink coverage (antialiased), G = blurred coverage (wet bead / feather),
  B = ink amount (pooling), A = time in seconds the nib wet that pixel.
All randomness is seeded.
"""
import math
import numpy as np

TEXT = "ZONE INTERDITE"
CAP_H = 0.016          # cap height, metres
GAP = 0.30             # letter gap, cap heights
SPACE = 0.62           # word space, cap heights
# A pointed steel nib under firm pressure, not a calligrapher's broad edge: secret writing was done with an
# ordinary pen. A little thick-thin remains from the nib spreading on the downstrokes.
NIB_W = 0.00115        # nib edge width, metres
NIB_T = 0.00042        # nib edge thickness, metres
NIB_ANGLE = math.radians(32.0)
BASELINE_Y = 0.024     # baseline in paper coords (paper centred on origin)
X_OFF = 0.0
RES = 20000            # ink map px per metre (20 px/mm)
STEP = 0.00010         # uniform resample step for timing, metres


def _line(a, b, step=0.01):
    a = np.asarray(a, float); b = np.asarray(b, float)
    n = max(2, int(np.linalg.norm(b - a) / step) + 1)
    t = np.linspace(0.0, 1.0, n)[:, None]
    return a + (b - a) * t


def _arc(c, rx, ry, a0, a1, step=0.01):
    n = max(3, int(abs(math.radians(a1 - a0)) * max(rx, ry) / step) + 1)
    a = np.radians(np.linspace(a0, a1, n))
    return np.stack([c[0] + rx * np.cos(a), c[1] + ry * np.sin(a)], 1)


def _cat(*parts):
    out = [parts[0]]
    for p in parts[1:]:
        out.append(p[1:])
    return np.concatenate(out)


def glyph(ch):
    """Return (width, [strokes]) in cap-height units, stroke order as written."""
    if ch == 'Z':
        # Barred, as many continental hands wrote it; the bar goes in last.
        return 0.70, [_cat(_line((0.03, 1), (0.68, 1)), _line((0.68, 1), (0.0, 0.0)),
                           _line((0.0, 0.0), (0.72, 0.0))), _line((0.17, 0.5), (0.55, 0.52))]
    if ch == 'O':
        return 0.80, [_arc((0.40, 0.5), 0.40, 0.5, 100, 100 + 372)]
    if ch == 'N':
        return 0.66, [_cat(_line((0, 0), (0, 1)), _line((0, 1), (0.66, 0)), _line((0.66, 0), (0.66, 1)))]
    if ch == 'E':
        # Draughtsman's proportions: the bottom bar longest, the middle bar just above centre.
        return 0.62, [_cat(_line((0.55, 1), (0, 1)), _line((0, 1), (0, 0)), _line((0, 0), (0.64, 0))),
                      _line((0.0, 0.56), (0.44, 0.57))]
    if ch == 'I':
        return 0.02, [_line((0.01, 1), (0.01, 0))]
    if ch == 'T':
        return 0.72, [_line((0, 1), (0.72, 1)), _line((0.36, 1), (0.36, 0))]
    if ch == 'R':
        return 0.64, [_line((0, 0), (0, 1)),
                      _cat(_line((0, 1), (0.33, 1)), _arc((0.33, 0.75), 0.27, 0.25, 90, -90),
                           _line((0.33, 0.5), (0.03, 0.5)), _line((0.03, 0.5), (0.66, 0.0)))]
    if ch == 'D':
        return 0.68, [_line((0, 0), (0, 1)),
                      _cat(_line((0, 1), (0.24, 1)), _arc((0.24, 0.5), 0.43, 0.5, 90, -90),
                           _line((0.24, 0), (0, 0)))]
    raise ValueError(ch)


def _resample(p, step):
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(2, int(s[-1] / step) + 1)
    si = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(si, s, p[:, 0]), np.interp(si, s, p[:, 1])], 1)


def _gauss1d(sigma):
    r = max(1, int(3 * sigma))
    x = np.arange(-r, r + 1)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    return k / k.sum()


def _smooth(a, sigma):
    k = _gauss1d(sigma)
    r = len(k) // 2
    pad = np.pad(a, (r, r), mode='edge')
    return np.convolve(pad, k, mode='valid')


# How human the hand is: a practised letterer, quick and confident, but not a machine.
HAND = {
    "slant_sd": 0.025, "scale_sd": 0.035, "dy_sd": 0.02, "rot_sd": 0.022, "gap_sd": 0.045,
    "bow_sd": 0.018,       # straight strokes bow slightly (fraction of stroke length)
    "end_sd": 0.028,       # strokes stop short or overshoot their joins (cap heights)
    "drift": 0.009,        # slow wander of the whole stroke, which moves corners about (cap heights)
    "tick_p": 0.4,        # chance a stroke starts with a small nib entry tick
    "wob": 0.0035,         # fine tremor (cap heights)
}


def _humanise(p, rng):
    """One stroke, in cap-height units: bow, uneven ends, a drifting path, and sometimes an entry tick."""
    p = _resample(p, 0.004)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    L = max(s[-1], 1e-6)
    d = np.gradient(p, axis=0)
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
    nrm = np.stack([-d[:, 1], d[:, 0]], 1)
    # Bow: the hand pulls a straight line into a very shallow curve.
    bow = rng.normal(0, HAND["bow_sd"]) * L
    p = p + nrm * (bow * np.sin(math.pi * s / L))[:, None]
    # Slow drift in x and y: corners land a little off where they were aimed.
    ph = rng.uniform(0, 2 * math.pi, 4)
    lam = rng.uniform(0.9, 1.5)
    p = p + np.stack([np.sin(2 * math.pi * s / lam + ph[0]), np.sin(2 * math.pi * s / lam + ph[2])], 1) * HAND["drift"]
    # Ends: overshoot or stop short along the tangent.
    t0 = p[1] - p[0]; t0 /= np.linalg.norm(t0) + 1e-12
    t1 = p[-1] - p[-2]; t1 /= np.linalg.norm(t1) + 1e-12
    e0 = rng.normal(0, HAND["end_sd"])
    e1 = rng.normal(0.01, HAND["end_sd"])
    head = [p[0] - t0 * e0] if e0 > 0 else []
    tail = [p[-1] + t1 * e1] if e1 > 0 else []
    if e0 < 0:
        p = p[s > -e0] if (s > -e0).sum() > 3 else p
    if e1 < 0:
        p = p[s[:len(p)] < L + e1] if len(p) > 3 and (s[:len(p)] < L + e1).sum() > 3 else p
    parts = [np.array(head)] if head else []
    parts.append(p)
    if tail:
        parts.append(np.array(tail))
    p = np.concatenate(parts)
    # The nib lands with a small tick before it moves off along the stroke.
    if rng.random() < HAND["tick_p"]:
        n0 = np.array([-t0[1], t0[0]])
        side = 1.0 if rng.random() < 0.5 else -1.0
        tick = p[0] - t0 * rng.uniform(0.008, 0.02) + n0 * side * rng.uniform(0.01, 0.022)
        p = np.concatenate([tick[None, :], p])
    return p


def build_strokes(seed=1944):
    """Return list of (N,2) arrays in metres (paper coords), in writing order."""
    rng = np.random.default_rng(seed)
    raw = []
    x = 0.0
    for ch in TEXT:
        if ch == ' ':
            x += SPACE
            continue
        w, sts = glyph(ch)
        slant = 0.12 + rng.normal(0, HAND["slant_sd"])   # a quick practised hand leans about 7 degrees
        sc = 1.0 + rng.normal(0, HAND["scale_sd"])
        dy = rng.normal(0, HAND["dy_sd"])
        rot = rng.normal(0, HAND["rot_sd"])
        cr, sr = math.cos(rot), math.sin(rot)
        for s in sts:
            p = _humanise(s.copy(), rng)
            p[:, 0] += p[:, 1] * slant
            p -= (w / 2, 0.5)
            p = np.stack([p[:, 0] * cr - p[:, 1] * sr, p[:, 0] * sr + p[:, 1] * cr], 1)
            p = p * sc + (w / 2, 0.5)
            p += (x, dy)
            p = _resample(p, 0.004)
            # hand wobble along the stroke normal
            d = np.gradient(p, axis=0)
            d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
            nrm = np.stack([-d[:, 1], d[:, 0]], 1)
            sl = np.arange(len(p)) * 0.004
            ph = rng.uniform(0, 2 * math.pi, 2)
            wob = HAND["wob"] / 0.0035 * 0.0035 * np.sin(2 * math.pi * sl / 0.9 + ph[0]) + 0.0015 * np.sin(2 * math.pi * sl / 0.31 + ph[1])
            p += nrm * wob[:, None]
            # slight corner rounding
            p[:, 0] = _smooth(p[:, 0], 2.0)
            p[:, 1] = _smooth(p[:, 1], 2.0)
            raw.append(p)
        x += w * sc + GAP + rng.normal(0, HAND["gap_sd"])
    width = x - GAP
    out = []
    for p in raw:
        q = p.copy()
        u = q[:, 0] / width
        q[:, 1] += 0.035 * u - 0.025 * np.sin(math.pi * u)   # gentle uphill drift and sag
        q = q * CAP_H
        q[:, 0] += X_OFF - width * CAP_H / 2
        q[:, 1] += BASELINE_Y
        out.append(_resample(q, STEP))
    return out


def time_strokes(strokes, t0, t1):
    """Assign a time to every sample. Returns (times list, speeds list)."""
    V = 1.0
    times, speeds = [], []
    t = 0.0
    for i, s in enumerate(strokes):
        d = np.diff(s, axis=0)
        seg = np.linalg.norm(d, axis=1)
        sl = np.concatenate([[0.0], np.cumsum(seg)])
        L = sl[-1]
        ang = np.arctan2(d[:, 1], d[:, 0])
        turn = np.abs((np.diff(ang) + math.pi) % (2 * math.pi) - math.pi)
        turn = np.concatenate([[0.0], turn, [0.0]])
        tsm = _smooth(turn, 8.0)
        sp = 1.0 / (1.0 + 45.0 * tsm)
        ramp = 0.0018
        sp *= np.clip(0.25 + sl / ramp, 0, 1) * np.clip(0.35 + (L - sl) / ramp, 0, 1)
        dt = seg / (V * 0.5 * (sp[1:] + sp[:-1]))
        ts = t + np.concatenate([[0.0], np.cumsum(dt)])
        times.append(ts)
        speeds.append(sp)
        t = ts[-1]
        if i + 1 < len(strokes):
            dist = np.linalg.norm(strokes[i + 1][0] - s[-1])
            t += 0.0035 + dist / (2.2 * V)
    total = t
    times = [t0 + ts / total * (t1 - t0) for ts in times]
    return times, speeds


def lift_gaps(strokes, times):
    gaps = []
    for i in range(len(strokes) - 1):
        gaps.append((times[i][-1], times[i + 1][0], strokes[i][-1], strokes[i + 1][0]))
    return gaps


def pen_tip(t, strokes, times, t_enter=0.0, t_exit=None):
    """Nib tip position (x, y, z) at time t, paper coords; z = lift above paper."""
    first, last = strokes[0][0], strokes[-1][-1]
    ts0, ts1 = times[0][0], times[-1][-1]
    if t <= ts0:
        a = np.clip((t - t_enter) / max(ts0 - t_enter, 1e-6), 0, 1)
        e = 1 - (1 - a) ** 3
        start = first + np.array([0.022, -0.010])
        p = start + (first - start) * e
        return float(p[0]), float(p[1]), 0.016 * (1 - e) ** 1.5
    if t >= ts1:
        a = min(1.0, (t - ts1) / 0.45)
        e = a * a * (3 - 2 * a)
        p = last + np.array([0.020, -0.012]) * e
        return float(p[0]), float(p[1]), 0.014 * e ** 1.2
    for i, ts in enumerate(times):
        if ts[0] <= t <= ts[-1]:
            s = strokes[i]
            return float(np.interp(t, ts, s[:, 0])), float(np.interp(t, ts, s[:, 1])), 0.0
        if i + 1 < len(times) and ts[-1] < t < times[i + 1][0]:
            a = (t - ts[-1]) / (times[i + 1][0] - ts[-1])
            e = a * a * (3 - 2 * a)
            p0, p1 = strokes[i][-1], strokes[i + 1][0]
            p = p0 + (p1 - p0) * e
            h = min(0.004, 0.0012 + 0.25 * np.linalg.norm(p1 - p0))
            return float(p[0]), float(p[1]), h * math.sin(math.pi * a)
    return float(last[0]), float(last[1]), 0.0


def rasterize(strokes, times, speeds, seed=7):
    rng = np.random.default_rng(seed)
    allp = np.concatenate(strokes)
    margin = 0.003
    x0, y0 = allp.min(0) - margin
    x1, y1 = allp.max(0) + margin
    W = int((x1 - x0) * RES) + 1
    H = int((y1 - y0) * RES) + 1
    mask = np.zeros((H, W), np.float32)
    amt = np.zeros((H, W), np.float32)
    tmap = np.full((H, W), 1000.0, np.float32)
    ua = np.array([math.cos(NIB_ANGLE), math.sin(NIB_ANGLE)])
    va = np.array([-ua[1], ua[0]])
    ah = NIB_W / 2 * RES
    bh = NIB_T / 2 * RES
    R = int(ah + 3)
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    for s, ts, sp in zip(strokes, times, speeds):
        seg = np.linalg.norm(np.diff(s, axis=0), axis=1)
        sl = np.concatenate([[0.0], np.cumsum(seg)])
        L = sl[-1]
        n = max(2, int(L * RES / 0.5))
        si = np.linspace(0, L, n)
        px = (np.interp(si, sl, s[:, 0]) - x0) * RES
        py = (np.interp(si, sl, s[:, 1]) - y0) * RES
        pt = np.interp(si, sl, ts)
        psp = np.interp(si, sl, sp)
        ph = rng.uniform(0, 6.28, 3)
        q = (0.72 + 0.38 * np.exp(-si / 0.0008) + 0.40 * np.exp(-(L - si) / 0.0010)
             + 0.22 * (1 - psp) + 0.08 * np.sin(si / 0.003 + ph[0]) + 0.06 * np.sin(si / 0.0011 + ph[1]))
        # pressure: nib edge a touch narrower as it lands
        wf = 0.82 + 0.18 * np.clip(si / 0.0012, 0, 1)
        for k in range(n):
            ix, iy = int(round(px[k])), int(round(py[k]))
            if ix - R < 0 or iy - R < 0 or ix + R + 1 > W or iy + R + 1 > H:
                continue
            dx = xx - (px[k] - ix)
            dy = yy - (py[k] - iy)
            du = np.abs(dx * ua[0] + dy * ua[1])
            dv = np.abs(dx * va[0] + dy * va[1])
            a = ah * wf[k]
            qx = du - (a - bh)
            qy = dv
            sd = np.sqrt(np.maximum(qx, 0) ** 2 + qy ** 2) - bh
            cov = np.clip(0.5 - sd, 0, 1)
            sl_ = (slice(iy - R, iy + R + 1), slice(ix - R, ix + R + 1))
            np.maximum(mask[sl_], cov, out=mask[sl_])
            np.maximum(amt[sl_], cov * q[k], out=amt[sl_])
            tt = tmap[sl_]
            np.minimum(tt, np.where(cov > 0.02, pt[k], 1000.0), out=tt)
    # dilate the time map so bilinear filtering at edges stays sane
    for _ in range(8):
        t = tmap
        m = np.minimum.reduce([t, np.roll(t, 1, 0), np.roll(t, -1, 0), np.roll(t, 1, 1), np.roll(t, -1, 1)])
        tmap = np.where(t > 999, m, t)
    blur = mask.copy()
    k = _gauss1d(3.0)
    r = len(k) // 2
    blur = np.apply_along_axis(lambda a: np.convolve(np.pad(a, r, mode='edge'), k, 'valid'), 1, blur)
    blur = np.apply_along_axis(lambda a: np.convolve(np.pad(a, r, mode='edge'), k, 'valid'), 0, blur)
    rgba = np.stack([mask, blur.astype(np.float32), amt, tmap], -1)
    return rgba, (float(x0), float(y0), float(x1 - x0), float(y1 - y0))


if __name__ == '__main__':
    st = build_strokes()
    tm, sp = time_strokes(st, 0.4, 4.2)
    print(len(st), 'strokes', sum(len(s) for s in st), 'samples')
    img, box = rasterize(st, tm, sp)
    print(img.shape, box)
