###############
# Qiyas Sadıqov CC
###############
import argparse
import re
import sys

WORD = re.compile(r"[\w%'’]+")

def count(text):
    return len(WORD.findall(text))

def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s.strip()]

def lines_for(sentence, max_words):
    tokens = sentence.split()
    if count(sentence) <= max_words:
        return [sentence]
    lines, current = [], []
    for i, token in enumerate(tokens):
        current.append(token)
        words_now = count(" ".join(current))
        rest = count(" ".join(tokens[i + 1:]))
        soft_break = re.search(r"[,;:]$", token) and words_now >= 3 and rest >= 2
        if words_now >= max_words or soft_break:
            if 0 < rest < 3 and words_now + rest <= max_words + 2:
                continue
            lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))
    return lines

def min_seconds(n_words, per_word, base, floor):
    return max(floor, n_words * per_word + base)

def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def main():
    p = argparse.ArgumentParser(description="Check how long on-screen text needs, and draft subtitle cards or an SRT.")
    p.add_argument("file", nargs="?", help="Text file. Each line is one on-screen phrase, or paste the whole script. Reads stdin when omitted.")
    p.add_argument("--per-word", type=float, default=0.3, help="Seconds per word (default 0.3).")
    p.add_argument("--base", type=float, default=0.5, help="Base seconds added to every card (default 0.5).")
    p.add_argument("--floor", type=float, default=1.5, help="Minimum seconds on screen (default 1.5).")
    p.add_argument("--max-words", type=int, default=6, help="Max words per subtitle line (default 6).")
    p.add_argument("--subtitles", action="store_true", help="Split into subtitle cards: two lines at most, never across sentences.")
    p.add_argument("--srt", action="store_true", help="Print a draft SRT with back-to-back minimum timings.")
    a = p.parse_args()
    text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not raw_lines:
        sys.exit("No text found.")

    if not (a.subtitles or a.srt):
        print("| # | Words | Min on screen | Text |")
        print("|---|---|---|---|")
        for i, line in enumerate(raw_lines, 1):
            n = count(line)
            flag = " (long: split or shorten)" if n > a.max_words * 2 else ""
            print(f"| {i} | {n} | {min_seconds(n, a.per_word, a.base, a.floor):.1f} s{flag} | {line} |")
        return

    cards = []
    for raw in raw_lines:
        for sentence in sentences(raw):
            rows = lines_for(sentence, a.max_words)
            for i in range(0, len(rows), 2):
                cards.append(rows[i:i + 2])

    t = 0.0
    long_lines = 0
    for i, card in enumerate(cards, 1):
        n = sum(count(r) for r in card)
        long_lines += sum(1 for r in card if count(r) > a.max_words)
        d = min_seconds(n, a.per_word, a.base, a.floor)
        if a.srt:
            print(i)
            print(f"{srt_time(t)} --> {srt_time(t + d)}")
            print("\n".join(card))
            print()
        else:
            print(f"[{d:.1f} s] " + " / ".join(card))
        t += d
    if not a.srt:
        print(f"\n{len(cards)} cards, at least {t:.1f} s of reading time.")
        if long_lines:
            print(f"{long_lines} line(s) run over {a.max_words} words to avoid leaving one or two words alone; shorten them if you can.")

if __name__ == "__main__":
    main()
