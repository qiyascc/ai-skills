###############
# Qiyas Sadıqov CC
###############
import argparse
import json
import re
import shutil
import subprocess
import sys

def measure(path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg is not installed. Install it (https://ffmpeg.org/download.html) and run again.")
    cmd = [ffmpeg, "-hide_banner", "-nostats", "-i", path, "-vn",
           "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", result.stderr, re.S)
    if not match:
        sys.exit(f"Could not measure {path}:\n{result.stderr[-800:]}")
    data = json.loads(match.group(0))
    return {
        "integrated_lufs": float(data["input_i"]),
        "true_peak_dbtp": float(data["input_tp"]),
        "loudness_range_lu": float(data["input_lra"]),
    }

def verdict(m, target, peak):
    notes = []
    diff = m["integrated_lufs"] - target
    if abs(diff) <= 1:
        notes.append(f"loudness OK ({m['integrated_lufs']:.1f} LUFS, target {target:g})")
    else:
        notes.append(f"{'turn down' if diff > 0 else 'turn up'} by about {abs(diff):.1f} dB to reach {target:g} LUFS")
    if m["true_peak_dbtp"] > peak:
        notes.append(f"true peak {m['true_peak_dbtp']:.1f} dBTP is above {peak:g}: add a limiter")
    else:
        notes.append(f"true peak OK ({m['true_peak_dbtp']:.1f} dBTP)")
    return notes

def main():
    p = argparse.ArgumentParser(description="Measure loudness of a finished video or audio file, and compare a voice stem with a music stem. Needs ffmpeg.")
    p.add_argument("file", nargs="?", help="Final mix (video or audio).")
    p.add_argument("--voice", help="Voice-only stem, to compare with --music.")
    p.add_argument("--music", help="Music-only stem, to compare with --voice.")
    p.add_argument("--target", type=float, default=-14.0, help="Integrated loudness target in LUFS (default -14).")
    p.add_argument("--peak", type=float, default=-1.0, help="True peak ceiling in dBTP (default -1).")
    p.add_argument("--json", action="store_true", help="Print JSON.")
    a = p.parse_args()
    if not a.file and not (a.voice and a.music):
        p.error("give a final mix, or both --voice and --music")

    report = {}
    if a.file:
        m = measure(a.file)
        report["mix"] = {**m, "notes": verdict(m, a.target, a.peak)}
    if a.voice and a.music:
        v, mu = measure(a.voice), measure(a.music)
        gap = v["integrated_lufs"] - mu["integrated_lufs"]
        if gap < 15:
            note = f"music is only {gap:.1f} dB under the voice: lower it by about {18 - gap:.1f} dB under speech"
        elif gap > 28:
            note = f"music is {gap:.1f} dB under the voice: it may disappear on phone speakers"
        else:
            note = f"voice sits {gap:.1f} dB above the music: a comfortable bed"
        report["stems"] = {"voice_lufs": v["integrated_lufs"], "music_lufs": mu["integrated_lufs"], "gap_db": round(gap, 1), "note": note}

    if a.json:
        print(json.dumps(report, indent=2))
        return
    if "mix" in report:
        m = report["mix"]
        print(f"Mix: {m['integrated_lufs']:.1f} LUFS integrated, {m['true_peak_dbtp']:.1f} dBTP true peak, {m['loudness_range_lu']:.1f} LU range")
        for n in m["notes"]:
            print(f"- {n}")
    if "stems" in report:
        s = report["stems"]
        print(f"Voice {s['voice_lufs']:.1f} LUFS, music {s['music_lufs']:.1f} LUFS")
        print(f"- {s['note']}")

if __name__ == "__main__":
    main()
