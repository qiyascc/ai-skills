---
name: "grade-critic"
description: "Check a photo, a set of photos or a video grade like a colorist's scopes (waveform, RGB parade, vectorscope with skin line, histogram) and report clipping, crushed blacks, colour casts, skin-tone errors, saturation and set consistency with concrete fixes."
---

# Grade Critic

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Eyes adapt and phone screens lie. Scopes do not. You measure the grade, show the scopes, and say exactly what to fix and by how much.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/critic.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/critic.py tools/`. Needs numpy, Pillow, opencv-python-headless, ffmpeg (video).
`python3 tools/critic.py check a.jpg b.jpg clip.mp4 crit [--every 1.0] [--style natural|film|bright] [--skin-target 123]`
Outputs `crit/report.md`, `report.json` and one `scopes_NNN.jpg` per image/frame (image with clipped areas in red and crushed areas in blue, luma waveform, RGB parade, vectorscope with the skin line, histogram).

## 2. What it measures and the targets
| Measure | natural | film | bright |
|---|---|---|---|
| black point (1st percentile luma) | 0.02-0.08 | 0.03-0.12 (lifted, printed blacks) | 0.02-0.10 |
| white point (99th percentile) | 0.88-0.98 | 0.80-0.95 (rolled highlights) | 0.90-0.99 |
| median level | 0.38-0.52 | 0.36-0.50 | 0.45-0.60 |
| contrast (p95-p5) | 0.45-0.80 | 0.40-0.75 | 0.40-0.75 |
Plus: clipped highlights (> 1% flagged), crushed blacks (> 2%), colour cast in neutral pixels (Lab a/b distance > 4), saturation (mean chroma, extreme pixels), skin hue angle vs the skin line (vectorscope ~123 deg; flagged beyond +-10 deg; only when skin-coloured pixels are a plausible share of the frame, walls and wood are ignored), highlight and shadow tints, and across a set: exposure, contrast, saturation and white-balance outliers.
Choose `--style film` when the user wants a film look (lifted blacks and soft whites are intended there, not errors).

## 3. Workflow
1. Run `check` on everything that belongs together (all photos of a listing, frames of a video every 1 s).
2. Open the lowest-scoring scopes sheets (Read tool) and confirm the tool's findings visually before reporting.
3. Report: overall verdict, set consistency first (outliers by name), then per image the 1-3 most important fixes in plain language with numbers ("lower highlights about 1/3 stop", "remove yellow cast: b* +6 in neutrals").
4. Offer the fix: **listing-photo-grader** for property sets, **film-lab** or **reference-matcher** for looks, **show-look-builder** for cross-camera consistency; then re-check and show the score change.
