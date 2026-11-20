---
name: "beat-snap-reeditor"
description: "Re-time an existing video edit so every cut lands on the music grid (beats, eighths, and 8-beat phrase starts for the biggest changes), using tiny speed changes, trims or holds, then render it with the music."
---

# Beat Snap Re-Editor

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Most edits are "almost" on the beat. Viewers feel the difference without knowing why. You take a finished edit plus its music, detect every cut, and move each one onto the grid without changing the order or the story.

Reply in the user's language.

## 0. Setup
The script ships with this skill as `scripts/beatsnap.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/beatsnap.py tools/`. Needs ffmpeg and numpy.
- `python3 tools/beatsnap.py plan edit.mp4 music.mp3 snap [--bpm 128] [--offset 0.12] [--music-start 31.5] [--max-speed 0.08] [--phrase-every 8]`
- `python3 tools/beatsnap.py render edit.mp4 music.mp3 snap/plan.json out.mp4`

## 1. Rules the planner follows
- Every cut moves to the nearest eighth note; the strongest visual changes (top 25% by cut strength) prefer the nearest 8-beat phrase start if it is within 0.6 s.
- A segment reaches its new length by a speed change within +-8% (invisible), else by trimming its tail or holding its last frame.
- No segment shorter than 0.25 s; order never changes; the end lands on a beat.

## 2. Workflow
1. Get BPM and the first downbeat. If the user knows the BPM, pass `--bpm`; detection can be half or double. If the music starts mid-track, pass `--music-start` (seconds into the track where the edit begins) and check `--offset` by listening for the first kick.
2. Run `plan`, read `snap/plan.md`: every cut, its target, the grid type and the shift. Sanity rules: shifts above 0.25 s mean the edit was cut to a different tempo; holds on talking shots will look frozen (prefer trims there).
3. Adjust by hand if needed (edit plan.json: targets/segments), then `render`.
4. Verify: open frames around 2-3 cuts and confirm the music hit lands on the first new frame. Then run **retention-oracle** (off-beat cuts should be 0).

## 3. When not to snap
- Dialogue cuts: words must not be clipped. Snap only cuts that sit in silence or on B-roll; keep speech cuts where they are (remove them from plan.json segments' adjustments).
- Very slow music (< 80 BPM): snap to beats, not eighths (`--phrase-every 4` and fewer moves).
