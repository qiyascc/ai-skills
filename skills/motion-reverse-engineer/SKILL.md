---
name: "motion-reverse-engineer"
description: "Reverse-engineer a reference video, GIF or set of frames into a pro, timed motion prompt (scenes, palette, BPM, accents, transitions) and verify a render against the reference with checkpoint comparisons."
---

# Motion Reverse Engineer

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

The real skill behind top motion prompts: watch a finished video, measure it, and write a second-by-second spec precise enough to recreate it, then prove the recreation matches. This skill measures what can be measured with tools (timing, cuts, motion accents, palette, BPM, loop) and guides you to describe the rest (hero, transitions, camera, sound) in the house spec format.

Reply in the user's language. Output specs in English unless asked otherwise.

## 0. Files in this skill

| File | Use it when |
|---|---|
| `scripts/ref.py` | Measuring a reference video, pulling checkpoint frames, comparing a render with the reference |
| `assets/observation-sheet.md` | Writing down what the eyes see (section 2) before writing the spec |

`scripts/ref.py` needs ffmpeg/ffprobe, numpy, Pillow and scipy. Run it from this skill's folder:
- `python3 scripts/ref.py analyze ref.mp4 ref_out --every 0.5` → `report.md`, `report.json`, frames every 0.5 s + at scene changes, contact sheet
- `python3 scripts/ref.py frames ref.mp4 out 1.8 6.5 13.3` → exact checkpoint frames
- `python3 scripts/ref.py compare ref.mp4 mine.mp4 cmp 1.8 6.5 13.3` → side-by-side sheet + structure/colour scores per checkpoint

Inputs: a video file the user attaches, a downloaded file, or only still frames (then skip `analyze`, read the frames visually and ask for timestamps if they are not labelled). If a site blocks downloading, ask the user to attach the file.

## 1. Measure (tools)

Run `analyze`, then read `report.md` and LOOK at the contact sheet and key frames (Read tool on the images).
Collect:
- size, fps, duration, frame count
- scene changes (none = continuous take → transitions are object handoffs)
- motion accents (peaks of motion energy) and their beat positions → the event rhythm
- BPM + first beat (verify: accents should sit on beats/eighths; if they sit on every other beat, double/halve)
- palette hex with shares → background vs accent colours
- share of pixels that differ between the first and last frame (under 0.5% = designed loop)

## 2. Observe (eyes): answer these from the frames

Fill `assets/observation-sheet.md` as you go.

1. **Arc:** which spine (product flow / problem→relief / search→find / inside the object)?
2. **Hero:** what single object persists? List every form it takes, with times.
3. **Transitions:** for each scene change, which handoff (same-object match, grow-from-cause, liquid fill/iris, through an opening, whip, collapse)?
4. **Camera:** static drift, push, pull, orbit, dive, parallax layers? Zoom factors per shot (estimate from object sizes between frames).
5. **Type:** display vs support font style (serif italic, condensed grotesk, SF-like neo-grotesk), weights, colours, how text enters (typed, rolled from a mask, popped).
6. **Motion style:** UI physics (pop/overshoot/squash) or real physics (gravity, one rebound)? Motion blur visible? Fades used or not?
7. **Light & material:** glows, speculars, grain, DOF, render style (flat vector, soft 3D, path-traced photoreal).
8. **Sound:** if audio exists, list audible events (clicks, whooshes, chimes) with times; music mood.
9. **Ban list:** what the video conspicuously avoids (no people, no emoji, no particles…), write it down; it is part of the look.

## 3. Write the spec

Use the exact format from **motion-story-director** (GLOBAL RULES / LOOK / HERO / BAN LIST / SCENES with times + frames / SOUND / CHECKPOINTS). Add at the top:
"Create only the full-frame [W×H] animation. The reference shows the result inside a promotional layout; that layout is not part of the requested result." (when the reference is a collage/mockup).

Precision rules:
- every time to 0.01 s with frame numbers; positions as fractions of W/H; sizes relative to W
- every count explicit and consistent; every number cross-checked against the frames (prompts drift from their references: e.g. a spec said "32 m" while the reference showed "14 m")
- name easing curves and motion-blur settings (see motion-render-pro)
- pick 3 CHECKPOINT timestamps at signature moments (logo, money moment, ending)

Run `python3 scripts/timeline.py lint spec.txt` from **motion-story-director** before delivering.

## 4. Verify a render

After rendering (motion-render-pro), run `compare` at the checkpoints. Structure > 0.6 and colour > 0.9 = OK; otherwise open `compare.jpg`, name the drift (wrong position, colour, timing offset, missing element) and fix the spec or scene code. Timing drift test: compare ±0.1 s around a checkpoint; if a neighbour matches better, the event is early/late by that much.

## 5. Deliver

- The spec (as a file if long, e.g. `spec.txt`), the contact sheet, and a 5-line "what makes this work" summary (hero, rhythm, transitions, camera, sound).
- Respect IP: recreating a branded ad for study is fine; for commercial use, swap real logos/characters/UI for an invented brand and say so.
