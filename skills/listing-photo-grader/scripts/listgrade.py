###############
# Qiyas Sadıqov CC
###############
import json, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageOps

USAGE = """listing-photo-grader: batch-grade real-estate photos to a consistent, honest, professional standard.

  python3 listgrade.py grade IN_DIR OUT_DIR [--long 2048] [--warmth 0.35] [--hdr 0.7] [--clarity 0.4] [--verticals on|off]
        [--max-tilt 8] [--look look.cube] [--look-strength 0.5] [--denoise 0] [--sharpen 0.4] [--consistency 0.7] [--quality 90] [--brightness 0.18]
      -> OUT_DIR/<name>.jpg for every photo, before_after.jpg contact sheet, report.md + report.json (every change, per photo)

Per photo, in order:
  1. verticals: detects near-vertical architectural lines and removes camera roll + keystone (converging verticals)
     with a perspective correction, then crops the empty borders (skipped when lines disagree or tilt > --max-tilt)
  2. white balance from near-neutral pixels, keeping --warmth of the room's own warmth (warm light sells interiors)
  3. window pull: exposure fusion of virtual -1/0/+1 EV versions, so the room is bright and the window still shows outside,
     then the median brightness is set to --brightness (linear, 0.18 = classic bright interior) with a soft highlight shoulder
  4. clarity (local contrast on luminance only), optional denoise, light sharpening
  5. set consistency: every photo is pulled toward the set's median exposure and white balance
  6. optional brand look (.cube from film-lab / reference-matcher / show-look-builder) at a gentle strength
Honesty rule built in: only global tone/colour and geometry corrections; nothing is added, removed or replaced.
Needs: numpy, Pillow, opencv-python-headless.
"""

def srgb_to_lin(v): return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
def lin_to_srgb(v): v = np.clip(v, 0, 1); return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)

def fix_verticals(img, max_tilt=8.0):
    H, W = img.shape[:2]; s = 900 / max(H, W); small = cv2.resize(img, (int(W * s), int(H * s)))
    g = cv2.cvtColor((small * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY); e = cv2.Canny(cv2.GaussianBlur(g, (3, 3), 0), 50, 150)
    lines = cv2.HoughLinesP(e, 1, np.pi / 360, 60, minLineLength=int(small.shape[0] * 0.15), maxLineGap=8)
    info = {"applied": False}
    if lines is None: info["reason"] = "no lines"; return img, info
    th, xs, ws = [], [], []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        dx, dy = x2 - x1, y2 - y1
        if dy == 0: continue
        if dy < 0: x1, y1, x2, y2 = x2, y2, x1, y1; dx, dy = -dx, -dy
        ang = np.degrees(np.arctan2(dx, dy))
        if abs(ang) < 20: th.append(ang); xs.append(((x1 + x2) / 2) / small.shape[1] - 0.5); ws.append(np.hypot(dx, dy))
    if len(th) < 3: info["reason"] = f"only {len(th)} vertical lines"; return img, info
    th, xs, ws = map(np.array, (th, xs, ws)); A = np.stack([xs, np.ones_like(xs)], 1) * ws[:, None]
    (a, b), *_ = np.linalg.lstsq(A, th * ws, rcond=None); resid = float(np.sqrt(np.average((th - (a * xs + b)) ** 2, weights=ws)))
    tl, tr = b - a / 2, b + a / 2
    if max(abs(tl), abs(tr)) > max_tilt or resid > 2.5: info.update(reason=f"tilt {tl:.1f}/{tr:.1f} deg or line spread {resid:.1f} too large, left as is"); return img, info
    if max(abs(tl), abs(tr)) < 0.3: info.update(reason="already straight"); return img, info
    roll = float(b); R = np.vstack([cv2.getRotationMatrix2D((W / 2, H / 2), -roll, 1.0), [0, 0, 1]])
    dl, dr = H * np.tan(np.radians(tl - roll)), H * np.tan(np.radians(tr - roll))
    src = np.float32([[-dl, 0], [W - dr, 0], [W, H], [0, H]]); dst = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    Mx = cv2.getPerspectiveTransform(src, dst) @ R; out = cv2.warpPerspective(img, Mx, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    q = cv2.perspectiveTransform(np.float32([[[0, 0]], [[W, 0]], [[W, H]], [[0, H]]]), Mx)[:, 0]
    x0, x1 = int(np.ceil(max(q[0, 0], q[3, 0], 0))), int(np.floor(min(q[1, 0], q[2, 0], W)))
    y0, y1 = int(np.ceil(max(q[0, 1], q[1, 1], 0))), int(np.floor(min(q[2, 1], q[3, 1], H)))
    if x1 - x0 > W * 0.6 and y1 - y0 > H * 0.6: out = out[y0:y1, x0:x1]
    else: info.update(reason="correction would crop too much, left as is"); return img, info
    info.update(applied=True, tilt_left=round(float(tl), 2), tilt_right=round(float(tr), 2), lines=int(len(th)), crop=[int(out.shape[1]), int(out.shape[0])])
    return out, info

def white_balance(img, keep=0.35):
    lin = srgb_to_lin(img); px = lin.reshape(-1, 3); lum = px @ np.array([0.2126, 0.7152, 0.0722])
    m = (lum > np.percentile(lum, 25)) & (lum < np.percentile(lum, 97)); p = px[m]
    ch = (p.max(1) - p.min(1)) / (p.max(1) + 1e-6); p = p[ch <= np.percentile(ch, 30)]
    ref = np.median(p, 0); g = ref.mean() / np.maximum(ref, 1e-6); g = g / g[1]; g = np.clip(g ** (1 - keep), 0.6, 1.6)
    blown = np.clip((img.min(-1, keepdims=True) - 0.92) / 0.06, 0, 1)
    return lin_to_srgb(lin * (g * (1 - blown) + blown)), [round(float(x), 3) for x in g], blown

def set_brightness(img, target=0.18):
    lin = srgb_to_lin(img); med = float(np.median(lin @ np.array([0.2126, 0.7152, 0.0722])))
    lin = lin * (target / max(med, 1e-4)); lin = lin / (1 + np.maximum(lin - 0.8, 0) * 1.5)
    return lin_to_srgb(lin)

def window_pull(img, amount=0.7):
    if amount <= 0: return img
    lin = srgb_to_lin(img); stack = [(lin_to_srgb(lin * k) * 255).astype(np.uint8) for k in (0.45, 1.0, 2.0)]
    fused = cv2.createMergeMertens(1.0, 1.0, 0.0).process([s.astype(np.float32) / 255 for s in stack])
    fused = np.clip(fused, 0, 1)
    lo, hi = np.percentile(fused, 0.5), np.percentile(fused, 99.7); fused = np.clip((fused - lo) / max(hi - lo, 1e-3), 0, 1)
    return img + (fused - img) * amount

def clarity(img, amount=0.4):
    if amount <= 0: return img
    lab = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2LAB); L = lab[..., 0]
    cl = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8)).apply(L)
    lab[..., 0] = np.clip(L + (cl.astype(np.float32) - L) * amount, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB).astype(np.float32) / 255

def sharpen(img, amount=0.4):
    if amount <= 0: return img
    bl = cv2.GaussianBlur(img, (0, 0), 1.2); return np.clip(img + (img - bl) * amount, 0, 1)

def read_cube(path):
    size, rows = None, []
    for line in open(path):
        t = line.split()
        if not t or t[0].startswith("#"): continue
        if t[0] == "LUT_3D_SIZE": size = int(t[1])
        elif len(t) == 3:
            try: rows.append([float(x) for x in t])
            except ValueError: pass
    return np.array(rows, np.float32).reshape(size, size, size, 3), size

def trilinear(table, x, S):
    p = np.clip(x, 0, 1) * (S - 1); i0 = np.minimum(np.floor(p).astype(np.int32), S - 2); f = p - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]; fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    c = lambda db, dg, dr: table[b0 + db, g0 + dg, r0 + dr]
    c00 = c(0, 0, 0) * (1 - fr) + c(0, 0, 1) * fr; c01 = c(0, 1, 0) * (1 - fr) + c(0, 1, 1) * fr
    c10 = c(1, 0, 0) * (1 - fr) + c(1, 0, 1) * fr; c11 = c(1, 1, 0) * (1 - fr) + c(1, 1, 1) * fr
    return (c00 * (1 - fg) + c01 * fg) * (1 - fb) + (c10 * (1 - fg) + c11 * fg) * fb

def stats(img):
    lin = srgb_to_lin(img); lum = lin @ np.array([0.2126, 0.7152, 0.0722]); m = (lum > 0.03) & (lum < 0.85)
    return {"median": float(np.median(lum)), "rb": float(np.log(np.median(lin[..., 0][m]) / max(np.median(lin[..., 2][m]), 1e-4))) if m.any() else 0.0,
            "clipped": float((img.max(-1) > 0.985).mean() * 100), "crushed": float((img.max(-1) < 0.02).mean() * 100)}

def grade(inp, out, o):
    os.makedirs(out, exist_ok=True)
    files = [f for f in sorted(os.listdir(inp)) if f.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic"))]
    if not files: raise SystemExit("no photos found")
    look = read_cube(o["look"]) if o["look"] else None; mid, rep = [], []
    for f in files:
        pil = ImageOps.exif_transpose(Image.open(os.path.join(inp, f))).convert("RGB"); pil.thumbnail((o["long"], o["long"]), Image.LANCZOS)
        img = np.asarray(pil).astype(np.float32) / 255; before = stats(img); steps = {}
        if o["verticals"] == "on": img, steps["verticals"] = fix_verticals(img, o["max_tilt"])
        img, steps["wb_gains"], blown = white_balance(img, o["warmth"])
        img = window_pull(img, o["hdr"]); img = set_brightness(img, o["brightness"]); img = clarity(img, o["clarity"])
        if o["denoise"] > 0:
            u8 = (img * 255).astype(np.uint8); img = cv2.fastNlMeansDenoisingColored(u8, None, 2 + 4 * o["denoise"], 2 + 4 * o["denoise"], 7, 21).astype(np.float32) / 255
        img = sharpen(img, o["sharpen"]); mid.append((f, img, before, steps, blown))
    S_ = [stats(m[1]) for m in mid]; med_l = float(np.median([s["median"] for s in S_])); med_rb = float(np.median([s["rb"] for s in S_]))
    thumbs = []
    for (f, img, before, steps, blown), s in zip(mid, S_):
        k = o["consistency"]; gain = (med_l / max(s["median"], 1e-4)) ** k; rb = (med_rb - s["rb"]) * k
        tint = np.array([np.exp(rb / 2), 1.0, np.exp(-rb / 2)], np.float32)
        lin = srgb_to_lin(img) * gain * (tint * (1 - blown) + blown)
        img2 = lin_to_srgb(lin / max(1.0, np.percentile(lin, 99.8)) if np.percentile(lin, 99.8) > 1 else lin)
        if look is not None:
            T, Sz = look; lk = trilinear(T, img2, Sz); img2 = img2 + (lk - img2) * o["look_strength"]
        img2 = np.clip(img2, 0, 1); name = os.path.splitext(f)[0] + ".jpg"
        Image.fromarray((img2 * 255 + 0.5).astype(np.uint8)).save(os.path.join(out, name), quality=o["quality"], subsampling=0, optimize=True)
        after = stats(img2); steps.update(exposure_set_gain=round(float(gain), 3), balance_shift=round(float(rb), 3))
        rep.append({"file": f, "out": name, "before": {k: round(v, 3) for k, v in before.items()}, "after": {k: round(v, 3) for k, v in after.items()}, "steps": steps})
        src = ImageOps.exif_transpose(Image.open(os.path.join(inp, f))).convert("RGB"); src.thumbnail((360, 360)); dst = Image.fromarray((img2 * 255).astype(np.uint8)); dst.thumbnail((360, 360))
        thumbs.append((f, src, dst))
    th = max(t[1].height for t in thumbs); sheet = Image.new("RGB", (2 * 370 + 20, len(thumbs) * (th + 28) + 10), (16, 16, 16)); d = ImageDraw.Draw(sheet)
    for i, (f, a, b) in enumerate(thumbs):
        sheet.paste(a, (10, 10 + i * (th + 28))); sheet.paste(b, (380, 10 + i * (th + 28))); d.text((12, 12 + i * (th + 28) + th), f"{f}: before | after", fill=(230, 230, 230))
    sheet.save(os.path.join(out, "before_after.jpg"), quality=88)
    md = [f"# Listing photo grade: {len(rep)} photos", "", "Edits are global only (tone, colour, geometry). Nothing was added, removed or replaced.", "",
          "| photo | verticals | WB gains | exposure median before > after | clipped % before > after | crushed % before > after |", "|---|---|---|---|---|---|"]
    for r in rep:
        v = r["steps"].get("verticals", {}); vt = f"fixed {v.get('tilt_left')}/{v.get('tilt_right')} deg" if v.get("applied") else v.get("reason", "off")
        md.append(f"| {r['file']} | {vt} | {r['steps']['wb_gains']} | {r['before']['median']:.3f} > {r['after']['median']:.3f} | {r['before']['clipped']:.1f} > {r['after']['clipped']:.1f} | {r['before']['crushed']:.1f} > {r['after']['crushed']:.1f} |")
    spread = lambda key, which: float(np.std([r[which][key] for r in rep]))
    md += ["", f"Set consistency (std of exposure median): before {spread('median', 'before'):.3f}, after {spread('median', 'after'):.3f}", "", "Contact sheet: before_after.jpg"]
    open(os.path.join(out, "report.md"), "w").write("\n".join(md)); json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1); print("\n".join(md))

if __name__ == "__main__":
    a = sys.argv; g = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "grade":
        grade(a[2], a[3], {"long": int(g("--long", 2048)), "warmth": float(g("--warmth", 0.35)), "hdr": float(g("--hdr", 0.7)), "clarity": float(g("--clarity", 0.4)),
                           "verticals": g("--verticals", "on"), "max_tilt": float(g("--max-tilt", 8)), "look": g("--look"), "look_strength": float(g("--look-strength", 0.5)),
                           "denoise": float(g("--denoise", 0)), "sharpen": float(g("--sharpen", 0.4)), "consistency": float(g("--consistency", 0.7)), "quality": int(g("--quality", 90)), "brightness": float(g("--brightness", 0.18))})
    else: print(USAGE)
