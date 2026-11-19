###############
# Qiyas Sadıqov CC
###############
import argparse
import statistics
import sys
import time

def main():
    argparse.ArgumentParser(
        description="Estimate a track's BPM by tapping Enter on every beat while it plays. Type q and Enter to finish."
    ).parse_args()
    print("Play the track and press Enter on every beat. Type q and Enter to finish (8+ taps recommended).")
    taps = []
    for line in sys.stdin:
        if line.strip().lower() == "q":
            break
        taps.append(time.monotonic())
        if len(taps) >= 2:
            gaps = [b - a for a, b in zip(taps, taps[1:])]
            print(f"taps {len(taps)}: {60 / statistics.median(gaps):.1f} BPM", flush=True)
    if len(taps) < 4:
        sys.exit("Need at least 4 taps.")
    gaps = [b - a for a, b in zip(taps, taps[1:])]
    bpm = 60 / statistics.median(gaps)
    print(f"Estimated tempo: {bpm:.1f} BPM (half {bpm / 2:.1f}, double {bpm * 2:.1f}). Round to the nearest whole number for beat_grid.py.")

if __name__ == "__main__":
    main()
