###############
# Qiyas Sadıqov CC
###############
import csv, datetime as dt, hashlib, re, sys

USAGE = """ad-tracking-setup: measurement plumbing for ads: UTM templates with platform macros, event plans per business
type, privacy-safe hashing of customer lists (E.164 phones for AZ, TR and more), CRM event files for Meta's
Conversions API for CRM, and a launch checklist.

  python3 tracking.py utm meta|google|tiktok|reddit|linkedin|telegram [--base https://site.az/page]
  python3 tracking.py events ecommerce|leadgen|messaging|realestate|course|app|local
  python3 tracking.py hash CUSTOMERS.csv OUT.csv [--country AZ]   -> normalised + SHA-256 hashed email, phone, fn, ln, ct, country (Meta / Google / TikTok customer lists)
  python3 tracking.py crm-events CRM.csv OUT.csv [--country AZ] [--currency AZN]
        CRM.csv columns: lead_id (optional), email, phone, stage (lead|contacted|qualified|booked|won), time (ISO or unix), value (optional)
        -> rows ready for Conversions API for CRM (event_name, event_time, action_source=system_generated, hashed user data, lead_event_source=crm)
  python3 tracking.py checklist                                  -> launch checklist (pixel, CAPI, dedup, EMQ, domains, attribution)
Needs: Python 3 only.
"""

UTM = {"meta": "utm_source={{site_source_name}}&utm_medium=paid_social&utm_campaign={{campaign.name}}&utm_term={{adset.name}}&utm_content={{ad.name}}&utm_id={{campaign.id}}",
       "google": "utm_source=google&utm_medium=cpc&utm_campaign={campaignid}&utm_term={keyword}&utm_content={creative}  (auto-tagging gclid stays on)",
       "tiktok": "utm_source=tiktok&utm_medium=paid_social&utm_campaign=__CAMPAIGN_NAME__&utm_term=__AID_NAME__&utm_content=__CID_NAME__",
       "reddit": "utm_source=reddit&utm_medium=paid_social&utm_campaign=CAMPAIGN_NAME&utm_content=AD_NAME  (replace with Reddit's macros if your account shows them)",
       "linkedin": "utm_source=linkedin&utm_medium=paid_social&utm_campaign=CAMPAIGN_NAME&utm_content=AD_NAME",
       "telegram": "utm_source=telegram&utm_medium=paid_messenger&utm_campaign=CAMPAIGN_NAME&utm_content=CHANNEL_OR_AD  (Telegram has no macros; for bots use a start parameter, e.g. t.me/yourbot?start=ad01)"}
EVENTS = {
 "ecommerce": [("ViewContent", "product page", "content_ids, value, currency"), ("AddToCart", "add to cart", "content_ids, value, currency"), ("InitiateCheckout", "checkout start", "value, num_items"), ("AddPaymentInfo", "payment step", "value"), ("Purchase", "order confirmed (server side too)", "value, currency, order_id as event_id")],
 "leadgen": [("ViewContent", "key page view", "content_name"), ("Lead", "form submit or instant form", "lead_id, value (expected lead value)"), ("CompleteRegistration", "account or signup", ""), ("Schedule", "meeting booked", "value"), ("QualifiedLead / Converted (CRM)", "CRM stage changes, sent via Conversions API for CRM", "lead_id, stage, value")],
 "messaging": [("Conversation started", "automatic for click to message ads", ""), ("LeadSubmitted (business messaging)", "agent or bot marks a qualified chat; send via Conversions API for business messaging / your WhatsApp platform", "ctwa_clid, value"), ("Purchase (business messaging)", "sale closed in chat", "value, currency")],
 "realestate": [("ViewContent", "listing page", "listing id (content_ids), price, city, rooms"), ("Search", "search with filters", "search_string, city"), ("Contact", "call / WhatsApp click on a listing", "listing id"), ("Lead", "viewing request form", "listing id, value"), ("Schedule", "viewing booked", "value"), ("Won (CRM)", "deal signed", "commission as value")],
 "course": [("ViewContent", "course page", "course id, price"), ("Lead", "free lesson / consultation request", "course id"), ("CompleteRegistration", "webinar or trial signup", ""), ("Schedule", "consultation booked", ""), ("Purchase", "payment", "value, currency")],
 "app": [("Install", "first open (SDK / MMP)", ""), ("CompleteRegistration", "signup", ""), ("StartTrial / Subscribe", "trial or subscription", "value, currency"), ("Purchase", "in-app purchase", "value, currency")],
 "local": [("Contact", "call or WhatsApp tap", ""), ("FindLocation", "map / directions tap", ""), ("Schedule", "booking", ""), ("Purchase (offline)", "in-store sale uploaded from POS/CRM", "value")]}
CC = {"AZ": ("994", 9), "TR": ("90", 10), "GE": ("995", 9), "KZ": ("7", 10), "UZ": ("998", 9), "RU": ("7", 10), "AE": ("971", 9), "SA": ("966", 9), "DE": ("49", None), "GB": ("44", 10), "US": ("1", 10)}
STAGE_EVENT = {"lead": "Lead", "contacted": "Contacted", "qualified": "QualifiedLead", "booked": "Schedule", "won": "Converted"}

def sha(x): return hashlib.sha256(x.encode("utf-8")).hexdigest() if x else ""

def phone_e164(p, country):
    d = re.sub(r"\D", "", p or "")
    if not d: return ""
    cc, nl = CC.get(country, ("", None))
    if d.startswith("00"): d = d[2:]
    if cc and nl and d.startswith(cc + "0") and len(d) == len(cc) + 1 + nl: d = cc + d[len(cc) + 1:]
    if cc and d.startswith(cc) and (nl is None or len(d) == len(cc) + nl): return d
    if d.startswith("0"): d = d[1:]
    if nl and len(d) == nl: return cc + d
    return d if len(d) > 9 else ""

def norm_name(x): return re.sub(r"[^\w]", "", (x or "").strip().lower(), flags=re.UNICODE)

def hash_file(src, dst, country="AZ"):
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig"))); keys = {k.lower().strip(): k for k in rows[0]}
    get = lambda r, *names: next((r[keys[n]] for n in names if n in keys and r[keys[n]]), "")
    out, bad = [], 0
    for r in rows:
        em = get(r, "email", "e-mail", "mail").strip().lower(); ph = phone_e164(get(r, "phone", "telefon", "tel", "mobile", "nömrə"), country)
        if not em and not ph: bad += 1; continue
        out.append({"email": sha(em), "phone": sha(ph), "fn": sha(norm_name(get(r, "fn", "first_name", "ad", "name"))), "ln": sha(norm_name(get(r, "ln", "last_name", "soyad", "surname"))),
                    "ct": sha(norm_name(get(r, "city", "ct", "şəhər", "şehir"))), "country": sha(country.lower())})
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["email", "phone", "fn", "ln", "ct", "country"]); w.writeheader(); w.writerows(out)
    print(f"-> {dst}: {len(out)} hashed rows, {bad} skipped (no e-mail or phone). Raw data never leaves your machine in clear text; keep consent records (KVKK / AZ personal data law).")

def ts(t):
    t = (t or "").strip()
    if t.isdigit(): return int(t)
    try: return int(dt.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp())
    except ValueError: return int(dt.datetime.now().timestamp())

def crm_events(src, dst, country="AZ", currency="AZN"):
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig"))); out = []
    for r in rows:
        st = (r.get("stage") or "").strip().lower()
        if st not in STAGE_EVENT: continue
        out.append({"event_name": STAGE_EVENT[st], "event_time": ts(r.get("time")), "action_source": "system_generated", "lead_id": r.get("lead_id", ""), "em": sha((r.get("email") or "").strip().lower()),
                    "ph": sha(phone_e164(r.get("phone"), country)), "value": r.get("value", ""), "currency": currency if r.get("value") else "", "lead_event_source": "crm", "event_source": "crm"})
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["event_name"]); w.writeheader(); w.writerows(out)
    print(f"-> {dst}: {len(out)} CRM events ({', '.join(sorted({o['event_name'] for o in out}))}). Send via Conversions API for CRM (or a partner such as Zapier/Make), then use the Conversion leads performance goal on instant form campaigns.")

CHECK = ["Pixel on every page; Conversions API server events for the same events, both carrying the same event_id (deduplication)", "Events Manager: test events received; Event Match Quality 6+ (8+ at scale): send e-mail, phone, external_id, fbp/fbc, IP and user agent",
         "Domain verified in Business Manager; aggregated event priorities no longer limit web events, but keep the purchase / lead event clean", "Value and currency on Purchase (and on Lead if you can estimate lead value)",
         "UTM template on every ad (tracking.py utm); same names as the naming convention", "CRM: lead_id stored, stages updated within 24 hours, sent back to Meta (Conversions API for CRM) for conversion leads optimisation",
         "Messaging: track qualified chats and sales from WhatsApp / Instagram (business messaging events) so click to message ads learn quality", "Attribution: 7-day click, 1-day engage-through, 1-day view is the default; report with the same setting every time; 7d and 28d view no longer exist",
         "Analytics: GA4 or similar with consent mode; compare platform conversions with your own orders weekly (expect differences)", "Consent and law: cookie / data consent where required (KVKK in Turkey, GDPR in the EU, AZ personal data law); customer lists only with consent"]

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) > 2 and a[1] == "utm": base = opt("--base"); u = UTM[a[2]]; print((base + ("&" if "?" in base else "?") if base else "") + u)
    elif len(a) > 2 and a[1] == "events": print(f"# Event plan: {a[2]}\n| event | fires when | parameters |\n|---|---|---|"); [print(f"| {e} | {w} | {p} |") for e, w, p in EVENTS[a[2]]]
    elif len(a) > 3 and a[1] == "hash": hash_file(a[2], a[3], opt("--country", "AZ").upper())
    elif len(a) > 3 and a[1] == "crm-events": crm_events(a[2], a[3], opt("--country", "AZ").upper(), opt("--currency", "AZN"))
    elif len(a) > 1 and a[1] == "checklist": [print(f"- [ ] {c}") for c in CHECK]
    else: print(USAGE)
