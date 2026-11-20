---
name: "master-editor"
description: "Run a whole edit the way master film editors work, step by step: brief, first-impression dailies, boards and selects, assembly without temp music, cut points, J/L sound, rhythm, Rule of Six review, fresh-eyes screenings with a notes heat map, tighten and lock."
---

# Master Editor

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

This is the general skill: the cutting-room protocol distilled from Walter Murch, Thelma Schoonmaker, Dede Allen, Edward Dmytryk, Kirk Baxter, Eddie Hamilton and the research of James Cutting and Tim Smith. It runs a project through twelve steps, tracks them, and calls the five specialist skills at the right moments.

Reply in the user's language.

## 0. Principles on the wall
- **Emotion first** (Murch's Rule of Six: emotion 51, story 23, rhythm 10, eye trace 7, 2D plane 5, 3D space 4). Never give up a higher one for a lower one.
- **Protect first impressions.** The first viewing should give an emotional reaction, not a critical one (Dmytryk). Write feelings in pass 1, fixes later.
- **Do not let the set blind you.** Only what was captured matters, not what was intended (Baxter). Knowing how hard a shot was to get is no reason to keep it (Murch).
- **Every scene as if it were the only one** (Baxter), then the whole.
- **Cut bare first.** If a scene plays without music it really plays (Christopher McQuarrie, cut by Eddie Hamilton).
- **Never cut without a positive reason; cut long when unsure; cut in movement** (Dmytryk).
- **Sound leads.** J and L cuts make dialogue flow (Dede Allen).
- **Invisible is not mandatory.** Schoonmaker and Scorsese break continuity when the emotion asks for it; the audience follows feeling before geometry.
- **Attention is the material.** Continuity rules work because they hide cuts in moments when attention is elsewhere (Tim Smith); good pacing fluctuates at every scale (Cutting).

## 1. Setup
The script ships with this skill as `scripts/editroom.py`. Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/editroom.py tools/`. It calls the specialist tools from the same `tools/` folder: load the skills **selects-builder**, **cut-point-finder**, **split-edit-builder**, **rhythm-architect** and **rule-of-six-judge** and copy their scripts (`selects.py`, `cutpoint.py`, `splitedit.py`, `rhythm.py`, `sixjudge.py`) from each skill's `scripts/` folder next to it when a stage needs them.
- `python3 tools/editroom.py init PROJECT --clips raw/ --title "Name"`: folders 01_raw to 06_screenings, PROTOCOL.md, state.json
- `python3 tools/editroom.py status PROJECT`: progress and the next step
- `python3 tools/editroom.py run PROJECT selects|cutpoints CLIP...|split EDIT.json|rhythm CUT.mp4 [REF.mp4]|judge CUT.mp4`
- `python3 tools/editroom.py done PROJECT N "note"`: tick manual steps
- `python3 tools/editroom.py screening PROJECT notes.csv cut.mp4 [--bin 5]`: heat map of audience notes (bored, confused, lost, loved, laugh) joined with measured flat zones

## 2. The twelve steps
1. Brief: what each scene must make the viewer feel, written before seeing footage.
2. Dailies pass 1: everything once, straight through, first impressions only.
3. Boards and selects (**selects-builder**).
4. Pass 2: timecoded notes on circled takes.
5. Assembly, scene by scene, no temp music on the first pass.
6. Cut points for every transition (**cut-point-finder**).
7. Sound grammar: J/L cuts, room tone (**split-edit-builder**).
8. Rhythm pass, with a reference if there is one (**rhythm-architect**).
9. Rule of Six review: measure, then watch the weakest cuts for emotion and story (**rule-of-six-judge**).
10. Fresh eyes: a break, then a screening with new viewers; collect timecoded notes; run `screening`. When several viewers report the same spot, the cause usually sits a little before it.
11. Lift and tighten: remove what has no positive reason to stay; re-screen.
12. Lock: sync, levels, flash frames, export, archive.

## 3. Working with the user
- Short-form (Reels, ads) compresses the steps but keeps the order: brief, selects, bare cut, cut points, sound, rhythm, review, one fresh-eyes check. Combine with **retention-oracle** and **beat-snap-reeditor** for social video.
- At each step show the evidence (boards, sheets, plots, heat map) and ask for the user's feeling before giving yours.
- Keep PROTOCOL.md updated; it is the project's memory when the user returns later.
