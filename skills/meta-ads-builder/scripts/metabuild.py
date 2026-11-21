###############
# Qiyas Sadıqov CC
###############
import csv, json, os, re, sys

USAGE = """meta-ads-builder: turn a strategy blueprint into an exact Meta Ads Manager build (campaigns, ad sets, ads,
audiences to create, exclusions, budgets, naming), audit it against the 2026 platform rules, and print the click path.

  python3 metabuild.py build BLUEPRINT.json OUT_DIR [--ads-per-set 4] [--geo AZ] [--age 18-65] [--month 2611]
      -> build_sheet.csv (one row per campaign / ad set / ad), audiences.md (every custom audience to create, with
         source, window and UI path), naming.md, clickpath.md, audit.md
  python3 metabuild.py audit BLUEPRINT.json                  -> only the audit
  python3 metabuild.py names MARKET STAGE OBJECTIVE GOAL [MONTH] -> naming convention example
BLUEPRINT.json comes from ad-strategy-architect (strategist.py blueprint) or is written by hand with the same fields.
Platform facts used (2026): ~50 optimisation events per ad set per week to exit learning; detailed targeting exclusions
removed (Jan 2025); ad set placement exclusions being removed (account level controls and value rules remain; limited
spend up to 5% per excluded placement); default attribution 7-day click, 1-day engage-through, 1-day view; 7-day and
28-day view windows removed (Jan 2026); Advantage+ is the default setup for Sales, Leads and App; special ad categories
(housing, employment, financial products) are mandatory for audiences in the US, Canada and listed EU countries.
Needs: Python 3 only.
"""

SOURCES = [
    (r"website|visitor|add to cart|viewed items|purchas", "Website (Pixel / Conversions API)", 180, "Audiences > Create audience > Custom audience > Website"),
    (r"video", "Video (Facebook and Instagram)", 365, "Custom audience > Video > choose videos and % watched"),
    (r"ig|instagram|engager|messaged|follow", "Instagram account / Facebook Page engagement", 365, "Custom audience > Instagram account or Facebook Page > engagement type"),
    (r"lead form|leads|form opener|registrant", "Lead form (instant forms)", 90, "Custom audience > Lead form > opened / submitted"),
    (r"customer list|crm|customers|buyers", "Customer list (hashed e-mail / phone)", None, "Custom audience > Customer list (prepare with ad-tracking-setup hash)"),
]
EU_HOUSING = {"US", "CA", "DE", "FR", "ES", "IT", "NL", "BE", "AT", "IE", "SE", "PL", "PT", "DK", "FI", "GR", "CZ", "HU", "RO"}
TR_AZ = str.maketrans("əıöüşğçƏİÖÜŞĞÇ", "eiousgcEIOUSGC")
ABBR = {"Awareness": "AWR", "Engagement": "ENG", "Traffic": "TRF", "Leads": "LEA", "Sales": "SAL", "App": "APP"}

def obj_code(o):
    for k, v in ABBR.items():
        if o.startswith(k): return v
    return "MIX"

def stage_code(s): return re.sub(r"[^A-Z0-9]", "", s.split(":")[0].split(" ")[0].translate(TR_AZ).upper())[:6] or "ST"

def window(text):
    m = re.search(r"(\d+)\s*d", text); return int(m.group(1)) if m else None

def audience_spec(name):
    for pat, src, mx, ui in SOURCES:
        if re.search(pat, name, re.I):
            w = window(name); note = ""
            if mx and w and w > mx: note = f"window {w}d exceeds the {mx}d maximum: use {mx}d"
            return {"name": name, "source": src, "window": w, "max": mx, "ui": ui, "note": note}
    return {"name": name, "source": "check (custom definition)", "window": window(name), "max": None, "ui": "Custom audience", "note": ""}

def names(market, stage, obj, goal, month="2611"): return f"{market}_{stage}_{obj}_{re.sub(r'[^A-Za-z]', '', goal.translate(TR_AZ))[:10].upper()}_{month}"

def audit(bp, geo=None):
    out, b = [], bp.get("brief", {}); geo = geo or b.get("market", "")
    st = bp["stages"]; cat = str(b.get("category", "")).lower()
    if any(k in cat for k in ("real estate", "emlak", "daşınmaz", "property", "mortgage", "rent")) and geo in EU_HOUSING: out.append(("high", "Housing special ad category is mandatory for this geo: no age/gender/zip targeting, no lookalikes, no detailed targeting exclusions; 15 mile minimum radius in the US"))
    elif any(k in cat for k in ("real estate", "emlak", "daşınmaz", "property")): out.append(("info", f"Housing special ad category is not legally required for {geo} audiences, but select it if any audience is in the US, CA or listed EU countries"))
    if any(k in cat for k in ("loan", "kredi", "credit", "insurance", "sigorta", "bank", "invest")) and geo in EU_HOUSING: out.append(("high", "Financial products and services special ad category applies for this geo"))
    for s in st:
        if s.get("learning_ok") is False: out.append(("high", f"{s['stage']}: daily budget {s['daily_budget']} is below ~{s['daily_needed_for_learning']} needed for 50 results/week; use one ad set, merge stages or optimise a more frequent event"))
        if s["daily_budget"] and s["daily_budget"] < (b["monthly_budget"] / b["monthly_budget_usd"] if b.get("monthly_budget") and b.get("monthly_budget_usd") else 1): out.append(("mid", f"{s['stage']}: very small daily budget; delivery will be thin"))
        for a in s["include"]:
            w = audience_spec(a)
            if w["note"]: out.append(("mid", f"{s['stage']}: {a}: {w['note']}"))
    for i, s in enumerate(st):
        for j, t in enumerate(st):
            if i < j and t["include"]:
                def covered(a):
                    sa, wa = audience_spec(a)["source"], window(a) or 0
                    return any(audience_spec(e)["source"] == sa and (window(e) or 9999) >= wa for e in s["exclude"])
                missing = [a for a in t["include"] if not covered(a)]
                if s["include"] == [] and missing: out.append(("low", f"{s['stage']} (broad) does not exclude {', '.join(missing)} from {t['stage']}: some warm people will see cold ads (fine if intended)"))
    if len(st) > 3 and b.get("monthly_budget_usd", 1e9) < 600: out.append(("mid", "4+ campaigns on a small budget: merge into 2 (cold and warm)"))
    out += [("info", "Detailed targeting exclusions no longer exist: exclude with custom audiences only"), ("info", "Placement exclusions at ad set level are being removed: keep Advantage+ placements; use account level placement controls or value rules if needed"),
            ("info", "Default attribution: 7-day click, 1-day engage-through, 1-day view; 7-day and 28-day view are gone, so older reports look higher"),
            ("info", "Do not edit budgets more than ~20% at a time or change creative/targeting during the first 7 days; each significant edit restarts learning")]
    return out

def build(bp_path, out, ads_per_set=4, geo=None, age="18-65", month="2611"):
    bp = json.load(open(bp_path, encoding="utf-8")); b = bp.get("brief", {}); geo = geo or b.get("market", "XX"); os.makedirs(out, exist_ok=True); cur = bp.get("currency", "")
    rows, auds = [], {}
    for s in bp["stages"]:
        sc = stage_code(s["stage"]); oc = obj_code(s["objective"]); cname = names(geo, sc, oc, s["performance_goal"], month)
        rows.append({"level": "campaign", "name": cname, "objective": s["objective"].split(" (")[0], "performance_goal": s["performance_goal"], "budget": f"campaign budget {s['daily_budget']} {cur}/day", "audience": "", "include": "", "exclude": "", "placements": "", "notes": s["message"]})
        aud = "AdvPlus" if not s["include"] else "Warm"
        asname = f"{sc}_{aud}_{geo}_{age.replace('-', '')}"
        rows.append({"level": "ad set", "name": asname, "objective": "", "performance_goal": s["performance_goal"], "budget": "(campaign budget)", "audience": s["audience"], "include": "; ".join(s["include"]),
                     "exclude": "; ".join(s["exclude"]), "placements": "Advantage+ placements", "notes": f"geo {geo}, age {age}, attribution 7d click / 1d engage-through / 1d view"})
        for k in range(1, ads_per_set + 1):
            rows.append({"level": "ad", "name": f"{sc}_C{k:02d}_FORMAT_HOOK_v1", "objective": "", "performance_goal": "", "budget": "", "audience": "", "include": "", "exclude": "", "placements": "", "notes": "distinct concept (persona x angle x format); fill from ad-creative-strategist"})
        for a in s["include"] + s["exclude"]: auds[a] = audience_spec(a)
    with open(os.path.join(out, "build_sheet.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    A = ["# Custom audiences to create (once; they refresh automatically)", "", "| audience | source | window | how |", "|---|---|---|---|"]
    A += [f"| {a['name']} | {a['source']} | {str(a['window']) + 'd' if a['window'] else 'n/a'}{' (max ' + str(a['max']) + 'd)' if a['max'] else ''} | {a['ui']}{'. ' + a['note'] if a['note'] else ''} |" for a in auds.values()]
    A += ["", "Retargeting pools under about 1,000 matched people deliver poorly: widen windows before splitting.", "Customer lists: normalise and SHA-256 hash e-mails and phones (E.164, e.g. +994..., +90...) with ad-tracking-setup before upload."]
    open(os.path.join(out, "audiences.md"), "w", encoding="utf-8").write("\n".join(A))
    open(os.path.join(out, "naming.md"), "w", encoding="utf-8").write("\n".join(["# Naming convention", "Campaign: MARKET_STAGE_OBJECTIVE_GOAL_YYMM, e.g. " + names(geo, "C1", "ENG", "ThruPlay", month), "Ad set: STAGE_AUDIENCE_GEO_AGE, e.g. C1_AdvPlus_" + geo + "_1865",
        "Ad: STAGE_CONCEPT_FORMAT_HOOK_vN, e.g. C1_C03_REEL9x16_PAINQ_v2", "Use the same names in UTM parameters: utm_campaign={{campaign.name}}&utm_term={{adset.name}}&utm_content={{ad.name}}"]))
    C = ["# Click path in Ads Manager (2026)", "1. Events Manager: confirm Pixel + Conversions API, test events, Event Match Quality 6+ (8+ for big spenders).", "2. Audiences: create every audience in audiences.md first, so they fill before launch.",
         "3. Create > choose objective per campaign (Awareness, Traffic, Engagement, Leads, App promotion, Sales). Sales, Leads and App open in Advantage+ setup by default; keep it unless strict stage separation needs original audience controls.",
         "4. Special ad categories: declare housing / employment / financial when the audience includes US, CA or listed EU countries.", "5. Campaign budget (Advantage campaign budget) on; daily budgets from build_sheet.csv.",
         "6. Ad set: conversion location (website, instant form, messaging apps (WhatsApp / Messenger / Instagram), calls, app, Instagram profile), performance goal, attribution default.",
         "7. Audience: Advantage+ audience with suggestions for cold stages; add custom audience exclusions listed in the sheet. Warm stages: include the custom audiences.", "8. Placements: Advantage+ placements. Use 9:16 assets with safe zones plus 4:5 or 1:1.",
         "9. Ads: 3 to 6 genuinely different concepts per ad set (Andromeda groups near duplicates). Add UTM parameters. Partnership ads for creator content.", "10. Publish together, then do not touch for 7 days except to pause clear losers (spend over 2 to 3x target cost per result with no results)."]
    open(os.path.join(out, "clickpath.md"), "w", encoding="utf-8").write("\n".join(C))
    au = audit(bp, geo); md = ["# Audit"] + [f"- [{lvl}] {t}" for lvl, t in au]
    open(os.path.join(out, "audit.md"), "w", encoding="utf-8").write("\n".join(md)); print("\n".join(md)); print(f"\n-> {out}: build_sheet.csv ({len(rows)} rows), audiences.md ({len(auds)} audiences), naming.md, clickpath.md, audit.md")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "build": build(a[2], a[3], int(opt("--ads-per-set", 4)), opt("--geo"), opt("--age", "18-65"), opt("--month", "2611"))
    elif len(a) > 2 and a[1] == "audit": [print(f"- [{l}] {t}") for l, t in audit(json.load(open(a[2], encoding="utf-8")))]
    elif len(a) > 5 and a[1] == "names": print(names(*a[2:7]))
    else: print(USAGE)
