###############
# Qiyas Sadıqov CC
###############
import datetime as dt, sys

USAGE = """market-audience-intel: market and audience knowledge for advertising, strongest on Azerbaijan and Turkey.

  python3 marketintel.py markets                               -> markets in the database
  python3 marketintel.py profile AZ                            -> full market profile (people, platforms, money, language, law, calendar)
  python3 marketintel.py compare AZ TR GE                      -> side by side table
  python3 marketintel.py afford AZ PRICE [--currency AZN]      -> price vs income: months of salary, framing, funnel advice
  python3 marketintel.py persona AZ --category "real estate" [--age 25-44] [--city Baku] [--income mid|high|low] [--b2b]
                                                               -> persona sheet: platforms, language, angles, objections, trust signals, price framing
  python3 marketintel.py calendar AZ [--from 2026-11-21] [--months 6]  -> upcoming peaks and quiet days to plan around
Figures carry their date and source. Economic and platform numbers move: refresh them before big decisions.
Needs: Python 3 only.
"""

MK = {
 "AZ": {"name": "Azerbaijan", "currency": "AZN", "usd": 1.70, "population_m": 10.25, "pop_src": "Trading Economics, Dec 2025",
        "social_m": 8.44, "social_src": "DataReportal Digital 2027 (Oct 2026), 80.6% of population",
        "platforms": {"Facebook": "5.34M users (NapoleonCat, Sep 2026), 53% men", "Instagram": "4.54M users (NapoleonCat, Sep 2026), 25-34 is the biggest group (~35%)", "YouTube": "largest share of social traffic (40.5%, Oct 2026, StatCounter via Trend)", "TikTok": "large among under 30s; check reach and ads availability in TikTok Ads Manager", "Telegram": "news and channels; Telegram Ads is contextual, channel based", "WhatsApp": "default messenger; click to WhatsApp ads fit buying habits"},
        "age_note": "Meta audience is young: 18-34 is about 60% of Instagram users",
        "wage": 1174, "wage_src": "average nominal monthly wage Jan-Jun 2026, State Statistics Committee (gross); Baku higher, regions much lower (Nakhchivan 803)", "median_wage": 600, "min_wage": 400, "inflation": "5.7% (Feb 2026)",
        "money": ["Cash still strong but cards growing fast: 22.3M payment cards (Mar 2026); card-to-card transfers were 71% of e-commerce volume in 2024", "Installment culture: BirKart, Tamkart and Birbank 'taksit' cards, 0% installments at partner stores (3 to 24 months)", "E-commerce about 3% of retail; Birmarket (Bir ecosystem) largest marketplace; Trendyol via Birbank BNPL", "Prices are compared in manat and often in USD for real estate and cars"],
        "language": ["Azerbaijani (Latin) is the state language and the default for ads", "Russian widely used in Baku, especially among older, educated and some upper-income audiences: test RU versions for Baku premium segments", "Turkish content is understood well; Turkish slang can feel foreign in brand copy", "Write numbers the local way: 450 AZN or 450 ₼"],
        "culture": ["Trust is personal: faces, real office, phone number, WhatsApp, and recommendations matter more than logos", "Family decisions for big purchases (housing, education, cars): show the family benefit", "Baku vs regions: different income and price expectations; split geo or messages", "Price is often asked in DM ('qiymət?'): put price or 'from' price in the ad when you can to filter leads", "Avoid comparative attacks on named competitors"],
        "law": ["Law on Advertising (Reklam haqqında Qanun): ads should be in Azerbaijani; other languages can accompany it (check the current text for your case)", "No misleading claims; financial, medical, alcohol and tobacco rules apply; real estate ads must not mislead on area, price or status", "Personal data: Law on Personal Data; get consent for lead forms and customer list uploads", "Meta Special Ad Categories (housing, employment, finance) are mandatory only when targeting US, CA or listed EU countries, not AZ, but keep targeting fair"],
        "cpm_usd": "1.2 to 2.5 (Meta, broad, estimate)",
        "calendar": [("01-01", "New Year (gift season starts mid December)"), ("01-20", "20 January Day of National Mourning: no promotions"), ("03-08", "Women's Day: big gift and beauty peak"), ("03-20", "Novruz holidays (about 20-24 March): family, food, gifts, travel"), ("05-09", "Victory over Fascism Day"), ("05-28", "Independence Day"), ("06-15", "National Salvation Day"), ("09-01", "Knowledge Day: back to school and courses"), ("09-27", "Remembrance Day: respectful tone, no promos"), ("11-08", "Victory Day (Zəfər Günü)"), ("11-09", "State Flag Day"), ("12-31", "Solidarity Day and New Year eve")],
        "seasons": ["Courses and education: late August to October and January to February", "Real estate: spring (March to May) and autumn (September to November) are strongest; slow mid-summer", "Ramadan: evening (iftar to late night) engagement rises; daytime CPMs can drop"]},
 "TR": {"name": "Turkey", "currency": "TRY", "usd": 50.4, "population_m": 86.0, "pop_src": "TÜİK estimate",
        "social_m": 61.0, "social_src": "DataReportal Digital 2027 (Oct 2026), 69.3% of population; 25h04m social media per week (Digital 2026)",
        "platforms": {"Instagram": "66M audience (NapoleonCat, Jul 2026); most used app, about 1h53m per day; 25-34 largest group (21.7M)", "YouTube": "about 40% of internet traffic (2026); strong for long-form and search", "TikTok": "about 1h25m per day; strong under 35; Spark Ads and creators", "Facebook": "older audience; still large reach", "X": "news, sports, politics; brand safety care", "WhatsApp": "default messenger; click to WhatsApp works for services and e-commerce"},
        "age_note": "Instagram ad audience slightly male (52.7%)",
        "wage": 28075, "wage_src": "net minimum wage 2026 (about 40% of employees earn minimum wage, Sözcü); use net minimum wage as the mass-market anchor", "median_wage": None, "min_wage": 28075, "inflation": "29.77% annual (TÜİK, Oct 2026); prices change monthly",
        "money": ["Card payments over 80% of retail (2026); credit card installments (taksit) are central: show 'peşin fiyatına 6 taksit' when true", "Marketplaces dominate: Trendyol, Hepsiburada, Amazon TR, N11; price comparison is constant", "High inflation: refresh prices in creative often; avoid hard-coded prices in long-running ads or use 'from' wording", "Ad invoices: Meta adds a location fee for Turkish audiences from 1 July 2026 to cover the 5% digital service tax (2.5% from 2027); VAT 20% on imported services via reverse charge"],
        "language": ["Turkish only for the mass market; English loanwords fine for tech and youth", "Formal 'siz' for premium, finance, health; 'sen' for youth brands", "Regional and Kurdish speaking audiences exist; test, do not stereotype"],
        "culture": ["Deal seeking and comparison: show real savings, reviews, warranty, free shipping, return policy", "Trust: 'faturalı', 'garantili', official dealer, physical address, KEP/company info", "Football, family, food and humour work; avoid political and religious polarisation", "Speed in WhatsApp and DMs matters"],
        "law": ["Ticari Reklam ve Haksız Ticari Uygulamalar Yönetmeliği changes in force 1 Aug 2026: influencer posts must say 'reklam' clearly; AI-made content must be disclosed; profiling children for targeted ads is banned; strict rules for discount claims (previous price must be real)", "Reklam Kurulu fines for hidden advertising and unprovable claims (influencer cases reported at 500,000 to 4,000,000 TL)", "KVKK consent for lead forms and customer list uploads; ETK/İYS registration for commercial SMS and e-mail", "Comparative ads only with provable, fair claims; 'en ucuz', 'Türkiye'nin 1 numarası' need evidence"],
        "cpm_usd": "1.5 to 3.5 (Meta, broad, estimate; rises in Nov-Dec)",
        "calendar": [("01-01", "Yılbaşı"), ("02-14", "Sevgililer Günü"), ("03-08", "Dünya Kadınlar Günü"), ("04-23", "23 Nisan"), ("SUN2-05", "Anneler Günü (second Sunday of May)"), ("SUN3-06", "Babalar Günü (third Sunday of June)"), ("09-01", "Okula dönüş (late August to September)"), ("10-29", "Cumhuriyet Bayramı"), ("11-11", "11.11 indirimleri"), ("FRI_LAST-11", "Efsane Cuma / Black Friday (the Friday after the fourth Thursday of November) and Efsane Kasım")],
        "seasons": ["Q4 (Efsane Kasım to Yılbaşı) is the most expensive auction period", "Summer: tourism and travel peak; Istanbul audiences leave for holidays in July-August", "Exam seasons (YKS in June, KPSS) drive course demand in spring"]},
 "GE": {"name": "Georgia", "currency": "GEL", "usd": 2.7, "population_m": 3.7, "pop_src": "Geostat", "social_m": None, "social_src": "", "platforms": {"Facebook": "dominant platform in Georgia", "Instagram": "strong in Tbilisi", "TikTok": "youth"}, "age_note": "",
        "wage": 641, "wage_src": "average net, USD, CEOWORLD 2025 (gross about 807 USD Jun 2025, CEIC)", "median_wage": None, "min_wage": None, "inflation": "check Geostat", "money": ["Cards widely used in Tbilisi"], "language": ["Georgian first; Russian and English for some segments"], "culture": ["Facebook is more important than in most countries"], "law": ["check current advertising law"], "cpm_usd": "1 to 2.5 (estimate)", "calendar": [("01-07", "Orthodox Christmas"), ("05-26", "Independence Day")], "seasons": ["Tourism summer peak"]},
 "KZ": {"name": "Kazakhstan", "currency": "KZT", "usd": 500.0, "population_m": 20.3, "pop_src": "", "social_m": None, "social_src": "", "platforms": {"Instagram": "main commerce platform", "TikTok": "large youth reach", "Telegram": "news and channels", "WhatsApp": "default messenger"}, "age_note": "",
        "wage": 988, "wage_src": "average nominal monthly wage H1 2026, USD, Eurasian Economic Commission", "median_wage": None, "min_wage": None, "inflation": "check", "money": ["Kaspi ecosystem: Kaspi QR, Kaspi installments (Kaspi Red) dominate payments"], "language": ["Russian and Kazakh; bilingual creative performs safest"], "culture": ["Instagram shops and DM selling are normal"], "law": ["Kazakh language requirements for ads: check"], "cpm_usd": "1 to 2.5 (estimate)", "calendar": [("03-22", "Nauryz (21-23 March)")], "seasons": []},
 "UZ": {"name": "Uzbekistan", "currency": "UZS", "usd": 12500.0, "population_m": 37.5, "pop_src": "", "social_m": None, "social_src": "", "platforms": {"Telegram": "the main platform (channels, bots, shops)", "Instagram": "commerce", "YouTube": "video"}, "age_note": "very young population",
        "wage": 560, "wage_src": "average nominal monthly wage H1 2026, USD (Tashkent about 950)", "median_wage": None, "min_wage": None, "inflation": "check", "money": ["Uzum and Click/Payme; installments via Uzum Nasiya"], "language": ["Uzbek (Latin and Cyrillic) and Russian"], "culture": ["Telegram first: channel ads and bots convert"], "law": ["check"], "cpm_usd": "0.6 to 1.5 (estimate)", "calendar": [("03-21", "Navruz")], "seasons": []},
 "AE": {"name": "United Arab Emirates", "currency": "AED", "usd": 3.67, "population_m": 10.0, "pop_src": "", "social_m": None, "social_src": "", "platforms": {"Instagram": "high spend", "TikTok": "high", "Snapchat": "strong", "LinkedIn": "B2B"}, "age_note": "expat majority",
        "wage": None, "wage_src": "high income, very unequal by nationality and job", "median_wage": None, "min_wage": None, "inflation": "", "money": ["Cards, Tabby/Tamara BNPL"], "language": ["English and Arabic; Russian, Hindi, Urdu segments"], "culture": ["Premium, speed, status; Ramadan is the key season"], "law": ["UAE Media Council advertiser and influencer licences"], "cpm_usd": "4 to 9 (estimate)", "calendar": [("12-02", "National Day")], "seasons": ["Ramadan and Eid", "White Friday (November)"]},
 "SA": {"name": "Saudi Arabia", "currency": "SAR", "usd": 3.75, "population_m": 35.0, "pop_src": "", "social_m": None, "social_src": "", "platforms": {"Snapchat": "very strong", "TikTok": "very strong", "X": "strong", "Instagram": "strong"}, "age_note": "young",
        "wage": None, "wage_src": "", "median_wage": None, "min_wage": None, "inflation": "", "money": ["Mada cards, Tabby/Tamara BNPL"], "language": ["Arabic (Saudi dialect for social)"], "culture": ["Family, faith-respectful creative"], "law": ["GCAM regulations, Mawthooq influencer licence"], "cpm_usd": "3 to 7 (estimate)", "calendar": [("09-23", "Saudi National Day")], "seasons": ["Ramadan, White Friday"]},
 "DE": {"name": "Germany", "currency": "EUR", "usd": 0.92, "population_m": 84.0, "pop_src": "", "social_m": None, "social_src": "", "platforms": {"Instagram": "", "Facebook": "", "YouTube": "", "TikTok": ""}, "age_note": "", "wage": None, "wage_src": "", "median_wage": None, "min_wage": None, "inflation": "", "money": ["PayPal, Klarna, invoice"], "language": ["German"], "culture": ["Privacy sensitive, fact based"], "law": ["GDPR consent, Meta special ad categories apply in listed EU countries", "EU political ads regulation (TTPA)"], "cpm_usd": "6 to 10", "calendar": [], "seasons": ["Q4"]},
 "GB": {"name": "United Kingdom", "currency": "GBP", "usd": 0.78, "population_m": 69.0, "pop_src": "", "social_m": None, "social_src": "", "platforms": {}, "age_note": "", "wage": None, "wage_src": "", "median_wage": None, "min_wage": None, "inflation": "", "money": [], "language": ["English"], "culture": [], "law": ["ASA / CAP code, #ad for influencers"], "cpm_usd": "7 to 11", "calendar": [], "seasons": ["Q4"]},
 "US": {"name": "United States", "currency": "USD", "usd": 1.0, "population_m": 340.0, "pop_src": "", "social_m": None, "social_src": "", "platforms": {}, "age_note": "", "wage": None, "wage_src": "", "median_wage": None, "min_wage": None, "inflation": "", "money": [], "language": ["English, Spanish"], "culture": [], "law": ["Special ad categories (housing, employment, credit/financial) mandatory", "FTC endorsement guides"], "cpm_usd": "10 to 20", "calendar": [], "seasons": ["Q4"]},
}
ISLAMIC = [("2026-02-18", "Ramadan begins (approx.)"), ("2026-03-20", "Ramazan Bayramı / Eid al-Fitr (approx.)"), ("2026-05-27", "Qurban / Kurban Bayramı / Eid al-Adha (approx.)"),
           ("2027-02-08", "Ramadan begins (approx.)"), ("2027-03-10", "Ramazan Bayramı / Eid al-Fitr (approx.)"), ("2027-05-17", "Qurban / Kurban Bayramı / Eid al-Adha (approx.)")]
MUSLIM_MAJORITY = {"AZ", "TR", "KZ", "UZ", "AE", "SA"}
GLOBAL = [("FRI_LAST-11", "Black Friday"), ("11-11", "Singles Day 11.11")]

def resolve(code, year):
    if code.startswith("SUN") or code.startswith("FRI"):
        kind, mon = code.split("-"); mon = int(mon); wd = 6 if kind.startswith("SUN") else 4
        days = [dt.date(year, mon, d) for d in range(1, 32) if _valid(year, mon, d) and dt.date(year, mon, d).weekday() == wd]
        if kind == "FRI_LAST" and mon == 11:
            return [dt.date(year, 11, d) for d in range(1, 31) if dt.date(year, 11, d).weekday() == 3][3] + dt.timedelta(days=1)
        return days[-1] if kind.endswith("LAST") else days[int(kind[3]) - 1]
    m, d = map(int, code.split("-")); return dt.date(year, m, d)

def _valid(y, m, d):
    try: dt.date(y, m, d); return True
    except ValueError: return False

def profile(c):
    m = MK[c]; L = [f"# {m['name']} ({c})", f"Population {m['population_m']}M ({m['pop_src']})" + (f"; social media identities {m['social_m']}M ({m['social_src']})" if m["social_m"] else ""), ""]
    L += ["## Platforms"] + [f"- {k}: {v}" for k, v in m["platforms"].items()] + ([f"- {m['age_note']}"] if m["age_note"] else [])
    L += ["", "## Money"] + ([f"- Income anchor: {m['wage']} {m['currency'] if c in ('AZ', 'TR') else 'USD'} ({m['wage_src']})"] if m["wage"] else []) + ([f"- Median wage about {m['median_wage']} {m['currency']}"] if m["median_wage"] else []) + ([f"- Minimum wage {m['min_wage']} {m['currency']}"] if m["min_wage"] else []) + ([f"- Inflation {m['inflation']}"] if m["inflation"] else []) + [f"- {x}" for x in m["money"]]
    L += ["", "## Language"] + [f"- {x}" for x in m["language"]] + ["", "## Culture and trust"] + [f"- {x}" for x in m["culture"]] + ["", "## Law and platform rules"] + [f"- {x}" for x in m["law"]]
    L += ["", f"## Cost\n- Meta CPM {m['cpm_usd']} USD", "", "## Seasons"] + [f"- {x}" for x in m["seasons"]]
    print("\n".join(L))

def compare(codes):
    rows = [("population M", "population_m"), ("social M", "social_m"), ("income anchor", "wage"), ("currency", "currency"), ("CPM USD", "cpm_usd"), ("inflation", "inflation")]
    print("| | " + " | ".join(codes) + " |\n|---|" + "---|" * len(codes))
    for lab, k in rows: print(f"| {lab} | " + " | ".join(str(MK[c].get(k) or "") for c in codes) + " |")
    print("| top platforms | " + " | ".join(", ".join(list(MK[c]["platforms"])[:4]) for c in codes) + " |")

def afford(c, price, cur=None):
    m = MK[c]; cur = cur or m["currency"]; p_local = price * m["usd"] if (cur == "USD" and m["currency"] != "USD") else price
    w = m["wage"]; wcur = m["currency"] if c in ("AZ", "TR") else "USD"
    p_cmp = p_local / m["usd"] if wcur == "USD" else p_local
    months = p_cmp / w if w else None
    print(f"# Affordability in {m['name']}: {price} {cur}")
    if months is None: print("No income anchor in the database for this market; add one."); return
    print(f"- Equals {months:.2f} months of the income anchor ({w} {wcur}; {m['wage_src']})")
    if months < 0.05: adv = ["Impulse range: sell directly (Sales objective, catalog or landing page), low friction checkout", "Volume and creative variety matter more than education"]
    elif months < 0.5: adv = ["Considered but quick: show price, proof and guarantee; retarget 7 to 30 days", "Installments help if over about 0.2 months"]
    elif months < 3: adv = ["Considered purchase: lead or chat first, answer objections, show monthly payment (e.g. 12 installments)", "Use proof heavy retargeting and a 30 to 90 day window"]
    else: adv = ["High ticket: consultation, viewing or call is the conversion; optimise for qualified leads (CRM feedback)", "Target realistic income segments by message and geography (premium districts), not by guessing interests", "Show financing (mortgage, installments, down payment) and total value; family decision content"]
    for x in adv: print(f"- {x}")
    if months >= 0.2: print(f"- Monthly framing: 6 installments = {p_local / 6:,.0f} {m['currency']}, 12 = {p_local / 12:,.0f}, 24 = {p_local / 24:,.0f}")

ANGLES = {"real estate": (["location and daily life", "investment return and price per m²", "family space and schools", "payment plan / mortgage / installments", "trust: documents, title deed (kupça / tapu), developer track record"], ["is the price real", "hidden fees", "document problems", "construction delays"], ["video walkthrough", "agent face and phone", "real photos not renders", "map pin and distances"]),
          "course": (["career result and salary", "practical, project based", "mentor and community", "certificate and job help", "flexible schedule"], ["will I really get a job", "too hard / no time", "price", "online quality"], ["graduate stories with names", "free trial lesson", "curriculum detail", "teacher profile"]),
          "ecommerce": (["product in use", "price and savings", "speed of delivery", "reviews and UGC", "bundle or gift"], ["quality vs photo", "returns", "delivery time", "fake products"], ["reviews", "return policy", "cash on delivery or installments", "real customer videos"]),
          "beauty": (["visible result", "expert / clinic", "before after where allowed", "price packages", "comfort and safety"], ["pain", "safety", "price"], ["licensed staff", "real results within policy", "reviews"]),
          "b2b": (["time or money saved", "risk reduction", "case study numbers", "integration and support", "expert POV"], ["switching cost", "security", "ROI unclear"], ["logos", "case studies", "demo"]),
          "default": (["outcome", "proof", "price/value", "ease", "story"], ["price", "trust", "need"], ["reviews", "faces", "guarantee"])}

def persona(c, cat, age="25-44", city=None, income="mid", b2b=False):
    m = MK[c]; key = next((k for k in ANGLES if k in cat.lower().replace("-", "")), "b2b" if b2b else "default"); ang, obj, trust = ANGLES[key]
    plats = list(m["platforms"])
    print(f"# Persona: {cat} buyer in {m['name']}" + (f", {city}" if city else "") + f", age {age}, income {income}")
    print(f"- Where: {', '.join(plats[:4])}" + ("; LinkedIn for decision makers" if b2b else ""))
    print(f"- Language: {m['language'][0]}" + (f"; {m['language'][1]}" if len(m['language']) > 1 and (income == 'high' or c == 'AZ') else ""))
    print("- Angles to test: " + "; ".join(ang)); print("- Objections to answer in ads and chat: " + "; ".join(obj)); print("- Trust signals: " + "; ".join(trust))
    print("- Culture: " + "; ".join(m["culture"][:3]))
    if income == "high": print("- Premium: fewer words, real places, calm confidence; avoid discount language")
    if income == "low": print("- Mass market: price clarity, installments, savings, strong guarantees")
    print("- Targeting reality 2026: broad delivery with creative written for this persona beats narrow interest stacks; use geography and language as hard filters only when they truly define the market")

def calendar(c, start=None, months=6):
    s = dt.date.fromisoformat(start) if start else dt.date.today(); e = s + dt.timedelta(days=int(months * 30.5)); ev = []
    for y in (s.year, s.year + 1):
        own = {k for k, _ in MK[c]["calendar"]}; glob = [g for g in (GLOBAL if c != "AZ" else [("FRI_LAST-11", "Black Friday (growing in Baku retail)")]) if g[0] not in own]
        for code, name in MK[c]["calendar"] + glob:
            try: d = resolve(code, y)
            except Exception: continue
            if s <= d <= e: ev.append((d, name))
    if c in MUSLIM_MAJORITY: ev += [(dt.date.fromisoformat(d), n) for d, n in ISLAMIC if s <= dt.date.fromisoformat(d) <= e]
    print(f"# {MK[c]['name']}: {s} to {e}")
    for d, n in sorted(set(ev)): print(f"- {d} ({(d - s).days} days): {n}" + ("" if "no promo" in n else f"; build warm audiences from {d - dt.timedelta(days=35)}"))
    for x in MK[c]["seasons"]: print(f"- season: {x}")
    print("Islamic dates are approximate (moon sighting can shift them by a day).")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 1 and a[1] == "markets": [print(f"{k}  {v['name']}") for k, v in MK.items()]
    elif len(a) > 2 and a[1] == "profile": profile(a[2].upper())
    elif len(a) > 2 and a[1] == "compare": compare([x.upper() for x in a[2:]])
    elif len(a) > 3 and a[1] == "afford": afford(a[2].upper(), float(a[3]), opt("--currency"))
    elif len(a) > 2 and a[1] == "persona": persona(a[2].upper(), opt("--category", "default"), opt("--age", "25-44"), opt("--city"), opt("--income", "mid"), "--b2b" in a)
    elif len(a) > 2 and a[1] == "calendar": calendar(a[2].upper(), opt("--from"), float(opt("--months", 6)))
    else: print(USAGE)
