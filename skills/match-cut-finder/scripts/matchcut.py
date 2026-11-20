###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw

USAGE = """match-cut-finder: find frames across clips that share shape, colour, position or motion,
and render seamless match-cut transitions between them.

  python3 matchcut.py find CLIPS_DIR OUT_DIR [--top 12] [--step 0.2] [--mode any|tailhead]
      -> OUT_DIR/matches.json + matches.md + sheet.jpg (pairs side by side)
  python3 matchcut.py render A.mp4 tA B.mp4 tB OUT.mp4 [--pre 1.2] [--post 1.5] [--style cut|whip|morph] [--w 1080 --h 1920]
      -> A plays up to tA, B continues from tB, aligned on the matched subject (centroid shift),
         optional whip (directional blur, 4 frames) or morph (6-frame aligned blend).
Scores: shape (Hu moments of the dominant silhouette), colour (HSV histogram), position
(subject centroid), motion (mean optical-flow direction), brightness. Weighted sum, 0..1.
Needs: ffmpeg, numpy, Pillow, opencv-python-headless.
"""

def run(c): return subprocess.run(c, capture_output=True, text=True)

def duration(p):
    return float(json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", p]).stdout)["format"]["duration"])

def frames(p, step):
    cap = cv2.VideoCapture(p); fps = cap.get(cv2.CAP_PROP_FPS) or 30; n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out, prev = [], None; every = max(1, int(round(step * fps)))
    for i in range(0, n, every):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, f = cap.read()
        if not ok: break
        small = cv2.resize(f, (144, int(144 * f.shape[0] / f.shape[1])))
        g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(prev, g, None, .5, 2, 9, 2, 5, 1.1, 0).reshape(-1, 2).mean(0) if prev is not None else np.zeros(2)
        prev = g; out.append((i / fps, small, g, flow))
    cap.release(); return out

def describe(small, g, flow):
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [18, 8], [0, 180, 0, 256]).flatten(); hist /= hist.sum() + 1e-9
    bl = cv2.GaussianBlur(g, (5, 5), 0); _, th = cv2.threshold(bl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if th.mean() > 127: th = 255 - th
    cs, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    H, W = g.shape
    inner = [c for c in cs if (lambda x, y, w, h: x > 1 and y > 1 and x + w < W - 1 and y + h < H - 1)(*cv2.boundingRect(c)) and cv2.contourArea(c) > 0.004 * W * H]
    cs = inner or cs
    if cs:
        c = max(cs, key=cv2.contourArea); m = cv2.moments(c); area = cv2.contourArea(c) / (W * H)
        hu = cv2.HuMoments(m).flatten(); hu = -np.sign(hu) * np.log10(np.abs(hu) + 1e-12)
        cx, cy = (m["m10"] / (m["m00"] + 1e-9)) / W, (m["m01"] / (m["m00"] + 1e-9)) / H
    else:
        hu, cx, cy, area = np.zeros(7), .5, .5, 0
    return {"hist": hist, "hu": hu, "c": np.array([cx, cy]), "area": area, "flow": flow, "bright": g.mean() / 255}

def score(a, b):
    colour = 1 - 0.5 * np.abs(a["hist"] - b["hist"]).sum()
    shape = float(np.exp(-np.abs(a["hu"][:4] - b["hu"][:4]).sum() / 4)) * (1 if min(a["area"], b["area"]) > 0.01 else 0.3)
    pos = float(np.exp(-np.linalg.norm(a["c"] - b["c"]) * 4))
    size = float(np.exp(-abs(a["area"] - b["area"]) * 8))
    fa, fb = a["flow"], b["flow"]; na, nb = np.linalg.norm(fa), np.linalg.norm(fb)
    motion = 0.5 if na < .2 and nb < .2 else float((np.dot(fa, fb) / (na * nb + 1e-9) + 1) / 2) if na > .2 and nb > .2 else 0.3
    bright = 1 - abs(a["bright"] - b["bright"])
    parts = {"shape": shape, "colour": colour, "position": pos, "size": size, "motion": motion, "brightness": bright}
    total = .28 * shape + .2 * colour + .2 * pos + .12 * size + .12 * motion + .08 * bright
    return total, parts

def find(d, out, top=12, step=0.2, mode="any"):
    os.makedirs(out, exist_ok=True)
    clips = sorted(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm", ".m4v")))
    data = {}
    for c in clips:
        fr = frames(c, step); dur = fr[-1][0] if fr else 0
        data[c] = [(t, s, describe(s, g, fl)) for t, s, g, fl in fr]
        if mode == "tailhead": data[c] = [(t, s, dsc, dur) for t, s, dsc in data[c]]
    res = []
    for i, a in enumerate(clips):
        for b in clips:
            if a == b: continue
            A = data[a]; B = data[b]
            if mode == "tailhead":
                A = [x for x in A if x[0] >= x[3] - 1.5]; B = [x for x in B if x[0] <= 1.5]
            for ta, sa, da, *_ in A:
                for tb, sb, db, *_ in B:
                    s, parts = score(da, db); res.append((s, a, ta, b, tb, parts, sa, sb))
    res.sort(key=lambda r: -r[0]); picked = []
    for r in res:
        if all(not (r[1] == p[1] and r[3] == p[3] and abs(r[2] - p[2]) < 0.6 and abs(r[4] - p[4]) < 0.6) for p in picked): picked.append(r)
        if len(picked) >= top: break
    rows = []; sheet = Image.new("RGB", (2 * 200 + 30, len(picked) * 380 + 10), (18, 18, 18)); dr = ImageDraw.Draw(sheet)
    for k, (s, a, ta, b, tb, parts, sa, sb) in enumerate(picked):
        why = max(parts, key=parts.get)
        rows.append({"rank": k + 1, "score": round(float(s), 3), "a": a, "t_a": round(ta, 2), "b": b, "t_b": round(tb, 2), "strongest": why, "parts": {x: round(float(y), 2) for x, y in parts.items()}})
        for j, sm in enumerate((sa, sb)):
            im = Image.fromarray(cv2.cvtColor(sm, cv2.COLOR_BGR2RGB)).resize((200, 355)); sheet.paste(im, (10 + j * 210, 10 + k * 380))
        dr.text((12, 10 + k * 380 + 357), f"#{k+1} {s:.2f} {why}  {os.path.basename(a)}@{ta:.1f} > {os.path.basename(b)}@{tb:.1f}", fill=(230, 230, 230))
    sheet.save(os.path.join(out, "sheet.jpg")); json.dump(rows, open(os.path.join(out, "matches.json"), "w"), indent=1)
    md = ["| # | score | from | to | strongest |", "|---|---|---|---|---|"] + [f"| {r['rank']} | {r['score']} | {os.path.basename(r['a'])} @ {r['t_a']} s | {os.path.basename(r['b'])} @ {r['t_b']} s | {r['strongest']} |" for r in rows]
    open(os.path.join(out, "matches.md"), "w").write("\n".join(md)); print("\n".join(md)); print("sheet:", os.path.join(out, "sheet.jpg"))

def centroid(p, t):
    cap = cv2.VideoCapture(p); cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = cap.read(); cap.release()
    g = cv2.cvtColor(cv2.resize(f, (144, int(144 * f.shape[0] / f.shape[1]))), cv2.COLOR_BGR2GRAY)
    return describe(cv2.cvtColor(g, cv2.COLOR_GRAY2BGR), g, np.zeros(2))["c"]

def render(a, ta, b, tb, out, pre=1.2, post=1.5, style="cut", W=1080, H=1920):
    ca, cb = centroid(a, ta), centroid(b, tb); dx, dy = (ca - cb) * [W, H]
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30"
    s = max(0, ta - pre)
    fa = f"[0:v]trim={s}:{ta},setpts=PTS-STARTPTS,{fit}[a]"
    pad = int(max(abs(dx), abs(dy))) + 4
    fb = (f"[1:v]trim={tb}:{tb + post},setpts=PTS-STARTPTS,{fit},pad={W + 2 * pad}:{H + 2 * pad}:{pad}:{pad},"
          f"crop={W}:{H}:{pad - dx:.0f}+(({pad}-({pad - dx:.0f}))*min(t/0.5\\,1)):{pad - dy:.0f}+(({pad}-({pad - dy:.0f}))*min(t/0.5\\,1))[b]")
    if style == "morph":
        fc = f"{fa};{fb};[a][b]xfade=transition=fade:duration=0.2:offset={ta - s - 0.2:.3f}[v]"
    elif style == "whip":
        fc = (f"{fa};{fb};[a][b]xfade=transition=slideleft:duration=0.133:offset={ta - s - 0.133:.3f},"
              f"tmix=frames=3[v]")
    else:
        fc = f"{fa};{fb};[a][b]concat=n=2:v=1[v]"
    r = run(["ffmpeg", "-loglevel", "error", "-y", "-i", a, "-i", b, "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out])
    if r.returncode: print(r.stderr); sys.exit(1)
    print(f"-> {out}  (B shifted {dx:+.0f},{dy:+.0f} px at the cut, easing back to centre over 0.5 s)")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "find": find(a[2], a[3], int(opt("--top", 12)), float(opt("--step", .2)), opt("--mode", "any"))
    elif len(a) > 6 and a[1] == "render": render(a[2], float(a[3]), a[4], float(a[5]), a[6], float(opt("--pre", 1.2)), float(opt("--post", 1.5)), opt("--style", "cut"), int(opt("--w", 1080)), int(opt("--h", 1920)))
    else: print(USAGE)
