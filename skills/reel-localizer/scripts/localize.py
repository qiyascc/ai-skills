###############
# Qiyas Sadıqov CC
###############
import json, os, re, subprocess, sys
from PIL import ImageFont

USAGE = """reel-localizer: one video -> many language versions with captions that are re-timed, re-wrapped
and re-sized per language (not just translated), kept inside platform safe zones.

  python3 localize.py from-srt IN.srt OUT_captions.json --lang en        -> caption skeleton from an SRT
  python3 localize.py transcribe VIDEO.mp4 OUT_captions.json [--lang az]  -> skeleton via faster-whisper/whisper if installed
  python3 localize.py render VIDEO.mp4 captions.json OUT_DIR --langs az,ru,en [--font PATH] [--style bold|clean|box]
        [--pos lower|middle] [--platform reels|tiktok|shorts] [--accent "#F0662B"] [--max-lines 2] [--cps 17]
      -> OUT_DIR/<video>_<lang>.mp4 + .ass + .srt for every language, plus check.md (fit + reading-speed report)

captions.json:
{ "source": "en",
  "segments": [ {"start": 0.4, "end": 2.2,
                 "text": {"en": "Sea view from every room", "ru": "...", "az": "..."},
                 "emph": {"en": "Sea view", "ru": "...", "az": "..."} } ] }
Claude writes the translations into "text" (and the key phrase per language into "emph").
Per language the tool: wraps by real glyph width, shrinks the font down to 75% before adding a line,
splits a segment in two (by words, proportional time) when it exceeds the reading speed (chars/second),
flags captions still too fast to read (shorten the translation or extend the time),
pops captions in with a 115%->100% scale (no fades), colours the key phrase, keeps text out of UI zones.
Needs: ffmpeg with libass, Pillow.
"""

ZONES = {"reels": (0.13, 0.22, 0.11), "tiktok": (0.12, 0.25, 0.14), "shorts": (0.10, 0.20, 0.12)}
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

def run(c): return subprocess.run(c, capture_output=True, text=True)
def ts_srt(t): ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000); return f"{h:02}:{m:02}:{s:02},{ms:03}"
def ts_ass(t): cs = int(round(t * 100)); h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); return f"{h}:{m:02}:{cs // 100:02}.{cs % 100:02}"
def ass_color(hx, a="00"): hx = hx.lstrip("#"); return f"&H{a}{hx[4:6]}{hx[2:4]}{hx[0:2]}".upper()

def from_srt(srt, out, lang):
    blocks = re.split(r"\n\s*\n", open(srt, encoding="utf-8-sig").read().strip()); segs = []
    for b in blocks:
        L = b.strip().splitlines(); m = next((re.findall(r"(\d+):(\d+):(\d+)[,.](\d+)", l) for l in L if "-->" in l), None)
        if not m or len(m) < 2: continue
        tt = [int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000 for h, mi, s, ms in m[:2]]
        text = " ".join(l for l in L if "-->" not in l and not l.strip().isdigit())
        segs.append({"start": round(tt[0], 3), "end": round(tt[1], 3), "text": {lang: text}, "emph": {}})
    json.dump({"source": lang, "segments": segs}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print(f"{len(segs)} segments -> {out}")

def transcribe(video, out, lang=None):
    try:
        from faster_whisper import WhisperModel
        m = WhisperModel("small", compute_type="int8"); segs, info = m.transcribe(video, language=lang, word_timestamps=False)
        S = [{"start": round(s.start, 3), "end": round(s.end, 3), "text": {info.language: s.text.strip()}, "emph": {}} for s in segs]; src = info.language
    except ImportError:
        try:
            import whisper
            r = whisper.load_model("small").transcribe(video, language=lang); src = r.get("language", lang or "en")
            S = [{"start": round(s["start"], 3), "end": round(s["end"], 3), "text": {src: s["text"].strip()}, "emph": {}} for s in r["segments"]]
        except ImportError:
            raise SystemExit("No transcriber: pip install faster-whisper (or give an SRT / write captions.json by hand).")
    json.dump({"source": src, "segments": S}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print(f"{len(S)} segments ({src}) -> {out}")

def wrap(text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def fit(text, fontpath, size, maxw, max_lines):
    for s in range(size, int(size * 0.75) - 1, -2):
        f = ImageFont.truetype(fontpath, s); L = wrap(text, f, maxw)
        if len(L) <= max_lines: return s, L, True
    f = ImageFont.truetype(fontpath, int(size * 0.75)); return int(size * 0.75), wrap(text, f, maxw), False

def split_for_speed(seg_text, start, end, cps):
    dur = end - start; chars = len(seg_text)
    if chars / max(dur, 0.01) <= cps or len(seg_text.split()) < 4 or dur < 1.6: return [(seg_text, start, end)]
    w = seg_text.split(); k = len(w) // 2; a, b = " ".join(w[:k]), " ".join(w[k:])
    mid = start + dur * len(a) / max(1, len(a) + len(b))
    return split_for_speed(a, start, mid, cps) + split_for_speed(b, mid, end, cps)

def probe(v):
    s = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-print_format", "json", "-show_streams", v]).stdout)["streams"][0]
    return s["width"], s["height"]

def render(video, caps, outdir, langs, font=None, style="bold", pos="lower", platform="reels", accent="#F0662B", max_lines=2, cps=17):
    os.makedirs(outdir, exist_ok=True); W, H = probe(video); C = json.load(open(caps, encoding="utf-8"))
    fontpath = next((p for p in [font] + FONTS if p and os.path.exists(p)), None)
    if not fontpath: raise SystemExit("No TTF font found: pass --font /path/to/font.ttf")
    family = ImageFont.truetype(fontpath, 20).getname()[0]
    top, bot, right = ZONES.get(platform, ZONES["reels"]); margin_lr = int(W * 0.08); maxw = W - margin_lr - int(W * right)
    base = int(W * (0.068 if style == "bold" else 0.055)); mv = int(H * bot) + 20 if pos == "lower" else int(H * 0.40)
    stem = os.path.splitext(os.path.basename(video))[0]; report = ["| lang | captions | shrunk | over 2 lines | split for speed | too fast to read |", "|---|---|---|---|---|---|"]
    for lang in langs:
        events, srt, shr, over, splits, n, fast = [], [], 0, 0, 0, 0, []
        for seg in C["segments"]:
            txt = seg["text"].get(lang)
            if not txt: continue
            emph = (seg.get("emph") or {}).get(lang)
            parts = split_for_speed(txt, seg["start"], seg["end"], cps); splits += len(parts) - 1
            for ptxt, a, b in parts:
                size, lines, ok = fit(ptxt, fontpath, base, maxw, max_lines); shr += size < base; over += not ok; n += 1
                if len(ptxt) / max(b - a, 0.01) > cps * 1.15: fast.append(round(a, 2))
                body = r"\N".join(lines)
                if emph and emph in body.replace(r"\N", " "):
                    for word in emph.split():
                        body = body.replace(word, "{\\c" + ass_color(accent) + "}" + word + "{\\c&H00FFFFFF&}", 1)
                pop = r"{\fs%d\fscx115\fscy115\t(0,90,\fscx100\fscy100)}" % size
                events.append(f"Dialogue: 0,{ts_ass(a)},{ts_ass(b)},Main,,0,0,0,,{pop}{body}")
                srt.append(f"{len(srt) + 1}\n{ts_srt(a)} --> {ts_srt(b)}\n" + "\n".join(lines) + "\n")
        border = 3 if style == "box" else 1; outline = 0 if style == "box" else max(3, base // 14)
        back = ass_color("#000000", "40") if style == "box" else ass_color("#000000", "80")
        ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{family},{base},&H00FFFFFF,&H00FFFFFF,&H00000000,{back},-1,0,0,0,100,100,0,0,{border},{outline},{0 if style == 'box' else 2},2,{margin_lr},{int(W * right)},{mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n"
        ap = os.path.join(outdir, f"{stem}_{lang}.ass"); open(ap, "w", encoding="utf-8").write(ass)
        open(os.path.join(outdir, f"{stem}_{lang}.srt"), "w", encoding="utf-8").write("\n".join(srt))
        fd = os.path.dirname(fontpath); esc = ap.replace("\\", "/").replace(":", "\\:")
        r = run(["ffmpeg", "-loglevel", "error", "-y", "-i", video, "-vf", f"subtitles='{esc}':fontsdir='{fd}'", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                 "-pix_fmt", "yuv420p", "-c:a", "copy", os.path.join(outdir, f"{stem}_{lang}.mp4")])
        if r.returncode: print(r.stderr[-1500:]); sys.exit(1)
        report.append(f"| {lang} | {n} | {shr} | {over} | {splits} | {fast or '-'} |"); print(f"{lang}: {n} captions -> {stem}_{lang}.mp4")
    open(os.path.join(outdir, "check.md"), "w").write("\n".join(report)); print("\n".join(report))

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "from-srt": from_srt(a[2], a[3], opt("--lang", "en"))
    elif len(a) > 3 and a[1] == "transcribe": transcribe(a[2], a[3], opt("--lang"))
    elif len(a) > 4 and a[1] == "render":
        render(a[2], a[3], a[4], opt("--langs", "en").split(","), opt("--font"), opt("--style", "bold"), opt("--pos", "lower"), opt("--platform", "reels"),
               opt("--accent", "#F0662B"), int(opt("--max-lines", 2)), float(opt("--cps", 17)))
    else: print(USAGE)
