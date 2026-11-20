---
name: "split-edit-builder"
description: "Turn hard dialogue cuts into J-cuts and L-cuts (Dede Allen's sound overlaps) from an edit list and the source clips' handles, fill holes with room tone, and render the result plus a CMX3600 EDL with separate picture and sound events."
---

# Split Edit Builder

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Dede Allen (The Hustler, Bonnie and Clyde, Dog Day Afternoon) broke the habit of cutting sound and picture together: she let the next scene's sound arrive early or the last scene's sound linger. Today every dialogue scene is cut this way. A hard cut on every line feels like a slideshow; split edits make conversation flow.

Reply in the user's language.

## 0. The grammar
- **L-cut**: A is still talking, we cut to B listening. A's voice carries over B's face. Use it when the reaction matters more than the speaker's face.
- **J-cut**: B starts talking while we are still on A, then we cut to B. The voice pulls us into the next shot. Use it to move a scene forward or to bridge scenes.
- **Hard cut + 2-4 frame crossfade**: when both talk across the cut, or for impact.
- **Room tone**: every hole an overlap leaves gets the room's own quiet, never digital silence.
- Never cut a word in half. Never use media past a clip's real end. Never show a mouth moving with no sound.

## 1. Setup
The script ships with this skill as `scripts/splitedit.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/splitedit.py tools/`. Needs numpy and ffmpeg.
1. `python3 tools/splitedit.py init clips/ edit.json [--handle 0.5]` makes a starter edit list (clips in name order, trimmed by the handle at both ends so overlaps have media). Or write edit.json by hand from the user's cut: `{"fps": 25, "events": [{"clip": "a.mp4", "in": 1.0, "out": 4.2}, ...]}` (seconds in each source clip).
2. `python3 tools/splitedit.py plan edit.json out [--max-lead 20] [--max-lag 25]` writes plan.json and plan.md with a proposal and the reason for each cut.
3. `python3 tools/splitedit.py render edit.json final.mp4 --plan out/plan.json [--roomtone 1] [--xfade 3]` renders the video (picture length unchanged) and `final.edl` with separate V and A events for import into Resolve or Premiere.

## 2. How the proposals are made
| Situation at the cut | Proposal | How it is built |
|---|---|---|
| A talking at its out point, B silent at its head (listener) | L | sound cut rolls later until A's line ends (inside A's handle, max 25 frames) |
| B's line starts at its in point, A quiet | J | picture cut rolls later (we stay on A for up to 20 frames while B's voice starts), only where A is not speaking in that extra picture |
| both talking | hard | 3-frame crossfade |
| nobody talking | hard | free choice; prelapping ambience is a taste call |
Each overlap is limited so every shot keeps some of its own sound and picture.

## 3. Workflow
1. Get the cut as an edit list (or build one with `init`). If the user only has a flattened video, explain that split edits need the source clips with handles, or offer **rule-of-six-judge** to find cuts that click instead.
2. Run `plan`, show plan.md, and let the user override any row by editing plan.json (type J/L/hard, frames).
3. Render, then watch the cuts (or extract frames around them) and listen: no doubled words, no clicks, room tone continuous.
4. Deliver the video and the EDL, with the import path (Resolve: File > Import > Timeline > EDL; Premiere: File > Import, choose the .edl).
