# App recipes

Read this when the user needs to actually do something in their editor. Menu names change between versions; describe the feature by name and where it usually lives, and if a step does not match what the user sees, have them search the app's help for the feature name.

## Contents

- CapCut
- Edits (Meta)
- Premiere Pro
- DaVinci Resolve
- Same five techniques in every app

---

## CapCut

| Technique | How |
|---|---|
| Auto captions | Text → Auto captions; pick the spoken language, then restyle with the support font. Docs: capcut.com/help/auto-captions-in-capcut |
| Punch-in | Select the clip, set a keyframe (diamond next to Position or Scale) at the start of the line, move forward a few frames, scale to 110 to 120 %. Docs: capcut.com/help/keyframes-in-capcut-pc |
| Text entrance | Select the text → Animation → In; keep it to 8 to 12 frames |
| Colour screen | Add a solid colour background or a coloured image as a clip, add one text layer, 0.8 to 2 s |
| Music under voice | Lower the music clip volume; on desktop use volume keyframes to dip it under dense sentences |

## Edits (Meta)

Instagram's own editing app, launched 22 April 2025, free on iOS and Android, sign-in with Instagram.

- At launch: frame-accurate timeline, automatic captions, overlays, green-screen camera, watermark-free export, direct posting to Instagram and Facebook.
- Keyframes, sound effects and a royalty-free music library were announced as "coming soon" at launch; check whether they are in the user's version before relying on them.
- Good choice when the video goes to Instagram first and the user edits on the phone.
- Source: creators.facebook.com/blog/edits-video-creation-app

## Premiere Pro

| Technique | How |
|---|---|
| Auto ducking | Mark the voice clips as Dialogue and the music as Music in the Essential Sound panel, then on the music use Ducking → Duck Against: Dialogue, set Sensitivity, Duck Amount and Fade Duration, and generate keyframes. Docs: helpx.adobe.com/premiere (search "automatically duck audio") |
| Vertical from horizontal | Sequence → Auto Reframe Sequence, 9:16; check each shot, the tracking is not perfect on fast motion |
| Punch-in | Effect Controls → Scale keyframes, or a nested clip with Scale 112 % for hard punch-ins |
| Captions | Text panel → Transcribe sequence → Create captions, then restyle with the support font |
| Loudness | Loudness Radar or the Loudness Meter effect on the mix bus, see the music picker's mixing guide for targets |

## DaVinci Resolve

| Technique | How |
|---|---|
| Ducking | Fairlight page: the Ducker track FX listens to one or more dialogue tracks and lowers the music. Docs: blackmagicdesign.com/products/davinciresolve/fairlight |
| Loudness | Fairlight loudness meter on the monitoring panel, with a selectable standard; Normalize Audio Levels from a clip's right-click menu |
| Punch-in | Inspector → Transform → Zoom keyframes, or Dynamic Zoom for slow push-ins |
| Vertical timeline | Project Settings → custom resolution 1080×1920 before editing |

## Same five techniques in every app

1. **Two fonts:** save a text preset or template for display and for support.
2. **Colour screen:** a solid colour clip plus one text layer, hard cuts in and out.
3. **Ducking:** automatic ducking if the app has it, otherwise volume keyframes around each sentence.
4. **Punch-in:** a scale keyframe of 110 to 120 % on the line, back to 100 % after.
5. **Safe zone check:** create a PNG with `scripts/safe_zones.py -o overlay.png`, import it as the top layer (an overlay or picture-in-picture layer in phone apps) at about 50 % opacity, and hide or delete it before export.
