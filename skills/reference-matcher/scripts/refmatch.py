###############
# Qiyas Sadıqov CC
###############
import json, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw

USAGE = """reference-matcher: measure the look of a reference frame/photo and build a LUT that moves your image toward it,
with an honest similarity report.

  python3 refmatch.py measure REF.jpg OUT_DIR        -> look fingerprint: tone curve, black/white points, contrast,
                                                       palette, saturation per hue, split-tone tints, grain, halation hint
  python3 refmatch.py build REF.jpg TARGET.jpg OUT.cube [--strength 1.0] [--tone 1.0] [--color 1.0] [--size 33] [--preview prev.jpg]
      -> tone: luminance distribution matching (smoothed, monotonic); colour: per-hue chroma scale + hue rotation
         (12 hue sectors, smoothly interpolated, clamped), neutral-axis tints per shadows/mids/highlights.
         Writes OUT.cube (sRGB in, sRGB out), OUT.report.md with before/after similarity and what could NOT transfer.
  python3 refmatch.py apply IN.jpg LOOK.cube OUT.jpg [--strength 1]
Several references: pass REF as a folder; their statistics are pooled (a "look" rather than one frame).
Needs: numpy, Pillow, opencv-python-headless.
"""

def srgb_to_lin(v): return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
def lin_to_srgb(v): v = np.clip(v, 0, 1); return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]], np.float32); Mi = np.linalg.inv(M).astype(np.float32)
WP = np.array([0.9505, 1.0, 1.089], np.float32)
def to_lab(rgb):
    xyz = srgb_to_lin(rgb) @ M.T / WP; f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
def from_lab(L):
    fy = (L[..., 0] + 16) / 116; fx = fy + L[..., 1] / 500; fz = fy - L[..., 2] / 200
    f = np.stack([fx, fy, fz], -1); xyz = np.where(f > 0.2069, f ** 3, (f - 16 / 116) / 7.787) * WP
    return lin_to_srgb(xyz @ Mi.T)

def load(p, maxs=900):
    if os.path.isdir(p):
        ims = [load(os.path.join(p, f), maxs) for f in sorted(os.listdir(p)) if f.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"))]
        return np.concatenate([i.reshape(-1, 1, 3) for i in ims], 0)
    im = Image.open(p).convert("RGB"); im.thumbnail((maxs, maxs)); return np.asarray(im).astype(np.float32) / 255

SECT = 12
def stats(rgb):
    L = to_lab(rgb).reshape(-1, 3); C = np.hypot(L[:, 1], L[:, 2]); H = np.degrees(np.arctan2(L[:, 2], L[:, 1])) % 360
    s = {"L": L[:, 0], "cdf": np.cumsum(np.histogram(L[:, 0], 256, (0, 100))[0]) / len(L)}
    col = C > 6; s["sect"] = []
    for k in range(SECT):
        c0 = k * 360 / SECT; m = col & (((H - c0 + 360) % 360) < 360 / SECT)
        if m.mean() > 0.004:
            hh = np.radians(H[m]); s["sect"].append({"share": float(m.mean()), "chroma": float(np.median(C[m])), "hue": float(np.degrees(np.arctan2(np.sin(hh).mean(), np.cos(hh).mean())) % 360)})
        else: s["sect"].append(None)
    neu = C < 10
    for name, lo, hi in [("shadows", 0, 30), ("mids", 30, 70), ("highlights", 70, 101)]:
        m = neu & (L[:, 0] >= lo) & (L[:, 0] < hi); s[name] = (float(L[m, 1].mean()), float(L[m, 2].mean())) if m.sum() > 50 else (0.0, 0.0)
    s["black"], s["white"] = float(np.percentile(L[:, 0], 1)), float(np.percentile(L[:, 0], 99)); s["contrast"] = float(np.percentile(L[:, 0], 95) - np.percentile(L[:, 0], 5))
    s["chroma"] = float(C.mean()); s["mean_ab"] = (float(np.median(L[:, 1])), float(np.median(L[:, 2]))); return s

def texture(rgb):
    g = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    hp = g - cv2.GaussianBlur(g, (0, 0), 1.2); flat = cv2.GaussianBlur(np.abs(g - cv2.GaussianBlur(g, (0, 0), 6)), (0, 0), 6) < 0.02
    grain = float(hp[flat].std()) if flat.mean() > 0.05 else None
    hi = g > 0.92; halo = None
    if hi.mean() > 0.002:
        ring = (cv2.dilate(hi.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0) & ~hi
        if ring.sum() > 50: r, gg, b = [rgb[..., k][ring].mean() for k in range(3)]; halo = float(r - b)
    return grain, halo

def measure(ref, out):
    os.makedirs(out, exist_ok=True); rgb = load(ref); s = stats(rgb)
    grain, halo = texture(rgb if rgb.ndim == 3 and rgb.shape[1] > 1 else rgb)
    im = Image.new("RGB", (900, 330), (16, 16, 16)); d = ImageDraw.Draw(im)
    d.line([(40, 300), (290, 50)], fill=(70, 70, 70)); pts = [(40 + i / 255 * 250, 300 - np.searchsorted(s["cdf"], i / 255) / 255 * 250) for i in range(0, 256, 4)]
    d.line(pts, fill=(240, 240, 240), width=2); d.text((40, 20), "tone distribution (cumulative)", fill=(200, 200, 200))
    x = 340
    for k, sec in enumerate(s["sect"]):
        if not sec: continue
        hue = np.radians(sec["hue"]); lab = np.array([[[60, sec["chroma"] * np.cos(hue), sec["chroma"] * np.sin(hue)]]], np.float32)
        col = tuple(int(v * 255) for v in from_lab(lab)[0, 0]); w = max(6, int(sec["share"] * 900))
        d.rectangle([x, 60, x + w, 200], fill=col); d.text((x, 210), f"{int(sec['hue'])}", fill=(180, 180, 180)); x += w + 4
        if x > 880: break
    d.text((340, 20), "palette by hue sector (width = share, colour = median chroma)", fill=(200, 200, 200))
    im.save(os.path.join(out, "fingerprint.png"))
    rep = {"black_L": round(s["black"], 1), "white_L": round(s["white"], 1), "contrast_L": round(s["contrast"], 1), "mean_chroma": round(s["chroma"], 1),
           "tints_ab": {k: [round(v, 1) for v in s[k]] for k in ("shadows", "mids", "highlights")}, "grain_std": None if grain is None else round(grain, 4),
           "halation_red_minus_blue": None if halo is None else round(halo, 3), "sectors": s["sect"]}
    json.dump(rep, open(os.path.join(out, "fingerprint.json"), "w"), indent=1)
    md = [f"# Look fingerprint: {os.path.basename(ref)}", f"- black L {rep['black_L']}, white L {rep['white_L']}, contrast {rep['contrast_L']} (L units)",
          f"- mean chroma {rep['mean_chroma']} (natural ~15-25, muted < 12, vivid > 28)",
          f"- split tone (Lab a/b): shadows {rep['tints_ab']['shadows']}, mids {rep['tints_ab']['mids']}, highlights {rep['tints_ab']['highlights']}",
          f"- grain (high-pass std in flat areas): {rep['grain_std']} (clean < 0.006, visible 0.01-0.02, heavy > 0.025)",
          f"- halation hint (red minus blue around highlights): {rep['halation_red_minus_blue']} (> 0.05 suggests warm halos)", "", "fingerprint.png: tone curve and palette"]
    open(os.path.join(out, "fingerprint.md"), "w").write("\n".join(md)); print("\n".join(md))

def circ_interp(params, hue):
    c = np.array([p[0] for p in params]); v = np.array([p[1] for p in params]); o = np.argsort(c); c, v = c[o], v[o]
    cc = np.concatenate([c - 360, c, c + 360]); vv = np.concatenate([v, v, v]); return np.interp(hue, cc, vv)

def build_fn(R, T, strength=1.0, tone=1.0, color=1.0):
    q = np.linspace(0, 1, 257); tl = np.quantile(T["L"], q); rl = np.quantile(R["L"], q)
    tl = np.maximum.accumulate(tl + np.arange(257) * 1e-6); lmap_x, lmap_y = tl, rl
    k = np.ones(9) / 9; sm = np.convolve(np.pad(lmap_y, 4, mode="edge"), k, "valid"); sm = np.maximum.accumulate(sm)
    cs, hs, warn = [], [], []
    for i, (r, t) in enumerate(zip(R["sect"], T["sect"])):
        ctr = i * 360 / SECT + 360 / SECT / 2
        if r and t:
            cs.append((ctr, float(np.clip(r["chroma"] / max(t["chroma"], 1e-3), 0.5, 1.8))))
            hs.append((ctr, float(np.clip(((r["hue"] - t["hue"] + 180) % 360) - 180, -25, 25))))
        elif r and not t and r["share"] > 0.02: warn.append(f"reference has hue {int(r['hue'])} deg ({r['share']:.0%} of pixels) that your image does not contain: that part of the look cannot transfer")
    if not cs: cs, hs = [(0, 1.0), (180, 1.0)], [(0, 0.0), (180, 0.0)]
    wb = (np.array(R["mean_ab"]) - np.array(T["mean_ab"])) * 0.8
    tint_r = {k: (np.array(R[k]) - np.array(T[k])) * 0.4 for k in ("shadows", "mids", "highlights")}
    def fn(rgb):
        L = to_lab(rgb); l, a, b = L[..., 0], L[..., 1], L[..., 2]
        l2 = np.interp(l, lmap_x, sm); l2 = l + (l2 - l) * tone * strength
        a = a + wb[0] * color * strength; b = b + wb[1] * color * strength
        C = np.hypot(a, b); H = np.degrees(np.arctan2(b, a)) % 360
        sc = circ_interp(cs, H); dh = circ_interp(hs, H); w = np.clip((C - 2) / 8, 0, 1)
        C2 = C * (1 + (sc - 1) * w * color * strength); H2 = np.radians(H + dh * w * color * strength)
        a2, b2 = C2 * np.cos(H2), C2 * np.sin(H2)
        ws = np.clip((45 - l2) / 25, 0, 1); wh = np.clip((l2 - 55) / 25, 0, 1); wm = np.clip(1 - ws - wh, 0, 1)
        for wt, key in ((ws, "shadows"), (wm, "mids"), (wh, "highlights")):
            a2 = a2 + wt * tint_r[key][0] * color * strength * 0.8; b2 = b2 + wt * tint_r[key][1] * color * strength * 0.8
        return from_lab(np.stack([l2, a2, b2], -1))
    return fn, warn

def write_cube(path, size, fn, title):
    r = np.linspace(0, 1, size, dtype=np.float32); b, g, rr = np.meshgrid(r, r, r, indexing="ij")
    out = fn(np.stack([rr, g, b], -1).reshape(-1, 1, 3)).reshape(-1, 3)
    with open(path, "w") as f:
        f.write(f'TITLE "{title}"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n'); f.writelines(f"{x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in out)

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

def similarity(A, B):
    la, lb = to_lab(A).reshape(-1, 3), to_lab(B).reshape(-1, 3); out = {}
    for i, (n, rng) in enumerate([("L", (0, 100)), ("a", (-60, 60)), ("b", (-60, 60))]):
        ha = np.histogram(la[:, i], 64, rng)[0] / len(la); hb = np.histogram(lb[:, i], 64, rng)[0] / len(lb); out[n] = round(float(np.minimum(ha, hb).sum()), 3)
    out["overall"] = round(float(np.mean(list(out.values()))), 3); return out

def build(ref, target, out, strength=1.0, tone=1.0, color=1.0, size=33, preview=None):
    Rrgb, Trgb = load(ref), load(target); R, T = stats(Rrgb), stats(Trgb)
    fn, warn = build_fn(R, T, strength, tone, color)
    write_cube(out, size, fn, f"refmatch {os.path.basename(ref)} (sRGB in/out)")
    table, S = read_cube(out); after = trilinear(table, Trgb, S)
    before_s, after_s = similarity(Trgb, Rrgb), similarity(after, Rrgb)
    if preview:
        full = np.asarray(Image.open(target).convert("RGB")).astype(np.float32) / 255; res = trilinear(table, full, S)
        Image.fromarray((np.clip(res, 0, 1) * 255).astype(np.uint8)).save(preview, quality=93)
    md = [f"# Reference match: {os.path.basename(target)} -> {os.path.basename(ref)}", f"- LUT: {out} ({size}^3, strength {strength}, tone {tone}, colour {color})",
          f"- similarity before: {before_s}", f"- similarity after:  {after_s}  (1.0 = identical distributions)",
          "- what moved: tone distribution, global colour balance, per-hue saturation and hue, shadow/mid/highlight tints",
          "- what a LUT cannot carry: lighting, contrast of the scene itself, lens, depth of field, grain, halation (add grain/halation with film-lab)"] + [f"- WARNING: {w}" for w in warn]
    open(os.path.splitext(out)[0] + ".report.md", "w").write("\n".join(md)); print("\n".join(md))

def apply(inp, cube, out, strength=1.0):
    table, S = read_cube(cube); im = np.asarray(Image.open(inp).convert("RGB")).astype(np.float32) / 255
    res = trilinear(table, im, S); res = im + (res - im) * strength
    Image.fromarray((np.clip(res, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out, quality=95); print("->", out)

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "measure": measure(a[2], a[3])
    elif len(a) > 4 and a[1] == "build": build(a[2], a[3], a[4], float(opt("--strength", 1)), float(opt("--tone", 1)), float(opt("--color", 1)), int(opt("--size", 33)), opt("--preview"))
    elif len(a) > 4 and a[1] == "apply": apply(a[2], a[3], a[4], float(opt("--strength", 1)))
    else: print(USAGE)
