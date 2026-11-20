###############
# Qiyas Sadıqov CC
###############
import csv, json, os, subprocess, sys, urllib.request
import numpy as np
import cv2
from PIL import Image, ImageDraw

USAGE = """cut-point-finder: frame-exact cut point suggestions the way master editors find them.

  python3 cutpoint.py find CLIP [CLIP ...] OUT_DIR [--top 3] [--tc-start 00:00:00:00] [--no-faces] [--sheet on|off]
      -> OUT_DIR/<clip>_cuts.json, cuts.csv, report.md, <clip>_markers.edl (DaVinci Resolve marker EDL),
         <clip>_sheet.jpg (each suggested frame with the frames around it)

Evidence it collects per frame (all measured, nothing guessed):
  blink      the darkest pixels in both eye regions of the detected face lighten together for 2-8 frames (lid closed) (Murch: a blink is the mind's own cut;
             suggest cutting 1-2 frames BEFORE the blink while the actor is in character)
  line_end   speech energy falls into a pause of at least 0.25 s (a thought has finished)
  exit       a moving subject's leading edge reaches the frame border (cut when the exit is inevitable, not after)
  action     a local peak of motion (Dmytryk: whenever possible, cut in movement; the motion hides the cut)
Events closer than 6 frames are merged and scored; the report ranks the best out-points per clip with reasons.
Faces use OpenCV Haar cascades (found in cv2.data or downloaded once from the OpenCV GitHub repo into ./models).
Needs: numpy, opencv-python-headless, Pillow, ffmpeg/ffprobe.
"""

HAAR_URL = "https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/"

def cascade(name):
    for d in [getattr(getattr(cv2, "data", None), "haarcascades", "") or "", os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"), "models"]:
        p = os.path.join(d, name)
        if d and os.path.exists(p): return cv2.CascadeClassifier(p)
    os.makedirs("models", exist_ok=True); p = os.path.join("models", name)
    try: urllib.request.urlretrieve(HAAR_URL + name, p); return cv2.CascadeClassifier(p)
    except Exception as e: sys.stderr.write(f"face model unavailable ({e}); blink detection skipped\n"); return None

def probe(path):
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path], capture_output=True, text=True).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video"); n, d = map(int, v["r_frame_rate"].split("/"))
    has_a = any(s["codec_type"] == "audio" for s in pr["streams"])
    return n / d, int(v["width"]), int(v["height"]), float(pr["format"]["duration"]), has_a

def frames(path, w, h):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(w * h)
        if len(b) < w * h: break
        yield np.frombuffer(b, np.uint8).reshape(h, w)
    p.wait()

def audio_env(path, fps, n):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if len(a) == 0: return None
    hop = 160; rms = np.sqrt(np.convolve(a ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
    t = np.arange(len(rms)) * 0.01; idx = np.clip((np.arange(n) / fps / 0.01).astype(int), 0, len(rms) - 1)
    return rms, t, idx

def tc(frame, fps, start=0):
    f = int(round(fps)); x = frame + start; return f"{x // (3600 * f):02d}:{x // (60 * f) % 60:02d}:{x // f % 60:02d}:{x % f:02d}"

def tc_to_frames(s, fps):
    h, m, sec, f = map(int, s.split(":")); return ((h * 60 + m) * 60 + sec) * int(round(fps)) + f

def analyze(path, use_faces=True):
    fps, W, H, dur, has_a = probe(path); aw = 480; ah = int(H * aw / W) // 2 * 2
    fc = cascade("haarcascade_frontalface_default.xml") if use_faces else None
    eye_e, face_ok, mot, lead_r, lead_l, cx = [], [], [], [], [], []
    prev, box = None, None
    for i, g in enumerate(frames(path, aw, ah)):
        if fc is not None:
            fs = fc.detectMultiScale(g, 1.1, 5, minSize=(ah // 8, ah // 8))
            box = max(fs, key=lambda b: b[2] * b[3]) if len(fs) else None
        if box is not None:
            x, y, w, h = box
            eyes = [g[y + int(h * 0.27): y + int(h * 0.47), x + int(w * (cx - 0.13)): x + int(w * (cx + 0.13))].astype(np.float32) for cx in (0.30, 0.70)]
            ref = np.median(g[y + int(h * 0.2): y + int(h * 0.8), x + int(w * 0.2): x + int(w * 0.8)]) + 1e-3
            eye_e.append([float(np.percentile(r, 5) / ref) for r in eyes] if min(r.size for r in eyes) > 50 else [np.nan, np.nan]); face_ok.append(True)
        else: eye_e.append([np.nan, np.nan]); face_ok.append(False)
        s = cv2.resize(g, (240, int(240 * ah / aw)))
        if prev is not None:
            fl = cv2.calcOpticalFlowFarneback(prev, s, None, 0.5, 3, 15, 3, 5, 1.2, 0); mag = np.hypot(fl[..., 0], fl[..., 1])
            glob = np.median(mag); m = mag > max(1.0, glob * 2.5); mot.append(float(mag.mean()))
            cols = np.where(m.any(0))[0]
            lead_r.append(cols.max() / s.shape[1] if len(cols) > 3 else np.nan); lead_l.append(cols.min() / s.shape[1] if len(cols) > 3 else np.nan)
            cx.append(float((np.arange(s.shape[1])[None, :] * m).sum() / max(m.sum(), 1)) / s.shape[1] if m.sum() > 20 else np.nan)
        else: mot.append(0.0); lead_r.append(np.nan); lead_l.append(np.nan); cx.append(np.nan)
        prev = s
    n = len(mot); ev = []
    e = np.array(eye_e).reshape(-1, 2)
    if np.isfinite(e[:, 0]).sum() > 10:
        med = np.array([np.nanmedian(e[max(0, i - 12): i + 13], 0) for i in range(n)])
        low = np.isfinite(e).all(1) & (e > med * 1.22).all(1); i = 0
        while i < n:
            if low[i]:
                j = i
                while j + 1 < n and low[j + 1]: j += 1
                if 2 <= j - i + 1 <= 8 and i > 0: ev.append({"frame": max(0, i - 2), "type": "blink", "detail": f"blink frames {i}-{j}, cut 2 frames before", "w": 0.8})
                i = j + 1
            else: i += 1
    if has_a:
        env = audio_env(path, fps, n)
        if env:
            rms, t, idx = env; floor = np.percentile(rms, 10); thr = max(floor * 4, np.percentile(rms, 90) * 0.12)
            sp = rms > thr; k = 0
            sp = np.convolve(sp.astype(float), np.ones(12) / 12, "same") > 0.3
            while k < len(sp) - 1:
                if sp[k] and not sp[k + 1]:
                    j = k + 1
                    while j < len(sp) and not sp[j]: j += 1
                    if (j - k) * 0.01 >= 0.25:
                        f = int(round((k + 1) * 0.01 * fps)) + 2
                        if f < n: ev.append({"frame": f, "type": "line_end", "detail": f"speech pause {(j - k) * 0.01:.2f}s starts at {(k + 1) * 0.01:.2f}s", "w": 0.6})
                    k = j
                else: k += 1
    lr, ll, c = np.array(lead_r), np.array(lead_l), np.array(cx); done = set()
    for i in range(6, n):
        if not np.isfinite(c[i - 5:i + 1]).all(): continue
        v = c[i] - c[i - 5]
        for side, lead, cond in (("right", lr, v > 0.02), ("left", ll, v < -0.02)):
            if side in done or not cond or not np.isfinite(lead[i]): continue
            if (side == "right" and lead[i] >= 0.995) or (side == "left" and lead[i] <= 0.005):
                ev.append({"frame": i, "type": "exit", "detail": f"subject reaches {side} edge: exit inevitable", "w": 0.8}); done.add(side)
    m = np.convolve(np.array(mot), np.ones(5) / 5, "same"); base = np.median(m) + 1e-6
    for i in range(3, n - 3):
        if m[i] == m[i - 3:i + 4].max() and m[i] > base * 1.6 and m[i] > 0.3:
            ev.append({"frame": i, "type": "action", "detail": f"motion peak {m[i] / base:.1f}x median: cut in movement", "w": 0.5})
    ev.sort(key=lambda x: x["frame"]); groups = []
    for x in ev:
        if groups and x["frame"] - groups[-1][-1]["frame"] <= 6: groups[-1].append(x)
        else: groups.append([x])
    cands = []
    for g in groups:
        main = max(g, key=lambda x: x["w"]); types = sorted({x["type"] for x in g})
        score = min(1.0, main["w"] + 0.15 * (len(types) - 1))
        cands.append({"frame": int(main["frame"]), "time": round(main["frame"] / fps, 3), "timecode": tc(int(main["frame"]), fps), "score": round(score, 2),
                      "types": types, "reasons": list(dict.fromkeys(x["detail"] for x in g))})
    return {"clip": path, "fps": round(fps, 3), "frames": n, "duration": round(dur, 2), "faces_found": int(sum(face_ok)), "candidates": cands}

def sheet(path, res, out, top):
    best = sorted(res["candidates"], key=lambda c: -c["score"])[:top]
    if not best: return
    fps = res["fps"]; tw = 240; rows = []
    for c in sorted(best, key=lambda c: c["frame"]):
        tiles = []
        for off in (-2, 0, 2):
            f = max(0, c["frame"] + off)
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{f / fps:.3f}", "-i", path, "-frames:v", "1", "-vf", f"scale={tw}:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
            if raw: tiles.append(Image.open(__import__("io").BytesIO(raw)).convert("RGB"))
        if tiles: rows.append((c, tiles))
    th = rows[0][1][0].height; im = Image.new("RGB", (3 * tw + 40, len(rows) * (th + 26) + 10), (16, 16, 16)); d = ImageDraw.Draw(im)
    for r, (c, tiles) in enumerate(rows):
        for k, t in enumerate(tiles): im.paste(t, (10 + k * (tw + 10), 10 + r * (th + 26)))
        d.text((12, 12 + r * (th + 26) + th), f"{c['timecode']} f{c['frame']} score {c['score']} {'+'.join(c['types'])}   (-2 | cut | +2)", fill=(235, 235, 235))
    im.save(out, quality=88)

def edl(res, out, start):
    fps = res["fps"]; name = os.path.splitext(os.path.basename(res["clip"]))[0]; col = {"blink": "ResolveColorBlue", "line_end": "ResolveColorGreen", "exit": "ResolveColorRed", "action": "ResolveColorYellow"}
    L = [f"TITLE: {name} cut points", "FCM: NON-DROP FRAME", ""]
    for k, c in enumerate(res["candidates"], 1):
        a, b = tc(c["frame"], fps, start), tc(c["frame"] + 1, fps, start)
        L += [f"{k:03d}  001      V     C        {a} {b} {a} {b}  ", f" |C:{col.get(c['types'][0], 'ResolveColorBlue')} |M:{'+'.join(c['types'])} {c['score']} |D:1", ""]
    open(out, "w").write("\n".join(L))

def find(clips, out, top=3, start_tc="00:00:00:00", faces=True, make_sheet=True):
    os.makedirs(out, exist_ok=True); rows, md = [], ["# Cut point suggestions", ""]
    for c in clips:
        res = analyze(c, faces); name = os.path.splitext(os.path.basename(c))[0]
        for x in res["candidates"]: x["timecode"] = tc(x["frame"], res["fps"], tc_to_frames(start_tc, res["fps"]))
        json.dump(res, open(os.path.join(out, f"{name}_cuts.json"), "w"), indent=1)
        edl(res, os.path.join(out, f"{name}_markers.edl"), tc_to_frames(start_tc, res["fps"]))
        if make_sheet: sheet(c, res, os.path.join(out, f"{name}_sheet.jpg"), top)
        best = sorted(res["candidates"], key=lambda x: -x["score"])[:top]
        md += [f"## {os.path.basename(c)}  ({res['duration']} s, {res['fps']} fps, face in {res['faces_found']}/{res['frames']} frames)"]
        md += [f"{i}. **{x['timecode']}** (frame {x['frame']}, {x['time']} s) score {x['score']}: {'; '.join(x['reasons'])}" for i, x in enumerate(best, 1)] or ["- no strong cut evidence; cut on story/emotion judgement"]
        md.append(f"All {len(res['candidates'])} candidates: {name}_cuts.json, markers: {name}_markers.edl, frames: {name}_sheet.jpg"); md.append("")
        for x in res["candidates"]: rows.append([os.path.basename(c), x["frame"], x["time"], x["timecode"], x["score"], "+".join(x["types"]), " | ".join(x["reasons"])])
    with open(os.path.join(out, "cuts.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["clip", "frame", "seconds", "timecode", "score", "types", "reasons"]); w.writerows(rows)
    md += ["Markers: DaVinci Resolve > timeline/clip > right-click > Timelines > Import > Timeline Markers from EDL. cuts.csv works anywhere."]
    open(os.path.join(out, "report.md"), "w").write("\n".join(md)); print("\n".join(md))

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "find":
        flags = {"--top", "--tc-start", "--sheet"}; pos = [x for i, x in enumerate(a[2:], 2) if x not in flags and a[i - 1] not in flags and x != "--no-faces"]
        find(pos[:-1], pos[-1], int(opt("--top", 3)), opt("--tc-start", "00:00:00:00"), "--no-faces" not in a, opt("--sheet", "on") == "on")
    else: print(USAGE)
