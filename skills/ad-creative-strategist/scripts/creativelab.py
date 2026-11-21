###############
# Qiyas Sadıqov CC
###############
import csv, itertools, json, os, re, sys

USAGE = """ad-creative-strategist: generate a diversified creative matrix (persona x angle x awareness level x format),
hooks and copy in Azerbaijani, Turkish, Russian or English, lint copy against placement limits, local ad law and
Meta policy, and score how different a set of concepts really is (Andromeda groups near duplicates).

  python3 creativelab.py matrix BRIEF.json OUT_DIR [--n 12] [--lang tr|az|ru|en] [--stage cold|warm|hot]
      -> concepts.csv + concepts.md: concept id, persona, angle, awareness level, format, hook, body framework, CTA, proof needed
  python3 creativelab.py hooks LEVEL [--lang tr]       -> hook templates for unaware | problem | solution | product | most
  python3 creativelab.py lint COPY.csv [--market TR|AZ] -> COPY.csv columns: id, primary_text, headline, description, placement
  python3 creativelab.py diversity CONCEPTS.csv         -> pairwise similarity of concepts (persona, angle, format, creator, hook, setting)
BRIEF.json: offer, category, audience, benefits[], proof[], objections[], price, guarantee, market, personas[] (optional).
Needs: Python 3 only.
"""

ANGLES = [("pain", "name the exact pain in their words", "problem"), ("desire", "show the dream outcome", "unaware"), ("proof", "results, numbers, testimonials", "product"),
          ("comparison", "us vs the usual way (no named competitor)", "solution"), ("objection", "answer the top objection head on", "product"), ("offer", "price, bonus, guarantee, deadline", "most"),
          ("story", "a customer or founder story with a turn", "unaware"), ("authority", "expert explains a mistake", "problem"), ("demo", "show it working in 10 seconds", "solution"),
          ("behind the scenes", "how it is made or delivered", "product"), ("myth", "bust a common belief", "problem"), ("social", "many people already do it", "solution")]
FORMATS = [("Reel 9:16 talking head", "video"), ("Reel 9:16 UGC / creator", "video"), ("Reel 9:16 demo with captions", "video"), ("4:5 static with one bold line", "image"),
           ("carousel 1:1 (steps or listings)", "carousel"), ("4:5 testimonial quote card", "image"), ("Story 9:16 poll / question style", "video"), ("before / after (only where policy allows)", "image")]
FRAMEWORKS = {"PAS": "Problem, Agitate, Solution", "AIDA": "Attention, Interest, Desire, Action", "BAB": "Before, After, Bridge", "4U": "Useful, Urgent, Unique, Ultra specific", "FAB": "Feature, Advantage, Benefit", "PASTOR": "Problem, Amplify, Story, Transformation, Offer, Response"}
HOOKS = {
 "en": {"unaware": ["Nobody tells you this about {topic}", "I tried {topic} for 30 days", "This is what {audience} do differently"], "problem": ["Still {pain}?", "The real reason you {pain}", "Stop {mistake}. Do this instead"],
        "solution": ["{solution} vs {old_way}: which works?", "3 ways to {outcome}, ranked", "How {audience} get {outcome} without {pain}"], "product": ["Why {offer} costs {price}", "{n} people already {outcome} with {offer}", "Everything you get in {offer}"],
        "most": ["Last {n} places at {price}", "{offer}: {bonus} until {deadline}", "Ready? Message us 'START'"]},
 "tr": {"unaware": ["{topic} hakkında kimsenin söylemediği şey", "{topic} için 30 gün denedim", "{audience} bunu farklı yapıyor"], "problem": ["Hâlâ {pain} mı?", "{pain} yaşamanın asıl sebebi", "{mistake} yapmayı bırakın"],
        "solution": ["{solution} mi {old_way} mı?", "{outcome} için 3 yol", "{pain} olmadan {outcome}"], "product": ["{offer} neden {price}?", "{n} kişi {offer} ile {outcome}", "{offer} içinde neler var?"],
        "most": ["{price} fiyatla son {n} kontenjan", "{deadline} tarihine kadar {bonus} hediye", "Hazırsanız 'BAŞLA' yazın"]},
 "az": {"unaware": ["{topic} haqqında heç kimin demədiyi şey", "{topic} üçün 30 gün sınadım", "{audience} bunu fərqli edir"], "problem": ["Hələ də {pain}?", "{pain} əsl səbəbi", "{mistake} etməyi dayandırın"],
        "solution": ["{solution}, yoxsa {old_way}?", "{outcome} üçün 3 yol", "{pain} olmadan {outcome}"], "product": ["{offer} niyə {price}?", "{n} nəfər artıq {offer} ilə {outcome}", "{offer} daxilində nələr var?"],
        "most": ["{price} qiymətə son {n} yer", "{deadline} tarixinədək {bonus} hədiyyə", "Hazırsınızsa 'BAŞLA' yazın"]},
 "ru": {"unaware": ["Об этом в {topic} никто не говорит", "Я пробовал {topic} 30 дней", "{audience} делают это иначе"], "problem": ["Всё ещё {pain}?", "Настоящая причина: {pain}", "Хватит {mistake}"],
        "solution": ["{solution} или {old_way}?", "3 способа {outcome}", "{outcome} без {pain}"], "product": ["Почему {offer} стоит {price}", "{n} человек уже {outcome} с {offer}", "Что входит в {offer}"],
        "most": ["Последние {n} мест по {price}", "До {deadline}: {bonus} в подарок", "Готовы? Напишите 'СТАРТ'"]}}
CTA = {"en": ["Message us", "Book a free call", "See prices", "Get the plan"], "tr": ["Bize yazın", "Ücretsiz görüşme alın", "Fiyatları görün", "Detaylar için tıklayın"],
       "az": ["Bizə yazın", "Pulsuz konsultasiya", "Qiymətlərə baxın", "Ətraflı məlumat"], "ru": ["Напишите нам", "Бесплатная консультация", "Узнать цены", "Подробнее"]}
LIMITS = {"feed": (125, 40, 30), "reels": (72, 40, 0), "stories": (125, 40, 0), "marketplace": (125, 40, 20), "carousel": (80, 45, 18), "reddit": (300, 150, 0), "tiktok": (100, 0, 0), "telegram": (160, 0, 0)}
RISK = {"TR": [(r"\ben ucuz\b|\ben iyi\b|1 numara|bir numaralı|lider\b", "superlative claim: needs provable evidence (Reklam Kurulu)"), (r"garanti", "guarantee: state terms clearly"), (r"%\s?\d+\s*indirim|\d+\s?%\s*indirim|indirim", "discount: the previous price must be real and documented (Aug 2026 rules)"),
                (r"son \d+|sadece bugün|stoklarla sınırlı", "scarcity: must be true"), (r"kesin|mucize|anında", "absolute promise: risky"), (r"yapay zeka|ai ile", "AI-generated content must be disclosed")],
        "AZ": [(r"ən ucuz|ən yaxşı|1 nömrəli|lider", "superlative claim: needs proof (Advertising Law: no misleading ads)"), (r"zəmanət", "guarantee: give terms"), (r"endirim", "discount: be ready to prove the old price"), (r"möcüzə|dərhal|qəti", "absolute promise: risky")],
        "ALL": [(r"\byou\b.*\b(overweight|fat|debt|depressed|diabetic|single)\b|\bare you (overweight|in debt|depressed)", "Meta policy: do not assert or imply personal attributes"), (r"before.?after|önce.?sonra|əvvəl.?sonra", "before/after imagery is restricted for health, weight and cosmetic claims"), (r"guaranteed|100%|%100", "absolute claims attract review and distrust")]}

def fill(t, b):
    d = {"topic": b.get("category", "this"), "audience": b.get("audience", "people like you"), "pain": (b.get("objections") or ["struggle"])[0], "mistake": b.get("mistake", "guessing"), "solution": b.get("offer", "our way"),
         "old_way": b.get("old_way", "the usual way"), "outcome": (b.get("benefits") or ["get results"])[0], "offer": b.get("offer", "the offer"), "price": str(b.get("price", "")), "n": str(b.get("n", 50)),
         "bonus": b.get("bonus", "a bonus"), "deadline": b.get("deadline", "Friday")}
    return re.sub(r"\{(\w+)\}", lambda m: d.get(m.group(1), m.group(0)), t)

def matrix(path, out, n=12, lang="tr", stage="cold"):
    b = json.load(open(path, encoding="utf-8")); os.makedirs(out, exist_ok=True); personas = b.get("personas") or [b.get("audience", "core buyer")]
    levels = {"cold": ["unaware", "problem", "solution"], "warm": ["solution", "product"], "hot": ["product", "most"]}[stage]
    angs = [a for a in ANGLES if a[2] in levels] or ANGLES; chosen, seen = [], set(); i = 0
    while len(chosen) < n and i < n * 20:
        a, f, p = angs[i % len(angs)], FORMATS[(i * 3 + i // len(angs)) % len(FORMATS)], personas[i % len(personas)]
        if (a[0], f[0]) not in seen: chosen.append((p, a, f)); seen.add((a[0], f[0]))
        i += 1
    rows = []
    for i, (p, a, f) in enumerate(chosen, 1):
        lvl = a[2] if a[2] in levels else levels[0]; hooks = HOOKS.get(lang, HOOKS["en"])[lvl]; hook = fill(hooks[i % len(hooks)], b)
        fw = ["PAS", "AIDA", "BAB", "4U", "FAB", "PASTOR"][i % 6]; proof = (b.get("proof") or ["testimonial"])[i % max(1, len(b.get("proof") or [1]))]
        rows.append({"id": f"C{i:02d}", "persona": p, "angle": a[0], "angle_idea": a[1], "awareness": lvl, "format": f[0], "hook": hook, "framework": f"{fw}: {FRAMEWORKS[fw]}",
                     "cta": CTA.get(lang, CTA["en"])[i % 4], "proof_needed": proof, "creator": ["founder", "customer", "team member", "creator/UGC", "voiceover only"][i % 5], "setting": ["office", "street", "home", "site / location", "screen recording"][(i + i // 5) % 5]})
    with open(os.path.join(out, "concepts.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    md = [f"# Creative matrix: {b.get('offer', '')} ({stage}, {lang})", "Each concept differs in angle and format, and rotates creator and setting, so the delivery system sees distinct creative entities.", ""]
    md += [f"## {r['id']} {r['angle']} / {r['format']}\n- Persona: {r['persona']}; awareness: {r['awareness']}\n- Hook (first 1 to 2 s): **{r['hook']}**\n- Body: {r['framework']}; idea: {r['angle_idea']}\n- Proof: {r['proof_needed']}; creator: {r['creator']}; setting: {r['setting']}\n- CTA: {r['cta']}" for r in rows]
    md += ["", "Production rules: captions on every video, hook in the first 1 to 2 seconds, key text inside the 9:16 safe zone (keep top ~14% and bottom ~20% clear), real faces and places beat stock, sound on for Reels."]
    open(os.path.join(out, "concepts.md"), "w", encoding="utf-8").write("\n".join(md)); print("\n".join(md[:30])); print(f"... -> {out}/concepts.csv ({len(rows)} concepts)")

def lint(path, market="TR"):
    rules = RISK.get(market, []) + RISK["ALL"]; issues = 0
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        pl = (r.get("placement") or "feed").lower(); lim = LIMITS.get(pl, LIMITS["feed"]); msgs = []
        for field, mx in zip(("primary_text", "headline", "description"), lim):
            t = r.get(field) or ""
            if mx and len(t) > mx: msgs.append(f"{field} {len(t)} chars > {mx} visible on {pl} (rest is cut)")
        txt = " ".join(r.get(k) or "" for k in ("primary_text", "headline", "description")).lower().replace("\u0307", "")
        msgs += [m for pat, m in rules if re.search(pat, txt)]
        if not re.search(r"[?!.]|\b(yaz|tıkla|message|book|bizə|напиш)", txt): msgs.append("no clear call to action")
        print(f"- {r.get('id', '?')}: " + ("; ".join(msgs) if msgs else "ok")); issues += len(msgs)
    print(f"{issues} issue(s). Turkey since 1 Aug 2026: influencer/partner content must carry 'reklam'; AI-generated people or voices must be disclosed." if market == "TR" else f"{issues} issue(s).")

def diversity(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig"))); fields = [f for f in ("persona", "angle", "format", "creator", "hook", "setting") if f in rows[0]]; flagged = 0
    for a, b in itertools.combinations(rows, 2):
        same = sum((a[f] or "").strip().lower() == (b[f] or "").strip().lower() for f in fields); sim = same / len(fields)
        if sim >= 0.6: print(f"- {a.get('id')} and {b.get('id')}: {sim:.0%} alike ({', '.join(f for f in fields if a[f] == b[f])}): likely treated as one creative"); flagged += 1
    print(f"{len(rows)} concepts, {flagged} near-duplicate pair(s). Aim for 0: change angle, format and the person on screen, not just colours or text.")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 3 and a[1] == "matrix": matrix(a[2], a[3], int(opt("--n", 12)), opt("--lang", "tr"), opt("--stage", "cold"))
    elif len(a) > 2 and a[1] == "hooks": [print("- " + h) for h in HOOKS.get(opt("--lang", "en"), HOOKS["en"])[a[2]]]
    elif len(a) > 2 and a[1] == "lint": lint(a[2], opt("--market", "TR").upper())
    elif len(a) > 2 and a[1] == "diversity": diversity(a[2])
    else: print(USAGE)
