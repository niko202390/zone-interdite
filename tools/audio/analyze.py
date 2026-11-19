"""Quick objective checks for generated WAVs: 1/3-octave band energy, seam continuity for loops."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import build_audio as B


def bands(x):
    if x.ndim == 2:
        x = x.mean(1)
    X = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / B.SR)
    out = []
    lo = 25.0
    while lo * 2 ** (1 / 3) < 20000:
        hi = lo * 2 ** (1 / 3)
        out.append((lo, X[(f >= lo) & (f < hi)].sum()))
        lo = hi
    e = np.array([v for _, v in out])
    e = 10 * np.log10(e / e.max() + 1e-15)
    return [(int(lo), v) for (lo, _), v in zip(out, e)]


if __name__ == "__main__":
    for name in sys.argv[1:]:
        w = B.read_wav(Path(name))
        b = bands(w["pcm"])
        print(Path(name).name)
        print("   " + " ".join(f"{lo}:{v:.0f}" for lo, v in b))


def verify(root):
    """Check every WAV: format, peak, smpl loop points, and click-free loop seams."""
    import json
    man = {e["file"]: e for e in json.loads((root / "manifest.json").read_text())["sounds"]}
    total = 0
    problems = []
    files = sorted(root.rglob("*.wav"))
    for p in files:
        rel = p.relative_to(root).as_posix()
        total += p.stat().st_size
        w = B.read_wav(p)
        x = w["pcm"]
        e = man.get(rel)
        if e is None:
            problems.append(f"{rel}: not in manifest")
            continue
        if (w["fmt"], w["sr"], w["bits"], w["ch"]) != (1, 44100, 16, e["channels"]):
            problems.append(f"{rel}: bad format {w['fmt'], w['sr'], w['bits'], w['ch']}")
        peak = 20 * np.log10(np.abs(x).max() + 1e-12)
        if peak > -0.9:
            problems.append(f"{rel}: peak {peak:.2f} dBFS")
        if e["loop"]:
            sm = w.get("smpl")
            if not sm or sm["loops"] != 1 or sm["type"] != 0 or sm["start"] != 0 or sm["end"] != len(x) - 1:
                problems.append(f"{rel}: smpl chunk wrong {sm}")
            d = np.abs(np.diff(x, axis=0))
            seam = np.abs(x[0] - x[-1]).max()
            p999 = np.percentile(d.max(1), 99.9)
            ratio = seam / (p999 + 1e-12)
            print(f"  loop {rel:<36} seam jump {seam:.5f}  vs p99.9 step {p999:.5f}  ratio {ratio:.2f}")
            if ratio > 1.0:
                problems.append(f"{rel}: loop seam jump {ratio:.2f}x the 99.9th-percentile step")
        elif "smpl" in w:
            problems.append(f"{rel}: one-shot has smpl chunk")
    missing = [k for k in man if not (root / k).exists()]
    problems += [f"{k}: in manifest but missing" for k in missing]
    print(f"{len(files)} wav files, {total / 1e6:.1f} MB total")
    print("PROBLEMS:" if problems else "no problems found")
    for pr in problems:
        print("  " + pr)


def preview_files(root, pattern, out, **kw):
    items = [(p.stem, B.read_wav(p)["pcm"]) for p in sorted(root.glob(pattern))]
    items = [(n, x[:, 0] if x.shape[1] == 1 else x) for n, x in items]
    B.montage(items, out, **kw)
