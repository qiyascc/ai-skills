---
name: "cut-point-finder"
description: "Find frame-exact cut points in clips the way master editors do (just before a blink, at the end of a line, when an exit becomes inevitable, on a motion peak) and export them as markers for Resolve, Premiere or any NLE."
---

# Cut Point Finder

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

"Where exactly do I cut?" is the oldest question in the cutting room. Masters answer it with a few reliable signals. This skill measures those signals in the footage and proposes frames, with the reason for each, so the editor decides faster and with evidence.

Reply in the user's language.

## 0. The craft behind it
- **The blink** (Walter Murch): a blink is the mind's own cut, the moment one thought ends. When an actor is in character, the right cut usually falls one or two frames *before* the blink. Sometimes, for drama, just after it.
- **End of the line**: a pause after a sentence is a finished thought; cutting into the pause feels natural, cutting inside a word feels wrong.
- **The inevitable exit** (Murch): do not wait until someone has left the frame or the door has closed. Cut at the frame where it becomes inevitable.
- **Cut in movement** (Edward Dmytryk): motion hides the cut and carries the eye across it.
- **Cut long when unsure** (Dmytryk): pick the later frame, trim later.
- **Dynamic trim**: play the shot at speed and hit the cut frame on the fly, then repeat; the frame you hit twice is usually right. Use the tool's candidates as the starting points for this test.

## 1. Setup
The script ships with this skill as `scripts/cutpoint.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/cutpoint.py tools/`. Needs numpy, opencv-python-headless, Pillow, ffmpeg. Face detection uses OpenCV Haar cascades; if they are not bundled with cv2 the script downloads them once from the OpenCV GitHub repo into `models/`.

`python3 tools/cutpoint.py find clip1.mp4 clip2.mp4 out [--top 3] [--tc-start 01:00:00:00] [--no-faces] [--sheet on|off]`

Outputs per clip: `<clip>_cuts.json` (all candidates), `<clip>_markers.edl` (Resolve marker EDL: blue blink, green line end, red exit, yellow action), `<clip>_sheet.jpg` (each suggested frame with -2 and +2 frames), plus `cuts.csv` and `report.md` for all clips.

## 2. Workflow
1. Ask which clips and whether the cut is an out-point (leaving A) or an in-point (entering B). Default: out-points.
2. Run `find`. Open the sheets with Read and check the frames yourself: is the actor in character, is the action really at its peak?
3. Report per clip the best 2-3 frames in timecode with plain reasons ("frame 78: 2 frames before her blink, right after the line ends"). When several signals agree in one candidate, say so: that is the strongest cut.
4. Give the marker file and the import path: Resolve: right-click the timeline or clip > Timelines > Import > Timeline Markers from EDL. Premiere and others: use cuts.csv as a cue sheet. Set `--tc-start` to the timeline start (often 01:00:00:00) when markers go onto a timeline.
5. Hand over to **split-edit-builder** when the cut is between dialogue shots, and to **rule-of-six-judge** once the cut is in the edit.

## 3. Rules
- The tool proposes, the editor decides. Emotion beats every signal: a perfect blink cut in the wrong emotional moment is still wrong.
- Blink detection needs a visible, reasonably frontal face. With no face the report says so and relies on sound and motion.
- Never claim the tool knows the "right" frame. Say which evidence supports it.
