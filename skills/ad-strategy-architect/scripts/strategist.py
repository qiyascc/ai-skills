###############
# Qiyas Sadıqov CC
###############
import json, os, sys

USAGE = """ad-strategy-architect: a library of advertising methodologies that picks the right one for a business and turns
it into a full campaign architecture (stages, audiences, exclusions, objectives, messages, KPIs, budget split,
learning-phase check).

  python3 strategist.py list                                  -> all methodologies, one line each
  python3 strategist.py show METHOD                           -> the method in full (idea, stages, rules, pitfalls)
  python3 strategist.py recommend BRIEF.json [--top 3]        -> fit score of every method for this business, with reasons
  python3 strategist.py blueprint METHOD BRIEF.json OUT_DIR   -> blueprint.md + blueprint.json (input for meta-ads-builder)
  python3 strategist.py brief OUT.json                        -> writes an example brief to fill in

BRIEF fields: business, category, offer, price, currency, market (AZ, TR, GE, KZ, UZ, AE, SA, DE, GB, US), goal (sales | leads |
messages | awareness | app | traffic), sales_cycle (instant | short | long), margin (0-1), monthly_budget (in currency),
b2b, local, has_pixel, has_crm, has_catalog, website, messaging (whatsapp | instagram | none), followers,
brand_stage (new | growing | known), content_engine (low | mid | high), repeat_purchase, notes.
Cost figures are planning estimates; replace them with the account's own numbers as soon as they exist.
Needs: Python 3 only.
"""

CPM_USD = {"AZ": 1.6, "TR": 2.0, "GE": 1.6, "KZ": 1.8, "UZ": 1.1, "AE": 6.0, "SA": 4.5, "DE": 8.0, "GB": 9.0, "US": 14.0}
FX_PER_USD = {"USD": 1.0, "AZN": 1.70, "EUR": 0.905, "TRY": 50.4, "GEL": 2.7, "KZT": 500.0, "UZS": 12500.0, "AED": 3.67, "SAR": 3.75, "GBP": 0.78}

def S(stage, audience, include, exclude, objective, goal, message, kpi, share):
    return {"stage": stage, "audience": audience, "include": include, "exclude": exclude, "objective": objective, "performance_goal": goal, "message": message, "kpi": kpi, "share": share}

M = {
 "awareness-ladder-loop": {"name": "Awareness ladder loop (4 campaigns)", "origin": "practitioner method (course and service businesses)",
  "idea": "Four campaigns, one per relationship level: category-interested strangers, people who know the brand but do not follow, followers/warm, contacted or customers. Exclusions keep every person in exactly one stage; retention windows move them up automatically, so the system runs as an endless loop.",
  "fit": lambda b: 3 * (b["goal"] in ("sales", "leads", "messages")) + 2 * (b["sales_cycle"] in ("short", "long")) + 2 * (b["content_engine"] != "low") + (b["followers"] >= 1000) + (b["monthly_budget_usd"] >= 600) - 2 * (b["monthly_budget_usd"] < 300) + (b["category_course"]),
  "stages": [S("C1 Cold: interested, do not know us", "broad or Advantage+ audience in market; category interests only as suggestions", [], ["IG and FB engagers 365d", "video viewers 365d", "website visitors 180d", "lead form submitters 90d", "customer list"], "Awareness or Engagement", "ThruPlay / video views, or Instagram profile visits", "who we are, the problem we solve, proof in one line; no hard sell", "hook rate 25%+, cost per 50% view, warm pool growth", 0.40),
             S("C2 Know us, do not follow", "people who engaged or watched but are not followers", ["video viewers 50%+ 365d", "IG/FB engagers 365d"], ["IG/FB engagers 30d", "leads 90d", "customer list"], "Engagement", "Instagram profile visits / follows (where available)", "why follow: free value, results, behind the scenes, social proof", "cost per profile visit, follower growth", 0.20),
             S("C3 Followers and warm", "recent engagers, website visitors, followers", ["IG/FB engagers 30d", "website visitors 30d", "messaged the account 90d"], ["leads 30d", "customer list"], "Leads, Sales or Engagement (messages)", "Leads / conversations / purchases", "the offer: curriculum or service detail, price, guarantee, testimonials, deadline", "CPL or cost per conversation, lead to sale rate", 0.30),
             S("C4 Contacted and customers", "people we already talked to or sold to", ["customer list (CRM)", "lead form submitters 90d", "purchasers 180d"], ["purchasers of this product 30d (unless upsell)"], "Sales or Engagement (messages)", "Purchases / conversations", "reminders, objections answered, upsell, referral, next cohort", "close rate, repeat purchase, referral count", 0.10)],
  "rules": ["With a small budget merge C1+C2 and C3+C4 into two campaigns (learning needs volume).", "Never let stages overlap: every include list is excluded from the stage below it.", "Retargeting pools under ~1,000 people do not deliver well: widen the window (30 to 90 to 180 days) before splitting.", "Advantage+ sales campaigns cannot hold strict exclusions: use standard setup for C1 to C3 when stage separation matters.", "Refresh C1 creative every 2 to 4 weeks; C3 and C4 can reuse proof assets longer."],
  "pitfalls": ["Too many ad sets per stage starves learning.", "Using 7-day windows in a small market empties the warm pools.", "Selling hard in C1."]},
 "tofu-mofu-bofu": {"name": "Classic funnel with retargeting (TOFU / MOFU / BOFU)", "origin": "direct response standard",
  "idea": "Prospecting at the top, consideration content in the middle, conversion offers at the bottom, each fed by the audience the stage above creates.",
  "fit": lambda b: 3 * (b["goal"] in ("sales", "leads")) + 2 * b["has_pixel"] + 1 * b["website"] + (b["monthly_budget_usd"] >= 1000) - 1 * (b["monthly_budget_usd"] < 400),
  "stages": [S("TOFU prospecting", "broad / Advantage+", [], ["website visitors 180d", "customers"], "Sales or Leads (optimise for the real conversion when volume allows)", "Purchases / leads", "problem, desire, product reveal", "CPA, CPM, CTR", 0.65),
             S("MOFU consideration", "engagers and video viewers who did not visit", ["video viewers 50% 90d", "engagers 90d"], ["website visitors 30d", "customers"], "Traffic or Sales", "Landing page views / purchases", "proof, comparisons, how it works", "LPV cost, add to cart rate", 0.15),
             S("BOFU conversion", "site visitors and cart abandoners", ["website visitors 30d", "add to cart 14d"], ["purchasers 30d"], "Sales", "Purchases", "offer, urgency that is real, guarantee", "ROAS, frequency under 5/week", 0.20)],
  "rules": ["Bottom stage usually takes 10 to 25% of spend; more only with big traffic.", "Frequency caps do not exist for conversion campaigns: watch frequency manually."], "pitfalls": ["Over-crediting BOFU (it harvests what TOFU created)."]},
 "see-think-do-care": {"name": "See, Think, Do, Care", "origin": "Avinash Kaushik (Google)",
  "idea": "Plan content and media by intent cluster, not by funnel stage: See = everyone in the category, Think = some commercial intent, Do = ready now, Care = existing customers (2+ purchases).",
  "fit": lambda b: 2 + 2 * (b["content_engine"] == "high") + (b["repeat_purchase"]) + (b["brand_stage"] != "new"),
  "stages": [S("See", "largest addressable audience", [], ["customers"], "Awareness", "Reach / ThruPlay", "entertaining or useful category content", "reach, recall, search lift", 0.35),
             S("Think", "category intent signals", ["engagers 180d", "search and Reddit intent"], ["customers"], "Traffic or Engagement", "LPV / engaged sessions", "guides, comparisons, demos", "engaged visits, micro conversions", 0.25),
             S("Do", "ready to buy", ["visitors 30d", "brand search"], ["customers 30d"], "Sales or Leads", "Purchases / leads", "offer, price, trust", "CPA, ROAS", 0.30),
             S("Care", "customers", ["customer list"], [], "Sales or Engagement", "repeat purchase / referrals", "loyalty, community, upsell", "LTV, repeat rate", 0.10)],
  "rules": ["Measure each cluster with its own KPI; never judge See by CPA."], "pitfalls": ["Skipping Care for repeat-purchase businesses."]},
 "schwartz-awareness": {"name": "Five levels of awareness messaging ladder", "origin": "Eugene Schwartz, Breakthrough Advertising (1966)",
  "idea": "Same audience, different message by awareness level: unaware, problem aware, solution aware, product aware, most aware. The structure is creative-first: each ad concept is written for one level and Meta finds who it fits.",
  "fit": lambda b: 3 + 2 * (b["brand_stage"] == "new") + 1 * (b["content_engine"] != "low"),
  "stages": [S("Unaware", "broad", [], ["customers"], "Awareness or Sales (broad)", "ThruPlay / purchases", "story or identity hook, no product first", "hook rate", 0.25),
             S("Problem aware", "broad", [], ["customers"], "Sales or Leads", "conversions", "name the pain precisely, agitate, hint the solution", "CTR", 0.25),
             S("Solution aware", "broad + engagers", [], ["customers"], "Sales or Leads", "conversions", "why this approach beats alternatives", "CVR", 0.20),
             S("Product aware", "engagers, visitors", ["engagers 90d", "visitors 90d"], ["customers"], "Sales or Leads", "conversions", "proof, reviews, demo, risk reversal", "CPA", 0.20),
             S("Most aware", "warm", ["visitors 30d", "leads 30d"], ["customers 30d"], "Sales", "purchases", "the deal: price, bonus, deadline", "ROAS", 0.10)],
  "rules": ["Write at least one concept per level; under Andromeda the concepts are the targeting."], "pitfalls": ["Writing every ad for the most aware."]},
 "andromeda-consolidated": {"name": "Consolidated broad + creative diversification", "origin": "Meta Andromeda era (2025-2026) best practice",
  "idea": "One campaign per objective, campaign budget, broad or Advantage+ audience, 10 to 30 genuinely different creative concepts (persona x angle x format x creator). Creative does the targeting.",
  "fit": lambda b: 2 + 2 * b["has_pixel"] + 2 * (b["content_engine"] == "high") + (b["goal"] in ("sales", "leads")) + (b["monthly_budget_usd"] >= 1500) - 2 * (b["content_engine"] == "low"),
  "stages": [S("Main", "broad / Advantage+ audience", [], ["customers (if a new-customer goal)"], "Sales or Leads (Advantage+)", "Purchases / leads / conversion leads", "diverse concepts: pain, desire, proof, comparison, founder, UGC, demo, offer", "blended CPA, ROAS, creative hit rate", 0.85),
             S("Retargeting (optional)", "visitors, engagers", ["visitors 30d", "engagers 30d"], ["customers 30d"], "Sales", "Purchases", "proof and offer", "incremental CPA", 0.15)],
  "rules": ["Near-duplicate ads count as one creative entity: vary hooks, people, setting, format, message.", "Give it 2+ weeks and 50 events per week before judging.", "Placement and detailed-targeting exclusions are mostly gone; use account-level controls and value rules."], "pitfalls": ["Many small ad sets with interest stacks that reach the same people anyway."]},
 "advantage-scale-lab": {"name": "Advantage+ scaling engine + manual testing lab", "origin": "2026 practitioner split",
  "idea": "60 to 70% of budget in an Advantage+ sales/leads campaign with proven creatives, 30 to 40% in a manual lab that tests new concepts; winners graduate into the engine.",
  "fit": lambda b: 1 + 3 * (b["monthly_budget_usd"] >= 3000) + 2 * b["has_pixel"] + (b["goal"] == "sales") + (b["content_engine"] == "high"),
  "stages": [S("Engine", "Advantage+", [], [], "Sales or Leads (Advantage+)", "Purchases / leads", "proven winners only", "ROAS, CPA", 0.65), S("Lab", "broad, manual", [], ["customers"], "Sales or Leads", "conversions", "3 to 5 new concepts per week", "hit rate, CPA vs target", 0.35)],
  "rules": ["A concept graduates after beating target CPA with meaningful spend (2 to 3x CPA)."], "pitfalls": ["Starving the lab when the engine is doing well."]},
 "creative-testing-322": {"name": "3:2:2 creative testing", "origin": "DTC media buying practice",
  "idea": "3 visuals x 2 primary texts x 2 headlines in one flexible ad / ad set; read which combination Meta favours, then iterate one variable at a time.",
  "fit": lambda b: 2 + (b["content_engine"] != "low") + (b["monthly_budget_usd"] >= 800),
  "stages": [S("Test", "broad", [], ["customers"], "Sales or Leads", "conversions", "one concept, 3 executions", "CPA, CTR, hook rate", 0.30), S("Scale", "broad", [], ["customers"], "Sales or Leads", "conversions", "graduated winners", "CPA", 0.70)],
  "rules": ["Change one thing per round: concept, then hook, then details."], "pitfalls": ["Calling winners on a few clicks."]},
 "binet-field-60-40": {"name": "Brand building vs activation split (60/40)", "origin": "Binet and Field, IPA (2013; 62:38 in Effectiveness in Context; B2B about 46:54)",
  "idea": "Long-term brand building (broad reach, emotion, memorable assets) and short-term activation (targeted, rational, offer) both matter; the average optimum is about 60:40, B2B nearer 46:54, new or tiny brands lean activation.",
  "fit": lambda b: 1 + 2 * (b["brand_stage"] != "new") + (b["monthly_budget_usd"] >= 2000) + (b["repeat_purchase"]),
  "stages": [S("Brand", "broad reach", [], [], "Awareness", "Reach / ThruPlay", "emotional story, distinctive assets, category entry points", "reach, recall, branded search, share of search", 0.60), S("Activation", "in-market", [], [], "Sales or Leads", "conversions", "offer, reasons to buy now", "CPA, ROAS", 0.40)],
  "rules": ["Adjust the split by category, life stage and B2B (about 46:54)."], "pitfalls": ["Judging brand spend by last-click CPA."]},
 "ehrenberg-bass-reach": {"name": "Mental and physical availability (How Brands Grow)", "origin": "Byron Sharp and the Ehrenberg-Bass Institute",
  "idea": "Grow penetration by reaching all category buyers, linking the brand to many category entry points with consistent distinctive assets; only about 5% of buyers are in market at any time (95-5 rule).",
  "fit": lambda b: 1 + 2 * (b["brand_stage"] != "new") + (b["repeat_purchase"]) + (b["monthly_budget_usd"] >= 3000) + b["b2b"],
  "stages": [S("Continuous reach", "all category buyers", [], [], "Awareness", "Reach (frequency 1 to 2 per week)", "category entry points (when, where, with whom, why), same distinctive assets every time", "reach %, brand recall, share of search", 0.70), S("Capture", "in-market", [], [], "Sales or Leads", "conversions", "easy to buy", "CPA", 0.30)],
  "rules": ["Be always on rather than bursty when possible.", "Never change the distinctive assets (colours, logo, sound, character) every campaign."], "pitfalls": ["Narrow loyalty targeting instead of reach."]},
 "click-to-message": {"name": "Conversational funnel (click to WhatsApp / Instagram DM)", "origin": "Meta messaging ads; dominant in markets that buy through chat (AZ, TR, Gulf, LatAm)",
  "idea": "The ad opens a chat instead of a landing page; a fast human or bot qualifies, answers, sends prices, catalogs and books. Optimise for leads in chat, not just conversations, once you send quality signals back.",
  "fit": lambda b: 3 * (b["messaging"] != "none") + 2 * (b["market"] in ("AZ", "TR", "AE", "SA", "UZ", "KZ", "GE")) + 2 * (b["goal"] in ("messages", "leads", "sales")) + (not b["website"]) + (b["price_high"]),
  "stages": [S("Prospecting to chat", "broad / Advantage+", [], ["messaged us 30d", "customers"], "Engagement or Leads (conversion location: messaging apps)", "Conversations, or leads in chat (needs signals)", "one clear question to start the chat; price or availability teaser", "cost per conversation, reply rate, qualified rate", 0.75),
             S("Re-engage", "people who messaged but did not buy", ["messaged us 90d"], ["customers 30d"], "Engagement (messages) or Sales", "Conversations / purchases", "new listing, reminder, offer", "cost per qualified chat", 0.25)],
  "rules": ["Reply in under 5 minutes during working hours; speed decides conversion.", "Pre-fill the first message and use quick replies.", "Send chat outcomes (qualified, booked, sold) back to Meta so it optimises for quality.", "The 72-hour free window after an ad click covers follow-ups."], "pitfalls": ["Cheap chats that never answer the first question."]},
 "instant-form-crm": {"name": "Instant form lead gen with CRM feedback (conversion leads)", "origin": "Meta Lead Ads + Conversions API for CRM",
  "idea": "Native forms for volume; higher intent form type and qualifying questions for quality; CRM stages (contacted, qualified, sold) sent back via Conversions API so Meta optimises for quality leads.",
  "fit": lambda b: 2 * (b["goal"] == "leads") + 2 * b["has_crm"] + (b["sales_cycle"] == "long") + (b["price_high"]) + (not b["website"]),
  "stages": [S("Lead capture", "broad / Advantage+", [], ["leads 90d", "customers"], "Leads (instant form)", "Leads, then Conversion leads once CRM events flow", "clear value exchange, 2 to 3 qualifying questions", "CPL, cost per qualified lead, contact rate", 0.80), S("Nurture", "form openers and leads", ["lead form openers 90d", "leads 90d"], ["customers"], "Engagement or Leads", "conversations / leads", "proof, FAQ, booking", "booked rate", 0.20)],
  "rules": ["Call within 5 minutes; lead value decays fast.", "Use the higher intent review step when junk leads appear."], "pitfalls": ["Optimising for raw lead volume forever."]},
 "lead-magnet": {"name": "Lead magnet funnel", "origin": "content marketing classic",
  "idea": "Give a specific free asset (checklist, guide, mini course, price list, report) for contact details, nurture by email/WhatsApp, then offer.",
  "fit": lambda b: 2 * (b["goal"] == "leads") + (b["sales_cycle"] == "long") + b["b2b"] + (b["content_engine"] != "low") + b["category_course"],
  "stages": [S("Magnet", "broad", [], ["leads 180d", "customers"], "Leads", "Leads", "the asset solves one narrow problem now", "CPL", 0.70), S("Offer to leads", "leads", ["leads 30d"], ["customers"], "Sales or Leads", "purchases / calls", "the paid next step", "lead to sale rate", 0.30)],
  "rules": ["The magnet must be a slice of the paid product, not a random freebie."], "pitfalls": ["Leads with no follow-up sequence."]},
 "webinar-event": {"name": "Webinar / live event funnel", "origin": "course and B2B launches",
  "idea": "Register for a live or recorded session, remind, deliver value, pitch at the end, follow up with replay and deadline.",
  "fit": lambda b: 3 * b["category_course"] + 2 * (b["price_high"]) + b["b2b"] + (b["sales_cycle"] != "instant"),
  "stages": [S("Registration", "broad + engagers", [], ["registrants", "customers"], "Leads", "Registrations", "the one big promise of the session", "cost per registrant, show rate", 0.70), S("Reminder and replay", "registrants", ["registrants 14d"], ["buyers"], "Engagement or Sales", "show up / purchases", "reminder, replay, deadline", "show rate, close rate", 0.30)],
  "rules": ["Plan for a 25 to 40% show rate; the replay sells too."], "pitfalls": ["No deadline after the event."]},
 "value-ladder": {"name": "Value ladder / tripwire", "origin": "Russell Brunson style funnels",
  "idea": "A low-price entry offer that converts strangers into buyers, then step them up to core and premium offers.",
  "fit": lambda b: 2 * (b["goal"] == "sales") + (b["repeat_purchase"]) + b["category_course"] + (b["website"]),
  "stages": [S("Entry offer", "broad", [], ["buyers"], "Sales", "Purchases", "irresistible small first step", "CPA vs entry price", 0.75), S("Upsell", "entry buyers", ["entry buyers 60d"], ["core buyers"], "Sales", "Purchases", "the core offer", "take rate", 0.25)],
  "rules": ["The entry offer can break even; profit comes from the ladder."], "pitfalls": ["No ladder behind the tripwire."]},
 "offer-engineering": {"name": "Offer engineering (value equation)", "origin": "Alex Hormozi, $100M Offers",
  "idea": "Before media, raise perceived value: dream outcome x likelihood of achievement, divided by time delay x effort. Add guarantees, bonuses, scarcity that is real, and naming.",
  "fit": lambda b: 3 + (b["brand_stage"] == "new") + (b["price_high"]),
  "stages": [S("Offer test", "broad", [], ["customers"], "Sales or Leads", "conversions", "2 to 3 offer versions with the same creative", "CVR, CPA by offer", 1.0)],
  "rules": ["Test offers before creatives when conversion rate is the bottleneck."], "pitfalls": ["Fake urgency (also illegal under consumer law in TR and EU)."]},
 "organic-amplification": {"name": "Organic first, paid amplification (dollar a day, Spark / partnership ads)", "origin": "Dennis Yu, TikTok Spark Ads, Meta partnership ads",
  "idea": "Post a lot organically, boost the posts that already over-perform with small budgets, then promote the best to conversion campaigns. Creator content runs as partnership or Spark ads.",
  "fit": lambda b: 2 * (b["content_engine"] == "high") + (b["followers"] >= 5000) + (b["monthly_budget_usd"] < 1500) + (b["brand_stage"] == "new"),
  "stages": [S("Amplify winners", "broad + engagers", [], [], "Engagement or Awareness", "ThruPlay / engagement", "your best organic posts as they are", "cost per engaged view", 0.40), S("Convert", "engagers", ["engagers 90d"], ["customers"], "Sales, Leads or Messages", "conversions", "offer using proven posts", "CPA", 0.60)],
  "rules": ["Only amplify posts that beat your organic median."], "pitfalls": ["Boosting everything with the Boost button and no exclusions."]},
 "jab-jab-hook": {"name": "Jab, jab, jab, right hook content rhythm", "origin": "Gary Vaynerchuk",
  "idea": "Give value several times (education, entertainment, help) before asking; in ads, run value pieces to cold audiences and the ask to those who consumed them.",
  "fit": lambda b: 1 + (b["content_engine"] != "low") + (b["brand_stage"] == "new") + b["local"],
  "stages": [S("Jabs", "broad", [], ["customers"], "Engagement or Awareness", "ThruPlay", "useful, native, no ask", "hook rate, saves, shares", 0.6), S("Right hook", "jab consumers", ["video viewers 50% 60d"], ["customers"], "Sales, Leads or Messages", "conversions", "the ask", "CPA", 0.4)],
  "rules": [], "pitfalls": ["Jabs that are disguised ads."]},
 "ugc-creators": {"name": "Creator / UGC led performance", "origin": "TikTok and Meta partnership ads",
  "idea": "A roster of creators makes many authentic videos; best ones run as partnership/Spark ads from the creator handle; creative diversity comes from the people.",
  "fit": lambda b: 2 * (b["goal"] in ("sales", "app")) + (b["monthly_budget_usd"] >= 1500) + (b["content_engine"] != "high"),
  "stages": [S("Creator tests", "broad", [], ["customers"], "Sales or App", "conversions", "one brief, many faces and settings", "hook rate, CPA per creator", 0.4), S("Scale", "broad", [], ["customers"], "Sales or App", "conversions", "winning creators and angles", "CPA", 0.6)],
  "rules": ["Label paid partnerships (TR: 'reklam' label mandatory since 1 Aug 2026)."], "pitfalls": ["Scripted UGC that looks like TV."]},
 "catalog-dynamic": {"name": "Catalog / dynamic ads (products, listings, courses)", "origin": "Meta Advantage+ catalog ads; real estate home listing catalogs",
  "idea": "Upload a catalog; Meta shows each person the items they are most likely to want, prospecting and retargeting viewed items.",
  "fit": lambda b: 3 * b["has_catalog"] + b["has_pixel"] + (b["goal"] == "sales") + b["category_listings"],
  "stages": [S("Catalog prospecting", "broad", [], ["purchasers 30d"], "Sales (catalog)", "Purchases / leads", "best sellers or newest listings", "ROAS", 0.6), S("Catalog retargeting", "viewers", ["viewed items 14d"], ["purchasers 30d"], "Sales (catalog)", "Purchases", "the exact items viewed", "ROAS", 0.4)],
  "rules": ["Housing catalogs fall under the Housing special ad category where it applies (US, CA, some EU)."], "pitfalls": ["Bad feed images and stale prices."]},
 "seasonal-burst": {"name": "Seasonal burst with pre-built audiences", "origin": "retail calendar practice",
  "idea": "Build warm pools 4 to 6 weeks before a peak (Ramadan, Novruz, Black Friday / Efsane Cuma, 11.11, back to school, New Year), then burst offers to them with fresh creative.",
  "fit": lambda b: 2 * (b["season"] is not None) + (b["goal"] == "sales") + (b["repeat_purchase"]),
  "stages": [S("Warm up", "broad", [], ["customers"], "Engagement or Awareness", "ThruPlay / engagement", "teasers, early access list", "pool size", 0.3), S("Peak", "warm + broad", ["engagers 60d", "visitors 60d", "early list"], [], "Sales", "Purchases", "the real offer", "ROAS", 0.6), S("After", "buyers", ["buyers 30d"], [], "Sales", "Purchases", "cross-sell, review request", "repeat rate", 0.1)],
  "rules": ["CPMs rise near peaks; buy reach early."], "pitfalls": ["Launching new campaigns on peak day (no learning time)."]},
 "local-radius": {"name": "Local radius / store and call ads", "origin": "local business practice",
  "idea": "Tight geography, map and call CTAs, messages, reviews and offers people can walk to.",
  "fit": lambda b: 4 * b["local"] + (b["messaging"] != "none"),
  "stages": [S("Local awareness", "radius around location", [], [], "Awareness", "Reach", "what, where, why now", "reach in radius", 0.4), S("Local action", "radius + engagers", [], ["customers 30d"], "Engagement / Leads / Traffic", "calls, messages, directions", "offer and easy contact", "cost per call or chat", 0.6)],
  "rules": ["Radius too small kills delivery: start 5 to 15 km in cities."], "pitfalls": ["Interest targeting on a tiny geo."]},
 "app-install": {"name": "App install and in-app events", "origin": "app growth practice",
  "idea": "Advantage+ app campaigns optimising for installs first, then in-app events or value once SDK/MMP signals are reliable.",
  "fit": lambda b: 6 * (b["goal"] == "app"),
  "stages": [S("Installs to events", "broad", [], [], "App promotion", "Installs then app events / value", "app in use, outcome, offer", "CPI, cost per key event, D7 retention", 1.0)], "rules": ["Fix SKAN/AEM and MMP before scaling."], "pitfalls": ["Optimising installs that never open."]},
 "abm-b2b": {"name": "B2B account based and demand gen", "origin": "LinkedIn B2B Institute, ABM practice",
  "idea": "Target named accounts and job roles (LinkedIn), retarget on Meta with customer lists, educate the 95% out of market, capture the 5% with demos.",
  "fit": lambda b: 5 * b["b2b"] + (b["sales_cycle"] == "long"),
  "stages": [S("Demand creation", "ICP roles and accounts", [], ["customers"], "Awareness / Engagement", "views, engagement", "insight, POV, proof", "account reach, engagement", 0.5), S("Capture", "engaged accounts + search intent", ["engagers 90d", "site visitors 90d"], ["customers"], "Leads", "demo requests", "demo, audit, case study", "cost per SQL", 0.5)],
  "rules": ["B2B optimum split is about 46% brand, 54% activation."], "pitfalls": ["Judging by MQL volume."]},
 "intent-capture": {"name": "Intent capture (search, Reddit, YouTube)", "origin": "search marketing",
  "idea": "Be present where people already search or ask: Google Search / AI Max, YouTube, Reddit keyword and community targeting.",
  "fit": lambda b: 2 * (b["sales_cycle"] != "instant") + b["website"] + b["b2b"] + (b["price_high"]),
  "stages": [S("Search and community", "keywords, subreddits, topics", [], [], "Search / Conversions", "conversions", "answer the query exactly", "CPA, impression share", 1.0)], "rules": ["Pair with social to create the demand that search captures."], "pitfalls": ["Only bidding on your own brand."]},
 "retention-care": {"name": "Retention, upsell and referral", "origin": "lifecycle marketing",
  "idea": "Customer lists and purchase events power upsell, win-back and referral ads; cheap revenue from people who already trust you.",
  "fit": lambda b: 3 * (b["repeat_purchase"]) + b["has_crm"] + (b["brand_stage"] != "new"),
  "stages": [S("Care", "customers", ["customer list", "purchasers 180d"], ["purchasers 14d"], "Sales or Engagement", "purchases / referrals", "what is next for them, referral reward", "repeat rate, LTV", 1.0)], "rules": [], "pitfalls": ["Showing acquisition discounts to loyal customers."]},
 "sequencing-story": {"name": "Sequential storytelling", "origin": "Meta sequencing (auction Awareness/Engagement, rolling out Feb 2026)",
  "idea": "Show a set order of ads (setup, conflict, resolution, offer) to the same people.",
  "fit": lambda b: 1 + (b["content_engine"] == "high") + (b["brand_stage"] != "new"),
  "stages": [S("Sequence", "broad", [], ["customers"], "Awareness or Engagement", "Reach / ThruPlay", "episode 1 to 4", "completion by step", 1.0)], "rules": ["Use retargeting by video view as a fallback where sequencing is not available."], "pitfalls": []},
}

def norm(b):
    d = {"currency": "USD", "market": "AZ", "goal": "sales", "sales_cycle": "short", "margin": 0.5, "monthly_budget": 1000, "b2b": False, "local": False, "has_pixel": False,
         "has_crm": False, "has_catalog": False, "website": True, "messaging": "none", "followers": 0, "brand_stage": "new", "content_engine": "mid", "repeat_purchase": False, "season": None, "price": 0, "category": ""}
    d.update(b); fx = FX_PER_USD.get(d["currency"], 1.0)
    d["monthly_budget_usd"] = d["monthly_budget"] / fx; d["price_usd"] = d["price"] / fx
    d["price_high"] = d["price_usd"] >= 300; c = d["category"].lower()
    d["category_course"] = any(k in c for k in ("course", "kurs", "education", "egitim", "təhsil", "academy", "school", "training"))
    d["category_listings"] = any(k in c for k in ("real estate", "emlak", "daşınmaz", "property", "car", "auto", "hotel", "travel"))
    return d

def why(mid, b):
    r = []
    if mid == "awareness-ladder-loop":
        r += ["fits a relationship-building sale" if b["sales_cycle"] != "instant" else "instant sales gain less from a 4-step ladder"]
        if b["monthly_budget_usd"] < 600: r.append("budget is small: run it as 2 merged campaigns")
    if mid == "click-to-message" and b["messaging"] != "none": r.append(f"customers can buy in {b['messaging']} chats")
    if mid in ("andromeda-consolidated", "advantage-scale-lab") and not b["has_pixel"]: r.append("needs pixel/CAPI signals first")
    if b["content_engine"] == "low" and mid in ("andromeda-consolidated", "ugc-creators", "organic-amplification"): r.append("needs more creative output than you produce now")
    if mid == "instant-form-crm" and not b["has_crm"]: r.append("works better once CRM stages are sent back")
    return r

def recommend(path, top=3):
    b = norm(json.load(open(path, encoding="utf-8"))); sc = sorted(((m["fit"](b), k) for k, m in M.items()), reverse=True)
    print(f"# Methodology fit for {b.get('business', 'this business')} ({b['market']}, goal {b['goal']}, ~{b['monthly_budget_usd']:.0f} USD/month)\n")
    for i, (s, k) in enumerate(sc):
        mark = "**" if i < top else ""
        print(f"{i + 1:2d}. {mark}{M[k]['name']}{mark} [{k}] score {s}" + (f"  ({'; '.join(why(k, b))})" if why(k, b) else ""))
    print(f"\nSuggested combination: {M[sc[0][1]]['name']} as the structure" + (f", {M[sc[1][1]]['name']} as the second layer" if len(sc) > 1 else "") + ", offer-engineering and schwartz-awareness for the messages.")
    return [k for _, k in sc[:top]]

def blueprint(mid, path, out):
    if mid not in M: raise SystemExit(f"unknown method {mid}; run list")
    b = norm(json.load(open(path, encoding="utf-8"))); m = M[mid]; os.makedirs(out, exist_ok=True); fx = FX_PER_USD.get(b["currency"], 1.0)
    cpm = CPM_USD.get(b["market"], 5.0) * fx; stages = []
    for s in m["stages"]:
        bud = b["monthly_budget"] * s["share"]; daily = bud / 30.4
        conv = any(k in s["objective"] for k in ("Sales", "Leads", "App")) or "messag" in s["objective"].lower()
        est_cpa = cpm / 1000 / 0.010 / 0.08 if conv else None; need = est_cpa * 50 / 7 if est_cpa else None
        stages.append({**s, "monthly_budget": round(bud, 2), "daily_budget": round(daily, 2), "est_cost_per_result": round(est_cpa, 2) if est_cpa else None,
                       "daily_needed_for_learning": round(need, 2) if need else None, "learning_ok": (daily >= need) if need else None})
    bp = {"method": mid, "name": m["name"], "brief": {k: v for k, v in b.items() if not callable(v)}, "currency": b["currency"], "est_cpm": round(cpm, 2), "stages": stages, "rules": m["rules"], "pitfalls": m["pitfalls"]}
    json.dump(bp, open(os.path.join(out, "blueprint.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    md = [f"# {m['name']}: blueprint for {b.get('business', '')}", f"_{m['origin']}_", "", m["idea"], "",
          f"Market {b['market']}, budget {b['monthly_budget']} {b['currency']}/month, planning CPM ~{cpm:.2f} {b['currency']} (estimate, replace with real data).", ""]
    for i, s in enumerate(stages, 1):
        md += [f"## {i}. {s['stage']}  ({s['share']:.0%}, {s['monthly_budget']} {b['currency']}/month, {s['daily_budget']}/day)",
               f"- Audience: {s['audience']}", f"- Include: {', '.join(s['include']) or 'none (broad)'}", f"- Exclude: {', '.join(s['exclude']) or 'none'}",
               f"- Objective: {s['objective']}; performance goal: {s['performance_goal']}", f"- Message: {s['message']}", f"- KPI: {s['kpi']}"]
        if s["learning_ok"] is False: md.append(f"- WARNING: about {s['daily_needed_for_learning']} {b['currency']}/day is needed for ~50 results/week at the estimated cost per result ({s['est_cost_per_result']}). Merge stages, use one ad set, or optimise for a more frequent event.")
        md.append("")
    md += ["## Rules"] + [f"- {r}" for r in m["rules"]] + ["", "## Pitfalls"] + [f"- {p}" for p in m["pitfalls"]] + ["", "Next: meta-ads-builder (build sheet), ad-budget-planner (real numbers), ad-creative-strategist (concepts per stage), ad-tracking-setup (events and audiences)."]
    open(os.path.join(out, "blueprint.md"), "w", encoding="utf-8").write("\n".join(md)); print("\n".join(md))

EXAMPLE = {"business": "Kod Akademiya", "category": "online course", "offer": "Python bootcamp, 3 months", "price": 450, "currency": "AZN", "market": "AZ", "goal": "leads",
           "sales_cycle": "short", "margin": 0.7, "monthly_budget": 1500, "b2b": False, "local": False, "has_pixel": True, "has_crm": False, "has_catalog": False,
           "website": True, "messaging": "whatsapp", "followers": 6000, "brand_stage": "growing", "content_engine": "mid", "repeat_purchase": False, "season": None, "notes": ""}

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 1 and a[1] == "list": [print(f"{k:24s} {m['name']}  ({m['origin']})") for k, m in M.items()]
    elif len(a) > 2 and a[1] == "show" and a[2] not in M: print(f"unknown method {a[2]}; run list"); sys.exit(1)
    elif len(a) > 2 and a[1] == "show":
        m = M[a[2]]; print(f"# {m['name']}\n{m['origin']}\n\n{m['idea']}\n"); [print(f"- {s['stage']} ({s['share']:.0%}): {s['audience']}; include {s['include']}; exclude {s['exclude']}; {s['objective']} / {s['performance_goal']}; message: {s['message']}; KPI: {s['kpi']}") for s in m["stages"]]
        print("\nRules:"); [print("- " + r) for r in m["rules"]]; print("Pitfalls:"); [print("- " + p) for p in m["pitfalls"]]
    elif len(a) > 2 and a[1] == "recommend": recommend(a[2], int(opt("--top", 3)))
    elif len(a) > 4 and a[1] == "blueprint": blueprint(a[2], a[3], a[4])
    elif len(a) > 2 and a[1] == "brief": json.dump(EXAMPLE, open(a[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False); print("->", a[2])
    else: print(USAGE)
