---
name: "motion-render-pro"
description: "Render pro-grade motion graphics videos (MP4) from code with true motion blur, frame-exact timing, no-fade rules, named easing curves and style-correct physics. Use for any animated video, motion graphic, UI animation or promo built in code."
---

# Motion Render Pro

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Studio-grade rendering standards for motion videos Claude builds in code. Default Claude animation (CSS transitions, linear/ease, opacity fades, no blur) looks like a website. These rules make it look like a film.

Reply in the user's language. This skill is the RENDER layer. For scene planning use **motion-story-director**, for audio **motion-sound-design**, for copying a reference video **motion-reverse-engineer**.

## 0. Files in this skill

| File | Use it when |
|---|---|
| `scripts/engine.mjs` | Every render: deterministic frames, sub-frame motion blur, easing, keyframes, beat grid, camera smoothing, typing, glow, masked text, ffmpeg output |
| `assets/scene-template.mjs` | Starting a new scene file |
| `assets/DESIGN.template.md` | Starting the project's `DESIGN.md` |

## Setup (once per project)

1. Make a project folder and copy the engine into it: `mkdir -p motion-tools && cp <this skill>/scripts/engine.mjs motion-tools/`. It must live inside the project so Node finds the project's `node_modules`. Do not edit the copy; scene code goes in its own file.
2. `cd` into the project, `npm init -y && npm i @napi-rs/canvas` (prebuilt, no system deps). ffmpeg must exist (`which ffmpeg`) for `render()`; `still()` works without it.
3. Copy `assets/DESIGN.template.md` to `DESIGN.md` and fill it (palette hex, fonts, hero object, motion vocabulary, ban list), and create `CLAUDE.md` with one line pointing to it, so the look survives across sessions.
4. Fonts: register real fonts with `GlobalFonts.registerFromPath(path, family)` from `@napi-rs/canvas` (download Google Fonts .ttf via npm `@fontsource/*` packages or ask the user). Never rely on a default serif/sans for the final.

If running inside a chat where Motion/Design artifact types exist and the user did not ask for an MP4 file, those artifact types may be the better delivery; this skill is for code-rendered MP4.

## 1. The 6 non-negotiables

1. **Every frame is a pure function of time.** `draw(ctx, t)` only. No timers, no `Math.random()` (use `rng(seed)`), no state carried between frames. This makes renders repeatable, frame-exact and blur-able.
2. **True motion blur.** Each output frame = average of N sub-frames across the shutter (default 180° = `shutter: 0.5`). Use 8 sub-frames for normal motion, 16-32 for fast whips; `subframes` can be a function of `t` so only fast sections pay. Liquid/shape edges evaluated per sub-frame stay sharp when still.
3. **No fades on objects or text.** Things enter and leave by moving, scaling from their cause, squeezing into a point, rolling out of a line mask (`maskedText`), being revealed by a shape, or leaving past an edge. Opacity is allowed only for light (glows, halos, bloom) and where the spec explicitly asks.
4. **Named easing only.** Never linear for anything visible (except constant spins). Pick from the vocabulary below and name it in the plan.
5. **The camera never stands still and never shakes.** Global camera = `smoothPath()` of keyframes (Gaussian sigma ≈ 0.16 s, ≤ 25 px/frame); accents live in objects, not in camera jolts.
6. **Approve a still before animating.** Render 2-4 key frames with `still()` at the signature moments, show them, get a yes, then render motion. After the render, extract the same timestamps again as checkpoints.

## 2. Easing vocabulary (all in `E`)

| Name | Use | Feel |
|---|---|---|
| `E.start` | objects that begin a move | jumps ~35% on the first moving frame, long brake |
| `E.drop` = bezier(.42,0,.25,1) | drops, crawls, travel | accelerate, peak 7-8%/frame, ~15 frames brake |
| `E.camera` = bezier(.42,0,.36,1) | camera moves between shots | finish on or before the event |
| `E.spread` | puddles, fills, expansions | accelerate to full, +10% overshoot, recoil |
| `E.push` | lists, stacks, conveyor | velocity 20u(1-u)³; overlap pushes so lists never stop |
| `E.spring(t, z, w)` | UI elements landing | small overshoot (z 0.6-0.8) |
| `E.critical(t, w)` | logos, coins, premium reveals | critically damped, no overshoot |
| `E.sine` | breathing, sways, loops | symmetric in-out |
| `pop(t, t0, fps, 1.18)` | badges, icons, checkmarks | 115-120% in 2-3 frames, settle in 7, no bounce |

Durations: most in/out moves 7-12 frames (0.23-0.4 s at 30 fps). Nothing appears or disappears in one frame.

## 3. Physics by style (never mix)

- **UI / graphic style:** pop, overshoot, squash 10-15% on landings, springs, liquid metaballs, light that blooms.
- **Photoreal / 3D style:** true gravity (y = ½gt²), every contact = impact + ONE small rebound, no squash, nothing scales from zero, rolling without slipping, paper with air drag (flutter, slide, never float). In Blender, use rigid-body / cloth sims or keyframe from these formulas; render with Cycles + denoiser, 180° shutter motion blur, f/2.8-style DOF focused on the guide object.

## 4. Light, glow and type

- Glow = additive halo to ~2.1 R (half strength at 1.2 R, gone by 2 R) using `glow()` (globalCompositeOperation 'lighter'). On white backgrounds additive light disappears; paint a large saturated soft spot BEHIND the object instead.
- Only light is transparent. Specular highlight top-left, faint fresnel rim for glossy objects.
- Typography: max 2 families; display (heavy/condensed or italic serif) for hero words, clean sans for support. Tight tracking on big numbers. iOS/system UI is never typed; it slides or rolls in whole.
- Typing: `typing()` gives per-letter jitter (0.55-1.45× avg, longer after spaces), each letter rises from its mask in 2 frames; caret solid 0.35 s after the last letter, then soft blink (`caret()`). New letters may arrive in accent colour and cool to white over ~6 characters.
- Odometers for numbers: digits on wheels under a hard mask, ≤ 0.5 digit per frame, ones land last.

## 5. Composition rules

- 1080×1920 vertical unless told otherwise; keep text/icons ≥ 75 px (or 0.11 W) from edges; Instagram UI zones: top ~250 px, bottom ~420 px, right ~120 px.
- Hero element large in frame; crops past the edges are good. 2-3 depth layers with parallax and defocus.
- Centre groups to the frame AND to each other.
- Ban list (default AI-slop): emoji, generic particles, pulse rings, dashed lines, outline icons, invented logos, stock "tech" glows everywhere, drawn people/faces. Allow only what the spec asks.
- Loops: when asked, the last frame must equal frame 0 (verify with motion-reverse-engineer `analyze` → first/last similarity > 0.95).

## 6. Workflow

1. Get or write the timed spec (motion-story-director).
2. Copy `assets/scene-template.mjs` to `scene.mjs` and build on it: constants (W, H, FPS, D, palette), `grid(bpm)`, camera `smoothPath`, one function per scene, a `draw(ctx,t)` that dispatches by time and handles overlaps for transitions.
3. `still()` at signature moments (`node scene.mjs --stills` with the template) → show → approve.
4. Draft render: half resolution, `subframes: 1`, `preset: 'ultrafast'` to check timing.
5. Final: full res, subframes 8 (fast parts 16-32), crf 16-18, `preset: 'veryfast'` (use 'slow' only if asked for best quality).
6. Mix audio with motion-sound-design and mux.
7. Checkpoints: extract frames at the planned timestamps and compare with stills/reference. Send the MP4 to the user.

Render cost guide (1080×1920, Node, single core): ~0.05-0.15 s per sub-frame for simple 2D. 15 s × 30 fps × 8 sub-frames ≈ 3600 sub-frames ≈ 3-9 min. Warn the user before >15 min renders; use the `from`/`to` frame range options to render in chunks and concat with ffmpeg if needed.

## 7. Minimal scene template

`assets/scene-template.mjs`: a background, a camera push on `E.camera`, an icon that pops on beat 1 and travels on `E.drop` with a glow. `node scene.mjs --stills` writes check frames, `node scene.mjs` renders `out.mp4` with 16 sub-frames during the fast move and 8 elsewhere.
