---
name: "reel-localizer"
description: "Turn one video into many language versions with captions that are translated, re-wrapped by real glyph width, re-sized, re-timed for reading speed, key-phrase highlighted and kept in platform safe zones, burned in plus SRT files."
---

# Reel Localizer

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Subtitle tools translate words. You localise the screen: a Russian line is 30% longer than English, Azerbaijani has ə, ğ, ı, ş, and a caption that fits in one language breaks the layout in another. Every language gets its own fitted, timed, styled version.

Reply in the user's language.

## 0. Setup
The script ships with this skill as `scripts/localize.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/localize.py tools/`. Needs ffmpeg with libass (`ffmpeg -filters | grep subtitles`) and Pillow. Optional transcription: `pip install faster-whisper --break-system-packages`.
- `python3 tools/localize.py transcribe video.mp4 captions.json [--lang az]` or `from-srt in.srt captions.json --lang en`
- `python3 tools/localize.py render video.mp4 captions.json loc --langs az,ru,en,tr [--style bold|clean|box] [--pos lower|middle] [--platform reels] [--accent "#F0662B"] [--max-lines 2] [--cps 17]`

## 1. Workflow
1. **Source captions:** transcribe, import an SRT, or write captions.json from the script. Fix names and numbers (transcribers mishear brand names, prices, streets).
2. **Translate yourself** into each target language inside captions.json. Translate for the screen, not word for word: shorter, spoken, same meaning, numbers and prices identical, local units/currency where relevant. Fill `emph` with the 1-3 word key phrase per language (it gets the accent colour).
3. **Render** all languages. Read `loc/check.md`:
   - "shrunk" = font reduced (fine up to 75%), "over 2 lines" = still too long, "too fast to read" = more characters per second than people can read.
   - For any flagged caption: shorten that translation or give it more time, then render again. Never accept a flagged caption.
4. Look at one frame per language (Read tool) to confirm glyphs, position and highlight.
5. Deliver the MP4s and SRTs; also translate the post caption and hashtags per language.

## 2. Built-in rules
- Wrap by actual glyph width of the chosen font; shrink up to 25% before adding a line; max 2 lines.
- Split a caption into two (by words, time proportional) when it exceeds the reading speed and lasts at least 1.6 s; never below ~0.8 s per caption.
- Captions pop in at 115% then settle (no fades), sit above the platform's bottom UI zone and left of the right button column.
