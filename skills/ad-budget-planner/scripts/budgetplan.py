###############
# Qiyas Sadıqov CC
###############
import csv, json, math, os, sys

USAGE = """ad-budget-planner: reverse-funnel budget planning. From a sales or revenue goal and unit economics to the
impressions, clicks, leads and budget needed, with breakeven checks, scenarios, learning-phase feasibility, weekly
pacing and a split by strategy stage.

  python3 budgetplan.py plan --price 450 --margin 0.7 --currency AZN --market AZ [--sales 20 | --revenue 9000 | --budget 1500]
        [--cpm 2.7] [--ctr 1.0] [--cvr 8] [--close 25] [--ltv-mult 1.0] [--months 1] [--blueprint blueprint.json] [--out plan_dir]
      cvr   = % of link clicks (or chat starts) that become a lead / result
      close = % of leads that buy (100 for direct e-commerce purchases)
      --budget instead of a goal answers "what will this budget buy?"
  python3 budgetplan.py breakeven --price 450 --margin 0.7 [--ltv-mult 1.5]   -> breakeven CPA and ROAS
Outputs plan.md and plan.csv when --out is given. Planning CPMs and FX are estimates: replace with account data.
Needs: Python 3 only.
"""

CPM_USD = {"AZ": 1.6, "TR": 2.0, "GE": 1.6, "KZ": 1.8, "UZ": 1.1, "AE": 6.0, "SA": 4.5, "DE": 8.0, "GB": 9.0, "US": 14.0}
FX = {"USD": 1.0, "AZN": 1.70, "TRY": 50.4, "EUR": 0.905, "GEL": 2.7, "KZT": 500.0, "UZS": 12500.0, "AED": 3.67, "SAR": 3.75, "GBP": 0.78}

def funnel(budget, cpm, ctr, cvr, close):
    imp = budget / cpm * 1000; clicks = imp * ctr / 100; leads = clicks * cvr / 100; sales = leads * close / 100
    return {"budget": budget, "impressions": imp, "clicks": clicks, "leads": leads, "sales": sales, "cpl": budget / leads if leads else None, "cpa": budget / sales if sales else None}

def plan(o):
    cur = o["currency"]; fx = FX.get(cur, 1.0); cpm = o["cpm"] or CPM_USD.get(o["market"], 5.0) * fx
    unit_profit = o["price"] * o["margin"] * o["ltv_mult"]; be_cpa = unit_profit; be_roas = 1 / (o["margin"] * o["ltv_mult"]) if o["margin"] else None
    cost_per_sale = cpm / 1000 / (o["ctr"] / 100) / (o["cvr"] / 100) / (o["close"] / 100)
    if o["budget"]: budget = o["budget"]
    else:
        sales = o["sales"] or (o["revenue"] / o["price"] if o["revenue"] else 10); budget = sales * cost_per_sale
    base = funnel(budget, cpm, o["ctr"], o["cvr"], o["close"])
    scen = {"pessimistic": funnel(budget, cpm * 1.25, o["ctr"] * 0.75, o["cvr"] * 0.75, o["close"] * 0.85), "base": base, "optimistic": funnel(budget, cpm * 0.85, o["ctr"] * 1.25, min(100, o["cvr"] * 1.2), min(100, o["close"] * 1.1))}
    weeks = 4.35 * o["months"]; wk_leads = base["leads"] / weeks; max_sets = max(0, math.floor(wk_leads / 50))
    L = [f"# Budget plan ({o['market']}, {cur})", f"Price {o['price']} {cur}, gross margin {o['margin']:.0%}, LTV multiplier {o['ltv_mult']}: profit per customer {unit_profit:,.2f} {cur}",
         f"Breakeven cost per sale {be_cpa:,.2f} {cur}; breakeven ROAS {be_roas:.2f}" if be_roas else "", f"Assumptions: CPM {cpm:,.2f}, link CTR {o['ctr']}%, click to lead {o['cvr']}%, lead to sale {o['close']}%", "",
         f"## Base case over {o['months']} month(s)", f"- Budget **{budget:,.0f} {cur}** ({budget / fx:,.0f} USD), about {budget / (30.4 * o['months']):,.0f} {cur}/day",
         f"- Impressions {base['impressions']:,.0f}, link clicks {base['clicks']:,.0f}, leads {base['leads']:,.1f}, sales {base['sales']:,.1f}",
         f"- Cost per lead {base['cpl']:,.2f}, cost per sale {base['cpa']:,.2f} {cur}: " + ("PROFITABLE on first purchase" if base["cpa"] and base["cpa"] < o["price"] * o["margin"] else "profitable only with repeat/LTV" if base["cpa"] and base["cpa"] < be_cpa else "LOSS at these assumptions: fix offer, price, conversion or close rate before scaling"), "",
         "## Scenarios", "| case | impressions | clicks | leads | sales | cost per sale |", "|---|---|---|---|---|---|"]
    L += [f"| {k} | {v['impressions']:,.0f} | {v['clicks']:,.0f} | {v['leads']:,.1f} | {v['sales']:,.1f} | {v['cpa']:,.2f} |" if v["cpa"] else f"| {k} | {v['impressions']:,.0f} | {v['clicks']:,.0f} | {v['leads']:,.1f} | 0 | n/a |" for k, v in scen.items()]
    L += ["", "## Learning phase", f"- About {wk_leads:,.1f} leads/results per week: room for {max_sets} ad set(s) that can reach ~50 optimisation events/week" + (" (optimise one ad set, or a more frequent event such as conversations or landing page views, and accept 'learning limited')" if max_sets < 1 else ""),
          f"- Daily budget an ad set needs for 50 results/week at cost per lead {base['cpl']:,.2f}: {base['cpl'] * 50 / 7:,.0f} {cur}" if base["cpl"] else "", "", "## Weekly pacing"]
    L += [f"- Week {w + 1}: {budget / weeks * min(1, weeks - w):,.0f} {cur}" + (" (launch, no edits for 7 days)" if w == 0 else "") for w in range(int(math.ceil(weeks)))]
    rows = []
    if o.get("blueprint"):
        bp = json.load(open(o["blueprint"], encoding="utf-8")); L += ["", f"## Split by stage ({bp['name']})"]
        for s in bp["stages"]:
            sb = budget * s["share"]; L.append(f"- {s['stage']}: {s['share']:.0%} = {sb:,.0f} {cur} ({sb / (30.4 * o['months']):,.1f}/day)"); rows.append([s["stage"], s["share"], round(sb, 2)])
    L += ["", "Turkey: Meta adds a location fee for Turkish audiences (5% digital service tax in 2026, 2.5% from 2027) and VAT applies via reverse charge; budget the gross amount." if o["market"] == "TR" else ""]
    txt = "\n".join(x for x in L if x is not None); print(txt)
    if o.get("out"):
        os.makedirs(o["out"], exist_ok=True); open(os.path.join(o["out"], "plan.md"), "w", encoding="utf-8").write(txt)
        with open(os.path.join(o["out"], "plan.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["case", "budget", "impressions", "clicks", "leads", "sales", "cost_per_lead", "cost_per_sale"])
            for k, v in scen.items(): w.writerow([k, round(v["budget"], 2), round(v["impressions"]), round(v["clicks"]), round(v["leads"], 1), round(v["sales"], 1), round(v["cpl"] or 0, 2), round(v["cpa"] or 0, 2)])
            if rows: w.writerow([]); w.writerow(["stage", "share", "budget"]); w.writerows(rows)

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d; fl = lambda k, d=None: float(opt(k)) if opt(k) is not None else d
    if len(a) > 1 and a[1] in ("plan", "breakeven"):
        o = {"price": fl("--price", 100), "margin": fl("--margin", 0.5), "currency": opt("--currency", "USD"), "market": opt("--market", "AZ").upper(), "sales": fl("--sales"), "revenue": fl("--revenue"), "budget": fl("--budget"),
             "cpm": fl("--cpm"), "ctr": fl("--ctr", 1.0), "cvr": fl("--cvr", 8.0), "close": fl("--close", 25.0), "ltv_mult": fl("--ltv-mult", 1.0), "months": fl("--months", 1.0), "blueprint": opt("--blueprint"), "out": opt("--out")}
        if a[1] == "breakeven": print(f"breakeven cost per sale {o['price'] * o['margin'] * o['ltv_mult']:.2f} {o['currency']}, breakeven ROAS {1 / (o['margin'] * o['ltv_mult']):.2f}")
        else: plan(o)
    else: print(USAGE)
