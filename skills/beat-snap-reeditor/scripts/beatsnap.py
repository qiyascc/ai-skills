###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys
import numpy as np

USAGE = """beat-snap-reeditor: re-time an existing edit so every cut lands on the music grid.

  python3 beatsnap.py plan EDIT.mp4 MUSIC.(wav|mp3) OUT_DIR [--bpm 128] [--offset 0.0] [--music-start 0] [--max-speed 0.08] [--phrase-every 8]
      -> OUT_DIR/plan.json + plan.md: detected cuts, beat grid, the target for every cut
         (beat, eighth, or phrase start for the biggest visual changes) and how each segment gets there.
  python3 beatsnap.py render EDIT.mp4 MUSIC OUT_DIR/plan.json OUT.mp4
      -> segments retimed (speed change within +-max-speed, else trim or hold the last frame), concatenated, music laid under.
Rules: cuts move to the nearest eighth note; the strongest visual changes (top 25% by cut strength)
prefer the nearest 8-beat phrase start within 0.6 s; no segment shorter than 0.25 s; order never changes.
Needs: ffmpeg/ffprobe, numpy.
"""

def run(c): return subprocess.run(c, capture_output=True, text=True)

def probe(p):
    r = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", p]).stdout)
    v = next((s for s in r["streams"] if s["codec_type"] == "video"), None)
    fps = (lambda n, d: n / d if d else 30)(*map(int, v["avg_frame_rate"].split("/"))) if v else None
    return float(r["format"]["duration"]), fps

def cuts_of(p):
    r = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-print_format", "json", "-show_streams", p]).stdout)["streams"][0]
    fs = min(60, round((lambda n, d: n / d if d else 30)(*map(int, r["avg_frame_rate"].split("/")))))
    h = int(round(r["height"] * 96 / r["width"] / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-vf", f"fps={fs},scale=96:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    g = np.frombuffer(raw, np.uint8).reshape(-1, h * 96).astype(np.float32)
    hist = [np.histogram(f, 32, (0, 255))[0] / f.size for f in g]
    hd = np.array([np.abs(hist[i + 1] - hist[i]).sum() for i in range(len(hist) - 1)])
    thr = max(0.35, float(np.median(hd) + 8 * np.median(np.abs(hd - np.median(hd))))) if len(hd) else 1
    idx = [i for i in np.where(hd > thr)[0]]
    merged = []
    for i in idx:
        if merged and i - merged[-1][0] <= 2:
            if hd[i] > merged[-1][1]: merged[-1] = (i, hd[i])
        else: merged.append((i, hd[i]))
    return [((i + 1) / fs, float(s)) for i, s in merged]

def bpm_of(p, start=0.0, dur=None):
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", str(start), "-i", p] + (["-t", str(dur)] if dur else []) + ["-ac", "1", "-ar", "11025", "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32); hop = 128; fr = 11025 / hop
    e = np.array([np.sum(x[i:i + hop] ** 2) for i in range(0, len(x) - hop, hop)])
    on = np.maximum(0, np.diff(np.log1p(e * 1e3))); on -= on.mean()
    ac = np.correlate(on, on, "full")[len(on) - 1:]; lags = np.arange(len(ac)) / fr
    best = max(np.arange(70, 181, 0.5), key=lambda b: sum(np.interp(60 / b * m, lags, ac) for m in (1, 2, 4)))
    period = 60 / best * fr
    ph = max(np.arange(0, period, 0.5), key=lambda q: on[np.clip((q + np.arange(0, len(on) - q, period)).astype(int), 0, len(on) - 1)].sum())
    return float(best), (ph + 1) / fr

def plan(edit, music, out, bpm=None, offset=None, mstart=0.0, maxs=0.08, phrase=8):
    os.makedirs(out, exist_ok=True); dur, fps = probe(edit); cuts = cuts_of(edit)
    if bpm is None or offset is None:
        b, ph = bpm_of(music, mstart, dur + 5); bpm = bpm or b; offset = ph if offset is None else offset
    beat = 60 / bpm; eighth = beat / 2
    grid = lambda t: offset + round((t - offset) / eighth) * eighth
    strong = set(sorted(range(len(cuts)), key=lambda i: -cuts[i][1])[:max(1, len(cuts) // 4)]) if cuts else set()
    targets = []
    for i, (t, s) in enumerate(cuts):
        tgt, kind = grid(t), "eighth"
        if abs((tgt - offset) / beat - round((tgt - offset) / beat)) < 1e-6: kind = "beat"
        if i in strong:
            ph_t = offset + round((t - offset) / (beat * phrase)) * beat * phrase
            if abs(ph_t - t) <= 0.6 and ph_t > 0: tgt, kind = ph_t, "PHRASE"
        prev = targets[-1]["target"] if targets else 0.0
        while tgt - prev < 0.25: tgt += eighth; kind = "eighth (pushed)"
        targets.append({"cut": round(t, 3), "strength": round(s, 2), "target": round(tgt, 3), "kind": kind, "shift": round(tgt - t, 3)})
    end_t = offset + round((dur - offset) / beat) * beat
    if end_t <= (targets[-1]["target"] if targets else 0) + 0.25: end_t = dur
    src = [0.0] + [c["cut"] for c in targets] + [dur]; dst = [0.0] + [c["target"] for c in targets] + [round(end_t, 3)]
    segs = []
    for k in range(len(src) - 1):
        L, T = src[k + 1] - src[k], dst[k + 1] - dst[k]; sp = L / T if T > 0 else 1
        if abs(sp - 1) <= maxs: how = f"speed x{sp:.3f}"
        elif T < L: how = "trim tail"; sp = 1
        else: how = "hold last frame"; sp = 1
        segs.append({"i": k, "src_in": round(src[k], 3), "src_out": round(src[k + 1], 3), "dst_len": round(T, 3), "speed": round(sp, 4), "how": how})
    p = {"edit": edit, "music": music, "music_start": mstart, "bpm": bpm, "offset": round(offset, 3), "fps": fps, "cuts": targets, "segments": segs, "new_duration": dst[-1]}
    json.dump(p, open(os.path.join(out, "plan.json"), "w"), indent=1)
    md = [f"BPM {bpm} (beat {beat:.3f} s, first beat {offset:.3f} s); {len(cuts)} cuts; new length {dst[-1]:.2f} s", "",
          "| cut | strength | target | grid | shift |", "|---|---|---|---|---|"] + [f"| {c['cut']} | {c['strength']} | {c['target']} | {c['kind']} | {c['shift']:+.3f} |" for c in targets] + \
         ["", "| seg | source | new length | method |", "|---|---|---|---|"] + [f"| {s['i']} | {s['src_in']}-{s['src_out']} | {s['dst_len']} | {s['how']} |" for s in segs]
    open(os.path.join(out, "plan.md"), "w").write("\n".join(md)); print("\n".join(md))

def render(edit, music, plan_path, out):
    p = json.load(open(plan_path)); fps = p["fps"] or 30; parts = []; at = 0.0
    for s in p["segments"]:
        L = s["src_out"] - s["src_in"]; T = s["dst_len"]
        nf = int(round((at + T) * fps)) - int(round(at * fps)); at += T
        f = f"[0:v]trim={s['src_in']}:{s['src_out']},setpts=PTS-STARTPTS"
        if s["how"].startswith("speed"): f += f",setpts=PTS/{s['speed']}"
        elif s["how"] == "trim tail": f += f",trim=0:{T}"
        else: f += f",tpad=stop_mode=clone:stop_duration={max(0, T - L):.3f}"
        f += f",fps={fps},tpad=stop_mode=clone:stop=2,trim=end_frame={nf},setpts=PTS-STARTPTS[s{s['i']}]"; parts.append(f)
    n = len(p["segments"]); fc = ";".join(parts) + ";" + "".join(f"[s{i}]" for i in range(n)) + f"concat=n={n}:v=1[v]"
    r = run(["ffmpeg", "-loglevel", "error", "-y", "-i", edit, "-ss", str(p["music_start"]), "-i", music, "-filter_complex", fc,
             "-map", "[v]", "-map", "1:a", "-t", str(p["new_duration"]), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", out])
    if r.returncode: print(r.stderr[-2000:]); sys.exit(1)
    print(f"-> {out} ({p['new_duration']:.2f} s, {n} segments on a {p['bpm']} BPM grid)")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None, t=float: t(a[a.index(k) + 1]) if k in a else d
    if len(a) > 4 and a[1] == "plan": plan(a[2], a[3], a[4], opt("--bpm"), opt("--offset"), opt("--music-start", 0.0), opt("--max-speed", 0.08), opt("--phrase-every", 8, int))
    elif len(a) > 5 and a[1] == "render": render(a[2], a[3], a[4], a[5])
    else: print(USAGE)
