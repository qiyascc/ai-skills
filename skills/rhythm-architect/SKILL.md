---
name: "rhythm-architect"
description: "Measure the rhythm of an edit (shot lengths, motion, loudness) against the 1/f pattern found in films that hold attention, find flat and metronomic stretches, compare with a reference film, and map a reference or Eisenstein pattern onto planned shot lengths."
---

# Rhythm Architect

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Cognitive psychologist James Cutting measured every shot in 150 popular films (1935-2005) and found that shot-length sequences have drifted toward a 1/f pattern, the same fluctuation found in human attention. A later study of 295 films found the same convergence in shot duration, scene duration, motion and loudness. Sergei Eisenstein named the tools a century earlier: metric montage (absolute lengths), rhythmic montage (lengths plus movement inside the frame), tonal and overtonal montage. This skill turns both into measurements and plans.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/rhythm.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/rhythm.py tools/`. Needs numpy, opencv-python-headless, Pillow, ffmpeg.
- `python3 tools/rhythm.py analyze cut.mp4 out`: rhythm.md, rhythm.json, rhythm.png (shot lengths, motion and loudness over time, flat zones in red)
- `python3 tools/rhythm.py compare cut.mp4 reference.mp4 out`: side by side, what to change in plain words
- `python3 tools/rhythm.py map reference.mp4|rhythm.json|none DURATION_S plan.json [--shots N] [--pattern ref|accelerate|decelerate|steady|wave]`: planned shot lengths (seconds and frames, exact total), plan.md and an EDL of planned cut markers

## 2. Reading the numbers
| Measure | Meaning |
|---|---|
| ASL, median, CV | average and median shot length, spread (under 0.3 = very even, reads mechanical unless intended) |
| alpha (shots, motion, loudness) | slope of the power spectrum: about 1 = variety at every scale (1/f), about 0 = random, negative = choppy back and forth, about 2 = slow drift with little local variety |
| metronomic run | 8 shots in a row of nearly equal length |
| flat zone | 6+ seconds of low motion and steady sound: attention will sag |
The shot alpha carries an uncertainty of about +-5/sqrt(shots) (about +-0.7 at 50 shots, +-0.3 at 300): under about 100 shots it is indicative only; say so and lean on the metronomic runs and flat zones.

## 3. Workflow
1. `analyze` the cut (or `compare` with a reference the user admires). Show rhythm.png.
2. Translate into editing language: where pace builds and releases, where it stalls, which runs are mechanical. Point to timecodes.
3. Plan: for a new edit or a re-cut, `map` the reference's shape onto the target duration, or use a pattern: accelerate (tension toward a climax, Eisenstein's metric acceleration), decelerate (landing, emotion), wave (build and release), steady (deliberate metric montage). Import the EDL markers to cut to the plan, then use **beat-snap-reeditor** if music should own the grid.
4. Never chase a number for its own sake: alpha near 1 is a description of films that hold attention, not a law. Story and emotion decide.
