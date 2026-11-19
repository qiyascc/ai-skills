# AI skills

Skills for coding agents by [Qiyas CC](https://qiyas.cc/). Each skill is a folder in `skills/<name>/` with a `SKILL.md` and, sometimes, extra files.

## Skills

| Skill | Name | What it does |
| --- | --- | --- |
| [Reels Edit Director](skills/reels-edit-director) | `reels-edit-director` | Turn a Reel, TikTok or YouTube Shorts idea, script, voiceover or footage description into a precise, timestamped edit plan and a copy-paste editor brief covering typography, colour-screen breaks, music, sound effects, motion and pacing. Also diagnoses drafts that feel boring, chaotic or lose viewers. Use this whenever someone wants to edit, cut, plan, improve or brief a short vertical video, asks how to make a Reel more engaging, needs subtitles or on-screen text timed, or says things like "my video feels flat", "write a brief for my editor" or "how should I edit this", even if they never say "edit plan". |
| [Reels Music Picker](skills/reels-music-picker) | `reels-music-picker` | Pick background music for an Instagram Reel, TikTok or YouTube Short by mood rather than genre, then tell the editor exactly where the track's changes land, how loud it sits under the voice, which version to use and whether a business account may use it. Includes beat and bar maths, a loudness checker and licensing guidance. Use this whenever someone asks what song or sound to use for a short video, wants trending audio, needs music that fits a voiceover, asks how to sync cuts to the beat, how loud music should be under talking, or whether they are allowed to use a track on a business account. |

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
