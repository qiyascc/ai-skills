---
name: "match-cut-finder"
description: "Find frames across a folder of clips that share shape, colour, position or motion and render seamless match-cut transitions between them (hard cut, whip or aligned morph), so raw footage cuts like a commercial."
---

# Match Cut Finder

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

A match cut joins two different shots through something they share: a round door handle becomes a steering wheel, a turning head continues as a turning car, a bright window becomes a sunrise. Editors spend hours hunting these. You find candidates in seconds, show them, and render the chosen ones with the subject aligned.

Reply in the user's language.

## 0. Setup
The script ships with this skill as `scripts/matchcut.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/matchcut.py tools/`. Needs ffmpeg, numpy, Pillow, opencv-python-headless.
- `python3 tools/matchcut.py find clips/ mc --top 12 [--step 0.2] [--mode any|tailhead]`
- `python3 tools/matchcut.py render A.mp4 tA B.mp4 tB out.mp4 [--style cut|whip|morph] [--pre 1.2 --post 1.5] [--w 1080 --h 1920]`

## 1. How matches are scored
Weighted 0-1: **shape** (Hu moments of the main silhouette, ignoring floor/sky that touch the frame edge), **colour** (HSV histogram), **position** (subject centroid), **size**, **motion** (optical-flow direction: continuing a movement is the strongest match), **brightness**. `strongest` in the report says why a pair matched.

## 2. Workflow
1. Put the clips in one folder. `--mode tailhead` only pairs the last 1.5 s of one clip with the first 1.5 s of another (good when clip order is fixed); `any` searches everywhere (good when building a montage).
2. Run `find`, open `mc/sheet.jpg` (Read tool) and judge the pairs with your eyes: keep pairs that a viewer would read as one continuous thing. Discard pairs that only match on flat colour.
3. For each chosen pair pick a style:
   - **cut**: invisible join, B is shifted so its subject lands where A's was, then eases to centre over 0.5 s. Best for shape matches.
   - **whip**: 4-frame directional slide + blur. Best when both shots move the same way.
   - **morph**: 6-frame aligned blend. Best for colour/light matches (window to sun).
4. `render` each transition, check it frame by frame around the cut, then assemble (ffmpeg concat) or hand the timestamps to the main edit.
5. Use 1-3 match cuts per short video: they are signature moments, not every cut.

## 3. Tips
- Shoot for it: same subject size and position in frame across scenes multiplies good matches.
- Motion continuity beats shape: a hand moving right into a car moving right reads as one gesture.
- Put the match cut on a strong beat (see **beat-snap-reeditor**) and give it a sound (whoosh or a matched sound, see **motion-sound-design**).
