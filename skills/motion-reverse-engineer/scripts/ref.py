###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

USAGE = """motion-ref: reverse-engineer a reference video into measurable facts, and check a render against it.

  python3 ref.py analyze REF.mp4 OUT_DIR [--every 0.5]
      -> OUT_DIR/report.md + report.json: size, fps, duration, frame count, cut/scene changes,
         motion-energy curve (accent peaks), estimated BPM + beat phase, dominant palette (hex),
         frames every N s + at every scene change, and a timestamped contact sheet.
  python3 ref.py frames REF.mp4 OUT_DIR 1.8 6.5 13.3      -> exact checkpoint frames
  python3 ref.py compare REF.mp4 MINE.mp4 OUT_DIR 1.8 6.5 13.3
      -> side-by-side sheet + per-checkpoint similarity (structure + colour), so you see what drifted.
Needs: ffmpeg/ffprobe, numpy, Pillow, scipy.
"""

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def probe(path):
    r = json.loads(sh(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path]).stdout)
    v = next(s for s in r["streams"] if s["codec_type"] == "video")
    num, den = map(int, v.get("avg_frame_rate", "30/1").split("/"))
    fps = num / den if den else 30
    dur = float(r["format"].get("duration", v.get("duration", 0)))
    has_audio = any(s["codec_type"] == "audio" for s in r["streams"])
    return {"width": v["width"], "height": v["height"], "fps": round(fps, 3), "duration": round(dur, 3),
            "frames": int(round(dur * fps)), "audio": has_audio}

def frame_at(path, t, out, w=None):
    vf = ["-vf", f"scale={w}:-2"] if w else []
    sh(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", *vf, out])
    return out

def small_frames(path, fps_s=10, w=96):
    info = probe(path); h = int(round(info["height"] * w / info["width"] / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"fps={fps_s},scale={w}:{h},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32), fps_s

def palette(img_paths, k=6):
    px = np.concatenate([np.asarray(Image.open(p).convert("RGB").resize((64, 114))).reshape(-1, 3) for p in img_paths]).astype(np.float32)
    rng = np.random.default_rng(0); c = px[rng.choice(len(px), k, replace=False)]
    for _ in range(12):
        lab = np.argmin(((px[:, None] - c[None]) ** 2).sum(-1), 1)
        c = np.array([px[lab == i].mean(0) if np.any(lab == i) else c[i] for i in range(k)])
    share = np.bincount(lab, minlength=k) / len(lab); order = np.argsort(-share)
    return [{"hex": "#%02X%02X%02X" % tuple(int(v) for v in c[i]), "share": round(float(share[i]), 3)} for i in order]

def bpm_estimate(path, dur):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", "11025", "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    if len(x) < 11025 * 3: return None
    hop = 256; frames = len(x) // hop
    e = np.array([np.sum(x[i * hop:(i + 1) * hop] ** 2) for i in range(frames)])
    on = np.maximum(0, np.diff(np.log1p(e * 1000))); on -= on.mean()
    ac = np.correlate(on, on, "full")[len(on) - 1:]; fr = 11025 / hop
    lags = np.arange(len(ac)) / fr; best, bv = None, -1
    for bpm in np.arange(70, 181, 0.5):
        L = 60 / bpm; score = sum(np.interp(L * m, lags, ac) for m in (1, 2, 4))
        if score > bv: bv, best = score, bpm
    period = 60 / best * fr; phases = np.arange(0, period, 0.5)
    ph = max(phases, key=lambda p: on[np.clip((p + np.arange(0, len(on) - p, period)).astype(int), 0, len(on) - 1)].sum())
    return {"bpm": float(best), "beat_s": round(60 / best, 4), "first_beat_s": round(ph / fr, 3),
            "note": "estimate; verify by ear. Often half/double of the true tempo."}

def contact(images, labels, out, cols=6, w=220):
    ims = [Image.open(p).convert("RGB") for p in images]
    h = int(w * ims[0].height / ims[0].width); rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + 28)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * w, (i // cols) * (h + 28)
        sheet.paste(im.resize((w, h)), (x, y)); d.text((x + 6, y + h + 6), lab, fill=(235, 235, 235))
    sheet.save(out); return out

def cmd_analyze(path, out, every=0.5):
    os.makedirs(out, exist_ok=True); info = probe(path); dur = info["duration"]
    g, fs = small_frames(path)
    diff = np.abs(np.diff(g, axis=0)).mean((1, 2)) if len(g) > 1 else np.zeros(1)
    hist = [np.histogram(f, 32, (0, 255))[0] / f.size for f in g]
    hd = np.array([np.abs(hist[i + 1] - hist[i]).sum() for i in range(len(hist) - 1)]) if len(hist) > 1 else np.zeros(1)
    thr = max(0.35, float(np.percentile(hd, 97)) if len(hd) else 1)
    cuts = [round(float(i + 1) / fs, 2) for i in np.where(hd > thr)[0]]
    motion = [{"t": round(i / fs, 2), "energy": round(float(v), 2)} for i, v in enumerate(diff)]
    from scipy.signal import find_peaks
    pk, _ = find_peaks(diff, distance=max(1, int(fs * 0.3)), prominence=max(0.5, float(np.std(diff)) * 0.8))
    accents = [round(float(p) / fs, 2) for p in pk]
    times = sorted(set([round(x, 2) for x in np.arange(0, dur, every)] + [max(0, c - 0.05) for c in cuts] + [round(dur - 0.05, 2)]))
    fdir = os.path.join(out, "frames"); os.makedirs(fdir, exist_ok=True)
    paths = [frame_at(path, t, os.path.join(fdir, f"f_{t:06.2f}.jpg"), 540) for t in times]
    sheet = contact(paths, [f"{t:.2f}s" for t in times], os.path.join(out, "contact_sheet.jpg"))
    pal = palette(paths[:: max(1, len(paths) // 12)])
    beat = bpm_estimate(path, dur) if info["audio"] else None
    loop = None
    if len(g) > 2:
        loop = round(float(1 - np.abs(g[0] - g[-1]).mean() / 255), 3)
    rep = {"video": info, "scene_changes_s": cuts, "accent_peaks_s": accents, "palette": pal, "music": beat,
           "loop_similarity_first_last": loop, "events_per_second": round(len(accents) / max(dur, 1e-6), 2),
           "frames_dir": fdir, "contact_sheet": sheet, "motion_energy": motion}
    json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1)
    md = [f"# Reference report: {os.path.basename(path)}",
          f"- {info['width']}x{info['height']}, {info['fps']} fps, {dur} s ({info['frames']} frames), audio: {info['audio']}",
          f"- scene changes (hard cuts/flashes): {cuts or 'none detected (continuous take)'}",
          f"- motion accents: {accents}  ->  {rep['events_per_second']} big events/s",
          f"- palette: " + ", ".join(f"{p['hex']} ({p['share']:.0%})" for p in pal),
          f"- music: {beat['bpm']} BPM, beat {beat['beat_s']} s, first beat ~{beat['first_beat_s']} s ({beat['note']})" if beat else "- music: none / not detected",
          f"- first/last frame similarity: {loop} (>0.95 suggests a seamless loop)",
          "", "Accent peaks vs beat grid:" if beat else ""]
    if beat:
        for a in accents:
            n = (a - beat["first_beat_s"]) / beat["beat_s"]
            md.append(f"  - {a:.2f}s = beat {n:.2f}" + ("  (on beat)" if abs(n - round(n)) < .15 else "  (eighth)" if abs(n * 2 - round(n * 2)) < .2 else ""))
    md += ["", f"Frames: {fdir}", f"Contact sheet: {sheet}"]
    open(os.path.join(out, "report.md"), "w").write("\n".join(md))
    print("\n".join(md))

def cmd_frames(path, out, times):
    os.makedirs(out, exist_ok=True)
    for t in times: print(frame_at(path, t, os.path.join(out, f"ref_{t:06.2f}.png")))

def cmd_compare(ref, mine, out, times):
    os.makedirs(out, exist_ok=True); rows = []; scores = []
    for t in times:
        a = frame_at(ref, t, os.path.join(out, f"ref_{t:.2f}.png"), 360); b = frame_at(mine, t, os.path.join(out, f"mine_{t:.2f}.png"), 360)
        A = np.asarray(Image.open(a).convert("RGB").resize((180, 320))).astype(np.float32)
        B = np.asarray(Image.open(b).convert("RGB").resize((180, 320))).astype(np.float32)
        ga, gb = A.mean(2), B.mean(2)
        ga, gb = (ga - ga.mean()) / (ga.std() + 1e-6), (gb - gb.mean()) / (gb.std() + 1e-6)
        struct = float((ga * gb).mean()); col = float(1 - np.abs(A.mean((0, 1)) - B.mean((0, 1))).mean() / 255)
        scores.append({"t": t, "structure": round(struct, 3), "colour": round(col, 3)}); rows += [a, b]
    contact(rows, sum([[f"REF {s['t']}s", f"MINE s={s['structure']} c={s['colour']}"] for s in scores], []),
            os.path.join(out, "compare.jpg"), cols=2, w=360)
    for s in scores:
        flag = "OK" if s["structure"] > .6 and s["colour"] > .9 else "CHECK"
        print(f"{s['t']:>6.2f}s  structure {s['structure']:+.2f}  colour {s['colour']:.2f}  {flag}")
    print("sheet:", os.path.join(out, "compare.jpg"))

if __name__ == "__main__":
    a = sys.argv
    if len(a) < 4: print(USAGE); sys.exit(1)
    if a[1] == "analyze": cmd_analyze(a[2], a[3], float(a[a.index("--every") + 1]) if "--every" in a else 0.5)
    elif a[1] == "frames": cmd_frames(a[2], a[3], [float(x) for x in a[4:]])
    elif a[1] == "compare": cmd_compare(a[2], a[3], a[4], [float(x) for x in a[5:]])
