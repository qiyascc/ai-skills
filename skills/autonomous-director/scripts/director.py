###############
# Qiyas Sadıqov CC
###############
import json, os, re, shutil, subprocess, sys, datetime
import numpy as np
from PIL import Image

USAGE = """autonomous-director: a pass/fail quality gate for any rendered video, built for render -> check -> fix loops.

  python3 director.py init OUT_spec.json [--w 1080 --h 1920 --fps 30 --dur 15]   -> a check spec to edit
  python3 director.py check SPEC.json VIDEO.mp4 [--iter N] [--log loop_log.md]
      -> prints PASS/FAIL per check with a concrete fix, writes VIDEO.check.json, appends to the loop log,
         exit code 0 when everything required passes, 1 otherwise (so a loop can stop by itself).
Checks (only those present in the spec run): resolution, fps, duration; black frames; frozen stretches;
silence gaps; loudness (LUFS) and true peak; checkpoint frames vs reference stills (structure + colour);
expected on-screen text at times (OCR); text inside platform UI zones; seamless loop (first vs last frame);
file size limit.
Needs: ffmpeg/ffprobe, numpy, Pillow; tesseract for text checks.
"""

def run(c): return subprocess.run(c, capture_output=True, text=True)
ZONES = {"reels": (0.13, 0.22, 0.11), "tiktok": (0.12, 0.25, 0.14), "shorts": (0.10, 0.20, 0.12)}
SPEC = {"width": 1080, "height": 1920, "fps": 30, "duration": 15.0, "duration_tol": 0.1,
        "lufs": -13, "lufs_tol": 1.5, "true_peak_max": -1.0, "max_silence_s": 0.6,
        "no_black_frames": True, "max_frozen_s": 1.0, "loop": False, "max_size_mb": 100,
        "checkpoints": [{"t": 1.8, "ref": "ref_1.80.png", "min_structure": 0.6, "min_colour": 0.9}],
        "expect_text": [{"t": 13.0, "contains": "motion out"}], "safe_platform": "reels"}

def frame(v, t, out, w=None):
    run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{max(0, t):.3f}", "-i", v, "-frames:v", "1"] + (["-vf", f"scale={w}:-2"] if w else []) + [out]); return out

def last_frame(v, out, w=None):
    run(["ffmpeg", "-loglevel", "error", "-y", "-sseof", "-1", "-i", v] + (["-vf", f"scale={w}:-2"] if w else []) + ["-update", "1", out]); return out

def sim(a, b):
    if not (os.path.exists(a) and os.path.exists(b)): return 0.0, 0.0
    A = np.asarray(Image.open(a).convert("RGB").resize((180, 320))).astype(np.float32); B = np.asarray(Image.open(b).convert("RGB").resize((180, 320))).astype(np.float32)
    ga, gb = A.mean(2), B.mean(2); ga = (ga - ga.mean()) / (ga.std() + 1e-6); gb = (gb - gb.mean()) / (gb.std() + 1e-6)
    return float((ga * gb).mean()), colour_match(A, B)

def colour_match(A, B):
    key = lambda p: (p[:, 0] // 32) * 64 + (p[:, 1] // 32) * 8 + p[:, 2] // 32
    pa = A.reshape(-1, 3); ka = key(pa).astype(int); bg = pa[ka == np.bincount(ka, minlength=512).argmax()].mean(0)
    hists, shares = [], []
    for X in (A, B):
        p = X.reshape(-1, 3); m = np.sqrt(((p - bg) ** 2).sum(1)) > 24; shares.append(m.mean())
        h = np.bincount(key(p[m]).astype(int), minlength=512).astype(np.float64); hists.append(h / max(h.sum(), 1))
    if max(shares) < 0.003: return float(1 - np.abs(A.mean((0, 1)) - B.mean((0, 1))).mean() / 255)
    if min(shares) < 0.003: return 0.0
    return float(np.minimum(*hists).sum())

def check(spec_path, v, it=None, log=None):
    S = json.load(open(spec_path)); base = os.path.dirname(os.path.abspath(spec_path)); res = []
    add = lambda name, ok, got, fix, req=True: res.append({"check": name, "pass": bool(ok), "got": got, "fix": "" if ok else fix, "required": req})
    pr = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", v]).stdout)
    vs = next(s for s in pr["streams"] if s["codec_type"] == "video"); n, d = map(int, vs["avg_frame_rate"].split("/")); fps = n / d if d else 0
    dur = float(pr["format"]["duration"]); size_mb = float(pr["format"]["size"]) / 1e6; has_a = any(s["codec_type"] == "audio" for s in pr["streams"])
    if "width" in S: add("resolution", (vs["width"], vs["height"]) == (S["width"], S["height"]), f"{vs['width']}x{vs['height']}", f"render at {S['width']}x{S['height']}")
    if "fps" in S: add("fps", abs(fps - S["fps"]) < 0.05, round(fps, 3), f"render at {S['fps']} fps (no resampling after render)")
    if "duration" in S: add("duration", abs(dur - S["duration"]) <= S.get("duration_tol", 0.1), round(dur, 3), f"length must be {S['duration']} s; check the last scene end / -shortest on audio")
    if "max_size_mb" in S: add("file size", size_mb <= S["max_size_mb"], round(size_mb, 1), "raise CRF by 2 or use -preset slow", req=False)
    if S.get("no_black_frames"):
        out = run(["ffmpeg", "-hide_banner", "-i", v, "-vf", "blackdetect=d=0.05:pix_th=0.06", "-an", "-f", "null", "-"]).stderr
        bl = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", out); add("black frames", not bl, bl[:5], "a scene renders empty at these times: check scene ranges/overlaps and asset loading")
    if "max_frozen_s" in S:
        out = run(["ffmpeg", "-hide_banner", "-i", v, "-vf", f"freezedetect=n=0.002:d={S['max_frozen_s']}", "-an", "-f", "null", "-"]).stderr
        fz = re.findall(r"freeze_start: ([\d.]+)", out); add("frozen stretches", not fz, fz[:5], f"nothing moves for >{S['max_frozen_s']} s here: add camera drift/breathing (no frozen frames)", req=False)
    if has_a and ("lufs" in S or "true_peak_max" in S):
        out = run(["ffmpeg", "-hide_banner", "-i", v, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
        I = re.findall(r"I:\s+(-?[\d.]+) LUFS", out); TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out); I = float(I[-1]) if I else None; TP = float(TP[-1]) if TP else None
        if "lufs" in S: add("loudness", I is not None and abs(I - S["lufs"]) <= S.get("lufs_tol", 1.5), I, f"master to {S['lufs']} LUFS (loudnorm), then limit")
        if "true_peak_max" in S: add("true peak", TP is not None and TP <= S["true_peak_max"], TP, f"limit true peak to {S['true_peak_max']} dBTP")
    elif "lufs" in S: add("audio present", False, None, "the video has no audio track; mux the mix")
    if has_a and "max_silence_s" in S:
        out = run(["ffmpeg", "-hide_banner", "-i", v, "-af", f"silencedetect=n=-50dB:d={S['max_silence_s']}", "-f", "null", "-"]).stderr
        si = re.findall(r"silence_start: ([\d.]+)", out); add("silence", not si, si[:5], "fill silence with music/ambience or extend the music", req=False)
    tmpd = v + "_frames"; os.makedirs(tmpd, exist_ok=True)
    for cp in S.get("checkpoints", []):
        ref = os.path.join(base, cp["ref"])
        if not os.path.exists(ref): add(f"checkpoint {cp['t']}s", False, "missing ref", f"reference still not found: {ref}", req=False); continue
        mine = frame(v, cp["t"], os.path.join(tmpd, f"c_{cp['t']:.2f}.png"), 360); s_, c_ = sim(ref, mine)
        near = {dt: sim(ref, frame(v, cp["t"] + dt, os.path.join(tmpd, f"c_{cp['t'] + dt:.2f}.png"), 360))[0] for dt in (-0.2, -0.1, 0.1, 0.2)}
        best = max(near, key=near.get); hint = f"; event is {'early' if best < 0 else 'late'} by ~{abs(best):.1f} s" if near[best] > s_ + 0.08 else ""
        add(f"checkpoint {cp['t']}s", s_ >= cp.get("min_structure", .6) and c_ >= cp.get("min_colour", .9), {"structure": round(s_, 2), "colour": round(c_, 2)},
            f"frame differs from reference (compare {mine} with {ref}){hint}")
    if S.get("expect_text") or S.get("safe_platform"):
        if not shutil.which("tesseract"): add("text checks", False, "no tesseract", "install tesseract to run text checks", req=False)
        else:
            for et in S.get("expect_text", []):
                fp = frame(v, et["t"], os.path.join(tmpd, f"t_{et['t']:.2f}.png")); txt = run(["tesseract", fp, "-", "--psm", "11"]).stdout.lower()
                add(f"text at {et['t']}s", et["contains"].lower() in " ".join(txt.split()), " ".join(txt.split())[:60], f"'{et['contains']}' must be readable at {et['t']} s (contrast, size, timing)")
            if S.get("safe_platform"):
                top, bot, right = ZONES[S["safe_platform"]]; hits = []
                for t in np.arange(0.5, dur, 1.0):
                    fp = frame(v, t, os.path.join(tmpd, "z.png")); tsv = run(["tesseract", fp, "-", "--psm", "11", "tsv"]).stdout.splitlines()[1:]
                    for l in tsv:
                        c = l.split("\t")
                        if len(c) == 12 and c[11].strip() and len(c[11].strip()) > 1 and float(c[10]) > 60:
                            x, y, w, h = map(int, c[6:10])
                            if y < top * vs["height"] or y + h > (1 - bot) * vs["height"] or x + w > (1 - right) * vs["width"]: hits.append(round(float(t), 1))
                add("UI safe zones", not hits, sorted(set(hits))[:8], f"move text out of {S['safe_platform']} UI zones at these times", req=False)
    if S.get("loop"):
        a = frame(v, 0, os.path.join(tmpd, "first.png"), 360); b = last_frame(v, os.path.join(tmpd, "last.png"), 360)
        if os.path.exists(a) and os.path.exists(b):
            ga, gb = (np.asarray(Image.open(x).convert("L").resize((180, 320))).astype(np.float32) for x in (a, b)); ch = float((np.abs(ga - gb) > 16).mean() * 100)
        else: ch = 100.0
        add("seamless loop", ch < 0.5, {"changed_pct": round(ch, 2)}, "last frame must match frame 0 (same layout, colour, camera); under 0.5% of pixels may differ")
    req_fail = [r for r in res if r["required"] and not r["pass"]]; status = "PASS" if not req_fail else "FAIL"
    json.dump({"video": v, "status": status, "checks": res}, open(v + ".check.json", "w"), indent=1)
    lines = [f"{'PASS' if r['pass'] else ('FAIL' if r['required'] else 'WARN')}  {r['check']}: {r['got']}" + (f"  -> {r['fix']}" if r["fix"] else "") for r in res]
    print("\n".join(lines) + f"\n\nSTATUS: {status} ({len(req_fail)} required failing)")
    if log:
        with open(log, "a") as f:
            f.write(f"\n## Iteration {it if it is not None else '?'} ({datetime.datetime.now():%H:%M}) {status}\n" + "\n".join("- " + l for l in lines if not l.startswith("PASS")) + "\n")
    sys.exit(0 if status == "PASS" else 1)

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 2 and a[1] == "init":
        s = dict(SPEC); s.update({k: t(opt("--" + f)) for k, f, t in [("width", "w", int), ("height", "h", int), ("fps", "fps", float), ("duration", "dur", float)] if opt("--" + f)})
        json.dump(s, open(a[2], "w"), indent=1); print("->", a[2])
    elif len(a) > 3 and a[1] == "check": check(a[2], a[3], opt("--iter"), opt("--log"))
    else: print(USAGE)
