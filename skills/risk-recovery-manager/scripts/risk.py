###############
# Qiyas Sadıqov CC
###############
import csv, json, math, os, sys, glob
import numpy as np, pandas as pd

USAGE = """risk-recovery-manager: position sizing, portfolio allocation (one idea or many, decided by edge and correlation),
drawdown throttle and recovery plan, Monte Carlo of goals vs ruin, and trade journal analytics.

  python3 risk.py size --balance 1000 --risk 1 --entry 1.0850 --stop 1.0820 --symbol EURUSD [--account USD] [--contract 100000] [--quote-rate 1] [--leverage 30]
  python3 risk.py allocate IDEAS (scan.json from ta.py or ideas.csv) --balance 1000 [--prices DIR] [--budget 6] [--max-per 2.5] [--dd 0] [--leverage 30]
      -> allocation.csv: which ideas get risk and how much (could be 1 idea or 15), correlation clusters, margin
  python3 risk.py throttle --peak 1200 --equity 1030 [--base-risk 1]   -> current risk level and the recovery ladder
  python3 risk.py recovery                                              -> % gain needed to recover each drawdown
  python3 risk.py simulate --win 0.45 --rr 2 --risk 1 [--trades 100] [--goal 60] [--ruin 30] [--throttle] [--runs 20000]
  python3 risk.py target --goal 60 --trades 100 [--ruin 30]            -> what win rate / R:R / risk a goal really requires, and its odds
  python3 risk.py kelly --win 0.45 --rr 2                               -> Kelly, half and quarter Kelly risk %
  python3 risk.py journal JOURNAL.csv [--out dir]                       -> expectancy by setup/symbol/hour, tilt and overtrading checks
JOURNAL.csv columns: time, symbol, setup, dir, entry, stop, exit, risk_pct (or size), pnl, notes (R computed if missing).
Needs: Python 3, numpy, pandas.
"""

CONTRACTS = {"XAUUSD": 100, "XAGUSD": 5000, "XPTUSD": 100, "USOIL": 1000, "UKOIL": 1000, "WTI": 1000, "BRENT": 1000, "NATGAS": 10000,
             "US500": 1, "US30": 1, "US100": 1, "DE40": 1, "UK100": 1, "JP225": 1, "BTCUSD": 1, "ETHUSD": 1}
CCY = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK", "DKK", "PLN", "HUF", "CZK", "TRY", "ZAR", "MXN", "SGD", "HKD", "CNH", "ILS"}
LADDER = [(0, 1.0), (5, 0.75), (10, 0.5), (15, 0.25), (20, 0.0)]

def throttle_mult(dd):
    m = 1.0
    for lim, mult in LADDER:
        if dd >= lim: m = mult
    return m

def contract_value(symbol, account, entry, contract, quote_rate):
    s = symbol.upper().replace("/", ""); base, quote = (s[:3], s[3:6]) if len(s) >= 6 and s[:6].isalpha() else (None, None)
    if quote_rate: conv = quote_rate
    elif quote == account: conv = 1.0
    elif base == account: conv = 1 / entry
    else: conv = 1.0
    return contract * conv, conv

def size(balance, risk, entry, stop, symbol, account="USD", contract=None, quote_rate=None, leverage=30):
    s = symbol.upper(); fx = len(s) == 6 and s[:3] in CCY and s[3:] in CCY and s not in CONTRACTS
    contract = contract or CONTRACTS.get(s) or (100000 if fx else 1); per_lot, conv = contract_value(s, account, entry, contract, quote_rate)
    risk_amt = balance * risk / 100; dist = abs(entry - stop)
    if dist <= 0: raise SystemExit("stop must differ from entry")
    lots = risk_amt / (dist * per_lot); notional = lots * contract * entry * (conv if fx else 1); margin = notional / leverage
    pip = 0.01 if "JPY" in s else 0.0001
    print(f"# Position size {s}: risk {risk}% of {balance} {account} = {risk_amt:.2f} {account}")
    print(f"- stop distance {dist:.6g}" + (f" ({dist / pip:.1f} pips, pip value per lot {pip * per_lot:.2f} {account})" if fx else ""))
    print(f"- size {lots:.3f} lots of {contract:g} ({lots * contract:,.6g} units); notional ~{notional:,.0f} {account}; margin at 1:{leverage:g} ~{margin:,.2f} {account} ({margin / balance * 100:.0f}% of balance)")
    if fx and not quote_rate and account not in (s[:3], s[3:]): print(f"- WARNING: {s[3:]} is not the account currency: pip value above is in {s[3:]}; pass --quote-rate ({account} per 1 {s[3:]}) for a correct size")
    if margin > balance * 0.5: print("- WARNING: margin over 50% of balance: a small adverse move can trigger a margin call; reduce size or widen nothing, skip the trade")
    if lots < 0.01 and contract > 1: print("- below the usual 0.01 lot minimum: this account is too small for this stop; use a smaller stop only if the setup allows, or skip")
    return lots

def load_ideas(path):
    if path.endswith(".json"):
        rows = json.load(open(path)); out = []
        for r in rows:
            if r.get("best_dir") and r.get("plan"):
                p = r["plan"]; out.append({"symbol": r["symbol"], "dir": r["best_dir"], "score": r["best_score"], "setup": r["best"], "entry": p["entry"], "stop": p["stop"], "rr": p["rr"]})
        return out
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        out.append({"symbol": r["symbol"], "dir": 1 if str(r["dir"]).lower() in ("1", "long", "buy") else -1, "score": float(r.get("score", 60)), "setup": r.get("setup", ""),
                    "entry": float(r["entry"]), "stop": float(r["stop"]), "rr": float(r.get("rr", 2)), "win": float(r["win"]) if r.get("win") else None})
    return out

def edge_from(idea):
    if idea.get("win"): p = idea["win"]
    else: p = 1 / (1 + idea["rr"]) + 0.002 * (idea["score"] - 50)
    b = idea["rr"]; ev = p * b - (1 - p); kelly = ev / b if b > 0 else 0
    return p, ev, max(0.0, kelly)

def returns_matrix(prices_dir, symbols):
    rets = {}
    for s in symbols:
        f = next(iter(glob.glob(os.path.join(prices_dir, f"{s}*.csv"))), None)
        if not f: continue
        d = pd.read_csv(f, sep=None, engine="python"); d.columns = [c.lower().strip("<>") for c in d.columns]; c = pd.to_numeric(d["close"], errors="coerce")
        rets[s] = np.log(c).diff().tail(500).reset_index(drop=True)
    return pd.DataFrame(rets).dropna() if rets else None

def allocate(path, balance, prices=None, budget=6.0, max_per=2.5, dd=0.0, leverage=30, out="allocation.csv"):
    ideas = [i for i in load_ideas(path) if i["score"] >= 50]
    if not ideas: print("No idea scores 50 or more: no trade is a position too. Cash stays in the account."); return []
    mult = throttle_mult(dd); budget *= mult; max_per *= mult
    if mult == 0: print(f"Drawdown {dd}%: trading paused by the recovery ladder. Review the journal before the next trade."); return []
    for i in ideas: i["p"], i["ev"], i["kelly"] = edge_from(i)
    ideas = [i for i in ideas if i["ev"] > 0]; ideas.sort(key=lambda i: -i["ev"])
    R = returns_matrix(prices, [i["symbol"] for i in ideas]) if prices else None
    corr = R.corr() if R is not None and len(R) > 50 else None
    chosen = []
    for i in ideas:
        raw = min(max_per, 100 * i["kelly"] / 4)
        same_bet = []
        if corr is not None and i["symbol"] in corr:
            for c in chosen:
                if c["symbol"] in corr:
                    rho = corr.loc[i["symbol"], c["symbol"]] * i["dir"] * c["dir"]
                    if rho > 0.6: same_bet.append((c["symbol"], round(float(rho), 2)))
        if same_bet: raw *= 0.5 ** len(same_bet)
        i["risk_pct"] = round(raw, 2); i["same_bet_as"] = same_bet; chosen.append(i)
    tot = sum(i["risk_pct"] for i in chosen)
    if tot > budget:
        for i in chosen: i["risk_pct"] = round(i["risk_pct"] * budget / tot, 2)
    chosen = [i for i in chosen if i["risk_pct"] >= 0.1]
    top = chosen[0]["ev"] if chosen else 0; conc = len(chosen) == 1 or (chosen and chosen[0]["risk_pct"] >= 0.6 * sum(i["risk_pct"] for i in chosen))
    print(f"# Allocation for {balance} (risk budget {budget:.1f}% total, max {max_per:.1f}% per idea" + (f", throttled x{mult} for {dd}% drawdown" if mult < 1 else "") + ")")
    print("| symbol | dir | setup | score | est. hit rate | EV per R | risk % | risk amount | correlated with |\n|---|---|---|---|---|---|---|---|---|")
    rows = []
    for i in chosen:
        amt = balance * i["risk_pct"] / 100; print(f"| {i['symbol']} | {'LONG' if i['dir'] == 1 else 'SHORT'} | {i['setup']} | {i['score']:.0f} | {i['p']:.0%} | {i['ev']:+.2f} | {i['risk_pct']} | {amt:.2f} | {', '.join(f'{s} ({r})' for s, r in i['same_bet_as'])} |")
        rows.append({k: i.get(k) for k in ("symbol", "dir", "setup", "score", "entry", "stop", "rr", "p", "ev", "risk_pct")} | {"risk_amount": round(amt, 2)})
    total = sum(i["risk_pct"] for i in chosen)
    print(f"Total open risk {total:.2f}% ({balance * total / 100:.2f}). " + ("Concentrated: one idea clearly dominates, so most of the risk goes there." if conc else f"Spread over {len(chosen)} ideas because no single edge dominates and correlation was checked."))
    print("Then size each line with: risk.py size --entry ... --stop ... --risk <risk %>. The allocation can be 1 idea or many: the cap is on risk, never on conviction.")
    with open(out, "w", newline="") as f:
        if rows: w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return rows

def throttle(peak, equity, base):
    dd = max(0.0, (1 - equity / peak) * 100); m = throttle_mult(dd)
    print(f"# Drawdown {dd:.1f}% (peak {peak}, now {equity}): risk per trade {base * m:.2f}% (x{m})")
    for lim, mult in LADDER: print(f"- drawdown {lim}%+: risk x{mult}" + ("  <- now" if throttle_mult(dd) == mult and dd >= lim else "") + ("  (stop trading, review journal, demo only until 20 good trades)" if mult == 0 else ""))
    print("Recovery rule: step back up one level only after equity regains half of the distance to the peak AND the last 10 trades have positive expectancy.")
    print("Never increase size to win losses back (martingale): it converts a drawdown into a wipe-out. Recovery comes from a positive edge plus time.")

def recovery():
    print("| drawdown | gain needed to recover | trades at +0.3R and 1% risk |\n|---|---|---|")
    for d in (5, 10, 15, 20, 30, 40, 50, 60, 75, 90):
        need = 1 / (1 - d / 100) - 1; n = math.log(1 + need) / math.log(1 + 0.003); print(f"| {d}% | {need * 100:.0f}% | ~{n:.0f} |")

def simulate(win, rr, risk, trades=100, goal=60, ruin=30, use_throttle=False, runs=20000, quiet=False):
    rng = np.random.default_rng(1); hit = rng.random((runs, trades)) < win
    eq = np.ones(runs); peak = np.ones(runs); maxdd = np.zeros(runs); reached = np.zeros(runs, bool); ruined = np.zeros(runs, bool)
    for t in range(trades):
        alive = ~(reached | ruined); dd = 1 - eq / peak
        r = risk / 100 * (np.vectorize(throttle_mult)(dd * 100) if use_throttle else 1.0)
        eq = np.where(alive, eq * (1 + np.where(hit[:, t], r * rr, -r)), eq); peak = np.maximum(peak, eq); maxdd = np.maximum(maxdd, 1 - eq / peak)
        reached |= alive & (eq >= 1 + goal / 100); ruined |= alive & (eq <= 1 - ruin / 100)
    ev = win * rr - (1 - win)
    res = {"p_goal": reached.mean(), "p_ruin": ruined.mean(), "median_end": np.median(eq) - 1, "p10": np.percentile(eq, 10) - 1, "p90": np.percentile(eq, 90) - 1, "median_maxdd": np.median(maxdd), "p95_maxdd": np.percentile(maxdd, 95), "ev": ev}
    if not quiet:
        print(f"# Monte Carlo: win {win:.0%}, R:R {rr}, risk {risk}%/trade, {trades} trades, {runs} runs" + (", with drawdown throttle" if use_throttle else ""))
        print(f"- expectancy {ev:+.2f}R per trade" + ("  (NEGATIVE: no sizing can fix this)" if ev <= 0 else ""))
        print(f"- chance to reach +{goal}% before -{ruin}%: {res['p_goal']:.1%}; chance of hitting -{ruin}% first: {res['p_ruin']:.1%}")
        print(f"- final result: median {res['median_end']:+.1%}, worst 10% {res['p10']:+.1%}, best 10% {res['p90']:+.1%}")
        print(f"- max drawdown: median {res['median_maxdd']:.1%}, worst 5% {res['p95_maxdd']:.1%}")
    return res

def target(goal, trades, ruin):
    print(f"# What does +{goal}% in {trades} trades require? (ruin line -{ruin}%)\n| win rate | R:R | risk % | P(goal) | P(ruin) | median end |\n|---|---|---|---|---|---|")
    for win, rr in ((0.30, 2.0), (0.34, 2.0), (0.40, 2.0), (0.45, 2.0), (0.50, 2.0), (0.55, 1.5)):
        for risk in (1, 2, 3, 5):
            r = simulate(win, rr, risk, trades, goal, ruin, False, 5000, quiet=True)
            print(f"| {win:.0%} | {rr} | {risk} | {r['p_goal']:.0%} | {r['p_ruin']:.0%} | {r['median_end']:+.0%} |")
    print("Read it honestly: the first rows (30 to 34% at 2R, zero or negative edge) are where most retail traders really are; the table only looks good if the edge is real and proven in a journal.")
    print("High goals in short windows need large risk per trade, and large risk raises the ruin odds as fast as the goal odds.")

def kelly(win, rr):
    k = (win * rr - (1 - win)) / rr
    print(f"Kelly {k * 100:.1f}% of equity per trade; half Kelly {k * 50:.1f}%; quarter Kelly {k * 25:.1f}%." + (" Negative: no edge, do not trade this." if k <= 0 else " Use quarter Kelly or less: win-rate estimates are noisy and full Kelly drawdowns are brutal (50%+ is normal)."))

def journal(path, out=None):
    d = pd.read_csv(path); d.columns = [c.lower().strip() for c in d.columns]; d["time"] = pd.to_datetime(d["time"], errors="coerce")
    if "r" not in d.columns:
        d["r"] = (d.exit - d.entry) * np.where(d["dir"].astype(str).str.lower().isin(["1", "long", "buy"]), 1, -1) / (d.entry - d.stop).abs()
    d = d.dropna(subset=["r"]).sort_values("time"); R = d.r
    eqv = (1 + d.get("risk_pct", pd.Series(1, index=d.index)) / 100 * R).cumprod(); dd = eqv / eqv.cummax().clip(lower=1) - 1
    print(f"# Journal: {len(d)} trades, win rate {(R > 0).mean():.0%}, expectancy {R.mean():+.2f}R, profit factor {R[R > 0].sum() / max(1e-9, -R[R <= 0].sum()):.2f}, max DD {dd.min():.1%}")
    for col in ("setup", "symbol"):
        if col in d:
            g = d.groupby(col).r.agg(["count", "mean", "sum"]).sort_values("sum", ascending=False)
            print(f"## by {col}"); [print(f"- {k}: {int(r['count'])} trades, {r['mean']:+.2f}R avg, {r['sum']:+.1f}R total" + ("  <- cut this" if r["count"] >= 10 and r["mean"] < 0 else "")) for k, r in g.iterrows()]
    d["hour"] = d.time.dt.hour; g = d.groupby("hour").r.mean()
    print("## worst hours: " + ", ".join(f"{h}:00 ({v:+.2f}R)" for h, v in g.sort_values().head(3).items()))
    gap = d.time.diff().dt.total_seconds() / 60; prev_loss = R.shift() < 0
    rp = d.get("risk_pct", pd.Series(np.nan, index=d.index)); bigger = rp > rp.shift()
    tilt = d[(prev_loss) & (gap < 30)]
    if len(tilt): print(f"## tilt: {len(tilt)} trades opened within 30 min of a loss, avg {tilt.r.mean():+.2f}R" + (f"; {int((bigger & prev_loss & (gap < 30)).sum())} of them with BIGGER risk (revenge sizing)" if rp.notna().any() else ""))
    per_day = d.groupby(d.time.dt.date).size()
    if per_day.max() > 5: print(f"## overtrading: max {per_day.max()} trades in a day; days with 5+ trades average {d[d.time.dt.date.isin(per_day[per_day >= 5].index)].r.mean():+.2f}R")
    streak = max((len(list(g)) for k, g in __import__('itertools').groupby(R <= 0) if k), default=0); print(f"## longest losing streak: {streak}")
    if out:
        os.makedirs(out, exist_ok=True); d.to_csv(os.path.join(out, "journal_scored.csv"), index=False)

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, dflt=None: a[a.index(k) + 1] if k in a else dflt; f = lambda k, dflt=None: float(opt(k)) if opt(k) is not None else dflt
    cmd = a[1] if len(a) > 1 else ""
    if cmd == "size": size(f("--balance", 1000), f("--risk", 1), f("--entry"), f("--stop"), opt("--symbol", "EURUSD"), opt("--account", "USD").upper(), f("--contract"), f("--quote-rate"), f("--leverage", 30))
    elif cmd == "allocate": allocate(a[2], f("--balance", 1000), opt("--prices"), f("--budget", 6), f("--max-per", 2.5), f("--dd", 0), f("--leverage", 30), opt("--out", "allocation.csv"))
    elif cmd == "throttle": throttle(f("--peak"), f("--equity"), f("--base-risk", 1))
    elif cmd == "recovery": recovery()
    elif cmd == "simulate": simulate(f("--win", 0.45), f("--rr", 2), f("--risk", 1), int(f("--trades", 100)), f("--goal", 60), f("--ruin", 30), "--throttle" in a, int(f("--runs", 20000)))
    elif cmd == "target": target(f("--goal", 60), int(f("--trades", 100)), f("--ruin", 30))
    elif cmd == "kelly": kelly(f("--win", 0.45), f("--rr", 2))
    elif cmd == "journal": journal(a[2], opt("--out"))
    else: print(USAGE)
