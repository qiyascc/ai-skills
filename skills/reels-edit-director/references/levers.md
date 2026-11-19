# The five levers in detail

Read this when you assign levers to beats, or when the user asks how to do one of them well.

Intensity scale used everywhere in this skill: **0 off · 1 whisper · 2 noticeable · 3 signature moment.** A video gets at most two levers at 3. Everything else stays at 1 or 2, because a signature only reads as a signature when the rest of the edit is calm.

## Contents

1. Typography (visuals)
2. Colour screens (visuals)
3. Music (audio)
4. Sound effects (audio)
5. Motion (movement)
6. How the levers combine

---

## 1. Typography

**Job:** make text part of the composition, not a subtitle glued to the same spot.

**Two typefaces, two jobs.**
- *Display* (heavy, condensed, serif italic or bold grotesk): only the one to four words that matter most in a beat. If everything is display, nothing is.
- *Support* (clean sans, regular or medium): explanations, labels, subtitles.

**Place text with the shot.** Beside the face, next to the object being discussed, or in deliberate negative space. Centre-bottom for every line is the default that makes edits look like every other edit.

**Use position and scale to mean something.** Left-big against right-small, stacked against single line. The hierarchy, colours and spacing stay consistent; only the arrangement changes to signal a new idea.

**Contrast pairs.** When the script sets two ideas against each other ("not X, but Y"), give X display type on one side, then bring Y in at a contrasting position or a larger scale. The viewer sees the argument before they hear it.

**Readability.**
- Minimum time on screen: about `0.3 s × words + 0.5 s`, never below 1.5 s for a phrase. `scripts/text_timing.py` does this maths.
- Busy background: subtle shadow, thin outline, or a solid colour block behind the text.
- Keep everything that matters inside the platform safe zone (see `platform-specs.md`, or draw an overlay with `scripts/safe_zones.py`).

**Subtitles.**
- Support font, two lines at most, three to six words per line.
- Highlight only the single key word per line (colour or weight). Highlighting every word is the same as highlighting none.
- Break lines at natural phrase boundaries, never between an article and its noun, and never run one card across two sentences.
- When display text already shows the words being spoken, hide the subtitle for that moment. Saying the same thing twice on screen splits attention.

Font pairings by mood, with licences, are in `typography.md`.

## 2. Colour screens

**Job:** a deliberate visual reset that makes one sentence land.

- A full-screen solid colour (brand colour, or one that contrasts with the footage) with **one short line** of text.
- Use it to introduce a new point, punch a surprising statement, or create a pause before a payoff.
- Duration about 0.8 to 2 s: long enough to read at the pace of this edit, no longer.
- Enter with a hard cut (strongest) or a very quick dissolve. Leave with a purposeful cut back to camera.
- **Budget:** one in a video up to 30 s, two or three at most in longer ones. More than that and the video feels interrupted instead of punctuated.
- Best placement: right after a setup line ("Here's what most people get wrong…"), then the counter idea on the colour screen, then back to camera to explain.
- Colour choice: if the footage is warm, a cool or neutral card resets harder; if the brand has one strong colour, this is where it earns its place.

## 3. Music

**Job:** set personality and emotion. The same footage reads completely differently under a different track.

- Choose by the energy, pace and emotion of the message, not by what is trending.
- Audition two or three tracks against the same opening 5 to 10 s and keep the one that supports the voice instead of competing with it.
- Under speech use instrumental, low-vocal or slowed versions, and keep the bed roughly 18 to 25 dB under the voice, ducked further under dense sentences. Detailed levels and loudness targets are in the music picker skill (`reels-music-picker/references/mixing.md`) when it is installed.
- Map the track's intro, build, drop and outro before cutting. The strongest line, the reveal or the transformation goes on a change. Align *selected* moments to the beat; never force every cut onto it.
- Check on headphones and on a phone speaker.
- Business accounts: Meta says certain business accounts do not get the licensed music library, and TikTok says businesses cannot use its general library commercially. Use Meta Sound Collection on Instagram and Facebook, TikTok's Commercial Music Library, or a licensed royalty-free library, and confirm the track before the edit is locked.

For track picks, placement maps and licensing, use the **reels-music-picker** skill when it is installed.

## 4. Sound effects

**Job:** direct attention, not make every second louder.

Where they earn their place:
- A subtle whoosh when a headline moves into frame.
- A soft click or pop as a key word appears.
- A restrained impact or low boom under the single most important statement.
- A quiet swell connecting two visually different shots.
- Natural sound from the footage (pouring coffee, keyboard, footsteps) for realism.

Rules:
- When several words appear in sequence, accent only the most important reveal.
- Keep SFX under the voice and vary them; the same whoosh on every cut becomes noise within three cuts.
- Typical budget: two to five accents in a 30 s video. Palette: three sound types at most.
- **Mute test:** mute the SFX track. If the edit loses clarity or punch, the effects had a job. If it feels better, delete them.

Where to get sounds legally is in `sound-sources.md`.

## 5. Motion

**Job:** keep a talking video alive without flashy motion graphics.

1. **Punch-in:** scale to about 110 to 120 % (or crop in) on a stronger point, return to normal framing after. Check the face stays sharp; heavy punch-ins on 1080p footage soften quickly.
2. **Text entrance:** fade, slide or scale up one key phrase over 8 to 12 frames with an ease-out.
3. **Clean transition:** a match cut or restrained movement between related clips. Spins, glitches and zoom blur only if they are the brand.
4. **Graphic emphasis:** an underline, highlight, circle or arrow drawn on to guide the eye.
5. **Controlled zoom-out:** pull back after a close-up to reveal context.

Rules: one easing style for the whole video, one movement idea at a time, nothing competes with the speaker's face. A punch-in rhythm of one every two or three key lines is plenty for a talking head.

## 6. How the levers combine

| Format | Usual signature levers | Usually quiet |
|---|---|---|
| Talking head, educational | Typography, punch-ins | SFX, colour screens (one at most) |
| Opinion or myth-buster | Colour screen, typography | Music (low bed) |
| Voiceover with B-roll story | Music, typography | SFX (ambient only) |
| Day in the life | Music (cut to beat) | Text (minimal) |
| Transformation, before and after | Music (reveal on the drop), motion | Text |
| Product or fashion | Music, motion | Colour screens |

If two signature levers fight for the same moment, the one that serves the money line wins and the other drops to 1.
