# Mixing and sync spec

Read this when you give the editor levels, ducking, versions, a structure map or loudness targets.

## Voice first

The voice carries the message, so everything is set relative to it.

- **Music under speech:** start the bed roughly 18 to 25 dB below the voice. In phone apps with a 0 to 100 % slider that usually lands around 8 to 15 %, but sliders are not standardised, so judge by ear on a phone speaker.
- **Ducking:** lower the music further under dense sentences and lift it only in gaps, with fades of about 200 to 500 ms so the pumping is not audible. Premiere Pro (Essential Sound, Ducking) and DaVinci Resolve (Fairlight Ducker) do this automatically; in CapCut and phone apps use volume keyframes. Click-level steps are in the edit director skill, `reels-edit-director/references/app-recipes.md`.
- **No speech:** music can come up to full level, but keep the true peak under the ceiling below.
- **Check:** headphones and a phone speaker. Phone speakers lose most bass, so a bass-only "hit" may vanish there.

`scripts/loudness_check.py --voice voice.wav --music music.wav` measures the gap between exported stems and says whether the bed is too loud or too quiet.

## Loudness of the final mix

None of Instagram, TikTok or YouTube publishes an official loudness target. The figures below are industry practice, so present them that way.

| Target | Value | Basis |
|---|---|---|
| Integrated loudness of the final mix | about **-14 to -16 LUFS** | widely used for streaming and social; YouTube is often measured around -14 LUFS in third-party tests |
| True peak | **-1 dBTP** or lower | avoids clipping after the platform re-encodes the audio |
| Speech-led content, conservative | -16 LUFS | Apple Podcasts requires -16 LKFS ±1 dB with true peak at or below -1 dBFS; AES TD1008 suggests -18 LUFS for speech distribution |

`scripts/loudness_check.py final.mp4` measures the export (integrated LUFS, true peak, loudness range) and says how many dB to move. It needs ffmpeg. The default target is -14 LUFS and -1 dBTP; pass `--target -16` for a quieter, speech-first mix.

Practical order: mix by ear for the voice-to-music balance first, then bring the whole mix to the target with a limiter on the master, then measure.

## Versions

- Instrumental, slowed, sped-up or looped edits sit better under speech than vocal originals.
- Lyrics that compete with the script make both harder to follow; if the only good version has vocals, drop it lower and keep it out of the sentences that matter.
- Sped-up versions raise perceived energy; slowed versions add weight and nostalgia.

## Structure map

Before cutting, listen through once and mark:

| Section | What to put there |
|---|---|
| Intro (first sound) | The hook. Trim so something audible happens within the first 0.5 s; never open on silence or a long fade-in |
| First build | Rising tension: process shots, setup lines |
| Drop or change | The money line, the reveal, the transformation |
| Breakdown or pause | A beat of silence before a payoff line works well in opinion videos |
| Outro | The CTA; fade the last 0.5 to 1 s or end on a natural hit |

For a looping video, match the energy of the last second to the first so the loop is not obvious.

## Beat-sync with restraint

- Sync **selected** moments (reveals, outfit or product changes, scene shifts), not every cut, unless the format is a montage where cutting on every beat is the point.
- Most pop and electronic tracks change on phrase boundaries of 4 or 8 bars. `scripts/beat_grid.py` lists bar and phrase starts once you know the BPM and the time of the first downbeat, and snaps planned moments to the nearest bar.
- A cut a few frames **before** the beat often feels more on-beat than one exactly on it, because the eye needs a moment to register the new shot. Let the editor nudge by eye.

## Audition

Test two or three candidates on the same opening 5 to 10 s, with the voice in. Keep the one that supports the voice rather than the one that is most exciting alone.
