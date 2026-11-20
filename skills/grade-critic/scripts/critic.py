###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw

USAGE = """grade-critic: measure a grade like a colorist's scopes do, and say exactly what is wrong.

  python3 critic.py check IMG_or_VIDEO [more ...] OUT_DIR [--every 1.0] [--skin-target 123] [--style natural|film|bright]
      -> OUT_DIR/report.md, report.json, and per image a scopes sheet (image with clipped/crushed overlay,
         luma waveform, RGB parade, vectorscope with skin-tone line, histogram).
Measures per image: clipped highlights and crushed blacks (% of pixels), black/white points, mid-grey level,
contrast (p95-p5), colour cast in neutrals (Lab a/b of low-chroma pixels), saturation (mean chroma, % over gamut-ish
limits), skin-tone hue angle against the skin line, highlight/shadow tint.
Across a set (several images or video frames): exposure, white balance and saturation consistency; outliers flagged.
Needs: numpy, Pillow, opencv-python-headless, ffmpeg (for video).
"""

def srgb_to_lin(v): return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]], np.float32)
def lab(rgb):
    xyz = srgb_to_lin(rgb) @ M.T / np.array([0.9505, 1.0, 1.089], np.float32)
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

STYLES = {"natural": {"black": (0.02, 0.08), "white": (0.88, 0.98), "grey": (0.38, 0.52), "contrast": (0.45, 0.8), "chroma": (8, 30)},
          "film": {"black": (0.03, 0.12), "white": (0.80, 0.95), "grey": (0.36, 0.50), "contrast": (0.4, 0.75), "chroma": (6, 26)},
          "bright": {"black": (0.02, 0.10), "white": (0.90, 0.99), "grey": (0.45, 0.60), "contrast": (0.4, 0.75), "chroma": (8, 30)}}

def frames_of(path, every):
    if path.lower().endswith((".mp4", ".mov", ".m4v", ".webm", ".mkv")):
        dur = float(json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", path], capture_output=True, text=True).stdout)["format"]["duration"])
        out = []
        for t in np.arange(0, dur, every):
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
            if raw: out.append((f"{os.path.basename(path)}@{t:.1f}s", cv2.cvtColor(cv2.imdecode(np.frombuffer(raw, np.uint8), 1), cv2.COLOR_BGR2RGB)))
        return out
    return [(os.path.basename(path), np.asarray(Image.open(path).convert("RGB")))]

def analyze(name, rgb8, skin_target, style):
    im = rgb8.astype(np.float32) / 255; h, w = im.shape[:2]
    if max(h, w) > 1400: s = 1400 / max(h, w); im = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA); h, w = im.shape[:2]
    Y = im @ np.array([0.2126, 0.7152, 0.0722], np.float32); L = lab(im); C = np.hypot(L[..., 1], L[..., 2])
    clip = (im.max(-1) >= 0.995); crush = (im.max(-1) <= 0.012)
    mids = (L[..., 0] > 15) & (L[..., 0] < 95)
    neutral = (C < 8) & mids; cast_kind = "in neutrals"
    if neutral.mean() < 0.05 and mids.mean() > 0.05:
        neutral = mids & (C <= min(35.0, float(np.percentile(C[mids], 20)))); cast_kind = "likely (no true neutrals, least coloured pixels used)"
    cast = (float(np.median(L[..., 1][neutral])), float(np.median(L[..., 2][neutral]))) if neutral.mean() > 0.01 else (0.0, 0.0)
    hi, lo = Y >= np.percentile(Y, 90), Y <= np.percentile(Y, 10)
    tint = lambda m: (round(float(L[..., 1][m].mean()), 1), round(float(L[..., 2][m].mean()), 1))
    ycc = cv2.cvtColor((im * 255).astype(np.uint8), cv2.COLOR_RGB2YCrCb).astype(np.float32)
    cr, cb = ycc[..., 1] - 128, ycc[..., 2] - 128
    skin = (ycc[..., 1] > 135) & (ycc[..., 1] < 175) & (ycc[..., 2] > 85) & (ycc[..., 2] < 125) & (Y > 0.15) & (Y < 0.9)
    skin_angle = float(np.degrees(np.arctan2(cr[skin].mean(), cb[skin].mean())) % 360) if 0.01 < skin.mean() < 0.35 else None
    st = STYLES[style]; m = {
        "name": name, "size": [w, h], "clipped_pct": round(float(clip.mean() * 100), 2), "crushed_pct": round(float(crush.mean() * 100), 2),
        "black_point": round(float(np.percentile(Y, 1)), 3), "white_point": round(float(np.percentile(Y, 99)), 3), "mid_grey": round(float(np.median(Y)), 3),
        "contrast": round(float(np.percentile(Y, 95) - np.percentile(Y, 5)), 3), "cast_ab": [round(cast[0], 1), round(cast[1], 1)],
        "chroma_mean": round(float(C.mean()), 1), "oversat_pct": round(float((C > 75).mean() * 100), 2),
        "highlight_tint_ab": tint(hi), "shadow_tint_ab": tint(lo), "skin_pct": round(float(skin.mean() * 100), 1),
        "skin_angle": round(skin_angle, 1) if skin_angle is not None else None}
    issues = []
    if m["clipped_pct"] > 1.0: issues.append(("high", f"{m['clipped_pct']}% clipped highlights: pull highlights / lower exposure, or roll off with a softer curve"))
    if m["crushed_pct"] > 2.0: issues.append(("high", f"{m['crushed_pct']}% crushed blacks: lift shadows or soften the toe"))
    if not st["black"][0] <= m["black_point"] <= st["black"][1]: issues.append(("mid", f"black point {m['black_point']} (target {st['black'][0]}-{st['black'][1]} for {style})"))
    if not st["white"][0] <= m["white_point"] <= st["white"][1]: issues.append(("mid", f"white point {m['white_point']} (target {st['white'][0]}-{st['white'][1]})"))
    if not st["grey"][0] <= m["mid_grey"] <= st["grey"][1]: issues.append(("mid", f"median level {m['mid_grey']} looks {'dark' if m['mid_grey'] < st['grey'][0] else 'bright'} (target {st['grey'][0]}-{st['grey'][1]})"))
    if not st["contrast"][0] <= m["contrast"] <= st["contrast"][1]: issues.append(("low", f"contrast {m['contrast']} ({'flat' if m['contrast'] < st['contrast'][0] else 'harsh'})"))
    if np.hypot(*cast) > 4: issues.append(("high", f"colour cast {cast_kind} a={cast[0]:.1f} b={cast[1]:.1f}: {'warm/yellow' if cast[1] > 0 else 'cool/blue'}{' + magenta' if cast[0] > 2 else ' + green' if cast[0] < -2 else ''}; correct white balance"))
    if m["chroma_mean"] < st["chroma"][0]: issues.append(("low", f"saturation low (mean chroma {m['chroma_mean']})"))
    if m["chroma_mean"] > st["chroma"][1] or m["oversat_pct"] > 2: issues.append(("mid", f"saturation high (mean chroma {m['chroma_mean']}, {m['oversat_pct']}% extreme)"))
    if skin_angle is not None and abs(((skin_angle - skin_target) + 180) % 360 - 180) > 10:
        d = ((skin_angle - skin_target) + 180) % 360 - 180
        issues.append(("high", f"skin tones off the skin line by {d:+.0f} deg ({'too red/magenta' if d > 0 else 'too yellow/green'}); fix with a hue vs hue or WB tweak"))
    m["issues"] = [{"severity": s, "text": t} for s, t in issues]
    m["score"] = max(0, 100 - sum({"high": 18, "mid": 9, "low": 4}[s] for s, _ in issues))
    return m, im, Y, clip, crush, cr, cb, skin_target

def scopes(path, im, Y, clip, crush, cr, cb, skin_target, m):
    h, w = im.shape[:2]; S = 360; vis = (im * 255).astype(np.uint8).copy()
    vis[clip] = [255, 40, 40]; vis[crush] = [40, 90, 255]
    pv = Image.fromarray(vis).resize((int(w * S / h), S))
    wf = np.zeros((256, 512), np.float32); xs = (np.arange(w) * 511 / max(1, w - 1)).astype(int)
    for c in range(0, w, max(1, w // 512)): np.add.at(wf, (255 - (Y[:, c] * 255).astype(int), np.full(h, xs[c])), 1)
    wf = np.clip(np.log1p(wf) / np.log1p(wf.max() + 1e-6) * 255, 0, 255).astype(np.uint8)
    par = np.zeros((256, 3 * 256, 3), np.uint8)
    for k in range(3):
        acc = np.zeros((256, 256), np.float32); xs2 = (np.arange(w) * 255 / max(1, w - 1)).astype(int)
        for c in range(0, w, max(1, w // 256)): np.add.at(acc, (255 - (im[:, c, k] * 255).astype(int), np.full(h, xs2[c])), 1)
        par[:, k * 256:(k + 1) * 256, k] = np.clip(np.log1p(acc) / np.log1p(acc.max() + 1e-6) * 255, 0, 255).astype(np.uint8)
    vs = np.zeros((256, 256), np.float32); np.add.at(vs, (np.clip(128 - cr.astype(int), 0, 255), np.clip(128 + cb.astype(int), 0, 255)), 1)
    vsi = Image.fromarray(np.clip(np.log1p(vs) / np.log1p(vs.max() + 1e-6) * 255, 0, 255).astype(np.uint8)).convert("RGB"); d = ImageDraw.Draw(vsi)
    ang = np.radians(skin_target); d.line([(128, 128), (128 + 120 * np.cos(ang), 128 - 120 * np.sin(ang))], fill=(255, 170, 60), width=2)
    d.ellipse([28, 28, 228, 228], outline=(90, 90, 90))
    hist = Image.new("RGB", (256, 256), (10, 10, 10)); hd = ImageDraw.Draw(hist)
    for k, col in enumerate([(255, 80, 80), (80, 255, 80), (80, 140, 255)]):
        hh = np.histogram(im[..., k], 128, (0, 1))[0]; hh = hh / (hh.max() + 1e-6) * 240
        hd.line([(i * 2, 255 - v) for i, v in enumerate(hh)], fill=col, width=1)
    W = pv.width + 512 + 20; sheet = Image.new("RGB", (max(W, 3 * 256 + 552), S + 300), (14, 14, 14))
    sheet.paste(pv, (0, 0)); sheet.paste(Image.fromarray(wf).convert("RGB").resize((512, S)), (pv.width + 10, 0))
    sheet.paste(Image.fromarray(par), (0, S + 30)); sheet.paste(vsi, (3 * 256 + 10, S + 30)); sheet.paste(hist, (3 * 256 + 276, S + 30))
    dd = ImageDraw.Draw(sheet); dd.text((4, S + 6), f"{m['name']}  score {m['score']}  (red = clipped, blue = crushed, orange line = skin)", fill=(230, 230, 230))
    sheet.save(path, quality=90)

def check(paths, out, every=1.0, skin_target=123.0, style="natural"):
    os.makedirs(out, exist_ok=True); res = []
    for p in paths:
        for name, rgb in frames_of(p, every):
            m, *rest = analyze(name, rgb, skin_target, style); res.append(m)
            scopes(os.path.join(out, f"scopes_{len(res):03d}.jpg"), *rest, m); m["scopes"] = f"scopes_{len(res):03d}.jpg"
    md = [f"# Grade check ({len(res)} images/frames, style {style})", ""]
    if len(res) > 1:
        keys = {"mid_grey": "exposure", "contrast": "contrast", "chroma_mean": "saturation"}
        md.append("## Consistency across the set")
        for k, lab_ in keys.items():
            v = np.array([r[k] for r in res]); z = (v - np.median(v)) / (v.std() + 1e-6)
            outl = [f"{res[i]['name']} ({v[i]:.2f})" for i in np.where(np.abs(z) > 1.5)[0]]
            md.append(f"- {lab_}: median {np.median(v):.2f}, spread {v.std():.2f}" + (f"; outliers: {', '.join(outl)}" if outl else "; consistent"))
        ab = np.array([r["cast_ab"] for r in res]); dist = np.hypot(*(ab - np.median(ab, 0)).T)
        bad = [res[i]["name"] for i in np.where(dist > 3)[0]]
        md.append("- white balance: " + (f"drifts on {', '.join(bad)}" if bad else "consistent")); md.append("")
    for r in sorted(res, key=lambda r: r["score"]):
        md += [f"## {r['name']}: {r['score']}/100  ({r['scopes']})",
               f"black {r['black_point']} / grey {r['mid_grey']} / white {r['white_point']}, contrast {r['contrast']}, clipped {r['clipped_pct']}%, crushed {r['crushed_pct']}%, "
               f"cast a/b {r['cast_ab']}, chroma {r['chroma_mean']}, skin {r['skin_angle']} deg ({r['skin_pct']}% px)"]
        md += [f"- [{i['severity']}] {i['text']}" for i in r["issues"]] or ["- no issues"]
        md.append("")
    open(os.path.join(out, "report.md"), "w").write("\n".join(md)); json.dump(res, open(os.path.join(out, "report.json"), "w"), indent=1); print("\n".join(md))

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "check":
        flags = {"--every", "--skin-target", "--style"}; pos = [x for i, x in enumerate(a[2:], 2) if x not in flags and a[i - 1] not in flags]
        check(pos[:-1], pos[-1], float(opt("--every", 1.0)), float(opt("--skin-target", 123)), opt("--style", "natural"))
    else: print(USAGE)
