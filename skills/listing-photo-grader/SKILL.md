---
name: "listing-photo-grader"
description: "Batch-grade real-estate photos to a consistent professional standard: vertical and keystone correction, honest white balance, window pull, brightness, clarity, set-wide consistency and an optional brand look, with a before/after sheet and a full edit report."
---

# Listing Photo Grader

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Property photos sell when they are bright, straight, true to colour and consistent across the listing. You grade a whole listing in one pass and document every change.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/listgrade.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/listgrade.py tools/`. Needs numpy, Pillow, opencv-python-headless.
`python3 tools/listgrade.py grade photos/ graded [--long 2048] [--brightness 0.18] [--warmth 0.35] [--hdr 0.7] [--clarity 0.4] [--verticals on|off] [--max-tilt 8] [--look brand.cube] [--look-strength 0.5] [--denoise 0] [--sharpen 0.4] [--consistency 0.7] [--quality 90]`
Outputs graded JPGs, `before_after.jpg`, `report.md`, `report.json`.

## 2. What happens to each photo
1. **Verticals**: near-vertical lines are detected; camera roll and converging verticals (keystone) are corrected with a perspective transform, then empty borders are cropped. Skipped automatically when lines disagree, tilt exceeds `--max-tilt`, or the crop would lose more than 40%.
2. **White balance** from neutral pixels, keeping `--warmth` (35%) of the room's own warmth: warm light sells, but yellow walls should not turn blue.
3. **Window pull**: exposure fusion of virtual -1/0/+1 EV versions, so rooms are bright and windows still show the view.
4. **Brightness**: median set to `--brightness` (0.18 linear = bright, airy interior) with a soft shoulder that protects windows.
5. **Clarity** on luminance only, optional denoise, light sharpening.
6. **Set consistency**: every photo is pulled 70% toward the set's median exposure and balance.
7. **Brand look** (optional): a cube from **show-look-builder**, **film-lab** (try ektar_100 + scan or 2393 at 0.3-0.5 for property) or **reference-matcher**, at a gentle strength.

## 3. Honesty rule (non-negotiable)
Only global tone, colour and geometry corrections. Never remove cracks, stains, power lines or neighbouring buildings, never replace skies or views, never add furniture or change room sizes. Misleading property images can be illegal and destroy trust. If the user asks for such edits, explain the risk and offer honest alternatives (better framing, reshoot at golden hour, clearly labelled "virtual staging" made separately).

## 4. Workflow
1. Collect all photos of one listing (exterior, rooms, views). Order is kept.
2. Run `grade`; open `before_after.jpg` (Read tool) and send it to the user.
3. Check with **grade-critic** (`--style bright`): clipped windows, colour cast, consistency.
4. Adjust per need: darker moody brand = `--brightness 0.14`; very mixed light = `--warmth 0.2`; lots of noise (night, phone) = `--denoise 0.5`.
5. Deliver the graded set; feed the best ones to **listing-to-reel** for the video.
