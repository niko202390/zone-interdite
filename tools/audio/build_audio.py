#!/usr/bin/env python3
"""
Zone Interdite procedural audio builder (M1 "First Night").

Everything here is synthesized from scratch with numpy. No samples, no downloads.
Run it with Blender's bundled Python, which ships numpy:

  "C:/Program Files/Blender Foundation/Blender 5.3/5.3/python/bin/python.exe" \
      tools/audio/build_audio.py [--only GLOB] [--no-previews]

Outputs:  game/assets/audio/<category>/*.wav  and  game/assets/audio/manifest.json
Previews: tools/audio/previews/*.png  (spectrogram montages, git-ignored)

Every random generator is seeded from its output file name, so rebuilds are
byte-identical. Loops are made periodic by construction: circular FFT noise,
circular filtering/convolution, events folded around the loop point, and
integer cycle counts for oscillators. Each loop also carries a WAV 'smpl'
chunk that Godot's importer reads ("Detect from WAV").
"""
import argparse
import fnmatch
import json
import math
import struct
import sys
import time
import zlib
from pathlib import Path

import numpy as np

SR = 44100
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "game" / "assets" / "audio"
PREV = ROOT / "tools" / "audio" / "previews"
TAU = 2.0 * np.pi


# =============================================================================
# Basics
# =============================================================================

def N(sec):
    return int(round(sec * SR))


def tax(n):
    return np.arange(n) / SR


def db(x):
    return 10.0 ** (x / 20.0)


def rng_for(name, k=0):
    return np.random.default_rng(zlib.crc32(f"{name}#{k}".encode()))


def pk(x):
    """Peak-normalise to 1."""
    m = np.abs(x).max()
    return x / m if m > 0 else x


def normalize(x, peak_db=-1.0):
    return pk(x) * db(peak_db)


def loop_len(sec, mult=512):
    """Loop length in samples, rounded to a multiple of `mult` so STFT frame grids are periodic."""
    return int(round(sec * SR / mult)) * mult


def next_pow2(n):
    return 1 << int(math.ceil(math.log2(max(2, n))))


def fade(x, fin=0.0, fout=0.0):
    x = np.array(x, float, copy=True)
    n = len(x)
    if fin > 0:
        k = min(n, N(fin))
        w = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, k))
        x[:k] = (x[:k].T * w).T
    if fout > 0:
        k = min(n, N(fout))
        w = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k))
        x[n - k:] = (x[n - k:].T * w).T
    return x


def pad_to(x, n):
    if len(x) >= n:
        return x[:n]
    shape = (n - len(x),) + x.shape[1:]
    return np.concatenate([x, np.zeros(shape)])


# =============================================================================
# Frequency responses + filtering (minimum-phase by default: causal, no pre-ring)
# =============================================================================

def freqs_for(nfft):
    return np.fft.rfftfreq(nfft, 1.0 / SR)


def r_lp(f, fc, order=2):
    return 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))


def r_hp(f, fc, order=2):
    return 1.0 / np.sqrt(1.0 + (fc / np.maximum(f, 1e-6)) ** (2 * order))


def r_bp(f, lo, hi, order=2):
    return r_hp(f, lo, order) * r_lp(f, hi, order)


def r_peak(f, fc, gain_db, bw_oct=1.0):
    """Smooth bell in log-frequency. bw_oct = full width at half height, in octaves."""
    sig = bw_oct / 2.355
    lf = np.log2(np.maximum(f, 1e-3) / fc)
    return 1.0 + (db(gain_db) - 1.0) * np.exp(-0.5 * (lf / sig) ** 2)


def r_res(f, fc, bw):
    """Two-pole resonator magnitude normalised to 1 at fc (bw in Hz)."""
    f = np.maximum(f, 1e-3)
    return 1.0 / np.sqrt(1.0 + ((f * f - fc * fc) / (f * bw)) ** 2)


def _minphase(mag, nfft):
    logm = np.log(np.maximum(mag, 1e-7))
    c = np.fft.irfft(logm, n=nfft)
    w = np.zeros(nfft)
    w[0] = 1.0
    w[1:(nfft + 1) // 2] = 2.0
    if nfft % 2 == 0:
        w[nfft // 2] = 1.0
    return np.exp(np.fft.rfft(c * w))


def filt(x, H, minphase=True, circular=False, pad=0.5):
    """Filter x with magnitude response H(f) (callable or array)."""
    x = np.asarray(x, float)
    if x.ndim == 2:
        return np.stack([filt(x[:, c], H, minphase, circular, pad) for c in range(x.shape[1])], 1)
    n = len(x)
    nfft = n if circular else next_pow2(n + N(pad))
    f = freqs_for(nfft)
    mag = H(f) if callable(H) else H
    mag = np.broadcast_to(np.asarray(mag, float), f.shape)
    G = _minphase(mag, nfft) if minphase else mag
    y = np.fft.irfft(np.fft.rfft(x, nfft) * G, nfft)
    return y[:n]


def conv(x, h, circular=False, out_len=None):
    """FFT convolution. Mono x with stereo h gives stereo out; stereo x with stereo h is per-channel."""
    x = np.asarray(x, float)
    h = np.asarray(h, float)
    if x.ndim == 1 and h.ndim == 2:
        return np.stack([conv(x, h[:, c], circular, out_len) for c in range(h.shape[1])], 1)
    if x.ndim == 2 and h.ndim == 2:
        return np.stack([conv(x[:, c], h[:, c], circular, out_len) for c in range(x.shape[1])], 1)
    if x.ndim == 2:
        return np.stack([conv(x[:, c], h, circular, out_len) for c in range(x.shape[1])], 1)
    n, m = len(x), len(h)
    if circular:
        if m > n:
            hh = np.zeros(n)
            for i in range(0, m, n):
                seg = h[i:i + n]
                hh[:len(seg)] += seg
            h = hh
        y = np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(h, n), n)
        return y
    L = out_len or (n + m - 1)
    nfft = next_pow2(n + m)
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)
    return y[:L]


def stft_apply(x, mask_fn, nfft=2048, hop=512, circular=False):
    """Time-varying zero-phase filter. mask_fn(t_centers[s], f[Hz]) -> (frames, bins)."""
    x = np.asarray(x, float)
    n = len(x)
    win = np.hanning(nfft + 1)[:-1]
    if circular:
        assert n % hop == 0, "circular STFT needs len % hop == 0"
        xp = np.concatenate([x[-nfft:], x, x[:nfft]])
    else:
        xp = np.concatenate([np.zeros(nfft), x, np.zeros(nfft)])
    nfr = (len(xp) - nfft) // hop + 1
    f = freqs_for(nfft)
    out = np.zeros(len(xp))
    wsum = np.zeros(len(xp))
    w2 = win * win
    B = 768
    for b0 in range(0, nfr, B):
        b1 = min(nfr, b0 + B)
        starts = np.arange(b0, b1) * hop
        idx = starts[:, None] + np.arange(nfft)[None, :]
        X = np.fft.rfft(xp[idx] * win, axis=1)
        tc = (starts + nfft / 2 - nfft) / SR
        M = mask_fn(tc, f)
        Y = np.fft.irfft(X * M, n=nfft, axis=1) * win
        for i, s in enumerate(starts):
            out[s:s + nfft] += Y[i]
            wsum[s:s + nfft] += w2
    out = out[nfft:nfft + n] / np.maximum(wsum[nfft:nfft + n], 1e-9)
    return out


# =============================================================================
# Noise, envelopes, oscillators, modulators
# =============================================================================

def white(rng, n):
    return rng.standard_normal(n)


def colored(rng, n, slope_db_oct):
    """Spectrally shaped noise, generated in the frequency domain, so it's periodic in n."""
    nb = n // 2 + 1
    X = rng.standard_normal(nb) + 1j * rng.standard_normal(nb)
    f = freqs_for(n)
    f[0] = f[1]
    X *= (f / 1000.0) ** (slope_db_oct / 6.0206)
    X[0] = 0
    x = np.fft.irfft(X, n)
    return x / (x.std() + 1e-12)


def env_ad(n, attack, tau, delay=0.0, curve=1.0):
    t = tax(n) - delay
    e = np.zeros(n)
    if attack > 0:
        a = (t >= 0) & (t < attack)
        e[a] = (t[a] / attack) ** curve
        d = t >= attack
        e[d] = np.exp(-(t[d] - attack) / tau)
    else:
        d = t >= 0
        e[d] = np.exp(-t[d] / tau)
    return e


def env_pts(n, pts, offset=0.0):
    ts = [p[0] + offset for p in pts]
    vs = [p[1] for p in pts]
    return np.interp(tax(n), ts, vs, left=vs[0], right=vs[-1])


def burst(rng, n, tau, lo=None, hi=None, attack=0.0, delay=0.0, order=2):
    x = white(rng, n) * env_ad(n, attack, tau, delay)
    if lo or hi:
        x = filt(x, lambda f: (r_hp(f, lo, order) if lo else 1.0) * (r_lp(f, hi, order) if hi else 1.0))
    return x


def friedlander(n, td, b=1.6, delay=0.0):
    t = tax(n) - delay
    return np.where(t >= 0, (1.0 - t / td) * np.exp(-b * np.maximum(t, 0) / td), 0.0)


class Mod:
    """Smooth random modulator: zero mean, unit std, optionally periodic in `period` seconds."""

    def __init__(self, rng, dur, max_hz, ctrl_hz=None, periodic=True):
        ctrl_hz = ctrl_hz or max(400.0, 4.0 * max_hz)
        nc = max(16, int(round(dur * ctrl_hz)))
        self.ctrl_hz = nc / dur
        X = np.fft.rfft(rng.standard_normal(nc))
        f = np.fft.rfftfreq(nc, 1.0 / self.ctrl_hz)
        X *= r_lp(f, max_hz, 3)
        X[0] = 0
        m = np.fft.irfft(X, nc)
        self.m = m / (m.std() + 1e-12)
        self.dur = dur
        self.periodic = periodic
        self.tc = np.arange(nc) / self.ctrl_hz

    def __call__(self, t):
        t = np.asarray(t, float)
        if self.periodic:
            return np.interp(t, self.tc, self.m, period=self.dur)
        return np.interp(t, self.tc, self.m)


def phase_cycles(f, periodic=False):
    """Instantaneous frequency (Hz, per sample) to phase in cycles. If periodic, nudge to an integer total."""
    f = np.asarray(f, float)
    ph = np.concatenate([[0.0], np.cumsum(f)[:-1]]) / SR
    if periodic:
        total = ph[-1] + f[-1] / SR
        ph -= (total - round(total)) * (np.arange(len(f)) / len(f))
    return ph


def saw_table(nharm, rolloff=1.0, size=4096):
    x = np.arange(size) / size
    tab = np.zeros(size)
    for k in range(1, nharm + 1):
        tab += np.sin(TAU * k * x) / k ** rolloff
    return tab / np.abs(tab).max()


def table_osc(tab, ph):
    size = len(tab)
    p = (ph % 1.0) * size
    i0 = np.floor(p).astype(np.int64)
    fr = p - i0
    i0 %= size
    i1 = (i0 + 1) % size
    return tab[i0] * (1 - fr) + tab[i1] * fr


def qf(f, dur):
    """Quantise frequency to an integer number of cycles in a loop of `dur` seconds."""
    return round(f * dur) / dur


# =============================================================================
# Modal synthesis
# =============================================================================

STEEL = (1.0, 1.47, 2.09, 2.76, 3.52, 4.40, 5.31)
BRASS_CASE = (1.0, 1.43, 1.97, 2.61)


def modal_ir(n, freqs, taus, amps, rng=None, delay=0.0):
    t = tax(n) - delay
    out = np.zeros(n)
    for f, tau, a in zip(freqs, taus, amps):
        if f >= SR * 0.47:
            continue
        m = min(n, int((delay + tau * 9.0) * SR) + 2)
        tt = np.maximum(t[:m], 0.0)
        ph = rng.uniform(0, TAU) if rng is not None else 0.0
        seg = a * np.exp(-tt / tau) * np.sin(TAU * f * tt + ph)
        seg[t[:m] < 0] = 0.0
        k = max(2, min(m // 5, N(0.03)))
        seg[m - k:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k))
        out[:m] += seg
    return out


def metal_hit(rng, dur, base, n_modes=6, tau=(0.04, 0.006), click=0.5, ratios=STEEL, jitter=0.05):
    n = N(dur)
    k = min(n_modes, len(ratios))
    freqs = [base * ratios[i] * (1 + rng.uniform(-jitter, jitter)) for i in range(k)]
    taus = np.geomspace(tau[0], tau[1], k)
    amps = [rng.uniform(0.45, 1.0) / (1.0 + 0.35 * i) for i in range(k)]
    y = pk(modal_ir(n, freqs, taus, amps, rng))
    if click > 0:
        y = y + click * pk(burst(rng, n, 0.0005, 2500, 16000))
    return fade(pk(y), 0, dur * 0.3)


def sparse_clicks(rng, n, rate, t0, t1, lo, hi, skew=1.0, amp_sigma=0.6):
    k = rng.poisson(max(0.0, rate * (t1 - t0)))
    x = np.zeros(n)
    if k == 0:
        return x
    ts = t0 + (t1 - t0) * rng.random(k) ** skew
    idx = np.clip((ts * SR).astype(int), 0, n - 1)
    amps = rng.lognormal(0, amp_sigma, k) * rng.choice([-1, 1], k)
    np.add.at(x, idx, amps)
    return filt(x, lambda f: r_bp(f, lo, hi, 2))


def thud(rng, n, tau, hi=300, f0=None, delay=0.0, attack=0.002):
    y = pk(burst(rng, n, tau, 30, hi, attack=attack, delay=delay))
    if f0:
        t = np.maximum(tax(n) - delay, 0)
        s = np.sin(TAU * phase_cycles(np.full(n, f0) * (1 + 0.4 * np.exp(-t / 0.01))))
        s *= env_ad(n, attack, tau * 1.3, delay)
        y = y + 0.8 * pk(s)
    return pk(y)


# =============================================================================
# Placement, panning, dynamics, loops
# =============================================================================

def place(buf, snd, t0, gain=1.0, circular=False):
    """Add snd into buf at t0 seconds. Mono into stereo is duplicated; circular wraps around the end."""
    snd = np.asarray(snd, float) * gain
    if buf.ndim == 2 and snd.ndim == 1:
        snd = np.stack([snd, snd], 1)
    n = len(buf)
    i0 = int(round(t0 * SR))
    if circular:
        i0 %= n
        pos = 0
        while pos < len(snd):
            j = (i0 + pos) % n
            take = min(len(snd) - pos, n - j)
            buf[j:j + take] += snd[pos:pos + take]
            pos += take
    else:
        a = max(0, i0)
        b = min(n, i0 + len(snd))
        if b > a:
            buf[a:b] += snd[a - i0:b - i0]
    return buf


def pan(x, p):
    th = (np.clip(p, -1, 1) + 1.0) * np.pi / 4.0
    return np.stack([x * np.cos(th), x * np.sin(th)], 1)


def sat(x, drive=2.0, asym=0.0):
    y = np.tanh(drive * (x + asym)) - np.tanh(drive * asym)
    return y


def limit(x, ceiling_db=-1.0, release=0.05, look=0.0015):
    """Look-ahead peak limiter with exponential release (peak-hold, max-accumulate trick)."""
    c = db(ceiling_db)
    a = np.abs(x) if x.ndim == 1 else np.abs(x).max(1)
    g = np.minimum(1.0, c / np.maximum(a, 1e-12))
    w = max(1, N(look))
    gp = np.concatenate([g, np.ones(w)])
    g_la = np.lib.stride_tricks.sliding_window_view(gp, w).min(axis=1)[:len(g)]
    d = np.maximum(1.0 - g_la, 1e-12)
    ts = release * SR
    j = np.arange(len(d))
    u = np.log(d) + j / ts
    r = np.exp(np.maximum.accumulate(u) - j / ts)
    gain = 1.0 - np.minimum(r, 1.0 - 1e-9)
    gain = np.minimum(gain, g_la)
    y = (x.T * gain).T
    return np.clip(y, -c, c)


def fold(x, L):
    """Fold a rendered buffer into a loop of length L (additive wrap of the overflow)."""
    y = np.array(x[:L], float, copy=True)
    if len(y) < L:
        y = pad_to(y, L)
    pos = L
    while pos < len(x):
        seg = x[pos:pos + L]
        y[:len(seg)] += seg
        pos += L
    return y


# =============================================================================
# Synthetic impulse responses
# =============================================================================

_BANDS = [(0, 180), (180, 360), (360, 720), (720, 1440), (1440, 2880), (2880, 5760), (5760, 11520), (11520, 22050)]


def _band_masks(f):
    masks = []
    for lo, hi in _BANDS:
        m = np.ones_like(f)
        if lo > 0:
            m *= r_hp(f, lo, 4)
        if hi < 22050:
            m *= r_lp(f, hi, 4)
        masks.append(m)
    return masks


def ir_build(rng, length, taps, late, stereo=True, mod=None):
    n = N(length)
    ch = 2 if stereo else 1
    ir = np.zeros((n, ch))
    kcache = {}
    for tp in taps:
        lp = int(tp.get("lp", 16000))
        if lp not in kcache:
            d = np.zeros(1024)
            d[0] = 1.0
            kcache[lp] = filt(d, lambda f: r_lp(f, lp, 2), pad=0.05)
        k = kcache[lp] * tp["g"]
        i0 = N(tp["t"])
        if i0 >= n:
            continue
        seg = k[:n - i0]
        if stereo:
            th = (np.clip(tp.get("pan", 0.0), -1, 1) + 1) * np.pi / 4
            ir[i0:i0 + len(seg), 0] += seg * np.cos(th) * 1.4142
            ir[i0:i0 + len(seg), 1] += seg * np.sin(th) * 1.4142
        else:
            ir[i0:i0 + len(seg), 0] += seg
    if late:
        t = tax(n)
        nfft = n
        f = freqs_for(nfft)
        masks = _band_masks(f)
        cf = np.array([max(60.0, math.sqrt(max(lo, 60) * hi)) for lo, hi in _BANDS])
        tf = np.array([p[0] for p in late["t60"]])
        tv = np.array([p[1] for p in late["t60"]])
        t60s = np.interp(np.log(cf), np.log(tf), tv)
        onset = np.clip((t - late["start"]) / max(late.get("fade", 0.02), 1e-4), 0, 1)
        onset = 0.5 - 0.5 * np.cos(np.pi * onset)
        rolling = 1.0
        if mod:
            m = Mod(rng, length, mod[0], periodic=False)
            rolling = np.clip(1.0 + mod[1] * m(t), 0.2, 2.0)
        tails = np.zeros((n, ch))
        for c in range(ch):
            X = np.fft.rfft(white(rng, n))
            tail = np.zeros(n)
            for mk, T60 in zip(masks, t60s):
                tail += np.fft.irfft(X * mk, n) * np.exp(-6.9078 * t / T60)
            tails[:, c] = tail * onset * rolling
        # late["gain"] is the energy ratio of the diffuse tail to the discrete early reflections
        e_taps = float((ir ** 2).sum()) or 1.0
        e_tail = float((tails ** 2).sum()) + 1e-12
        ir += tails * math.sqrt(late["gain"] * e_taps / e_tail)
    return ir if stereo else ir[:, 0]


def ir_street(rng):
    """Narrow granite street: facade slapbacks, flutter between facades, far houses, rolling tail."""
    c = 343.0
    dl, dr = rng.uniform(3.0, 5.5), rng.uniform(4.0, 7.5)
    W = dl + dr
    taps = [dict(t=2 * dl / c, g=0.62, lp=9000, pan=-0.75), dict(t=2 * dr / c, g=0.52, lp=8500, pan=0.75)]
    t_fl = 2 * dl / c
    for k in range(1, 11):
        t_fl += 2 * W / c * rng.uniform(0.97, 1.03)
        taps.append(dict(t=t_fl, g=0.5 * 0.72 ** k, lp=9000 * 0.78 ** k, pan=0.6 if k % 2 else -0.6))
    for _ in range(4):
        D = rng.uniform(18, 45)
        taps.append(dict(t=2 * D / c, g=rng.uniform(0.18, 0.34), lp=rng.uniform(2500, 4500), pan=rng.uniform(-0.4, 0.4)))
    for _ in range(4):
        D = rng.uniform(55, 110)
        taps.append(dict(t=2 * D / c, g=rng.uniform(0.08, 0.18), lp=rng.uniform(1200, 2200), pan=rng.uniform(-0.9, 0.9)))
    late = dict(start=0.04, fade=0.08, gain=0.6,
                t60=[(125, 1.9), (250, 1.7), (500, 1.4), (1000, 1.1), (2000, 0.8), (4000, 0.5), (8000, 0.3), (16000, 0.15)])
    return ir_build(rng, 2.6, taps, late, mod=(4.0, 0.35))


def ir_interior(rng):
    taps = []
    for _ in range(36):
        t = rng.uniform(0.002, 0.024)
        taps.append(dict(t=t, g=rng.uniform(0.25, 0.7) * (1.0 - t * 18), lp=rng.uniform(5000, 12000), pan=rng.uniform(-1, 1)))
    late = dict(start=0.006, fade=0.018, gain=3.0,
                t60=[(125, 1.5), (250, 1.35), (500, 1.15), (1000, 1.0), (2000, 0.8), (4000, 0.55), (8000, 0.35), (16000, 0.2)])
    return ir_build(rng, 1.9, taps, late)


def ir_field(rng):
    taps = [dict(t=0.0016, g=0.45, lp=6000, pan=0.0)]
    for _ in range(5):
        D = rng.uniform(60, 140)
        taps.append(dict(t=2 * D / 343.0, g=rng.uniform(0.06, 0.14), lp=rng.uniform(1200, 2400), pan=rng.uniform(-1, 1)))
    late = dict(start=0.05, fade=0.1, gain=0.8, t60=[(125, 1.1), (500, 0.7), (2000, 0.4), (8000, 0.18)])
    return ir_build(rng, 1.6, taps, late)


def ir_village(rng, length=3.2):
    taps = []
    for _ in range(8):
        t = rng.uniform(0.02, 0.22)
        taps.append(dict(t=t, g=rng.uniform(0.12, 0.35), lp=rng.uniform(2000, 5000), pan=rng.uniform(-1, 1)))
    late = dict(start=0.02, fade=0.08, gain=2.5,
                t60=[(125, 2.6), (250, 2.3), (500, 2.0), (1000, 1.6), (2000, 1.1), (4000, 0.7), (8000, 0.4), (16000, 0.2)])
    return ir_build(rng, length, taps, late)


def ir_hall(rng, length=7.5):
    taps = []
    for _ in range(40):
        t = rng.uniform(0.01, 0.09)
        taps.append(dict(t=t, g=rng.uniform(0.05, 0.25), lp=rng.uniform(3000, 8000), pan=rng.uniform(-1, 1)))
    late = dict(start=0.02, fade=0.12, gain=10.0,
                t60=[(125, 6.5), (250, 6.0), (500, 5.2), (1000, 4.3), (2000, 3.3), (4000, 2.3), (8000, 1.4), (16000, 0.8)])
    return ir_build(rng, length, taps, late)


def add_reverb(x, ir, wet, dry=1.0, circular=False):
    """dry*x + wet*reverb(x), with the wet signal peak-matched to x. Mono x with stereo IR gives stereo."""
    w = conv(x, ir, circular=circular)
    x2 = np.stack([x, x], 1) if (w.ndim == 2 and x.ndim == 1) else x
    if not circular:
        x2 = pad_to(x2, len(w))
    return dry * x2 + wet * pk(w) * max(np.abs(x).max(), 1e-12)


# =============================================================================
# WAV IO
# =============================================================================

def write_wav(path, x, loop=False, name=""):
    x = np.asarray(x, float)
    ch = 1 if x.ndim == 1 else x.shape[1]
    rng = rng_for(name or str(path), 991)
    tpdf = (rng.random(x.shape) - rng.random(x.shape))
    pcm = np.clip(np.round(x * 32767.0 + tpdf), -32768, 32767).astype("<i2")
    data = pcm.tobytes()
    nframes = len(x)
    fmt = struct.pack("<HHIIHH", 1, ch, SR, SR * ch * 2, ch * 2, 16)
    chunks = [b"fmt " + struct.pack("<I", len(fmt)) + fmt]
    chunks.append(b"data" + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) % 2 else b""))
    if loop:
        smpl = struct.pack("<9I", 0, 0, int(1e9 / SR), 60, 0, 0, 0, 1, 0)
        smpl += struct.pack("<6I", 0, 0, 0, nframes - 1, 0, 0)
        chunks.append(b"smpl" + struct.pack("<I", len(smpl)) + smpl)
    body = b"WAVE" + b"".join(chunks)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def read_wav(path):
    b = path.read_bytes()
    assert b[:4] == b"RIFF" and b[8:12] == b"WAVE", "not RIFF/WAVE"
    pos = 12
    info = {}
    while pos + 8 <= len(b):
        cid = b[pos:pos + 4]
        size = struct.unpack("<I", b[pos + 4:pos + 8])[0]
        body = b[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            fmt, ch, sr, _, _, bits = struct.unpack("<HHIIHH", body[:16])
            info.update(fmt=fmt, ch=ch, sr=sr, bits=bits)
        elif cid == b"data":
            info["pcm"] = np.frombuffer(body, "<i2").reshape(-1, info["ch"]).astype(float) / 32768.0
        elif cid == b"smpl":
            vals = struct.unpack("<15I", body[:60])
            info["smpl"] = dict(loops=vals[7], type=vals[10], start=vals[11], end=vals[12])
        pos += 8 + size + (size & 1)
    return info


# =============================================================================
# Sound designs: weapons (P38)
# =============================================================================

def blast_core(rng, n, mech=True, level_mech=0.2):
    """The 9 mm muzzle blast as heard by the shooter. Returns float mono, not normalised."""
    t = tax(n)
    td = rng.uniform(0.00045, 0.0008)
    fr = filt(friedlander(n, td, b=rng.uniform(1.3, 2.0)), lambda f: r_hp(f, 28, 2))
    crack = filt(white(rng, n) * env_ad(n, 0.00005, rng.uniform(0.0018, 0.0032)),
                 lambda f: r_bp(f, 1100, 12000, 2) * r_peak(f, 3600, 4.0, 1.4))
    blast = filt(white(rng, n) * env_ad(n, 0.0003, rng.uniform(0.010, 0.018)),
                 lambda f: r_bp(f, 170, 4200, 2) * r_peak(f, 950, 5.0, 1.5))
    f0, f1 = rng.uniform(140, 190), rng.uniform(46, 60)
    fq = f1 + (f0 - f1) * np.exp(-t / 0.032)
    body = np.sin(TAU * phase_cycles(fq)) * env_ad(n, 0.0007, rng.uniform(0.035, 0.05))
    rumble = filt(white(rng, n) * env_ad(n, 0.002, rng.uniform(0.04, 0.06)), lambda f: r_bp(f, 32, 430, 2))
    chuff = filt(white(rng, n) * env_ad(n, 0.003, 0.03, delay=0.001), lambda f: r_bp(f, 280, 1500, 1))
    nf = np.zeros(n)
    for d, g in [(0.0011, 0.38), (0.0029, 0.26), (0.0054, 0.18), (0.0083, 0.1)]:
        place(nf, filt(pk(blast)[:N(0.08)], lambda f: r_lp(f, 7000, 1)), d, g)
    mix = (1.0 * pk(fr) + 0.6 * pk(crack) + 0.9 * pk(blast) + 0.4 * pk(body)
           + 0.35 * pk(rumble) + 0.35 * pk(chuff) + 0.5 * nf)
    if mech:
        m = np.zeros(n)
        t_rear = rng.uniform(0.008, 0.012)
        t_bat = t_rear + rng.uniform(0.013, 0.02)
        place(m, metal_hit(rng, 0.12, rng.uniform(1900, 2400), tau=(0.035, 0.006)), t_rear, 0.6)
        place(m, metal_hit(rng, 0.2, rng.uniform(1450, 1850), tau=(0.055, 0.008)), t_bat, 1.0)
        m += 0.35 * pk(filt(white(rng, n) * env_ad(n, 0.0004, 0.01, delay=t_bat), lambda f: r_bp(f, 2000, 9000)))
        mix = mix + level_mech * pk(m)
    return mix


def p38_shot(rng):
    n = N(0.75)
    x = blast_core(rng, n, mech=True, level_mech=0.22)
    # Saturate only the first ~30 ms (the blast), so the decay keeps its natural shape.
    w = env_pts(n, [(0, 1.0), (0.02, 1.0), (0.05, 0.0)])
    xs = pk(x)
    x = w * sat(xs * 1.5, drive=1.8, asym=0.05) / math.tanh(1.8 * 1.5) + (1 - w) * xs
    x = filt(x, lambda f: r_hp(f, 25, 2) * r_peak(f, 110, -4.0, 1.5) * r_peak(f, 850, 4.0, 2.0))
    x = limit(normalize(x, 2.0), -1.0, release=0.03)
    return fade(x, 0, 0.08)


def shot_tail(rng, kind):
    n = N(0.5)
    hp = 180 if kind == "street" else 80
    exc = filt(blast_core(rng, n, mech=False), lambda f: r_lp(f, 9000, 1) * r_hp(f, hp, 2) * r_peak(f, 1200, 4.0, 2.0))
    ir = {"street": ir_street, "interior": ir_interior}[kind](rng)
    wet = conv(exc, ir)
    L = N(2.4 if kind == "street" else 1.8)
    wet = pad_to(wet, L)
    wet = filt(wet, lambda f: r_hp(f, 35, 2))
    if kind == "interior":
        wet = sat(pk(wet) * 1.3, 1.4)
    return fade(normalize(wet, -1.0), 0.0, 0.3)


def p38_dryfire(rng):
    n = N(0.35)
    x = 0.05 * pk(burst(rng, n, 0.02, 1500, 6000, attack=0.02))
    place(x, metal_hit(rng, 0.06, rng.uniform(3500, 4200), n_modes=4, tau=(0.012, 0.003)), 0.055, 0.35)
    place(x, metal_hit(rng, 0.25, rng.uniform(1700, 2100), tau=(0.05, 0.008)), 0.058, 1.0)
    place(x, thud(rng, N(0.08), 0.01, hi=400), 0.058, 0.45)
    return fade(normalize(x), 0, 0.03)


def p38_slide_back(rng):
    n = N(0.42)
    sc = white(rng, n) * env_pts(n, [(0, 0), (0.012, 0.55), (0.1, 1.0), (0.118, 0.25), (0.13, 0)])

    def mask(tc, f):
        fc = 2600 + 1600 * np.clip(tc / 0.12, 0, 1)
        return r_bp(f[None, :], 1300, 8000, 2) * (0.4 + 1.6 * r_res(f[None, :], fc[:, None], 900))

    x = 0.45 * pk(stft_apply(sc, mask, nfft=512, hop=128))
    place(x, metal_hit(rng, 0.06, rng.uniform(2800, 3400), n_modes=4, tau=(0.015, 0.004)), 0.06, 0.4)
    place(x, metal_hit(rng, 0.18, rng.uniform(1600, 2000), tau=(0.04, 0.007)), 0.126, 0.85)
    place(x, thud(rng, N(0.08), 0.02, hi=600), 0.0, 0.15)
    return fade(normalize(x), 0.001, 0.04)


def p38_slide_forward(rng):
    n = N(0.42)
    x = 0.35 * pk(burst(rng, n, 0.012, 2000, 8000, attack=0.02))
    place(x, metal_hit(rng, 0.32, rng.uniform(1300, 1600), tau=(0.09, 0.01)), 0.03, 1.0)
    place(x, thud(rng, N(0.1), 0.012, hi=500), 0.03, 0.55)
    place(x, metal_hit(rng, 0.3, rng.uniform(4800, 5600), n_modes=3, tau=(0.12, 0.05), click=0.1), 0.031, 0.22)
    return fade(normalize(x), 0.001, 0.05)


def p38_mag_out(rng):
    n = N(0.38)
    x = np.zeros(n)
    place(x, metal_hit(rng, 0.05, rng.uniform(3000, 3500), n_modes=4, tau=(0.012, 0.004)), 0.0, 0.6)
    fr = white(rng, n) * env_pts(n, [(0, 0), (0.02, 0), (0.035, 0.8), (0.11, 0.6), (0.13, 0)])
    fr = filt(fr, lambda f: r_bp(f, 900, 5500) * (1 + 1.6 * r_res(f, 820, 120) + 1.1 * r_res(f, 1900, 220)))
    x += 0.45 * pk(fr)
    place(x, metal_hit(rng, 0.08, rng.uniform(2300, 2700), n_modes=4, tau=(0.02, 0.005)), 0.13, 0.3)
    return fade(normalize(x), 0.0005, 0.04)


def p38_mag_in(rng):
    n = N(0.38)
    fr = white(rng, n) * env_pts(n, [(0, 0), (0.01, 0.6), (0.075, 0.9), (0.085, 0)])
    x = 0.4 * pk(filt(fr, lambda f: r_bp(f, 900, 5500) * (1 + 1.4 * r_res(f, 900, 140))))
    place(x, metal_hit(rng, 0.22, rng.uniform(1400, 1800), tau=(0.05, 0.008)), 0.085, 1.0)
    place(x, metal_hit(rng, 0.06, rng.uniform(3300, 3800), n_modes=4, tau=(0.012, 0.004)), 0.091, 0.5)
    place(x, thud(rng, N(0.08), 0.012, hi=450), 0.085, 0.5)
    return fade(normalize(x), 0.0005, 0.04)


def p38_decocker(rng):
    n = N(0.32)
    x = np.zeros(n)
    place(x, metal_hit(rng, 0.06, rng.uniform(2600, 3000), n_modes=4, tau=(0.014, 0.004)), 0.0, 0.5)
    place(x, metal_hit(rng, 0.2, rng.uniform(1500, 1900), tau=(0.04, 0.007)), 0.012, 0.9)
    place(x, thud(rng, N(0.08), 0.012, hi=450), 0.012, 0.4)
    return fade(normalize(x), 0.0005, 0.04)


def casing_cobble(rng):
    n = N(1.0)
    x = np.zeros(n)
    base = rng.uniform(4300, 5200)
    t, dt, a = 0.0, rng.uniform(0.11, 0.18), 1.0
    for _ in range(int(rng.integers(4, 7))):
        freqs = [base * r * (1 + rng.uniform(-0.02, 0.02)) for r in BRASS_CASE]
        taus = [0.07, 0.05, 0.035, 0.022]
        amps = [rng.uniform(0.4, 1.0) for _ in freqs]
        hit = pk(modal_ir(N(0.3), freqs, [ta * rng.uniform(0.6, 1.0) for ta in taus], amps, rng))
        hit += 0.35 * pk(burst(rng, N(0.3), 0.0007, 1800, 9000))
        place(x, hit, t, a)
        t += dt
        dt *= rng.uniform(0.5, 0.7)
        a *= rng.uniform(0.45, 0.65)
        if t > 0.85:
            break
    for _ in range(int(rng.integers(3, 7))):
        place(x, pk(modal_ir(N(0.05), [base * rng.uniform(0.98, 1.4)], [0.01], [1], rng)), t + rng.uniform(0, 0.12), a * 0.4)
    return fade(normalize(x), 0, 0.05)


# =============================================================================
# Impacts
# =============================================================================

def impact_stone(rng):
    n = N(0.8)
    x = 0.9 * pk(filt(friedlander(n, rng.uniform(0.0002, 0.0004)), lambda f: r_hp(f, 700, 2)))
    x += 0.6 * pk(burst(rng, n, 0.003, 900, 12000))
    x += 0.5 * pk(modal_ir(n, [rng.uniform(700, 1200), rng.uniform(1800, 2500), rng.uniform(3300, 4000)],
                           [0.016, 0.009, 0.005], [1, 0.7, 0.5], rng))
    x += 0.35 * pk(sparse_clicks(rng, n, 2500, 0.0, 0.25, 2000, 9000, skew=2.2))
    for _ in range(int(rng.integers(3, 8))):
        place(x, metal_hit(rng, 0.04, rng.uniform(2500, 5500), n_modes=3, tau=(0.008, 0.003), ratios=(1, 1.7, 2.6)),
              rng.uniform(0.1, 0.65), rng.uniform(0.05, 0.18))
    x += 0.25 * pk(burst(rng, n, 0.08, 1000, 6000, attack=0.004))
    return fade(normalize(sat(pk(x) * 1.2, 1.5)), 0, 0.06)


def impact_wood(rng):
    n = N(0.6)
    x = 1.0 * thud(rng, n, 0.015, hi=600)
    x += 0.45 * pk(modal_ir(n, [rng.uniform(180, 260), rng.uniform(380, 480), rng.uniform(650, 900), rng.uniform(1100, 1500)],
                            [0.03, 0.02, 0.012, 0.008], [1, 0.8, 0.5, 0.35], rng))
    x += 0.6 * pk(burst(rng, n, 0.002, 1200, 9000))
    x += 0.6 * pk(sparse_clicks(rng, n, 900, 0.0, 0.08, 1200, 6000, skew=1.5))
    return fade(normalize(sat(pk(x) * 1.2, 1.4)), 0, 0.06)


def impact_dirt(rng):
    n = N(0.7)
    x = 1.0 * thud(rng, n, 0.025, hi=300, f0=rng.uniform(55, 75))
    spray = filt(white(rng, n) * env_ad(n, 0.01, rng.uniform(0.09, 0.14)), lambda f: r_bp(f, 300, 2200))
    x += 0.55 * pk(spray)
    x += 0.3 * pk(sparse_clicks(rng, n, 400, 0.05, 0.45, 300, 1800, skew=1.6))
    return fade(normalize(x), 0, 0.06)


def ricochet(rng):
    dur = rng.uniform(0.75, 1.05)
    n = N(dur)
    t = tax(n)
    x = 0.5 * impact_stone(rng)[:n]
    x = pad_to(x, n)
    f0, f1 = rng.uniform(2800, 4000), rng.uniform(900, 1600)
    fq = f1 + (f0 - f1) * np.exp(-t / rng.uniform(0.18, 0.32))
    fm = rng.uniform(35, 85)
    jit = Mod(rng, dur, 25, periodic=False)
    fq = fq * (1 + 0.01 * jit(t))
    ph = phase_cycles(fq)
    tumble = 1 + 0.6 * np.sin(TAU * phase_cycles(np.full(n, fm) * (1 + 0.2 * jit(t))))
    whine = np.sin(TAU * ph) + 0.25 * np.sin(2 * TAU * ph)
    hiss = filt(white(rng, n), lambda f: r_bp(f, 1200, 7000))
    env = env_pts(n, [(0, 0), (0.015, 0), (0.03, 1.0), (dur * 0.4, 0.55), (dur, 0)])
    x += 0.8 * pk((whine + 0.15 * pk(hiss)) * tumble * env)
    return fade(normalize(x), 0, 0.05)


# =============================================================================
# Footsteps
# =============================================================================

def step_cobble(rng, run=False):
    n = N(0.4)
    x = (0.8 * pk(burst(rng, n, 0.003, 700, 6000)) + 0.6 * thud(rng, n, 0.01, hi=280)
         + 0.5 * pk(burst(rng, n, 0.007, 300, 1500)))
    x += 0.35 * pk(modal_ir(n, [rng.uniform(900, 1300), rng.uniform(2100, 2700)], [0.012, 0.006], [1, 0.6], rng))
    x += 0.25 * pk(sparse_clicks(rng, n, 600 if run else 300, 0.0, 0.05, 2500, 9000))
    dt = rng.uniform(0.045, 0.065) if run else rng.uniform(0.07, 0.11)
    toe = 0.55 * pk(burst(rng, n, 0.0035, 900, 7000, delay=dt)) + 0.35 * thud(rng, n, 0.008, hi=300, delay=dt)
    x += toe * rng.uniform(0.45, 0.65)
    if run:
        x += 0.25 * pk(burst(rng, n, 0.025, 1500, 8000, attack=0.008, delay=dt + 0.01))
    return fade(normalize(x), 0, 0.05)


def step_mud(rng, run=False):
    n = N(0.55)
    x = 0.7 * thud(rng, n, 0.03, hi=450, attack=0.004)
    w = white(rng, n) * env_pts(n, [(0, 0), (0.01, 1), (0.05, 0.6), (0.09, 0.9), (0.11, 0.05), (0.2, 0)])
    r1, r2 = rng.uniform(380, 520), rng.uniform(900, 1200)
    x += 0.8 * pk(filt(w, lambda f: r_bp(f, 250, 1800) * (1 + 1.6 * r_res(f, r1, 120) + 1.0 * r_res(f, r2, 200))))
    for _ in range(int(rng.integers(2, 6))):
        m = N(0.05)
        tt = tax(m)
        f0 = rng.uniform(350, 900)
        b = np.sin(TAU * phase_cycles(f0 * (1 + 22 * tt))) * env_ad(m, 0.0004, rng.uniform(0.006, 0.014))
        place(x, b, rng.uniform(0.03, 0.25), rng.uniform(0.15, 0.35))
    t_lift = rng.uniform(0.24, 0.34) if not run else rng.uniform(0.16, 0.22)
    suck = filt(white(rng, n) * env_pts(n, [(0, 0), (t_lift - 0.06, 0), (t_lift, 1.0), (t_lift + 0.03, 0)]),
                lambda f: r_bp(f, 400, 1500))
    x += 0.4 * pk(suck)
    if run:
        x += 0.5 * pk(burst(rng, n, 0.04, 1000, 6000, attack=0.003))
    return fade(normalize(x), 0, 0.05)


def step_gravel(rng, run=False):
    n = N(0.45)
    x = 0.45 * thud(rng, n, 0.012, hi=250)
    heel = sparse_clicks(rng, n, 6000 if run else 4000, 0.0, 0.09, 1200, 7000, skew=1.8, amp_sigma=0.8)
    dt = rng.uniform(0.05, 0.07) if run else rng.uniform(0.08, 0.12)
    toe = sparse_clicks(rng, n, 3500 if run else 2500, dt, dt + 0.08, 1200, 7000, skew=1.8, amp_sigma=0.8)
    crunch = filt(heel + 0.7 * toe, lambda f: r_peak(f, 3000, 4.0, 1.2))
    x += 1.0 * pk(crunch)
    bed = white(rng, n) * (env_ad(n, 0.004, 0.04) + 0.6 * env_ad(n, 0.004, 0.04, delay=dt))
    x += 0.25 * pk(filt(bed, lambda f: r_bp(f, 1500, 6000)))
    return fade(normalize(x), 0, 0.05)


def step_grass(rng, run=False):
    n = N(0.45)
    sw = white(rng, n) * env_pts(n, [(0, 0), (0.02, 1), (0.12, 0.4), (0.3, 0)])
    x = 0.6 * pk(filt(sw, lambda f: r_bp(f, 1200, 7000)))
    x += 0.7 * thud(rng, n, 0.02, hi=220)
    x += 0.2 * pk(sparse_clicks(rng, n, 150, 0.0, 0.15, 2500, 9000))
    dt = rng.uniform(0.05, 0.07) if run else rng.uniform(0.09, 0.13)
    sw2 = white(rng, n) * env_pts(n, [(0, 0), (dt, 0), (dt + 0.02, 0.6), (dt + 0.15, 0)])
    x += 0.45 * pk(filt(sw2, lambda f: r_bp(f, 1500, 7500)))
    if run:
        x += 0.3 * pk(filt(white(rng, n) * env_ad(n, 0.01, 0.06), lambda f: r_bp(f, 800, 5000)))
    return fade(normalize(x), 0, 0.05)


def wood_knock(rng, n, delay, amp):
    fr = [rng.uniform(110, 150), rng.uniform(230, 300), rng.uniform(480, 620), rng.uniform(1050, 1400)]
    y = pk(modal_ir(n, fr, [0.07, 0.045, 0.025, 0.012], [1, 0.7, 0.45, 0.3], rng, delay=delay))
    y += 0.4 * pk(burst(rng, n, 0.0015, 1500, 9000, delay=delay))
    return amp * y


def step_wood(rng, run=False, creak=False):
    n = N(0.85 if creak else 0.5)
    x = wood_knock(rng, n, 0.0, 1.0) + 0.5 * thud(rng, n, 0.012, hi=250)
    dt = rng.uniform(0.05, 0.07) if run else rng.uniform(0.08, 0.12)
    x += wood_knock(rng, n, dt, 0.55)
    if creak:
        t0, dur = rng.uniform(0.05, 0.12), rng.uniform(0.25, 0.4)
        f0 = rng.uniform(90, 160)
        tr = np.zeros(n)
        tt = t0
        while tt < t0 + dur:
            i = int(tt * SR)
            if i < n:
                tr[i] = 1.0
            tt += (1.0 / f0) * (1 + 0.18 * rng.standard_normal())
            f0 *= 1.0 + 0.004 * rng.standard_normal()
        tr *= env_pts(n, [(0, 0), (t0, 0), (t0 + dur * 0.3, 1), (t0 + dur, 0)])
        cr = filt(tr, lambda f: r_res(f, 520, 160) + 0.7 * r_res(f, 1350, 260) + 0.5 * r_res(f, 2800, 400))
        x += 0.45 * pk(cr)
    return fade(normalize(x), 0, 0.05)


def step_hobnail(rng):
    n = N(0.5)
    x = 1.0 * thud(rng, n, 0.018, hi=320, f0=rng.uniform(80, 100))
    place(x, metal_hit(rng, 0.18, rng.uniform(1800, 2300), tau=(0.05, 0.008)), 0.0, 0.55)
    for _ in range(int(rng.integers(4, 9))):
        place(x, metal_hit(rng, 0.05, rng.uniform(3000, 6000), n_modes=3, tau=(0.015, 0.004)), rng.uniform(0, 0.012), rng.uniform(0.2, 0.35))
    x += 0.25 * pk(sparse_clicks(rng, n, 800, 0.0, 0.06, 2500, 9000))
    dt = rng.uniform(0.09, 0.13)
    x += 0.5 * thud(rng, n, 0.02, hi=260, delay=dt)
    for _ in range(int(rng.integers(5, 11))):
        place(x, metal_hit(rng, 0.05, rng.uniform(3000, 6500), n_modes=3, tau=(0.014, 0.004)), dt + rng.uniform(0, 0.015), rng.uniform(0.18, 0.3))
    x += 0.3 * pk(burst(rng, n, 0.03, 2000, 9000, attack=0.01, delay=dt + 0.01))
    return fade(normalize(sat(pk(x) * 1.15, 1.3)), 0, 0.05)


# =============================================================================
# Ambience loops (periodic by construction)
# =============================================================================

def wind_gusts_loop(rng):
    L = loop_len(80.0)
    dur = L / SR
    g = Mod(rng, dur, 0.06)
    h = Mod(rng, dur, 0.6)
    out = np.zeros((L, 2))
    common = colored(rng, L, -4.5)
    for c in range(2):
        x = 0.72 * common + 0.55 * colored(rng, L, -4.5)
        shift = 0.35 * c

        def mask(tc, f, shift=shift):
            G = np.clip(0.55 + 0.3 * g(tc + shift) + 0.09 * h(tc + shift), 0.05, 1.35)[:, None]
            F = f[None, :]
            fc = 170 + 1700 * G ** 1.6
            body = r_lp(F, fc, 2) * r_hp(F, 35, 2) * (0.12 + G ** 1.4)
            wf = 520 + 420 * G
            whistle = 5.0 * np.clip(G - 0.78, 0, None) ** 1.5 * r_res(F, wf, 22)
            return body + whistle

        out[:, c] = stft_apply(x, mask, circular=True)
    rumble = filt(colored(rng, L, -6), lambda f: r_lp(f, 90, 2), circular=True)
    out += 0.25 * np.stack([rumble, rumble], 1) / (np.abs(rumble).max() + 1e-12) * np.abs(out).max()
    return normalize(out, -3.0)


def rain_light_loop(rng):
    L = loop_len(60.0)
    dur = L / SR
    out = np.zeros((L, 2))
    K = 20
    kernels = []
    for k in range(K):
        fk = math.exp(rng.uniform(math.log(1500), math.log(9500)))
        tau = rng.uniform(0.0008, 0.005)
        m = N(tau * 7) + 16
        tt = tax(m)
        ker = np.sin(TAU * fk * tt) * np.exp(-tt / tau) + 0.5 * rng.standard_normal(m) * np.exp(-tt / 0.0004)
        kernels.append(pk(ker))
    pats = []
    for k in range(6):
        m = N(0.06)
        tt = tax(m)
        ker = np.sin(TAU * rng.uniform(400, 1500) * tt) * np.exp(-tt / rng.uniform(0.005, 0.01))
        ker += 0.6 * filt(rng.standard_normal(m) * np.exp(-tt / 0.003), lambda f: r_bp(f, 500, 4000))
        pats.append(pk(ker))
    for c in range(2):
        acc = np.zeros(L)
        for ker in kernels:
            cnt = rng.poisson(750 / K * dur)
            tr = np.zeros(L)
            np.add.at(tr, rng.integers(0, L, cnt), rng.lognormal(-1.2, 0.6, cnt))
            acc += conv(tr, ker, circular=True)
        for ker in pats:
            cnt = rng.poisson(8 / 6 * dur)
            tr = np.zeros(L)
            np.add.at(tr, rng.integers(0, L, cnt), rng.lognormal(-0.6, 0.5, cnt))
            acc += 2.2 * conv(tr, ker, circular=True)
        bed = filt(colored(rng, L, -1.5), lambda f: r_bp(f, 500, 9000), circular=True)
        mod = Mod(rng, dur, 0.1)
        bed *= 1.0 + 0.2 * mod(tax(L))
        out[:, c] = pk(acc) + 0.3 * pk(bed)
    out = filt(out, lambda f: r_lp(f, 8000, 1) * r_peak(f, 4000, -2.0, 2.0), circular=True)
    return normalize(out, -4.0)


def drip(rng, kind="plink"):
    m = N(0.12)
    tt = tax(m)
    if kind == "plink":
        f0, tau = math.exp(rng.uniform(math.log(700), math.log(2600))), rng.uniform(0.006, 0.016)
        rise = rng.uniform(15, 35)
    else:
        f0, tau = rng.uniform(300, 700), rng.uniform(0.012, 0.025)
        rise = rng.uniform(5, 12)
    y = np.sin(TAU * phase_cycles(f0 * (1 + rise * tt))) * env_ad(m, 0.0003, tau)
    y += 0.25 * pk(burst(rng, m, 0.0004, 2000, 12000))
    return pk(y)


def drips_loop(rng):
    L = loop_len(60.0)
    dur = L / SR
    out = np.zeros((L, 2))
    for p, period in zip([-0.7, -0.2, 0.35, 0.8], [0.93, 1.61, 2.27, 1.17]):
        t = rng.uniform(0, period)
        while t < dur:
            place(out, pan(drip(rng, "plink" if rng.random() < 0.8 else "plop"), p + rng.uniform(-0.05, 0.05)), t,
                  rng.uniform(0.5, 1.0), circular=True)
            t += period * (1 + 0.08 * rng.standard_normal())
    t = 0.0
    while True:
        t += rng.exponential(1 / 0.5)
        if t >= dur:
            break
        place(out, pan(drip(rng, "plink" if rng.random() < 0.6 else "plop"), rng.uniform(-1, 1)), t,
              rng.uniform(0.2, 0.7), circular=True)
    ir = ir_street(rng)
    wet = conv(out, ir, circular=True)
    out = out + 0.35 * pk(wet) * np.abs(out).max()
    return normalize(out, -4.0)


def distant_sea_loop(rng):
    L = loop_len(80.0)
    dur = L / SR
    out = np.zeros((L, 2))
    k = 8
    for i in range(k):
        t0 = i * dur / k + rng.uniform(-1.5, 1.5)
        n = N(12.0)
        tc = 2.5 + rng.uniform(-0.4, 0.4)
        amp = rng.uniform(0.6, 1.0)
        for c in range(2):
            sw = filt(colored(rng, n, -6) * env_pts(n, [(0, 0), (tc, 1), (tc + 1.5, 0.3), (7.0, 0)]), lambda f: r_lp(f, 260, 2))
            cr = filt(colored(rng, n, -3) * env_ad(n, rng.uniform(0.25, 0.5), rng.uniform(0.6, 1.0), delay=tc),
                      lambda f: r_bp(f, 70, 1400, 2))
            wa = filt(colored(rng, n, -3) * env_ad(n, 0.5, rng.uniform(1.0, 1.6), delay=tc + 0.7), lambda f: r_bp(f, 450, 3200, 2))
            sh = sparse_clicks(rng, n, 220, tc + 0.8, tc + 5.0, 1500, 5000, skew=1.6) * env_ad(n, 0.0, 1.5, delay=tc + 0.8)
            wave = fade(0.5 * pk(sw) + amp * pk(cr) + 0.35 * pk(wa) + 0.12 * pk(sh), 0.0, 3.0)
            place(out[:, c:c + 1], wave[:, None] * (1.0 if c == 0 else rng.uniform(0.75, 1.0)), t0 + 0.02 * c, 1.0, circular=True)
    bed = filt(colored(rng, L, -6), lambda f: r_lp(f, 160, 2), circular=True)
    bed2 = filt(colored(rng, L, -6), lambda f: r_lp(f, 160, 2), circular=True)
    out += 0.35 * np.abs(out).max() * np.stack([pk(bed), pk(bed2)], 1)
    out = filt(out, lambda f: r_lp(f, 2500, 2), circular=True)
    wet = conv(out, ir_field(rng), circular=True)
    out = out + 0.3 * pk(wet) * np.abs(out).max()
    return normalize(out, -4.0)


def fire_crackle(rng, size):
    """One crackle: a short cluster of resonant micro-clicks; bigger ones get a low woody body."""
    m = N(0.07)
    y = np.zeros(m)
    t0 = 0.0
    for k in range(1 + rng.poisson(min(6.0, size))):
        t0 += rng.exponential(0.003) if k else 0.0
        f = math.exp(rng.uniform(math.log(900), math.log(5500)))
        tau = rng.uniform(0.0004, 0.002)
        n = N(tau * 8) + 4
        tk = tax(n)
        click = np.sin(TAU * f * tk + rng.uniform(0, TAU)) * np.exp(-tk / tau) + 0.6 * rng.standard_normal(n) * np.exp(-tk / (tau * 0.5))
        place(y, click, t0, rng.lognormal(0, 0.5))
    y = pk(y)
    if size > 2.5:
        y += min(1.0, size / 8) * pk(burst(rng, m, rng.uniform(0.004, 0.009), 120, 900))
    return pk(y)


def fire_pop(rng):
    """A big pop: sharp crack, woody body, a little ring from the iron drum, trailing sparks."""
    m = N(0.5)
    y = 1.0 * pk(burst(rng, m, 0.0015, 1500, 12000))
    y += 0.8 * pk(burst(rng, m, rng.uniform(0.008, 0.015), 150, 1200, attack=0.0005))
    y += 0.15 * pk(modal_ir(m, [rng.uniform(380, 520), rng.uniform(900, 1200)], [rng.uniform(0.025, 0.05), 0.02], [1, 0.6], rng))
    for _ in range(int(rng.integers(2, 7))):
        place(y, fire_crackle(rng, 1.0), rng.uniform(0.05, 0.4), rng.uniform(0.05, 0.18))
    return fade(pk(y), 0, 0.1)


def fire_crackle_loop(rng):
    """Small wood fire in an iron brazier: roar/hiss bed, bursty crackles, pops, sap hiss, ember settle (mono loop)."""
    L = loop_len(24.0)
    dur = L / SR
    t = tax(L)
    flick, slow, hf = Mod(rng, dur, 1.5), Mod(rng, dur, 0.15), Mod(rng, dur, 6.0)
    roar = filt(colored(rng, L, -6), lambda f: r_bp(f, 40, 520, 2) * r_peak(f, 160, 3.0, 1.5), circular=True)
    roar = pk(roar) * np.clip(1.0 + 0.25 * flick(t) + 0.2 * slow(t), 0.4, 1.8)
    hiss = filt(colored(rng, L, -1.5), lambda f: r_bp(f, 1500, 7000, 2), circular=True)
    hiss = pk(hiss) * np.clip(0.7 + 0.35 * hf(t) + 0.2 * flick(t), 0.1, 1.6)
    bed = 0.2 * roar + 0.05 * hiss

    ev = np.zeros(L)
    burst_mod = Mod(rng, dur, 0.4)
    tc = 0.0
    while True:
        rate = 1.5 + 7.0 * float(np.clip(0.5 + 0.5 * burst_mod(tc), 0, 1)) ** 2   # 1.5-8.5 crackles/s, clustered
        tc += rng.exponential(1.0 / rate)
        if tc >= dur:
            break
        size = min(8.0, rng.pareto(1.6) + 1.0)                                # heavy-tailed sizes
        place(ev, fire_crackle(rng, size), tc, 0.22 * size ** 0.9, circular=True)
    for _ in range(max(3, rng.poisson(0.35 * dur))):
        place(ev, fire_pop(rng), rng.uniform(0, dur), rng.uniform(0.6, 1.0), circular=True)
    for _ in range(int(rng.integers(2, 4))):                                    # sap hiss: steam escaping a log
        d = rng.uniform(0.8, 2.5)
        m = N(d)
        fz = Mod(rng, d, 30, periodic=False)
        fc = rng.uniform(3500, 6000)
        sap = filt(white(rng, m), lambda f: r_res(f, fc, 800)) * np.clip(1 + 0.6 * fz(tax(m)), 0, 2)
        sap *= env_pts(m, [(0, 0), (0.2, 1), (d - 0.5, 0.8), (d, 0)])
        sap += 0.3 * pk(sparse_clicks(rng, m, 25, 0, d, 2500, 8000))
        place(ev, pk(sap), rng.uniform(0, dur), 0.12, circular=True)
    for _ in range(int(rng.integers(1, 3))):                                    # ember settle: soft slump + charcoal tinkle
        m = N(0.5)
        es = thud(rng, m, 0.03, hi=250) + 0.5 * pk(sparse_clicks(rng, m, 45, 0.01, 0.3, 1000, 4000, skew=1.5))
        place(ev, pk(es), rng.uniform(0, dur), 0.25, circular=True)

    out = bed + ev
    out = filt(out, lambda f: r_peak(f, 450, 2.0, 0.8) * r_peak(f, 1100, 1.5, 0.8) * r_hp(f, 35, 2), circular=True)
    out = sat(pk(out) * 1.3, 1.0)          # memoryless soft-knee, so it's loop-safe; rounds off only the biggest pops
    return normalize(out, -3.0)


def church_bell_toll(rng):
    dur = 16.0
    n = N(dur)
    F = 196.0
    parts = [(0.5, 12.0, 0.5), (1.0, 8.0, 0.6), (1.2, 6.0, 0.8), (1.5, 4.0, 0.3), (2.0, 4.5, 1.0),
             (2.5, 2.4, 0.4), (2.667, 2.0, 0.25), (3.0, 1.8, 0.35), (4.0, 1.2, 0.25), (4.5, 0.9, 0.15),
             (5.33, 0.7, 0.12), (5.9, 0.5, 0.1), (6.7, 0.35, 0.08)]
    fs, ts, amps = [], [], []
    for r, tau, a in parts:
        f = F * r * (1 + rng.uniform(-0.004, 0.004))
        df = rng.uniform(0.3, 1.4)
        fs += [f, f + df]
        ts += [tau, tau * rng.uniform(0.8, 1.1)]
        amps += [a, a * rng.uniform(0.3, 0.7)]
    x = pk(modal_ir(n, fs, ts, amps, rng))
    x += 0.25 * pk(burst(rng, n, 0.015, 1000, 6000))
    hi = [F * r for r in rng.uniform(7.5, 16, 8)]
    x += 0.12 * pk(modal_ir(n, hi, rng.uniform(0.1, 0.3, 8), rng.uniform(0.3, 1, 8), rng))
    x = filt(x, lambda f: r_lp(f, 3500, 1) * r_hp(f, 60, 2))
    x = add_reverb(x, ir_village(rng), wet=0.6)
    x = x[:n] if x.ndim == 1 else x[:n, 0]
    return fade(normalize(x), 0.0, 1.5)


def distant_engine_pass(rng):
    dur = 16.0
    n = N(dur)
    t = tax(n)
    v, tc, d0 = 11.0, 8.0, 55.0
    xx = v * (t - tc)
    r = np.sqrt(d0 ** 2 + xx ** 2)
    vr = v * xx / r
    dop = 343.0 / (343.0 + vr)
    m1 = Mod(rng, dur, 0.3, periodic=False)
    rpm = 2400 + 120 * np.sin(TAU * t / 5.3) + 60 * m1(t)
    f_fire = rpm / 60.0 * 2.0 * dop
    ph = phase_cycles(f_fire)
    fl = np.floor(ph)
    idx = np.nonzero(np.diff(fl))[0]
    tr = np.zeros(n)
    cyl = np.array([1.0, 0.85, 0.95, 0.8])
    tr[idx] = cyl[np.arange(len(idx)) % 4] * (1 + 0.1 * rng.standard_normal(len(idx)))
    km = N(0.015)
    kt = tax(km)
    ker = 0.7 * np.exp(-kt / 0.003) * rng.standard_normal(km) + np.exp(-kt / 0.004) * np.sin(TAU * 180 * kt)
    exhaust = filt(conv(tr, ker)[:n], lambda f: r_bp(f, 40, 2500))
    tone = sum(np.sin(TAU * h * ph + rng.uniform(0, TAU)) / h for h in range(1, 7))
    whine = np.sin(TAU * phase_cycles(rpm / 60.0 * 7.3 * dop))
    tires = filt(white(rng, n), lambda f: r_bp(f, 250, 1200))
    src = pk(exhaust) + 0.4 * pk(tone) + 0.04 * whine + 0.2 * pk(tires)
    src = src * (d0 / r)

    def mask(tcs, f):
        rr = np.interp(tcs, t, r)[:, None]
        fc = 400 + 9000 * (d0 / rr) ** 1.3
        return r_lp(f[None, :], fc, 2) * r_hp(f[None, :], 35, 2)

    src = stft_apply(src, mask)
    src = add_reverb(src, ir_village(rng), wet=0.45)
    src = src[:n] if src.ndim == 1 else src[:n, 0]
    return fade(normalize(src), 1.5, 1.5)


# =============================================================================
# Player
# =============================================================================

def formant_noise(rng, n, env, formants, lo, hi):
    x = white(rng, n) * env
    return filt(x, lambda f: r_bp(f, lo, hi) * (0.05 + sum(g * r_res(f, fc, bw) for fc, bw, g in formants)))


def glottal(rng, n, f0, env, shimmer=0.1):
    t = tax(n)
    jit = Mod(rng, n / SR, 30, periodic=False)
    ph = phase_cycles(f0 * (1 + 0.02 * jit(t)))
    src = sum(np.sin(TAU * k * ph) / k ** 1.2 for k in range(1, 30) if k * f0 < SR * 0.45)
    return src * env * (1 + shimmer * jit(t + 1.3))


def breath_calm_loop(rng):
    L = loop_len(8.0)
    dur = L / SR
    out = np.zeros(L)
    for k in range(2):
        t0 = k * dur / 2
        di, de = rng.uniform(1.3, 1.5), rng.uniform(1.8, 2.0)
        ni, ne = N(di), N(de)
        ei = np.sin(np.pi * np.clip(tax(ni) / di, 0, 1)) ** 1.6
        ee = env_pts(ne, [(0, 0), (de * 0.22, 1.0), (de, 0)]) ** 1.4
        inh = formant_noise(rng, ni, ei, [(1000, 400, 1.0), (2600, 600, 0.6)], 400, 6000)
        exh = formant_noise(rng, ne, ee, [(600, 300, 1.0), (1500, 500, 0.7)], 200, 4500)
        place(out, 0.6 * pk(inh), t0, circular=True)
        place(out, 0.8 * pk(exh), t0 + di + 0.25, circular=True)
    return normalize(out, -1.0)


def breath_exhausted_loop(rng):
    L = loop_len(8.4)
    dur = L / SR
    out = np.zeros(L)
    cyc = dur / 6
    for k in range(6):
        t0 = k * cyc
        di, de = cyc * rng.uniform(0.3, 0.36), cyc * rng.uniform(0.42, 0.48)
        ni, ne = N(di), N(de)
        ei = np.sin(np.pi * np.clip(tax(ni) / di, 0, 1)) ** 1.2
        ee = env_pts(ne, [(0, 0), (de * 0.15, 1.0), (de, 0)]) ** 1.2
        inh = formant_noise(rng, ni, ei, [(800, 350, 1.0), (1800, 500, 0.7), (2800, 700, 0.5)], 600, 7000)
        exh = formant_noise(rng, ne, ee, [(700, 250, 1.0), (1300, 350, 0.8), (2600, 600, 0.5)], 250, 6000)
        vo = glottal(rng, ne, rng.uniform(110, 135), ee ** 1.5)
        vo = filt(vo, lambda f: r_res(f, 650, 110) + 0.7 * r_res(f, 1100, 140) + 0.4 * r_res(f, 2500, 220))
        a = rng.uniform(0.8, 1.15)
        place(out, a * 0.75 * pk(inh), t0, circular=True)
        place(out, a * (pk(exh) + 0.22 * pk(vo)), t0 + di + cyc * 0.03, circular=True)
    return normalize(out, -1.0)


def heartbeat_loop(rng):
    L = loop_len(6.0)
    dur = L / SR
    out = np.zeros(L)
    beat = dur / 8
    for k in range(8):
        t0 = k * beat
        m = N(0.25)
        tt = tax(m)
        lub = np.sin(TAU * phase_cycles(40 + 15 * np.exp(-tt / 0.03))) * env_ad(m, 0.014, 0.04, curve=2.0)
        lub = lub + 0.5 * pk(burst(rng, m, 0.03, 20, 120, attack=0.012))
        dub = np.sin(TAU * phase_cycles(np.full(m, 62.0))) * env_ad(m, 0.012, 0.03, curve=2.0)
        a = rng.uniform(0.9, 1.05)
        place(out, a * pk(lub), t0, circular=True)
        place(out, a * 0.7 * pk(dub), t0 + 0.28, circular=True)
    # gentle saturation adds 80-250 Hz harmonics so the beat reads on small speakers; low-pass keeps it soft
    out = filt(sat(pk(out) * 1.4, 1.2), lambda f: r_lp(f, 380, 2), circular=True)
    return normalize(out, -1.0)


def cloth_wool(rng):
    dur = rng.uniform(0.5, 0.9)
    n = N(dur)
    env = np.zeros(n)
    for _ in range(int(rng.integers(2, 5))):
        t0 = rng.uniform(0, dur * 0.5)
        a, d = rng.uniform(0.04, 0.12), rng.uniform(0.1, 0.25)
        env += rng.uniform(0.4, 1.0) * env_ad(n, a, d, delay=t0, curve=1.5)
    fib = Mod(rng, dur, 30, periodic=False)
    env *= np.clip(1 + 0.5 * fib(tax(n)), 0.2, 2)
    x = pk(filt(white(rng, n) * env, lambda f: r_bp(f, 350, 3200) * r_peak(f, 900, 3.0, 1.5)))
    x += 0.5 * pk(filt(white(rng, n) * env, lambda f: r_lp(f, 300, 2)))
    x += 0.08 * pk(sparse_clicks(rng, n, 60, 0, dur, 2000, 7000)) * np.clip(env / (env.max() + 1e-9), 0, 1)
    return fade(normalize(x), 0.005, 0.05)


def tinnitus_loop(rng):
    L = loop_len(8.0)
    dur = L / SR
    t = tax(L)
    f0 = qf(4700.0, dur)
    m1, m2, m3 = Mod(rng, dur, 0.5), Mod(rng, dur, 5.0), Mod(rng, dur, 0.4)
    f = f0 * (1 + 0.004 * m1(t) + 0.0015 * m2(t))
    tone = np.sin(TAU * phase_cycles(f, periodic=True)) * (1 + 0.15 * m3(t))
    band = filt(colored(rng, L, 0), lambda fr: r_res(fr, 4400, 300), circular=True, minphase=False)
    hiss = filt(colored(rng, L, 0), lambda fr: r_res(fr, 3200, 500), circular=True, minphase=False)
    out = pk(tone) + 0.32 * pk(band) + 0.1 * pk(hiss)
    return normalize(out, -3.0)


# =============================================================================
# Alarm
# =============================================================================

def whistle_blast(rng, dur, f0=3050.0):
    n = N(dur)
    t = tax(n)
    trem = Mod(rng, dur, 6, periodic=False)
    p = env_pts(n, [(0, 0), (0.03, 1.15), (0.08, 1.0), (dur - 0.06, 1.0), (dur, 0)]) * (1 + 0.05 * trem(t))
    fr = 20 + 10 * p + 2 * trem(t + 0.7)
    trill = 0.5 + 0.5 * np.cos(TAU * phase_cycles(fr))
    am = 1 - 0.75 * trill ** 1.5
    fm = f0 * (1 + 0.02 * p) - 110 * trill
    ph = phase_cycles(fm)
    tone = np.sin(TAU * ph) + 0.12 * np.sin(2 * TAU * ph)
    noise = filt(white(rng, n), lambda f: r_bp(f, f0 * 0.6, f0 * 1.6))
    return (pk(tone) * am + 0.15 * pk(noise) * (0.5 + 0.5 * am)) * p


def whistle_trill(rng, pattern):
    blasts = [whistle_blast(rng, d, rng.uniform(2950, 3150)) for d, _ in pattern]
    total = sum(d + g for d, g in pattern) + 0.1
    x = np.zeros(N(total))
    t = 0.0
    for b, (d, g) in zip(blasts, pattern):
        place(x, b, t)
        t += d + g
    return fade(normalize(x), 0, 0.05)


def siren_hand_crank(rng):
    dur = 12.5
    n = N(dur)
    t = tax(n)
    fmax = rng.uniform(520, 560)
    up = fmax * (1 - np.exp(-t / 1.5))
    hold_f = fmax
    down = hold_f * np.exp(-(t - 8.0) / 2.2)
    f = np.where(t < 8.0, up, down)
    f = np.maximum(f, 40.0)
    crank = 1 + 0.03 * np.sin(TAU * phase_cycles(np.full(n, 1.7))) + 0.01 * Mod(rng, dur, 1.0, periodic=False)(t)
    f = f * crank
    amp = np.clip(f / fmax, 0, 1.1) ** 1.5
    ph = phase_cycles(f)
    ph2 = phase_cycles(f * 1.003)
    D = 0.4
    x = np.zeros(n)
    for k in range(1, 40):
        a = abs(math.sin(math.pi * k * D)) / k
        ok = (k * f) < SR * 0.45
        x += ok * a * (np.sin(TAU * k * ph) + 0.5 * np.sin(TAU * k * ph2))
    x = filt(x, lambda fr: r_peak(fr, 1400, 6.0, 1.5) * r_hp(fr, 80, 2) * r_lp(fr, 6000, 2))
    air = filt(white(rng, n), lambda fr: r_bp(fr, 800, 6000)) * amp
    x = pk(x) * amp + 0.08 * pk(air)
    return fade(normalize(x), 0.02, 0.4)


def bark(rng, dur, f0p):
    n = N(dur)
    t = tax(n)
    contour = np.interp(t, [0, 0.02, dur], [0.8, 1.0, 0.62]) * f0p
    jit = Mod(rng, dur, 300, periodic=False)
    f = contour * (1 + 0.04 * jit(t))
    ph = phase_cycles(f)
    src = sum(np.sin(TAU * k * ph + rng.uniform(0, 0.4)) / k ** 1.0 for k in range(1, 22) if k * f0p < SR * 0.45)
    src = src * (1 + 0.45 * np.sin(np.pi * ph))
    sh = Mod(rng, dur, 150, periodic=False)
    src = src * (1 + 0.2 * sh(t))
    asp = filt(white(rng, n), lambda fr: r_hp(fr, 1000, 2))
    env = np.interp(t, [0, 0.006, 0.4 * dur, dur], [0, 1, 0.9, 0]) ** 1.3
    F = [(rng.uniform(550, 700), 130, 1.0), (rng.uniform(1250, 1500), 170, 0.7), (rng.uniform(2300, 2700), 230, 0.45), (3500, 320, 0.25)]
    y = filt(pk(src) + 0.35 * pk(asp), lambda fr: 0.04 + sum(g * r_res(fr, fc, bw) for fc, bw, g in F))
    y = y * env
    y[:N(0.02)] += 0.3 * pk(burst(rng, N(0.02), 0.004, 400, 3000))
    return pk(y)


def dog_bark_distant(rng, times):
    f0p = rng.uniform(300, 420)
    total = times[-1] + 3.0
    x = np.zeros(N(total))
    for t0 in times:
        place(x, bark(rng, rng.uniform(0.13, 0.22), f0p * rng.uniform(0.92, 1.08)), t0, rng.uniform(0.75, 1.0))
    x = filt(x, lambda f: r_lp(f, 2200, 2) * r_hp(f, 150, 2))
    x = add_reverb(x, ir_village(rng), wet=0.55)
    x = x[:N(total)] if x.ndim == 1 else x[:N(total), 0]
    return fade(normalize(x), 0, 0.6)


# =============================================================================
# Music
# =============================================================================

def circ_window(t, center, half, dur):
    d = (t - center + dur / 2) % dur - dur / 2
    return np.where(np.abs(d) < half, 0.5 + 0.5 * np.cos(np.pi * d / half), 0.0)


def drone_dread_loop(rng):
    L = loop_len(120.0)
    dur = L / SR
    t = tax(L)
    out = np.zeros((L, 2))
    swell = 0.6 + 0.4 * np.tanh(Mod(rng, dur, 0.03)(t))
    sub = (0.5 * np.sin(TAU * qf(36.71, dur) * t) + 0.35 * np.sin(TAU * qf(36.95, dur) * t + 1.0)
           + 0.25 * np.sin(TAU * qf(73.42, dur) * t + 2.0))
    rough = 0.18 * (np.sin(TAU * qf(73.42, dur) * t + 0.5) + np.sin(TAU * qf(77.78, dur) * t))
    out += ((sub + rough) * swell)[:, None] * np.array([1.0, 1.0])

    chords = [[73.42, 110.0, 155.56, 207.65], [69.30, 98.0, 146.83, 207.65], [73.42, 87.31, 123.47, 130.81]]
    tab = saw_table(60, rolloff=1.15)
    strings = np.zeros((L, 2))
    for ci, chord in enumerate(chords):
        win = circ_window(t, ci * dur / 3 + dur / 6, dur * 0.36, dur)
        for note in chord:
            vm = Mod(rng, dur, 0.08)
            vamp = np.clip(0.55 + 0.45 * vm(t), 0, 1.2)
            p = rng.uniform(-0.6, 0.6)
            for cents in (-5, 0, 4):
                f = qf(note * 2 ** (cents / 1200), dur)
                vib = 0.0012 * np.sin(TAU * qf(rng.uniform(4.2, 5.2), dur) * t + rng.uniform(0, TAU))
                ph = phase_cycles(f * (1 + vib), periodic=True) + rng.uniform(0, 1)
                v = table_osc(tab, ph) * win * vamp
                th = (p + 1) * np.pi / 4
                strings[:, 0] += v * math.cos(th)
                strings[:, 1] += v * math.sin(th)
    strings = filt(strings, lambda f: r_lp(f, 1500, 2) * r_peak(f, 500, 3.0, 1.5) * r_hp(f, 50, 2), circular=True)
    out += 0.6 * pk(strings) * np.abs(out).max()

    scrapes = np.zeros((L, 2))
    for te in [14.0, 41.0, 73.0, 101.0]:
        d = rng.uniform(4.0, 7.0)
        m = N(d + 3.5)
        tt = tax(m)
        bow = white(rng, m) * env_pts(m, [(0, 0), (1.2, 1), (d - 1.5, 0.8), (d, 0)])
        bow *= 1 + 0.5 * np.sin(TAU * phase_cycles(rng.uniform(40, 90) * (1 + 0.1 * Mod(rng, d + 3.5, 2, periodic=False)(tt))))
        bow = filt(bow, lambda f: r_bp(f, 300, 6000))
        f1 = rng.uniform(180, 320)
        ratios = [1, 1.59, 2.14, 2.30, 2.65, 2.92, 3.16, 3.50, 4.15, 4.6]
        mir = modal_ir(N(3.0), [f1 * r for r in ratios], rng.uniform(0.8, 2.5, len(ratios)), rng.uniform(0.3, 1.0, len(ratios)), rng)
        sc = conv(bow, mir)[:m]
        place(scrapes, pan(pk(sc), rng.uniform(-0.8, 0.8)), te, 1.0, circular=True)
    out += 0.35 * scrapes / (np.abs(scrapes).max() + 1e-12) * np.abs(out).max()

    boom = np.zeros(L)
    bm = N(4.0)
    bt = tax(bm)
    b = pk(burst(rng, bm, 0.4, 20, 200, attack=0.02)) + 0.8 * np.sin(TAU * 40 * bt) * env_ad(bm, 0.02, 0.5)
    place(boom, pk(b), 62.0, circular=True)
    out += 0.3 * np.stack([boom, boom], 1) * np.abs(out).max()

    air = filt(np.stack([colored(rng, L, 0), colored(rng, L, 0)], 1), lambda f: r_hp(f, 5000, 2), circular=True)
    out += 0.015 * pk(air) * np.abs(out).max() * (1 + 0.5 * Mod(rng, dur, 0.05)(t))[:, None]

    ir = ir_hall(rng)
    wet = conv(out, ir, circular=True)
    out = out + 0.45 * pk(wet) * np.abs(out).max()
    out = sat(pk(out) * 1.2, 1.1)
    return normalize(out, -3.0)


def stinger_rise(rng):
    dur = 7.0
    n = N(dur)
    t = tax(n)
    tab = saw_table(40, rolloff=1.0)
    hit_t = 3.2
    x = np.zeros((n, 2))
    for v in range(8):
        f0 = rng.uniform(200, 400)
        semis = rng.uniform(7, 12)
        speed = rng.uniform(0.8, 1.2)
        prog = np.clip(t / (hit_t * speed), 0, 1) ** 1.6
        f = f0 * 2 ** (semis * prog / 12)
        ph = phase_cycles(f) + rng.uniform(0, 1)
        trem_r = 9 + 5 * prog
        trem = 1 - 0.5 * (0.5 + 0.5 * np.sin(TAU * phase_cycles(trem_r)))
        env = np.clip(t / hit_t, 0, 1) ** 2.2 * (t < hit_t + 0.05)
        sig = table_osc(tab, ph) * trem * env
        x += pan(sig, rng.uniform(-0.8, 0.8))

    def mask(tc, f):
        fc = 800 + 6200 * np.clip(tc / hit_t, 0, 1) ** 2
        return r_lp(f[None, :], fc[:, None], 2)

    x = np.stack([stft_apply(x[:, c], mask) for c in range(2)], 1)
    riser = white(rng, n) * np.clip(t / hit_t, 0, 1) ** 3 * (t < hit_t)

    def rmask(tc, f):
        fc = 600 * 2 ** (4 * np.clip(tc / hit_t, 0, 1))
        return r_res(f[None, :], fc[:, None], fc[:, None] * 0.6)

    riser = stft_apply(riser, rmask)
    x += 0.35 * pan(pk(riser), 0.0) * 1.4142
    hit = np.zeros(n)
    place(hit, thud(rng, N(3.0), 0.5, hi=180, f0=42), hit_t)
    place(hit, metal_hit(rng, 2.5, rng.uniform(300, 420), n_modes=7, tau=(1.2, 0.2), click=0.3), hit_t, 0.6)
    x = pk(x) + 0.9 * np.stack([pk(hit), pk(hit)], 1)
    x = add_reverb(x, ir_hall(rng, 5.0), wet=0.5)[:n]
    x = sat(pk(x) * 1.4, 1.3)
    return fade(normalize(x), 0.01, 0.8)


def stinger_slam(rng):
    dur = 6.0
    n = N(dur)
    t = tax(n)
    hit_t = 1.0
    swell = np.zeros(N(1.6))
    swell_src = filt(white(rng, len(swell)) * env_ad(len(swell), 0.0, 0.25), lambda f: r_bp(f, 400, 8000))
    swell = pk(add_reverb(swell_src, ir_hall(rng, 1.6), wet=1.0, dry=0.0)[:len(swell), 0])
    swell = swell[::-1][-N(hit_t):]
    x = np.zeros((n, 2))
    place(x, swell * np.linspace(0, 1, len(swell)) ** 2, 0.0, 0.7)
    tab = saw_table(60, rolloff=0.9)
    low = np.zeros(n)
    for f0 in [36.71, 38.89, 55.0, 58.27]:
        ph = phase_cycles(np.full(n, f0 * rng.uniform(0.998, 1.002))) + rng.uniform(0, 1)
        low += table_osc(tab, ph)
    low *= env_ad(n, 0.04, 1.6, delay=hit_t)
    low = sat(pk(low) * 3.0, 1.5)
    low = filt(low, lambda f: r_lp(f, 2200, 2))
    x += 0.9 * np.stack([low, low], 1)
    scr_f = 3000 * 2 ** (-1.5 * np.clip((t - hit_t) / 4.0, 0, 1))
    scr_ph = phase_cycles(scr_f * (1 + 0.01 * Mod(rng, dur, 12, periodic=False)(t)))
    scr = table_osc(saw_table(8), scr_ph) * env_ad(n, 0.05, 1.4, delay=hit_t)
    x += 0.25 * pan(pk(filt(scr, lambda f: r_bp(f, 1500, 9000))), 0.35) * 1.4142
    hit = np.zeros(n)
    place(hit, thud(rng, N(3.0), 0.5, hi=160, f0=38), hit_t)
    place(hit, metal_hit(rng, 3.0, rng.uniform(250, 350), n_modes=7, tau=(1.5, 0.25), click=0.4), hit_t, 0.7)
    x += np.stack([pk(hit), pk(hit)], 1)
    x = add_reverb(x, ir_hall(rng, 5.0), wet=0.55)[:n]
    x = sat(pk(x) * 1.4, 1.3)
    return fade(normalize(x), 0.0, 0.8)


# =============================================================================
# Registry
# =============================================================================

REG = []


def reg(path, fn, cat, desc, loop=False, gain=0.0, priority=9):
    REG.append(dict(path=path, fn=fn, cat=cat, desc=desc, loop=loop, gain=gain, priority=priority))


def build_registry():
    for i in range(1, 5):
        reg(f"weapons/p38_shot_{i:02d}.wav", p38_shot, "weapons", "Walther P38 9 mm shot as heard by the shooter: blast, body, slide clack (dry)", gain=0.0, priority=1)
    for i in range(1, 3):
        reg(f"weapons/tail_street_{i:02d}.wav", lambda r: shot_tail(r, "street"), "weapons",
            "Gunshot tail in a narrow granite street: facade slapbacks, flutter echo, rolling far reflections (no direct sound)", gain=-8.0, priority=1)
    reg("weapons/tail_interior_01.wav", lambda r: shot_tail(r, "interior"), "weapons",
        "Gunshot tail in a small stone room: dense, boomy reflections (no direct sound)", gain=-4.0, priority=1)
    reg("weapons/p38_dryfire.wav", p38_dryfire, "weapons", "P38 trigger pull on an empty chamber: sear click + hammer fall", gain=-12, priority=1)
    reg("weapons/p38_slide_back.wav", p38_slide_back, "weapons", "P38 slide racked back by hand: scrape, hammer cocks, slide stop", gain=-12, priority=1)
    reg("weapons/p38_slide_forward.wav", p38_slide_forward, "weapons", "P38 slide released forward: slams into battery", gain=-10, priority=1)
    reg("weapons/p38_mag_out.wav", p38_mag_out, "weapons", "P38 heel-release magazine pulled out", gain=-14, priority=1)
    reg("weapons/p38_mag_in.wav", p38_mag_in, "weapons", "P38 magazine inserted and seated", gain=-12, priority=1)
    reg("weapons/p38_decocker.wav", p38_decocker, "weapons", "P38 safety/decocker lever: hammer drops safely", gain=-13, priority=1)
    for i in range(1, 5):
        reg(f"weapons/casing_cobble_{i:02d}.wav", casing_cobble, "weapons", "9 mm brass casing bouncing on cobbles", gain=-18, priority=1)

    for i in range(1, 5):
        reg(f"impacts/impact_stone_{i:02d}.wav", impact_stone, "impacts", "Bullet strike on granite: crack, chips, grit", gain=-6, priority=2)
    for i in range(1, 4):
        reg(f"impacts/impact_wood_{i:02d}.wav", impact_wood, "impacts", "Bullet strike on wood: thud and splinter", gain=-6, priority=2)
    for i in range(1, 4):
        reg(f"impacts/impact_dirt_{i:02d}.wav", impact_dirt, "impacts", "Bullet strike on earth/mud: thump and spray", gain=-8, priority=2)
    for i in range(1, 4):
        reg(f"impacts/ricochet_{i:02d}.wav", ricochet, "impacts", "Ricochet off stone: strike then tumbling whine", gain=-6, priority=2)

    surfaces = {"cobble": step_cobble, "mud": step_mud, "gravel": step_gravel, "grass": step_grass, "wood": step_wood}
    for s, fn in surfaces.items():
        for i in range(1, 7):
            if s == "wood" and i == 6:
                reg(f"footsteps/{s}_walk_{i:02d}.wav", lambda r: step_wood(r, False, creak=True), "footsteps",
                    "Leather sole on floorboards, walking, with board creak", gain=-16, priority=3)
            else:
                reg(f"footsteps/{s}_walk_{i:02d}.wav", (lambda fn: (lambda r: fn(r, False)))(fn), "footsteps",
                    f"Player leather-soled shoe on {s}, walking", gain=-16, priority=3)
        for i in range(1, 5):
            reg(f"footsteps/{s}_run_{i:02d}.wav", (lambda fn: (lambda r: fn(r, True)))(fn), "footsteps",
                f"Player leather-soled shoe on {s}, running", gain=-11, priority=3)
    for i in range(1, 7):
        reg(f"footsteps/npc_hobnail_cobble_{i:02d}.wav", step_hobnail, "footsteps",
            "German hobnailed jackboot on cobbles: heel iron clack and studs", gain=-12, priority=3)

    reg("ambience/wind_gusts_loop.wav", wind_gusts_loop, "ambience", "Winter coastal wind, slow gusts with faint whistles (stereo loop)", loop=True, gain=-18, priority=4)
    reg("ambience/rain_light_loop.wav", rain_light_loop, "ambience", "Light drizzle on stone, slate and puddles (stereo loop)", loop=True, gain=-20, priority=4)
    reg("ambience/drips_loop.wav", drips_loop, "ambience", "Eaves and gutters dripping into puddles in a stone street (stereo loop)", loop=True, gain=-22, priority=4)
    reg("ambience/distant_sea_loop.wav", distant_sea_loop, "ambience", "Distant surf below the cliffs, slow wave cycle (stereo loop)", loop=True, gain=-20, priority=4)
    reg("ambience/fire_crackle_loop.wav", fire_crackle_loop, "ambience",
        "Small wood fire in an iron brazier drum: low roar, irregular crackles and pops, sap hiss, ember settle (mono loop)",
        loop=True, gain=-14, priority=4)
    reg("ambience/church_bell_toll.wav", church_bell_toll, "ambience", "Single toll of a village church bell, distant, long decay", gain=-10, priority=4)
    reg("ambience/distant_engine_pass_01.wav", distant_engine_pass, "ambience", "Air-cooled 4-cylinder vehicle passing at ~55 m (Doppler, air absorption)", gain=-14, priority=4)

    reg("player/breath_calm_loop.wav", breath_calm_loop, "player", "Calm nasal breathing, 15/min", loop=True, gain=-26, priority=5)
    reg("player/breath_exhausted_loop.wav", breath_exhausted_loop, "player", "Heavy exhausted mouth breathing after a sprint", loop=True, gain=-16, priority=5)
    reg("player/heartbeat_loop.wav", heartbeat_loop, "player", "Heartbeat at 80 bpm (scale pitch for rate)", loop=True, gain=-14, priority=5)
    for i in range(1, 5):
        reg(f"player/cloth_wool_move_{i:02d}.wav", cloth_wool, "player", "Heavy wool overcoat rustle", gain=-22, priority=5)
    reg("player/tinnitus_loop.wav", tinnitus_loop, "player", "Post-gunshot tinnitus: ~4.7 kHz unsteady ring + narrow noise band", loop=True, gain=-12, priority=5)

    reg("alarm/whistle_trill_01.wav", lambda r: whistle_trill(r, [(1.6, 0.0)]), "alarm", "Pea whistle, one long trilled blast", gain=-6, priority=6)
    reg("alarm/whistle_trill_02.wav", lambda r: whistle_trill(r, [(0.35, 0.12), (0.35, 0.12), (1.2, 0.0)]), "alarm", "Pea whistle, two short blasts and one long", gain=-6, priority=6)
    reg("alarm/siren_hand_crank.wav", siren_hand_crank, "alarm", "Hand-cranked siren: wind up, hold, wind down", gain=-6, priority=6)
    for i, times in enumerate([[0.0, 0.45], [0.0], [0.0, 0.35, 0.8], [0.0, 0.5, 0.85, 1.6]], 1):
        reg(f"alarm/dog_bark_distant_{i:02d}.wav", (lambda tm: (lambda r: dog_bark_distant(r, tm)))(times), "alarm",
            "Large dog barking at a distance (formant synthesis, experimental)", gain=-8, priority=6)

    reg("music/drone_dread_loop.wav", drone_dread_loop, "music", "Low evolving dread drone: dissonant clusters, distant metal scrapes (stereo loop)", loop=True, gain=-14, priority=7)
    reg("music/stinger_terror_01.wav", stinger_rise, "music", "Terror stinger: rising tremolo cluster to a hit, then reverb tail", gain=-10, priority=7)
    reg("music/stinger_terror_02.wav", stinger_slam, "music", "Terror stinger: reverse swell into low brass-like slam and diving screech", gain=-10, priority=7)


# =============================================================================
# Previews (spectrogram montages), no external libraries
# =============================================================================

FONT = {
    "A": [".#.", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."], "C": [".##", "#..", "#..", "#..", ".##"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."], "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": [".##", "#..", "#.#", "#.#", ".##"], "H": ["#.#", "#.#", "###", "#.#", "#.#"], "I": ["###", ".#.", ".#.", ".#.", "###"],
    "J": ["..#", "..#", "..#", "#.#", ".#."], "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"], "O": [".#.", "#.#", "#.#", "#.#", ".#."],
    "P": ["##.", "#.#", "##.", "#..", "#.."], "Q": [".#.", "#.#", "#.#", "##.", ".##"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."], "T": ["###", ".#.", ".#.", ".#.", ".#."], "U": ["#.#", "#.#", "#.#", "#.#", "###"],
    "V": ["#.#", "#.#", "#.#", "#.#", ".#."], "W": ["#.#", "#.#", "###", "###", "#.#"], "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."], "Z": ["###", "..#", ".#.", "#..", "###"], "0": ["###", "#.#", "#.#", "#.#", "###"],
    "1": [".#.", "##.", ".#.", ".#.", "###"], "2": ["##.", "..#", ".#.", "#..", "###"], "3": ["##.", "..#", ".#.", "..#", "##."],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "##.", "..#", "##."], "6": [".##", "#..", "###", "#.#", "###"],
    "7": ["###", "..#", ".#.", ".#.", ".#."], "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "##."],
    "_": ["...", "...", "...", "...", "###"], ".": ["...", "...", "...", "...", ".#."], "-": ["...", "...", "###", "...", "..."],
    " ": ["...", "...", "...", "...", "..."], "/": ["..#", "..#", ".#.", "#..", "#.."],
}


def draw_text(img, x, y, s, color=(255, 255, 255), scale=2):
    for ch in s.upper():
        g = FONT.get(ch, FONT[" "])
        for r, row in enumerate(g):
            for c, px in enumerate(row):
                if px == "#":
                    img[y + r * scale:y + (r + 1) * scale, x + c * scale:x + (c + 1) * scale] = color
        x += 4 * scale
    return img


CMAP = np.array([[0, 0, 4], [40, 11, 84], [101, 21, 110], [159, 42, 99], [212, 72, 66], [245, 125, 21], [250, 193, 39], [252, 255, 164]], float)


def colorize(v):
    v = np.clip(v, 0, 1) * (len(CMAP) - 1)
    i = np.floor(v).astype(int)
    i = np.clip(i, 0, len(CMAP) - 2)
    fr = (v - i)[..., None]
    return (CMAP[i] * (1 - fr) + CMAP[i + 1] * fr).astype(np.uint8)


def spec_image(x, width, height=150, wave_h=50, fmin=30.0, fmax=20000.0):
    if x.ndim == 2:
        x = x.mean(1)
    n = len(x)
    nfft = 2048
    hop = max(32, int(math.ceil((n + nfft) / width)))
    xp = np.concatenate([np.zeros(nfft // 2), x, np.zeros(nfft)])
    nfr = max(1, (len(xp) - nfft) // hop)
    idx = np.arange(nfr)[:, None] * hop + np.arange(nfft)[None, :]
    S = np.abs(np.fft.rfft(xp[idx] * np.hanning(nfft), axis=1))
    S = 20 * np.log10(S + 1e-9)
    S -= S.max()
    f = freqs_for(nfft)
    rows = np.geomspace(fmax, fmin, height)
    bins = np.clip(np.searchsorted(f, rows), 1, len(f) - 1)
    img_s = colorize((S[:, bins].T + 90) / 90)
    w = img_s.shape[1]
    wave = np.zeros((wave_h, w, 3), np.uint8)
    for c in range(w):
        seg = x[c * hop: c * hop + hop]
        if len(seg) == 0:
            continue
        lo, hi = seg.min(), seg.max()
        y0 = int((1 - (hi + 1) / 2) * (wave_h - 1))
        y1 = int((1 - (lo + 1) / 2) * (wave_h - 1))
        wave[max(0, y0):min(wave_h, y1 + 1), c] = (120, 200, 255)
    wave[wave_h // 2, :, :] = np.maximum(wave[wave_h // 2, :, :], 40)
    return np.concatenate([wave, img_s], 0)


def write_png(path, img):
    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def montage(items, path, max_secs=None, px_per_sec=500, max_w=1400):
    tiles = []
    for name, x in items:
        if max_secs:
            x = x[:N(max_secs)]
        w = int(min(max_w, max(200, len(x) / SR * px_per_sec)))
        tile = spec_image(x, w)
        hdr = np.zeros((16, tile.shape[1], 3), np.uint8)
        draw_text(hdr, 2, 3, f"{name}  {len(x) / SR:.2f}S", scale=2)
        tiles.append(np.concatenate([hdr, tile], 0))
    W = max(t.shape[1] for t in tiles)
    rows = [np.concatenate([t, np.zeros((t.shape[0], W - t.shape[1], 3), np.uint8)], 1) for t in tiles]
    sep = np.full((4, W, 3), 60, np.uint8)
    img = np.concatenate([r for t in rows for r in (t, sep)], 0)
    write_png(path, img)


# =============================================================================
# Main
# =============================================================================

def env_metrics(x):
    """Peak dBFS, and when the 5 ms RMS envelope first falls 20/40 dB below its maximum (after the peak)."""
    m = np.abs(x) if x.ndim == 1 else np.abs(x).max(1)
    w = N(0.005)
    r = np.sqrt(np.convolve(m * m, np.ones(w) / w, mode="same"))
    i = int(np.argmax(r))
    rd = 20 * np.log10(r / (r[i] + 1e-12) + 1e-12)
    def drop(d):
        k = np.nonzero(rd[i:] < -d)[0]
        return f"{(i + k[0]) / SR * 1000:5.0f}ms" if len(k) else "  never"
    return f"pk={20 * np.log10(m.max() + 1e-12):5.1f}dB  -20@{drop(20)} -40@{drop(40)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="*", help="glob over relative paths, e.g. 'weapons/*'")
    ap.add_argument("--no-previews", action="store_true")
    args = ap.parse_args()
    build_registry()
    manifest_path = OUT / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = {e["file"]: e for e in json.loads(manifest_path.read_text())["sounds"]}
        except Exception:
            manifest = {}
    built = {}
    t_all = time.time()
    for e in REG:
        if not fnmatch.fnmatch(e["path"], args.only):
            continue
        t0 = time.time()
        rng = rng_for(e["path"])
        x = e["fn"](rng)
        x = np.asarray(x, float)
        if not np.all(np.isfinite(x)):
            raise RuntimeError(f"non-finite samples in {e['path']}")
        p = OUT / e["path"]
        write_wav(p, x, loop=e["loop"], name=e["path"])
        built[e["path"]] = x
        ch = 1 if x.ndim == 1 else 2
        manifest[e["path"]] = dict(file=e["path"], category=e["cat"], duration_s=round(len(x) / SR, 3), channels=ch,
                                   loop=e["loop"], sample_rate=SR, suggested_gain_db=e["gain"], description=e["desc"])
        print(f"  {e['path']:<44} {len(x) / SR:6.2f}s  ch={ch}  {time.time() - t0:5.1f}s  {env_metrics(x)}", flush=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(dict(
        generator="tools/audio/build_audio.py", sample_rate=SR, bit_depth=16,
        notes="Positional sounds are mono and dry; suggested_gain_db is a mixing hint relative to a 0 dB gunshot. Loops carry a WAV smpl chunk.",
        sounds=sorted(manifest.values(), key=lambda d: d["file"])), indent=1))
    print(f"built {len(built)} files in {time.time() - t_all:.1f}s")

    if not args.no_previews and built:
        groups = {}
        for k, x in built.items():
            groups.setdefault(k.split("/")[0], []).append((Path(k).stem, x))
        for g, items in groups.items():
            if g in ("ambience", "music"):
                montage(items, PREV / f"{g}.png", max_secs=30, px_per_sec=40)
            elif g == "footsteps":
                for s in ["cobble", "mud", "gravel", "grass", "wood", "npc"]:
                    sub = [it for it in items if it[0].startswith(s)]
                    if sub:
                        montage(sub, PREV / f"footsteps_{s}.png", px_per_sec=1600)
            else:
                montage(items, PREV / f"{g}.png", px_per_sec=900 if g in ("weapons", "impacts") else 250)
        print("previews written to", PREV)


if __name__ == "__main__":
    main()
