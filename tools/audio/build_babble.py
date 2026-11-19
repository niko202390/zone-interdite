"""Synthesise 'fuzzy' non-speech voice babble from scratch: language-flavoured gibberish that sounds like
speech from a distance, through rain and fog, without being words. Subtitles carry the meaning.

Source-filter model, done per frame in the frequency domain (fast, numpy only):
  voiced source (glottal sawtooth with jitter) and noise source, shaped by formant envelopes per phoneme.
Each language has its own vowel set, consonants, syllable rhythm and intonation:
  de  hard plosives, ach/ich fricatives, clipped syllables, falling statements
  fr  nasal vowels, smooth even rhythm, rising phrase ends
  en  diphthong-ish glides, stress-timed rhythm
Styles: talk (conversational) and shout (raised pitch, flatter spectral tilt, rasp).

Usage: "<blender python>" -I tools/audio/build_babble.py
Writes game/assets/audio/voice/<lang>_<style>[_f]_<s|m|l>_NN.wav, deterministic.
"""
import os
import struct
import numpy as np

SR = 44100
NFFT = 1024
HOP = 256
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "game", "assets", "audio", "voice")

# Vowel formants (F1, F2, F3) for an adult male voice, Hz.
V = {
    "a": (750, 1250, 2500), "e": (450, 1900, 2550), "i": (280, 2250, 2900), "o": (450, 850, 2400),
    "u": (300, 750, 2300), "oe": (450, 1500, 2400), "ue": (280, 1700, 2200), "schwa": (500, 1450, 2450),
    "E": (580, 1800, 2500), "ae": (660, 1700, 2450), "I": (400, 1950, 2550), "A~": (650, 1050, 2500),
    "O~": (480, 800, 2400), "E~": (600, 1600, 2500), "ai": (700, 1500, 2500), "au": (650, 1000, 2400),
}
NASAL = {"A~", "O~", "E~"}

LANG = {
    "de": {"vowels": ["a", "e", "i", "o", "u", "oe", "ue", "schwa", "E", "ai", "au", "a", "e", "schwa"],
           "cons": ["k", "t", "p", "sh", "x", "ts", "s", "f", "n", "m", "l", "r", "c", "h", "g", "d", "b"],
           "syl": (0.15, 0.21), "coda": 0.55, "contour": "fall"},
    "fr": {"vowels": ["a", "e", "i", "o", "u", "E", "schwa", "oe", "A~", "O~", "E~", "a", "e"],
           "cons": ["s", "zh", "sh", "t", "k", "p", "m", "n", "l", "r", "v", "d", "b"],
           "syl": (0.12, 0.165), "coda": 0.18, "contour": "rise"},
    "en": {"vowels": ["ae", "E", "I", "a", "o", "u", "schwa", "ai", "au", "e", "i"],
           "cons": ["t", "d", "k", "s", "h", "w", "r", "l", "n", "m", "th", "p", "b", "f"],
           "syl": (0.13, 0.24), "coda": 0.45, "contour": "mixed"},
}

# Consonants: (kind, noise centre Hz, noise width Hz, duration s). Voiced fricatives/nasals/liquids also voice.
C = {
    "k": ("plosive", 2600, 1400, 0.07), "t": ("plosive", 4200, 2500, 0.065), "p": ("plosive", 900, 900, 0.07),
    "g": ("vplosive", 2400, 1400, 0.06), "d": ("vplosive", 3800, 2200, 0.055), "b": ("vplosive", 800, 800, 0.06),
    "s": ("fric", 6500, 2500, 0.09), "sh": ("fric", 3300, 1600, 0.1), "x": ("fric", 1700, 900, 0.1),
    "c": ("fric", 4000, 1800, 0.09), "f": ("fric", 5000, 4500, 0.08), "th": ("fric", 5500, 5000, 0.07),
    "h": ("fric", 1500, 2500, 0.06), "ts": ("affric", 5800, 2600, 0.1), "zh": ("vfric", 3200, 1600, 0.09),
    "v": ("vfric", 4500, 4000, 0.07), "n": ("nasal", 0, 0, 0.065), "m": ("nasal", 0, 0, 0.07),
    "l": ("liquid", 0, 0, 0.055), "r": ("liquid", 0, 0, 0.06), "w": ("liquid", 0, 0, 0.06),
}


def envelope(freqs, formants, bandwidths, tilt_db_per_oct):
    env = np.zeros_like(freqs)
    for f, bw, amp in zip(formants, bandwidths, (1.0, 0.7, 0.45, 0.25)):
        env += amp / (1.0 + ((freqs - f) / (bw * 0.5)) ** 2)
    octaves = np.log2(np.maximum(freqs, 60.0) / 120.0)
    return env * 10 ** (tilt_db_per_oct * octaves / 20.0)


def plan_utterance(rng, lang, seconds, style, female):
    """A list of segments: dicts with duration, voicing, formants, noise params, gain."""
    L = LANG[lang]
    segs = []
    t = 0.0
    scale = 1.17 if female else 1.0
    while t < seconds:
        # A word of 1-3 syllables, then a short gap.
        for s in range(rng.integers(1, 4)):
            stressed = s == 0 and rng.random() < 0.7
            if rng.random() < 0.8:
                c = C[L["cons"][rng.integers(len(L["cons"]))]]
                segs.append({"kind": c[0], "nc": c[1], "nw": c[2], "dur": c[3] * rng.uniform(0.8, 1.2)})
            v = L["vowels"][rng.integers(len(L["vowels"]))]
            lo, hi = L["syl"]
            vdur = rng.uniform(lo, hi) * (1.35 if stressed else 0.9) * (1.15 if style == "shout" else 1.0)
            segs.append({"kind": "vowel", "f": [x * scale for x in V[v]], "nasal": v in NASAL, "dur": vdur,
                         "stress": stressed})
            if rng.random() < L["coda"]:
                c = C[L["cons"][rng.integers(len(L["cons"]))]]
                segs.append({"kind": c[0], "nc": c[1], "nw": c[2], "dur": c[3] * rng.uniform(0.7, 1.0)})
        segs.append({"kind": "gap", "dur": rng.uniform(0.03, 0.11)})
        t = sum(s["dur"] for s in segs)
    return segs


def synth(rng, lang, seconds, style, female):
    segs = plan_utterance(rng, lang, seconds, style, female)
    total = sum(s["dur"] for s in segs) + 0.15
    n = int(total * SR)
    frames = n // HOP + 4
    # Per-frame parameter tracks.
    voicing = np.zeros(frames)
    noise_g = np.zeros(frames)
    noise_c = np.full(frames, 3000.0)
    noise_w = np.full(frames, 2000.0)
    gain = np.zeros(frames)
    F = np.tile(np.array([500.0, 1500.0, 2500.0, 3500.0]), (frames, 1))
    nasal = np.zeros(frames)
    stress = np.zeros(frames)
    t = 0.0
    last_f = [500.0, 1500.0, 2500.0]
    for s in segs:
        a = int(t * SR / HOP)
        b = max(a + 1, int((t + s["dur"]) * SR / HOP))
        k = s["kind"]
        if k == "vowel":
            f = s["f"]
            # Glide from the previous formants over the first 40 ms.
            for i in range(a, min(b, frames)):
                g = min(1.0, (i - a) * HOP / SR / 0.04)
                F[i, :3] = [last_f[j] + (f[j] - last_f[j]) * g for j in range(3)]
            last_f = list(f)
            voicing[a:b] = 1.0
            gain[a:b] = 1.0
            nasal[a:b] = 1.0 if s["nasal"] else 0.0
            stress[a:b] = 1.0 if s["stress"] else 0.0
        elif k in ("fric", "vfric", "affric"):
            noise_g[a:b] = 0.55 if k != "affric" else 0.7
            noise_c[a:b] = s["nc"]
            noise_w[a:b] = s["nw"]
            voicing[a:b] = 0.55 if k == "vfric" else 0.0
            gain[a:b] = 0.6
        elif k in ("plosive", "vplosive"):
            closure = a + max(1, (b - a) * 2 // 3)
            gain[a:closure] = 0.04
            voicing[a:closure] = 0.3 if k == "vplosive" else 0.0
            noise_g[closure:b] = 0.9
            noise_c[closure:b] = s["nc"]
            noise_w[closure:b] = s["nw"]
            gain[closure:b] = 0.8
        elif k == "nasal":
            voicing[a:b] = 1.0
            gain[a:b] = 0.55
            F[a:b, :3] = [260.0, 1100.0, 2300.0]
            nasal[a:b] = 1.0
        elif k == "liquid":
            voicing[a:b] = 1.0
            gain[a:b] = 0.75
            F[a:b, :3] = [380.0, 1100.0, 1700.0]
        t += s["dur"]

    # Smooth tracks so nothing clicks.
    def smooth(x, w=3):
        kern = np.ones(w) / w
        return np.convolve(x, kern, mode="same")
    voicing, gain, noise_g = smooth(voicing), smooth(gain, 4), smooth(noise_g)
    for j in range(3):
        F[:, j] = smooth(F[:, j], 5)

    # Pitch contour.
    base = (205.0 if female else 112.0) * (1.6 if style == "shout" else 1.0)
    x = np.linspace(0.0, 1.0, frames)
    contour = LANG[lang]["contour"]
    if contour == "fall":
        f0 = base * (1.12 - 0.25 * x)
    elif contour == "rise":
        f0 = base * (1.0 - 0.1 * x + 0.28 * np.clip((x - 0.82) / 0.18, 0, 1))
    else:
        f0 = base * (1.05 - 0.12 * x + 0.06 * np.sin(x * 9.0))
    f0 *= 1.0 + 0.12 * smooth(stress, 7)
    f0 *= 1.0 + 0.015 * rng.standard_normal(frames)
    f0_samples = np.interp(np.arange(n), np.arange(frames) * HOP, f0)
    phase = np.cumsum(f0_samples / SR)
    voiced = 2.0 * (phase % 1.0) - 1.0
    voiced += 0.04 * rng.standard_normal(n) * (2.0 if style == "shout" else 1.0)   # breath and rasp
    noise = rng.standard_normal(n)

    window = np.hanning(NFFT)
    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    out = np.zeros(n + NFFT)
    norm = np.zeros(n + NFFT)
    tilt = -7.0 if style == "shout" else -11.0
    bws = (90.0, 120.0, 170.0, 250.0)
    for i in range(frames):
        start = i * HOP
        if start + NFFT > n:
            break
        if gain[i] < 0.01:
            norm[start:start + NFFT] += window ** 2
            continue
        sv = np.fft.rfft(voiced[start:start + NFFT] * window)
        sn = np.fft.rfft(noise[start:start + NFFT] * window)
        ev = envelope(freqs, F[i], bws, tilt)
        if nasal[i] > 0.1:
            ev *= 1.0 - 0.6 * nasal[i] / (1.0 + ((freqs - 1000.0) / 300.0) ** 2)   # anti-formant
            ev += 0.6 * nasal[i] / (1.0 + ((freqs - 250.0) / 80.0) ** 2)
        en = np.exp(-0.5 * ((freqs - noise_c[i]) / max(noise_w[i] * 0.5, 50.0)) ** 2)
        spec = voicing[i] * sv * ev + noise_g[i] * sn * en * 0.35 + 0.02 * sn * ev
        frame = np.fft.irfft(spec * gain[i]) * window
        out[start:start + NFFT] += frame
        norm[start:start + NFFT] += window ** 2
    out = out[:n] / np.maximum(norm[:n], 1e-3)
    # Fuzz it: a gentle low-pass and a touch of room noise, so it reads as distant speech, not words.
    spec = np.fft.rfft(out)
    fr = np.fft.rfftfreq(len(out), 1.0 / SR)
    spec *= 1.0 / (1.0 + (fr / (5200.0 if style == "shout" else 4200.0)) ** 4)
    out = np.fft.irfft(spec, len(out))
    fade = int(0.02 * SR)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    peak = np.max(np.abs(out)) + 1e-9
    return (out / peak * (10 ** (-1.0 / 20.0))).astype(np.float32)


def write_wav(path, data):
    pcm = np.clip(data * 32767.0, -32768, 32767).astype("<i2").tobytes()
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, SR, SR * 2, 2, 16))
        f.write(b"data" + struct.pack("<I", len(pcm)) + pcm)


def main():
    os.makedirs(OUT, exist_ok=True)
    plan = [("de", "talk", False, 8), ("de", "shout", False, 8), ("fr", "talk", False, 6),
            ("fr", "talk", True, 6), ("en", "talk", False, 5)]
    lengths = {"s": (0.6, 1.0), "m": (1.4, 2.2), "l": (2.8, 3.8)}
    count = 0
    for lang, style, female, per_len in plan:
        for bucket, (lo, hi) in lengths.items():
            for k in range(per_len):
                seed = abs(hash((lang, style, female, bucket, k))) % (2 ** 32)
                # hash() is salted per process; derive a stable seed instead.
                seed = sum(ord(ch) * (i + 1) for i, ch in enumerate(f"{lang}{style}{female}{bucket}{k}")) * 7919
                rng = np.random.default_rng(seed)
                data = synth(rng, lang, rng.uniform(lo, hi), style, female)
                name = f"{lang}_{style}{'_f' if female else ''}_{bucket}_{k + 1:02d}.wav"
                write_wav(os.path.join(OUT, name), data)
                count += 1
    print("wrote", count, "clips to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
