---
name: "market-audience-intel"
description: "Market and audience intelligence for advertising, deepest on Azerbaijan and Turkey: platforms, purchasing power, payment and installment habits, language, culture, ad law, seasonal calendar, affordability framing and persona sheets."
---

# Market and Audience Intel

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

You know the market before you spend in it: who is online where, what money they have, how they pay, what language and tone they trust, what the law forbids and when demand peaks. Strongest on Azerbaijan and Turkey; also Georgia, Kazakhstan, Uzbekistan, UAE, Saudi Arabia, Germany, UK, US.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/marketintel.py` (Python 3 only). Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/marketintel.py tools/`.
- `profile AZ`, `compare AZ TR GE`, `markets`
- `afford AZ 120000 --currency AZN`: price as months of income, the funnel it calls for, installment framing
- `persona AZ --category "real estate" --city Baku --income high`
- `calendar TR --from 2026-11-21 --months 6`: peaks and quiet days, with the date to start building warm audiences

## 2. What the data says (snapshot, Nov 2026)
**Azerbaijan:** 10.25M people, 8.44M social media identities (80.6%); Facebook 5.3M and Instagram 4.5M ad audiences, 25-34 the biggest Instagram group; YouTube has the largest share of social traffic. Average nominal wage about 1,174 AZN (H1 2026, gross; Baku higher, regions much lower), median about 600, minimum 400, inflation about 5.7%. Cash still matters, but cards and 0% installment cards (BirKart, Tamkart, Birbank taksit) are everywhere; card-to-card transfers were 71% of e-commerce volume in 2024. Azerbaijani is the default ad language; Russian versions are worth testing for Baku premium segments. Trust is personal: faces, phone, WhatsApp, real office. Quiet days: 20 January and 27 September (no promotions).
**Turkey:** about 86M people, 61M social identities, about 25 hours of social media a week; Instagram is the main app (about 1h53m a day, 66M audience), then YouTube and TikTok. Net minimum wage 28,075 TL (2026), annual inflation 29.77% (Oct 2026), USD/TRY about 50.4 (Nov 2026). Credit card installments (taksit) drive purchases; marketplaces and price comparison are constant. Law since 1 Aug 2026: influencer content must carry "reklam", AI-generated content must be disclosed, children may not be profiled for targeting, discount claims need a real previous price; Reklam Kurulu fines are large. Meta adds a location fee for Turkish audiences (5% digital service tax in 2026, 2.5% from 2027).

## 3. Workflow
1. Run `profile` for every target market; summarise what changes the plan (platforms, language, payment, law, season).
2. Run `afford` with the real price: under 0.05 months of income sell directly; 0.05 to 0.5 show price, proof, installments; 0.5 to 3 go through leads or chat with monthly framing; above 3 months the conversion is a consultation or viewing, optimised for qualified leads.
3. Run `persona` per segment and feed the angles, objections and trust signals to **ad-creative-strategist**.
4. Run `calendar` and plan bursts with **ad-strategy-architect** (seasonal burst) 4 to 6 weeks ahead.
5. Refresh fast-moving numbers (wages, inflation, FX, platform users) with a web search before big budget decisions, and say when a figure is a dated snapshot.
