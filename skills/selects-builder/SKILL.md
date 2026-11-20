---
name: "selects-builder"
description: "Prepare raw footage like a top assistant editor: numbered still boards per scene, technical scoring of every take (focus, exposure, shake, faces, shot size, audio), a selects reel ordered wide to tight with slates, and two-pass note sheets."
---

# Selects Builder

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Before the first cut, master editors organise. Walter Murch pins four or five numbered stills of every setup on boards so the whole film is visible at a glance and his eye stays analytical. Kirk Baxter, David Fincher's editor, picks the best of everything and has it laid out per scene from wide to tight, then cuts every scene as if it were the only one. This skill does that preparation in minutes.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/selects.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/selects.py tools/`. Needs numpy, opencv-python-headless, Pillow, ffmpeg. Optional: faster-whisper or openai-whisper for transcripts (needs its model download; skipped silently when unavailable).

`python3 tools/selects.py build raw/ selects [--per-scene 2] [--max-sec 8] [--scene-by auto|name|look] [--transcribe auto|off]`

Outputs `boards/scene_X.jpg`, `selects.mp4`, `notes.md`, `notes.csv`, `takes.json`.

## 2. What it measures per take
| Measure | How | Flag |
|---|---|---|
| sharpness | Laplacian variance relative to brightness (a brighter take does not count as sharper), compared with the sharpest take of the same scene and shot size | under 60% = soft |
| exposure | median level, blown highlights, crushed shadows | over 3% blown, over 8% crushed, very dark or bright |
| stability | change of global camera motion over short full-rate bursts (whole-frame shift by phase correlation, so small moving subjects barely count) | shaky |
| faces and size | face share of frame: close over 8%, medium over 1.5%, else wide | used to order wide to tight |
| audio | speech share, level, clipping | clipping, very quiet |
Scenes come from names (S03_T02, sc3-tk2, 03A_2) or, when names carry no scene, from look (consecutive clips that look alike). The score weights sharpness 30, exposure 20, stability 20, audio 15, faces 15.

## 3. Workflow
1. Run `build` on the raw folder. Open the boards (Read) and send them to the user; they are the map of the material.
2. Explain the protocol: **pass 1** watch every take once without stopping and write only first impressions (Dmytryk: the first viewing should be emotional, not critical); **pass 2** rewatch the selected takes and write timecoded notes. notes.csv has both columns ready.
3. Present the selects reel and the technical reads. Make clear that the score is technical only: a soft take with the best performance beats a sharp dead one. Ask which performances the user loved and adjust the circled takes.
4. Next: assemble scene by scene, then **cut-point-finder** for transitions.
