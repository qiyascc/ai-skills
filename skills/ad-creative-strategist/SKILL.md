---
name: "ad-creative-strategist"
description: "Generate a diversified ad creative matrix (persona x angle x awareness level x format) with hooks, frameworks and CTAs in Azerbaijani, Turkish, Russian or English, lint copy for placement limits, local ad law and Meta policy, and score concept diversity the way Andromeda sees it."
---

# Ad Creative Strategist

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

In 2026 creative is the targeting. You produce concepts that are genuinely different (different person, angle, format, setting), written for the buyer's awareness level, legal in the market, and sized for the placement.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/creativelab.py` (Python 3 only). Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/creativelab.py tools/`.
- `matrix brief.json out --n 12 --lang tr|az|ru|en --stage cold|warm|hot` gives concepts.csv and concepts.md
- `hooks problem --lang az`: hook templates per awareness level
- `lint copy.csv --market TR|AZ`: length per placement, risky claims, Meta personal attribute policy, missing CTA
- `diversity concepts.csv`: flags pairs that are 60%+ alike (one creative entity to the delivery system)
Write the brief in the target language (offer, audience, benefits, proof, objections, price, personas) so hooks read naturally.

## 2. Building blocks
- Angles: pain, desire, proof, comparison (no named competitor), objection, offer, story, authority, demo, behind the scenes, myth, social proof.
- Awareness levels (Schwartz): unaware, problem, solution, product, most aware; cold stages lean unaware/problem/solution, warm product, hot most aware.
- Frameworks: PAS, AIDA, BAB, 4U, FAB, PASTOR.
- Formats: Reels 9:16 talking head, UGC/creator, demo with captions, 4:5 static, carousel, testimonial card, story poll, before/after only where policy allows.
- Limits: feed primary text about 125 visible characters, headline about 40; Reels text shorter; Telegram 160; keep 9:16 text out of the top ~14% and bottom ~20%.
- Law: Turkey (since 1 Aug 2026) "reklam" on influencer content, AI disclosure, real previous price for discounts, no unprovable superlatives; Azerbaijan Advertising Law: no misleading claims, Azerbaijani as the ad language; Meta: never assert personal attributes ("Are you in debt?").

## 3. Workflow
1. Get personas and angles from **market-audience-intel**; get the stage from **ad-strategy-architect**.
2. Run `matrix`; refine the hooks into natural local language; keep one concept per row.
3. Run `diversity` and fix near duplicates; run `lint` on the final copy.
4. Produce: script or layout per concept (first 2 seconds, proof moment, CTA), captions, 9:16 master plus 4:5 cut. For video editing use the user's Reels skills.
5. Ship 3 to 6 concepts per ad set; refresh cold creative every 2 to 4 weeks or when **ad-metrics-doctor** shows fatigue.
