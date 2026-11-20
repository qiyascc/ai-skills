# AI skills

Skills for coding agents by [Qiyas CC](https://qiyas.cc/). Each skill is a folder in `skills/<name>/` with a `SKILL.md` and, sometimes, extra files.

## Skills

| Skill | Name | What it does |
| --- | --- | --- |
| [Reels Edit Director](skills/reels-edit-director) | `reels-edit-director` | Turn a Reel, TikTok or Shorts script into a timestamped edit plan and a copy-paste brief for your editor: fonts, colour breaks, music, sound effects and motion, with restraint. |
| [Reels Music Picker](skills/reels-music-picker) | `reels-music-picker` | Pick music for short videos by mood, land your cuts and reveals on the beat, set the levels under your voice, and know what your account is allowed to use. |
| [Motion Story Director](skills/motion-story-director) | `motion-story-director` | Turn an idea into a frame-exact, beat-locked spec for a short motion film, with a hero object, object-handoff transitions and camera moves, and lint any motion prompt for timing and count errors. |
| [Motion Render Pro](skills/motion-render-pro) | `motion-render-pro` | Render motion graphics to MP4 from code with true motion blur, frame-exact timing, named easing, no fades on objects and physics that match the style. |
| [Motion Sound Design](skills/motion-sound-design) | `motion-sound-design` | Give every visual event its own sound, keep the music clean under it with band-limited micro-ducking, and master to -13 LUFS, with a built-in UI sound synthesizer and mixer. |
| [Motion Reverse Engineer](skills/motion-reverse-engineer) | `motion-reverse-engineer` | Measure a reference video (cuts, accents, BPM, palette, loop) and write a timed spec to recreate it, then score your render against it at checkpoints. |
| [Retention Oracle](skills/retention-oracle) | `retention-oracle` | Predict where viewers will swipe away before you post: hook timing, dead stretches, shot length, text overload, UI zones, silence, loudness and off-beat cuts, as a score with timestamped fixes. |
| [Beat Snap Re-Editor](skills/beat-snap-reeditor) | `beat-snap-reeditor` | Move every cut of a finished edit onto the music grid with tiny speed changes, trims or holds, without changing the order or the story, then render it with the music. |
| [Match Cut Finder](skills/match-cut-finder) | `match-cut-finder` | Find frames across your clips that share shape, colour, position or motion, and render match cuts with the subject aligned, as a hard cut, a whip or a short blend. |
| [Sticky Motion](skills/sticky-motion) | `sticky-motion` | Pin labels and callouts to objects in real footage with motion tracking, so a line like Sea view, 120 m² follows the balcony while the camera moves. |
| [Reel Localizer](skills/reel-localizer) | `reel-localizer` | Turn one video into many language versions with captions that are wrapped by real font width, resized, retimed for reading speed, highlighted and kept out of the platform UI. |
| [Listing to Reel](skills/listing-to-reel) | `listing-to-reel` | Turn a property listing (photos, price, facts, location) into a beat-locked vertical Reel with camera moves, a rolling price, fact chips, a location pin and an agent end card. |
| [Autonomous Director](skills/autonomous-director) | `autonomous-director` | Run any video render in a render, check, fix loop against a written quality gate (format, black or frozen frames, silence, loudness, reference frames, expected text, UI zones, loop) until it passes. |
| [Taste Genome](skills/taste-genome) | `taste-genome` | Measure the style of your published videos against their real stats and turn what separates your best posts from your weakest into edit rules, with honest limits on what the data can say. |

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
