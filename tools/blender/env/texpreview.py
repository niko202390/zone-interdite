"""Contact sheet for generated texture sets (reads PNGs written by texlib.write_png).
usage: python.exe texpreview.py out.png folder:name [folder:name ...]
Each row: albedo tiled 2x2 (seam check), normal, ORM — downsampled."""
import os
import struct
import sys
import zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from texlib import write_png  # noqa: E402


def read_png(path):
    data = open(path, "rb").read()
    pos = 8
    idat = b""
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
    assert (raw[:, 0] == 1).all(), "only Sub-filtered PNGs supported"
    rows = raw[:, 1:].reshape(h, w, c).astype(np.int64)
    rows = np.cumsum(rows, axis=1) % 256
    return rows.astype(np.uint8)


def down(img, size):
    h, w = img.shape[:2]
    f = max(1, h // size)
    img = img[: (h // f) * f, : (w // f) * f]
    return img.reshape(h // f, f, w // f, f, -1).mean((1, 3)).astype(np.uint8)


def main():
    out = sys.argv[1]
    rows = []
    S = 384
    for spec in sys.argv[2:]:
        folder, name = spec.split(":")
        a = read_png(os.path.join(folder, f"{name}_albedo.png"))[..., :3]
        tiles = np.tile(down(a, S // 2), (2, 2, 1))
        parts = [tiles]
        for s in ("normal", "orm"):
            p = os.path.join(folder, f"{name}_{s}.png")
            parts.append(down(read_png(p)[..., :3], S) if os.path.exists(p) else np.zeros((S, S, 3), np.uint8))
        parts = [p[:S, :S] if p.shape[0] >= S else np.pad(p, ((0, S - p.shape[0]), (0, S - p.shape[1]), (0, 0))) for p in parts]
        rows.append(np.concatenate(parts, 1))
    write_png(out, np.concatenate(rows, 0))


if __name__ == "__main__":
    main()
