###############
# Qiyas Sadıqov CC
###############
import csv, datetime, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

USAGE = """master-editor: the cutting-room protocol of master editors as a project you can run, track and test.

  python3 editroom.py init PROJECT [--clips RAW_DIR] [--title "Name"]   -> folders, PROTOCOL.md checklist, state.json
  python3 editroom.py status PROJECT                                   -> where the project is, what comes next
  python3 editroom.py run PROJECT STAGE [args]                         -> runs a stage with the sibling tools, logs results
        stages: selects | cutpoints CLIP... | split EDIT.json | rhythm CUT.mp4 [REF.mp4] | judge CUT.mp4
  python3 editroom.py done PROJECT STEP_NO ["note"]                     -> tick a protocol step (manual steps: viewing, notes)
  python3 editroom.py screening PROJECT NOTES.csv CUT.mp4 [--bin 5]    -> audience notes heat map: where viewers were bored,
        confused, lost or delighted; joined with rhythm flat zones when a rhythm.json exists
NOTES.csv columns: time (seconds, mm:ss or hh:mm:ss:ff), type (bored|confused|lost|loved|laugh|note), text, viewer
Sibling tools expected in the same folder: selects.py, cutpoint.py, splitedit.py, rhythm.py, sixjudge.py
Needs: numpy, Pillow (plus what the sibling tools need).
"""

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("Read the script or brief and write what each scene must make the viewer feel (before seeing any footage)", "manual"),
    ("Dailies pass 1: watch everything once, straight through, write first impressions only (no stopping, no cutting)", "manual"),
    ("Boards and selects: numbered still boards per scene, best takes wide to tight", "selects"),
    ("Pass 2 notes: rewatch circled takes, timecoded notes of best readings and reactions", "manual"),
    ("Assembly: cut every scene as if it were the only one; first pass WITHOUT temp music", "manual"),
    ("Cut points: blink, end of line, inevitable exit, motion peak for every transition", "cutpoints"),
    ("Sound grammar: J and L cuts for dialogue, room tone in every hole", "split"),
    ("Rhythm pass: shot-length shape, flat zones, metronomic runs; compare with a reference", "rhythm"),
    ("Rule of Six review: weakest cuts measured, then judged for emotion and story by watching", "judge"),
    ("Fresh eyes: a break, then a full screening with someone new; collect timecoded notes", "screening"),
    ("Lift and tighten: remove what has no positive reason to stay, re-screen", "manual"),
    ("Lock: final check of sync, levels, flash frames; export and archive the project", "manual"),
]
DIRS = ["01_raw", "02_selects", "03_assembly", "04_cuts", "05_analysis", "06_screenings", "notes"]

def load(pj): return json.load(open(os.path.join(pj, "state.json")))
def save(pj, s): json.dump(s, open(os.path.join(pj, "state.json"), "w"), indent=1); write_protocol(pj, s)

def write_protocol(pj, s):
    md = [f"# {s['title']}: cutting-room protocol", f"started {s['created']}", ""]
    for i, (txt, kind) in enumerate(STEPS, 1):
        st = s["steps"].get(str(i), {}); box = "x" if st.get("done") else " "
        md.append(f"- [{box}] **{i}. {txt}**" + (f"  _(tool: {kind})_" if kind != "manual" else "") + (f"\n    - {st['note']}" if st.get("note") else ""))
    md += ["", "## Rules on the wall", "- Emotion first, then story, then rhythm; eye trace, screen direction and space last (Rule of Six).",
           "- Never make a cut without a positive reason. When in doubt cut long, then trim.", "- Cut in movement; cut just before the blink; cut when the exit is inevitable.",
           "- The first viewing should give an emotional reaction, not a critical one: protect your first impressions.",
           "- A scene that works without music works. Music comes after the structure holds.", "- Hear the next scene before you see it when it pulls the story forward (J), stay on the listener when the reaction matters (L).",
           "- It does not matter what was intended, only what was captured.", "", "## Log"] + [f"- {x}" for x in s["log"][-40:]]
    open(os.path.join(pj, "PROTOCOL.md"), "w").write("\n".join(md))

def init(pj, clips=None, title=None):
    for d in DIRS: os.makedirs(os.path.join(pj, d), exist_ok=True)
    s = {"title": title or os.path.basename(os.path.abspath(pj)), "created": datetime.date.today().isoformat(), "clips": os.path.abspath(clips) if clips else None, "steps": {}, "log": []}
    open(os.path.join(pj, "notes", "first_impressions.md"), "w").write("# Pass 1: first impressions\nWrite feelings, not fixes. One line per take or scene.\n\n")
    open(os.path.join(pj, "06_screenings", "notes_template.csv"), "w").write("time,type,text,viewer\n00:42,bored,long walk to the car,A\n01:15,confused,who is the man on the phone?,B\n02:03,loved,her reaction to the news,A\n")
    save(pj, s); print(f"-> {pj}/PROTOCOL.md, folders {', '.join(DIRS)}")

def log(pj, s, msg): s["log"].append(f"{datetime.datetime.now():%Y-%m-%d %H:%M} {msg}"); save(pj, s)

def status(pj):
    s = load(pj); nxt = next((i for i in range(1, len(STEPS) + 1) if not s["steps"].get(str(i), {}).get("done")), None)
    done = sum(1 for v in s["steps"].values() if v.get("done")); print(f"{s['title']}: {done}/{len(STEPS)} steps done")
    for i, (txt, kind) in enumerate(STEPS, 1): print(f"  [{'x' if s['steps'].get(str(i), {}).get('done') else ' '}] {i:2d}. {txt}")
    if nxt: print(f"\nNEXT: step {nxt}: {STEPS[nxt - 1][0]}" + (f"\n  run: editroom.py run {pj} {STEPS[nxt - 1][1]} ..." if STEPS[nxt - 1][1] not in ("manual", "screening") else ""))

def tool(name, *args):
    p = os.path.join(HERE, name)
    if not os.path.exists(p): raise SystemExit(f"{name} not found next to editroom.py: copy it from its skill's scripts/ folder first")
    r = subprocess.run([sys.executable, p, *args], capture_output=True, text=True); print(r.stdout[-4000:])
    if r.returncode: print(r.stderr[-2000:]); raise SystemExit(f"{name} failed")

def run(pj, stage, args):
    s = load(pj); A = os.path.join(pj, "05_analysis")
    if stage == "selects":
        src = args[0] if args else s.get("clips")
        if not src: raise SystemExit("give the raw clips folder: run PROJECT selects RAW_DIR")
        tool("selects.py", "build", src, os.path.join(pj, "02_selects")); s["steps"]["3"] = {"done": True, "note": "boards + selects.mp4 in 02_selects"}; log(pj, s, "selects built")
    elif stage == "cutpoints":
        tool("cutpoint.py", "find", *args, os.path.join(A, "cutpoints")); s["steps"]["6"] = {"done": True, "note": f"{len(args)} clips, markers in 05_analysis/cutpoints"}; log(pj, s, "cut points found")
    elif stage == "split":
        tool("splitedit.py", "plan", args[0], os.path.join(A, "split")); s["steps"]["7"] = {"done": False, "note": "plan in 05_analysis/split; render with splitedit.py render after review"}; log(pj, s, "split edit plan made")
    elif stage == "rhythm":
        if len(args) > 1: tool("rhythm.py", "compare", args[0], args[1], os.path.join(A, "rhythm"))
        else: tool("rhythm.py", "analyze", args[0], os.path.join(A, "rhythm"))
        s["steps"]["8"] = {"done": True, "note": "05_analysis/rhythm"}; log(pj, s, f"rhythm analysed: {os.path.basename(args[0])}")
    elif stage == "judge":
        tool("sixjudge.py", "judge", args[0], os.path.join(A, "judge")); s["steps"]["9"] = {"done": False, "note": "measured; now watch the weakest cuts for emotion and story, then tick"}; log(pj, s, f"rule of six measured: {os.path.basename(args[0])}")
    else: raise SystemExit(f"unknown stage {stage}")

def to_s(t, fps=25.0):
    t = t.strip()
    if ":" not in t: return float(t)
    p = [float(x) for x in t.split(":")]
    return p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 3600 + p[1] * 60 + p[2] + p[3] / fps

def screening(pj, notes, cut, binsz=5):
    s = load(pj); pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", cut], capture_output=True, text=True).stdout)
    dur = float(pr["format"]["duration"]); v = next((x for x in pr["streams"] if x["codec_type"] == "video"), {"r_frame_rate": "25/1"}); n, d_ = map(int, v["r_frame_rate"].split("/")); fps = n / d_
    rows = [r for r in csv.DictReader(open(notes)) if r.get("time")]; outside = [r for r in rows if not 0 <= to_s(r["time"], fps) <= dur]; rows = [r for r in rows if r not in outside]; nb = int(np.ceil(dur / binsz)); kinds = ["bored", "confused", "lost", "loved", "laugh", "note"]
    H = {k: np.zeros(nb) for k in kinds}; viewers = set()
    for r in rows:
        k = r.get("type", "note").strip().lower(); k = k if k in H else "note"; b = min(nb - 1, int(to_s(r["time"], fps) // binsz)); H[k][b] += 1; viewers.add(r.get("viewer", "?"))
    neg = H["bored"] + H["confused"] + H["lost"]; pos = H["loved"] + H["laugh"]
    flat = []
    rj = os.path.join(pj, "05_analysis", "rhythm", "rhythm.json")
    if os.path.exists(rj): flat = json.load(open(rj)).get("flat_zones", [])
    out = os.path.join(pj, "06_screenings"); W, Hh = 1200, 260; im = Image.new("RGB", (W, Hh), (16, 16, 16)); d = ImageDraw.Draw(im)
    X = lambda t: 40 + (W - 60) * t / dur; mx = max(1, neg.max(), pos.max())
    for f in flat: d.rectangle([X(f["from_s"]), 20, X(f["to_s"]), Hh - 30], fill=(45, 35, 35))
    for b in range(nb):
        x0, x1 = X(b * binsz), X(min(dur, (b + 1) * binsz)) - 2
        if pos[b]: d.rectangle([x0, 125 - pos[b] / mx * 100, x1, 125], fill=(90, 200, 120))
        if neg[b]: d.rectangle([x0, 130, x1, 130 + neg[b] / mx * 100], fill=(230, 90, 80))
    d.line([(40, 128), (W - 20, 128)], fill=(90, 90, 90))
    for t in range(0, int(dur) + 1, max(10, int(dur / 12) // 10 * 10 or 10)): d.text((X(t) - 8, Hh - 22), f"{t // 60}:{t % 60:02d}", fill=(170, 170, 170))
    d.text((44, 4), "green up = loved/laugh, red down = bored/confused/lost, dark band = rhythm flat zone", fill=(220, 220, 220)); im.save(os.path.join(out, "heatmap.png"))
    hot = sorted(range(nb), key=lambda b: -neg[b])[:6]
    md = [f"# Screening notes: {os.path.basename(cut)}", f"{len(rows)} notes from {len(viewers)} viewers, {binsz}s bins" + (f"; {len(outside)} notes outside the cut's length ignored (check their times): " + ", ".join(r["time"] for r in outside) if outside else ""), "", "## Where attention broke (most negative notes first)"]
    for b in hot:
        if neg[b] == 0: break
        t0 = b * binsz; texts = [r["text"] for r in rows if b * binsz <= to_s(r["time"], fps) < (b + 1) * binsz and r.get("type", "").lower() in ("bored", "confused", "lost")]
        inflat = any(f["from_s"] <= t0 < f["to_s"] for f in flat)
        md.append(f"- **{t0 // 60}:{t0 % 60:02d}-{(t0 + binsz) // 60}:{(t0 + binsz) % 60:02d}**: {int(H['bored'][b])} bored, {int(H['confused'][b])} confused, {int(H['lost'][b])} lost" + (" (inside a measured flat zone)" if inflat else "") + (f": {'; '.join(texts[:4])}" if texts else ""))
    md += ["", "## What worked (keep it, protect it)"] + [f"- {b * binsz // 60}:{b * binsz % 60:02d}: {int(pos[b])} notes" for b in sorted(range(nb), key=lambda b: -pos[b])[:5] if pos[b]]
    md += ["", "Rule of thumb from the cutting room: when several viewers report the same spot, the problem is usually a little before it."]
    open(os.path.join(out, "screening.md"), "w").write("\n".join(md)); print("\n".join(md))
    s["steps"]["10"] = {"done": True, "note": f"{len(rows)} notes, 06_screenings/screening.md"}; log(pj, s, f"screening notes analysed ({len(rows)})")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 2 and a[1] == "init": init(a[2], opt("--clips"), opt("--title"))
    elif len(a) > 2 and a[1] == "status": status(a[2])
    elif len(a) > 3 and a[1] == "run": run(a[2], a[3], a[4:])
    elif len(a) > 3 and a[1] == "done":
        s = load(a[2]); s["steps"][a[3]] = {"done": True, "note": a[4] if len(a) > 4 else ""}; log(a[2], s, f"step {a[3]} done"); status(a[2])
    elif len(a) > 4 and a[1] == "screening": screening(a[2], a[3], a[4], int(opt("--bin", 5)))
    else: print(USAGE)
