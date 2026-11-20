---
name: "sticky-motion"
description: "Pin labels, callouts and graphics to objects in real footage with motion tracking (CSRT plus template re-anchoring and smoothing), so text like \"Sea view, 120 m²\" follows a balcony, product or person as the camera moves."
---

# Sticky Motion

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

After Effects users track points by hand to make graphics stick to footage. You do it from a sentence: find the object, track it, render a clean animated label that rides it.

Reply in the user's language.

## 0. Setup
The script ships with this skill as `scripts/sticky.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/sticky.py tools/`. Needs ffmpeg, numpy, Pillow, opencv-python-headless (CSRT tracker; if missing: `pip install opencv-contrib-python-headless --break-system-packages`).
- `python3 tools/sticky.py frame clip.mp4 0.0 pick.png --grid` still with a 100 px grid
- `python3 tools/sticky.py track clip.mp4 balcony.json --box x,y,w,h [--t 0] [--end 4] [--smooth 0.12]`
- `python3 tools/sticky.py render clip.mp4 out.mp4 --tracks balcony.json --label "Sea view" --sub "120 m²" [--style callout|pill|ring] [--color "#F0662B"] [--font path.ttf] [--side auto|left|right] [--in 0.3] [--out 0]`

## 1. Workflow
1. Render `frame --grid` at the moment the object is clearly visible and look at it (Read tool). Choose a tight box around a textured part of the object (corners, edges, signs track better than flat walls or sky). Write the box as x,y,w,h in pixels.
2. `track` from that time. Read the summary: lost % above 15 means a bad box (too flat, too big, occluded) or a cut inside the range: shorten `--end` to the shot, or pick a more textured box.
3. Spot-check: render `frame` at 2-3 times and compare with the track's `sx, sy` values in the JSON.
4. `render` with the label text in the audience language. Several objects: track each, then `--tracks a.json,b.json --label "A|B" --sub "x|y"`.
5. Deliver; add a pop SFX at label entry if sound is used (**motion-sound-design**).

## 2. Design rules built in
- Label pops in (115% then settle, no fade), leader line + ring on the object, stays inside 75 px margins, flips side automatically near the frame edge (and goes below the object near the top), shrinks away when tracking is lost.
- Keep labels short (max 3 words + a number). One label on screen at a time unless they are far apart.
- Use the brand accent colour; Azerbaijani/Russian/Turkish characters render with the default DejaVu font or any TTF passed with `--font`.
