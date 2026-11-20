###############
# Qiyas Sadıqov CC
###############
import json, os, re, shutil, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw

USAGE = """retention-oracle: predict where viewers drop off a short video BEFORE posting.

  python3 retention.py analyze VIDEO.mp4 OUT_DIR [--bpm 120] [--platform reels|tiktok|shorts]
      -> OUT_DIR/report.md, report.json, risk.png (per-second risk curve), key frames.

Measures: first-motion delay, hook timing (first cut / first on-screen text), shot lengths,
dead stretches (no motion, no new info), on-screen text density vs reading time (OCR),
text inside platform UI zones, silence (start + gaps), loudness (LUFS / true peak),
cut-to-beat alignment (given or estimated BPM).
Needs: ffmpeg/ffprobe, numpy, Pillow, opencv-python-headless; tesseract optional (text checks).
"""

ZONES = {"reels": (0.13, 0.22, 0.11), "tiktok": (0.12, 0.25, 0.14), "shorts": (0.10, 0.20, 0.12)}

def run(cmd): return subprocess.run(cmd, capture_output=True, text=True)

def probe(p):
    r = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", p]).stdout)
    v = next(s for s in r["streams"] if s["codec_type"] == "video")
    n, d = map(int, v["avg_frame_rate"].split("/"))
    return {"w": v["width"], "h": v["height"], "fps": n / d if d else 30, "dur": float(r["format"]["duration"]),
            "audio": any(s["codec_type"] == "audio" for s in r["streams"])}

def gray_stream(p, fps=10, w=108):
    i = probe(p); h = int(round(i["h"] * w / i["w"] / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-vf", f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)

def audio_env(p, sr=8000):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32), sr

def loudness(p):
    out = run(["ffmpeg", "-hide_banner", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", out); TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)
    return (float(I[-1]) if I else None, float(TP[-1]) if TP else None)

def est_bpm(x, sr, bpm=None):
    hop = 128; e = np.array([np.sum(x[i:i + hop] ** 2) for i in range(0, len(x) - hop, hop)])
    on = np.maximum(0, np.diff(np.log1p(e * 1e3))); on -= on.mean(); fr = sr / hop
    ac = np.correlate(on, on, "full")[len(on) - 1:]; lags = np.arange(len(ac)) / fr
    best = bpm or max(np.arange(70, 181, 0.5), key=lambda b: sum(np.interp(60 / b * m, lags, ac) for m in (1, 2, 4)))
    period = 60 / best * fr
    ph = max(np.arange(0, period, 0.5), key=lambda q: on[np.clip((q + np.arange(0, len(on) - q, period)).astype(int), 0, len(on) - 1)].sum())
    return float(best), (ph + 1) / fr

def ocr_boxes(img_path):
    if not shutil.which("tesseract"): return None
    r = run(["tesseract", img_path, "-", "--psm", "11", "tsv"])
    boxes = []
    for line in r.stdout.splitlines()[1:]:
        c = line.split("\t")
        if len(c) == 12 and c[11].strip() and c[10] not in ("-1",) and float(c[10]) > 55 and len(c[11].strip()) > 1:
            boxes.append((int(c[6]), int(c[7]), int(c[8]), int(c[9]), c[11].strip()))
    return boxes

def analyze(path, out, bpm=None, platform="reels"):
    os.makedirs(out, exist_ok=True); info = probe(path); dur = info["dur"]
    g = gray_stream(path); fs = 10
    motion = np.abs(np.diff(g, axis=0)).mean((1, 2)) if len(g) > 1 else np.zeros(1)
    cfs = min(60, round(info["fps"])); gc = gray_stream(path, cfs)
    hc = [np.histogram(f, 32, (0, 255))[0] / f.size for f in gc]
    hd = np.array([np.abs(hc[i + 1] - hc[i]).sum() for i in range(len(hc) - 1)]) if len(hc) > 1 else np.zeros(1)
    cuts = [round(float(i + 1) / cfs, 3) for i in np.where(hd > max(0.35, float(np.median(hd) + 8 * np.median(np.abs(hd - np.median(hd))))))[0]]
    first_motion = next((i / fs for i, m in enumerate(motion) if m > 1.0), dur)
    bounds = [0] + cuts + [dur]; shots = [round(b - a, 2) for a, b in zip(bounds, bounds[1:])]
    dead, run_start = [], None
    for i, m in enumerate(motion):
        t = i / fs
        if m < 0.6 and not any(abs(t - c) < 0.15 for c in cuts):
            run_start = t if run_start is None else run_start
        else:
            if run_start is not None and t - run_start > 0.8: dead.append((round(run_start, 2), round(t, 2)))
            run_start = None
    if run_start is not None and dur - run_start > 0.8: dead.append((round(run_start, 2), round(dur, 2)))
    fdir = os.path.join(out, "frames"); os.makedirs(fdir, exist_ok=True)
    top, bot, right = ZONES.get(platform, ZONES["reels"]); texts = []; zone_hits = []
    for t in np.arange(0, dur, 0.5):
        fp = os.path.join(fdir, f"t{t:05.1f}.png")
        run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", fp])
        b = ocr_boxes(fp) if os.path.exists(fp) else None
        if b is None: texts = None; break
        words = [w for *_, w in b]; texts.append({"t": round(float(t), 1), "words": len(words), "text": " ".join(words)[:80]})
        H, W = info["h"], info["w"]
        for x, y, w, h, wd in b:
            if y < top * H or y + h > (1 - bot) * H or x + w > (1 - right) * W:
                zone_hits.append({"t": round(float(t), 1), "word": wd})
    first_text = next((x["t"] for x in texts if x["words"] > 0), None) if texts else None
    sil_start, gaps, lufs, tp = None, [], None, None
    tempo = None
    if info["audio"]:
        x, sr = audio_env(path); win = sr // 10
        rms = np.array([np.sqrt(np.mean(x[i:i + win] ** 2) + 1e-12) for i in range(0, len(x) - win, win)])
        db = 20 * np.log10(rms + 1e-9); quiet = db < -45
        sil_start = round(float(np.argmax(~quiet)) / 10, 2) if quiet.any() and not quiet.all() else (dur if quiet.all() else 0.0)
        k = 0
        while k < len(quiet):
            if quiet[k]:
                j = k
                while j < len(quiet) and quiet[j]: j += 1
                if (j - k) / 10 > 0.6 and k > 0: gaps.append((round(k / 10, 1), round(j / 10, 1)))
                k = j
            else: k += 1
        lufs, tp = loudness(path)
        b0, ph = est_bpm(x, sr, bpm); tempo = {"bpm": float(b0), "first_beat": round(float(ph), 3)}
    off_beat = []
    if tempo and cuts:
        beat = 60 / tempo["bpm"]
        for c in cuts:
            n = (c - tempo["first_beat"]) / (beat / 2)
            if abs(n - round(n)) * beat / 2 > 0.07: off_beat.append(c)
    secs = int(np.ceil(dur)); risk = np.zeros(secs); fixes = []
    def add(t0, t1, v):
        for s in range(int(t0), min(secs, int(np.ceil(t1)) or 1)): risk[s] += v
    hook = min([c for c in cuts] + ([first_text] if first_text is not None else []) + [dur])
    if first_motion > 0.3: add(0, 1, 30); fixes.append(f"Nothing moves until {first_motion:.1f} s: start mid-action, frame 0 must move.")
    if hook > 1.5: add(0, 3, 25); fixes.append(f"Hook arrives at {hook:.1f} s (first cut or text). Put the hook line/text on screen in the first 1.0 s.")
    for a, b in dead: add(a, b, 25); fixes.append(f"Dead stretch {a}-{b} s (no motion, no cut): cut it, punch-in, or add B-roll/text.")
    for i, s in enumerate(shots):
        if s > 2.5: add(bounds[i], bounds[i + 1], 15); fixes.append(f"Shot {bounds[i]:.1f}-{bounds[i+1]:.1f} s lasts {s:.1f} s: split it or move the camera (target 1.2-1.6 s).")
    if sil_start and sil_start > 0.25: add(0, 1, 20); fixes.append(f"Audio starts at {sil_start:.1f} s: sound must start on frame 0.")
    for a, b in gaps: add(a, b, 15); fixes.append(f"Silence {a}-{b} s: fill with music/ambience or cut it.")
    if texts:
        for x in texts:
            if x["words"] > 14: add(x["t"], x["t"] + 0.5, 10)
        heavy = [x["t"] for x in texts if x["words"] > 14]
        if heavy: fixes.append(f"Too much text on screen at {heavy[:5]} s (>14 words): cut to the key words.")
        if zone_hits: add(0, 0, 0); fixes.append(f"Text inside {platform} UI zones (hidden by buttons/caption): {[z['t'] for z in zone_hits][:6]} s.")
    if off_beat: fixes.append(f"Cuts off the beat/eighth: {off_beat[:8]} s. Snap them (use beat-snap-reeditor).")
    if lufs is not None and (lufs < -16 or lufs > -11): fixes.append(f"Loudness {lufs} LUFS: master to about -13 LUFS for Reels/TikTok.")
    if tp is not None and tp > -1.0: fixes.append(f"True peak {tp} dBFS: limit to -1 dBTP or lower.")
    risk = np.clip(risk, 0, 100); score = int(max(0, 100 - risk.mean() * 1.2 - len(off_beat) * 1.5))
    drop = int(np.argmax(risk)) if risk.max() > 0 else None
    W, H = 900, 300; im = Image.new("RGB", (W, H), (250, 249, 246)); d = ImageDraw.Draw(im)
    for s, v in enumerate(risk):
        x0 = 40 + s * (W - 60) / max(secs, 1); x1 = 40 + (s + 1) * (W - 60) / max(secs, 1) - 3
        col = (217, 72, 65) if v >= 40 else (240, 166, 60) if v >= 20 else (90, 170, 110)
        d.rectangle([x0, H - 30 - v * 2.3, x1, H - 30], fill=col); d.text((x0, H - 24), f"{s}s", fill=(60, 60, 60))
    d.text((40, 8), f"Drop-off risk per second   score {score}/100", fill=(20, 20, 20)); im.save(os.path.join(out, "risk.png"))
    rep = {"video": info, "score": score, "likely_drop_second": drop, "first_motion_s": first_motion, "hook_s": hook,
           "cuts": cuts, "shots": shots, "dead": dead, "first_text_s": first_text, "text": texts, "zone_hits": zone_hits,
           "audio_start_s": sil_start, "silence_gaps": gaps, "lufs": lufs, "true_peak": tp, "tempo": tempo,
           "off_beat_cuts": off_beat, "risk_per_second": risk.tolist(), "fixes": fixes}
    json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1)
    md = [f"# Retention report: {os.path.basename(path)}", f"**Score {score}/100**" + (f", highest drop risk at second {drop}" if drop is not None else ""),
          f"- {info['w']}x{info['h']}, {dur:.2f} s, {len(cuts)} cuts, avg shot {np.mean(shots):.2f} s",
          f"- first motion {first_motion:.1f} s, hook {hook:.1f} s, audio starts {sil_start} s, loudness {lufs} LUFS / TP {tp}",
          f"- tempo {tempo}" if tempo else "- no audio", "", "## Fixes (most important first)"] + [f"{i+1}. {f}" for i, f in enumerate(fixes)] + ["", "Chart: risk.png"]
    open(os.path.join(out, "report.md"), "w").write("\n".join(md)); print("\n".join(md))

if __name__ == "__main__":
    a = sys.argv
    if len(a) < 4 or a[1] != "analyze": print(USAGE); sys.exit(1)
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    analyze(a[2], a[3], float(opt("--bpm")) if opt("--bpm") else None, opt("--platform", "reels"))
