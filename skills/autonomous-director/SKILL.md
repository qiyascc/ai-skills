---
name: "autonomous-director"
description: "Run any video render in a closed render-check-fix loop: a spec-driven quality gate (resolution, duration, black/frozen frames, silence, loudness, reference checkpoints, expected text, UI zones, seamless loop) that iterates until everything required passes."
---

# Autonomous Director

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Rendering is easy; finishing is hard. You never hand over a video that has not passed a written quality gate. You turn the brief into checks, render, check, fix the exact failures, and repeat until it passes or a stop condition is hit, keeping a log the user can read.

Reply in the user's language.

## 0. Setup
The script ships with this skill as `scripts/director.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/director.py tools/`. Needs ffmpeg, numpy, Pillow; tesseract for text checks.
- `python3 tools/director.py init check.json --w 1080 --h 1920 --fps 30 --dur 15`
- `python3 tools/director.py check check.json out.mp4 --iter 1 --log loop_log.md` (exit 0 = pass, 1 = fail)

## 1. Build the gate from the brief
Edit check.json: keep only checks that matter for this video.
- format: width, height, fps, duration (+ tolerance), max size
- integrity: no black frames, max frozen stretch, max silence
- audio: LUFS target (-13 social, -14 YouTube), true peak max
- look: checkpoints = timestamps + reference stills (approved stills from the render skills, or frames from a reference via **motion-reverse-engineer**), min structure/colour
- content: expect_text at times (prices, phone numbers, slogans), UI safe zones for the platform
- loop: first frame must match the last when the brief asks for a loop

## 2. The loop
1. Render (with **motion-render-pro**, **listing-to-reel**, Remotion, HyperFrames, ffmpeg, anything).
2. `check`. If PASS: deliver.
3. If FAIL: fix only what failed, using the fix hints (timing: the checkpoint check says if an event is early or late; loudness: remaster; black frames: scene ranges). Change one cause at a time, re-render (draft resolution for timing fixes, full for final), re-check with `--iter N`.
4. Stop conditions: PASS; 5 iterations; the same failure twice with no progress (then report the blocker and ask); or a fix that needs the user's taste.
5. For high-stakes deliveries, run a final independent review with a fresh agent (subagent) that sees only the brief, check.json and the video, not your reasoning.
6. Deliver the video with the loop log summary: iterations, what was fixed, warnings left on purpose.

## 3. Notes
- WARN items (frozen stretches, silence, UI zones, file size) do not block, but mention them.
- OCR is strict: a failed text check can mean low contrast or busy background; that is a real readability problem, fix it rather than lowering the bar.
