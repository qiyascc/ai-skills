###############
# Qiyas Sadıqov CC
###############
import json, os, random, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, resample

USAGE = """motion-sfx: synthesize a clean UI sound library and mix event-synced sound design.

  python3 sfx.py synth OUT_DIR                 # builds 12 sound types x 3 variants (48 kHz wav)
  python3 sfx.py mix cues.json OUT.wav         # mixes cues (+ optional music) and masters to target LUFS
  python3 sfx.py mux video.mp4 audio.wav out.mp4

cues.json:
{
  "duration": 15.0, "sr": 48000, "lufs": -13, "true_peak": -1.0,
  "library": "sfx_lib",                       # folder with TYPE_*.wav (synth output or real samples)
  "music": "track.mp3", "music_start": 49.735, "music_gain_db": 0, "music_highpass": 55,
  "duck": {"db": -8, "ms": 60, "band": [2000, 8000], "types": ["tick", "click", "key"]},
  "cues": [ {"t": 0.99, "type": "thud", "db": 0}, {"t": 1.20, "type": "click"} ]
}
Rules applied automatically: random pitch +-1 semitone, the same sample never twice within 2 s,
max 8 events per 0.25 s (extras dropped, reported), 160 Hz high-pass on small UI sounds.
"""

SR = 48000
SMALL = {"tick", "click", "key", "swish", "pop", "snip"}
LEVEL = {"tick": 10.5, "click": 10, "key": 9, "swish": 9.5, "whoosh": 6, "pop": 8, "thud": 7, "chime": 5,
         "shine": 6, "squelch": 7, "snip": 8, "shutter": 8}

def env(n, a, d, curve=4.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-curve * np.maximum(0, t - a) / max(d, 1e-4))
    return e

def hp(x, f, sr=SR):
    return sosfilt(butter(2, f, 'hp', fs=sr, output='sos'), x, axis=0)

def bp(x, lo, hi, sr=SR):
    return sosfilt(butter(2, [lo, hi], 'bp', fs=sr, output='sos'), x, axis=0)

def noise(n, rnd):
    return rnd.standard_normal(n)

def synth_one(kind, v):
    rnd = np.random.default_rng(1000 + v * 17 + sum(map(ord, kind)) % 997)
    j = 1 + 0.06 * (v - 1)
    if kind == "tick":
        n = int(.03 * SR); x = bp(noise(n, rnd), 3500 * j, 9000) * env(n, .0005, .006)
    elif kind == "click":
        n = int(.05 * SR); t = np.arange(n) / SR
        x = (bp(noise(n, rnd), 1800 * j, 6000) * .6 + np.sin(2 * np.pi * 900 * j * t) * .5) * env(n, .0008, .012)
    elif kind == "key":
        n = int(.06 * SR); x = bp(noise(n, rnd), 1500 * j, 7000) * env(n, .001, .015) + bp(noise(n, rnd), 300, 1200) * env(n, .001, .03) * .3
    elif kind == "pop":
        n = int(.09 * SR); t = np.arange(n) / SR; f = 600 * j * np.exp(-t * 30) + 300
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .001, .03)
    elif kind in ("whoosh", "swish"):
        L = .55 if kind == "whoosh" else .25; n = int(L * SR); t = np.linspace(0, 1, n)
        lo, hi = (300, 5000) if kind == "whoosh" else (900, 8000)
        nz = noise(n, rnd); out = np.zeros(n); seg = 512
        for i in range(0, n, seg):
            c = lo + (hi - lo) * (t[i] ** 1.5)
            chunk = nz[i:i + seg]; out[i:i + len(chunk)] = bp(chunk, c * .7, min(c * 1.4, SR / 2 - 100))
        x = out * np.sin(np.pi * t) ** 2
    elif kind == "thud":
        n = int(.25 * SR); t = np.arange(n) / SR; f = 120 * j * np.exp(-t * 18) + 55
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, .06) + bp(noise(n, rnd), 200, 900) * env(n, .001, .015) * .3
    elif kind in ("chime", "shine"):
        L = 1.2 if kind == "chime" else .7; n = int(L * SR); t = np.arange(n) / SR
        base = (880 if kind == "chime" else 1760) * j; x = np.zeros(n)
        for k, a in [(1, 1), (2.01, .45), (3.03, .2), (4.2, .1)]:
            x += a * np.sin(2 * np.pi * base * k * t) * np.exp(-t * (3 + k * 2))
        x *= env(n, .003 if kind == "chime" else .08, L)
        if kind == "shine": x += bp(noise(n, rnd), 6000, 12000) * env(n, .1, .25) * .15
    elif kind == "squelch":
        n = int(.22 * SR); t = np.arange(n) / SR; f = 220 * j + 500 * np.sin(np.pi * t / .22)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .01, .08) * (1 + .5 * np.sin(2 * np.pi * 38 * t))
    elif kind == "snip":
        n = int(.07 * SR); x = bp(noise(n, rnd), 2500 * j, 10000) * (env(n, .0005, .004) + np.roll(env(n, .0005, .006), int(.025 * SR)) * .8)
    elif kind == "shutter":
        n = int(.18 * SR); a = bp(noise(n, rnd), 1200, 8000)
        x = a * (env(n, .0005, .008) + np.roll(env(n, .0005, .012), int(.07 * SR)) * .9)
    else:
        raise ValueError(kind)
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.5
    return np.stack([x, x], 1)

def cmd_synth(out):
    os.makedirs(out, exist_ok=True)
    for kind in LEVEL:
        for v in (1, 2, 3):
            wavfile.write(f"{out}/{kind}_{v}.wav", SR, synth_one(kind, v).astype(np.float32))
    print(f"wrote {len(LEVEL) * 3} files to {out}")

def load(path, sr=SR, start=0.0, dur=None):
    with tempfile.TemporaryDirectory() as d:
        tmp = os.path.join(d, "a.wav")
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-ss", str(start), "-i", path]
        if dur: cmd += ["-t", str(dur)]
        subprocess.run(cmd + ["-ac", "2", "-ar", str(sr), "-c:a", "pcm_f32le", tmp], check=True)
        _, x = wavfile.read(tmp)
    x = x.astype(np.float64)
    return x if x.ndim == 2 else np.stack([x, x], 1)

def pitch(x, semis):
    r = 2 ** (semis / 12); n = max(8, int(len(x) / r))
    return resample(x, n, axis=0)

def cmd_mix(cfg_path, out):
    cfg = json.load(open(cfg_path)); base = os.path.dirname(os.path.abspath(cfg_path))
    sr = cfg.get("sr", SR); dur = cfg["duration"]; N = int(dur * sr); rnd = random.Random(cfg.get("seed", 3))
    lib = os.path.join(base, cfg.get("library", "sfx_lib"))
    files = {}
    for f in sorted(os.listdir(lib)):
        if f.endswith((".wav", ".mp3", ".flac", ".aif", ".aiff")):
            files.setdefault(f.rsplit("_", 1)[0] if "_" in f else os.path.splitext(f)[0], []).append(os.path.join(lib, f))
    fx = np.zeros((N, 2)); last_used = {}; times = []; dropped = []; dips = []
    duck = cfg.get("duck", {"db": -8, "ms": 60, "band": [2000, 8000], "types": ["tick", "click", "key"]})
    for c in sorted(cfg["cues"], key=lambda c: c["t"]):
        t, kind = c["t"], c["type"]
        if sum(1 for u in times if t - .25 < u <= t) >= 8: dropped.append(c); continue
        cands = files.get(kind)
        if not cands: print(f"! no samples for '{kind}' in {lib}", file=sys.stderr); continue
        fresh = [p for p in cands if t - last_used.get(p, -99) >= 2.0] or cands
        p = rnd.choice(fresh); last_used[p] = t; times.append(t)
        x = pitch(load(p, sr), rnd.uniform(-1, 1))
        if kind in SMALL: x = hp(x, 160, sr)
        g = 10 ** ((LEVEL.get(kind, 6) - 30 + c.get("db", 0)) / 20)
        x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * g * 0.1
        i = int(t * sr); j = min(N, i + len(x))
        if i < N: fx[i:j] += x[:j - i]
        if kind in duck.get("types", []): dips.append(t)
    mix = fx
    if cfg.get("music"):
        m = load(os.path.join(base, cfg["music"]), sr, cfg.get("music_start", 0), dur)
        m = np.pad(m, ((0, max(0, N - len(m))), (0, 0)))[:N]
        if cfg.get("music_highpass"): m = hp(m, cfg["music_highpass"], sr)
        m *= 10 ** (cfg.get("music_gain_db", 0) / 20) * 0.25
        lo, hi = duck.get("band", [2000, 8000]); band = bp(m, lo, hi, sr)
        gain = np.zeros(N); w = int(duck.get("ms", 60) / 1000 * sr); r = int(.01 * sr)
        for t in dips:
            i = int(t * sr); seg = np.ones(w + 2 * r); seg[:r] = np.linspace(0, 1, r); seg[-r:] = np.linspace(1, 0, r)
            a, b = max(0, i - r), min(N, i - r + len(seg)); gain[a:b] = np.maximum(gain[a:b], seg[:b - a])
        dipamt = 1 - 10 ** (duck.get("db", -8) / 20)
        m = m - band * (gain * dipamt)[:, None]
        mix = mix + m
    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "raw.wav"); wavfile.write(raw, sr, mix.astype(np.float32))
        lufs, tp = cfg.get("lufs", -13), cfg.get("true_peak", -1.0)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-af",
                        f"loudnorm=I={lufs}:TP={tp}:LRA=9,alimiter=limit={10 ** (tp / 20):.4f}:attack=5:release=50:level=false",
                        "-ar", str(sr), out], check=True)
    print(f"mixed {len(times)} cues -> {out} (target {cfg.get('lufs', -13)} LUFS)" + (f", dropped {len(dropped)} (>8 per 0.25 s)" if dropped else ""))

def cmd_mux(video, audio, out):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", out], check=True)
    print("->", out)

if __name__ == "__main__":
    if len(sys.argv) < 3: print(USAGE); sys.exit(1)
    {"synth": lambda: cmd_synth(sys.argv[2]), "mix": lambda: cmd_mix(sys.argv[2], sys.argv[3]),
     "mux": lambda: cmd_mux(*sys.argv[2:5])}[sys.argv[1]]()
