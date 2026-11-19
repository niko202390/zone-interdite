"""Synthesise the sounds of listening to London on a wartime wireless, from scratch:
  - the BBC's 'V for Victory' drum signal (. . . -), struck twice, on a muffled timpani
  - shortwave static with slow fading (QSB) and crackle, seamless loop
  - German jamming ('brouillage'): a warbling, rotating buzz over the carrier, seamless loop
  - a tuning sweep (dial turned through stations) for switching the set on
Mono, 44.1 kHz, deterministic. Loops carry a WAV smpl chunk.
Usage: "<blender python>" -I tools/audio/build_radio.py
"""
import os
import struct
import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "game", "assets", "audio", "radio")
rng = np.random.default_rng(1941)


def lowpass(x, cutoff):
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    spec *= 1.0 / (1.0 + (f / cutoff) ** 4)
    return np.fft.irfft(spec, len(x))


def bandpass(x, lo, hi):
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    spec *= (1.0 / (1.0 + (lo / np.maximum(f, 1)) ** 4)) * (1.0 / (1.0 + (f / hi) ** 4))
    return np.fft.irfft(spec, len(x))


def norm(x, peak_db=-1.0):
    return x / (np.max(np.abs(x)) + 1e-9) * 10 ** (peak_db / 20)


def loopify(x, xf=0.5):
    """Make a seamless loop by crossfading the tail into the head."""
    n = int(xf * SR)
    head = x[:n].copy()
    tail = x[-n:].copy()
    ramp = np.linspace(0, 1, n)
    x = x[:-n].copy()
    x[:n] = head * ramp + tail * (1 - ramp)
    return x


def write(name, x, loop=False):
    os.makedirs(OUT, exist_ok=True)
    pcm = np.clip(x * 32767, -32768, 32767).astype("<i2").tobytes()
    chunks = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, SR, SR * 2, 2, 16)
    chunks += b"data" + struct.pack("<I", len(pcm)) + pcm
    if loop:
        frames = len(pcm) // 2
        smpl = struct.pack("<9I", 0, 0, int(1e9 / SR), 60, 0, 0, 0, 1, 0)
        smpl += struct.pack("<6I", 0, 0, 0, frames - 1, 0, 0)
        chunks += b"smpl" + struct.pack("<I", len(smpl)) + smpl
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)


def drum(dur, strength):
    """A muffled timpani stroke: a pitched membrane with a falling pitch, felt-mallet thud and rattle."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f0 = 92.0
    pitch = f0 * (1.0 + 0.18 * np.exp(-t * 18.0))
    phase = 2 * np.pi * np.cumsum(pitch) / SR
    body = np.sin(phase) * np.exp(-t * 3.2) + 0.45 * np.sin(phase * 1.52) * np.exp(-t * 5.0) \
        + 0.25 * np.sin(phase * 1.99) * np.exp(-t * 7.0)
    thud = lowpass(rng.standard_normal(n), 400) * np.exp(-t * 40.0) * 2.5
    return (body + thud) * strength


def v_signal():
    # . . . -   (dot dot dot dash), twice, with the dash ringing longer
    seq = []
    for rep in range(2):
        for k in range(3):
            seq.append(drum(0.34, 0.8))
        seq.append(drum(1.2, 1.0))
        seq.append(np.zeros(int(0.9 * SR)))
    x = np.concatenate(seq)
    room = np.zeros(int(0.6 * SR))
    room[0] = 1
    tail = np.exp(-np.arange(len(room)) / SR * 6) * rng.standard_normal(len(room)) * 0.08
    x = np.convolve(x, room + tail)[: len(x) + len(room) // 2]
    return norm(bandpass(x, 90, 3200))


def static_loop(seconds=24.0):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    hiss = bandpass(rng.standard_normal(n), 300, 3600) * 0.35
    fade = 0.55 + 0.45 * np.sin(2 * np.pi * t / 7.3 + 1.0) * np.sin(2 * np.pi * t / 3.1)
    crackle = np.zeros(n)
    for i in rng.integers(0, n - 400, 160):
        crackle[i:i + 300] += rng.standard_normal(300) * np.exp(-np.arange(300) / 40.0) * rng.uniform(0.3, 1.2)
    carrier_whistle = 0.04 * np.sin(2 * np.pi * (1850 + 40 * np.sin(2 * np.pi * t / 11.0)) * t)
    x = hiss * fade + bandpass(crackle, 400, 5000) * 0.6 + carrier_whistle
    return norm(loopify(x), -3.0)


def jamming_loop(seconds=18.0):
    """German jammers: a harsh tone warbling up and down at a few Hz, chopped by a rotary interrupter."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    warble = 380 + 140 * np.sin(2 * np.pi * 2.6 * t) + 60 * np.sin(2 * np.pi * 0.37 * t)
    phase = 2 * np.pi * np.cumsum(warble) / SR
    tone = np.sign(np.sin(phase)) * 0.4 + np.sin(phase * 2) * 0.2
    chop = 0.6 + 0.4 * (np.sin(2 * np.pi * 11.0 * t) > 0)
    x = bandpass(tone * chop, 250, 3000) + bandpass(rng.standard_normal(n), 300, 3000) * 0.25
    return norm(loopify(x), -4.0)


def tuning_sweep(seconds=1.6):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    f = 600 + 2600 * (t / seconds) ** 1.3
    phase = 2 * np.pi * np.cumsum(f) / SR
    squeal = np.sin(phase) * 0.3 * np.exp(-((t - seconds * 0.6) / 0.35) ** 2)
    hiss = bandpass(rng.standard_normal(n), 300, 3800) * (0.3 + 0.2 * np.sin(2 * np.pi * 9 * t))
    click = np.zeros(n)
    click[:220] = rng.standard_normal(220) * np.exp(-np.arange(220) / 30.0)
    x = squeal + hiss + click * 1.5
    x[-2000:] *= np.linspace(1, 0, 2000)
    return norm(x, -2.0)


if __name__ == "__main__":
    write("bbc_v_signal.wav", v_signal())
    write("static_loop.wav", static_loop(), loop=True)
    write("jamming_loop.wav", jamming_loop(), loop=True)
    write("tuning_sweep.wav", tuning_sweep())
    print("wrote radio sounds to", os.path.abspath(OUT))
