###############
# Qiyas Sadıqov CC
###############
import argparse
import json

def grid(bpm, offset, duration, per_bar):
    beat = 60.0 / bpm
    beats = []
    i = 0
    while True:
        t = offset + i * beat
        if t > duration + 1e-9:
            break
        beats.append({"time": round(t, 3), "beat": i % per_bar + 1, "bar": i // per_bar + 1})
        i += 1
    return beat, beats

def nearest(beats, t, bars_only):
    pool = [b for b in beats if b["beat"] == 1] if bars_only else beats
    return min(pool, key=lambda b: abs(b["time"] - t)) if pool else None

def fmt(t):
    sign = "-" if t < 0 else ""
    m, s = divmod(abs(t), 60)
    return f"{sign}{int(m)}:{s:06.3f}"

def main():
    p = argparse.ArgumentParser(
        description="Beat and bar timestamps for a track on your edit timeline, snapping edit moments to them, "
                    "evenly spaced reveal slots, and where to trim a track so its drop lands at a chosen time.")
    p.add_argument("--bpm", type=float, required=True, help="Track tempo in beats per minute.")
    p.add_argument("--offset", type=float, default=0.0,
                   help="Time of the first downbeat ON THE EDIT TIMELINE, after trimming the track (default 0).")
    p.add_argument("--duration", type=float, default=30.0, help="Timeline length to cover in seconds (default 30).")
    p.add_argument("--beats-per-bar", type=int, default=4, help="Beats per bar (default 4).")
    p.add_argument("--phrase", type=int, default=8, help="Bars per phrase, where builds and changes usually land (default 8; try 4).")
    p.add_argument("--snap", help="Comma separated timeline moments in seconds to snap, e.g. 3.2,12.8.")
    p.add_argument("--beats", action="store_true", help="Snap to any beat instead of bar starts.")
    p.add_argument("--slots", help="START,END in seconds: list evenly spaced cut or reveal slots on the grid between them.")
    p.add_argument("--every", type=float, default=4, help="Beats between slots for --slots (default 4 = one per bar; 2 = twice per bar).")
    p.add_argument("--track-drop", type=float, help="Where the drop or change is in the ORIGINAL track, in seconds.")
    p.add_argument("--want-drop-at", type=float, help="Where you want that drop on the timeline, in seconds.")
    p.add_argument("--fps", type=float, default=30, help="Frame rate, for converting nudges to frames (default 30).")
    p.add_argument("--json", action="store_true", help="Print JSON.")
    a = p.parse_args()

    report = {}
    if a.track_drop is not None and a.want_drop_at is not None:
        start = a.track_drop - a.want_drop_at
        report["trim"] = {"start_track_at": round(start, 3), "drop_on_timeline": a.want_drop_at}

    beat, beats = grid(a.bpm, a.offset, a.duration, a.beats_per_bar)
    bar = beat * a.beats_per_bar
    bars = [b for b in beats if b["beat"] == 1]
    phrases = [b for b in bars if (b["bar"] - 1) % a.phrase == 0]
    report.update({"beat_seconds": round(beat, 4), "bar_seconds": round(bar, 4),
                   "bars": [b["time"] for b in bars], "phrases": [b["time"] for b in phrases]})

    snaps = []
    if a.snap:
        for raw in a.snap.split(","):
            t = float(raw)
            n = nearest(beats, t, not a.beats)
            if n:
                snaps.append({"moment": t, "snap_to": n["time"], "bar": n["bar"], "beat": n["beat"], "shift": round(n["time"] - t, 3)})
    report["snaps"] = snaps

    slots = []
    if a.slots:
        start, end = (float(x) for x in a.slots.split(","))
        first = nearest(beats, start, False)
        if first:
            step = beat * a.every
            t = first["time"]
            while t <= end + 1e-9:
                slots.append(round(t, 3))
                t += step
    report["slots"] = slots

    last = max([s["snap_to"] for s in snaps] + slots + [0.0])
    drift = (last - a.offset) * (1 - a.bpm / (a.bpm + 1)) if last > a.offset else 0.0
    report["drift_per_bpm_at_last_moment"] = round(drift, 3)

    if a.json:
        print(json.dumps(report, indent=2))
        return

    if "trim" in report:
        t = report["trim"]
        if t["start_track_at"] >= 0:
            print(f"Trim: start the track at {fmt(t['start_track_at'])} in the original file; the drop then lands at {fmt(a.want_drop_at)} on the timeline.")
        else:
            print(f"Trim: the drop is too early in the track. Start the music {fmt(-t['start_track_at'])} after the video starts, or pick a later change.")
        print("After trimming, find the first downbeat on the timeline and pass it as --offset.")
        print()
    print(f"{a.bpm:g} BPM: one beat = {beat:.3f} s, one bar = {bar:.3f} s, one {a.phrase}-bar phrase = {bar * a.phrase:.2f} s")
    print(f"A cut 2 to 3 frames early at {a.fps:g} fps = {2 / a.fps:.3f} to {3 / a.fps:.3f} s before the beat.")
    print()
    print("Phrase starts (likely spots for a build, drop or change; confirm by ear):")
    print(", ".join(fmt(b["time"]) for b in phrases) or "none in range")
    print()
    print("Bar starts:")
    print(", ".join(fmt(b["time"]) for b in bars))
    if snaps:
        print()
        print("| Moment | Snap to | Bar.beat | Shift |")
        print("|---|---|---|---|")
        for s in snaps:
            print(f"| {fmt(s['moment'])} | {fmt(s['snap_to'])} | {s['bar']}.{s['beat']} | {s['shift']:+.3f} s |")
    if slots:
        print()
        print(f"{len(slots)} slots every {a.every:g} beats ({beat * a.every:.3f} s): " + ", ".join(fmt(s) for s in slots))
    if drift > 0.05:
        print()
        print(f"Drift warning: if the real tempo is off by 1 BPM, the grid is about {drift:.2f} s off by {fmt(last)}. "
              "If the BPM is approximate, put markers on the actual beats in the editor and trust those.")

if __name__ == "__main__":
    main()
