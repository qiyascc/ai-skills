###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont

USAGE = """listing-to-reel: turn a property listing (photos + facts) into a beat-locked cinematic vertical Reel.

  python3 listing2reel.py example > spec.json          -> a spec to fill
  python3 listing2reel.py stills spec.json OUT_DIR      -> key frames for approval (hook, a fact frame, end card)
  python3 listing2reel.py render spec.json OUT.mp4 [--draft]   (--draft = half size, no motion blur)

What it does with every photo: a 2.5D camera move (push-in, pan, pull-out, orbit tilt via perspective warp)
on a sharp foreground over a blurred, scaled background so vertical frames never show bars; whip
transitions with directional blur on the beat; price as an odometer; facts as staggered pop-in chips;
location card with a pin; end card with brand, agent and phone; 3-sub-frame motion blur.
Each photo lives `beats_per_photo` beats (default 3 at 120 BPM = 1.5 s, the short-form sweet spot).
Needs: numpy, Pillow, opencv-python-headless, ffmpeg.
"""

EXAMPLE = {
    "size": [1080, 1920], "fps": 30, "bpm": 120, "beats_per_photo": 3,
    "photos": ["photo1.jpg", "photo2.jpg", "photo3.jpg"],
    "hook": "Dənizə 5 dəqiqə", "title": "3 otaqlı mənzil", "price": {"value": 185000, "currency": "AZN"},
    "facts": ["3 otaq", "120 m²", "9/16 mərtəbə", "Təmirli"], "location": "Yasamal, Bakı",
    "brand": "Khalif Estate", "agent": {"name": "Agent", "phone": "+994 50 000 00 00"}, "cta": "İndi zəng edin",
    "accent": "#F0662B", "dark": "#111114", "font": None, "font_bold": None, "music": None, "music_start": 0
}
FB = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]
FR = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf"]

def font(paths, size): return ImageFont.truetype(next(p for p in paths if p and os.path.exists(p)), size)
def hexc(h, a=255): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def sine(t): return 0.5 - 0.5 * np.cos(np.pi * clamp(t))
def expo_out(t): t = clamp(t); return 1 if t >= 1 else 1 - 2 ** (-10 * t)
def pop(f, up=3, settle=7, peak=1.15):
    if f <= 0: return 0.0
    if f < up: return peak * expo_out(f / up)
    return peak + (1 - peak) * sine((f - up) / settle)

class Reel:
    def __init__(s, spec, draft=False):
        s.S = spec; s.draft = draft; W, H = spec["size"]; k = 0.5 if draft else 1
        s.W, s.H = int(W * k) // 2 * 2, int(H * k) // 2 * 2; s.fps = spec["fps"]; s.beat = 60 / spec["bpm"]
        s.per = s.beat * spec.get("beats_per_photo", 3); s.k = k
        s.fb = lambda z: font([spec.get("font_bold")] + FB, int(z * k)); s.fr = lambda z: font([spec.get("font")] + FR, int(z * k))
        s.photos = [s.prep(p) for p in spec["photos"]]
        s.t_end_photos = s.per * len(s.photos); s.end_len = s.beat * 6; s.dur = s.t_end_photos + s.end_len
        s.acc = hexc(spec["accent"]); s.dark = hexc(spec["dark"])

    def prep(s, path):
        im = Image.open(path).convert("RGB"); W, H = s.W, s.H
        bg = im.resize((W, int(W * im.height / im.width)) if im.width / im.height < W / H else (int(H * im.width / im.height), H))
        bg = bg.resize((int(bg.width * 1.25), int(bg.height * 1.25))).filter(ImageFilter.GaussianBlur(28 * s.k))
        bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
        bg = Image.blend(bg, Image.new("RGB", bg.size, (0, 0, 0)), 0.35)
        sc = max(W * 1.18 / im.width, H * 0.62 / im.height); fg = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        return np.asarray(bg), np.asarray(fg)

    def photo_frame(s, i, u, move):
        bg, fg = s.photos[i]; W, H = s.W, s.H; fh, fw = fg.shape[:2]
        e = sine(u); z = {"push": 1 + 0.10 * e, "pull": 1.10 - 0.10 * e}.get(move, 1.04)
        pan = {"panl": 0.5 - 0.35 * e, "panr": 0.15 + 0.35 * e}.get(move, 0.5 - 0.0 * e)
        tilt = (e - 0.5) * 0.06 if move == "orbit" else 0
        tw, th = int(W * 1.0 * z), int(fh * W / fw * z)
        f2 = cv2.resize(fg, (max(tw, W), max(th, 2)), interpolation=cv2.INTER_LINEAR)
        x0 = int((f2.shape[1] - W) * (pan if move.startswith("pan") else 0.5)); crop = f2[:, x0:x0 + W]
        if tilt:
            h_, w_ = crop.shape[:2]; d = tilt * w_
            M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w_, 0], [w_, h_], [0, h_]]), np.float32([[d, -d * .4], [w_ + d, d * .4], [w_ - d, h_ - d * .4], [-d, h_ + d * .4]]))
            crop = cv2.warpPerspective(crop, M, (w_, h_), borderMode=cv2.BORDER_REFLECT)
        out = bg.copy(); y0 = int(H * 0.5 - crop.shape[0] / 2 - H * 0.04 * (e - 0.5))
        a, b = max(0, y0), min(H, y0 + crop.shape[0]); out[a:b] = crop[a - y0:b - y0]
        return out

    def frame(s, t):
        S, W, H = s.S, s.W, s.H; moves = ["push", "panl", "orbit", "panr", "pull"]
        if t < s.t_end_photos:
            i = int(t // s.per); u = (t - i * s.per) / s.per; img = s.photo_frame(i, u, moves[i % len(moves)])
            wf = 4 / s.fps; left = s.per - (t - i * s.per)
            if left < wf and i + 1 < len(s.photos):
                q = 1 - left / wf; nxt = s.photo_frame(i + 1, 0, moves[(i + 1) % len(moves)]); sh = int(W * sine(q))
                img = np.concatenate([img[:, sh:], nxt[:, :sh]], 1) if sh > 0 else img
                k = max(1, int(60 * s.k * np.sin(np.pi * q))); img = cv2.blur(img, (k, 1))
        else:
            img = np.full((H, W, 3), s.dark[:3], np.uint8)
        im = Image.fromarray(img).convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        f = lambda tt: (t - tt) * s.fps; M = int(75 * s.k)
        if t < s.t_end_photos:
            g = Image.linear_gradient("L").resize((W, H)); ov.paste((0, 0, 0, 0), (0, 0, W, H))
            shade = Image.new("RGBA", (W, H), (0, 0, 0, 255)); shade.putalpha(g.point(lambda v: int(max(0, v - 120) * 0.9)))
            im = Image.alpha_composite(im, shade)
        if t < s.per:
            fnt = s.fb(92); txt = S["hook"]; tw = d.textlength(txt, font=fnt); p = expo_out((t - 0.1) / 0.35); y = int(H * 0.17)
            mask = Image.new("RGBA", (W, int(130 * s.k)), (0, 0, 0, 0)); md = ImageDraw.Draw(mask)
            md.text(((W - tw) / 2, int((1 - p) * 120 * s.k)), txt, font=fnt, fill=(255, 255, 255, 255)); ov.alpha_composite(mask, (0, y))
        if t >= s.per * 0.5 and t < s.t_end_photos:
            tt = s.per * 0.5; sc = pop(f(tt)); fnt = s.fb(64); val = S["price"]["value"]
            roll = val * expo_out((t - tt) / 0.9); txt = f"{int(round(roll)):,}".replace(",", " ") + " " + S["price"]["currency"]
            card = Image.new("RGBA", (int(W - 2 * M), int(190 * s.k)), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
            cd.rounded_rectangle([0, 0, card.width - 1, card.height - 1], radius=int(28 * s.k), fill=s.dark[:3] + (225,))
            cd.rounded_rectangle([0, 0, int(14 * s.k), card.height - 1], radius=int(7 * s.k), fill=s.acc)
            cd.text((int(40 * s.k), int(22 * s.k)), S["title"], font=s.fr(40), fill=(220, 220, 225, 255))
            cd.text((int(40 * s.k), int(78 * s.k)), txt, font=fnt, fill=(255, 255, 255, 255))
            if sc > 0.01:
                cw, ch = int(card.width * sc), int(card.height * sc); c2 = card.resize((max(1, cw), max(1, ch)))
                ov.alpha_composite(c2, (int(M + (card.width - cw) / 2), int(H - int(H * 0.22) - card.height + (card.height - ch) / 2)))
        if s.per * 1.0 <= t < s.t_end_photos:
            x, y = M, int(H * 0.26); fnt = s.fb(40)
            for j, fact in enumerate(S["facts"]):
                tt = s.per + j * s.beat; sc = pop(f(tt))
                if sc <= 0.01: continue
                tw = d.textlength(fact, font=fnt); cw, ch = int(tw + 56 * s.k), int(78 * s.k)
                if x + cw > W - M: x = M; y += int(96 * s.k)
                chip = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); c = ImageDraw.Draw(chip)
                c.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=ch // 2, fill=(255, 255, 255, 235)); c.text((int(28 * s.k), int(16 * s.k)), fact, font=fnt, fill=s.dark)
                c2 = chip.resize((max(1, int(cw * sc)), max(1, int(ch * sc)))); ov.alpha_composite(c2, (int(x + cw * (1 - sc) / 2), int(y + ch * (1 - sc) / 2)))
                x += cw + int(16 * s.k)
        lt = s.per * (len(s.photos) - 1) + s.beat * 0.5
        if lt <= t < s.t_end_photos:
            sc = pop(f(lt)); fnt = s.fb(46); txt = S["location"]; tw = d.textlength(txt, font=fnt)
            cw, ch = int(tw + 130 * s.k), int(100 * s.k); card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); c = ImageDraw.Draw(card)
            c.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=int(24 * s.k), fill=s.acc)
            px, py, r = int(50 * s.k), ch // 2 - int(6 * s.k), int(18 * s.k)
            c.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255, 255)); c.polygon([(px - r * .8, py + r * .5), (px + r * .8, py + r * .5), (px, py + r * 2)], fill=(255, 255, 255, 255))
            c.ellipse([px - r * .4, py - r * .4, px + r * .4, py + r * .4], fill=s.acc); c.text((int(90 * s.k), int(22 * s.k)), txt, font=fnt, fill=(255, 255, 255, 255))
            c2 = card.resize((max(1, int(cw * sc)), max(1, int(ch * sc)))); ov.alpha_composite(c2, (int((W - cw * sc) / 2), int(H * 0.40)))
        if t >= s.t_end_photos:
            e0 = s.t_end_photos; lines = [(S["brand"], s.fb(84), (255, 255, 255, 255), 0), (S["agent"]["name"], s.fr(48), (200, 200, 205, 255), 1),
                                          (S["agent"]["phone"], s.fb(64), s.acc, 2), (S["cta"], s.fr(44), (255, 255, 255, 255), 3)]
            y = int(H * 0.36)
            for txt, fnt, col, j in lines:
                p = expo_out((t - e0 - j * s.beat * 0.5) / 0.35)
                if p > 0:
                    tw = d.textlength(txt, font=fnt); lh = int(fnt.size * 1.3)
                    mask = Image.new("RGBA", (W, lh), (0, 0, 0, 0)); ImageDraw.Draw(mask).text(((W - tw) / 2, int((1 - p) * lh)), txt, font=fnt, fill=col); ov.alpha_composite(mask, (0, y))
                y += int(fnt.size * 1.6)
            bar = int((W - 2 * M) * sine((t - e0) / (s.beat * 2))); d.rounded_rectangle([M, int(H * 0.33), M + bar, int(H * 0.33) + int(8 * s.k)], radius=4, fill=s.acc)
        return np.asarray(Image.alpha_composite(im, ov).convert("RGB"))

    def render(s, out):
        sub = 1 if s.draft else 3; tmp = out + ".v.mp4"; n = int(round(s.dur * s.fps))
        ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{s.W}x{s.H}", "-r", str(s.fps), "-i", "-",
                               "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        for i in range(n):
            t = i / s.fps
            fr = s.frame(t) if sub == 1 else np.mean([s.frame(t + ((k + .5) / sub - .5) * .5 / s.fps).astype(np.float32) for k in range(sub)], 0).astype(np.uint8)
            ff.stdin.write(fr.tobytes())
            if i % s.fps == 0: sys.stderr.write(f"{i}/{n}\n")
        ff.stdin.close(); ff.wait()
        if s.S.get("music"):
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-ss", str(s.S.get("music_start", 0)), "-i", s.S["music"], "-map", "0:v", "-map", "1:a",
                            "-af", f"afade=t=out:st={s.dur - 1:.2f}:d=1", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", out]); os.remove(tmp)
        else: os.replace(tmp, out)
        print(f"-> {out}  {s.dur:.2f} s, {len(s.photos)} photos x {s.per:.2f} s, BPM {s.S['bpm']} (cuts on beats)")

if __name__ == "__main__":
    a = sys.argv
    if len(a) > 1 and a[1] == "example": print(json.dumps(EXAMPLE, ensure_ascii=False, indent=1))
    elif len(a) > 3 and a[1] == "stills":
        spec = json.load(open(a[2], encoding="utf-8")); r = Reel(spec); os.makedirs(a[3], exist_ok=True)
        for t in [r.per * 0.8, r.per * 1.9, r.t_end_photos - 0.2, r.dur - 0.1]:
            Image.fromarray(r.frame(t)).save(os.path.join(a[3], f"still_{t:05.2f}.jpg"), quality=90); print(os.path.join(a[3], f"still_{t:05.2f}.jpg"))
    elif len(a) > 3 and a[1] == "render": Reel(json.load(open(a[2], encoding="utf-8")), "--draft" in a).render(a[3])
    else: print(USAGE)
