---
name: "taste-genome"
description: "Learn which editing and style choices actually perform for this creator by measuring style features across their published videos and correlating them with their real stats (views, saves, watch time), then turn the winners into edit rules."
---

# Taste Genome

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

You find the creator's personal "style DNA": not generic best practices, but what separates their own top videos from their weakest ones, measured. Then you turn it into rules every future edit follows.

Reply in the user's language.

## 0. Setup
The script ships with this skill as `scripts/genome.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/genome.py tools/`. Needs ffmpeg, numpy, opencv-python-headless; tesseract optional (`--ocr` adds on-screen text ratio, slower).
- `python3 tools/genome.py extract videos/ features.csv [--ocr]`
- `python3 tools/genome.py learn features.csv metrics.csv genome --metric saves --metric avg_watch_pct`

## 1. Collect inputs
- **Videos:** the exported originals of published posts (8 minimum, 20+ to trust). Same platform, similar format if possible.
- **metrics.csv:** `file` column matching the file names + numeric columns. Best metrics: saves, shares, avg watch %, follows from post. Views alone mostly measure distribution luck. If the user sends screenshots of insights, read the numbers and build the CSV yourself, then show it for confirmation.

## 2. Features measured per video
duration, cuts per second, average shot length, time to first cut, time to first motion, motion energy, brightness, saturation, warmth, contrast, face presence (when the OpenCV build has the face model), on-screen text ratio (`--ocr`), loudness, audio start, music BPM.

## 3. Read the result honestly
1. Open `genome/genome.md`. For each metric it shows the features that most separate the top third from the bottom third (median values, rank correlation, effect size in standard deviations).
2. Translate into 3-5 creator-language rules, e.g. "Your saved videos cut every 1.3 s, your weak ones every 2.8 s" or "Warmer colour grades get 2x saves".
3. Always state reliability (number of videos) and that correlation is not cause: frame each rule as a test for the next posts.
4. Look for confounders before claiming anything: a viral outlier, a different topic, a collab, paid boost. Re-run without outliers if one video dominates.

## 4. Make it operational
- Save the rules to `STYLE_DNA.md` (and `genome.json`) next to the user's projects; tell **reels-edit-director**, **motion-story-director** and **listing-to-reel** to follow it (pacing, hook timing, grade).
- Re-run monthly with new posts; keep a changelog of which rules held.
