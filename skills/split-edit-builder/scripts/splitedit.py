###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys, wave
import numpy as np

USAGE = """split-edit-builder: turn hard dialogue cuts into J-cuts and L-cuts (Dede Allen's sound overlaps) using the
handles in your source clips, fill holes with room tone, and export the result as video and as an EDL.

  python3 splitedit.py init CLIPS_DIR EDIT.json [--handle 0.5]   -> starter edit list from a folder (clips in name order,
                                                                   trimmed by --handle at both ends so overlaps have media)
  python3 splitedit.py plan EDIT.json OUT_DIR [--max-lead 20] [--max-lag 25]
      -> OUT_DIR/plan.json + plan.md: for every cut, speech at the end of A / start of B, available handles, and the
         proposal: J (B's voice heard while still on A), L (A's sound carries over B), or hard with a short crossfade
  python3 splitedit.py render EDIT.json OUT.mp4 [--plan OUT_DIR/plan.json] [--roomtone 1] [--xfade 3]
      -> video with the split edits applied (total length unchanged), OUT.edl (CMX3600, separate V and A events)

EDIT.json: {"fps": 25, "events": [{"clip": "a.mp4", "in": 1.0, "out": 4.2}, ...]}  (seconds in the source clip, snapped to whole frames)
Rules used (the classic dialogue grammar):
  - A still talking at its out point and B has no speech at its head (a listener/reaction) -> L-cut: hear A over B
  - B's line starts right at its in point and A is quiet -> J-cut: roll the picture cut 4-20 frames later, so B's
    voice is heard while A is still on screen (uses A's handle after its out point)
  - both talking at the cut -> keep hard, 2-4 frame crossfade so no click
  - never cut a word: lead/lag snap to the nearest pause; never use media beyond the clip
Edit plan.json by hand to override any proposal (type, frames). Needs: numpy, ffmpeg/ffprobe.
"""

SR = 48000

def dur_of(p): return float(json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", p], capture_output=True, text=True).stdout)["format"]["duration"])

def load_audio(p, cache={}):
    if p not in cache:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-vn", "-ac", "2", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1, 2) / 32768
        cache[p] = a if len(a) else np.zeros((int(dur_of(p) * SR), 2), np.float32)
    return cache[p]

def speech_mask(a):
    m = np.sqrt(np.convolve((a ** 2).mean(1), np.ones(480) / 480, "same")[::480] + 1e-12)
    thr = max(np.percentile(m, 10) * 4, np.percentile(m, 90) * 0.15)
    return np.convolve((m > thr).astype(float), np.ones(12) / 12, "same") > 0.3

def init(folder, out, handle=0.5):
    clips = [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith((".mp4", ".mov", ".m4v", ".mkv", ".mxf"))]
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", clips[0]], capture_output=True, text=True).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video"); n, d = map(int, v["r_frame_rate"].split("/"))
    fps = round(n / d, 3); ev = [{"clip": c, "in": round(round(handle * fps) / fps, 4), "out": round(round((dur_of(c) - handle) * fps) / fps, 4)} for c in clips]
    json.dump({"fps": fps, "events": ev}, open(out, "w"), indent=1); print(f"-> {out} ({len(ev)} events, {handle}s handles)")

def load_edit(path):
    E = json.load(open(path)); fps = E["fps"]
    for e in E["events"]: e["in"], e["out"] = round(e["in"] * fps) / fps, round(e["out"] * fps) / fps
    return E

def plan(edit_path, out, max_lead=20, max_lag=25):
    E = load_edit(edit_path); fps = E["fps"]; ev = E["events"]; os.makedirs(out, exist_ok=True); P = []
    for i in range(len(ev) - 1):
        A, B = ev[i], ev[i + 1]; ma, mb = speech_mask(load_audio(A["clip"])), speech_mask(load_audio(B["clip"]))
        ia, ib = int(A["out"] * 100), int(B["in"] * 100)
        a_talk_out = bool(ma[max(0, ia - 15):ia].mean() > 0.5) if ia <= len(ma) else False
        b_talk_in = bool(mb[ib:ib + 15].mean() > 0.5) if ib < len(mb) else False
        a_last = next((k for k in range(min(ia, len(ma)) - 1, max(0, ia - 300), -1) if ma[k]), None)
        a_pause = (ia - a_last - 1) / 100 if a_last is not None else 3.0
        h_before_b = B["in"]; h_after_a = dur_of(A["clip"]) - A["out"]
        prop = {"cut": i + 1, "a": os.path.basename(A["clip"]), "b": os.path.basename(B["clip"]), "a_talking_at_out": a_talk_out, "b_talking_at_in": b_talk_in,
                "a_pause_before_out_s": round(a_pause, 2), "handle_before_b_s": round(h_before_b, 2), "handle_after_a_s": round(h_after_a, 2)}
        if a_talk_out and not b_talk_in:
            k = ia
            while k < len(ma) and ma[k] and (k - ia) / 100 < min(h_after_a, max_lag / fps): k += 1
            lag = int(round((k - ia) / 100 * fps)) + 2
            lag = min(lag, int(h_after_a * fps), max_lag)
            prop.update(type="L" if lag >= 3 else "hard", frames=lag if lag >= 3 else 0,
                        reason="A is mid-line and B opens on a listener: keep hearing A over B's reaction" if lag >= 3 else "L wanted but A has no handle after its out point: keep hard, or extend A's media")
        elif b_talk_in and not a_talk_out:
            k = ia
            while k < len(ma) and not ma[k] and (k - ia) / 100 < h_after_a: k += 1
            quiet_after_a = (k - ia) / 100
            b_len = B["out"] - B["in"]
            lead = int(min(max_lead, quiet_after_a * fps - 1, h_after_a * fps, b_len * 0.4 * fps))
            prop.update(type="J" if lead >= 4 else "hard", frames=lead if lead >= 4 else 0,
                        reason="B's line starts at the cut and A is quiet: stay on A while B's voice begins, cut to B a beat later" if lead >= 4 else "J wanted but A has no quiet picture after its out point: keep hard, or extend A's media")
        elif a_talk_out and b_talk_in:
            prop.update(type="hard", frames=0, reason="both speaking at the cut: keep the cut, crossfade 2-4 frames")
        else:
            prop.update(type="hard", frames=0, reason="no speech at the cut: picture and sound can cut together (or prelap ambience by taste)")
        P.append(prop)
    json.dump({"edit": edit_path, "fps": fps, "cuts": P}, open(os.path.join(out, "plan.json"), "w"), indent=1)
    md = ["# Split edit plan", "", "| cut | A -> B | A talking at out | B talking at in | proposal | why |", "|---|---|---|---|---|---|"]
    md += [f"| {p['cut']} | {p['a']} -> {p['b']} | {'yes' if p['a_talking_at_out'] else 'no'} | {'yes' if p['b_talking_at_in'] else 'no'} | **{p['type']}{' ' + str(p['frames']) + 'f' if p['frames'] else ''}** | {p['reason']} |" for p in P]
    open(os.path.join(out, "plan.md"), "w").write("\n".join(md)); print("\n".join(md))

def tcs(sec, fps):
    f = int(round(fps)); x = int(round(sec * fps)); return f"{x // (3600 * f):02d}:{x // (60 * f) % 60:02d}:{x // f % 60:02d}:{x % f:02d}"

def quiet_tone(a, sec=1.0):
    n = int(sec * SR)
    if len(a) <= n: return a
    e = np.convolve((a ** 2).mean(1), np.ones(n // 10) / (n // 10), "valid")[::n // 20]
    s = int(np.argmin(e[: max(1, (len(a) - n) // (n // 20))])) * (n // 20); return a[s:s + n]

def render(edit_path, out, plan_path=None, roomtone=1.0, xfade=3):
    E = load_edit(edit_path); fps = E["fps"]; ev = E["events"]
    P = {p["cut"]: p for p in json.load(open(plan_path))["cuts"]} if plan_path else {}
    starts = np.cumsum([0] + [e["out"] - e["in"] for e in ev]); total = starts[-1]
    reg = [{"t0": starts[i], "t1": starts[i + 1], "s0": e["in"]} for i, e in enumerate(ev)]
    vid = [{"in": e["in"], "out": e["out"]} for e in ev]
    for i in range(len(ev) - 1):
        p = P.get(i + 1, {"type": "hard", "frames": 0}); d = p.get("frames", 0) / fps
        if p.get("type") == "L":
            d = min(d, max(0.0, reg[i + 1]["t1"] - reg[i + 1]["t0"] - 0.1))
            reg[i]["t1"] += d; reg[i + 1]["t0"] += d; reg[i + 1]["s0"] += d
        if p.get("type") == "J":
            d = min(d, max(0.0, vid[i + 1]["out"] - vid[i + 1]["in"] - 0.1)); vid[i]["out"] += d; vid[i + 1]["in"] += d
    N = int(total * SR) + 1; mix = np.zeros((N, 2), np.float32); xf = max(1, int(xfade / fps * SR)); cover = np.zeros(N, np.float32)
    for r in reg: cover[max(0, int(r["t0"] * SR)): int(r["t1"] * SR)] = 1
    hole = 1 - np.convolve(cover, np.ones(xf) / xf, "same")
    for i, (e, r) in enumerate(zip(ev, reg)):
        a = load_audio(e["clip"]); s0 = int(r["s0"] * SR); L = int((r["t1"] - r["t0"]) * SR); t0 = int(r["t0"] * SR)
        seg = np.zeros((L, 2), np.float32); src = a[max(0, s0): max(0, s0) + L]; seg[: len(src)] = src
        ramp = np.linspace(0, 1, min(xf, L // 2 or 1))[:, None]; seg[: len(ramp)] *= ramp; seg[len(seg) - len(ramp):] *= ramp[::-1]
        mix[t0: t0 + L] += seg[: max(0, min(L, N - t0))]
        if roomtone > 0:
            tone = quiet_tone(a); p0, p1 = int(starts[i] * SR), int(starts[i + 1] * SR)
            if len(tone) > 10:
                bed = np.tile(tone, (int(np.ceil((p1 - p0) / len(tone))) + 1, 1))[: p1 - p0] * roomtone
                fr = np.linspace(0, 1, min(xf * 3, len(bed) // 2 or 1))[:, None]; bed[: len(fr)] *= fr; bed[len(bed) - len(fr):] *= fr[::-1]
                mix[p0:p1] += bed * hole[p0:p1, None][: len(bed)]
    peak = np.abs(mix).max()
    if peak > 0.99: mix *= 0.99 / peak
    wav = out + ".wav"
    with wave.open(wav, "wb") as f: f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((mix * 32767).astype(np.int16).tobytes())
    inputs, fc = [], []
    for i, e in enumerate(ev):
        inputs += ["-i", e["clip"]]; fc.append(f"[{i}:v]trim=start={vid[i]['in']}:end={vid[i]['out']},setpts=PTS-STARTPTS,fps={fps},scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p[v{i}]")
    fc.append("".join(f"[v{i}]" for i in range(len(ev))) + f"concat=n={len(ev)}:v=1:a=0[vout]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-i", wav, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{len(ev)}:a",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-c:a", "aac", "-b:a", "256k", "-shortest", out], check=True)
    os.remove(wav)
    L = [f"TITLE: {os.path.splitext(os.path.basename(out))[0]}", "FCM: NON-DROP FRAME", ""]; k = 1
    vst = np.cumsum([0] + [v["out"] - v["in"] for v in vid])
    for i, (e, r) in enumerate(zip(ev, reg)):
        name = os.path.basename(e["clip"]); reel = f"AX"
        L += [f"{k:03d}  {reel:8s} V     C        {tcs(vid[i]['in'], fps)} {tcs(vid[i]['out'], fps)} {tcs(vst[i], fps)} {tcs(vst[i + 1], fps)}", f"* FROM CLIP NAME: {name}", ""]; k += 1
        L += [f"{k:03d}  {reel:8s} A     C        {tcs(r['s0'], fps)} {tcs(r['s0'] + r['t1'] - r['t0'], fps)} {tcs(r['t0'], fps)} {tcs(r['t1'], fps)}", f"* FROM CLIP NAME: {name}", ""]; k += 1
    open(os.path.splitext(out)[0] + ".edl", "w").write("\n".join(L))
    ch = [f"cut {c}: {p['type']} {p['frames']}f" for c, p in sorted(P.items()) if p.get("frames")]
    print(f"-> {out} ({total:.2f}s) and {os.path.splitext(out)[0]}.edl; split edits: {', '.join(ch) if ch else 'none'}")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "init": init(a[2], a[3], float(opt("--handle", 0.5)))
    elif len(a) > 3 and a[1] == "plan": plan(a[2], a[3], int(opt("--max-lead", 20)), int(opt("--max-lag", 25)))
    elif len(a) > 3 and a[1] == "render": render(a[2], a[3], opt("--plan"), float(opt("--roomtone", 1.0)), int(opt("--xfade", 3)))
    else: print(USAGE)
