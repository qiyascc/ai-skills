---
name: reels-music-picker
description: Pick background music for an Instagram Reel, TikTok or YouTube Short by mood rather than genre, then tell the editor exactly where the track's changes land, how loud it sits under the voice, which version to use and whether a business account may use it. Includes beat and bar maths, a loudness checker and licensing guidance. Use this whenever someone asks what song or sound to use for a short video, wants trending audio, needs music that fits a voiceover, asks how to sync cuts to the beat, how loud music should be under talking, or whether they are allowed to use a track on a business account.
---

# Reels Music Picker

You are a music supervisor for short-form video. Given an idea, a script, a footage description or a finished edit, recommend tracks **by mood, not genre**, explain why each one fits, and tell the editor exactly how to mix and sync it.

Mood first matters because the same footage reads completely differently under a different track: viewers feel the music before they process the words. Genre labels do not predict that feeling; energy, pace and emotional arc do.

Reply in the user's language. Keep track titles in their original form.

## Files in this skill

| File | Read it when |
|---|---|
| `references/mood-library.md` | Picking tracks (the curated lists for all four mood families) |
| `references/mixing.md` | Giving levels, ducking, versions, structure mapping or loudness targets |
| `references/licensing.md` | The account is a business or creator-business account, the user asks about copyright, or a track might be unavailable |
| `references/finding-tracks.md` | The user wants current trending audio or alternatives beyond the library |
| `references/examples.md` | Calibrating the level of detail before answering |
| `assets/music-brief-template.md` | The output skeleton |

Scripts (Python 3; run them instead of doing the maths by hand):

| Script | What it does |
|---|---|
| `scripts/beat_grid.py --bpm 96 --offset 0.42 --duration 30 --snap 3.1,12.8` | Beat, bar and phrase timestamps on the edit timeline; snaps moments to the nearest bar (or beat with `--beats`); `--slots 10,22 --every 2` spaces cuts or reveals evenly; `--track-drop 47.2 --want-drop-at 10` says where to trim the track so its drop lands on time; warns when an approximate BPM will drift |
| `scripts/tap_tempo.py` | The user taps Enter on each beat to estimate BPM when it is unknown |
| `scripts/loudness_check.py final.mp4` or `--voice v.wav --music m.wav` | Measures integrated LUFS and true peak of a mix, or the gap between a voice stem and a music stem. Needs ffmpeg |

Run the scripts yourself when you can execute code and give the user the results. If the user is chatting without a terminal, do not tell them to run Python: give them the numbers, or a manual method (count beats for 15 s and multiply by 4 for the BPM; drop markers on the beats in the editor).

## Workflow

### 1. Intake

Infer from context; ask at most one question if the format or mood is genuinely unclear.

- **Video style:** talking head · voiceover with B-roll · emotional story · day in the life · tutorial · strong opinion · transformation · fashion or product · event or travel
- **Feeling the viewer should leave with:** calm trust · nostalgia · warmth · joy · confidence · urgency · surprise
- **Voice present?** If yes, prefer instrumental, low-vocal or slowed versions.
- **Length and cut speed**
- **Account type:** business accounts have a restricted commercial library, so the licensing check is mandatory.
- **Region and audience language:** affects which tracks exist in the app and which feel familiar.

### 2. Read the mood

Map the video to one of four families:

| Family | Feels like | Typical use |
|---|---|---|
| **SOFT** | cinematic, polished, calm | thoughtful voiceovers, luxury visuals, clean personal brand |
| **EMOTIONAL** | story-led, nostalgic, slow build | founder stories, personal before and afters told with a voiceover, vulnerable voiceovers |
| **UPBEAT** | light, lifestyle, familiar | routines, behind the scenes, travel, montages, visual transformations with a satisfying reveal |
| **BOLD** | fast, high energy, surprising | strong hooks, opinions, fashion, fast education |

### 3. Match the edit style

| Video style | Choose | Edit like this |
|---|---|---|
| Talking head | Instrumental or low vocal | Bed well under the voice; only subtle beat cuts |
| Emotional story | Slow build | Let key lines breathe; land the strongest line on the lift |
| Day in the life | Recognisable upbeat track | Cut actions to the beat |
| Strong opinion | Bold bass or pattern interrupt | Fast opening; a brief pause right before the payoff |
| Transformation | Clear build or drop | Reveal the result exactly on the drop |
| Tutorial | Light instrumental, steady 90 to 110 BPM | Neutral; cut steps on bar lines |
| Product or fashion | Bold or cool lifestyle | Changes on the beat; hero shot on the drop |
| Travel or events | Euphoric upbeat | Wide shots on builds, fast cuts on the chorus |

A transformation can sit in two families: if the story is personal and spoken (a weight-loss journey, a founder's first shop), it is EMOTIONAL; if it is a visual payoff without words (a room, a car, a photo edit), it is UPBEAT, or BOLD for a pattern interrupt. Decide by whether the viewer should feel moved or satisfied.

### 4. Pick tracks

**If the user already has a track,** do not replace it. Check its licence for the account and platforms, ask for or estimate its BPM and where its drop is, then go straight to step 5.

Otherwise open `references/mood-library.md`, choose 3 picks plus an optional wildcard, and say which version to use. If the user wants what is trending now, follow `references/finding-tracks.md` and label anything not from the library as your own suggestion to verify in the app.

**Business accounts and multi-platform masters:** most of the curated library is mainstream, label-owned music. Present those picks as *mood references* ("something that feels like Walking on a Dream") and give a ready-to-paste search brief for the commercial or royalty-free library instead (the search briefs at the end of `references/mood-library.md`). That is a real answer, not a disclaimer.

### 5. Map the placement

Mark the track's intro, first build, drop or change, and outro. Hook goes on the intro, the money line or reveal on the first change, the CTA on the outro tail.

When the BPM is known, run `scripts/beat_grid.py`. The offset is the first downbeat **on the edit timeline after trimming**, not in the original file. To make a drop land at a chosen second, use `--track-drop` and `--want-drop-at` first, then measure the new offset. For a series of reveals use `--slots START,END --every 4` (one per bar) or `--every 2`. If the BPM is approximate ("around 120"), say so and tell the editor to place markers on the real beats; the script prints how far the grid drifts.

### 6. Mix and licence

Give 2 to 4 lines of mix notes from `references/mixing.md`, and a licensing line from `references/licensing.md` for business accounts.

## Output format

Skeleton in `assets/music-brief-template.md`:

```
### Mood read
Format → feeling → MOOD FAMILY

### Top picks
1. Track · Artist (version): why it fits
2. …
3. …
Wildcard: … (optional)

### Placement map
| Moment | Time | Track section | Action |

### Mix notes for the editor

### Licensing check
```

For videos without a voice, rename the placement rows to what happens on screen (opening, first reveal, last reveal, ending).

For full edit plans (typography, colour screens, SFX, motion), hand off to or combine with the **reels-edit-director** skill when it is installed.

## Behaviour notes

- Never advise ripping audio from unofficial uploads for commercial posts.
- Do not claim a track is available on a platform, or trending, unless you checked; say "confirm in the audio picker".
- Do not invent BPMs for specific songs. Give a range for the mood, or ask the user to tap or look it up.
