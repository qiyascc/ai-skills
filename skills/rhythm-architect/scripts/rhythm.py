###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw

USAGE = """rhythm-architect: measure the breathing of an edit (shot lengths, motion, loudness) against the 1/f pattern that
James Cutting's research found in films that hold attention, find flat or metronomic stretches, and turn a reference
film's rhythm (or an Eisenstein metric pattern) into a shot-length map for your own edit.

  python3 rhythm.py analyze VIDEO OUT_DIR                      -> rhythm.json, rhythm.md, rhythm.png
  python3 rhythm.py compare TARGET.mp4 REFERENCE.mp4 OUT_DIR   -> both analysed, differences in plain words, compare.png
  python3 rhythm.py map SOURCE DURATION_S OUT.json [--shots N] [--pattern ref|accelerate|decelerate|steady|wave] [--fps 25]
      SOURCE = a video or a rhythm.json to borrow the pattern from (or "none" with --pattern)
      -> OUT.json + OUT.md: list of target shot lengths (seconds and frames), OUT.edl markers at every planned cut
Measures: shots and their lengths (ASL, median, spread), the 1/f slope (alpha) of the shot-length series, of motion
per second and of loudness per second (alpha near 1 = fluctuations at every scale, like attention itself; near 0 =
random/unstructured; near 2 = slow drifts without local variety), metronomic stretches (8 shots with almost equal
lengths), flat zones (6+ s of low motion and steady sound). The shot alpha is uncertain by about +-5/sqrt(shots): under ~100 shots it is only indicative.
Needs: numpy, opencv-python-headless, Pillow, ffmpeg/ffprobe.
"""

def probe(p):
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", p], capture_output=True, text=True).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video"); n, d = map(int, v["r_frame_rate"].split("/"))
    return n / d, float(pr["format"]["duration"]), any(s["codec_type"] == "audio" for s in pr["streams"])

def read(p, w=160, h=90):
    pr = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", p, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while True:
        b = pr.stdout.read(w * h * 3)
        if len(b) < w * h * 3: break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    pr.wait()

def alpha(x):
    x = np.asarray(x, float)
    if len(x) < 16 or x.std() == 0: return None
    z = (x - x.mean()) / x.std(); n = len(z); P = np.abs(np.fft.rfft(z * np.hanning(n))) ** 2; f = np.fft.rfftfreq(n)
    m = (f > 0) & (f <= 0.25)
    if m.sum() < 4: return None
    lf, lp = np.log10(f[m]), np.log10(P[m] + 1e-12); bins = np.linspace(lf.min(), lf.max(), 9); xs, ys = [], []
    for a, b in zip(bins[:-1], bins[1:]):
        k = (lf >= a) & (lf <= b)
        if k.any(): xs.append(lf[k].mean()); ys.append(lp[k].mean())
    if len(xs) < 3: return None
    return round(float(-np.polyfit(xs, ys, 1)[0]), 2)

def analyze(p):
    fps, dur, has_a = probe(p); hs, diffs, motion, prev, prevg = [], [0.0], [], None, None
    for f in read(p):
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV); h = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256]); h = cv2.normalize(h, h).flatten(); g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        if prev is not None:
            diffs.append((1 - cv2.compareHist(prev, h, cv2.HISTCMP_CORREL)) * 0.6 + np.abs(f.astype(np.int16) - last).mean() / 255 * 2)
            motion.append(float(np.abs(g.astype(np.int16) - prevg).mean()))
        else: motion.append(0.0)
        prev, prevg, last = h, g, f
    d = np.array(diffs); n = len(d); cuts = []
    thr = np.array([max(0.035, (np.median(d[max(1, i - 12): i + 12]) + 1e-4) * 6) for i in range(n)]); high = d > thr; high[:2] = False
    def run(i):
        j, k = i, i
        while j - 1 >= 2 and high[j - 1]: j -= 1
        while k + 1 < n and high[k + 1]: k += 1
        return k - j + 1
    for i in range(2, n):
        if not high[i]: continue
        short = run(i) <= 2
        nb = max([d[j] for j in (i - 1, i + 1) if 1 <= j < n and not (short and high[j])], default=0.0)
        if d[i] > nb * 2.5 and (not cuts or i - cuts[-1] > 2 or (short and run(cuts[-1]) <= 2)): cuts.append(i)
    b = [0] + cuts + [n]; L = np.diff(b) / fps
    mot = np.array(motion); mot[cuts] = np.nan
    per_s = int(round(fps)); secs = n // per_s
    mot_s = np.array([np.nanmean(mot[i * per_s:(i + 1) * per_s]) for i in range(secs)]) if secs else np.zeros(0)
    loud_s = np.zeros(secs)
    if has_a:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        loud_s = np.array([20 * np.log10(np.sqrt((a[i * 8000:(i + 1) * 8000] ** 2).mean()) + 1e-6) if len(a[i * 8000:(i + 1) * 8000]) else -120 for i in range(secs)])
    metro = []; even = lambda w: w.std() / (w.mean() + 1e-9) < 0.12; i = 0
    while i + 8 <= len(L):
        if even(L[i:i + 8]):
            j = i + 8
            while j < len(L) and even(L[i:j + 1]): j += 1
            metro.append((i, j)); i = j
        else: i += 1
    flat = []
    if secs >= 6:
        lo_m = mot_s < np.nanpercentile(mot_s, 35); steady = np.abs(np.diff(loud_s, prepend=loud_s[0])) < 2.0 if has_a else np.ones(secs, bool)
        z = lo_m & steady; i = 0
        while i < secs:
            if z[i]:
                j = i
                while j + 1 < secs and z[j + 1]: j += 1
                if j - i + 1 >= 6: flat.append((i, j + 1))
                i = j + 1
            else: i += 1
    starts = np.cumsum([0] + list(L[:-1]))
    return {"file": p, "fps": round(fps, 3), "duration": round(dur, 2), "shots": int(len(L)), "cuts_frames": [int(c) for c in cuts],
            "shot_lengths": [round(float(x), 3) for x in L], "asl": round(float(L.mean()), 2), "median": round(float(np.median(L)), 2),
            "cv": round(float(L.std() / L.mean()), 2) if len(L) > 1 else 0, "alpha_shots": alpha(L) if len(L) > 1 and L.std() >= 0.05 * L.mean() else None, "alpha_motion": alpha(mot_s), "alpha_loudness": alpha(loud_s) if has_a else None,
            "motion_per_s": [round(float(x), 2) for x in np.nan_to_num(mot_s)], "loudness_per_s": [round(float(x), 1) for x in loud_s],
            "metronomic": [{"from_shot": a + 1, "to_shot": b_, "at_s": round(float(starts[a]), 1)} for a, b_ in metro],
            "flat_zones": [{"from_s": a, "to_s": b_} for a, b_ in flat], "alpha_error": round(5 / np.sqrt(max(len(L), 1)), 2), "reliable": bool(len(L) >= 100)}

def words(r):
    out = []
    a = r["alpha_shots"]
    if a is None: out.append("too few shots for a 1/f reading" if r["shots"] < 16 else "shot lengths almost equal: no 1/f shape to read")
    elif a < 0.5: out.append(f"shot lengths vary {'almost at random' if a >= 0 else 'in a choppy back-and-forth'} (alpha {a}): no long-range shape, add sections of building and releasing pace")
    elif a <= 1.4: out.append(f"shot lengths fluctuate at many scales (alpha {a}): close to the 1/f pattern of attention")
    else: out.append(f"shot lengths drift slowly (alpha {a}): long sections of the same pace, add local variety inside sections")
    if r["cv"] < 0.3 and r["shots"] > 8: out.append(f"very even shot lengths (spread {r['cv']}): reads mechanical unless it is a deliberate metric montage")
    for m in r["metronomic"]: out.append(f"metronomic run: shots {m['from_shot']}-{m['to_shot']} (from {m['at_s']}s) are almost the same length")
    for f in r["flat_zones"]: out.append(f"flat zone {f['from_s']}-{f['to_s']}s: little motion and steady sound, attention will sag (cut, add movement, or change the sound)")
    if not r["reliable"] and a is not None: out.append(f"only {r['shots']} shots: the shot alpha is uncertain by about +-{r['alpha_error']}, treat it as indicative and trust the metronomic runs and flat zones more")
    return out

def plot(rs, path, labels):
    W, Hr = 1200, 120; im = Image.new("RGB", (W, len(rs) * 3 * (Hr + 12) + 20), (16, 16, 16)); d = ImageDraw.Draw(im); y = 10
    for r, lab in zip(rs, labels):
        T = r["duration"]; X = lambda t: 60 + (W - 80) * t / max(T, 1e-6)
        rows = [("shots", r["shot_lengths"], "bars"), ("motion", r["motion_per_s"], "line"), ("sound", r["loudness_per_s"], "line")]
        for name, vals, kind in rows:
            d.rectangle([60, y, W - 20, y + Hr], outline=(60, 60, 60)); d.text((4, y + 4), name[:9], fill=(200, 200, 200)); d.text((64, y + 2), lab, fill=(150, 150, 150))
            for f in r["flat_zones"]: d.rectangle([X(f["from_s"]), y + 1, X(f["to_s"]), y + Hr - 1], fill=(50, 35, 35))
            v = np.array(vals, float)
            if len(v):
                lo, hi = (v.min(), v.max()) if v.max() > v.min() else (v.min() - 1, v.max() + 1)
                if kind == "bars":
                    t = 0
                    for x in v: hh = (x - 0) / (v.max() + 1e-9) * (Hr - 6); d.rectangle([X(t), y + Hr - hh, max(X(t) + 1, X(t + x) - 1), y + Hr], fill=(120, 190, 255)); t += x
                else:
                    pts = [(X(i + 0.5), y + Hr - 3 - (x - lo) / (hi - lo) * (Hr - 6)) for i, x in enumerate(v)]
                    if len(pts) > 1: d.line(pts, fill=(255, 190, 90), width=2)
            y += Hr + 12
    im.save(path)

def cmd_analyze(p, out):
    os.makedirs(out, exist_ok=True); r = analyze(p); json.dump(r, open(os.path.join(out, "rhythm.json"), "w"), indent=1); plot([r], os.path.join(out, "rhythm.png"), [os.path.basename(p)])
    md = [f"# Rhythm: {os.path.basename(p)}", f"{r['shots']} shots in {r['duration']}s, average shot {r['asl']}s, median {r['median']}s, spread (CV) {r['cv']}",
          f"1/f slope alpha: shots {r['alpha_shots']} (+-{r['alpha_error']}), motion {r['alpha_motion']}, loudness {r['alpha_loudness']}", ""] + [f"- {w}" for w in words(r)] + ["", "rhythm.png: shot lengths, motion and loudness over time (red = flat zones)"]
    open(os.path.join(out, "rhythm.md"), "w").write("\n".join(md)); print("\n".join(md)); return r

def cmd_compare(t, ref, out):
    os.makedirs(out, exist_ok=True); a, b = analyze(t), analyze(ref); json.dump({"target": a, "reference": b}, open(os.path.join(out, "compare.json"), "w"), indent=1)
    plot([a, b], os.path.join(out, "compare.png"), ["target: " + os.path.basename(t), "reference: " + os.path.basename(ref)])
    md = [f"# Rhythm: {os.path.basename(t)} vs {os.path.basename(ref)}", "| | target | reference |", "|---|---|---|"]
    for k, lab in (("shots", "shots"), ("asl", "average shot s"), ("median", "median shot s"), ("cv", "spread (CV)"), ("alpha_shots", "alpha shots"), ("alpha_motion", "alpha motion"), ("alpha_loudness", "alpha loudness")):
        md.append(f"| {lab} | {a[k]} | {b[k]} |")
    md += ["", "## What to change"]
    if a["asl"] > b["asl"] * 1.25: md.append(f"- your shots are on average {a['asl'] / b['asl']:.1f}x longer: tighten heads and tails before removing shots")
    if a["asl"] < b["asl"] * 0.8: md.append(f"- your shots are {b['asl'] / a['asl']:.1f}x shorter on average: let key moments breathe")
    if a["cv"] < b["cv"] * 0.75: md.append("- the reference varies shot length much more: alternate quick runs with held shots")
    if (a["alpha_shots"] or 0) + 0.3 < (b["alpha_shots"] or 0): md.append("- the reference builds and releases pace over longer sections: group shots into accelerating and slowing phrases")
    md += [f"- {w}" for w in words(a)]; md.append("- to copy the reference shape onto your timeline: rhythm.py map REFERENCE DURATION plan.json")
    open(os.path.join(out, "compare.md"), "w").write("\n".join(md)); print("\n".join(md))

def cmd_map(src, T, out, shots=None, pattern="ref", fps=25.0):
    if pattern == "ref":
        r = json.load(open(src)) if src.endswith(".json") else analyze(src); r = r.get("reference", r); rel = np.array(r["shot_lengths"], float); rel = rel / rel.mean()
        cum = np.cumsum(rel) - rel / 2; cum = cum / rel.sum()
        n = shots or max(3, int(round(T / (r["asl"]))))
        f = lambda x: float(np.interp(x, cum, rel))
    else:
        n = shots or max(3, int(round(T / 2.0)))
        f = {"accelerate": lambda x: 1.8 - 1.4 * x, "decelerate": lambda x: 0.4 + 1.4 * x, "steady": lambda x: 1.0,
             "wave": lambda x: 1 + 0.6 * np.cos(2 * np.pi * 2 * x)}[pattern]
    raw = [f((i + 0.5) / n) for i in range(n)]; d = np.array(raw) / sum(raw) * T
    fr = np.maximum(2, np.round(d * fps)).astype(int); fr[-1] += int(round(T * fps)) - fr.sum()
    starts = np.concatenate([[0], np.cumsum(fr)[:-1]])
    plan = {"source": src, "pattern": pattern, "duration": T, "fps": fps, "shots": [{"shot": i + 1, "start_s": round(s / fps, 3), "length_s": round(x / fps, 3), "frames": int(x)} for i, (s, x) in enumerate(zip(starts, fr))]}
    json.dump(plan, open(out, "w"), indent=1)
    md = [f"# Shot-length map ({pattern}{', from ' + os.path.basename(src) if pattern == 'ref' else ''}): {n} shots in {T}s", "| shot | starts | length | frames |", "|---|---|---|---|"]
    md += [f"| {s['shot']} | {s['start_s']}s | {s['length_s']}s | {s['frames']} |" for s in plan["shots"]]
    open(os.path.splitext(out)[0] + ".md", "w").write("\n".join(md))
    f_ = int(round(fps)); tc = lambda x: f"{x // (3600 * f_):02d}:{x // (60 * f_) % 60:02d}:{x // f_ % 60:02d}:{x % f_:02d}"
    L = ["TITLE: planned cuts", "FCM: NON-DROP FRAME", ""]
    for i, s in enumerate(starts[1:], 1): L += [f"{i:03d}  001      V     C        {tc(int(s))} {tc(int(s) + 1)} {tc(int(s))} {tc(int(s) + 1)}  ", f" |C:ResolveColorPurple |M:cut {i} |D:1", ""]
    open(os.path.splitext(out)[0] + ".edl", "w").write("\n".join(L)); print("\n".join(md))

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "analyze": cmd_analyze(a[2], a[3])
    elif len(a) > 4 and a[1] == "compare": cmd_compare(a[2], a[3], a[4])
    elif len(a) > 4 and a[1] == "map": cmd_map(a[2], float(a[3]), a[4], int(opt("--shots")) if opt("--shots") else None, opt("--pattern", "ref"), float(opt("--fps", 25)))
    else: print(USAGE)
