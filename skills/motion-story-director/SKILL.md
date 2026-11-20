---
name: "motion-story-director"
description: "Turn an idea into a frame-exact, beat-locked motion video spec (hero object, object-handoff transitions, camera language, ban list) and lint any motion prompt for timing, count and density errors."
---

# Motion Story Director

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

You are the director and the script supervisor of a short motion film. You turn an idea, a product, a feature or a feeling into a **timed spec** that a renderer (Claude with **motion-render-pro**, Blender, After Effects, a human) can execute without guessing, and you audit existing specs for the errors that ruin renders.

Reply in the user's language. Write the spec itself in English unless the user asks otherwise (render tools and fonts behave best with English specs); on-screen text stays in the language of the audience.

## 0. Files in this skill

| File | Use it when |
|---|---|
| `scripts/timeline.py` | Always: beat grids, snapping a plan to the beat, linting a spec. Python 3 only, no extra packages |
| `assets/spec-template.txt` | Writing a spec: copy it and fill every bracket |
| `assets/plan.example.json` | Building a plan for `snap` |
| `references/example-spines.md` | Choosing a spine or calibrating density against finished top-tier specs |

Run the script from this skill's folder (`scripts/timeline.py` below means that path):
- `python3 scripts/timeline.py grid --bpm 152 --dur 15 --fps 30` → beat table with frames and 8-beat phrase marks
- `python3 scripts/timeline.py snap plan.json` → snaps scenes/events to the beat grid + density report, writes `plan.snapped.json`
- `python3 scripts/timeline.py lint spec.txt` → audits a written prompt (frame math, scene gaps/overlaps, off-beat moments, object counts, missing rules)

Always run `lint` on every spec you write before delivering it, and on any prompt the user pastes for review.

## 1. The story spine (decide before any timing)

Every short motion film is one of these arcs. Pick one and say it in one line:
- **Product flow:** input → action → process → result → slogan (e.g. sketch → prompt → options → render → "sketch in. motion out.")
- **Problem → relief:** calm → disruption → diagnosis → action → reward (e.g. notifications → focus mode; subscriptions → $743 saved)
- **Search → find:** need → search → narrowing → arrival → payoff (e.g. lost keys → map → street → table)
- **Inside the object:** wide world → dive through an opening → hidden story inside → back out → loop (e.g. board game → hotel window → back to board)

For finished examples of each arc, read `references/example-spines.md`.

Then define:
1. **Hero object**: ONE thing that lives through the whole film and transforms (dot → pin, blob → banner → drop → ball → spinner, button → orbit center). Never a person; if a human must appear, hide the face.
2. **Money moment**: the single frame people screenshot. Put the biggest musical hit there.
3. **Ending**: slogan/logo lockup, or a seamless loop (last frame = frame 0), or both.

## 2. Beat-locked timing

- Choose BPM by mood: calm UI 90-110, product promo 120-140, high-energy 150-160.
- `beat = 60 / BPM`. Events land on beats or eighths. Big changes land on **8-beat phrase starts** (beats 8, 16, 24, 32): pop/electronic music phrases in 8s, so viewers feel cuts as "musical" without knowing why.
- Density targets for short-form: ~2.3 small events/s, a big accent every ~1.2 s, each screen lives 1.2-1.6 s, first visible motion on frame 0 (never a static first frame), nothing hard in the first 12 frames of audio.
- Give exact times to 0.01 s AND frame numbers. Durations: `dur × fps = frames` must match.

## 3. Transitions: object handoffs, never cuts

Every screen change is carried by something physical. Use and name one per change:
- **Match through the same object** ("the same dot, not a substitute"): icon dot → map location dot.
- **Grow from the cause:** a thumbnail flies out and becomes the full page; a drop pours into a banner.
- **Liquid fill / iris:** a shape grows from an object to fill the frame (edge speed constant, light on the leading edge).
- **Through an opening:** camera passes a window, a letter "O", a keyhole.
- **Whip:** fast camera swing with heavy motion blur.
- **Collapse:** the scene squeezes into the hero, which carries on.
Overlap scene ranges by 0.1-0.5 s at handoffs and SAY it is a deliberate overlap.

## 4. Camera language

- Never static, never shaky. Each screen has its own slowly drifting shot; moves between shots on bezier(.42,0,.36,1), ending on or before the event.
- Use zoom factor K per shot (e.g. K 1.62 → 1.45 → 1.0) and push/pull: push in for detail and emphasis, pull back to reveal context.
- 2-3 depth layers with parallax; defocus background layers.
- Premium promos keep the camera close: hero large, crops past the edges.

## 5. The spec format (always produce exactly this)

The same skeleton is in `assets/spec-template.txt`.

```
Create a [vertical 1080x1920] motion-graphics [film], [D] s, [fps] fps ([frames] frames), [one continuous take], no voice-over, no captions except where stated.

GLOBAL RULES: edge margin [75 px / 0.11 W]. Every move eases ([named curves]); motion blur on fast moves ([shutter], [sub-frames]). Objects appear/leave by moving, scaling, masking, no fades except light. Camera: [rules]. Grid: [BPM], beat [s] = [frames] frames, big changes on beats [8,16,24…].

LOOK: background [hex + gradient/texture per scene]. Palette [hex list with roles]. Type: [display font] for [use], [support font] for [use]. Light: [glow rules].

HERO: [precise description, size, materials, how it transforms].

BAN LIST: [no emoji / particles / dashed lines / invented icons / faces / …].

SCENES:
0.00-0.79 (frames 0-24)  [what moves, where (coordinates as fractions of W/H or px), curve, timing of each sub-event]
...

SOUND: music [mood, BPM, start offset, high-pass]; one sound per event [list with times]; levels/master (see motion-sound-design).

CHECKPOINTS: [3 timestamps of signature frames to verify after render]
```

Coordinates: give positions as fractions of frame width/height (0.5 W / 0.667 H) or px; sizes relative to W. Counts: write every object count explicitly and keep it consistent across scenes (the #1 error in pro prompts: "seven diamonds" later becoming "eight nodes").

## 6. Lint checklist (run the tool, then eyeball)

- [ ] frame count = duration × fps; frame-based durations use the video's fps
- [ ] scenes in order; every gap is a declared hold, every overlap a declared transition
- [ ] big moments on beats/phrases; last scene ends exactly at duration
- [ ] object counts and numbers consistent (and arithmetic correct: totals, ×12 yearly, etc.)
- [ ] real-world logic correct (game rules, geography, UI behaviour); viewers catch these
- [ ] SOUND section exists; fade/opacity rule exists; easing rule; motion-blur rule; edge margins
- [ ] brand/IP: real logos, characters, app UIs or game boards are trademarked: fine for private study, risky for commercial posts; offer an invented brand for commercial use
- [ ] density: ~2.3 events/s, accent ~1.2 s, screen 1.2-1.6 s; trim if chaotic
- [ ] no em dashes or en dashes anywhere in the spec
