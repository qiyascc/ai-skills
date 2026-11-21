###############
# Qiyas Sadıqov CC
###############
import csv, datetime as dt, glob, io, json, os, sys, contextlib

USAGE = """trading-desk: the orchestrator. Daily brief across many instruments, strategy playbook by regime, research
evidence base, legendary traders' numbers, structured bull/bear/risk debate, order tickets the user places by hand,
and a running journal.

  python3 desk.py daily PRICES_DIR --balance 1000 [--tf 1h] [--htf 4h] [--headlines file] [--dd 0] [--out brief]
      -> brief.md: regime and score per instrument, event risk, allocation (1 or many ideas), tickets
  python3 desk.py ticket --symbol EURUSD --dir long --entry 1.0850 --stop 1.0820 --target 1.0925 --risk 1 --balance 1000 [--setup trend] [--journal journal.csv]
  python3 desk.py debate SYMBOL [--analysis X_analysis.json] [--sentiment sentiment.json]   -> debate sheet to fill and decide
  python3 desk.py playbook [trending|ranging|squeeze|event|all]
  python3 desk.py legends
  python3 desk.py research
  python3 desk.py models
  python3 desk.py review JOURNAL.csv --peak 1200 --equity 1100      -> weekly review: stats, tilt, throttle level, what to cut
No orders are sent. Every ticket is executed by the user on the platform.
Needs: Python 3, numpy, pandas (and the sibling tools ta.py, risk.py, pulse.py in the same folder).
"""
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PLAYBOOK = [
 ("trend following", "trending", "EMA50 > EMA200, ADX > 25, efficiency > 0.3; enter on close or pullback, 2.5 ATR stop, trail 3 ATR chandelier", "strong: time-series momentum is documented across futures and FX for a century; wins rarely (35 to 45%) but big", "long flat periods; give back at reversals"),
 ("pullback in trend", "trending", "trend up, price back to EMA20 within 1 ATR, RSI reset 35 to 55, bullish close; 1.8 ATR stop, 2.5R target", "moderate: better entries than raw trend, more trades, more whipsaw", "trend may be ending; skip near big levels against you"),
 ("volatility squeeze breakout", "squeeze", "volatility percentile under 20%, then close beyond 20-bar range with a strong bar; 2 ATR stop", "moderate: volatility clusters (expansion follows contraction); many false breaks", "fakeouts at news; prefer breakouts in the higher-timeframe trend direction"),
 ("mean reversion", "ranging", "ADX < 20, z-score beyond 2, RSI extreme; target the 20 MA; 1.5 ATR stop", "moderate in ranges, deadly in trends", "never fade a trending market; small size"),
 ("carry", "any (calm markets)", "long high-yield vs low-yield currency when volatility is low; exit on volatility spikes", "strong historically, but crash-prone (negative skew) and weaker out of sample", "sudden unwinds; swap costs on CFDs can erase it"),
 ("event straddle / fade", "event", "after FOMC/NFP/CPI wait 15 to 30 min; trade the confirmed direction or fade an overextended spike back into the range", "weak to moderate: spreads widen, slippage; discipline matters more than the model", "never enter during the release second"),
 ("sentiment contrarian filter", "any", "do not join a crowd above 70% one side (broker client sentiment) or COT extreme (90th percentile); prefer setups against the crowd", "moderate as a filter, weak as a trigger", "crowds can stay right in strong trends"),
 ("session open range", "trending days", "London or New York open: 30 to 60 min range, trade the break with the daily bias", "weak to moderate, highly instrument specific; must be backtested", "chop days; overtrading"),
]

LEGENDS = [
 ("Jim Simons, Renaissance Medallion", "quant, short-term statistical patterns, heavy leverage", "about 66% a year before fees, 39% after, 1988 onward; essentially no losing years", "edge from data, many small bets, strict risk; impossible to copy at retail"),
 ("George Soros", "global macro, reflexivity, big concentrated bets", "about 36% a year 1969 to 1989", "concentrate when the thesis is strong, but drawdowns over 30% happened"),
 ("Stanley Druckenmiller", "macro, liquidity and central banks, size up when right", "about 30% a year for 30 years with no losing year (reported)", "the size of the bet matters more than the hit rate; cut fast when wrong"),
 ("Paul Tudor Jones", "macro and technicals, 200-day MA rule", "about 20%+ in his best decades", "defence first: 'never average losers', risk reduction after losses"),
 ("Ed Seykota / Richard Dennis (Turtles)", "systematic trend following", "Turtles turned small stakes into millions in the 1980s; long flat periods", "rules plus position sizing by volatility (ATR) and pyramiding winners only"),
 ("Warren Buffett", "long-term value investing (not trading)", "about 20% a year over six decades", "time and compounding beat activity; 20% a year is already legendary"),
 ("Retail CFD traders (benchmark)", "everything above, without the edge", "about 70 to 84% of accounts lose money at Capital.com; 97% of Brazilian day traders who persisted 300+ days lost", "the default outcome; avoiding it is the first goal"),
]

RESEARCH = [
 ("Retail outcome", "Capital.com discloses that about 70 to 84% of retail CFD accounts lose money (varies by entity and period). In Brazil, 97% of individuals who day traded futures for over 300 days lost money; only about 1% earned more than minimum wage; no evidence of learning.", "Chague, De-Losso, Giovannetti, 'Day trading for a living?' (2019/2020); broker risk warnings"),
 ("LLMs trading live", "Public live contests in 2025 to 2026 (Alpha Arena and others) show most frontier models lose money, overtrade and decide differently on identical prompts; one run lost about a third overall with 6 of 32 results positive. A six-month population study of LLM agent fleets found no directional edge.", "Nof1 Alpha Arena reports (2026); 'What LLM Trading Agents Actually Do in Production' (arXiv 2609.05663); LiveTradeBench (arXiv 2511.03628); Agent Market Arena (arXiv 2510.11695)"),
 ("Multi-agent frameworks", "TradingAgents (UCLA/MIT) splits work into fundamentals, sentiment, news and technical analysts, bull vs bear researchers, a trader and a risk team; reported strong backtests, but critics point to look-ahead leakage because models were trained on the test window.", "Xiao et al., TradingAgents (arXiv 2412.20138, AAAI 2025 workshop)"),
 ("Price foundation models", "Kronos is an open decoder-only model trained on 12B+ candlestick records from 45 exchanges (mini 4.1M, small 24.7M, base 102M params on Hugging Face); good zero-shot forecasts of volatility and paths, not a trading system by itself. Chronos and TimesFM are general time-series models.", "Shi et al., Kronos (arXiv 2508.02739); NeoQuasar/Kronos-* on Hugging Face"),
 ("News sentiment models", "On ~965k US news articles, LLM sentiment predicted next-day stock returns with about 72 to 74% accuracy (OPT 74.4%, BERT 72.5%, FinBERT 72.2%); small fine-tuned models like FinBERT can match much larger zero-shot models on financial sentiment.", "Kirtac and Germano (arXiv 2412.19245); Araci, FinBERT (arXiv 1908.10063); ProsusAI/finbert"),
 ("What works in FX historically", "Carry, momentum and value are the three documented currency premia; cross-sectional currency momentum earned up to ~10% a year in long samples; carry has crash risk. Out of sample and after publication, these returns shrink markedly.", "Menkhoff, Sarno, Schmeling, Schrimpf (BIS WP 366 / JFE); Hsu, Taylor, Wang, 'Out-of-sample performance of carry trades' (CEPR DP15052)"),
 ("Data an agent can use", "Broker APIs: Capital.com (official MCP, demo default, client sentiment), Binance (official MCP, Agent OS), MT5 (community MCPs), Alpaca (official). Positioning: CFTC COT weekly. News: RSS, Alpha Vantage news sentiment. Social: X API pay-per-use (~0.005 USD per post read), Reddit API.", "vendor documentation, 2026"),
 ("The best ever", "Medallion: ~66% gross, ~39% net per year since 1988; Soros ~36% (1969 to 1989) with 30%+ drawdowns; Buffett ~20% a year for six decades.", "Zuckerman; Mallaby; Berkshire letters"),
]

MODELS = [
 ("NeoQuasar/Kronos-mini / small / base", "candlestick (OHLCV) forecasting, volatility, synthetic paths", "pip install from github.com/shiyu-coder/Kronos; feed the last 400 to 512 bars; use the forecast distribution as one input (expected range, volatility), never as an order"),
 ("amazon/chronos-bolt-*, google/timesfm-*", "general time-series forecasting", "zero-shot baseline; compare against a naive forecast before trusting"),
 ("ProsusAI/finbert, yiyanghkust/finbert-tone", "financial sentiment classification (English)", "run on headlines; add to pulse.py output as a second opinion"),
 ("FinGPT (AI4Finance)", "LLaMA-based financial instruction models and datasets", "research use; heavy; prefer the lexicon + your own reading for speed"),
 ("TauricResearch/TradingAgents", "multi-agent LLM trading framework (code)", "architecture reference for the debate step; beware look-ahead in its backtests"),
]

def q(fn, *args, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): r = fn(*args, **kw)
    return r, buf.getvalue()

def ticket(symbol, direction, entry, stop, target, risk, balance, setup="", journal_path=None, account="USD", leverage=30, quiet=False):
    import risk as R
    lots, _ = q(R.size, balance, risk, entry, stop, symbol, account, None, None, leverage)
    d = 1 if str(direction).lower() in ("1", "long", "buy") else -1; rr = abs(target - entry) / abs(entry - stop) if target else None
    t = [f"## Ticket {symbol} {'BUY' if d == 1 else 'SELL'} ({setup})", f"- Size: {lots:.3f} lots (risk {risk}% = {balance * risk / 100:.2f} {account})", f"- Entry: {entry} (market or limit)", f"- Stop loss: {stop}  (place it WITH the order)", f"- Take profit: {target}" + (f"  (R:R {rr:.2f})" if rr else ""),
         "- Before you click: no !!! event in 30 min? spread normal? total open risk within budget? plan written in journal?", "- After: do not move the stop further away. Move to breakeven only at +1R if the plan says so."]
    if (d == 1 and stop >= entry) or (d == -1 and stop <= entry): t.append("- ERROR: stop is on the wrong side of entry. Do not place this.")
    if not quiet: print("\n".join(t))
    if journal_path:
        new = not os.path.exists(journal_path)
        with open(journal_path, "a", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(["time", "symbol", "setup", "dir", "entry", "stop", "target", "risk_pct", "lots", "exit", "pnl", "notes"])
            w.writerow([dt.datetime.now().isoformat(timespec="minutes"), symbol, setup, "long" if d == 1 else "short", entry, stop, target, risk, round(lots, 3), "", "", "planned"])
        if not quiet: print(f"(planned trade added to {journal_path}; fill exit and pnl when closed)")
    return "\n".join(t)

def daily(prices_dir, balance, tf=None, htf=None, headlines=None, dd=0.0, out="brief"):
    import ta, risk as R, pulse as P
    os.makedirs(out, exist_ok=True); files = sorted(glob.glob(os.path.join(prices_dir, "*.csv"))); rows = []
    for f in files:
        try: r, _ = q(ta.analyze, f, tf, htf, None, out, True); rows.append(r)
        except SystemExit as e: pass
        except Exception as e: print(f"skip {f}: {e}")
    rows.sort(key=lambda r: -r["best_score"]); json.dump(rows, open(os.path.join(out, "scan.json"), "w"), default=str)
    _, cal = q(P.calendar, None, 3); sent_txt = ""
    if headlines: _, sent_txt = q(P.sentiment, headlines, os.path.join(out, "sentiment.json"))
    alloc, alloc_txt = q(R.allocate, os.path.join(out, "scan.json"), balance, prices_dir, 6.0, 2.5, dd, 30, os.path.join(out, "allocation.csv"))
    md = [f"# Daily brief {dt.date.today()} (balance {balance}, drawdown {dd}%)", "", "## Market map", "| symbol | regime | best setup | dir | score |", "|---|---|---|---|---|"]
    md += [f"| {r['symbol']} | {r['regime']['trend']}/{r['regime']['strength']}/{r['regime']['volatility']} | {r['best']} | {'LONG' if r['best_dir'] == 1 else 'SHORT' if r['best_dir'] == -1 else '-'} | {r['best_score']} |" for r in rows]
    md += ["", "## Event risk (next 3 days)", cal.strip()]
    if sent_txt: md += ["", "## News and social", sent_txt.strip()]
    md += ["", "## Allocation", alloc_txt.strip(), "", "## Tickets (you place them; nothing is sent)"]
    for a in alloc or []:
        r = next(x for x in rows if x["symbol"] == a["symbol"]); p = r["plan"]
        md.append(ticket(a["symbol"], a["dir"], p["entry"], p["stop"], p["target"], a["risk_pct"], balance, a["setup"], None, quiet=True))
    if not alloc: md.append("No ticket today. Flat is a position.")
    md += ["", "## Analyst duties before any click", "1. Read each chart png and the evidence lines; downgrade anything that looks wrong.", "2. Run the debate for the top idea (desk.py debate).", "3. Check spreads and the platform's own sentiment; confirm no fresh headline overrides the plan."]
    open(os.path.join(out, "brief.md"), "w").write("\n".join(md)); print("\n".join(md)); print(f"\n-> {out}/brief.md")

def debate(symbol, analysis=None, sent=None):
    a = json.load(open(analysis)) if analysis else {}; s = json.load(open(sent)) if sent else {}
    print(f"# Debate sheet: {symbol}")
    if a: print(f"Technical: {a.get('best')} score {a.get('best_score')} dir {a.get('best_dir')}; regime {a.get('regime')}; levels {a.get('levels')}")
    if s: print(f"Sentiment: risk tone {s.get('risk_tone')}; assets {json.dumps({k: v['bias'] for k, v in s.get('assets', {}).items()})}")
    for role, qs in (("BULL researcher", ["strongest 3 reasons price goes up in the trade horizon", "which level proves the bull case wrong"]),
                     ("BEAR researcher", ["strongest 3 reasons price goes down", "what news or data could hit in the horizon", "where trapped traders are"]),
                     ("RISK manager", ["event risk in next 24h", "correlation with open positions", "is size within budget and throttle level", "what is the worst realistic slippage"]),
                     ("TRADER decision", ["take / reduce / skip", "entry, stop, target, size", "what would make me exit early"])):
        print(f"## {role}"); [print(f"- {x}: ") for x in qs]
    print("Rule: if bull and bear are both convincing, skip. Trade only when one side is clearly stronger AND the risk manager signs off.")

def review(journal_path, peak, equity):
    import risk as R
    R.journal(journal_path); print(); R.throttle(peak, equity, 1.0)
    print("\nWeekly questions: Which setup earned the most R? Which should be paused (negative after 10+ trades)? Any rule broken (moved stop, no stop, revenge trade)? Keep a one-line lesson.")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d; f = lambda k, d=None: float(opt(k)) if opt(k) is not None else d; cmd = a[1] if len(a) > 1 else ""
    if cmd == "daily": daily(a[2], f("--balance", 1000), opt("--tf"), opt("--htf"), opt("--headlines"), f("--dd", 0), opt("--out", "brief"))
    elif cmd == "ticket": ticket(opt("--symbol"), opt("--dir"), f("--entry"), f("--stop"), f("--target"), f("--risk", 1), f("--balance", 1000), opt("--setup", ""), opt("--journal"), opt("--account", "USD"), f("--leverage", 30))
    elif cmd == "debate": debate(a[2], opt("--analysis"), opt("--sentiment"))
    elif cmd == "playbook":
        k = a[2] if len(a) > 2 else "all"
        for n, reg, rule, ev, risk_ in PLAYBOOK:
            if k == "all" or k in reg: print(f"## {n} ({reg})\n- rules: {rule}\n- evidence: {ev}\n- main risk: {risk_}")
    elif cmd == "legends": print("| trader | style | returns | lesson |\n|---|---|---|---|"); [print(f"| {x[0]} | {x[1]} | {x[2]} | {x[3]} |") for x in LEGENDS]
    elif cmd == "research": [print(f"## {t}\n{b}\nSource: {s}\n") for t, b, s in RESEARCH]
    elif cmd == "models": [print(f"- **{m}**: {w}. How: {h}") for m, w, h in MODELS]
    elif cmd == "review": review(a[2], f("--peak"), f("--equity"))
    else: print(USAGE)
