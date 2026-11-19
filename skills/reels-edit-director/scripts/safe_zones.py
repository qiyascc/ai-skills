###############
# Qiyas Sadıqov CC
###############
import argparse
import struct
import sys
import zlib

WIDTH, HEIGHT = 1080, 1920

PLATFORMS = {
    "instagram": {"label": "Instagram Reels", "top": 250, "bottom": 420, "left": 60, "right": 120,
                  "source": "common creator practice for organic Reels, not an official Meta number"},
    "instagram-ads": {"label": "Instagram Reels ads", "top": 269, "bottom": 672, "left": 65, "right": 65,
                      "source": "Meta ads guide: keep 14% top, 35% bottom, 6% each side clear"},
    "tiktok": {"label": "TikTok", "top": 240, "bottom": 660, "left": 120, "right": 120,
               "source": "third-party guides; TikTok publishes template files, not pixel numbers"},
    "shorts": {"label": "YouTube Shorts", "top": 240, "bottom": 660, "left": 120, "right": 120,
               "source": "approximation; YouTube shows the real guides in the Shorts editor"},
    "all": {"label": "Organic Reels, TikTok and Shorts", "top": 250, "bottom": 660, "left": 120, "right": 120,
            "source": "union of the instagram, tiktok and shorts presets"},
}

def safe_rect(p):
    return p["left"], p["top"], WIDTH - p["left"] - p["right"], HEIGHT - p["top"] - p["bottom"]

def svg(p, grid):
    x, y, w, h = safe_rect(p)
    shade = "fill='#ff2d55' fill-opacity='0.28'"
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{WIDTH}' height='{HEIGHT}' viewBox='0 0 {WIDTH} {HEIGHT}'>",
        f"<rect x='0' y='0' width='{WIDTH}' height='{p['top']}' {shade}/>",
        f"<rect x='0' y='{HEIGHT - p['bottom']}' width='{WIDTH}' height='{p['bottom']}' {shade}/>",
        f"<rect x='0' y='{p['top']}' width='{p['left']}' height='{h}' {shade}/>",
        f"<rect x='{WIDTH - p['right']}' y='{p['top']}' width='{p['right']}' height='{h}' {shade}/>",
        f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='none' stroke='#00e5ff' stroke-width='4' stroke-dasharray='18 12'/>",
    ]
    for i in (1, 2):
        parts.append(f"<line x1='{WIDTH * i / 3:.0f}' y1='0' x2='{WIDTH * i / 3:.0f}' y2='{HEIGHT}' stroke='#ffffff' stroke-opacity='0.25' stroke-width='2'/>")
        parts.append(f"<line x1='0' y1='{HEIGHT * i / 3:.0f}' x2='{WIDTH}' y2='{HEIGHT * i / 3:.0f}' stroke='#ffffff' stroke-opacity='0.25' stroke-width='2'/>")
    if grid:
        gh = WIDTH * 4 / 3
        gy = (HEIGHT - gh) / 2
        parts.append(f"<rect x='0' y='{gy:.0f}' width='{WIDTH}' height='{gh:.0f}' fill='none' stroke='#ffd60a' stroke-width='3' stroke-dasharray='8 10'/>")
    parts.append(f"<text x='{x + 16}' y='{y + 44}' font-family='Helvetica, Arial, sans-serif' font-size='34' fill='#00e5ff'>{p['label']} safe area</text>")
    parts.append("</svg>")
    return "\n".join(parts)

def png(p, grid):
    buf = bytearray(WIDTH * HEIGHT * 4)

    def fill(x0, y0, x1, y1, rgba):
        x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(WIDTH, int(x1)), min(HEIGHT, int(y1))
        row = bytes(rgba) * (x1 - x0)
        for y in range(y0, y1):
            i = (y * WIDTH + x0) * 4
            buf[i:i + len(row)] = row

    def dashed_rect(x, y, w, h, t, dash, gap, rgba):
        step = dash + gap
        for d in range(0, int(w), step):
            fill(x + d, y, min(x + d + dash, x + w), y + t, rgba)
            fill(x + d, y + h - t, min(x + d + dash, x + w), y + h, rgba)
        for d in range(0, int(h), step):
            fill(x, y + d, x + t, min(y + d + dash, y + h), rgba)
            fill(x + w - t, y + d, x + w, min(y + d + dash, y + h), rgba)

    red = (255, 45, 85, 72)
    x, y, w, h = safe_rect(p)
    fill(0, 0, WIDTH, p["top"], red)
    fill(0, HEIGHT - p["bottom"], WIDTH, HEIGHT, red)
    fill(0, p["top"], p["left"], HEIGHT - p["bottom"], red)
    fill(WIDTH - p["right"], p["top"], WIDTH, HEIGHT - p["bottom"], red)
    for i in (1, 2):
        fill(WIDTH * i // 3 - 1, 0, WIDTH * i // 3 + 1, HEIGHT, (255, 255, 255, 64))
        fill(0, HEIGHT * i // 3 - 1, WIDTH, HEIGHT * i // 3 + 1, (255, 255, 255, 64))
    if grid:
        gh = WIDTH * 4 // 3
        dashed_rect(0, (HEIGHT - gh) // 2, WIDTH, gh, 3, 8, 10, (255, 214, 10, 255))
    dashed_rect(x, y, w, h, 4, 18, 12, (0, 229, 255, 255))

    raw = b"".join(b"\x00" + bytes(buf[r * WIDTH * 4:(r + 1) * WIDTH * 4]) for r in range(HEIGHT))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))

def main():
    ap = argparse.ArgumentParser(description="Safe-zone overlay (SVG, 1080x1920) for vertical video, or a check for one text box.")
    ap.add_argument("--platform", choices=PLATFORMS, default="all", help="Platform (default: all, the strictest union).")
    ap.add_argument("--check", nargs=4, type=int, metavar=("X", "Y", "W", "H"), help="Check a text box in 1080x1920 pixels.")
    ap.add_argument("--grid", action="store_true", help="Also draw the centred 3:4 band (1080x1440) that the Instagram profile grid shows.")
    ap.add_argument("-o", "--output", help="Write the overlay here. A .png name writes a PNG (works in CapCut and phone apps), anything else writes SVG. Without it, SVG goes to stdout.")
    a = ap.parse_args()
    p = PLATFORMS[a.platform]

    if a.check:
        bx, by, bw, bh = a.check
        x, y, w, h = safe_rect(p)
        problems = []
        if by < y:
            problems.append(f"top edge {y - by}px into the top UI zone")
        if by + bh > y + h:
            problems.append(f"bottom edge {by + bh - (y + h)}px into the caption and button zone")
        if bx < x:
            problems.append(f"left edge {x - bx}px too close to the screen edge")
        if bx + bw > x + w:
            problems.append(f"right edge {bx + bw - (x + w)}px into the action buttons column")
        print(f"{p['label']}: safe area x {x} to {x + w}, y {y} to {y + h} ({p['source']})")
        print("OK, the box is inside the safe area." if not problems else "Move it: " + "; ".join(problems) + ".")
        sys.exit(1 if problems else 0)

    if a.output and a.output.lower().endswith(".png"):
        with open(a.output, "wb") as f:
            f.write(png(p, a.grid))
        print(f"Wrote {a.output} ({p['source']}). Import it as the top layer, set opacity around 50 %, and hide it before export.")
        return
    out = svg(p, a.grid)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Wrote {a.output} ({p['source']}). Import it as the top layer, set opacity around 50 %, and hide it before export.")
    else:
        print(out)

if __name__ == "__main__":
    main()
