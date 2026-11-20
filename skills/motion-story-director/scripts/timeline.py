###############
# Qiyas Sadıqov CC
###############
import json, re, sys

USAGE = """motion-timeline: beat grid builder + spec linter for motion prompts.

  python3 timeline.py grid --bpm 152 --dur 15 --fps 30 [--offset 0]
      -> table of beats/eighths with seconds and frame numbers, 8-beat phrase marks.
  python3 timeline.py snap plan.json [--div 2]
      -> snaps every scene/event time to the beat grid, prints a frame-accurate timeline and density report.
  python3 timeline.py lint SPEC.txt [--bpm 152]
      -> checks a written prompt: duration x fps = frame count, scene ranges (gaps/overlaps/order),
         off-beat moments, object counts, density (screen life) and missing rules.

plan.json:
{ "bpm": 152, "fps": 30, "duration": 15, "offset": 0,
  "scenes": [ {"name": "Lock screen", "start": 0, "end": 0.79,
               "events": [ {"t": 0.59, "what": "blob hops", "big": false} ]} ] }
"""

def frames(t, fps): return round(t * fps)

def cmd_grid(bpm, dur, fps, offset=0.0):
    beat = 60 / bpm
    print(f"BPM {bpm}: beat {beat:.4f} s = {beat * fps:.2f} frames @ {fps} fps; eighth {beat / 2:.4f} s; bar(4) {beat * 4:.3f} s; phrase(8) {beat * 8:.3f} s\n")
    print("| beat | s | frame | mark |\n|---:|---:|---:|---|")
    n = 0
    while offset + n * beat <= dur + 1e-9:
        t = offset + n * beat; mark = "PHRASE (big change)" if n % 8 == 0 else "bar" if n % 4 == 0 else ""
        print(f"| {n} | {t:.3f} | {frames(t, fps)} | {mark} |"); n += 1

def density(events, scenes, dur):
    out = []
    if events:
        out.append(f"events/s: {len(events) / dur:.2f} (target ~2.3 small events/s)")
        big = sorted(e["t"] for e in events if e.get("big"))
        if len(big) > 1:
            gaps = [b - a for a, b in zip(big, big[1:])]
            out.append(f"big accents every {sum(gaps) / len(gaps):.2f} s on average (target ~1.2 s); longest gap {max(gaps):.2f} s")
    for s in scenes:
        life = s["end"] - s["start"]
        if life > 2.0: out.append(f"! '{s['name']}' lives {life:.2f} s (target 1.2-1.6 s; split it or add a camera move)")
    return out

def cmd_snap(path, div=2):
    p = json.load(open(path)); bpm, fps, dur, off = p["bpm"], p["fps"], p["duration"], p.get("offset", 0)
    step = 60 / bpm / div; snap = lambda t: round(off + round((t - off) / step) * step, 3)
    allev = []
    print("| scene | start | end | start beat | frames |\n|---|---:|---:|---:|---|")
    for s in p["scenes"]:
        s["start"], s["end"] = snap(s["start"]), snap(s["end"])
        print(f"| {s['name']} | {s['start']:.3f} | {s['end']:.3f} | {(s['start'] - off) * bpm / 60:.1f} | {frames(s['start'], fps)}-{frames(s['end'], fps)} |")
        for e in s.get("events", []):
            e["t"] = snap(e["t"]); allev.append(e)
            print(f"|  - {e['what']}{' (BIG)' if e.get('big') else ''} | {e['t']:.3f} | | {(e['t'] - off) * bpm / 60:.2f} | {frames(e['t'], fps)} |")
    print("\n" + "\n".join(density(allev, p["scenes"], dur)))
    json.dump(p, open(path.replace(".json", ".snapped.json"), "w"), indent=1)
    print(f"\nsaved {path.replace('.json', '.snapped.json')}")

NUM = r"(\d+(?:\.\d+)?)"
def cmd_lint(path, bpm=None):
    txt = open(path, encoding="utf-8").read(); warn = []; info = []
    m = re.search(NUM + r"\s*(?:-second|s\b|sec)", txt); dur = float(m.group(1)) if m else None
    f = re.search(NUM + r"\s*fps", txt); fps = float(f.group(1)) if f else None
    fr = re.search(r"\((\d+)\s*frames\)", txt)
    if dur and fps:
        info.append(f"duration {dur} s @ {fps} fps = {dur * fps:.1f} frames")
        if fr and abs(int(fr.group(1)) - dur * fps) > 1.01: warn.append(f"frame count {fr.group(1)} != {dur} x {fps} = {dur * fps:.1f}")
    b = bpm or (float(x.group(1)) if (x := re.search(NUM + r"\s*BPM", txt)) else None)
    if b: info.append(f"{b} BPM -> beat {60 / b:.4f} s" + (f" = {60 / b * fps:.2f} frames" if fps else ""))
    if fps and re.search(r"frames at (\d+) fps", txt) and re.search(r"frames at (\d+) fps", txt).group(1) != str(int(fps)):
        warn.append("frame-based durations are given for a different fps than the video fps")
    ranges = [(float(a), float(c), txt[x.end():x.end() + 50].split("\n")[0]) for x in re.finditer(r"(?m)^\s*(?:[A-Z0-9]+[.)]\s+)?" + NUM + r"\s*[-\u2013]\s*" + NUM, txt) for a, c in [x.groups()]]
    ranges = [r for r in ranges if r[1] > r[0]]
    if ranges:
        info.append(f"{len(ranges)} timed scenes found")
        for (a1, b1, n1), (a2, b2, n2) in zip(ranges, ranges[1:]):
            if a2 < a1: warn.append(f"scene order: {a2} starts before previous {a1}")
            elif a2 < b1 - 1e-6: info.append(f"overlap {a2:.2f}-{b1:.2f} s (fine if it is a deliberate transition; say so in the prompt)")
            elif a2 > b1 + 0.3: info.append(f"gap {b1:.2f}-{a2:.2f} s with nothing specified (fine if it is a hold; say what moves)")
        if dur and abs(ranges[-1][1] - dur) > 0.05: warn.append(f"last scene ends at {ranges[-1][1]} s but video is {dur} s")
        lives = [b_ - a_ for a_, b_, _ in ranges]
        info.append(f"screen life avg {sum(lives) / len(lives):.2f} s (target 1.2-1.6 s for short-form)")
    if b:
        times = sorted(set(float(t) for t in re.findall(r"(?:at|on|by|from)\s+(\d+\.\d+)\s*s", txt)))
        off = [t for t in times if abs((t * b / 60 * 2) - round(t * b / 60 * 2)) > 0.12]
        if off: info.append("not on beat/eighth: " + ", ".join(f"{t}s (beat {t * b / 60:.2f})" for t in off[:12]))
    counts = [" ".join(c) for c in re.findall(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty)\s+(?:\w+\s+){0,3}?(diamonds?|cards?|bubbles?|points?|nodes?|rows?|tiles?|icons?|dots?|lobes?|rays?)\b", txt, re.I)]
    if counts: info.append("object counts mentioned: " + ", ".join(counts[:15]) + " -> check they stay consistent between scenes")
    for k in ["SOUND", "MUSIC"]:
        if k in txt.upper(): break
    else: warn.append("no SOUND/MUSIC section")
    if not re.search(r"fade|opacity", txt, re.I): warn.append("no rule about fades/opacity (default Claude will fade everything)")
    if not re.search(r"motion blur", txt, re.I): warn.append("no motion-blur rule")
    if not re.search(r"ease|spring|bezier|curve", txt, re.I): warn.append("no easing rule")
    if not re.search(r"\d+\s*px|0\.\d+\s*[WH]\b|safe", txt): warn.append("no edge margin / safe-zone rule")
    print("INFO\n- " + "\n- ".join(info)); print("\nWARNINGS\n- " + ("\n- ".join(warn) if warn else "none"))

if __name__ == "__main__":
    a = sys.argv
    def opt(k, d=None, typ=float): return typ(a[a.index(k) + 1]) if k in a else d
    if len(a) < 2: print(USAGE); sys.exit(1)
    if a[1] == "grid": cmd_grid(opt("--bpm"), opt("--dur"), opt("--fps", 30), opt("--offset", 0.0))
    elif a[1] == "snap": cmd_snap(a[2], opt("--div", 2, int))
    elif a[1] == "lint": cmd_lint(a[2], opt("--bpm"))
