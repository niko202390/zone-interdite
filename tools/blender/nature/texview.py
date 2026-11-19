"""Composite card atlases over a dusk colour for inspection: python texview.py name [name...]"""
import os, sys, zlib, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "env"))
from texlib import write_png


def read_png(path):
    data = open(path, "rb").read()
    pos, idat, w = 8, b"", 0
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        t = data[pos + 4:pos + 8]
        d = data[pos + 8:pos + 8 + ln]
        if t == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", d[:10])
        elif t == b"IDAT":
            idat += d
        pos += 12 + ln
    c = {0: 1, 2: 3, 6: 4}[ct]
    raw = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, w * c + 1)
    out = np.zeros((h, w * c), np.int32)
    for y in range(h):
        f, row = raw[y, 0], raw[y, 1:].astype(np.int32)
        prev = out[y - 1] if y else np.zeros(w * c, np.int32)
        if f == 0: out[y] = row
        elif f == 1:
            out[y] = (row.reshape(w, c).cumsum(0) % 256).ravel()
        elif f == 2: out[y] = (row + prev) % 256
        else: raise ValueError(f)
    return out.reshape(h, w, c).astype(np.float32) / 255


for n in sys.argv[1:]:
    im = read_png(os.path.join(HERE, "out", "tex", f"{n}_albedo.png"))
    a = (im[..., 3] > 0.5)[..., None]
    bg = np.array((0.55, 0.42, 0.40), np.float32)
    comp = np.where(a, im[..., :3] * 1.6, bg)
    step = max(1, im.shape[0] // 1024)
    write_png(os.path.join(HERE, "previews", f"tex_{n}.png"), comp[::step, ::step])
