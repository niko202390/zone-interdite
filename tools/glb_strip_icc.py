"""Strip embedded ICC colour profiles (JPEG APP2 segments) from images inside .glb files.

Godot 4.7's in-memory JPEG loader fails on the APP2/ICC segment Blender writes into sRGB
(albedo) JPEGs, which leaves those materials without a base colour. Normal and ORM maps are
written without ICC data, so they were unaffected. The pixel data is untouched; only the
profile segment goes. Images are already sRGB, which is what Godot assumes.

Usage:  python glb_strip_icc.py <file-or-folder> [...]
Run it after every Blender export (tools/build_assets.sh does this).
"""
import json
import os
import struct
import sys

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942


def strip_app2(jpeg: bytes) -> bytes:
    if jpeg[:2] != b"\xff\xd8":
        return jpeg
    out = bytearray(jpeg[:2])
    i = 2
    while i < len(jpeg) - 3:
        if jpeg[i] != 0xFF:
            break
        marker = jpeg[i + 1]
        if marker == 0xDA:  # start of scan: the rest is entropy-coded data
            out += jpeg[i:]
            return bytes(out)
        seg_len = struct.unpack(">H", jpeg[i + 2:i + 4])[0]
        segment = jpeg[i:i + 2 + seg_len]
        if marker != 0xE2:
            out += segment
        i += 2 + seg_len
    out += jpeg[i:]
    return bytes(out)


def pad4(b: bytes, fill: bytes) -> bytes:
    return b + fill * ((4 - len(b) % 4) % 4)


def process(path: str) -> bool:
    data = open(path, "rb").read()
    magic, version, _ = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC:
        return False
    off = 12
    js = None
    binc = b""
    while off < len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        chunk = data[off + 8:off + 8 + clen]
        if ctype == CHUNK_JSON:
            js = json.loads(chunk)
        elif ctype == CHUNK_BIN:
            binc = chunk
        off += 8 + clen
    if js is None:
        return False

    image_views = {img["bufferView"] for img in js.get("images", []) if img.get("mimeType") == "image/jpeg" and "bufferView" in img}
    views = js.get("bufferViews", [])
    changed = False
    new_bin = bytearray()
    for idx, bv in enumerate(views):
        start = bv.get("byteOffset", 0)
        chunk = binc[start:start + bv["byteLength"]]
        if idx in image_views:
            stripped = strip_app2(chunk)
            if len(stripped) != len(chunk):
                changed = True
            chunk = stripped
        while len(new_bin) % 4:
            new_bin.append(0)
        bv["byteOffset"] = len(new_bin)
        bv["byteLength"] = len(chunk)
        new_bin += chunk
    if not changed:
        return False
    js["buffers"][0]["byteLength"] = len(new_bin)

    json_bytes = pad4(json.dumps(js, separators=(",", ":")).encode("utf-8"), b" ")
    bin_bytes = pad4(bytes(new_bin), b"\x00")
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    out = struct.pack("<III", GLB_MAGIC, version, total)
    out += struct.pack("<II", len(json_bytes), CHUNK_JSON) + json_bytes
    out += struct.pack("<II", len(bin_bytes), CHUNK_BIN) + bin_bytes
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, path)
    return True


def main(args):
    files = []
    for a in args:
        if os.path.isdir(a):
            for root, _, names in os.walk(a):
                files += [os.path.join(root, n) for n in names if n.lower().endswith(".glb")]
        else:
            files.append(a)
    for f in sorted(files):
        print(("stripped ICC  " if process(f) else "unchanged     ") + f)


if __name__ == "__main__":
    main(sys.argv[1:])
