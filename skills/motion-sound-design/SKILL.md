---
name: "motion-sound-design"
description: "Design and mix event-synced sound for motion videos and Reels: music choice and beat sync, one SFX per visual event, pitch variation, band-specific levels, micro-ducking and -13 LUFS mastering, with a built-in SFX synthesizer and mixer."
---

# Motion Sound Design

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Sound is half of why a motion video feels expensive. Default output usually has no sound or one music track slapped on. This skill makes every visual event *audible*, keeps the music clean under it, and masters to platform loudness. It ships a tool that synthesizes a clean UI sound library (no downloads needed) and mixes a cue list into a mastered WAV.

Reply in the user's language.

## 0. Files in this skill

| File | Use it when |
|---|---|
| `scripts/sfx.py` | Building the sound library, mixing a cue list, muxing audio into the video |
| `assets/cues.example.json` | Starting a cue list |

`scripts/sfx.py` needs Python 3 with numpy + scipy (`pip install numpy scipy`, add `--break-system-packages` only on a system Python that refuses) and ffmpeg for `mix` and `mux`. Run it from this skill's folder:
- `python3 scripts/sfx.py synth sfx_lib` → 12 sound types × 3 variants: tick, click, key, pop, whoosh, swish, thud, chime, shine, squelch, snip, shutter (no ffmpeg needed)
- `python3 scripts/sfx.py mix cues.json mix.wav` → places cues, applies all rules below, masters
- `python3 scripts/sfx.py mux video.mp4 mix.wav final.mp4`

Real samples beat synthesized ones: if the user has a pack (Epidemic, Artlist, freesound CC0), drop files into the library folder named `TYPE_anything.wav` (e.g. `whoosh_soft.wav`) and they are used automatically.

## 1. Music

- Choose by the film's emotion and energy, not by trend. UI/tech calm: soft minimal ambient, no drops, no heavy bass. Promo: punchy electronic 120-140 BPM. High-energy: 150-160 BPM.
- Lock the edit to the track: note its BPM, pick a start offset so **beat 0 lands on frame 0**, and put the film's biggest visual change on the track's drop/phrase change.
- High-pass music at ~55 Hz (no sub booms on phone speakers); no filter sweeps unless they tell the story.
- **Perspective sound:** when the camera goes inside something (a room, a device, underwater), cut the kick and bass and keep only the highs ("heard through the walls"); bring the low end back on the way out and hit full on the money moment.
- Licensing: commercial posts need licensed music (platform business library or a paid library). Never suggest ripping audio.
- If the user wants specific tracks by mood, use **reels-music-picker** if available.

## 2. One sound per visual event

Map every visual event to a sound type:

| Visual event | Sound |
|---|---|
| first frame / logo glint | shine (soft, nothing hard in the first 12 frames) |
| object hops / flies / camera whip | whoosh (long) or swish (short) |
| landing, drop into a slot | thud (soft, no sub) |
| card/banner sliding in | swish + click |
| button press, toggle, row collapse | click |
| digits, odometer wheels, counters | tick per landing digit |
| typing | key on letters (every 2nd-4th letter when fast) |
| icon/badge pop, checkmark | pop / snip / "marker stroke" (snip) |
| liquid spread, blob merge | squelch |
| shutter, iris, screenshot | shutter |
| success, final lockup | chime |

Rules (applied automatically by the mixer):
- random pitch ±1 semitone per hit, so repeats never sound robotic
- the same sample never twice within 2 s (3 variants per type)
- max 8 events in any 0.25 s (extras dropped and reported); clutter kills clarity
- 160 Hz high-pass on small UI sounds (ticks, clicks, keys, swishes, pops, snips)
- no musical notes, booms or sub hits in the SFX layer

## 3. Levels and mix

Default levels relative to the music in the same band (built into the tool, override per cue with `"db"`):
ticks +10.5 dB (4-10 kHz) · clicks +10 · keys +9 (1.5-8 kHz) · swishes +9.5 · hits/thuds +7 · pops +8 · squelch +7 · chime +5.

- **No pumping sidechain.** Instead, under each tick/click/key the music gets a -8 dB, 60 ms dip only in 2-8 kHz (micro-ducking) so the hit cuts through while the groove continues.
- Master: -13 LUFS integrated (Reels/TikTok/Shorts), true peak ≤ -1 dBTP, look-ahead limiter without pumping. For YouTube long-form use -14. `sfx.py mix` limits 1 dB under the true-peak target because AAC encoding in `mux` raises peaks by about 0.6 dB.
- Voice-over (if any) sits on top: music bed 18-25 dB below speech.
- Check on phone speaker AND headphones.

## 4. cues.json format

A copy to start from is in `assets/cues.example.json`.

```json
{
  "duration": 15.0, "lufs": -13, "true_peak": -1.0, "seed": 3,
  "library": "sfx_lib",
  "music": "track.mp3", "music_start": 49.735, "music_gain_db": 0, "music_highpass": 55,
  "duck": {"db": -8, "ms": 60, "band": [2000, 8000], "types": ["tick", "click", "key"]},
  "cues": [
    {"t": 0.05, "type": "shine"},
    {"t": 0.59, "type": "whoosh"},
    {"t": 0.99, "type": "thud"},
    {"t": 3.16, "type": "swish", "db": 12}
  ]
}
```
Paths are relative to the JSON file. Omit `music` for SFX-only.

## 5. Workflow

1. From the timed spec (motion-story-director), list every visual event with its exact time → cue list. Snap to the beat grid if the spec is beat-locked.
2. `synth` the library (or use the user's samples).
3. `mix` → read the report: dropped cues mean too much density at that moment.
4. Verify loudness: `ffmpeg -i mix.wav -af ebur128 -f null - 2>&1 | grep "I:"`.
5. `mux` with the rendered video; deliver the final MP4.

Write a short SOUND section for any spec in this form: music (mood, BPM, offset, high-pass) → event list with times → levels → master target.
