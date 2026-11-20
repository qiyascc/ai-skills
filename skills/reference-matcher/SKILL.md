---
name: "reference-matcher"
description: "Measure the look of a reference frame or photo (tone curve, black/white points, palette, per-hue saturation, split-tone tints, grain, halation) and build a LUT that moves the user's image toward it, with an honest before/after similarity report."
---

# Reference Matcher

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

People say "make it look like this frame". You measure that frame, transfer what can be transferred, and tell the truth about what cannot. A 1:1 copy of another image's look does not exist: lighting, lens and scene contrast are not in a LUT.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/refmatch.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/refmatch.py tools/`. Needs numpy, Pillow, opencv-python-headless.
- `python3 tools/refmatch.py measure ref.jpg fp` look fingerprint (fp/fingerprint.md, .json, .png)
- `python3 tools/refmatch.py build ref.jpg target.jpg look.cube [--strength 1] [--tone 1] [--color 1] [--size 33] [--preview prev.jpg]`
- `python3 tools/refmatch.py apply photo.jpg look.cube out.jpg [--strength 0.8]`
A folder as REF pools several frames into one look (better than a single frame).

## 2. What is measured and transferred
| Part | Measured | Transferred by |
|---|---|---|
| tone | luminance distribution, black/white points, contrast | quantile matching of L*, smoothed and kept monotonic |
| balance | median a*/b* | global shift (80%) |
| palette | 12 hue sectors: share, median chroma, mean hue | per-hue chroma scale (0.5-1.8x) and hue rotation (max 25 deg), smoothly interpolated, neutrals protected |
| split tone | a*/b* of neutral shadows, mids, highlights | residual tints |
| texture | grain (high-pass std in flat areas), halation hint (warm ring around highlights) | not by a LUT: add with **film-lab** |

## 3. Workflow
1. `measure` the reference and describe its look in words from the fingerprint: contrast, where blacks sit, palette, split tone, grain, halos.
2. `build` with the user's image as target and `--preview`; show the preview next to the reference.
3. Read the report: similarity before/after (L, a, b histogram overlap, 1.0 = identical distributions) and the WARNINGS (hues the reference has and the target does not: say clearly that those parts of the look cannot transfer).
4. Tune with `--tone`, `--color`, `--strength` (0.6-0.8 often looks more natural than 1.0). For a series, build from the most typical image and apply the same cube to all.
5. Add texture (grain, halation) with **film-lab** if the fingerprint shows it; verify with **grade-critic**.

## 4. Ethics and rights
Matching the look of a film frame for your own work is normal practice. Do not reproduce the reference image itself, and do not imply the result is the original film or a specific photographer's work.
