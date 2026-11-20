###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

USAGE = """sticky-motion: pin labels and graphics to objects in real footage (motion tracking + render).

  python3 sticky.py frame VIDEO.mp4 T OUT.png [--grid]        -> still with a coordinate grid, to pick the object box
  python3 sticky.py track VIDEO.mp4 OUT.json --box x,y,w,h [--t 0] [--end 999] [--smooth 0.12]
      -> per-frame centre, box and confidence; tracks forward from T with CSRT, re-anchors with template
         matching when CSRT fails, Gaussian-smooths the path, marks frames where the object is lost.
  python3 sticky.py render VIDEO.mp4 OUT.mp4 --tracks a.json[,b.json] --label "Sea view" [--sub "120 m2"] [--style pill|callout|ring]
        [--color "#F0662B"] [--font /path/font.ttf] [--side auto|left|right] [--in 0.3] [--out 0]
      -> the label rides the tracked point: pops in (115% then settle, no fade), leader line to the object,
         stays inside 75 px margins, hides by scaling down when tracking is lost.
Multiple labels: run track once per object, pass --tracks a.json,b.json with --label "A|B" (and --sub "x|y").
Needs: ffmpeg, numpy, Pillow, opencv-python-headless (CSRT tracker).
"""

def ease_pop(f, up=3, settle=7, peak=1.15):
    if f <= 0: return 0.0
    if f < up: return peak * (1 - 2 ** (-10 * f / up))
    k = min(1, (f - up) / settle); return peak + (1 - peak) * (0.5 - 0.5 * np.cos(np.pi * k))

def grab(p, t):
    cap = cv2.VideoCapture(p); cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = cap.read(); cap.release(); return f

def cmd_frame(p, t, out, grid=False):
    f = grab(p, t)
    if grid:
        H, W = f.shape[:2]
        for x in range(0, W, 100): cv2.line(f, (x, 0), (x, H), (0, 255, 255), 1); cv2.putText(f, str(x), (x + 2, 18), 0, .5, (0, 255, 255), 1)
        for y in range(0, H, 100): cv2.line(f, (0, y), (W, y), (0, 255, 255), 1); cv2.putText(f, str(y), (2, y - 3), 0, .5, (0, 255, 255), 1)
    cv2.imwrite(out, f); print(out, f.shape[1], "x", f.shape[0])

def make_tracker():
    for mk in (lambda: cv2.TrackerCSRT_create(), lambda: cv2.legacy.TrackerCSRT_create(), lambda: cv2.TrackerKCF_create()):
        try: return mk()
        except Exception: pass
    raise SystemExit("No OpenCV tracker available: pip install opencv-contrib-python-headless")

def cmd_track(p, out, box, t0=0.0, t1=1e9, smooth=0.12):
    cap = cv2.VideoCapture(p); fps = cap.get(cv2.CAP_PROP_FPS) or 30; n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    f0 = int(round(t0 * fps)); cap.set(cv2.CAP_PROP_POS_FRAMES, f0); ok, fr = cap.read()
    x, y, w, h = box; tr = make_tracker(); tr.init(fr, (x, y, w, h))
    tmpl = fr[y:y + h, x:x + w].copy(); rows = []; lost_run = 0
    for i in range(f0, min(n, int(t1 * fps) + 1)):
        if i > f0:
            ok, fr = cap.read()
            if not ok: break
        good, b = tr.update(fr) if i > f0 else (True, (x, y, w, h))
        conf = 1.0 if good else 0.0
        if not good:
            lx, ly, lw, lh = rows[-1]["box"] if rows else (x, y, w, h)
            pad = int(max(lw, lh) * 1.5); X0, Y0 = max(0, int(lx) - pad), max(0, int(ly) - pad)
            roi = fr[Y0:Y0 + int(lh) + 2 * pad, X0:X0 + int(lw) + 2 * pad]
            if roi.shape[0] > tmpl.shape[0] and roi.shape[1] > tmpl.shape[1]:
                res = cv2.matchTemplate(roi, tmpl, cv2.TM_CCOEFF_NORMED); _, mv, _, ml = cv2.minMaxLoc(res)
                if mv > 0.6:
                    b = (X0 + ml[0], Y0 + ml[1], tmpl.shape[1], tmpl.shape[0]); conf = float(mv)
                    tr = make_tracker(); tr.init(fr, tuple(int(v) for v in b))
        lost_run = 0 if conf > 0 else lost_run + 1
        bx = [float(v) for v in b] if conf > 0 else (rows[-1]["box"] if rows else [x, y, w, h])
        rows.append({"frame": i, "t": round(i / fps, 4), "box": bx, "cx": bx[0] + bx[2] / 2, "cy": bx[1] + bx[3] / 2, "conf": round(conf, 3)})
    cap.release()
    s = max(1e-3, smooth * fps); r = int(3 * s); k = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * s * s))
    cx = np.array([q["cx"] for q in rows]); cy = np.array([q["cy"] for q in rows]); wgt = np.array([1.0 if q["conf"] > 0 else 0.05 for q in rows])
    def sm(v):
        num = np.convolve(np.pad(v * wgt, r, mode="edge"), k, "valid"); den = np.convolve(np.pad(wgt, r, mode="edge"), k, "valid"); return num / den
    for q, a, b in zip(rows, sm(cx), sm(cy)): q["sx"], q["sy"] = round(float(a), 2), round(float(b), 2)
    lost = sum(1 for q in rows if q["conf"] == 0)
    json.dump({"video": p, "fps": fps, "rows": rows}, open(out, "w"))
    print(f"tracked {len(rows)} frames from {t0}s, lost {lost} ({lost / max(1, len(rows)):.0%}) -> {out}")

def hex2rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def load_font(path, size):
    for p in [path, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        if p and os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def draw_label(img, x, y, scale, label, sub, style, col, font, sfont, side, W, H):
    if scale <= 0.01: return img
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    tw = d.textlength(label, font=font); sw = d.textlength(sub, font=sfont) if sub else 0
    pw, ph = int(max(tw, sw) + 56), int(font.size * 1.5 + (sfont.size * 1.3 if sub else 0) + 20)
    gap = 90; side = side if side != "auto" else ("left" if x > W * 0.55 else "right")
    lx = x - gap - pw if side == "left" else x + gap; ly = y - ph - 70
    if ly < 75: ly = y + 70
    lx = min(max(75, lx), W - 75 - pw); ly = min(max(75, ly), H - 75 - ph)
    ax, ay = (lx + pw if side == "left" else lx), ly + ph / 2
    if style == "ring" or style == "callout":
        rr = 26 * scale; d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col + (255,), width=5)
    d.line([(x, y), (ax, ay)], fill=col + (255,), width=4); d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(255, 255, 255, 255))
    card = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2 if style == "pill" and not sub else 22, fill=(18, 18, 20, 235))
    cd.rounded_rectangle([0, 0, 12, ph - 1], radius=6, fill=col + (255,))
    cd.text((32, 12), label, font=font, fill=(255, 255, 255, 255))
    if sub: cd.text((32, 12 + font.size * 1.3), sub, font=sfont, fill=(200, 200, 205, 255))
    if scale != 1:
        cw, ch = max(1, int(pw * scale)), max(1, int(ph * scale)); card = card.resize((cw, ch), Image.LANCZOS)
        lx += (pw - cw) / 2; ly += (ph - ch) / 2
    ov.alpha_composite(card, (int(lx), int(ly)))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

def cmd_render(p, tracks, out, labels, subs, style="callout", color="#F0662B", font=None, side="auto", t_in=0.3, t_out=0.0):
    T = [json.load(open(x)) for x in tracks]; idx = [{r["frame"]: r for r in t["rows"]} for t in T]
    cap = cv2.VideoCapture(p); fps = cap.get(cv2.CAP_PROP_FPS) or 30; W = int(cap.get(3)); H = int(cap.get(4)); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fsz = max(28, W // 22); F, SF = load_font(font, fsz), load_font(font, int(fsz * 0.7)); col = hex2rgb(color)
    tmp = out + ".silent.mp4"
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    vis = [0] * len(T); lost = [0] * len(T)
    for i in range(n):
        ok, fr = cap.read()
        if not ok: break
        img = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)); t = i / fps
        for k, ix in enumerate(idx):
            r = ix.get(i)
            if not r or t < t_in or (t_out and t > t_out): vis[k] = 0; continue
            lost[k] = lost[k] + 1 if r["conf"] == 0 else 0
            if lost[k] > 4: vis[k] = max(0, vis[k] - 2); s = ease_pop(vis[k]) * (vis[k] / 10)
            else: vis[k] += 1; s = ease_pop(vis[k])
            img = draw_label(img, r["sx"], r["sy"], s, labels[k], subs[k] if k < len(subs) else "", style, col, F, SF, side, W, H)
        ff.stdin.write(np.asarray(img).tobytes())
    cap.release(); ff.stdin.close(); ff.wait()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-i", p, "-map", "0:v", "-map", "1:a?", "-c", "copy", "-shortest", out]); os.remove(tmp)
    print("->", out)

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 4 and a[1] == "frame": cmd_frame(a[2], float(a[3]), a[4], "--grid" in a)
    elif len(a) > 3 and a[1] == "track": cmd_track(a[2], a[3], [int(v) for v in opt("--box").split(",")], float(opt("--t", 0)), float(opt("--end", 1e9)), float(opt("--smooth", .12)))
    elif len(a) > 3 and a[1] == "render":
        cmd_render(a[2], opt("--tracks").split(","), a[3], (opt("--label") or "Label").split("|"), (opt("--sub") or "").split("|") if opt("--sub") else [],
                   opt("--style", "callout"), opt("--color", "#F0662B"), opt("--font"), opt("--side", "auto"), float(opt("--in", .3)), float(opt("--out", 0)))
    else: print(USAGE)
