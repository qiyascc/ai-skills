# Diagnosing a draft

Read this when the user shares a finished or draft video, or describes a problem ("it feels boring", "people drop off").

Diagnose first, then prescribe the **smallest** fix that solves it. Most weak edits need one change, not a redesign.

## Questions to answer before prescribing

1. Where does attention drop? (first 3 s, middle, before the CTA). If the user has retention data, use the drop point; if not, ask what they feel.
2. What is the money line, and does the edit treat it differently from every other line?
3. How many levers are running at full intensity? More than two usually means chaos; zero usually means flat.
4. Can you read every piece of text at the edit's speed, inside the safe zone, on a phone?
5. With the sound off, does the video still make sense? With the SFX muted, does it lose anything?

## Symptom table

| Symptom | Try this first | Then, if still weak |
|---|---|---|
| Visually repetitive | Change font scale and placement between ideas; add one colour-screen reset | A punch-in rhythm, one every 2 to 3 key lines |
| Flat, no emotion | Revisit the music: same footage, different track | Let key lines breathe; land them on the track's change |
| Weak at key moments | One restrained SFX accent on the money line | Punch-in plus display text on that line |
| Too static | Subtle punch-ins or one text animation | Insert one or two B-roll cutaways |
| Too chaotic | Remove competing effects; two fonts, one accent colour | Halve the SFX; slow the cut rhythm |
| Loses people in the first 3 s | Hook text in display type on frame 1; start mid-sentence; cut all dead air | A pattern-interrupt track or an opening colour screen |
| Drops off mid-video | Reorder so a payoff arrives by about 40 % of the runtime; tighten pauses under 0.3 s | A visual chapter marker (colour screen or big number) |
| Text nobody reads | Fewer words; run `scripts/text_timing.py` and give each card its minimum time | Move text next to what it describes instead of the bottom |
| Voice hard to hear | Music down under speech, duck harder on dense sentences | Instrumental or slowed version of the track |
| Ending feels abrupt | End on a natural music hit or a 0.5 to 1 s fade | For looping videos, match the last frame's energy to the first |
| Looks cheap | Remove stock transitions and preset text animations | One easing style, two fonts, consistent spacing |

## How to report a diagnosis

```
### What's happening
One or two sentences, specific to this video (timestamps if you have them).

### Smallest fix
The one change to make first, with exact instructions.

### If that is not enough
One or two follow-ups, in order.

### Leave alone
What already works and should not be touched.
```
