###############
# Qiyas Sadıqov CC
###############
import csv, json, os, re, subprocess, sys, urllib.request
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

USAGE = """selects-builder: prepare raw footage the way top assistant editors and their editors do it
(Murch's numbered still boards, Baxter's selects reel ordered wide to tight, two-pass note sheets).

  python3 selects.py build CLIPS_DIR OUT_DIR [--per-scene 2] [--max-sec 8] [--scene-by auto|name|look] [--transcribe auto|off]
      -> OUT_DIR/boards/scene_<x>.jpg   numbered stills (5 per take) per scene, like a wall of frame grabs
         OUT_DIR/selects.mp4            best takes per scene, wide to tight, each with a slate card and its best window
         OUT_DIR/notes.md / notes.csv   per take: technical read + empty pass-1 (first impression) and pass-2 (timecoded) columns
         OUT_DIR/takes.json             every measurement
Per take it measures: sharpness (Laplacian variance relative to brightness), exposure (median, clipped, crushed), stability (frame-to-frame jitter),
faces and shot size (wide / medium / close from face area), audio (speech share, level, clipping) and, if
faster-whisper or openai-whisper is installed and its model is available, a transcript for searching lines.
Scenes: from names like S03_T02, sc3-tk2, 03A_2 (scene-by name) or by look (consecutive clips that look alike).
Needs: numpy, opencv-python-headless, Pillow, ffmpeg/ffprobe.
"""

VID = (".mp4", ".mov", ".m4v", ".mkv", ".mxf", ".avi", ".mts")

def probe(p):
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", p], capture_output=True, text=True).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video"); n, d = map(int, v["r_frame_rate"].split("/"))
    return n / d, int(v["width"]), int(v["height"]), float(pr["format"]["duration"]), any(s["codec_type"] == "audio" for s in pr["streams"])

def cascade(name):
    for d in [getattr(getattr(cv2, "data", None), "haarcascades", "") or "", os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"), "models"]:
        if d and os.path.exists(os.path.join(d, name)): return cv2.CascadeClassifier(os.path.join(d, name))
    try:
        os.makedirs("models", exist_ok=True); urllib.request.urlretrieve("https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/" + name, os.path.join("models", name))
        return cv2.CascadeClassifier(os.path.join("models", name))
    except Exception: return None

def sample(p, step, w):
    fps, W, H, dur, _ = probe(p); h = int(H * w / W) // 2 * 2
    pr = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", p, "-vf", f"fps={1 / step},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    out = []
    while True:
        b = pr.stdout.read(w * h * 3)
        if len(b) < w * h * 3: break
        out.append(np.frombuffer(b, np.uint8).reshape(h, w, 3))
    pr.wait(); return out

def grab(p, t, w=400):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", p, "-frames:v", "1", "-vf", f"scale={w}:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(__import__("io").BytesIO(raw)).convert("RGB") if raw else None

def audio_stats(p):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if len(a) < 1600: return {"speech_pct": 0, "level_db": None, "clipping": False}, None
    rms = np.sqrt(np.convolve(a ** 2, np.ones(160) / 160, "same")[::160] + 1e-12); thr = max(np.percentile(rms, 10) * 4, np.percentile(rms, 90) * 0.15)
    sp = rms > thr
    return {"speech_pct": round(float(sp.mean() * 100), 1), "level_db": round(float(20 * np.log10(np.sqrt((a ** 2).mean()) + 1e-9)), 1), "clipping": bool((np.abs(a) > 0.99).mean() > 1e-4)}, sp

def transcribe(p):
    try:
        from faster_whisper import WhisperModel
        segs, _ = WhisperModel("base", compute_type="int8").transcribe(p); return " ".join(s.text.strip() for s in segs)
    except Exception: pass
    try:
        import whisper
        return whisper.load_model("base").transcribe(p)["text"].strip()
    except Exception: return None

def scene_take(name):
    n = os.path.splitext(name)[0]
    m = re.search(r"(?i)(?:^|[^a-z])s(?:c|cene)?[ _\-]?(\d+[a-z]?)[ _\-]*t(?:k|ake)?[ _\-]?(\d+)", n) or re.search(r"(?i)(?:^|[^0-9])(\d+[a-z]?)[ _\-](\d+)(?:$|[^0-9])", n)
    return (m.group(1).upper(), int(m.group(2))) if m else (None, None)

def camera_shake(p, dur, bursts=3):
    vals = []
    for k in range(bursts):
        t = dur * (k + 1) / (bursts + 1); w, h = 192, 108
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{max(0, t - 0.3):.2f}", "-t", "0.6", "-i", p, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
        fr = np.frombuffer(raw, np.uint8)[: len(raw) // (w * h) * w * h].reshape(-1, h, w).astype(np.float32); win = cv2.createHanningWindow((w, h), cv2.CV_32F)
        mv = [cv2.phaseCorrelate(a, b, win)[0] for a, b in zip(fr[:-1], fr[1:])]
        if len(mv) > 3: mv = np.array(mv); vals.append(float(np.mean(np.hypot(*np.diff(mv, axis=0).T))))
    return float(np.median(vals)) if vals else 0.0

def analyze(p, fc, step):
    fps, W, H, dur, has_a = probe(p); fr = sample(p, step, 320); sharp, med, clip, crush, faces, jit = [], [], [], [], [], []
    prev = None
    for f in fr:
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY); sharp.append(float(cv2.Laplacian(g, cv2.CV_64F).var() / max(float(g.mean()), 16.0) ** 2)); y = g / 255
        med.append(float(np.median(y))); clip.append(float((y > 0.98).mean())); crush.append(float((y < 0.02).mean()))
        if fc is not None:
            fs = fc.detectMultiScale(g, 1.1, 5, minSize=(g.shape[0] // 12, g.shape[0] // 12)); faces.append(max([w * h for (_, _, w, h) in fs], default=0) / g.size)

    face_area = float(np.median([x for x in faces if x > 0])) if any(x > 0 for x in faces) else 0.0
    size = "close" if face_area > 0.08 else "medium" if face_area > 0.015 else "wide" if face_area > 0 else "wide/no face"
    shake = camera_shake(p, dur)
    au, sp = audio_stats(p) if has_a else ({"speech_pct": 0, "level_db": None, "clipping": False}, None)
    s = np.array(sharp); q = s / (np.median(s) + 1e-6)
    win = max(1, int(min(dur, 8) / step)); best0 = 0
    if len(q) > win: best0 = int(np.argmax(np.convolve(q, np.ones(win), "valid")))
    return {"clip": p, "name": os.path.basename(p), "duration": round(dur, 2), "fps": round(fps, 3), "size": size, "face_area": round(face_area, 4),
            "face_pct": round(float(np.mean([x > 0 for x in faces]) * 100), 1) if faces else 0, "sharpness": round(float(np.median(sharp)), 5) if sharp else 0,
            "exposure_median": round(float(np.median(med)), 3) if med else 0, "clipped_pct": round(float(np.mean(clip) * 100), 2) if clip else 0,
            "crushed_pct": round(float(np.mean(crush) * 100), 2) if crush else 0, "shake": round(shake, 3), "audio": au, "best_start": round(best0 * step, 2)}

def score_set(takes):
    for t in takes:
        peers = [u["sharpness"] for u in takes if u["scene"] == t["scene"] and u["size"] == t["size"]]; ref = max(peers) + 1e-6
        s_sharp = float(np.clip(t["sharpness"] / ref, 0, 1))
        e = t["exposure_median"]; s_exp = float(np.clip(1 - abs(e - 0.42) / 0.35, 0, 1)) * (0.5 if t["clipped_pct"] > 3 else 1) * (0.7 if t["crushed_pct"] > 8 else 1)
        s_stab = float(np.clip(1 - t["shake"] / 1.2, 0, 1))
        a = t["audio"]; s_aud = 0.6 if a["level_db"] is None else float(np.clip(0.4 + a["speech_pct"] / 100, 0, 1)) * (0.4 if a["clipping"] else 1)
        s_face = 1.0 if t["face_pct"] > 50 else 0.7
        t["score"] = round(100 * (0.3 * s_sharp + 0.2 * s_exp + 0.2 * s_stab + 0.15 * s_aud + 0.15 * s_face), 1)
        notes = []
        if s_sharp < 0.6: notes.append("soft (focus or motion blur)")
        if t["clipped_pct"] > 3: notes.append(f"{t['clipped_pct']}% blown highlights")
        if t["crushed_pct"] > 8: notes.append(f"{t['crushed_pct']}% crushed shadows")
        if e < 0.2: notes.append("dark")
        if e > 0.7: notes.append("bright")
        if s_stab < 0.6: notes.append("shaky")
        if a["clipping"]: notes.append("audio clipping")
        if a["level_db"] is not None and a["level_db"] < -40: notes.append("very quiet audio")
        t["auto_read"] = ", ".join(notes) if notes else "clean: sharp, steady, well exposed"

def group_scenes(takes, mode):
    named = [scene_take(t["name"]) for t in takes]
    if mode == "name" or (mode == "auto" and all(s for s, _ in named)):
        for t, (s, k) in zip(takes, named): t["scene"], t["take"] = s or "?", k or 0
        return
    hs = []
    for t in takes:
        im = grab(t["clip"], t["duration"] / 2, 160); a = np.asarray(im) if im else np.zeros((90, 160, 3), np.uint8)
        hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV); h = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256]); hs.append(cv2.normalize(h, h).flatten())
    sc, k = 1, 1
    for i, t in enumerate(takes):
        if i and cv2.compareHist(hs[i - 1], hs[i], cv2.HISTCMP_CORREL) < 0.6: sc += 1; k = 1
        t["scene"], t["take"] = str(sc), k; k += 1

def font(sz):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", "/System/Library/Fonts/Helvetica.ttc", "C:/Windows/Fonts/arialbd.ttf"]:
        if os.path.exists(f): return ImageFont.truetype(f, sz)
    return ImageFont.load_default()

def boards(takes, out):
    os.makedirs(os.path.join(out, "boards"), exist_ok=True); tw = 300; no = 1
    for sc in sorted({t["scene"] for t in takes}, key=lambda x: (len(x), x)):
        rows = [t for t in takes if t["scene"] == sc]; tiles = []
        for t in rows:
            ims = [grab(t["clip"], t["duration"] * f, tw) for f in (0.08, 0.3, 0.5, 0.7, 0.92)]; tiles.append((t, ims))
        th = next((im.height for _, ims in tiles for im in ims if im), 170)
        B = Image.new("RGB", (5 * (tw + 8) + 270, len(tiles) * (th + 12) + 40), (18, 18, 18)); d = ImageDraw.Draw(B)
        d.text((10, 10), f"SCENE {sc}", fill=(255, 255, 255), font=font(20))
        for r, (t, ims) in enumerate(tiles):
            y = 40 + r * (th + 12)
            d.text((10, y + 4), f"T{t['take']}  {t['name'][:22]}", fill=(255, 220, 120), font=font(14))
            d.text((10, y + 26), f"score {t['score']}  {t['size']}", fill=(220, 220, 220), font=font(13))
            d.text((10, y + 46), t["auto_read"][:34], fill=(170, 170, 170), font=font(11))
            for c, im in enumerate(ims):
                if im is None: continue
                x = 262 + c * (tw + 8); B.paste(im, (x, y)); d.rectangle([x, y, x + 34, y + 18], fill=(0, 0, 0)); d.text((x + 4, y + 2), f"{no}", fill=(255, 255, 255), font=font(12)); no += 1
        B.save(os.path.join(out, "boards", f"scene_{sc}.jpg"), quality=88)

def slate(text_lines, path, W=1280, H=720):
    im = Image.new("RGB", (W, H), (12, 12, 12)); d = ImageDraw.Draw(im)
    for i, (t, sz, col) in enumerate(text_lines): d.text((80, 220 + i * 70), t, fill=col, font=font(sz))
    im.save(path)

def reel(takes, out, per_scene, max_sec):
    tmp = os.path.join(out, "_tmp"); os.makedirs(tmp, exist_ok=True); parts = []; order = {"wide/no face": 0, "wide": 1, "medium": 2, "close": 3}
    chosen = []
    for sc in sorted({t["scene"] for t in takes}, key=lambda x: (len(x), x)):
        best = sorted([t for t in takes if t["scene"] == sc], key=lambda t: -t["score"])[:per_scene]
        chosen += sorted(best, key=lambda t: (order.get(t["size"], 1), t["face_area"]))
    for i, t in enumerate(chosen):
        sp = os.path.join(tmp, f"s{i}.png"); slate([(f"SCENE {t['scene']}  TAKE {t['take']}", 54, (255, 255, 255)), (t["name"], 30, (255, 210, 120)), (f"score {t['score']}  {t['size']}  {t['auto_read']}", 26, (200, 200, 200))], sp)
        a = os.path.join(tmp, f"a{i}.mp4"); b = os.path.join(tmp, f"b{i}.mp4"); dur = min(max_sec, t["duration"] - t["best_start"])
        vf = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=25,format=yuv420p"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-t", "1.2", "-i", sp, "-f", "lavfi", "-t", "1.2", "-i", "anullsrc=r=48000:cl=stereo", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-shortest", a], check=True)
        has_a = probe(t["clip"])[4]
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t["best_start"]), "-t", f"{dur:.2f}", "-i", t["clip"]]
        if has_a: cmd += ["-vf", vf, "-af", "aresample=48000,aformat=channel_layouts=stereo"]
        else: cmd += ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a", "-vf", vf]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-ar", "48000", "-ac", "2", b]
        subprocess.run(cmd, check=True); parts += [a, b]
    lst = os.path.join(tmp, "list.txt"); open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(out, "selects.mp4")], check=True)
    for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
    os.rmdir(tmp); return chosen

def build(folder, out, per_scene=2, max_sec=8, scene_by="auto", trans="auto"):
    os.makedirs(out, exist_ok=True); clips = [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(VID)]
    if not clips: raise SystemExit("no video clips found")
    fc = cascade("haarcascade_frontalface_default.xml"); takes = []
    for i, c in enumerate(clips, 1):
        sys.stderr.write(f"[{i}/{len(clips)}] {os.path.basename(c)}\n"); t = analyze(c, fc, 0.5)
        if trans != "off": t["transcript"] = transcribe(c)
        takes.append(t)
    group_scenes(takes, scene_by); score_set(takes); boards(takes, out); chosen = reel(takes, out, per_scene, max_sec)
    json.dump(takes, open(os.path.join(out, "takes.json"), "w"), indent=1)
    cols = ["scene", "take", "name", "duration", "score", "size", "auto_read", "speech_pct", "pass1_first_impression", "pass2_timecoded_notes", "circle"]
    with open(os.path.join(out, "notes.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for t in sorted(takes, key=lambda t: (t["scene"], t["take"])): w.writerow([t["scene"], t["take"], t["name"], t["duration"], t["score"], t["size"], t["auto_read"], t["audio"]["speech_pct"], "", "", "yes" if t in chosen else ""])
    md = [f"# Selects: {len(takes)} takes, {len({t['scene'] for t in takes})} scenes", "",
          "Pass 1: watch each take once, straight through, and write only your first feeling (what moved you, what bored you). Do not stop, do not cut.",
          "Pass 2: rewatch the circled takes and write timecoded notes (best line readings, reactions, usable pieces).", ""]
    for sc in sorted({t["scene"] for t in takes}, key=lambda x: (len(x), x)):
        md += [f"## Scene {sc}  (boards/scene_{sc}.jpg)", "| take | clip | score | size | technical read | selected | pass 1 | pass 2 |", "|---|---|---|---|---|---|---|---|"]
        md += [f"| {t['take']} | {t['name']} | {t['score']} | {t['size']} | {t['auto_read']} | {'yes' if t in chosen else ''} |  |  |" for t in sorted([t for t in takes if t["scene"] == sc], key=lambda t: t["take"])]
        md.append("")
    if any(t.get("transcript") for t in takes): md += ["## Transcripts"] + [f"- **{t['name']}**: {t['transcript']}" for t in takes if t.get("transcript")]
    elif trans != "off": md += ["(no transcript: install faster-whisper or openai-whisper with a downloadable model to search lines)"]
    open(os.path.join(out, "notes.md"), "w").write("\n".join(md)); print("\n".join(md[:30])); print(f"\n-> selects.mp4 ({len(chosen)} takes, wide to tight per scene), boards/, notes.md, notes.csv")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "build": build(a[2], a[3], int(opt("--per-scene", 2)), float(opt("--max-sec", 8)), opt("--scene-by", "auto"), opt("--transcribe", "auto"))
    else: print(USAGE)
