###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image

USAGE = """film-lab: physically motivated negative + print film emulation for photos and video, with .cube LUT export.

  python3 filmlab.py stocks                                   -> list negatives, prints, formats
  python3 filmlab.py photo IN.jpg OUT.jpg --neg vision3_250d --print 2383 [--format 35mm] [--input srgb|rec709|slog3|logc3|vlog|linear]
        [--exposure 0] [--push 0] [--printer-lights 0,0,0] [--halation 1] [--bloom 1] [--grain 1] [--grain-color 0.35] [--strength 1] [--seed 1]
  python3 filmlab.py contact IN.jpg OUT_sheet.jpg [--negs a,b,c] [--prints 2383,2393] [--input srgb]   -> comparison grid to choose a look
  python3 filmlab.py lut OUT.cube --neg ... --print ... [--input srgb] [--size 33] [--exposure 0] [--push 0] [--printer-lights r,g,b]
        -> colour part of the pipeline (no spatial texture) for Lightroom/Resolve/Premiere/CapCut/ffmpeg
  python3 filmlab.py video IN.mp4 OUT.mp4 --neg ... --print ... [--format 35mm] [--input rec709] [--scale 1] [--halation 1] [--grain 1] [--weave 0]

Pipeline (per pixel, in this order):
  decode to scene-linear -> exposure/push -> halation (red layer scatter, sized by film format) + bloom
  -> negative: log exposure through per-layer characteristic curves (toe, gamma, shoulder) with layer crosstalk
  -> grain in the density domain (finer in highlights of the print, coarser in shadows), sized by format and ISO
  -> print: printer lights, print characteristic curves (dense blacks, rolled highlights), print dye tint
  -> display encode (sRGB). Mid grey is auto-calibrated so 18% grey lands at a natural display level.
Stocks are parametric approximations of published characteristic behaviour, not measured profiles.
Needs: numpy, Pillow, opencv-python-headless, ffmpeg (video).
"""

NEGS = {
    "vision3_50d":   {"gamma": [0.60, 0.62, 0.64], "toe": 0.55, "shoulder": 2.2, "sat": 1.05, "bias": [0.0, 0.0, 0.0], "iso": 50, "halo": 1.0, "note": "fine grain daylight cine negative, clean and neutral"},
    "vision3_250d":  {"gamma": [0.58, 0.60, 0.63], "toe": 0.60, "shoulder": 2.0, "sat": 1.00, "bias": [0.01, 0.0, -0.01], "iso": 250, "halo": 1.0, "note": "the modern daylight cine look, soft highlight roll-off"},
    "vision3_500t":  {"gamma": [0.56, 0.58, 0.62], "toe": 0.70, "shoulder": 1.9, "sat": 0.95, "bias": [0.03, 0.01, -0.02], "iso": 500, "halo": 1.2, "note": "tungsten night negative, cool shadows, visible grain"},
    "eterna_500":    {"gamma": [0.52, 0.54, 0.55], "toe": 0.75, "shoulder": 2.1, "sat": 0.82, "bias": [0.0, 0.01, 0.01], "iso": 500, "halo": 1.0, "note": "low-contrast, desaturated, greenish Fuji cine look"},
    "cinestill_800t": {"gamma": [0.57, 0.58, 0.62], "toe": 0.70, "shoulder": 1.8, "sat": 1.0, "bias": [0.04, 0.0, -0.03], "iso": 800, "halo": 2.2, "note": "500T without remjet: strong red halation around lights"},
    "portra_400":    {"gamma": [0.55, 0.56, 0.57], "toe": 0.65, "shoulder": 2.4, "sat": 0.90, "bias": [0.02, 0.01, -0.01], "iso": 400, "halo": 0.8, "note": "warm, forgiving skin tones, huge latitude"},
    "ektar_100":     {"gamma": [0.68, 0.70, 0.72], "toe": 0.50, "shoulder": 1.8, "sat": 1.30, "bias": [0.01, 0.0, -0.01], "iso": 100, "halo": 0.7, "note": "punchy saturated colour, fine grain, landscapes and architecture"},
    "gold_200":      {"gamma": [0.62, 0.62, 0.60], "toe": 0.60, "shoulder": 1.9, "sat": 1.12, "bias": [0.04, 0.02, -0.03], "iso": 200, "halo": 0.9, "note": "warm nostalgic consumer film, yellow lean"},
    "fuji_400h":     {"gamma": [0.54, 0.57, 0.56], "toe": 0.70, "shoulder": 2.3, "sat": 0.88, "bias": [-0.01, 0.02, 0.01], "iso": 400, "halo": 0.8, "note": "pastel, airy, minty greens, cool shadows"},
    "hp5":           {"gamma": [0.60, 0.60, 0.60], "toe": 0.65, "shoulder": 2.0, "sat": 0.0, "bias": [0, 0, 0], "iso": 400, "halo": 0.8, "kind": "bw", "note": "classic black and white, medium contrast"},
    "trix_400":      {"gamma": [0.68, 0.68, 0.68], "toe": 0.55, "shoulder": 1.8, "sat": 0.0, "bias": [0, 0, 0], "iso": 400, "halo": 0.8, "kind": "bw", "note": "gritty high-contrast black and white"},
}
PRINTS = {
    "2383":  {"gamma": [2.9, 2.85, 2.75], "dmax": 3.9, "toe": 0.22, "tint": [1.0, 0.985, 0.95], "cross": 1.10, "note": "Kodak Vision print: dense blacks, warm highlights, cyan-leaning shadows, the classic cinema print"},
    "2393":  {"gamma": [3.0, 3.0, 2.95], "dmax": 4.1, "toe": 0.20, "tint": [1.0, 0.995, 0.98], "cross": 1.18, "note": "Kodak premier print: cleaner and richer, deeper purer blacks than 2383"},
    "3513":  {"gamma": [2.6, 2.65, 2.7], "dmax": 3.6, "toe": 0.26, "tint": [0.97, 0.99, 1.0], "cross": 1.0, "note": "Fuji print: softer contrast, cooler, gentler colour separation"},
    "endura": {"gamma": [2.3, 2.3, 2.25], "dmax": 2.6, "toe": 0.30, "tint": [1.0, 0.99, 0.97], "cross": 1.0, "note": "RA-4 photo paper print: softer, the look of a darkroom print"},
    "scan":  {"gamma": [2.4, 2.4, 2.4], "dmax": 2.7, "toe": 0.30, "tint": [1.0, 1.0, 1.0], "cross": 1.0, "note": "neutral lab scan of the negative (no print stock), flatter and modern"},
}
FORMATS = {"8mm": 0.030, "16mm": 0.018, "35mm": 0.009, "65mm": 0.0045, "120": 0.005, "4x5": 0.0025}
GRAIN_SCALE = {"8mm": 2.6, "16mm": 1.8, "35mm": 1.0, "65mm": 0.55, "120": 0.6, "4x5": 0.35}

def srgb_to_lin(v): return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
def lin_to_srgb(v): v = np.clip(v, 0, 1); return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)
def rec709_to_lin(v): return np.where(v < 0.081, v / 4.5, ((v + 0.099) / 1.099) ** (1 / 0.45))
def slog3_to_lin(v):
    x = v * 1023
    return np.where(x >= 171.2102946929, (10 ** ((x - 420) / 261.5)) * (0.18 + 0.01) - 0.01, (x - 95) * 0.01125 / (171.2102946929 - 95))
def logc3_to_lin(v):
    cut, a, b, c, d, e, f = 0.010591, 5.555556, 0.052272, 0.247190, 0.385537, 5.367655, 0.092809
    return np.where(v > e * cut + f, (10 ** ((v - d) / c) - b) / a, (v - f) / e)
def vlog_to_lin(v):
    b, c, d = 0.00873, 0.241514, 0.598206
    return np.where(v < 0.181, (v - 0.125) / 5.6, 10 ** ((v - d) / c) - b)
def expand(lin, k=0.75):
    e = lin / (1.0001 - k * np.clip(lin, 0, 1)); return e * (0.18 / (0.18 / (1.0001 - k * 0.18)))
DECODE = {"srgb": lambda v: expand(srgb_to_lin(v)), "rec709": lambda v: expand(rec709_to_lin(v)), "slog3": slog3_to_lin, "logc3": logc3_to_lin,
          "vlog": vlog_to_lin, "linear": lambda v: v, "srgb-flat": srgb_to_lin}

def gauss(img, sigma):
    if sigma < 0.5: return img
    k = int(sigma * 3) * 2 + 1; return cv2.GaussianBlur(img, (k, k), sigma)

def neg_density(logE, gamma, toe, shoulder):
    x = logE
    lin = gamma * toe * np.log1p(np.exp(x / toe))
    return shoulder * np.tanh(lin / shoulder)

def print_response(logE_print, slope, dmax, toe):
    u = slope * logE_print
    d = toe * np.log1p(np.exp(np.clip(u / toe, -60, 60)))
    d = dmax * np.tanh(d / dmax)
    return 10 ** (-d)

class Film:
    def __init__(s, neg="vision3_250d", prn="2383", exposure=0.0, push=0.0, lights=(0, 0, 0)):
        if neg not in NEGS: raise SystemExit(f"unknown negative {neg}; run: stocks")
        if prn not in PRINTS: raise SystemExit(f"unknown print {prn}; run: stocks")
        s.N, s.P = NEGS[neg], PRINTS[prn]; s.neg, s.prn = neg, prn
        s.exposure, s.push, s.lights = exposure, push, np.array(lights, np.float32) * 0.025
        s.bw = s.N.get("kind") == "bw"
        s.offset = 0.0; s.offset = s._calibrate()

    def negative(s, lin):
        lin = np.maximum(lin, 0) * 2 ** (s.exposure + s.push)
        if s.bw: lin = np.repeat((lin @ np.array([0.27, 0.62, 0.11], np.float32))[..., None], 3, -1)
        logE = np.log10(lin / 0.18 + 1e-4)
        g = np.array(s.N["gamma"], np.float32) * (1 + 0.12 * s.push)
        D = np.stack([neg_density(logE[..., c] + 2.0, g[c], s.N["toe"], s.N["shoulder"]) for c in range(3)], -1)
        D = D + np.array(s.N["bias"], np.float32)
        if not s.bw:
            m = D.mean(-1, keepdims=True); D = m + (D - m) * s.N["sat"] * 1.18
        return D

    def print_(s, D):
        logEp = -D + s.offset + s.lights
        if not s.bw:
            m = logEp.mean(-1, keepdims=True); logEp = m + (logEp - m) * s.P["cross"]
        T = np.stack([print_response(logEp[..., c], s.P["gamma"][c] * 0.65, s.P["dmax"], s.P["toe"]) for c in range(3)], -1)
        T = T * np.array(s.P["tint"], np.float32)
        Tmin, Tmax = 10 ** (-s.P["dmax"]), 1.0
        return np.clip((T - Tmin) / (Tmax - Tmin), 0, 1)

    def _calibrate(s):
        grey = np.full((1, 1, 3), 0.18, np.float32); lo, hi = -3.0, 3.0
        for _ in range(40):
            s.offset = (lo + hi) / 2; v = s.print_(s.negative(grey)).mean()
            lo, hi = (lo, s.offset) if v < 0.18 else (s.offset, hi)
        return s.offset

    def color(s, lin): return s.print_(s.negative(lin))

def halation_bloom(lin, width, fmt, halo_k, bloom_k, stock_halo):
    if halo_k <= 0 and bloom_k <= 0: return lin
    H, W = lin.shape[:2]; small = cv2.resize(lin, (max(8, W // 4), max(8, H // 4)), interpolation=cv2.INTER_AREA)
    lum = small @ np.array([0.27, 0.62, 0.11], np.float32)
    hi = np.clip(lum - 0.9, 0, None)[..., None] * np.ones(3, np.float32)
    out = lin.copy()
    if halo_k > 0:
        r = FORMATS.get(fmt, 0.009) * W / 4 * (1 + 0.6 * (stock_halo - 1))
        h = gauss(hi, max(1.0, r)) * np.array([1.0, 0.22, 0.04], np.float32) * 0.35 * halo_k * stock_halo
        out = out + cv2.resize(h, (W, H), interpolation=cv2.INTER_LINEAR)
    if bloom_k > 0:
        b = gauss(np.clip(small - 0.6, 0, None), max(1.0, W / 4 * 0.02)) * 0.12 * bloom_k
        out = out + cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
    return out

def grain_field(shape, fmt, iso, seed, color_amount):
    H, W = shape[:2]; rng = np.random.default_rng(seed)
    size = GRAIN_SCALE.get(fmt, 1.0) * (iso / 250) ** 0.5 * max(1.0, W / 2400)
    amp = 0.011 * (iso / 250) ** 0.5 * GRAIN_SCALE.get(fmt, 1.0) ** 0.6
    mono = gauss(rng.standard_normal((H, W)).astype(np.float32), max(0.5, size * 0.7))
    chroma = np.stack([gauss(rng.standard_normal((H, W)).astype(np.float32), max(0.5, size * 0.8)) for _ in range(3)], -1)
    nrm = lambda a: a / (a.std() + 1e-6)
    g = (1 - color_amount) * nrm(mono)[..., None] + color_amount * nrm(chroma)
    return g * amp

def apply(lin, film, fmt="35mm", halation=1.0, bloom=1.0, grain=1.0, grain_color=0.6, seed=1):
    lin = halation_bloom(lin, lin.shape[1], fmt, halation, bloom, film.N.get("halo", 1.0))
    D = film.negative(lin)
    if grain > 0:
        g = grain_field(D.shape, fmt, film.N["iso"], seed, 0.0 if film.bw else grain_color) * grain
        D = D + g * (0.6 + 0.8 * np.exp(-((D - 0.6) ** 2) / 0.3))
    return film.print_(D)

def load(path, enc):
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255
    return DECODE[enc](im).astype(np.float32)

def save(path, disp, src_path=None):
    out = (lin_to_srgb(disp) * 255 + 0.5).astype(np.uint8); Image.fromarray(out).save(path, quality=95)

def blend(a, b, k): return a if k >= 1 else a * k + b * (1 - k)

def cmd_photo(a):
    o = opts(a); film = Film(o["neg"], o["print"], o["exposure"], o["push"], o["lights"])
    lin = load(a[2], o["input"]); disp = apply(lin, film, o["format"], o["halation"], o["bloom"], o["grain"], o["grain_color"], o["seed"])
    if o["strength"] < 1: disp = blend(disp, np.clip(srgb_to_lin(np.asarray(Image.open(a[2]).convert("RGB")).astype(np.float32) / 255), 0, 1), o["strength"])
    save(a[3], disp); print(f"-> {a[3]}  {film.neg} + {film.prn}, {o['format']}")

def cmd_contact(a):
    o = opts(a); negs = (o.get("negs") or "vision3_250d,vision3_500t,portra_400,ektar_100").split(","); prints = (o.get("prints") or "2383,2393,scan").split(",")
    src = Image.open(a[2]).convert("RGB"); src.thumbnail((480, 480)); tmp = "/tmp/_fl_src.png"; src.save(tmp)
    lin = load(tmp, o["input"]); h, w = lin.shape[:2]; pad = 34
    sheet = Image.new("RGB", (len(prints) * w + 10, len(negs) * (h + pad) + 10), (16, 16, 16))
    from PIL import ImageDraw; d = ImageDraw.Draw(sheet)
    for i, n in enumerate(negs):
        for j, p in enumerate(prints):
            f = Film(n, p, o["exposure"], o["push"], o["lights"]); disp = apply(lin, f, o["format"], o["halation"], o["bloom"], o["grain"], o["grain_color"], o["seed"])
            sheet.paste(Image.fromarray((lin_to_srgb(disp) * 255).astype(np.uint8)), (5 + j * w, 5 + i * (h + pad)))
            d.text((8 + j * w, 8 + i * (h + pad) + h), f"{n} + {p}", fill=(235, 235, 235))
    sheet.save(a[3], quality=92); print(f"-> {a[3]}  ({len(negs)} negatives x {len(prints)} prints)")

def write_cube(path, size, fn, title):
    r = np.linspace(0, 1, size, dtype=np.float32); b, g, rr = np.meshgrid(r, r, r, indexing="ij")
    grid = np.stack([rr, g, b], -1).reshape(-1, 1, 3); out = fn(grid).reshape(-1, 3)
    with open(path, "w") as f:
        f.write(f'TITLE "{title}"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        f.writelines(f"{x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in out)

def cmd_lut(a):
    o = opts(a); film = Film(o["neg"], o["print"], o["exposure"], o["push"], o["lights"]); dec = DECODE[o["input"]]
    write_cube(a[2], o["size"], lambda g: lin_to_srgb(film.color(dec(g))), f"filmlab {film.neg} + {film.prn} ({o['input']} in, sRGB out)")
    print(f"-> {a[2]}  {o['size']}^3, input {o['input']}, output sRGB/Rec.709 display")

def cmd_video(a):
    o = opts(a); film = Film(o["neg"], o["print"], o["exposure"], o["push"], o["lights"]); src, out = a[2], a[3]
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", src], capture_output=True, text=True).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video"); n, d = map(int, v["avg_frame_rate"].split("/")); fps = n / d
    W, H = int(v["width"] * o["scale"]) // 2 * 2, int(v["height"] * o["scale"]) // 2 * 2
    dec = DECODE[o["input"]]; S = 65; r = np.linspace(0, 1, S, dtype=np.float32)
    bb, gg, rr = np.meshgrid(r, r, r, indexing="ij"); table = film.color(dec(np.stack([rr, gg, bb], -1))).astype(np.float32)
    dec_ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", src, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    tmp = out + ".v.mp4"
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    i = 0
    while True:
        buf = dec_ff.stdout.read(W * H * 3)
        if len(buf) < W * H * 3: break
        enc_in = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
        if o["halation"] > 0 or o["bloom"] > 0:
            lin = dec(enc_in); lin2 = halation_bloom(lin, W, o["format"], o["halation"], o["bloom"], film.N.get("halo", 1.0))
            enc_in = np.clip(enc_in + (lin2 - lin) * 0.9, 0, 1)
        disp = trilinear(table, enc_in, S)
        if o["grain"] > 0:
            g = grain_field(disp.shape, o["format"], film.N["iso"], o["seed"] + i, 0.0 if film.bw else o["grain_color"]) * o["grain"] * 0.6
            disp = np.clip(disp * (1 + g * 2.2), 0, 1)
        if o["weave"] > 0:
            dx, dy = np.random.default_rng(i).normal(0, 0.6 * o["weave"], 2); disp = cv2.warpAffine(disp, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        enc.stdin.write((lin_to_srgb(disp) * 255 + 0.5).astype(np.uint8).tobytes()); i += 1
        if i % int(fps) == 0: sys.stderr.write(f"{i} frames\n")
    enc.stdin.close(); enc.wait(); dec_ff.wait()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-i", src, "-map", "0:v", "-map", "1:a?", "-c", "copy", "-shortest", out]); os.remove(tmp)
    print(f"-> {out}  {i} frames, {film.neg} + {film.prn}, {o['format']}")

def trilinear(table, x, S):
    p = np.clip(x, 0, 1) * (S - 1); i0 = np.floor(p).astype(np.int32); i0 = np.minimum(i0, S - 2); f = p - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]; fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    c = lambda db, dg, dr: table[b0 + db, g0 + dg, r0 + dr]
    c00 = c(0, 0, 0) * (1 - fr) + c(0, 0, 1) * fr; c01 = c(0, 1, 0) * (1 - fr) + c(0, 1, 1) * fr
    c10 = c(1, 0, 0) * (1 - fr) + c(1, 0, 1) * fr; c11 = c(1, 1, 0) * (1 - fr) + c(1, 1, 1) * fr
    return (c00 * (1 - fg) + c01 * fg) * (1 - fb) + (c10 * (1 - fg) + c11 * fg) * fb

def opts(a):
    g = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    return {"neg": g("--neg", "vision3_250d"), "print": g("--print", "2383"), "format": g("--format", "35mm"), "input": g("--input", "srgb"),
            "exposure": float(g("--exposure", 0)), "push": float(g("--push", 0)), "lights": [float(x) for x in g("--printer-lights", "0,0,0").split(",")],
            "halation": float(g("--halation", 1)), "bloom": float(g("--bloom", 1)), "grain": float(g("--grain", 1)), "grain_color": float(g("--grain-color", 0.35)),
            "strength": float(g("--strength", 1)), "seed": int(g("--seed", 1)), "size": int(g("--size", 33)), "scale": float(g("--scale", 1)),
            "weave": float(g("--weave", 0)), "negs": g("--negs"), "prints": g("--prints")}

if __name__ == "__main__":
    a = sys.argv
    if len(a) > 1 and a[1] == "stocks":
        print("NEGATIVES"); [print(f"  {k:15s} ISO {v['iso']:4d}  {v['note']}") for k, v in NEGS.items()]
        print("PRINTS"); [print(f"  {k:15s} {v['note']}") for k, v in PRINTS.items()]
        print("FORMATS  " + ", ".join(FORMATS)); print("INPUTS   " + ", ".join(DECODE))
    elif len(a) > 3 and a[1] == "photo": cmd_photo(a)
    elif len(a) > 3 and a[1] == "contact": cmd_contact(a)
    elif len(a) > 2 and a[1] == "lut": cmd_lut(a)
    elif len(a) > 3 and a[1] == "video": cmd_video(a)
    else: print(USAGE)
