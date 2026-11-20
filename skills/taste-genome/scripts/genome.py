###############
# Qiyas Sadıqov CC
###############
import csv, json, os, re, shutil, subprocess, sys
import numpy as np
import cv2

USAGE = """taste-genome: learn which style choices actually perform, from your own published videos + their stats.

  python3 genome.py extract VIDEOS_DIR features.csv [--ocr]
      -> one row of measurable style features per video (pacing, hook, motion, colour, faces, text, audio).
  python3 genome.py learn features.csv metrics.csv OUT_DIR [--metric saves] [--metric views ...]
      -> OUT_DIR/genome.md (what separates your top third from your bottom third, with effect sizes and
         rank correlations), genome.json (target ranges = your style DNA, usable as edit rules).
metrics.csv: a "file" column matching the video file names, then any numeric columns
(views, saves, shares, avg_watch_pct, follows...). Export from Instagram/TikTok insights or type it.
Honest limits: needs >= 8 videos for hints, >= 20 for anything you should trust; correlation is not cause.
Needs: ffmpeg, numpy, opencv-python-headless; tesseract optional (--ocr).
"""

def run(c): return subprocess.run(c, capture_output=True, text=True)

FEATURES = ["duration_s", "cuts_per_s", "avg_shot_s", "first_cut_s", "first_motion_s", "motion_energy", "brightness",
            "saturation", "warmth", "contrast", "face_ratio", "text_ratio", "loudness_lufs", "audio_start_s", "music_bpm"]

def feats(p, ocr=False):
    r = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", p]).stdout)
    v = next(s for s in r["streams"] if s["codec_type"] == "video"); dur = float(r["format"]["duration"]); has_a = any(s["codec_type"] == "audio" for s in r["streams"])
    w = 144; h = int(round(v["height"] * w / v["width"] / 2) * 2); fs = 6
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-vf", f"fps={fs},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    F = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    G = F.mean(3); motion = np.abs(np.diff(G, axis=0)).mean((1, 2)) if len(G) > 1 else np.zeros(1)
    hist = [np.histogram(g, 32, (0, 255))[0] / g.size for g in G]
    hd = np.array([np.abs(hist[i + 1] - hist[i]).sum() for i in range(len(hist) - 1)]) if len(hist) > 1 else np.zeros(1)
    cuts = [(i + 1) / fs for i in np.where(hd > max(0.35, float(np.median(hd) + 8 * np.median(np.abs(hd - np.median(hd))))))[0]]
    hsv = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2HSV) for f in F[::2]])
    sample = F[::fs]; faces = None
    try:
        xml = os.path.join(getattr(getattr(cv2, "data", None), "haarcascades", ""), "haarcascade_frontalface_default.xml")
        face = cv2.CascadeClassifier(xml) if os.path.exists(xml) else None
        if face is not None and not face.empty():
            faces = sum(1 for f in sample if len(face.detectMultiScale(cv2.cvtColor(cv2.resize(f, (w * 2, h * 2)), cv2.COLOR_BGR2GRAY), 1.15, 5)) > 0)
    except Exception: pass
    text_ratio = None
    if ocr and shutil.which("tesseract"):
        hits = 0; tmp = "/tmp/_g.png"
        for t in np.arange(0, dur, 1.0):
            run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", p, "-frames:v", "1", tmp])
            words = [x for x in run(["tesseract", tmp, "-", "--psm", "11"]).stdout.split() if len(x) > 2]; hits += len(words) >= 2
        text_ratio = hits / max(1, int(np.ceil(dur)))
    lufs, a_start, bpm = None, None, None
    if has_a:
        out = run(["ffmpeg", "-hide_banner", "-i", p, "-af", "ebur128", "-f", "null", "-"]).stderr; I = re.findall(r"I:\s+(-?[\d.]+) LUFS", out); lufs = float(I[-1]) if I else None
        x = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", "8000", "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
        if len(x) > 8000:
            win = 800; db = 20 * np.log10(np.array([np.sqrt(np.mean(x[i:i + win] ** 2)) + 1e-9 for i in range(0, len(x) - win, win)]))
            a_start = float(np.argmax(db > -45)) / 10 if (db > -45).any() else dur
            hop = 128; e = np.array([np.sum(x[i:i + hop] ** 2) for i in range(0, len(x) - hop, hop)]); on = np.maximum(0, np.diff(np.log1p(e * 1e3))); on -= on.mean()
            ac = np.correlate(on, on, "full")[len(on) - 1:]; lags = np.arange(len(ac)) / (8000 / hop)
            bpm = float(max(np.arange(70, 181, 1.0), key=lambda b: sum(np.interp(60 / b * m, lags, ac) for m in (1, 2, 4))))
    b, g_, r_ = [F[..., c].mean() for c in range(3)]
    return {"file": os.path.basename(p), "duration_s": round(dur, 2), "cuts_per_s": round(len(cuts) / dur, 3), "avg_shot_s": round(dur / (len(cuts) + 1), 2),
            "first_cut_s": round(cuts[0], 2) if cuts else round(dur, 2), "first_motion_s": round(next((i / fs for i, m in enumerate(motion) if m > 1), dur), 2),
            "motion_energy": round(float(motion.mean()), 2), "brightness": round(float(hsv[..., 2].mean() / 255), 3), "saturation": round(float(hsv[..., 1].mean() / 255), 3),
            "warmth": round(float((r_ - b) / 255), 3), "contrast": round(float(G.std() / 255), 3), "face_ratio": round(faces / max(1, len(sample)), 2) if faces is not None else None,
            "text_ratio": text_ratio, "loudness_lufs": lufs, "audio_start_s": a_start, "music_bpm": bpm}

def extract(d, out, ocr=False):
    vids = sorted(f for f in os.listdir(d) if f.lower().endswith((".mp4", ".mov", ".m4v", ".webm")))
    rows = []
    for v in vids:
        rows.append(feats(os.path.join(d, v), ocr)); print(f"{v}: {rows[-1]['cuts_per_s']} cuts/s, shot {rows[-1]['avg_shot_s']} s, faces {rows[-1]['face_ratio']}")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, ["file"] + FEATURES); w.writeheader(); [w.writerow(r) for r in rows]
    print(f"{len(rows)} videos -> {out}")

def rank(x):
    x = np.asarray(x, float); r = np.empty(len(x)); r[np.argsort(x, kind="mergesort")] = np.arange(len(x))
    for v in np.unique(x): r[x == v] = r[x == v].mean()
    return r
def spearman(a, b): ra, rb = rank(a), rank(b); return float(np.corrcoef(ra, rb)[0, 1]) if np.std(ra) and np.std(rb) else 0.0

def learn(fcsv, mcsv, out, metrics):
    os.makedirs(out, exist_ok=True)
    F = {r["file"]: r for r in csv.DictReader(open(fcsv))}; M = {os.path.basename(r["file"]): r for r in csv.DictReader(open(mcsv))}
    files = [f for f in F if f in M]; n = len(files)
    if n < 4: raise SystemExit(f"only {n} videos matched between the two files; need at least 8")
    metrics = metrics or [c for c in next(iter(M.values())).keys() if c != "file"]
    md = [f"# Taste genome ({n} videos)", "", "Reliability: " + ("weak hints only (<8 videos)" if n < 8 else "hints (8-19 videos)" if n < 20 else "usable (20+ videos)"), ""]
    dna = {"videos": n, "metrics": {}}
    for m in metrics:
        y = np.array([float(M[f][m] or 0) for f in files]); order = np.argsort(-y); k = max(1, n // 3)
        top, bot = [files[i] for i in order[:k]], [files[i] for i in order[-k:]]
        rows = []
        for feat in FEATURES:
            vals = [F[f][feat] for f in files]
            if any(v in ("", None, "None") for v in vals): continue
            x = np.array([float(v) for v in vals]); rho = spearman(x, y)
            tv = np.array([float(F[f][feat]) for f in top]); bv = np.array([float(F[f][feat]) for f in bot])
            spread = np.std(x) + 1e-9; eff = (np.median(tv) - np.median(bv)) / spread
            rows.append((abs(rho) * 0.6 + min(abs(eff), 2) / 2 * 0.4, feat, rho, eff, float(np.median(tv)), float(np.median(bv)), (float(np.percentile(tv, 25)), float(np.percentile(tv, 75)))))
        rows.sort(reverse=True)
        md += [f"## {m}: what your top third does differently", "", "| feature | top third (median) | bottom third | rank corr | effect |", "|---|---|---|---|---|"]
        md += [f"| {f} | {t:.2f} | {b:.2f} | {r:+.2f} | {e:+.2f} sd |" for _, f, r, e, t, b, _ in rows[:8]]
        strong = [(f, r, e, t, rng) for _, f, r, e, t, b, rng in rows if abs(r) >= 0.3 or abs(e) >= 0.8][:6]
        md += ["", "Rules to try next (from your own winners):"] + [f"- {'raise' if e > 0 else 'lower'} **{f}** toward {t:.2f} (your winners sit in {rng[0]:.2f} to {rng[1]:.2f})" for f, r, e, t, rng in strong] + [""]
        dna["metrics"][m] = {"top_files": top, "rules": [{"feature": f, "direction": "up" if e > 0 else "down", "target": round(t, 3), "range": [round(rng[0], 3), round(rng[1], 3)], "rho": round(r, 2), "effect_sd": round(e, 2)} for f, r, e, t, rng in strong]}
    md += ["Correlation is not cause: test one rule at a time on new posts and re-run learn monthly."]
    open(os.path.join(out, "genome.md"), "w").write("\n".join(md)); json.dump(dna, open(os.path.join(out, "genome.json"), "w"), indent=1); print("\n".join(md))

if __name__ == "__main__":
    a = sys.argv
    if len(a) > 3 and a[1] == "extract": extract(a[2], a[3], "--ocr" in a)
    elif len(a) > 4 and a[1] == "learn": learn(a[2], a[3], a[4], [a[i + 1] for i, x in enumerate(a) if x == "--metric"])
    else: print(USAGE)
