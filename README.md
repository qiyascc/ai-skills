# AI skills

Skills for coding agents by [Qiyas CC](https://qiyas.cc/). Each skill is a folder in `skills/<name>/` with a `SKILL.md` and, sometimes, extra files.

## Skills

| Skill | Name | What it does |
| --- | --- | --- |
| [Reels Edit Director](skills/reels-edit-director) | `reels-edit-director` | Turn a Reel, TikTok or Shorts script into a timestamped edit plan and a copy-paste brief for your editor: fonts, colour breaks, music, sound effects and motion, with restraint. |
| [Reels Music Picker](skills/reels-music-picker) | `reels-music-picker` | Pick music for short videos by mood, land your cuts and reveals on the beat, set the levels under your voice, and know what your account is allowed to use. |

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
