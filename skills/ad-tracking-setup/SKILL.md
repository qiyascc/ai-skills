---
name: "ad-tracking-setup"
description: "Set up ad measurement properly: UTM templates with platform macros, event plans per business type, SHA-256 hashing of customer lists with E.164 phones (AZ, TR and more), CRM event files for Meta's Conversions API for CRM, and a launch checklist for pixel, CAPI, deduplication and attribution."
---

# Ad Tracking Setup

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Ads optimise for the signals they receive. You make those signals complete, correct and privacy-safe, so the algorithm learns what a real customer is.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/tracking.py` (Python 3 only). Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/tracking.py tools/`.
- `utm meta|google|tiktok|reddit|linkedin|telegram [--base URL]`
- `events ecommerce|leadgen|messaging|realestate|course|app|local`
- `hash customers.csv hashed.csv --country AZ`: normalised e-mail, E.164 phone (050 123 45 67 becomes 994501234567; 0532 111 22 33 becomes 905321112233), names, city, country, all SHA-256
- `crm-events crm.csv events.csv --country AZ --currency AZN`: stages (lead, contacted, qualified, booked, won) as Conversions API for CRM rows
- `checklist`

## 2. Principles
- Pixel plus Conversions API with the same event_id for deduplication; Event Match Quality 6+ (8+ at scale).
- Value and currency on purchases, and on leads when you can estimate lead value.
- Conversion leads: send CRM stages back so instant form campaigns optimise for qualified leads (Meta reports about 21% lower cost per quality lead in tests); for click to WhatsApp send qualified chat and sale events.
- Same names in UTMs and campaigns (naming from **meta-ads-builder**).
- 2026 attribution default: 7-day click, 1-day engage-through, 1-day view; report consistently.
- Consent first: KVKK (Turkey), Azerbaijan personal data law, GDPR in the EU; upload only lists you have consent for; hashing happens locally.

## 3. Workflow
1. Pick the event plan for the business type; map each event to where it fires (browser, server, CRM, chat platform).
2. Generate UTMs per platform; add them to every ad.
3. Hash customer lists before uploading them as custom audiences or exclusions (C4 in the awareness ladder).
4. Export CRM stages weekly (or connect a partner like Zapier/Make) and send them with `crm-events` rows.
5. Run the checklist before launch and again after the first week.
