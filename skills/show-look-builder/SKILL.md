---
name: "show-look-builder"
description: "Build one signature look for a whole project or brand across every camera (phones, mirrorless, log cameras, drones): profile and normalise each camera, compose the look per camera into one LUT each, verify consistency, and write a look bible."
---

# Show Look Builder

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Big productions use one show look for every camera: normalise each camera to a common baseline, then apply the same look to all of it (the display-prep idea Steve Yedlin, ASC demonstrates: one transform, not shot-by-shot fiddling). You build that for a brand, so every photo and video is recognisably theirs.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/lookbuilder.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/lookbuilder.py tools/`. Needs numpy, Pillow, opencv-python-headless. The look itself comes from **film-lab** (`filmlab.py lut`) or **reference-matcher** (`refmatch.py build`).
- `python3 tools/lookbuilder.py profile CAM samples/ show --input srgb|rec709|slog3|logc3|vlog [--grey x,y,w,h] [--match-to show/other.json] [--keep-warmth 0.3]`
- `python3 tools/lookbuilder.py build LOOK show --cams show/a.json,show/b.json --look look.cube [--look-strength 1]`
- `python3 tools/lookbuilder.py check show --pairs show/a.json:a.jpg,show/b.json:b.jpg --look LOOK`
- `python3 tools/lookbuilder.py bible LOOK show --brand "Brand" --notes "..."`

## 2. Workflow
1. **Inventory cameras**: every device that produces content (iPhone, Samsung, Sony with S-Log3, drone...). For each, collect 5-15 typical frames/photos (export frames as JPG/PNG for video). Know each input encoding.
2. **Profile** each camera. Best: a frame with a grey card (`--grey x,y,w,h` of the card) = accurate white balance and exposure. Without a card the tool estimates from neutral pixels and keeps 30% of the scene's own warmth (grey-world over-corrects warm rooms). Use `--match-to` to equalise saturation and white balance to the main camera (without a grey card the second camera is pulled to the main camera's neutral, so profile both from the same scene or the same kind of light).
3. **Design the look** once (film-lab contact sheet, or reference-matcher from brand references). Export it as a cube with sRGB input.
4. **Build**: one cube per camera = normalise + look. Check with `check`: spread of exposure, balance and saturation before vs after must drop; show the consistency sheet.
5. **Bible**: write the look bible (files, install steps for Lightroom/Photoshop, Resolve, Premiere, Final Cut, CapCut, ffmpeg, and shooting rules). Deliver the folder.
6. **Gate**: run **grade-critic** on 5 frames per camera with the look applied.

## 3. Rules
- Lock white balance per scene when shooting; the normaliser is not a cure for mixed auto-WB clips inside one scene.
- Never stack a manufacturer LUT before the camera cube.
- Re-profile after firmware, picture profile or major lens changes.
