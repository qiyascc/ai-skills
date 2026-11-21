###############
# Qiyas Sadıqov CC
###############
import json, os, subprocess, sys

USAGE = """ad-platform-playbook: how each ad platform works (objectives, targeting, formats, minimums, strengths), a
platform mix recommender by market, goal and budget, and an asset spec checker for images and videos.

  python3 platforms.py list                                    -> platforms in the playbook
  python3 platforms.py card meta|tiktok|google|youtube|reddit|linkedin|telegram|x|snapchat|pinterest|yandex
  python3 platforms.py mix --market AZ --goal leads --budget-usd 900 [--b2b] [--young] [--category "real estate"]
  python3 platforms.py specs FILE [FILE ...] --placement meta_reels|meta_feed|meta_stories|tiktok|youtube_shorts|youtube_instream|reddit_feed|linkedin_feed|pinterest|snapchat
Facts are 2026 snapshots (sources in the skill); minimums and features change, so confirm in each Ads Manager.
Needs: Python 3; ffprobe for video checks; Pillow for image checks.
"""

P = {
 "meta": {"name": "Meta (Facebook, Instagram, Messenger, WhatsApp, Threads)", "objectives": "Awareness, Traffic, Engagement, Leads, App promotion, Sales; Advantage+ is the default for Sales, Leads, App",
          "targeting": "broad / Advantage+ audience (inputs are suggestions), custom audiences (website 180d, engagement and video 365d, lead forms 90d, customer lists), lookalikes; detailed targeting exclusions removed; creative diversification is the main lever (Andromeda)",
          "formats": "Reels and Stories 9:16, feed 4:5 / 1:1, carousel, collection, catalog ads, instant forms, click to WhatsApp / Messenger / Instagram Direct, partnership ads, calls",
          "minimum": "very low technical minimum; plan (expected cost per result x 50) / 7 per ad set per day to exit learning",
          "strength": "reach in AZ and TR, messaging commerce, lead forms, retargeting, catalog", "watch": "special ad categories for housing / employment / finance in US, CA, EU; attribution is 7d click + 1d engage-through + 1d view"},
 "tiktok": {"name": "TikTok Ads", "objectives": "Reach, Traffic, Video views, Community interaction, Lead generation, App promotion, Sales; Smart+ automation",
            "targeting": "broad works best; interests, behaviours, custom and lookalike audiences; search ads in TikTok search", "formats": "In-feed 9:16, Spark Ads (boost organic or creator posts), TopView, Lead gen forms, catalog",
            "minimum": "daily budget over 50 USD per campaign and over 20 USD per ad group; conversion campaigns practically need 100 to 250 USD/day per ad group", "strength": "under-35 attention, creator content, cheap reach", "watch": "creative wears out faster than Meta; check ad availability and reach for your country in Ads Manager"},
 "google": {"name": "Google Ads (Search, Performance Max, Demand Gen, Shopping)", "objectives": "Sales, Leads, Website traffic, App, Awareness; Search with AI Max, PMax across all inventory, Demand Gen on YouTube, Discover, Gmail, Maps",
            "targeting": "keywords and search intent, audience signals, customer match, locations", "formats": "text ads, responsive display, video, product feeds", "minimum": "no hard minimum; budget for 30+ conversions/month per campaign for smart bidding",
            "strength": "captures existing demand (people searching 'menzil satışı Bakı', 'kiralık daire')", "watch": "add negative keywords; PMax and Demand Gen can overlap"},
 "youtube": {"name": "YouTube (via Google Ads: Demand Gen, video campaigns)", "objectives": "Awareness, consideration, conversions (Demand Gen)", "targeting": "audiences, topics, keywords, customer match, placements",
             "formats": "Shorts 9:16, in-stream 16:9 (skippable after 5s), bumper 6s, in-feed", "minimum": "no hard minimum", "strength": "largest share of social traffic in AZ (2026) and about 40% of internet traffic in TR", "watch": "first 5 seconds must earn the view; brand in the first seconds"},
 "reddit": {"name": "Reddit Ads", "objectives": "Awareness, Consideration (traffic, engagement, video views), Conversions, App installs", "targeting": "communities (subreddits), interests, keywords in feed and conversation placements, custom audiences",
            "formats": "promoted posts (image, video, carousel), conversation ads in comment threads, product ads", "minimum": "about 5 USD/day", "strength": "research and purchase intent, tech, gaming, finance, niche hobbies; English-speaking markets",
            "watch": "users dislike salesy ads: write like a member; small reach in AZ and TR"},
 "linkedin": {"name": "LinkedIn Ads", "objectives": "Brand awareness, Website visits, Engagement, Video views, Lead generation, Conversions", "targeting": "job title, function, seniority, company, industry, skills, matched audiences",
              "formats": "single image, document, video, carousel, conversation, lead gen forms, thought leader ads", "minimum": "about 10 USD/day per campaign", "strength": "B2B decision makers", "watch": "CPCs are high; use for B2B only"},
 "telegram": {"name": "Telegram Ads", "objectives": "promote channels, bots, posts, mini apps; external links only in the EUR cabinet", "targeting": "contextual: channels, topics, languages, countries (no personal data)",
              "formats": "160-character sponsored message with a button; media in the EUR cabinet", "minimum": "TON/Gram cabinet min CPM about 0.1; EUR cabinet via agencies (deposit minimums vary by agency and niche)", "strength": "news and Russian-speaking audiences, Uzbekistan, crypto, channels", "watch": "contextual only; measure with UTM and bot starts"},
 "x": {"name": "X Ads", "objectives": "Reach, Engagement, Video views, Website traffic, App installs", "targeting": "keywords, follower lookalikes, interests, conversation topics", "formats": "promoted posts, video, carousel", "minimum": "no hard minimum", "strength": "news, sports, tech moments in TR", "watch": "brand safety settings"},
 "snapchat": {"name": "Snapchat Ads", "objectives": "Awareness, Consideration, Conversions", "targeting": "demographics, interests, lookalikes", "formats": "single image/video 9:16, story, collection, AR lenses", "minimum": "about 5 USD/day", "strength": "Saudi Arabia, UAE, young audiences", "watch": "small in AZ and TR"},
 "pinterest": {"name": "Pinterest Ads", "objectives": "Awareness, Consideration, Conversions, Catalog sales", "targeting": "keywords, interests, actalikes", "formats": "2:3 pins, video, carousel, collections", "minimum": "low", "strength": "home, fashion, weddings, planning", "watch": "small in AZ"},
 "yandex": {"name": "Yandex Direct", "objectives": "Search and network ads", "targeting": "keywords, audiences", "formats": "text, image, video", "minimum": "varies", "strength": "Russia, Belarus, Kazakhstan, Russian speakers", "watch": "not relevant for most AZ and TR campaigns"},
}
SPECS = {"meta_reels": {"ratio": (9, 16), "tol": 0.01, "min": (500, 889), "rec": (1080, 1920), "dur": (1, 90), "safe": "keep text and logos out of the top 14% and bottom 20% (and right edge icons)"},
         "meta_stories": {"ratio": (9, 16), "tol": 0.01, "min": (500, 889), "rec": (1080, 1920), "dur": (1, 120), "safe": "top 14% and bottom 20% clear"},
         "meta_feed": {"ratio": (4, 5), "alt": [(1, 1)], "tol": 0.03, "min": (600, 600), "rec": (1080, 1350), "dur": (1, 240), "safe": "primary text ~125 chars, headline ~40"},
         "tiktok": {"ratio": (9, 16), "tol": 0.01, "min": (540, 960), "rec": (1080, 1920), "dur": (5, 60), "safe": "keep text away from the right side icons and bottom caption area"},
         "youtube_shorts": {"ratio": (9, 16), "tol": 0.01, "min": (720, 1280), "rec": (1080, 1920), "dur": (1, 60), "safe": "brand in first seconds"},
         "youtube_instream": {"ratio": (16, 9), "tol": 0.01, "min": (1280, 720), "rec": (1920, 1080), "dur": (6, 180), "safe": "skippable after 5s: brand and hook in 5s"},
         "reddit_feed": {"ratio": (4, 5), "alt": [(1, 1), (16, 9)], "tol": 0.03, "min": (400, 300), "rec": (1080, 1350), "dur": (5, 180), "safe": "native look, text overlay ok"},
         "linkedin_feed": {"ratio": (1, 1), "alt": [(4, 5), (16, 9)], "tol": 0.03, "min": (360, 360), "rec": (1200, 1200), "dur": (3, 1800), "safe": "captions on"},
         "pinterest": {"ratio": (2, 3), "tol": 0.03, "min": (600, 900), "rec": (1000, 1500), "dur": (4, 900), "safe": "text in middle area"},
         "snapchat": {"ratio": (9, 16), "tol": 0.01, "min": (1080, 1920), "rec": (1080, 1920), "dur": (3, 180), "safe": "top and bottom 150 px clear"}}
STRENGTH = {"AZ": {"meta": 3, "youtube": 1.5, "google": 1.2, "tiktok": 1.2, "telegram": 0.7}, "TR": {"meta": 3, "google": 2.5, "youtube": 2, "tiktok": 2, "x": 0.6},
            "KZ": {"meta": 2.5, "tiktok": 2, "telegram": 1.5, "google": 1.5, "yandex": 1}, "UZ": {"telegram": 3, "meta": 2, "google": 1, "youtube": 1}, "GE": {"meta": 3, "google": 1.5, "tiktok": 1},
            "AE": {"meta": 2.5, "google": 2.5, "tiktok": 2, "snapchat": 1.5, "linkedin": 1}, "SA": {"snapchat": 2.5, "tiktok": 2.5, "meta": 2, "google": 2, "x": 1}, "default": {"meta": 3, "google": 2.5, "youtube": 1.5, "tiktok": 1.5, "reddit": 0.8}}
MIN_MONTH_USD = {"tiktok": 600, "linkedin": 300, "google": 150, "youtube": 150, "reddit": 150, "telegram": 300, "snapchat": 150}

def mix(market, goal, budget, b2b=False, young=False, category=""):
    w = dict(STRENGTH.get(market, STRENGTH["default"])); c = category.lower()
    if b2b: w["linkedin"] = w.get("linkedin", 0) + 2.5; w["tiktok"] = w.get("tiktok", 0) * 0.5
    if young: w["tiktok"] = w.get("tiktok", 0) + 0.8
    if goal in ("leads", "sales") and any(k in c for k in ("real estate", "emlak", "daşınmaz", "car", "auto", "insurance", "course", "clinic")): w["google"] = w.get("google", 0) + 0.5
    if goal == "messages": w["meta"] = w.get("meta", 0) + 2
    if goal == "awareness": w["youtube"] = w.get("youtube", 0) + 1
    order = sorted(w.items(), key=lambda kv: -kv[1]); chosen = []; left = budget
    for k, s in order:
        need = MIN_MONTH_USD.get(k, 0)
        fits = all(budget * w[c] / (sum(w[x] for x in chosen) + s) >= MIN_MONTH_USD.get(c, 0) for c in chosen + [k])
        if not chosen or (fits and left - need >= budget * 0.35 and budget >= 500): chosen.append(k); left -= need
        if budget < 500 and len(chosen) == 1: break
        if len(chosen) >= (2 if budget < 1500 else 3 if budget < 5000 else 4): break
    tot = sum(w[k] for k in chosen); print(f"# Platform mix: {market}, goal {goal}, about {budget:.0f} USD/month" + (", B2B" if b2b else ""))
    for k in chosen:
        share = w[k] / tot; print(f"- {P[k]['name']}: {share:.0%} (~{budget * share:,.0f} USD) | {P[k]['strength']}" + (f" | needs at least ~{MIN_MONTH_USD[k]} USD/month to work" if k in MIN_MONTH_USD else ""))
    if budget < 500: print("- Small budget: one platform done well beats three done thinly. Start with Meta; add search when demand exists.")
    print("- Re-split monthly by cost per qualified result, not by platform-reported ROAS alone (each platform credits itself).")

def ratio_ok(w, h, s):
    for r in [s["ratio"]] + s.get("alt", []):
        if abs(w / h - r[0] / r[1]) / (r[0] / r[1]) <= s["tol"]: return True, f"{r[0]}:{r[1]}"
    return False, f"{w}x{h} ({w / h:.3f})"

def specs(files, placement):
    s = SPECS[placement]; print(f"# Spec check for {placement} (wants {s['ratio'][0]}:{s['ratio'][1]}, recommended {s['rec'][0]}x{s['rec'][1]})")
    for f in files:
        issues, info = [], ""
        if f.lower().endswith((".mp4", ".mov", ".m4v", ".webm")):
            pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", f], capture_output=True, encoding="utf-8", errors="replace").stdout or "{}")
            v = next((x for x in pr.get("streams", []) if x["codec_type"] == "video"), None)
            if not v: print(f"- {f}: not readable"); continue
            w, h = int(v["width"]), int(v["height"])
            if int(float(v.get("tags", {}).get("rotate") or next((d["rotation"] for d in v.get("side_data_list", []) if "rotation" in d), 0))) % 180: w, h = h, w
            dur = float(pr["format"]["duration"]); has_a = any(x["codec_type"] == "audio" for x in pr["streams"]); size = os.path.getsize(f) / 1e6
            info = f"{w}x{h}, {dur:.1f}s, {'audio' if has_a else 'NO audio'}, {size:.1f} MB"
            if not (s["dur"][0] <= dur <= s["dur"][1]): issues.append(f"duration {dur:.1f}s outside {s['dur'][0]} to {s['dur'][1]}s")
            if not has_a and placement in ("meta_reels", "tiktok", "youtube_shorts", "snapchat"): issues.append("no audio track: sound-on placements perform better with audio")
        else:
            from PIL import Image
            im = Image.open(f); w, h = im.size
            if im.getexif().get(0x0112) in (5, 6, 7, 8): w, h = h, w
            info = f"{w}x{h} image"
        ok, r = ratio_ok(w, h, s)
        if not ok: issues.append(f"aspect {r} does not match")
        if w < s["min"][0] or h < s["min"][1]: issues.append(f"below minimum {s['min'][0]}x{s['min'][1]}")
        elif w < s["rec"][0]: issues.append(f"below recommended {s['rec'][0]}x{s['rec'][1]} (may look soft)")
        print(f"- {os.path.basename(f)} ({info}): " + ("; ".join(issues) if issues else "OK") + f". Safe zone: {s['safe']}")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 1 and a[1] == "list": [print(f"{k:10s} {v['name']}") for k, v in P.items()]
    elif len(a) > 2 and a[1] == "card": p = P[a[2]]; print(f"# {p['name']}"); [print(f"- {k}: {p[k]}") for k in ("objectives", "targeting", "formats", "minimum", "strength", "watch")]
    elif len(a) > 1 and a[1] == "mix": mix(opt("--market", "AZ").upper(), opt("--goal", "leads"), float(opt("--budget-usd", 1000)), "--b2b" in a, "--young" in a, opt("--category", ""))
    elif len(a) > 2 and a[1] == "specs": specs([x for x in a[2:] if not x.startswith("--") and x != opt("--placement")], opt("--placement", "meta_reels"))
    else: print(USAGE)
