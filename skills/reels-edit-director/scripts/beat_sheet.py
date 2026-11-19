###############
# Qiyas Sadıqov CC
###############
import argparse
import json
import re
import sys

ROLE_HINTS = [
    ("cta", re.compile(r"\b(follow|save|share|comment|dm|link in bio|subscribe|book|order|visit|come|call|try|shop|sign up|"
                       r"takip|kaydet|paylaş|yorum|yaz|gel|uğra|ara|dene|sipariş|bizden|izlə|abunə|gəl|zəng|sifariş|yadda saxla)\b", re.I)),
    ("turn", re.compile(r"\b(but|however|instead|actually|here's the thing|the truth|ama|fakat|aslında|amma|lakin|əslində)\b", re.I)),
]

NUMBER = re.compile(r"\d|%|\b(percent|times|thousand|million|yüzde|kat|bin|milyon|faiz|dəfə|min)\b", re.I)

def split_beats(text, long_words):
    parts = re.split(r"(?<=[.!?…])\s+|\s*\n\s*", text.strip())
    beats = []
    for part in (re.sub(r"\s+", " ", p).strip() for p in parts):
        if not part:
            continue
        if words(part) > long_words and re.search(r"[,;:]\s", part):
            pieces = re.split(r"(?<=[,;:])\s+", part)
            current = ""
            for piece in pieces:
                if current and words(current) >= 4 and words(piece) >= 3:
                    beats.append(current)
                    current = piece
                else:
                    current = f"{current} {piece}".strip()
            beats.append(current)
        else:
            beats.append(part)
    return beats

def words(line):
    return len(re.findall(r"[\w'’-]+", line))

def fmt(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m)}:{s:04.1f}"

def build(beats, wpm, pause, money):
    rate = wpm / 60.0
    rows = []
    t = 0.0
    for i, line in enumerate(beats):
        w = words(line)
        dur = max(w / rate, 0.8) + pause
        role = ""
        if i == 0:
            role = "hook"
        elif i == len(beats) - 1:
            role = "cta" if ROLE_HINTS[0][1].search(line) else "payoff"
        else:
            for name, rx in ROLE_HINTS:
                if rx.search(line):
                    role = name
                    break
        if money and money.lower() in line.lower():
            role = (role + "+money").strip("+")
        rows.append({"start": round(t, 2), "end": round(t + dur, 2), "words": w, "role": role, "line": line})
        t += dur
    if not money and len(rows) > 2:
        middle = rows[1:-1]
        best = max(middle, key=lambda r: (bool(NUMBER.search(r["line"])), r["role"] == "turn", r["words"]))
        best["role"] = (best["role"] + "+money?").strip("+")
    return rows

def markdown(rows):
    out = ["| Time | Role | Script | Text on screen (font, position) | Motion | Audio (music / SFX) |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {fmt(r['start'])} to {fmt(r['end'])} | {r['role']} | {r['line']} |  |  |  |")
    total = rows[-1]["end"] if rows else 0
    out.append("")
    out.append(f"Estimated runtime: {fmt(total)} ({total:.1f} s) for {sum(r['words'] for r in rows)} words.")
    out.append("Roles are a first guess (money? = guessed money line). Correct them before planning.")
    return "\n".join(out)

def main():
    p = argparse.ArgumentParser(description="Turn a script into a timed beat sheet skeleton (markdown or JSON).")
    p.add_argument("script", nargs="?", help="Script file. Reads stdin when omitted.")
    p.add_argument("--wpm", type=float, default=150,
                   help="Speaking rate in words per minute (default 150, a typical English pace). Languages with longer words, "
                        "such as Turkish or Azerbaijani, often land nearer 110 to 130; time a read-through if you can.")
    p.add_argument("--long", type=int, default=12, help="Split sentences longer than this many words at commas (default 12).")
    p.add_argument("--pause", type=float, default=0.25, help="Pause after each beat in seconds (default 0.25).")
    p.add_argument("--money", help="A phrase from the money line, to tag it explicitly.")
    p.add_argument("--json", action="store_true", help="Print JSON instead of markdown.")
    a = p.parse_args()
    text = open(a.script, encoding="utf-8").read() if a.script else sys.stdin.read()
    beats = split_beats(text, a.long)
    if not beats:
        sys.exit("No text found.")
    rows = build(beats, a.wpm, a.pause, a.money)
    print(json.dumps(rows, ensure_ascii=False, indent=2) if a.json else markdown(rows))

if __name__ == "__main__":
    main()
