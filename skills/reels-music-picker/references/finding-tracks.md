# Finding tracks and current trends

Read this when the user wants what is trending now, or alternatives beyond `mood-library.md`.

You cannot see the user's app. Anything you suggest beyond the library is a lead to check in the audio picker, not a confirmed option. Say so.

## Where trends are published

| Platform | Where | Status |
|---|---|---|
| Instagram | Trending audio, the top 50 tracks, on creators.instagram.com/get-inspired | official |
| Instagram | An up-arrow next to an audio name in Reels is widely read as "trending" | practice; Meta does not define it officially |
| TikTok | Creative Center, Trends, Songs: ads.tiktok.com/business/creativecenter/inspiration/popular/music/pc/en | official page; filters may change |
| YouTube Shorts | The Shorts audio library inside the app, and the sound page of any Short | official |

If you have web search, search those pages and recent coverage for the current month, then filter what you find by the mood family you chose. Trending is a tiebreaker, not the brief: a trending track that fights the voice still loses to a quiet instrumental that supports it.

## Searching inside the apps

- Search the title plus a version word: "instrumental", "slowed", "sped up", "piano version".
- Open the sound page of a Reel or TikTok you like: it lists other videos using the same audio, which shows how others cut to it.
- Save candidates to the app's saved audio, then audition them on the same opening 5 to 10 s.
- Business accounts: search inside the commercial library directly, with mood words.

## Searching outside the apps

- YouTube: "<title> instrumental", pick by length and by the version that has a clear change near the right time.
- Royalty-free libraries (see `licensing.md`): filter by mood, tempo range, and "no vocals".
- Note the BPM if the library shows it; feed it to `scripts/beat_grid.py`.

## Tempo ranges as a guide

Use these as ranges for the mood, not as facts about specific songs:

| Feeling | Typical tempo |
|---|---|
| Calm, reflective, luxury | about 60 to 90 BPM |
| Steady, explanatory | about 90 to 110 BPM |
| Lifestyle, upbeat | about 100 to 130 BPM |
| Fast, high energy | about 120 to 150 BPM, or a half-time feel at 140+ |

If you need a specific song's tempo, ask the user to tap it with `scripts/tap_tempo.py` or read it from the library page, rather than guessing.
