###############
# Qiyas Sadıqov CC
###############
import json, math, os, sys, glob
import numpy as np, pandas as pd

USAGE = """ta-signal-engine: technical analysis, regime detection, confluence signals, multi-timeframe view,
honest backtests (costs, walk-forward) and charts for forex, indices, commodities, stocks and crypto.

  python3 ta.py analyze PRICES.csv [--tf 1h] [--htf 4h] [--symbol EURUSD] [--out dir]
      -> indicators, regime, key levels, confluence score per strategy, chart.png, analysis.json
  python3 ta.py scan DIR_OR_FILES... [--tf 1h]          -> rank many instruments by signal score (best ideas first)
  python3 ta.py backtest PRICES.csv --strategy trend|breakout|meanrev|pullback|all [--cost-pips 1.2] [--pip 0.0001]
        [--risk 1] [--walk 4] [--out dir]               -> trades.csv, equity.png, metrics incl. walk-forward folds
  python3 ta.py fetch-capital EPIC --res HOUR|HOUR_4|DAY|MINUTE_15 [--max 1000] [--demo] -> EPIC_res.csv
        (read-only; needs CAP_API_KEY, CAP_IDENTIFIER, CAP_PASSWORD env vars; runs on the user's machine)
CSV: any export with time/date, open, high, low, close (volume optional): MT5, TradingView, Capital.com, Binance.
No orders are ever sent by this tool.
Needs: Python 3, numpy, pandas; Pillow for charts.
"""

def load(path):
    df = pd.read_csv(path, sep=None, engine="python")
    if str(df.columns[0]).replace(".", "", 1).isdigit(): df = pd.read_csv(path, sep=None, engine="python", header=None).iloc[:, :6].set_axis(["open_time", "open", "high", "low", "close", "volume"], axis=1)
    df.columns = [c.strip().lower().strip("<>").replace(" ", "_") for c in df.columns]
    if "date" in df.columns and "time" in df.columns and not str(df["date"].iloc[0]).count(":"):
        df["timestamp"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), errors="coerce")
    else:
        tcol = next((c for c in ("timestamp", "time", "datetime", "date", "open_time", "snapshottime") if c in df.columns), df.columns[0])
        s = df[tcol]; isnum = pd.api.types.is_numeric_dtype(s)
        df["timestamp"] = pd.to_datetime(s, unit=("us" if s.iloc[0] > 1e14 else "ms" if s.iloc[0] > 1e11 else "s"), errors="coerce") if isnum else pd.to_datetime(s.astype(str), errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
    ren = {"tickvol": "volume", "vol": "volume", "tick_volume": "volume"}
    df = df.rename(columns=ren); df = df.loc[:, ~df.columns.duplicated()]
    for c in ("open", "high", "low", "close"):
        if c not in df.columns: raise SystemExit(f"missing column {c} in {path}: {list(df.columns)}")
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if "volume" not in df.columns: df["volume"] = 0.0
    df = df.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")
    return df[["open", "high", "low", "close", "volume"]]

def resample(df, tf):
    rule = {"15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D", "1w": "1W"}[tf]
    return df.resample(rule).agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()

def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def rma(s, n): return s.ewm(alpha=1 / n, adjust=False).mean()
def atr(d, n=14):
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    return rma(tr, n)
def rsi(s, n=14):
    ch = s.diff(); up = rma(ch.clip(lower=0), n); dn = rma(-ch.clip(upper=0), n)
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))
def adx(d, n=14):
    upm = d.high.diff(); dnm = -d.low.diff()
    pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0); ndm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
    a = atr(d, n); pdi = 100 * rma(pd.Series(pdm, d.index), n) / a; ndi = 100 * rma(pd.Series(ndm, d.index), n) / a
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return rma(dx, n), pdi, ndi
def macd(s): m = ema(s, 12) - ema(s, 26); sig = ema(m, 9); return m, sig, m - sig
def boll(s, n=20, k=2): m = s.rolling(n).mean(); sd = s.rolling(n).std(); return m, m + k * sd, m - k * sd
def efficiency(s, n=20):
    return (s - s.shift(n)).abs() / s.diff().abs().rolling(n).sum()

def indicators(d):
    d = d.copy(); c = d.close
    d["ema20"], d["ema50"], d["ema200"] = ema(c, 20), ema(c, 50), ema(c, 200)
    d["atr"] = atr(d); d["rsi"] = rsi(c); d["adx"], d["pdi"], d["ndi"] = adx(d)
    d["macd"], d["macd_sig"], d["macd_hist"] = macd(c); d["bb_mid"], d["bb_up"], d["bb_lo"] = boll(c)
    d["don_hi"], d["don_lo"] = d.high.rolling(20).max().shift(), d.low.rolling(20).min().shift()
    d["er"] = efficiency(c); d["ret"] = c.pct_change()
    d["vol20"] = d.ret.rolling(20).std(); d["vol_pct"] = d.vol20.rolling(250, min_periods=50).rank(pct=True)
    d["z20"] = (c - d.bb_mid) / c.rolling(20).std()
    return d

def regime(r):
    trend = "up" if r.ema50 > r.ema200 and r.close > r.ema50 else "down" if r.ema50 < r.ema200 and r.close < r.ema50 else "mixed"
    strength = "trending" if (r.adx > 25 and r.er > 0.3) else "ranging" if r.adx < 18 else "transition"
    vol = "high vol" if r.vol_pct > 0.8 else "low vol (squeeze)" if r.vol_pct < 0.2 else "normal vol"
    return trend, strength, vol

def swing_levels(d, look=3, n=6):
    h, l = d.high.values, d.low.values; piv = []
    for i in range(look, len(d) - look):
        if h[i] == max(h[i - look:i + look + 1]): piv.append(h[i])
        if l[i] == min(l[i - look:i + look + 1]): piv.append(l[i])
    if not piv: return []
    a = float(d.atr.iloc[-1]) or 1e-9; piv.sort(); zones = []
    for p in piv:
        if zones and abs(p - zones[-1][0]) < 0.5 * a: z = zones[-1]; z[0] = (z[0] * z[1] + p) / (z[1] + 1); z[1] += 1
        else: zones.append([p, 1])
    price = d.close.iloc[-1]
    zones.sort(key=lambda z: (abs(z[0] - price) / a) - 0.4 * z[1])
    return [(round(z[0], 6), z[1], "resistance" if z[0] > price else "support") for z in zones[:n]]

def score(d, htf=None):
    r = d.iloc[-1]; p = d.iloc[-2]; out = {}
    tr, st, vo = regime(r)
    htf_dir = None
    if htf is not None and len(htf) > 210:
        hr = htf.iloc[-1]; htf_dir = 1 if hr.ema50 > hr.ema200 and hr.close > hr.ema50 else -1 if hr.ema50 < hr.ema200 and hr.close < hr.ema50 else 0
    def finish(name, direction, pts, why):
        if htf_dir is not None and direction != 0:
            if htf_dir == direction: pts += 10; why.append("higher timeframe agrees")
            elif htf_dir == -direction: pts -= 20; why.append("against higher timeframe")
        out[name] = {"dir": int(direction), "score": int(max(0, min(100, pts))) if direction else 0, "why": why}
    dirn = 1 if tr == "up" else -1 if tr == "down" else 0; pts = 30 if dirn else 0; why = [f"trend {tr}"]
    if dirn and st == "trending": pts += 25; why.append(f"ADX {r.adx:.0f}, efficiency {r.er:.2f}")
    if dirn and np.sign(r.macd_hist) == dirn: pts += 10; why.append("MACD momentum agrees")
    if dirn and ((dirn == 1 and r.rsi > 75) or (dirn == -1 and r.rsi < 25)): pts -= 15; why.append("stretched RSI: late entry")
    finish("trend", dirn, pts, why)
    dirn = 1 if tr == "up" else -1 if tr == "down" else 0; why = []; pts = 0
    if dirn:
        dist = (r.close - r.ema20) / r.atr * dirn
        if -1.0 < dist < 0.3: pts = 45; why.append(f"pulled back to EMA20 ({dist:+.1f} ATR)")
        if (dirn == 1 and 35 < r.rsi < 55) or (dirn == -1 and 45 < r.rsi < 65): pts += 15; why.append(f"RSI reset {r.rsi:.0f}")
        if (r.close - r.open) * dirn > 0: pts += 10; why.append("bar closed in trend direction")
        if st == "trending": pts += 10
    finish("pullback", dirn if pts else 0, pts, why or ["no pullback setup"])
    dirn = 1 if r.close > r.don_hi else -1 if r.close < r.don_lo else 0; why = []; pts = 0
    if dirn:
        pts = 40; why.append("20-bar Donchian breakout")
        if p.vol_pct < 0.35: pts += 20; why.append("from a volatility squeeze")
        if d.volume.iloc[-1] > 1.5 * d.volume.iloc[-21:-1].mean() > 0: pts += 10; why.append("volume expansion")
        if abs(r.close - r.open) > 0.8 * r.atr: pts += 10; why.append("strong breakout bar")
    finish("breakout", dirn, pts, why or ["no breakout"])
    dirn = -1 if r.z20 > 2 else 1 if r.z20 < -2 else 0; why = []; pts = 0
    if dirn:
        pts = 35; why.append(f"z-score {r.z20:+.1f}")
        if st == "ranging": pts += 25; why.append("ranging regime")
        else: pts -= 20; why.append("trending: fading is dangerous")
        if (dirn == 1 and r.rsi < 30) or (dirn == -1 and r.rsi > 70): pts += 10; why.append(f"RSI {r.rsi:.0f}")
    finish("meanrev", dirn, pts, why or ["no extreme"])
    return out, (tr, st, vo), htf_dir

def plan(d, name, direction, k_stop=None, rr=None):
    r = d.iloc[-1]; a = float(r.atr)
    k_stop = k_stop or {"trend": 2.5, "pullback": 1.8, "breakout": 2.0, "meanrev": 1.5}[name]
    rr = rr or {"trend": 3.0, "pullback": 2.5, "breakout": 2.5, "meanrev": 1.5}[name]
    entry = float(r.close); stop = entry - direction * k_stop * a; tgt = entry + direction * k_stop * a * rr
    if name == "meanrev": tgt = float(r.bb_mid)
    return {"entry": round(entry, 6), "stop": round(stop, 6), "target": round(tgt, 6), "stop_atr": k_stop, "rr": round(abs(tgt - entry) / abs(entry - stop), 2), "atr": round(a, 6)}

def chart(d, path, levels=(), title=""):
    try: from PIL import Image, ImageDraw
    except ImportError: return
    d = d.iloc[-150:]; W, H, pad = 1200, 620, 60; im = Image.new("RGB", (W, H), (14, 14, 18)); g = ImageDraw.Draw(im)
    lo, hi = d.low.min(), d.high.max(); lo -= (hi - lo) * 0.05; hi += (hi - lo) * 0.05
    y = lambda v: pad + (H - 2 * pad) * (1 - (v - lo) / (hi - lo)); n = len(d); bw = (W - 2 * pad) / n
    for lv, t, kind in levels: g.line([(pad, y(lv)), (W - pad, y(lv))], fill=(120, 60, 60) if kind == "resistance" else (50, 110, 70), width=1 + min(t, 3)); g.text((W - pad + 4, y(lv) - 6), f"{lv:.5g}", fill=(180, 180, 180))
    for i, (_, r) in enumerate(d.iterrows()):
        x = pad + i * bw + bw / 2; col = (70, 190, 120) if r.close >= r.open else (220, 80, 80)
        g.line([(x, y(r.high)), (x, y(r.low))], fill=col); g.rectangle([x - bw * 0.35, min(y(r.open), y(r.close)), x + bw * 0.35, max(y(r.open), y(r.close)) + 1], fill=col)
    for col, c in (("ema20", (240, 200, 80)), ("ema50", (90, 160, 255)), ("ema200", (200, 120, 255))):
        pts = [(pad + i * bw + bw / 2, y(v)) for i, v in enumerate(d[col]) if not np.isnan(v)]
        if len(pts) > 1: g.line(pts, fill=c, width=2)
    g.text((pad, 20), title + "   EMA20 yellow, EMA50 blue, EMA200 purple", fill=(230, 230, 230)); im.save(path)

def analyze(path, tf=None, htf=None, symbol=None, out=None, quiet=False):
    raw = load(path); d = indicators(resample(raw, tf) if tf else raw)
    H = indicators(resample(raw, htf)) if htf else None
    if len(d) < 220: raise SystemExit(f"need at least 220 bars, have {len(d)}")
    sig, (tr, st, vo), hd = score(d, H); lv = swing_levels(d.iloc[-400:]); r = d.iloc[-1]
    best = max(sig.items(), key=lambda kv: kv[1]["score"]); sym = symbol or os.path.splitext(os.path.basename(path))[0]
    res = {"symbol": sym, "time": str(d.index[-1]), "close": float(r.close), "regime": {"trend": tr, "strength": st, "volatility": vo, "htf_trend": hd},
           "indicators": {k: round(float(r[k]), 5) for k in ("ema20", "ema50", "ema200", "atr", "rsi", "adx", "macd_hist", "er", "z20", "vol_pct")},
           "levels": lv, "signals": sig, "best": best[0], "best_score": best[1]["score"], "best_dir": best[1]["dir"]}
    if best[1]["dir"]: res["plan"] = plan(d, best[0], best[1]["dir"])
    if not quiet:
        print(f"# {sym} {res['time']} close {r.close:.6g}")
        print(f"Regime: {tr}, {st}, {vo}" + (f"; higher timeframe {'up' if hd == 1 else 'down' if hd == -1 else 'mixed'}" if hd is not None else ""))
        print(f"RSI {r.rsi:.0f}, ADX {r.adx:.0f}, ATR {r.atr:.5g}, efficiency {r.er:.2f}, z {r.z20:+.1f}")
        print("Levels: " + "; ".join(f"{k} {v} ({t}x)" for v, t, k in lv))
        for k, v in sorted(sig.items(), key=lambda kv: -kv[1]["score"]): print(f"- {k}: {'LONG' if v['dir'] == 1 else 'SHORT' if v['dir'] == -1 else 'flat'} score {v['score']}: " + "; ".join(v["why"]))
        if "plan" in res: p = res["plan"]; print(f"Plan ({best[0]}): entry {p['entry']}, stop {p['stop']} ({p['stop_atr']} ATR), target {p['target']}, R:R {p['rr']}")
        print("Score guide: under 50 no trade, 50 to 69 small size, 70+ normal size. Confirm with market-pulse (news/events) before any order.")
    if out:
        os.makedirs(out, exist_ok=True); json.dump(res, open(os.path.join(out, f"{sym}_analysis.json"), "w"), indent=1, default=str)
        chart(d, os.path.join(out, f"{sym}_chart.png"), lv, f"{sym} {tf or ''} {tr}/{st}")
    return res

def scan(paths, tf=None):
    files = [f for p in paths for f in (glob.glob(os.path.join(p, "*.csv")) if os.path.isdir(p) else [p])]; rows = []
    for f in files:
        try: r = analyze(f, tf, quiet=True); rows.append(r)
        except SystemExit as e: print(f"- {f}: {e}")
    rows.sort(key=lambda r: -r["best_score"])
    print("| symbol | regime | best setup | dir | score | R:R |\n|---|---|---|---|---|---|")
    for r in rows: print(f"| {r['symbol']} | {r['regime']['trend']}/{r['regime']['strength']} | {r['best']} | {'LONG' if r['best_dir'] == 1 else 'SHORT' if r['best_dir'] == -1 else '-'} | {r['best_score']} | {r.get('plan', {}).get('rr', '')} |")
    json.dump(rows, open("scan.json", "w"), indent=1, default=str); print("-> scan.json (feed to risk.py allocate)")
    return rows

def signals_series(d, strat):
    c = d.close; trend = np.where((d.ema50 > d.ema200) & (c > d.ema50), 1, np.where((d.ema50 < d.ema200) & (c < d.ema50), -1, 0))
    if strat == "trend": e = pd.Series(trend, d.index) * ((d.adx > 25) & (d.er > 0.3))
    elif strat == "breakout": e = pd.Series(np.where(c > d.don_hi, 1, np.where(c < d.don_lo, -1, 0)), d.index)
    elif strat == "meanrev": e = pd.Series(np.where((d.z20 < -2) & (d.adx < 20), 1, np.where((d.z20 > 2) & (d.adx < 20), -1, 0)), d.index)
    elif strat == "pullback":
        dist = (c - d.ema20) / d.atr
        e = pd.Series(np.where((trend == 1) & (dist.between(-1, 0.3)) & (d.rsi.between(35, 55)), 1, np.where((trend == -1) & (dist.between(-0.3, 1)) & (d.rsi.between(45, 65)), -1, 0)), d.index)
    return e.astype(int)

def backtest(d, strat, cost, risk_pct=1.0, start_eq=10000.0):
    ent = signals_series(d, strat); k = {"trend": 2.5, "pullback": 1.8, "breakout": 2.0, "meanrev": 1.5}[strat]; rr = {"trend": 3.0, "pullback": 2.5, "breakout": 2.5, "meanrev": 1.5}[strat]
    o, h, l, c, a = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values; idx = d.index
    eq = start_eq; curve = []; trades = []; pos = None
    for i in range(210, len(d) - 1):
        if pos:
            dirn, en, st, tg, t0, size, _st0 = pos; exitp = None
            if dirn == 1:
                if l[i] <= st: exitp = min(o[i], st)
                elif h[i] >= tg: exitp = max(o[i], tg) if o[i] > tg else tg
            else:
                if h[i] >= st: exitp = max(o[i], st)
                elif l[i] <= tg: exitp = min(o[i], tg) if o[i] < tg else tg
            if exitp is None and strat == "meanrev" and ((dirn == 1 and c[i] >= d.bb_mid.values[i]) or (dirn == -1 and c[i] <= d.bb_mid.values[i])): exitp = c[i]
            if exitp is None and strat in ("trend", "breakout") and i - t0 > 5:
                trail = (max(h[t0:i + 1]) - 3 * a[i]) if dirn == 1 else (min(l[t0:i + 1]) + 3 * a[i])
                pos[2] = st = max(st, trail) if dirn == 1 else min(st, trail)
            if exitp is not None:
                pnl_r = ((exitp - en) * dirn - cost / 2) / abs(en - pos[6]); eq += size * pnl_r
                trades.append({"entry_time": idx[t0], "exit_time": idx[i], "dir": dirn, "entry": en, "exit": exitp, "R": round(pnl_r, 3), "equity": round(eq, 2)}); pos = None
        if pos is None and ent.iloc[i] != 0 and not np.isnan(a[i]):
            dirn = int(ent.iloc[i]); en = o[i + 1] + dirn * cost / 2; st = en - dirn * k * a[i]; tg = en + dirn * k * a[i] * rr
            pos = [dirn, en, st, tg, i + 1, eq * risk_pct / 100, st]
        curve.append((idx[i], eq))
    return pd.DataFrame(trades), pd.Series(dict(curve))

def metrics(tr, curve, bars_per_year):
    if tr.empty: return {"trades": 0}
    R = tr.R; ret = curve.pct_change().dropna(); dd = curve / curve.cummax() - 1
    years = len(curve) / bars_per_year; cagr = (curve.iloc[-1] / curve.iloc[0]) ** (1 / max(years, 1e-9)) - 1
    wins = R[R > 0]; losses = R[R <= 0]
    streak = max((len(list(g)) for k, g in __import__("itertools").groupby(R <= 0) if k), default=0)
    return {"trades": int(len(R)), "win_rate": round(float((R > 0).mean()) * 100, 1), "avg_win_R": round(float(wins.mean()), 2) if len(wins) else 0, "avg_loss_R": round(float(losses.mean()), 2) if len(losses) else 0,
            "expectancy_R": round(float(R.mean()), 3), "profit_factor": round(float(wins.sum() / -losses.sum()), 2) if losses.sum() < 0 else None,
            "total_return_pct": round((curve.iloc[-1] / curve.iloc[0] - 1) * 100, 1), "cagr_pct": round(cagr * 100, 1), "max_dd_pct": round(float(dd.min()) * 100, 1),
            "sharpe": round(float(ret.mean() / ret.std() * math.sqrt(bars_per_year)), 2) if ret.std() > 0 else None, "max_losing_streak": int(streak)}

def run_backtest(path, strat, cost_pips, pip, risk, walk, out):
    d = indicators(load(path)); cost = cost_pips * pip
    if len(d) < 220: raise SystemExit(f"need at least 220 bars, have {len(d)}")
    step = (d.index[-1] - d.index[0]) / max(1, len(d) - 1); bpy = pd.Timedelta(days=365) / step if step.total_seconds() > 0 else 252
    strats = ["trend", "pullback", "breakout", "meanrev"] if strat == "all" else [strat]; os.makedirs(out, exist_ok=True); summary = {}
    for s in strats:
        tr, curve = backtest(d, s, cost, risk); m = metrics(tr, curve, bpy); summary[s] = m
        folds = []
        if walk and len(d) > 600:
            n = len(d) // walk
            for f in range(walk):
                part = d.iloc[max(0, f * n - 210):(f + 1) * n]; t2, c2 = backtest(part, s, cost, risk); mm = metrics(t2, c2, bpy)
                folds.append({"fold": f + 1, "from": str(part.index[min(210, len(part) - 1)].date()), "trades": mm.get("trades", 0), "expectancy_R": mm.get("expectancy_R"), "return_pct": mm.get("total_return_pct")})
        m["walk_forward"] = folds; pos_f = sum(1 for f in folds if (f["expectancy_R"] or 0) > 0)
        m["robust"] = bool(folds) and pos_f >= math.ceil(0.75 * len(folds)) and (m.get("expectancy_R") or 0) > 0.05 and m.get("trades", 0) >= 30
        print(f"## {s}: " + ", ".join(f"{k} {v}" for k, v in m.items() if k != "walk_forward"))
        for f in folds: print(f"   fold {f['fold']} from {f['from']}: {f['trades']} trades, expectancy {f['expectancy_R']}R, return {f['return_pct']}%")
        if not tr.empty: tr.to_csv(os.path.join(out, f"trades_{s}.csv"), index=False)
        try:
            from PIL import Image, ImageDraw
            W, H = 1000, 360; im = Image.new("RGB", (W, H), (14, 14, 18)); g = ImageDraw.Draw(im); v = curve.values; lo, hi = v.min(), v.max() + 1e-9
            g.line([(40 + i * (W - 80) / len(v), H - 30 - (H - 60) * (x - lo) / (hi - lo)) for i, x in enumerate(v)], fill=(90, 200, 140), width=2)
            g.text((40, 8), f"{s}: return {m.get('total_return_pct')}%, max DD {m.get('max_dd_pct')}%, {m.get('trades')} trades", fill=(230, 230, 230)); im.save(os.path.join(out, f"equity_{s}.png"))
        except ImportError: pass
    json.dump(summary, open(os.path.join(out, "backtest.json"), "w"), indent=1, default=str)
    print("Robust = 30+ trades, expectancy over 0.05R and at least 75% of walk-forward folds positive. Anything else is not tradable yet.")
    print("Backtests include spread/commission as cost_pips but not swaps, slippage spikes or news gaps: expect live results to be worse.")
    return summary

def fetch_capital(epic, res="HOUR", mx=1000, demo=False):
    import urllib.request
    base = "https://demo-api-capital.backend-capital.com" if demo else "https://api-capital.backend-capital.com"
    key, ident, pw = os.environ.get("CAP_API_KEY"), os.environ.get("CAP_IDENTIFIER"), os.environ.get("CAP_PASSWORD")
    if not (key and ident and pw): raise SystemExit("set CAP_API_KEY, CAP_IDENTIFIER, CAP_PASSWORD (API key password) in the environment")
    req = urllib.request.Request(base + "/api/v1/session", data=json.dumps({"identifier": ident, "password": pw}).encode(), headers={"X-CAP-API-KEY": key, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r: cst, sec = r.headers["CST"], r.headers["X-SECURITY-TOKEN"]
    h = {"X-SECURITY-TOKEN": sec, "CST": cst}
    with urllib.request.urlopen(urllib.request.Request(f"{base}/api/v1/prices/{epic}?resolution={res}&max={min(mx, 1000)}", headers=h)) as r: data = json.load(r)
    rows = [{"timestamp": p["snapshotTimeUTC"], "open": (p["openPrice"]["bid"] + p["openPrice"]["ask"]) / 2, "high": (p["highPrice"]["bid"] + p["highPrice"]["ask"]) / 2,
             "low": (p["lowPrice"]["bid"] + p["lowPrice"]["ask"]) / 2, "close": (p["closePrice"]["bid"] + p["closePrice"]["ask"]) / 2, "volume": p.get("lastTradedVolume", 0)} for p in data["prices"]]
    fn = f"{epic}_{res}.csv"; pd.DataFrame(rows).to_csv(fn, index=False); print(f"-> {fn} ({len(rows)} bars, mid prices)")
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{base}/api/v1/clientsentiment/{epic}", headers=h)) as r: s = json.load(r)
        json.dump(s, open(f"{epic}_sentiment.json", "w")); print(f"-> {epic}_sentiment.json (client long/short %, use with pulse.py positioning)")
    except Exception as e: print(f"sentiment not fetched: {e}")

if __name__ == "__main__":
    a = sys.argv; opt = lambda k, dflt=None: a[a.index(k) + 1] if k in a else dflt
    if len(a) > 2 and a[1] == "analyze": analyze(a[2], opt("--tf"), opt("--htf"), opt("--symbol"), opt("--out"))
    elif len(a) > 2 and a[1] == "scan": scan([x for x in a[2:] if not x.startswith("--") and x != opt("--tf")], opt("--tf"))
    elif len(a) > 2 and a[1] == "backtest": run_backtest(a[2], opt("--strategy", "all"), float(opt("--cost-pips", 1.2)), float(opt("--pip", 0.0001)), float(opt("--risk", 1)), int(opt("--walk", 4)), opt("--out", "bt"))
    elif len(a) > 2 and a[1] == "fetch-capital": fetch_capital(a[2], opt("--res", "HOUR"), int(opt("--max", 1000)), "--demo" in a)
    else: print(USAGE)
