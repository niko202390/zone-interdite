"""Synthesise 'fuzzy' non-speech voice babble from scratch: language-flavoured gibberish that sounds like
speech from a distance, through rain and fog, without being words. Subtitles carry the meaning.

Source-filter model:
  voice source  a Rosenberg glottal pulse train generated period by period, with jitter (period noise),
                shimmer (amplitude noise), breath noise gated to the open phase, and, for shouts, a pressed,
                fast-closing pulse plus period-to-period roughness (strain).
  tract filter  a cascade of five formant resonators per 3 ms frame (frequency domain), with nasal
                pole/zero, gliding between consonant loci and vowel targets so syllables have real
                CV/VC transitions.
  consonants    sample-accurate plosive bursts by place of articulation, aspiration through the formants,
                fricative noise with its own spectrum, nasals, liquids, a uvular trill for de/fr 'r'.
Each language has its own vowel set, consonants, syllable rhythm and intonation:
  de  hard plosives, ach/ich fricatives, clipped syllables, falling statements
  fr  nasal vowels, smooth even rhythm, rising phrase ends
  en  diphthong-ish glides, stress-timed rhythm
Styles: talk (conversational) and shout (male F0 about 180-260 Hz, raised F1, pressed voice and strain,
longer stressed vowels, gaps for breath, a slapback and short outdoor tail off the house fronts).

Usage: python -I tools/audio/build_babble.py
Writes game/assets/audio/voice/<lang>_<style>[_f]_<s|m|l>_NN.wav, deterministic.
"""
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_audio as B   # noqa: E402  (filters, reverb IRs, limiter)

SR = 44100
NFFT = 1024
HOP = 128
FRIC_GAIN = 0.12    # fricative noise relative to the voiced peak
BURST_GAIN = 0.5
GR_MAX = -99.0      # largest limiter gain reduction in this run (dB), reported at the end
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "game", "assets", "audio", "voice")

# Vowel formants (F1, F2, F3) for an adult male voice, Hz. Diphthongs glide to a second target.
V = {
    "a": (750, 1250, 2500), "e": (450, 1900, 2550), "i": (280, 2250, 2900), "o": (450, 850, 2400),
    "u": (300, 750, 2300), "oe": (450, 1500, 2400), "ue": (280, 1700, 2200), "schwa": (500, 1450, 2450),
    "E": (580, 1800, 2500), "ae": (660, 1700, 2450), "I": (400, 1950, 2550), "A~": (650, 1050, 2500),
    "O~": (480, 800, 2400), "E~": (600, 1600, 2500), "ai": (700, 1500, 2500), "au": (650, 1000, 2400),
}
DIPH = {"ai": (350, 2100, 2700), "au": (380, 850, 2300)}
NASAL = {"A~", "O~", "E~"}

LANG = {
    "de": {"vowels": ["a", "e", "i", "o", "u", "oe", "ue", "schwa", "E", "ai", "au", "a", "e", "schwa"],
           "cons": ["k", "t", "p", "sh", "x", "ts", "s", "f", "n", "m", "l", "r", "c", "h", "g", "d", "b"],
           "syl": (0.15, 0.21), "coda": 0.55, "contour": "fall", "r": "uvular"},
    "fr": {"vowels": ["a", "e", "i", "o", "u", "E", "schwa", "oe", "A~", "O~", "E~", "a", "e"],
           "cons": ["s", "zh", "sh", "t", "k", "p", "m", "n", "l", "r", "v", "d", "b"],
           "syl": (0.12, 0.165), "coda": 0.18, "contour": "rise", "r": "uvular"},
    "en": {"vowels": ["ae", "E", "I", "a", "o", "u", "schwa", "ai", "au", "e", "i"],
           "cons": ["t", "d", "k", "s", "h", "w", "r", "l", "n", "m", "th", "p", "b", "f"],
           "syl": (0.13, 0.24), "coda": 0.45, "contour": "mixed", "r": "approx"},
}

# Consonants: kind, place, noise centre Hz, noise width Hz, duration s, noise level.
C = {
    "k": ("plosive", "vel", 2600, 1400, 0.075, 0.0), "t": ("plosive", "alv", 4500, 2800, 0.07, 0.0),
    "p": ("plosive", "lab", 900, 1200, 0.075, 0.0), "g": ("vplosive", "vel", 2400, 1400, 0.06, 0.0),
    "d": ("vplosive", "alv", 4000, 2400, 0.055, 0.0), "b": ("vplosive", "lab", 800, 1000, 0.06, 0.0),
    "s": ("fric", "alv", 6500, 2600, 0.095, 0.5), "sh": ("fric", "post", 3200, 1800, 0.1, 0.55),
    "x": ("fric", "vel", 1600, 1000, 0.1, 0.45), "c": ("fric", "post", 4000, 1800, 0.09, 0.45),
    "f": ("fric", "lab", 5000, 5000, 0.085, 0.2), "th": ("fric", "alv", 5500, 5000, 0.075, 0.15),
    "h": ("asp", "glot", 0, 0, 0.065, 0.35), "ts": ("affric", "alv", 6000, 2600, 0.1, 0.5),
    "zh": ("vfric", "post", 3200, 1800, 0.085, 0.3), "v": ("vfric", "lab", 4500, 4000, 0.07, 0.12),
    "n": ("nasal", "alv", 0, 0, 0.065, 0.0), "m": ("nasal", "lab", 0, 0, 0.07, 0.0),
    "l": ("liquid", "alv", 0, 0, 0.055, 0.0), "r": ("liquid", "uvu", 1300, 1200, 0.06, 0.0),
    "w": ("liquid", "lab", 0, 0, 0.06, 0.0),
}
# F2 locus per place of articulation: formants start/finish near here at CV/VC boundaries.
LOCUS = {"lab": 850.0, "alv": 1750.0, "post": 2100.0, "vel": 1950.0, "uvu": 1250.0, "glot": None}
LIQ_F = {"l": (360, 1150, 2700), "r_uvular": (480, 1250, 2350), "r_approx": (350, 1200, 1650), "w": (320, 750, 2300)}


def piece(track, t0, dur, level, rise, fall):
    """Write a smooth trapezoid envelope into a per-sample track (max-combined)."""
    n = len(track)
    a, b = int(t0 * SR), int((t0 + dur) * SR)
    if b <= a or a >= n:
        return
    b = min(b, n)
    m = b - a
    e = np.full(m, level)
    r, f = min(m // 2, max(1, int(rise * SR))), min(m // 2, max(1, int(fall * SR)))
    e[:r] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, r))
    e[m - f:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, f))
    track[a:b] = np.maximum(track[a:b], e)


def plan(rng, lang, seconds, style, female):
    """Timeline of segments (t0, dur, kind, ...) for one utterance, plus the speaker's F0 targets."""
    L = LANG[lang]
    shout = style == "shout"
    scale = (1.17 if female else 1.0) * rng.uniform(0.95, 1.05)       # vocal tract length per speaker
    segs, f0pts = [], []
    if female:
        base = rng.uniform(190, 225)
    elif shout:
        base = rng.uniform(205, 240)
    else:
        base = rng.uniform(102, 125)
    t = 0.04
    if shout and rng.random() < 0.6:                                     # a snatched breath before shouting
        d = rng.uniform(0.12, 0.2)
        segs.append(dict(t0=t, dur=d, kind="inhale"))
        t += d + rng.uniform(0.04, 0.08)
    phrase_start = t
    words = 0
    while t < seconds or words == 0:
        nsyl = int(rng.choice([1, 2, 2, 3])) if shout else int(rng.integers(1, 4))
        word_peak = base * (rng.uniform(1.05, 1.18) if shout else rng.uniform(1.0, 1.12))
        for s in range(nsyl):
            stressed = (s == 0 and rng.random() < 0.7) or nsyl == 1
            if rng.random() < 0.8:
                c = L["cons"][rng.integers(len(L["cons"]))]
                d = C[c][4] * rng.uniform(0.8, 1.2)
                segs.append(dict(t0=t, dur=d, kind="cons", c=c))
                t += d
            v = L["vowels"][rng.integers(len(L["vowels"]))]
            lo, hi = L["syl"]
            vd = rng.uniform(lo, hi) * (1.35 if stressed else 0.9)
            if shout:
                vd *= rng.uniform(1.2, 1.6) if stressed else 1.1
            F = [x * scale for x in V[v]]
            F2 = [x * scale for x in DIPH[v]] if v in DIPH else None
            if shout:   # mouth wide open: F1 up, F2 up a little
                F = [F[0] * 1.22, F[1] * 1.05, F[2]]
                F2 = [F2[0] * 1.2, F2[1] * 1.05, F2[2]] if F2 else None
            lvl = (1.0 if stressed else rng.uniform(0.6, 0.8))
            segs.append(dict(t0=t, dur=vd, kind="vowel", F=F, F2=F2, nasal=v in NASAL, level=lvl, stressed=stressed))
            # pitch: stressed vowels carry the word's peak; declination across the phrase
            decl = 1.0 - (0.18 if shout else 0.12) * min(1.0, (t - phrase_start) / max(seconds, 0.5))
            tgt = (word_peak if stressed else base * rng.uniform(0.9, 1.0)) * decl
            f0pts.append((t + vd * 0.35, tgt))
            f0pts.append((t + vd * 0.9, tgt * (0.9 if shout else 0.96)))
            t += vd
            if rng.random() < L["coda"]:
                c = L["cons"][rng.integers(len(L["cons"]))]
                d = C[c][4] * rng.uniform(0.7, 1.0)
                segs.append(dict(t0=t, dur=d, kind="cons", c=c))
                t += d
        words += 1
        gap = rng.uniform(0.12, 0.32) if shout else rng.uniform(0.03, 0.11)
        segs.append(dict(t0=t, dur=gap, kind="gap"))
        f0pts.append((t + gap * 0.5, f0pts[-1][1] * 0.97))
        t += gap
    return segs, f0pts, base, scale, t + 0.05


def glottal_source(rng, n, f0, shout, female, breath):
    """Period-by-period Rosenberg pulses (derivative, i.e. with lip radiation), jitter, shimmer, strain.
    Returns the voiced source and an open-phase gate for pulsed breath noise."""
    src = np.zeros(n)
    gate = np.zeros(n)
    jit = 0.022 if shout else (0.008 if female else 0.011)
    shim = 0.12 if shout else 0.06
    tp_q, tn_q = (0.36, 0.085) if shout else ((0.42, 0.2) if female else (0.4, 0.15))
    rough = B.Mod(rng, n / SR, 2.0, periodic=False)
    t = 0.0
    k = 0
    prev_a = 1.0
    while t < n / SR - 0.001:
        i = min(n - 1, int(t * SR))
        T = (1.0 / f0[i]) * (1.0 + jit * rng.standard_normal())
        T = max(T, 1.0 / 900.0)
        a = 1.0 + shim * rng.standard_normal()
        a = 0.6 * a + 0.4 * prev_a                         # shimmer is correlated period to period
        prev_a = a
        if shout:                                          # strain: alternating periods (diplophonia), on and off
            r = max(0.0, rough(t))
            a *= 1.0 + 0.18 * r * (1 if k % 2 else -1)
            T *= 1.0 + 0.02 * r * (1 if k % 2 else -1)
        Tp, Tn = tp_q * T, tn_q * T
        s0 = t * SR
        idx = np.arange(int(np.ceil(s0)), min(n, int(np.ceil(s0 + T * SR))))
        tau = idx / SR - t
        y = np.where(tau < Tp, 0.5 * np.pi / Tp * np.sin(np.pi * tau / Tp),
                     np.where(tau < Tp + Tn, -0.5 * np.pi / Tn * np.sin(np.pi * (tau - Tp) / (2 * Tn)), 0.0))
        src[idx] += a * y * T                              # x T: keep level roughly independent of pitch
        gate[idx] = np.where(tau < Tp + Tn, 1.0, 0.25)
        t += T
        k += 1
    return src, gate


def cascade(f, F, Bw):
    """Magnitude of a cascade of 2-pole resonators, each unity at DC (frames x bins)."""
    H = np.ones((F.shape[0], len(f)))
    ff = f[None, :] ** 2
    for j in range(F.shape[1]):
        Fj = F[:, j:j + 1]
        H *= Fj ** 2 / np.sqrt((Fj ** 2 - ff) ** 2 + (f[None, :] * Bw[j]) ** 2)
    return H


def stft_filter(x, H):
    """Weighted overlap-add filtering with per-frame magnitude H (frames x bins)."""
    n = len(x)
    win = np.hanning(NFFT + 1)[:-1]
    xp = np.concatenate([np.zeros(NFFT), x, np.zeros(NFFT)])
    nfr = H.shape[0]
    out = np.zeros(len(xp))
    wsum = np.zeros(len(xp))
    starts = np.arange(nfr) * HOP
    ok = starts + NFFT <= len(xp)
    starts = starts[ok]
    idx = starts[:, None] + np.arange(NFFT)[None, :]
    X = np.fft.rfft(xp[idx] * win, axis=1)
    Y = np.fft.irfft(X * H[:len(starts)], n=NFFT, axis=1) * win
    for i, s in enumerate(starts):
        out[s:s + NFFT] += Y[i]
        wsum[s:s + NFFT] += win * win
    return out[NFFT:NFFT + n] / np.maximum(wsum[NFFT:NFFT + n], 1e-6)


def burst(rng, place, amp, n_len):
    """Plosive release: a few ms of noise with the place's spectrum (labial flat-low, alveolar high, velar compact)."""
    m = int(0.02 * SR)
    tt = np.arange(m) / SR
    e = np.minimum(1.0, tt / 0.0003) * np.exp(-tt / rng.uniform(0.002, 0.004))
    z = rng.standard_normal(m) * e
    shape = {
        "lab": lambda f: B.r_lp(f, 1500, 2) * B.r_hp(f, 200, 2),
        "alv": lambda f: B.r_hp(f, 3000, 2) * B.r_peak(f, 4800, 6.0, 1.0),
        "post": lambda f: B.r_bp(f, 1800, 6000, 2) * B.r_peak(f, 2900, 6.0, 0.8),
        "vel": lambda f: B.r_bp(f, 1200, 5000, 2) * B.r_peak(f, rng.uniform(1900, 2700), 9.0, 0.5),
    }[place]
    return amp * B.pk(B.filt(z, shape, pad=0.05))


def synth(rng, lang, seconds, style, female):
    shout = style == "shout"
    segs, f0pts, base, scale, total = plan(rng, lang, seconds, style, female)
    n = int(total * SR)
    frames = (n + NFFT) // HOP + 1
    ft = np.arange(frames) * HOP / SR - NFFT / (2 * SR)   # frame centre times (stft_filter pads NFFT in front)
    voice = np.zeros(n)
    asp = np.zeros(n)
    fric = np.zeros(n)
    trill = np.zeros(n)
    bursts = np.zeros(n)
    nas_t, nas_v = [0.0], [0.0]
    fz_t, fz_c, fz_w = [0.0], [3000.0], [2000.0]
    fa = []   # formant anchors (t, F1, F2, F3)
    neutral = [500 * scale, 1450 * scale, 2450 * scale]
    fa.append((0.0, *neutral))
    rflav = LANG[lang]["r"]

    for i, s in enumerate(segs):
        t0, d, kind = s["t0"], s["dur"], s["kind"]
        prev = segs[i - 1] if i > 0 else None
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        if kind == "vowel":
            F, F2 = s["F"], s["F2"]
            pc = C[prev["c"]] if prev is not None and prev["kind"] == "cons" else None
            nc = C[nxt["c"]] if nxt is not None and nxt["kind"] == "cons" else None
            loc_in = LOCUS[pc[1]] if pc else None
            loc_out = LOCUS[nc[1]] if nc else None
            if loc_in:
                fa.append((t0, 320 * scale, (loc_in + 0.5 * (F[1] / scale - loc_in)) * scale, F[2] * 0.95))
            fa.append((t0 + min(0.055, d * 0.4), *F))
            end_t = F2 if F2 else F
            fa.append((t0 + d - min(0.045, d * 0.3), *end_t))
            if loc_out:
                fa.append((t0 + d, 350 * scale, (loc_out + 0.6 * (end_t[1] / scale - loc_out)) * scale, end_t[2] * 0.95))
            voiced_in = pc is not None and pc[0] in ("vplosive", "vfric", "nasal", "liquid")
            fall = 0.035 if (nxt is None or nxt["kind"] == "gap") else 0.012
            piece(voice, t0 - (0.005 if voiced_in else 0.0), d + 0.005, s["level"], 0.008 if voiced_in else 0.022, fall)
            va, vb = int(t0 * SR), min(n, int((t0 + d) * SR))
            if vb > va:   # a syllable swells early and sags toward its end
                voice[va:vb] *= np.interp(np.linspace(0, 1, vb - va), [0, 0.3, 1], [0.85, 1.0, rng.uniform(0.6, 0.8)])
            nas_t += [t0, t0 + d]
            nas_v += [0.8 if s["nasal"] else 0.0] * 2
        elif kind == "inhale":
            piece(asp, t0, d, 0.25, d * 0.5, d * 0.3)
            fa.append((t0, 600 * scale, 1300 * scale, 2500 * scale))
        elif kind == "cons":
            c = s["c"]
            ck, place, nc_, nw, _, nl = C[c]
            if ck in ("plosive", "vplosive"):
                rel = t0 + d * (0.62 if ck == "plosive" else 0.7)
                if ck == "vplosive":
                    piece(voice, t0, rel - t0, 0.1, 0.01, 0.005)               # voice bar during closure
                    fa.append((t0 + 0.01, 250 * scale, (LOCUS[place]) * scale, 2400 * scale))
                amp = rng.uniform(0.5, 0.8) * (1.2 if shout else 1.0) * (0.45 if ck == "vplosive" else 1.0)
                b = burst(rng, place, amp, n)
                B.place(bursts, b, rel)
                vot = (t0 + d - rel) * (1.0 if ck == "plosive" else 0.4)
                piece(asp, rel + 0.002, vot, 0.3 if ck == "plosive" else 0.1, 0.003, vot * 0.6)
            elif ck in ("fric", "vfric", "affric", "asp"):
                if ck == "affric":
                    B.place(bursts, burst(rng, "alv", rng.uniform(0.4, 0.6), n), t0 + 0.02)
                    piece(fric, t0 + 0.022, d - 0.022, nl, 0.006, 0.02)
                elif ck == "asp":
                    piece(asp, t0, d, nl * (1.3 if shout else 1.0), 0.015, 0.01)
                else:
                    piece(fric, t0, d, nl * (1.15 if shout else 1.0), 0.018, 0.02)
                if ck == "vfric":
                    piece(voice, t0, d, 0.35, 0.012, 0.012)
                if ck != "asp":
                    fz_t += [t0 - 0.002, t0 + d]
                    fz_c += [nc_, nc_]
                    fz_w += [nw, nw]
                if LOCUS.get(place):
                    fa.append((t0 + d * 0.5, 330 * scale, LOCUS[place] * scale, 2500 * scale))
            elif ck == "nasal":
                piece(voice, t0, d, 0.42, 0.01, 0.01)
                f2 = 1000 if c == "m" else 1500
                fa.append((t0 + 0.012, 260 * scale, f2 * scale, 2300 * scale))
                fa.append((t0 + d - 0.012, 260 * scale, f2 * scale, 2300 * scale))
                nas_t += [t0, t0 + 0.01, t0 + d - 0.01, t0 + d]
                nas_v += [0.0, 1.0, 1.0, 0.0]
            elif ck == "liquid":
                key = c if c != "r" else ("r_" + rflav)
                Fl = [x * scale for x in LIQ_F[key]]
                piece(voice, t0, d, 0.55, 0.01, 0.01)
                fa.append((t0 + d * 0.3, *Fl))
                fa.append((t0 + d * 0.7, *Fl))
                if key == "r_uvular":                       # uvular trill / fricative
                    piece(trill, t0, d, 0.22 * (1.3 if shout else 1.0), 0.008, 0.01)
                    fz_t += [t0, t0 + d]
                    fz_c += [nc_, nc_]
                    fz_w += [nw, nw]
        elif kind == "gap":
            pass

    # F0 contour: targets, language intonation, slow drift, and a pitch kick after voiceless consonants
    f0pts.sort()
    ts = np.array([0.0] + [p[0] for p in f0pts] + [total])
    vs = np.array([f0pts[0][1]] + [p[1] for p in f0pts] + [f0pts[-1][1]])
    tt = np.arange(n) / SR
    f0 = np.interp(tt, ts, vs)
    x01 = tt / total
    contour = LANG[lang]["contour"]
    if contour == "rise" and not shout:
        f0 *= 1.0 + 0.25 * np.clip((x01 - 0.82) / 0.18, 0, 1)
    elif contour == "mixed":
        f0 *= 1.0 + 0.05 * np.sin(x01 * 9.0 + rng.uniform(0, 6))
    k = int(0.04 * SR)
    f0 = np.convolve(np.pad(f0, (k, k), mode="edge"), np.hanning(2 * k + 1) / np.hanning(2 * k + 1).sum(), "same")[k:k + n]
    drift = B.Mod(rng, total, 3.0, periodic=False)
    f0 *= 1.0 + 0.015 * drift(tt)
    if not shout and not female and lang in ("de", "en"):   # phrase-final creak: low, irregular
        f0 *= 1.0 - 0.18 * np.clip((x01 - 0.88) / 0.12, 0, 1)

    breath = 0.05 if shout else (0.12 if female else 0.08)
    src, gate = glottal_source(rng, n, f0, shout, female, breath)
    src /= np.abs(src).max() + 1e-9
    k = int(0.004 * SR)
    sm = np.hanning(2 * k + 1)
    sm /= sm.sum()
    voice = np.convolve(voice, sm, "same")
    asp = np.convolve(asp, sm, "same")
    fric = np.convolve(fric, sm, "same")
    noise1 = rng.standard_normal(n)
    noise2 = rng.standard_normal(n)
    tr_rate = rng.uniform(24, 32)
    trill_am = 0.5 + 0.5 * np.cos(2 * np.pi * tr_rate * tt)
    tract_in = src * voice + noise1 * (breath * voice * gate * 2.5 + asp * 0.6)
    fric_in = noise2 * (fric + trill * trill_am)

    # frame tracks
    fa.sort(key=lambda a: a[0])
    fat = np.array([a[0] for a in fa])
    Fm = np.stack([np.interp(ft, fat, np.array([a[j] for a in fa])) for j in (1, 2, 3)], 1)
    kf = 5
    for j in range(3):
        Fm[:, j] = np.convolve(np.pad(Fm[:, j], (kf, kf), mode="edge"), np.ones(2 * kf + 1) / (2 * kf + 1), "same")[kf:kf + frames]
    F4 = np.full((frames, 1), 3500.0 * scale)
    F5 = np.full((frames, 1), 4500.0 * scale)
    Fall = np.concatenate([Fm, F4, F5], 1)
    Bw = (90.0, 110.0, 160.0, 250.0, 350.0) if not shout else (110.0, 120.0, 160.0, 230.0, 320.0)
    f = np.fft.rfftfreq(NFFT, 1.0 / SR)
    H = cascade(f, Fall, Bw)
    nas = np.interp(ft, nas_t, nas_v)[:, None]
    fz = rng.uniform(1000, 1300)
    anti = np.sqrt((fz ** 2 - f[None, :] ** 2) ** 2 + (f[None, :] * 200.0) ** 2) / fz ** 2
    npole = 250.0 ** 2 / np.sqrt((250.0 ** 2 - f[None, :] ** 2) ** 2 + (f[None, :] * 100.0) ** 2)
    H = H * (1 - nas + nas * np.minimum(anti, 1.5) * (0.5 + 0.5 * npole))
    if shout:
        H *= B.r_peak(f, 3000.0, 4.0, 1.2)[None, :]       # the "ring" of a raised voice
    fzc = np.interp(ft, fz_t, fz_c)[:, None]
    fzw = np.interp(ft, fz_t, fz_w)[:, None]
    Hf = 1.0 / (1.0 + ((f[None, :] - fzc) / (fzw * 0.5)) ** 2) * B.r_hp(f, 900.0, 2)[None, :]
    Hf /= np.sqrt((Hf ** 2).mean(1, keepdims=True)) + 1e-9   # equal energy per fricative

    voiced = stft_filter(tract_in, H)
    vref = np.abs(voiced).max() + 1e-9
    out = voiced + FRIC_GAIN * vref * stft_filter(fric_in, Hf) + BURST_GAIN * vref * bursts
    # distance and weather: roll off the top so it stays babble, not words
    lp = 5600.0 if shout else 4400.0
    out = B.filt(out, lambda fr: B.r_lp(fr, lp, 3) * B.r_hp(fr, 90.0, 2))
    if shout:
        out = B.sat(B.pk(out) * 1.6, 1.3)
        taps = [dict(t=rng.uniform(0.025, 0.055), g=0.38, lp=6000), dict(t=rng.uniform(0.07, 0.14), g=0.2, lp=4500)]
        for _ in range(5):
            taps.append(dict(t=rng.uniform(0.18, 0.5), g=rng.uniform(0.04, 0.1), lp=rng.uniform(2000, 3500)))
        late = dict(start=0.04, fade=0.08, gain=0.7, t60=[(125, 1.2), (500, 1.0), (1000, 0.85), (2000, 0.6), (4000, 0.4), (8000, 0.2)])
        ir = B.ir_build(rng, 1.0, taps, late, stereo=False)
        wet = B.conv(out, ir)[:n]
        out = out + 0.3 * B.pk(wet) * np.abs(out).max()
    fade = int(0.02 * SR)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    # consistent level: speech RMS (over voiced parts) to a target, peaks limited
    act = np.abs(out) > 0.05 * np.abs(out).max()
    rms = np.sqrt((out[act] ** 2).mean()) if act.any() else 1.0
    out = out * (10 ** ((-12.5 if shout else -15.5) / 20.0) / rms)
    global GR_MAX
    GR_MAX = max(GR_MAX, 20 * np.log10(np.abs(out).max()) + 1.0)
    out = B.limit(out, -1.0, release=0.04)
    return out.astype(np.float32)


def write_wav(path, data):
    pcm = np.clip(np.round(data * 32767.0), -32768, 32767).astype("<i2").tobytes()
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, SR, SR * 2, 2, 16))
        f.write(b"data" + struct.pack("<I", len(pcm)) + pcm)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    os.makedirs(OUT, exist_ok=True)
    plan_ = [("de", "talk", False, 8), ("de", "shout", False, 8), ("fr", "talk", False, 6),
             ("fr", "talk", True, 6), ("en", "talk", False, 5)]
    lengths = {"s": (0.6, 1.0), "m": (1.4, 2.2), "l": (2.8, 3.8)}
    count = 0
    for lang, style, female, per_len in plan_:
        for bucket, (lo, hi) in lengths.items():
            for k in range(per_len):
                name = f"{lang}_{style}{'_f' if female else ''}_{bucket}_{k + 1:02d}.wav"
                if only and not name.startswith(only):
                    continue
                # hash() is salted per process; derive a stable seed instead.
                seed = sum(ord(ch) * (i + 1) for i, ch in enumerate(f"{lang}{style}{female}{bucket}{k}")) * 7919
                rng = np.random.default_rng(seed)
                data = synth(rng, lang, rng.uniform(lo, hi), style, female)
                write_wav(os.path.join(OUT, name), data)
                count += 1
    print("wrote", count, "clips to", os.path.abspath(OUT), f"(max limiter reduction {max(0.0, GR_MAX):.1f} dB)")


if __name__ == "__main__":
    main()
