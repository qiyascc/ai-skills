---
name: "ad-budget-planner"
description: "Plan ad budgets backwards from a sales or revenue goal (or forwards from a fixed budget) with unit economics, breakeven CPA and ROAS, pessimistic/base/optimistic scenarios, learning-phase feasibility, weekly pacing and a split by strategy stage."
---

# Ad Budget Planner

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

You turn "how much should we spend?" into arithmetic the owner can check: from the goal down to impressions, with breakeven lines, honest scenarios and a check that the algorithm can even learn at this budget.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/budgetplan.py` (Python 3 only). Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/budgetplan.py tools/`.
- `plan --price 450 --margin 0.7 --currency AZN --market AZ --sales 20 [--cpm 2.7] [--ctr 1.0] [--cvr 8] [--close 25] [--ltv-mult 1.5] [--months 1] [--blueprint blueprint.json] [--out dir]`
- `--revenue 9000` instead of `--sales`, or `--budget 1500` to see what a budget buys
- `breakeven --price 450 --margin 0.7 [--ltv-mult 1.5]`

## 2. The model
impressions = budget / CPM x 1000; clicks = impressions x CTR; leads (or chats, or results) = clicks x CVR; sales = leads x close rate.
Breakeven cost per sale = price x gross margin x LTV multiplier; breakeven ROAS = 1 / (margin x LTV multiplier).
Learning check: weekly results / 50 = how many ad sets can exit learning; the daily budget an ad set needs = cost per result x 50 / 7.
Planning CPMs by market and FX (per USD, Nov 2026: AZN 1.70, TRY about 50.4) are estimates: replace them with the account's real CPM, CTR and conversion rates after the first 1 to 2 weeks.

## 3. Workflow
1. Collect price, margin, close rate (from sales history; ask, do not guess silently) and the goal.
2. Run `plan`; show the base case and the scenarios; say clearly whether the plan is profitable on first purchase, only with LTV, or not at all at these assumptions.
3. If learning is impossible at this budget, recommend fewer ad sets, merged stages, or a more frequent optimisation event (conversations, landing page views) and expect noisier results.
4. With a blueprint from **ad-strategy-architect**, split the budget by stage; Turkey plans should include the Meta location fee (digital service tax) and VAT.
5. Re-run monthly with real numbers from **ad-metrics-doctor**.
