###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys, urllib.request
import numpy as np
import cv2
from PIL import Image, ImageDraw

USAGE = """rule-of-six-judge: score every cut of a finished edit against Walter Murch's Rule of Six, measuring what can be
measured and preparing the rest (emotion, story) for human/Claude judgement.

  python3 sixjudge.py judge EDIT.mp4 OUT_DIR [--worst 10] [--beat on|off] [--tc-start 00:00:00:00]
      -> OUT_DIR/report.md, cuts.json, cut_NNN.jpg (outgoing tail | incoming head, attention dots, motion arrows),
         markers.edl (Resolve markers on the weakest cuts)

Measured per cut (Murch weights in brackets, emotion 51% and story 23% are judged by looking, not measured):
  rhythm (10)     shot length vs neighbours, flash frames, cut offset from the musical beat when music is present,
                  audio jump at the cut (cutting inside a word / level jump)
  eye trace (7)   distance between where attention sits at the end of shot A and at the start of shot B
                  (spectral-residual saliency, faces weighted up); suggests trims of A and B that line attention up
  2D plane (5)    screen direction: dominant motion direction flips across the cut (possible 180-degree problem)
  3D space (4)    jump cut: shot B is nearly the same framing as shot A (30-degree / size-change rule)
Technical score per cut = weighted rhythm, eye trace, plane, space (0-100). The report ranks the weakest cuts.
Needs: numpy, opencv-python-headless, Pillow, ffmpeg/ffprobe.
"""

def probe(path):
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path], capture_output=True, text=True).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video"); n, d = map(int, v["r_frame_rate"].split("/"))
    return n / d, int(v["width"]), int(v["height"]), any(s["codec_type"] == "audio" for s in pr["streams"])

def cascade(name):
    for d in [getattr(getattr(cv2, "data", None), "haarcascades", "") or "", os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"), "models"]:
        if d and os.path.exists(os.path.join(d, name)): return cv2.CascadeClassifier(os.path.join(d, name))
    try:
        os.makedirs("models", exist_ok=True); urllib.request.urlretrieve("https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/" + name, os.path.join("models", name))
        return cv2.CascadeClassifier(os.path.join("models", name))
    except Exception: return None

def read_all(path, w, h):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    out = []
    while True:
        b = p.stdout.read(w * h * 3)
        if len(b) < w * h * 3: break
        out.append(np.frombuffer(b, np.uint8).reshape(h, w, 3))
    p.wait(); return out

def detect_cuts(fr):
    hs, df = [], [0.0]
    for f in fr:
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV); h = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256]); hs.append(cv2.normalize(h, h).flatten())
    for i in range(1, len(fr)):
        hd = 1 - cv2.compareHist(hs[i - 1], hs[i], cv2.HISTCMP_CORREL)
        pd = np.abs(fr[i].astype(np.int16) - fr[i - 1]).mean() / 255
        df.append(hd * 0.6 + pd * 2.0)
    df = np.array(df); cuts = []
    thr = np.array([max(0.035, (np.median(df[max(1, i - 12): i + 12]) + 1e-4) * 6) for i in range(len(df))]); high = df > thr; high[:2] = False
    def run(i):
        j, k = i, i
        while j - 1 >= 2 and high[j - 1]: j -= 1
        while k + 1 < len(df) and high[k + 1]: k += 1
        return k - j + 1
    for i in range(2, len(df)):
        if not high[i]: continue
        short = run(i) <= 2
        nb = max([df[j] for j in (i - 1, i + 1) if 1 <= j < len(df) and not (short and high[j])], default=0.0)
        if df[i] > nb * 2.5 and (not cuts or i - cuts[-1] > 2 or (short and run(cuts[-1]) <= 2)): cuts.append(i)
    return cuts, df

def hue_hist(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV); h = cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 4], [0, 180, 0, 256, 0, 256]); return cv2.normalize(h, h).flatten()

def saliency(rgb):
    g = cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (64, 64)).astype(np.float32)
    F = np.fft.fft2(g); L = np.log(np.abs(F) + 1e-6); P = np.angle(F)
    R = L - cv2.blur(L, (3, 3)); S = np.abs(np.fft.ifft2(np.exp(R + 1j * P))) ** 2
    S = cv2.GaussianBlur(S, (0, 0), 2.5); return cv2.resize(S / (S.max() + 1e-9), (rgb.shape[1], rgb.shape[0]))

def attention(rgb, fc):
    h, w = rgb.shape[:2]
    if fc is not None:
        fs = fc.detectMultiScale(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), 1.1, 5, minSize=(h // 10, h // 10))
        if len(fs):
            x, y, fw, fh = max(fs, key=lambda b: b[2] * b[3]); return np.array([(x + fw / 2) / w, (y + fh * 0.4) / h]), "face", fw * fh / (w * h)
    S = saliency(rgb); m = S >= np.percentile(S, 95); ys, xs = np.nonzero(m)
    return np.array([xs.mean() / w, ys.mean() / h]), "saliency", None

def flow_x(frames):
    if len(frames) < 2: return 0.0
    v = []
    for a, b in zip(frames[:-1], frames[1:]):
        ga, gb = [cv2.resize(cv2.cvtColor(x, cv2.COLOR_RGB2GRAY), (160, 90)) for x in (a, b)]
        fl = cv2.calcOpticalFlowFarneback(ga, gb, None, 0.5, 3, 13, 3, 5, 1.2, 0); mag = np.hypot(fl[..., 0], fl[..., 1])
        m = mag > max(0.5, np.percentile(mag, 70)); v.append(float(fl[..., 0][m].mean()) if m.any() else 0.0)
    return float(np.median(v))

def audio(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    return a if len(a) > 1600 else None

def beat_grid(a, sr=16000):
    hop = 160; rms = np.sqrt(np.convolve(a ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
    on = np.maximum(np.diff(np.log(rms + 1e-6), prepend=0), 0); on = on - on.mean()
    ac = np.correlate(on, on, "full")[len(on) - 1:]; lags = np.arange(len(ac)); ok = (lags >= 33) & (lags <= 86)
    if not ok.any() or ac[0] <= 0: return None
    lag = lags[ok][np.argmax(ac[ok])]; conf = float(ac[lag] / ac[0])
    if conf < 0.25: return None
    period = lag * 0.01; phases = np.arange(lag); score = [on[p::lag].sum() for p in phases]; ph = phases[int(np.argmax(score))] * 0.01
    return {"bpm": round(60 / period, 1), "period": period, "phase": ph, "confidence": round(conf, 2)}

def tc(frame, fps, start=0):
    f = int(round(fps)); x = frame + start; return f"{x // (3600 * f):02d}:{x // (60 * f) % 60:02d}:{x // f % 60:02d}:{x % f:02d}"

def judge(path, out, worst=10, use_beat=True, start_tc="00:00:00:00"):
    os.makedirs(out, exist_ok=True); fps, W, H, has_a = probe(path); w = 384; h = int(H * w / W) // 2 * 2
    fr = read_all(path, w, h); n = len(fr); cuts, _ = detect_cuts(fr); fc = cascade("haarcascade_frontalface_default.xml")
    a = audio(path) if has_a else None; grid = beat_grid(a) if (a is not None and use_beat) else None
    bounds = [0] + cuts + [n]; lengths = np.diff(bounds) / fps; med_len = float(np.median(lengths)) if len(lengths) else 0
    start = sum(int(x) * m for x, m in zip(start_tc.split(":"), [3600 * int(round(fps)), 60 * int(round(fps)), int(round(fps)), 1]))
    res = []
    for k, c in enumerate(cuts):
        A, B = fr[c - 1], fr[c]; issues = []
        pa, ka, fa = attention(A, fc); pb, kb, fb = attention(B, fc); d = float(np.hypot(*(pa - pb)) / np.sqrt(2))
        best = (d, 0, 0)
        for ta in range(0, min(7, c - bounds[k] - 1)):
            qa, _, _ = attention(fr[c - 1 - ta], fc)
            for tb in range(0, min(7, bounds[k + 2] - c - 1)):
                qb, _, _ = attention(fr[c + tb], fc) if tb else (pb, None, None); dd = float(np.hypot(*(qa - qb)) / np.sqrt(2))
                if dd < best[0] - 0.03: best = (dd, ta, tb)
        eye = float(np.clip(1 - (d - 0.12) / 0.33, 0, 1))
        if d > 0.25: issues.append(("eye", f"attention jumps {d:.0%} of the frame ({ka} -> {kb})" + (f"; trimming {best[1]} frames off A and {best[2]} off B brings it to {best[0]:.0%}" if best[0] < d - 0.05 else "; reframe B or accept as an intended jolt")))
        va = flow_x(fr[max(bounds[k], c - 6):c]); vb = flow_x(fr[c:min(bounds[k + 2], c + 6)]); plane = 1.0
        if abs(va) > 0.6 and abs(vb) > 0.6 and np.sign(va) != np.sign(vb):
            plane = 0.2; issues.append(("plane", f"screen direction flips ({'right' if va > 0 else 'left'} -> {'right' if vb > 0 else 'left'}): check the 180-degree line unless the reversal is the point"))
        ga, gb = [cv2.resize(cv2.cvtColor(x, cv2.COLOR_RGB2GRAY), (64, 36)).astype(np.float32) for x in (A, B)]
        sim = float(np.corrcoef(ga.ravel(), gb.ravel())[0, 1]); space = 1.0
        size_ratio = (fb / fa) if (fa and fb) else None
        col_sim = float(cv2.compareHist(hue_hist(A), hue_hist(B), cv2.HISTCMP_CORREL))
        if (sim > 0.75 and col_sim > 0.7) or (size_ratio and 0.75 < size_ratio < 1.33 and np.hypot(*(pa - pb)) < 0.1 and col_sim > 0.5):
            space = 0.2; issues.append(("space", f"jump cut: B is almost the same framing as A (similarity {sim:.2f}{', face size x%.2f' % size_ratio if size_ratio else ''}); change angle 30+ degrees or size, or own it as a style"))
        rh = 1.0; L_in, L_out = lengths[k], lengths[k + 1]
        for L, nm in ((L_in, "outgoing"), (L_out, "incoming")):
            if L < 0.25: rh -= 0.4; issues.append(("rhythm", f"{nm} shot is only {L * fps:.0f} frames (flash frame?)"))
        if med_len and (L_in > 3.5 * med_len): rh -= 0.2; issues.append(("rhythm", f"outgoing shot {L_in:.1f}s is {L_in / med_len:.1f}x the median shot: check it earns its length"))
        off = None
        if grid:
            t = c / fps; ph = (t - grid["phase"]) / grid["period"]; off = (ph - round(ph)) * grid["period"]
            if abs(off) * fps > 2.5: rh -= 0.3; issues.append(("rhythm", f"cut lands {off * fps:+.0f} frames off the beat ({grid['bpm']} BPM)"))
        jump_db = None
        if a is not None:
            s = int(c / fps * 16000); w20 = 320
            if w20 < s < len(a) - w20:
                r1 = np.sqrt((a[s - w20:s] ** 2).mean() + 1e-10); r2 = np.sqrt((a[s:s + w20] ** 2).mean() + 1e-10); jump_db = 20 * np.log10(r2 / r1)
                both_loud = min(r1, r2) > np.sqrt((a ** 2).mean()) * 0.6
                on_beat = off is not None and abs(off) * fps <= 1.5
                if not on_beat and (abs(jump_db) > 8 or (both_loud and abs(jump_db) > 5)): rh -= 0.3; issues.append(("rhythm", f"audio jumps {jump_db:+.0f} dB exactly at the cut (cut inside a word or a level jump): add a 2-4 frame audio crossfade or move to a pause"))
        rh = float(np.clip(rh, 0, 1)); tech = round(100 * (10 * rh + 7 * eye + 5 * plane + 4 * space) / 26, 1)
        res.append({"cut": k + 1, "frame": c, "timecode": tc(c, fps, start), "time": round(c / fps, 3), "technical_score": tech,
                    "rhythm": round(rh, 2), "eye_trace": round(eye, 2), "plane": plane, "space": space, "attention_distance": round(d, 3),
                    "suggested_trim_A_B": [best[1], best[2]] if best[0] < d - 0.05 else None, "beat_offset_frames": None if off is None else round(off * fps, 1),
                    "audio_jump_db": None if jump_db is None else round(float(jump_db), 1), "issues": [{"criterion": c_, "text": t_} for c_, t_ in issues],
                    "pa": pa.tolist(), "pb": pb.tolist(), "va": va, "vb": vb})
    weak = sorted(res, key=lambda r: r["technical_score"])[:worst]
    for r in weak:
        A, B = Image.fromarray(fr[r["frame"] - 1]), Image.fromarray(fr[r["frame"]]); im = Image.new("RGB", (2 * w + 30, h + 50), (14, 14, 14)); im.paste(A, (10, 10)); im.paste(B, (w + 20, 10)); dr = ImageDraw.Draw(im)
        for (p, ox, col) in ((r["pa"], 10, (255, 200, 0)), (r["pb"], w + 20, (0, 220, 255))):
            x, y = ox + p[0] * w, 10 + p[1] * h; dr.ellipse([x - 7, y - 7, x + 7, y + 7], outline=col, width=3)
        x, y = w + 20 + r["pa"][0] * w, 10 + r["pa"][1] * h; dr.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(255, 200, 0), width=2)
        for v, ox in ((r["va"], 10), (r["vb"], w + 20)):
            if abs(v) > 0.6: cx = ox + w / 2; dr.line([(cx, h - 10), (cx + np.sign(v) * 40, h - 10)], fill=(255, 80, 80), width=4)
        dr.text((12, h + 16), f"cut {r['cut']} {r['timecode']} technical {r['technical_score']}  | yellow = eye on A (also shown on B), cyan = eye on B, red = motion", fill=(230, 230, 230))
        im.save(os.path.join(out, f"cut_{r['cut']:03d}.jpg"), quality=88)
    L = ["TITLE: weakest cuts", "FCM: NON-DROP FRAME", ""]
    for i, r in enumerate(weak, 1):
        a_, b_ = tc(r["frame"], fps, start), tc(r["frame"] + 1, fps, start)
        L += [f"{i:03d}  001      V     C        {a_} {b_} {a_} {b_}  ", f" |C:ResolveColorRed |M:cut {r['cut']} tech {r['technical_score']}: {r['issues'][0]['text'][:80] if r['issues'] else 'ok'} |D:1", ""]
    open(os.path.join(out, "markers.edl"), "w").write("\n".join(L))
    for r in res: [r.pop(k) for k in ("pa", "pb", "va", "vb")]
    summary = {"file": path, "fps": round(fps, 3), "cuts": len(res), "shots": len(lengths), "median_shot_s": round(med_len, 2), "beat": grid,
               "mean_technical": round(float(np.mean([r["technical_score"] for r in res])), 1) if res else None}
    json.dump({"summary": summary, "cuts": res}, open(os.path.join(out, "cuts.json"), "w"), indent=1)
    md = [f"# Rule of Six check: {os.path.basename(path)}", f"{len(res)} cuts, {len(lengths)} shots, median shot {med_len:.2f}s, " + (f"music beat {grid['bpm']} BPM (confidence {grid['confidence']})" if grid else "no steady beat detected (rhythm judged without a grid)"),
          f"Mean technical score {summary['mean_technical']}/100 (rhythm, eye trace, 2D plane, 3D space).", "",
          "Emotion (51%) and story (23%) are NOT measured. Look at each sheet below and judge: is the cut true to the emotion of the moment, does it move the story? A cut that wins there may break every rule underneath.", "",
          f"## Weakest {len(weak)} cuts"]
    for r in weak:
        md += [f"### cut {r['cut']} at {r['timecode']}: technical {r['technical_score']}  (cut_{r['cut']:03d}.jpg)", f"rhythm {r['rhythm']}, eye trace {r['eye_trace']}, plane {r['plane']}, space {r['space']}"]
        md += [f"- [{i['criterion']}] {i['text']}" for i in r["issues"]] or ["- no measurable problem"]
    md += ["", "## All cuts", "| # | timecode | technical | issues |", "|---|---|---|---|"] + [f"| {r['cut']} | {r['timecode']} | {r['technical_score']} | {len(r['issues'])} |" for r in res]
    open(os.path.join(out, "report.md"), "w").write("\n".join(md)); print("\n".join(md[:40]))

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "judge": judge(a[2], a[3], int(opt("--worst", 10)), opt("--beat", "on") == "on", opt("--tc-start", "00:00:00:00"))
    else: print(USAGE)
