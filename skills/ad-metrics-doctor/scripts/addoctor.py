###############
# Qiyas Sadıqov CC
###############
import csv, os, re, sys
from collections import defaultdict

USAGE = """ad-metrics-doctor: read an ad platform export (Meta Ads Manager CSV in English or Turkish, or any CSV with similar
columns), compute every KPI, diagnose each campaign / ad set / ad through the funnel, and give a verdict with the fix.

  python3 addoctor.py diagnose EXPORT.csv OUT_DIR [--target-cpa 20] [--target-roas 3] [--market-cpm 3.0] [--level ad|adset|campaign]
      -> report.md, verdicts.csv, cpa_chart.png (if Pillow is installed)
  python3 addoctor.py glossary [TERM]          -> advertising glossary (English and Turkish terms, plain definitions)
Diagnosis order (where the funnel breaks): delivery (CPM) > attention (hook rate, thumb stop) > interest (link CTR) >
conversion (CVR, cost per result) > economics (CPA vs target, ROAS) > wear-out (frequency, CTR decay over days) >
learning (results per week per ad set). Verdicts: SCALE, KEEP, FIX_HOOK, FIX_OFFER, FIX_LANDING, FATIGUE, LEARNING, KILL.
Needs: Python 3; Pillow optional for the chart.
"""

ALIASES = {"campaign": ["campaign name", "kampanya adı", "kampanya adi"], "adset": ["ad set name", "reklam seti adı", "reklam seti adi"], "ad": ["ad name", "reklam adı", "reklam adi"],
           "day": ["day", "gün", "reporting starts", "raporlama başlangıcı", "date"], "day_end": ["reporting ends", "raporlama sonu"], "spend": ["amount spent", "harcanan tutar", "spend", "cost"], "impressions": ["impressions", "gösterim"],
           "reach": ["reach", "erişim"], "link_clicks": ["link clicks", "bağlantı tıklamaları", "clicks"], "results": ["results", "sonuçlar"], "purchases": ["purchases", "satın almalar"],
           "value": ["purchases conversion value", "satın alma dönüşüm değeri", "conversion value", "revenue"], "leads": ["leads", "potansiyel müşteriler"],
           "messages": ["messaging conversations started", "başlatılan mesajlaşma sohbetleri"], "v3": ["3-second video plays", "3 saniyelik video oynatmaları", "video plays 3s"], "thruplay": ["thruplays", "thruplay"]}

def find_cols(header):
    h = [x.strip().lower() for x in header]; cols = {}
    for key, al in ALIASES.items():
        for i, name in sorted(enumerate(h), key=lambda c: next((j for j, a in enumerate(al) if c[1].startswith(a)), len(al))):
            if any(name.startswith(a) for a in al) and not (key == "purchases" and ("value" in name or "değer" in name)) and not (key == "link_clicks" and "cost" in name) and not (key in ("results", "spend") and ("per " in name or "başına" in name)):
                cols[key] = i; break
    return cols

def num(x):
    x = (x or "").strip().replace(" ", "")
    if not x or x in ("-", "--"): return 0.0
    if "," in x and "." in x: x = x.replace(".", "").replace(",", ".") if x.rfind(",") > x.rfind(".") else x.replace(",", "")
    elif re.fullmatch(r"-?[1-9]\d{0,2}([.,]\d{3})+", x): x = x.replace(",", "").replace(".", "")
    elif "," in x: x = x.replace(",", ".")
    try: return float(x.replace("%", ""))
    except ValueError: return 0.0

def load(path, level):
    with open(path, encoding="utf-8-sig") as f: txt = f.read()
    head = txt.split("\n", 1)[0]; rows = list(csv.reader(txt.splitlines(True), delimiter=";" if head.count(";") > head.count(",") else ","))
    cols = find_cols(rows[0]); lv = level if level in cols else next((k for k in ("ad", "adset", "campaign") if k in cols), None)
    agg, days = defaultdict(lambda: defaultdict(float)), defaultdict(list)
    for r in rows[1:]:
        if not r or len(r) < len(rows[0]) // 2: continue
        key = r[cols[lv]] if lv else "all"
        if not key or key.lower().startswith(("total", "toplam")): continue
        for k in ("spend", "impressions", "reach", "link_clicks", "results", "purchases", "value", "leads", "messages", "v3", "thruplay"):
            if k in cols: agg[key][k] += num(r[cols[k]])
        if "day" in cols and ("day_end" not in cols or r[cols["day_end"]] == r[cols["day"]]): days[key].append((r[cols["day"]], num(r[cols["impressions"]]) if "impressions" in cols else 0, num(r[cols["link_clicks"]]) if "link_clicks" in cols else 0, num(r[cols["reach"]]) if "reach" in cols else 0))
    return agg, days, lv, cols

def kpis(a):
    k = defaultdict(float, a); imp = a["impressions"] or 1; res = a["results"] or a["purchases"] or a["leads"] or a["messages"]
    k["result_count"] = res; k["cpm"] = a["spend"] / imp * 1000 if a["impressions"] else None; k["ctr"] = a["link_clicks"] / imp * 100 if "link_clicks" in a and a["impressions"] else None; k["cpc"] = a["spend"] / a["link_clicks"] if a["link_clicks"] else None
    k["cvr"] = res / a["link_clicks"] * 100 if a["link_clicks"] else None; k["cpa"] = a["spend"] / res if res else None; k["roas"] = a["value"] / a["spend"] if a["spend"] and a["value"] else None
    k["freq"] = a["impressions"] / a["reach"] if a["reach"] else None; k["hook"] = a["v3"] / imp * 100 if a["v3"] else None; k["hold"] = a["thruplay"] / a["v3"] * 100 if a["v3"] and a["thruplay"] else None
    return k

def decay(series):
    s = sorted(series)
    if len(s) < 6: return None
    ctr = lambda part: sum(x[2] for x in part) / max(1, sum(x[1] for x in part)) * 100
    return ctr(s[:3]), ctr(s[-3:])

def verdict(k, t_cpa, t_roas, m_cpm, dec, days_n):
    why = []; v = "KEEP"
    if k["spend"] == 0: return "NO_DELIVERY", ["no spend: check status, budget, audience size, review"]
    if k["result_count"] == 0 and t_cpa and k["spend"] >= 2.5 * t_cpa: return "KILL", [f"spent {k['spend']:.2f} (over 2.5x target cost per result) with no results"]
    if m_cpm and k["cpm"] and k["cpm"] > 1.8 * m_cpm: why.append(f"CPM {k['cpm']:.2f} is high vs market ~{m_cpm}: audience too narrow, low ad quality ranking, or peak season")
    if k["hook"] is not None and k["hook"] < 20: v = "FIX_HOOK"; why.append(f"hook rate {k['hook']:.1f}% (3s plays / impressions) is low: change the first 1 to 2 seconds")
    if k["ctr"] is not None and k["ctr"] < 0.7 and v == "KEEP": v = "FIX_OFFER"; why.append(f"link CTR {k['ctr']:.2f}% is low: the promise, offer or CTA does not pull")
    if k["cvr"] is not None and k["link_clicks"] >= 50 and k["cvr"] < 2 and v == "KEEP": v = "FIX_LANDING"; why.append(f"conversion rate {k['cvr']:.1f}% after the click is low: landing page, form, chat reply speed or price mismatch")
    if k["freq"] and k["freq"] > 3.5 or (dec and dec[1] < 0.75 * dec[0]): v = "FATIGUE" if v == "KEEP" else v; why.append(f"wear-out: frequency {k['freq'] or 0:.1f}" + (f", CTR fell {dec[0]:.2f}% to {dec[1]:.2f}%" if dec else "") + ": new concepts, not new colours")
    weekly = k["result_count"] / max(1, days_n) * 7 if days_n else None
    if weekly is not None and weekly < 50 and v == "KEEP": why.append(f"about {weekly:.0f} results/week: learning limited; consolidate ad sets or optimise a more frequent event")
    good_cpa = t_cpa and k["cpa"] and k["cpa"] <= t_cpa; good_roas = t_roas and k["roas"] and k["roas"] >= t_roas
    if (good_cpa or good_roas) and v in ("KEEP", "FATIGUE"): v = "SCALE" if v == "KEEP" else v; why.append(f"beats target ({'CPA ' + format(k['cpa'], '.2f') if k['cpa'] else ''}{' ROAS ' + format(k['roas'], '.2f') if k['roas'] else ''}): raise budget 15 to 20% every 2 to 3 days or duplicate into the scaling campaign")
    elif t_cpa and k["cpa"] and k["cpa"] > 1.5 * t_cpa and v == "KEEP": v = "FIX_OFFER"; why.append(f"CPA {k['cpa']:.2f} is over 1.5x target {t_cpa}")
    if v == "KEEP" and weekly is not None and weekly < 50: v = "LEARNING"
    return v, why

def diagnose(path, out, t_cpa=None, t_roas=None, m_cpm=None, level="ad"):
    agg, days, lv, cols = load(path, level); os.makedirs(out, exist_ok=True); rows = []
    tot = defaultdict(float)
    for a in agg.values():
        for k, x in a.items(): tot[k] += x
    T = kpis(tot); ndays = len({d[0] for s in days.values() for d in s}) or None
    for name, a in agg.items():
        k = kpis(a); v, why = verdict(k, t_cpa, t_roas, m_cpm, decay(days.get(name, [])), ndays); rows.append((name, k, v, why))
    rows.sort(key=lambda r: -r[1]["spend"])
    f = lambda x, d=2: "" if x is None else f"{x:.{d}f}"
    md = [f"# Ad diagnosis: {os.path.basename(path)} (level: {lv}, {len(rows)} rows" + (f", {ndays} days" if ndays else "") + ")", "",
          f"Total spend {T['spend']:.2f}, impressions {T['impressions']:.0f}, CPM {f(T['cpm'])}, link CTR {f(T['ctr'])}%, results {T['result_count']:.0f}, cost per result {f(T['cpa'])}" + (f", ROAS {f(T['roas'])}" if T['roas'] else "") + (f", frequency {f(T['freq'])}" if T['freq'] else ""), "",
          "| name | spend | CPM | hook % | CTR % | CVR % | results | CPA | ROAS | freq | verdict |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {n[:40]} | {f(k['spend'])} | {f(k['cpm'])} | {f(k['hook'], 1)} | {f(k['ctr'])} | {f(k['cvr'], 1)} | {k['result_count']:.0f} | {f(k['cpa'])} | {f(k['roas'])} | {f(k['freq'], 1)} | **{v}** |" for n, k, v, _ in rows]
    md += ["", "## Why and what to do"] + [f"- **{n}** ({v}): " + ("; ".join(w) if w else "healthy, leave it alone") for n, k, v, w in rows]
    share = rows[0][1]["spend"] / T["spend"] * 100 if T["spend"] and rows else 0
    if share > 70 and len(rows) > 2: md.append(f"\nNote: one item takes {share:.0f}% of spend. Under Andromeda that is normal; judge the others by whether they add results, not by equal spend.")
    if ndays and "reach" in cols: md.append("\nFrequency from daily rows sums daily reach, so it is a lower bound; export without the day breakdown for true reach.")
    md += ["", "Columns found: " + ", ".join(sorted(cols)), "Reminder: since 2026 the default attribution is 7-day click, 1-day engage-through, 1-day view; compare periods with the same setting."]
    open(os.path.join(out, "report.md"), "w", encoding="utf-8").write("\n".join(md)); print("\n".join(md))
    with open(os.path.join(out, "verdicts.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["name", "spend", "cpm", "hook", "ctr", "cvr", "results", "cpa", "roas", "frequency", "verdict", "why"])
        for n, k, v, why in rows: w.writerow([n, f(k["spend"]), f(k["cpm"]), f(k["hook"]), f(k["ctr"]), f(k["cvr"]), k["result_count"], f(k["cpa"]), f(k["roas"]), f(k["freq"]), v, " | ".join(why)])
    try:
        from PIL import Image, ImageDraw
        data = [(n, k["cpa"]) for n, k, _, _ in rows if k["cpa"]][:15]
        if data:
            W, H = 900, 40 + 28 * len(data); im = Image.new("RGB", (W, H), (16, 16, 16)); d = ImageDraw.Draw(im); mx = max(c for _, c in data)
            for i, (n, c) in enumerate(data):
                y = 20 + i * 28; w = int((W - 330) * c / mx); col = (90, 200, 120) if t_cpa and c <= t_cpa else (230, 90, 80) if t_cpa else (120, 170, 255)
                d.text((10, y + 4), n[:38], fill=(220, 220, 220)); d.rectangle([300, y, 300 + w, y + 20], fill=col); d.text((306 + w, y + 4), f"{c:.2f}", fill=(220, 220, 220))
            if t_cpa: x = 300 + int((W - 330) * t_cpa / mx); d.line([(x, 10), (x, H - 10)], fill=(255, 210, 80), width=2)
            im.save(os.path.join(out, "cpa_chart.png"))
    except ImportError: pass

GLOSSARY = [
 ("Impressions / Gösterim", "times an ad was shown"), ("Reach / Erişim", "unique people who saw it"), ("Frequency / Sıklık", "impressions / reach; over ~3.5 per week on cold audiences usually means wear-out"),
 ("CPM / BGBM (bin gösterim başına maliyet)", "cost per 1,000 impressions; the price of attention, set by the auction"), ("CTR (link) / Bağlantı TO", "link clicks / impressions; 'all clicks' CTR includes likes and profile taps"),
 ("CPC / TBM", "cost per (link) click"), ("CVR / Dönüşüm oranı", "results / link clicks"), ("CPA, CPL, CPR / Sonuç başına maliyet", "cost per acquisition / lead / result"),
 ("ROAS / Reklam harcamasının getirisi", "revenue / ad spend; breakeven ROAS = 1 / gross margin"), ("MER / Blended ROAS", "total revenue / total marketing spend; the honest business view"),
 ("AOV / Ortalama sepet", "average order value"), ("LTV / Müşteri yaşam boyu değeri", "gross profit from a customer over time"), ("CAC / Müşteri edinme maliyeti", "all acquisition cost / new customers"),
 ("Hook rate / Thumb-stop", "3-second video plays / impressions; 25 to 35% is good on Reels"), ("Hold rate", "ThruPlays (15s or complete) / 3-second plays"), ("ThruPlay", "video watched 15 seconds or to the end"),
 ("Learning phase / Öğrenme aşaması", "the delivery system explores until about 50 optimisation events per ad set per week; 'Learning limited' means it cannot get there"),
 ("Significant edit", "budget change over ~20%, new creative, targeting or bid change: restarts learning"), ("Objective / Hedef", "Awareness, Traffic, Engagement, Leads, App promotion, Sales"),
 ("Performance goal / Performans hedefi", "what the ad set optimises for (e.g. ThruPlay, landing page views, leads, conversion leads, conversations, purchases, value)"),
 ("Conversion location / Dönüşüm konumu", "website, app, instant form, messaging apps (WhatsApp, Messenger, Instagram), calls, Instagram profile"),
 ("Advantage+ (campaign, audience, placements, creative)", "Meta automation that decides audience, placements, budget split and creative variations"), ("Advantage campaign budget (CBO)", "budget at campaign level shared across ad sets"),
 ("ABO", "budget at ad set level (manual control, good for clean tests)"), ("Bid strategies", "highest volume (default), cost per result goal (cost cap), ROAS goal (min ROAS), bid cap"),
 ("Value rules / Değer kuralları", "bid more or less for chosen audiences, placements, devices"), ("Custom audience / Özel hedef kitle", "people from your sources: website, video viewers, IG/FB engagers, lead forms, customer list"),
 ("Lookalike / Benzer hedef kitle", "people similar to a seed audience (largely absorbed by Advantage+ audience)"), ("Advantage+ audience", "broad delivery where your targeting inputs are suggestions"),
 ("Special ad categories / Özel reklam kategorileri", "housing, employment, financial products, social issues; restricted targeting in the US, CA, listed EU countries"),
 ("Pixel / Piksel", "browser tag that sends website events"), ("Conversions API (CAPI)", "server-to-server events; with deduplication via event_id"), ("Event Match Quality (EMQ)", "0 to 10 score of how well events match people; aim 6+, 8+ at scale"),
 ("Conversion leads (CRM)", "optimise instant form campaigns for leads that become qualified in your CRM"), ("Attribution setting / İlişkilendirme", "2026 default: 7-day click, 1-day engage-through, 1-day view"),
 ("Engage-through attribution", "conversions after non-link interactions or 5s+ video views (renamed from engaged-view in 2026)"), ("Incrementality / Lift test", "test vs holdout to measure what ads truly caused"),
 ("Andromeda", "Meta's 2025 retrieval system; rewards genuinely different creatives, groups near duplicates into one entity"), ("Creative fatigue", "performance drop as the same people see the same concept"),
 ("Partnership ads / Spark Ads", "creator or organic posts run as ads from the creator handle (Meta / TikTok)"), ("Instant form / Anında form", "native lead form; 'higher intent' adds a review step"),
 ("Click to message / Mesaj reklamları", "ads that open WhatsApp, Messenger or Instagram Direct"), ("Retargeting / Yeniden hedefleme", "ads to people who already interacted"), ("Prospecting / Soğuk kitle", "ads to people who never interacted"),
 ("TOFU / MOFU / BOFU", "top, middle, bottom of funnel"), ("UTM", "URL parameters that tell analytics which ad brought the visit"), ("Dark post", "ad-only post not shown on the page feed"), ("Breakeven CPA", "price x gross margin")]

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "diagnose":
        g = lambda k: float(opt(k)) if opt(k) else None
        diagnose(a[2], a[3], g("--target-cpa"), g("--target-roas"), g("--market-cpm"), opt("--level", "ad"))
    elif len(a) > 1 and a[1] == "glossary":
        q = " ".join(a[2:]).lower(); [print(f"- **{t}**: {d}") for t, d in GLOSSARY if q in t.lower() or q in d.lower()]
    else: print(USAGE)
