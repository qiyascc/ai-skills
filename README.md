# AI agent skills for Claude Code, Codex and Cursor

Free, open source agent skills by [Qiyas CC](https://qiyas.cc/). Each skill is a folder in `skills/<name>/` with a `SKILL.md` and, sometimes, scripts and reference files. They follow the open [Agent Skills](https://agentskills.io) format, so the same folder works in Claude Code, Codex, Cursor, OpenCode and other agents that read it.

Browse them with full descriptions at [qiyas.cc/ai-skills](https://qiyas.cc/ai-skills/).

## Skills

| Skill | Folder | What it does |
| --- | --- | --- |
| [Reels Edit Director](https://qiyas.cc/ai-skills/reels-edit-director/) | [`reels-edit-director`](skills/reels-edit-director) | Turn a Reel, TikTok or Shorts script into a timestamped edit plan and a copy-paste brief for your editor: fonts, colour breaks, music, sound effects and motion, with restraint. |
| [Reels Music Picker](https://qiyas.cc/ai-skills/reels-music-picker/) | [`reels-music-picker`](skills/reels-music-picker) | Pick music for short videos by mood, land your cuts and reveals on the beat, set the levels under your voice, and know what your account is allowed to use. |
| [Motion Story Director](https://qiyas.cc/ai-skills/motion-story-director/) | [`motion-story-director`](skills/motion-story-director) | Turn an idea into a frame-exact, beat-locked spec for a short motion film, with a hero object, object-handoff transitions and camera moves, and lint any motion prompt for timing and count errors. |
| [Motion Render Pro](https://qiyas.cc/ai-skills/motion-render-pro/) | [`motion-render-pro`](skills/motion-render-pro) | Render motion graphics to MP4 from code with true motion blur, frame-exact timing, named easing, no fades on objects and physics that match the style. |
| [Motion Sound Design](https://qiyas.cc/ai-skills/motion-sound-design/) | [`motion-sound-design`](skills/motion-sound-design) | Give every visual event its own sound, keep the music clean under it with band-limited micro-ducking, and master to -13 LUFS, with a built-in UI sound synthesizer and mixer. |
| [Motion Reverse Engineer](https://qiyas.cc/ai-skills/motion-reverse-engineer/) | [`motion-reverse-engineer`](skills/motion-reverse-engineer) | Measure a reference video (cuts, accents, BPM, palette, loop) and write a timed spec to recreate it, then score your render against it at checkpoints. |
| [Retention Oracle](https://qiyas.cc/ai-skills/retention-oracle/) | [`retention-oracle`](skills/retention-oracle) | Predict where viewers will swipe away before you post: hook timing, dead stretches, shot length, text overload, UI zones, silence, loudness and off-beat cuts, as a score with timestamped fixes. |
| [Beat Snap Re-Editor](https://qiyas.cc/ai-skills/beat-snap-reeditor/) | [`beat-snap-reeditor`](skills/beat-snap-reeditor) | Move every cut of a finished edit onto the music grid with tiny speed changes, trims or holds, without changing the order or the story, then render it with the music. |
| [Match Cut Finder](https://qiyas.cc/ai-skills/match-cut-finder/) | [`match-cut-finder`](skills/match-cut-finder) | Find frames across your clips that share shape, colour, position or motion, and render match cuts with the subject aligned, as a hard cut, a whip or a short blend. |
| [Sticky Motion](https://qiyas.cc/ai-skills/sticky-motion/) | [`sticky-motion`](skills/sticky-motion) | Pin labels and callouts to objects in real footage with motion tracking, so a line like Sea view, 120 m² follows the balcony while the camera moves. |
| [Reel Localizer](https://qiyas.cc/ai-skills/reel-localizer/) | [`reel-localizer`](skills/reel-localizer) | Turn one video into many language versions with captions that are wrapped by real font width, resized, retimed for reading speed, highlighted and kept out of the platform UI. |
| [Listing to Reel](https://qiyas.cc/ai-skills/listing-to-reel/) | [`listing-to-reel`](skills/listing-to-reel) | Turn a property listing (photos, price, facts, location) into a beat-locked vertical Reel with camera moves, a rolling price, fact chips, a location pin and an agent end card. |
| [Autonomous Director](https://qiyas.cc/ai-skills/autonomous-director/) | [`autonomous-director`](skills/autonomous-director) | Run any video render in a render, check, fix loop against a written quality gate (format, black or frozen frames, silence, loudness, reference frames, expected text, UI zones, loop) until it passes. |
| [Taste Genome](https://qiyas.cc/ai-skills/taste-genome/) | [`taste-genome`](skills/taste-genome) | Measure the style of your published videos against their real stats and turn what separates your best posts from your weakest into edit rules, with honest limits on what the data can say. |
| [Film Lab](https://qiyas.cc/ai-skills/film-lab/) | [`film-lab`](skills/film-lab) | Run a photo or a video through a negative stock, a print stock and a film format, with halation, bloom and grain, and export the colour as a .cube LUT. |
| [Grade Critic](https://qiyas.cc/ai-skills/grade-critic/) | [`grade-critic`](skills/grade-critic) | Check a photo, a set or a video grade like a colorist's scopes do and get clipping, colour casts, skin tone errors and set consistency with concrete fixes. |
| [Listing Photo Grader](https://qiyas.cc/ai-skills/listing-photo-grader/) | [`listing-photo-grader`](skills/listing-photo-grader) | Grade all photos of a property listing in one pass: straight verticals, honest white balance, window pull, brightness and set consistency, with a before and after sheet. |
| [Reference Matcher](https://qiyas.cc/ai-skills/reference-matcher/) | [`reference-matcher`](skills/reference-matcher) | Measure the look of a reference frame or photo and build a LUT that moves your image toward it, with a before and after similarity report that says what could not transfer. |
| [Show Look Builder](https://qiyas.cc/ai-skills/show-look-builder/) | [`show-look-builder`](skills/show-look-builder) | Build one signature look for a project or a brand across every camera: profile and normalise each camera, make one LUT per camera, check consistency and write a look bible. |
| [Cut Point Finder](https://qiyas.cc/ai-skills/cut-point-finder/) | [`cut-point-finder`](skills/cut-point-finder) | Find frame exact cut points in your clips (just before a blink, at the end of a line, when an exit becomes inevitable, on a motion peak) and get them as Resolve markers. |
| [Master Editor](https://qiyas.cc/ai-skills/master-editor/) | [`master-editor`](skills/master-editor) | Run a whole edit as a twelve step project the way master film editors work, from brief and dailies to selects, cut points, sound, rhythm, review, screenings and lock. |
| [Rhythm Architect](https://qiyas.cc/ai-skills/rhythm-architect/) | [`rhythm-architect`](skills/rhythm-architect) | Measure the rhythm of an edit against the 1/f pattern of films that hold attention, find flat and metronomic stretches, compare with a reference and plan shot lengths. |
| [Rule of Six Judge](https://qiyas.cc/ai-skills/rule-of-six-judge/) | [`rule-of-six-judge`](skills/rule-of-six-judge) | Score every cut of a finished edit against Walter Murch's Rule of Six: rhythm, eye trace, screen direction and jump cuts measured, emotion and story judged by watching. |
| [Selects Builder](https://qiyas.cc/ai-skills/selects-builder/) | [`selects-builder`](skills/selects-builder) | Prepare raw footage like an assistant editor: still boards per scene, a technical read of every take, a selects reel ordered wide to tight and two-pass note sheets. |
| [Split Edit Builder](https://qiyas.cc/ai-skills/split-edit-builder/) | [`split-edit-builder`](skills/split-edit-builder) | Turn hard dialogue cuts into J-cuts and L-cuts from an edit list and the clips' handles, fill holes with room tone, and render the result with a CMX3600 EDL. |

## Install

From GitHub:

```
npx skills add qiyascc/ai-skills
```

From qiyas.cc:

```
npx skills add https://qiyas.cc
```

The command finds the agents on your machine (Claude Code, Codex, Cursor, OpenCode and more) and lets you pick the skills. Add `--skill <name>` for one skill and `-g` to install it for every project.

Every skill can also be downloaded as a zip from [qiyas.cc/ai-skills](https://qiyas.cc/ai-skills/). Unzip it into your agent's skills folder, for example `~/.claude/skills/<name>/`.

## License

MIT
