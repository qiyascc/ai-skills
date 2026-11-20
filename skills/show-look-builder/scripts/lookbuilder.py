###############
# Qiyas Sadıqov CC
###############
import json, os, sys, datetime
import numpy as np
from PIL import Image, ImageDraw

USAGE = """show-look-builder: one signature look across every camera of a project or brand (Yedlin-style display prep):
normalise each camera to a common baseline, then apply one look transform to all of them.

  python3 lookbuilder.py profile CAM_NAME SAMPLES(dir|files..) OUT_DIR [--input srgb|rec709|slog3|logc3|vlog] [--grey x,y,w,h] [--match-to OTHER_CAM.json] [--keep-warmth 0.3]
      -> OUT_DIR/CAM_NAME.json (white balance gains, exposure, saturation) + CAM_NAME_normalize.cube (camera encoding in, neutral sRGB out)
  python3 lookbuilder.py build LOOK_NAME OUT_DIR --cams a.json,b.json --look look.cube [--look-strength 1.0] [--size 33]
      -> per camera: LOOK_NAME_<cam>.cube = normalise then look (one file to drop on that camera's footage)
  python3 lookbuilder.py check OUT_DIR --pairs camA.json:imgA.jpg,camB.json:imgB.jpg [--look LOOK_NAME]
      -> consistency before/after (exposure, white balance, saturation spread) + side-by-side sheet
  python3 lookbuilder.py bible LOOK_NAME OUT_DIR [--brand "Khalif Estate"] [--notes "..."]
      -> LOOK_NAME_bible.md: what the look is, files per camera, how to install in Lightroom/Resolve/Premiere/CapCut, shooting rules
The look itself comes from film-lab (filmlab.py lut ...) or reference-matcher (refmatch.py build ...).
Needs: numpy, Pillow, opencv-python-headless.
"""

def srgb_to_lin(v): return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
def lin_to_srgb(v): v = np.clip(v, 0, 1); return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)
def rec709_to_lin(v): return np.where(v < 0.081, v / 4.5, ((v + 0.099) / 1.099) ** (1 / 0.45))
def slog3_to_lin(v):
    x = v * 1023; return np.where(x >= 171.2102946929, (10 ** ((x - 420) / 261.5)) * 0.19 - 0.01, (x - 95) * 0.01125 / (171.2102946929 - 95))
def logc3_to_lin(v):
    cut, a, b, c, d, e, f = 0.010591, 5.555556, 0.052272, 0.247190, 0.385537, 5.367655, 0.092809
    return np.where(v > e * cut + f, (10 ** ((v - d) / c) - b) / a, (v - f) / e)
def vlog_to_lin(v): return np.where(v < 0.181, (v - 0.125) / 5.6, 10 ** ((v - 0.598206) / 0.241514) - 0.00873)
DEC = {"srgb": srgb_to_lin, "rec709": rec709_to_lin, "slog3": slog3_to_lin, "logc3": logc3_to_lin, "vlog": vlog_to_lin}
LOG = {"slog3", "logc3", "vlog"}
def to_display(lin, is_log):
    if not is_log: return lin_to_srgb(lin)
    x = np.maximum(lin, 0); return lin_to_srgb(x * (1 + x / 16) / (1 + x) * 1.25)

def load_many(src, maxs=800):
    files = [os.path.join(src, f) for f in sorted(os.listdir(src))] if isinstance(src, str) and os.path.isdir(src) else (src if isinstance(src, list) else [src])
    ims = []
    for f in files:
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")):
            im = Image.open(f).convert("RGB"); im.thumbnail((maxs, maxs)); ims.append(np.asarray(im).astype(np.float32) / 255)
    if not ims: raise SystemExit("no images found (export a few frames as JPG/PNG for video cameras)")
    return ims

def profile(cam, samples, out, enc="srgb", grey=None, match_to=None, keep=0.3):
    os.makedirs(out, exist_ok=True); ims = load_many(samples); dec = DEC[enc]
    lins = [dec(i) for i in ims]
    if grey:
        x, y, w, h = grey; patch = lins[0][y:y + h, x:x + w].reshape(-1, 3); ref = np.median(patch, 0); method = "grey card"
    else:
        px = np.concatenate([l.reshape(-1, 3) for l in lins]); lum = px @ np.array([0.2126, 0.7152, 0.0722])
        m = (lum > np.percentile(lum, 20)) & (lum < np.percentile(lum, 95)); px = px[m]
        chroma = (px.max(1) - px.min(1)) / (px.max(1) + 1e-6); px = px[chroma < np.percentile(chroma, 35)]
        ref = np.median(px, 0); method = "neutral-pixel estimate"
    gains = (ref.mean() / np.maximum(ref, 1e-6)); gains = gains / gains[1]
    if not grey: gains = gains ** (1 - keep)
    other = json.load(open(match_to)) if match_to else None
    if other and not grey and other.get("neutral"):
        gains = np.array(other["neutral"]) / np.maximum(ref, 1e-6); gains = gains / gains[1]; method = f"neutral-pixel estimate, white balance matched to {other['camera']}"
    neutral = ref * gains; neutral = neutral / neutral[1]
    allpx = np.concatenate([(l * gains).reshape(-1, 3) for l in lins]); lum = allpx @ np.array([0.2126, 0.7152, 0.0722])
    expo = float(0.18 / max(np.median(lum), 1e-4)) if not grey else float(0.18 / max((ref * gains).mean(), 1e-4))
    disp = to_display(allpx * expo, enc in LOG); sat = float((disp.max(1) - disp.min(1)).mean())
    sat_gain = 1.0
    if other: sat_gain = float(np.clip(other["saturation"] / max(sat, 1e-4), 0.7, 1.4))
    P = {"camera": cam, "input": enc, "method": method + ("" if grey or "matched" in method else f", keeps {keep:.0%} of scene warmth"), "wb_gains": [round(float(g), 4) for g in gains], "neutral": [round(float(n), 4) for n in neutral], "exposure_gain": round(expo, 4),
         "exposure_stops": round(float(np.log2(expo)), 2), "saturation": round(sat, 4), "saturation_gain": round(sat_gain, 3), "created": datetime.date.today().isoformat()}
    json.dump(P, open(os.path.join(out, f"{cam}.json"), "w"), indent=1)
    write_cube(os.path.join(out, f"{cam}_normalize.cube"), 33, lambda g: normalize(g, P), f"{cam} normalize ({enc} in, sRGB out)")
    print(json.dumps(P, indent=1)); print(f"-> {out}/{cam}.json, {cam}_normalize.cube")

def normalize(rgb, P):
    lin = DEC[P["input"]](rgb) * np.array(P["wb_gains"], np.float32) * P["exposure_gain"]
    d = to_display(lin, P["input"] in LOG)
    if P.get("saturation_gain", 1) != 1:
        m = d @ np.array([0.2126, 0.7152, 0.0722], np.float32); d = np.clip(m[..., None] + (d - m[..., None]) * P["saturation_gain"], 0, 1)
    return d

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

def build(name, out, cams, look, strength=1.0, size=33):
    os.makedirs(out, exist_ok=True); T, S = read_cube(look)
    for cp in cams:
        P = json.load(open(cp))
        def fn(g, P=P):
            n = normalize(g, P); l = trilinear(T, n, S); return n + (l - n) * strength
        path = os.path.join(out, f"{name}_{P['camera']}.cube"); write_cube(path, size, fn, f"{name} for {P['camera']} ({P['input']} in, sRGB out)"); print("->", path)

def metrics(img):
    lin = srgb_to_lin(img); lum = lin @ np.array([0.2126, 0.7152, 0.0722]); m = (lum > 0.05) & (lum < 0.8)
    rgb = lin[m]; return float(np.median(lum)), float(np.log(np.median(rgb[:, 0]) / np.median(rgb[:, 2]))), float((img.max(-1) - img.min(-1)).mean())

def check(out, pairs, look=None):
    rows = []; tiles = []
    for pr in pairs:
        cj, ip = pr.split(":"); P = json.load(open(cj)); im = load_many([ip])[0]
        n = normalize(im, P); final = n
        if look:
            lp = os.path.join(out, f"{look}_{P['camera']}.cube")
            if os.path.exists(lp): T, S = read_cube(lp); final = np.clip(trilinear(T, im, S), 0, 1)
        rows.append((P["camera"], metrics(im if P["input"] not in LOG else to_display(DEC[P["input"]](im), True)), metrics(n))); tiles.append((P["camera"], im, final))
    md = ["| camera | exposure before | after | warm/cool before | after | saturation before | after |", "|---|---|---|---|---|---|---|"]
    for cam, b, a in rows: md.append(f"| {cam} | {b[0]:.3f} | {a[0]:.3f} | {b[1]:+.3f} | {a[1]:+.3f} | {b[2]:.3f} | {a[2]:.3f} |")
    spread = lambda k, i: float(np.std([r[k][i] for r in rows]))
    md += ["", f"spread before: exposure {spread(1, 0):.3f}, balance {spread(1, 1):.3f}, saturation {spread(1, 2):.3f}",
           f"spread after:  exposure {spread(2, 0):.3f}, balance {spread(2, 1):.3f}, saturation {spread(2, 2):.3f}  (lower = more consistent)"]
    th = 300; sheet = Image.new("RGB", (2 * 420 + 30, len(tiles) * (th + 30) + 10), (16, 16, 16)); d = ImageDraw.Draw(sheet)
    for i, (cam, a, b) in enumerate(tiles):
        for j, im in enumerate((a, b)):
            t = Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8)); t.thumbnail((420, th)); sheet.paste(t, (10 + j * 430, 10 + i * (th + 30)))
        d.text((12, 10 + i * (th + 30) + th + 4), f"{cam}: original | {'look' if look else 'normalised'}", fill=(230, 230, 230))
    sheet.save(os.path.join(out, "consistency_sheet.jpg"), quality=90); open(os.path.join(out, "consistency.md"), "w").write("\n".join(md)); print("\n".join(md))

def bible(name, out, brand="", notes=""):
    cams = [f for f in sorted(os.listdir(out)) if f.startswith(name + "_") and f.endswith(".cube")]
    md = [f"# {name}: look bible" + (f" for {brand}" if brand else ""), "", f"Created {datetime.date.today()}.", notes, "",
          "## Files", *[f"- `{c}`: apply to footage/photos from camera **{c[len(name) + 1:-5]}** (one LUT does normalisation + look)" for c in cams], "",
          "## Install", "- Lightroom / Camera Raw: Profiles > Import Profiles needs .xmp; use Photoshop Color Lookup or a LUT-to-profile converter, or apply in Resolve/Photoshop.",
          "- DaVinci Resolve: Project Settings > Color Management > Lookup Tables > Open LUT folder, copy the .cube, refresh, apply on a node (last node before output).",
          "- Premiere Pro: Lumetri Color > Creative > Look > Browse, or Basic Correction > Input LUT for the camera LUT.",
          "- Final Cut Pro: Custom LUT effect. CapCut desktop: Adjustment > LUT > Import.",
          "- ffmpeg: `ffmpeg -i in.mp4 -vf lut3d=FILE.cube -c:a copy out.mp4`", "",
          "## Shooting rules that keep the look consistent",
          "- Lock white balance per scene (no auto WB), expose the main subject consistently (grey card or skin at the same level).",
          "- Phones: turn off HDR/auto-tone effects when possible; same resolution and frame rate across devices.",
          "- Log cameras: use the matching camera LUT from this folder; never stack a manufacturer LUT before it.",
          "- Re-profile a camera when firmware, picture profile or lens changes noticeably.", "",
          "## Quality gate", "- Run grade-critic on 5 frames per camera after applying; exposure and white-balance spread must stay low."]
    p = os.path.join(out, f"{name}_bible.md"); open(p, "w").write("\n".join(md)); print("->", p)

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    flags = {"--input", "--grey", "--match-to", "--keep-warmth"}
    if len(a) > 4 and a[1] == "profile":
        pos = [x for i, x in enumerate(a[2:], 2) if x not in flags and a[i - 1] not in flags]
        profile(pos[0], pos[1:-1] if len(pos) > 3 else pos[1], pos[-1], opt("--input", "srgb"), [int(v) for v in opt("--grey").split(",")] if opt("--grey") else None, opt("--match-to"), float(opt("--keep-warmth", 0.3)))
    elif len(a) > 3 and a[1] == "build": build(a[2], a[3], opt("--cams").split(","), opt("--look"), float(opt("--look-strength", 1)), int(opt("--size", 33)))
    elif len(a) > 2 and a[1] == "check": check(a[2], opt("--pairs").split(","), opt("--look"))
    elif len(a) > 3 and a[1] == "bible": bible(a[2], a[3], opt("--brand", ""), opt("--notes", ""))
    else: print(USAGE)
