# Platform specs

Read this for safe zones, length limits, resolution and subtitle reading speed. Checked in November 2026. Platforms change these often: when a number decides something important, tell the user to confirm it in the app.

Labels: **official** means the platform's own page says it; **practice** means common creator or third-party guidance, not a platform rule.

## Instagram Reels

| Item | Value | Status |
|---|---|---|
| Canvas | 9:16, 1080×1920 for organic posts | practice (Meta's ads guide recommends 1440×2560 for Reels ads) |
| Length | Up to 20 minutes can be recorded and edited; **only Reels of 3 minutes or less are recommended to new audiences** | official (about.instagram.com/features/reels) |
| Safe zone, ads | Keep 14 % top, 35 % bottom and 6 % each side free of text and logos (about 269 px, 672 px, 65 px at 1080×1920) | official percentages, Meta ads guide; pixels are arithmetic |
| Safe zone, organic | About 250 px top, 420 px bottom, 120 px on the right (buttons), 60 px left | practice |
| Profile grid | Since January 2025 the grid shows taller 3:4 thumbnails, so a 9:16 cover is cropped to the centre 1080×1440 band | grid change official (Mosseri), 3:4 ratio practice |

Practical rule: put the hook text and the cover title inside the centre 1080×1440 band **and** inside the organic safe zone. `scripts/safe_zones.py --platform instagram --grid` draws both.

## TikTok

| Item | Value | Status |
|---|---|---|
| Canvas | Full-screen 9:16, at least 720p; 1080×1920 is the usual export | 720p minimum official (TikTok SMB guide); 1080×1920 practice |
| Length | Posting API allows up to 10 minutes | official (developer docs); in-app recording and upload limits not verified |
| Safe zone | TikTok publishes downloadable templates and says it depends on caption length and add-ons; no pixel numbers | official |
| Safe zone numbers | About 240 px top, 660 px bottom, 120 px each side | practice |

## YouTube Shorts

| Item | Value | Status |
|---|---|---|
| Canvas | Square or vertical | official |
| Length | Up to 3 minutes for uploads on or after 15 October 2024 | official (support.google.com/youtube/answer/15424877) |
| Copyright | A Short **longer than one minute with an active Content ID claim** is blocked worldwide until the claim is resolved | official, same page |
| Safe zone | The Shorts editor shows guide lines for the unsafe area; no pixel numbers published | official |
| Music in Shorts | Up to 90 s of a song from the Shorts audio library, depending on the song; those licences are for personal, non-commercial content | official |

The Content ID rule matters for music choice: a Short over 60 s with an unlicensed track can disappear entirely, not just lose monetization.

## Cross-posting one master

If one video goes to all three platforms, export 1080×1920 and keep essential text inside the union safe area (`scripts/safe_zones.py --platform all`): about 250 px top, 660 px bottom, 120 px each side. That leaves a 840×1010 px area that is safe everywhere.

## Cover frame and export

- **Cover:** choose or design a frame where the title sits inside the centre 1080×1440 band (Instagram profile grid) and inside the safe zone. A cover with a face and three to five words of display text is the usual pattern.
- **Export (practice, not platform rules):** 1080×1920, the same frame rate as the footage (24, 25 or 30 fps; do not convert 25 to 30), H.264, AAC audio at 48 kHz. Upload over Wi-Fi with the app's high-quality upload setting on, where the app has one.

## Subtitle and on-screen text reading speed

| Guideline | Numbers | Status |
|---|---|---|
| BBC Subtitle Guidelines (2026) | 160 to 180 words per minute, about 0.33 to 0.375 s per word | official |
| Netflix English | Up to 42 characters per line, 2 lines; adult content up to 20 characters per second | official (Netflix pages disagree; another lists 17) |
| Netflix duration | Minimum 5/6 s, maximum 7 s per subtitle | official |

Short-form text moves faster than broadcast subtitles but is also read on a small screen while the speaker talks. That is why this skill uses `0.3 s × words + 0.5 s` with a 1.5 s floor for designed text (`scripts/text_timing.py`), and 3 to 6 words per subtitle line.

## Sources

- Instagram Reels features: https://about.instagram.com/features/reels/
- Instagram creators blog (3-minute Reels, January 2025): https://creators.instagram.com/blog/the-latest-with-instagram
- Meta ads guide, Instagram Reels: https://www.facebook.com/business/ads-guide/update/video/instagram-reels
- TikTok in-feed ads spec: https://ads.tiktok.com/help/article/tiktok-auction-in-feed-ads
- TikTok Content Posting API: https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide
- YouTube Shorts length and Content ID: https://support.google.com/youtube/answer/15424877
- YouTube Shorts editor guides: https://support.google.com/youtube/answer/16215842
- BBC subtitle guidelines: https://www.bbc.co.uk/accessibility/forproducts/guides/subtitles/
- Netflix timed text style guide: https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617
