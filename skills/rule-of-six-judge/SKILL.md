---
name: "rule-of-six-judge"
description: "Score every cut of a finished edit against Walter Murch's Rule of Six: measure rhythm, eye trace, screen direction and jump cuts, show the weakest cuts as frame pairs, then judge emotion and story by watching."
---

# Rule of Six Judge

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Walter Murch ranks what makes a cut good: **emotion 51%, story 23%, rhythm 10%, eye trace 7%, two-dimensional plane of the screen 5%, three-dimensional space 4%**. Never give up emotion for story, story for rhythm, and so on down the list. Higher criteria can hide problems in lower ones, never the reverse. This skill measures the four bottom criteria with tools and makes you look, deliberately, at the top two.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/sixjudge.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/sixjudge.py tools/`. Needs numpy, opencv-python-headless, Pillow, ffmpeg.

`python3 tools/sixjudge.py judge edit.mp4 out [--worst 10] [--beat on|off] [--tc-start 01:00:00:00]`

Outputs `report.md`, `cuts.json`, `cut_NNN.jpg` for the weakest cuts (tail of A | head of B, yellow circle = where the eye was on A, also drawn on B; cyan = where the eye lands on B; red arrows = motion direction), `markers.edl`.

## 2. What is measured
| Criterion | Measured as | Typical fix |
|---|---|---|
| rhythm (10) | flash frames, shots far longer than the median, cut offset from the musical beat, audio level jump exactly at the cut (cut inside a word) | move the cut to the beat or a pause, 2-4 frame audio crossfade, trim the long shot |
| eye trace (7) | distance between attention at the end of A and the start of B (faces first, else spectral-residual saliency); searches trims of up to 6 frames that line the two up | trim as suggested, reframe B, or accept a deliberate jolt |
| 2D plane (5) | dominant motion direction reverses across the cut | check the 180-degree line, insert a neutral shot, or keep it if the reversal is the point |
| 3D space (4) | B nearly identical in framing to A (jump cut), face size change under 33% | change angle 30+ degrees or size, cut away, or own the jump cut as a style |
Emotion and story are not measured. The tool never pretends otherwise.

## 3. Workflow
1. Run `judge` on the whole edit (export a reference file first).
2. Open every `cut_NNN.jpg` of the weakest cuts with Read. For each, also judge **emotion** (is this the moment the feeling peaks or turns?) and **story** (does the cut add information or a question?). Where emotion and story are clearly served, tell the user to keep the cut even if the technical score is low: that is Murch's hierarchy.
3. Report: the 3-5 cuts that most need work, each with timecode, what is wrong in plain words, and the concrete fix (frames to trim, where to move it). Then the overall pattern (for example "most issues are off-beat cuts in the montage at 01:20-01:45").
4. Offer the next tool: **cut-point-finder** to find better frames, **split-edit-builder** for dialogue cuts that click, **rhythm-architect** when the problem is overall pace.

## 4. Rules
- Low technical score does not mean a bad cut; high does not mean a good one. Say this when presenting numbers.
- Cut detection can merge very fast cuts or miss soft dissolves; mention dissolves if you see them in the frames.
