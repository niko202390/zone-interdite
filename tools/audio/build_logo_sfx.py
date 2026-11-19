"""Sounds for the animated title logo, synthesised from scratch:
  pen_scratch_loop   a steel nib on laid paper (seamless loop)
  lighter_open       the hinged lid flicked open: a bright metallic clink with a short ring
  lighter_strike     the flint wheel rasped by a thumb, a spark crackle, then the wick catching
  flame_loop         a petrol lighter flame: soft roar and flutter (seamless loop)
  lighter_close      the lid snapped shut: a duller clack
Mono, 44.1 kHz, deterministic. Usage: "<blender python>" -I tools/audio/build_logo_sfx.py
"""
import os
import struct
import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "game", "assets", "audio", "ui")
rng = np.random.default_rng(1944)


def bp(x, lo, hi):
    s = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    s *= (1 / (1 + (lo / np.maximum(f, 1)) ** 4)) * (1 / (1 + (f / hi) ** 4))
    return np.fft.irfft(s, len(x))


def norm(x, db=-1.0):
    return x / (np.max(np.abs(x)) + 1e-9) * 10 ** (db / 20)


def loopify(x, xf=0.3):
    n = int(xf * SR)
    r = np.linspace(0, 1, n)
    y = x[:-n].copy()
    y[:n] = x[:n] * r + x[-n:] * (1 - r)
    return y


def write(name, x, loop=False):
    os.makedirs(OUT, exist_ok=True)
    pcm = np.clip(x * 32767, -32768, 32767).astype("<i2").tobytes()
    body = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, SR, SR * 2, 2, 16) + b"data" + struct.pack("<I", len(pcm)) + pcm
    if loop:
        frames = len(pcm) // 2
        smpl = struct.pack("<9I", 0, 0, int(1e9 / SR), 60, 0, 0, 0, 1, 0) + struct.pack("<6I", 0, 0, 0, frames - 1, 0, 0)
        body += b"smpl" + struct.pack("<I", len(smpl)) + smpl
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body)


def ring(freqs, decays, n, amps):
    t = np.arange(n) / SR
    return sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d, a in zip(freqs, decays, amps))


def pen_scratch(seconds=4.0):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    fibre = bp(rng.standard_normal(n), 1800, 7500)
    # Strokes: pressure comes and goes as letters are formed.
    strokes = np.clip(0.55 + 0.45 * np.sin(2 * np.pi * 3.1 * t + 2 * np.sin(2 * np.pi * 0.7 * t)), 0, 1) ** 1.5
    ticks = np.zeros(n)
    for i in rng.integers(0, n - 200, 90):
        ticks[i:i + 120] += rng.standard_normal(120) * np.exp(-np.arange(120) / 18.0)
    x = fibre * strokes * 0.5 + bp(ticks, 2500, 9000) * 0.4
    return norm(loopify(x), -6.0)


def lighter_open():
    n = int(0.5 * SR)
    click = bp(rng.standard_normal(n), 2000, 12000) * np.exp(-np.arange(n) / SR * 260)
    clink = ring([3150, 4720, 6900, 2280], [26, 34, 48, 20], n, [0.6, 0.4, 0.25, 0.3])
    return norm(click * 0.8 + clink * 0.5, -2.0)


def lighter_strike():
    n = int(1.3 * SR)
    t = np.arange(n) / SR
    rasp_env = np.clip((t - 0.02) / 0.02, 0, 1) * np.clip((0.22 - t) / 0.05, 0, 1)
    wheel = bp(rng.standard_normal(n), 900, 6500) * rasp_env * (0.6 + 0.4 * np.sin(2 * np.pi * 95 * t))
    sparks = np.zeros(n)
    for i in rng.integers(int(0.08 * SR), int(0.3 * SR), 40):
        sparks[i:i + 60] += rng.standard_normal(60) * np.exp(-np.arange(60) / 9.0)
    catch_env = np.clip((t - 0.24) / 0.08, 0, 1) * np.exp(-np.clip(t - 0.32, 0, None) * 2.5)
    whoomp = bp(rng.standard_normal(n), 80, 900) * catch_env
    return norm(wheel * 0.7 + bp(sparks, 3000, 11000) * 0.5 + whoomp * 0.9, -2.0)


def flame_loop(seconds=6.0):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    roar = bp(rng.standard_normal(n), 60, 700)
    flutter = 0.75 + 0.25 * np.sin(2 * np.pi * 7.3 * t + np.sin(2 * np.pi * 0.9 * t) * 2)
    hiss = bp(rng.standard_normal(n), 2000, 6000) * 0.08
    return norm(loopify(roar * flutter + hiss), -8.0)


def lighter_close():
    n = int(0.35 * SR)
    clack = bp(rng.standard_normal(n), 600, 6000) * np.exp(-np.arange(n) / SR * 180)
    body = ring([1650, 2480, 3900], [40, 55, 70], n, [0.5, 0.3, 0.2])
    return norm(clack + body * 0.4, -2.0)


if __name__ == "__main__":
    write("pen_scratch_loop.wav", pen_scratch(), loop=True)
    write("lighter_open.wav", lighter_open())
    write("lighter_strike.wav", lighter_strike())
    write("flame_loop.wav", flame_loop(), loop=True)
    write("lighter_close.wav", lighter_close())
    print("wrote logo sounds to", os.path.abspath(OUT))
