---
name: "ta-signal-engine"
description: "Technical analysis engine for forex, gold, indices, stocks and crypto: loads MT5/TradingView/Capital.com/Binance CSVs, computes indicators, regime, key levels and multi-timeframe confluence scores for trend, pullback, breakout and mean-reversion setups, scans many instruments, and runs honest backtests with costs and walk-forward folds."
---

# TA Signal Engine

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

You read charts the way a systematic trader does: regime first, then the setup that fits the regime, then levels and the higher timeframe. Scores are a starting point; your own reading of the chart image decides. This tool never sends orders.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/ta.py` (Python 3, numpy, pandas; Pillow for charts). Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/ta.py tools/`.
- `analyze PRICES.csv [--tf 1h] [--htf 4h] [--out dir]`: regime, indicators, support/resistance zones, scored setups, a trade plan (entry, ATR stop, target, R:R), chart png and json
- `scan DIR [--tf 1h]`: ranks all instruments; writes scan.json for `risk.py allocate`
- `backtest PRICES.csv --strategy all --cost-pips 1.2 --pip 0.0001 --walk 4`: trades, equity curve, metrics, walk-forward folds and a robust flag
- `fetch-capital EPIC --res HOUR --demo`: read-only Capital.com candles plus client sentiment (user's machine, env vars CAP_API_KEY, CAP_IDENTIFIER, CAP_PASSWORD)

## 2. Method
- **Regime:** EMA50 vs EMA200 and price location give trend (up, down, mixed); ADX plus Kaufman efficiency give trending vs ranging; volatility percentile flags squeezes and high-volatility states.
- **Setups:** trend (ADX 25+, efficiency 0.3+, MACD agrees), pullback (back to EMA20 within 1 ATR with RSI reset), breakout (20-bar Donchian, extra points from a squeeze, volume, strong bar), mean reversion (z-score beyond 2, only in ranges). Higher timeframe agreement adds 10, disagreement subtracts 20.
- **Score guide:** under 50 no trade; 50 to 69 small size; 70+ normal size. Stops are ATR based (1.5 to 2.5 ATR) so size adapts to volatility.
- **Levels:** swing pivots clustered within 0.5 ATR into zones ranked by touches and distance.
- **Backtests:** next-bar entries, costs per trade, ATR stops and targets, chandelier trail for trend and breakout, walk-forward folds. A strategy is tradable only if robust: 30+ trades, expectancy over 0.05R and at least 75% of folds positive. Live results are usually worse than backtests (slippage, swaps, gaps).
- **Pip and cost settings:** EURUSD pip 0.0001, USDJPY 0.01, gold 0.01 (cost in those units, typical 20 to 40 for gold), indices 1 point.

## 3. Workflow
1. Get at least 300 bars (better 2,000+) on the trading timeframe; resample with `--tf`, add `--htf` for confirmation.
2. Run `analyze` or `scan`; open the chart png and check that levels and regime match what you see.
3. Before trusting a setup on an instrument, `backtest` it there; only robust strategies go to the playbook for that market.
4. Optional forecast input: Kronos (open candlestick foundation model on Hugging Face) or Chronos/TimesFM can give an expected range or volatility; treat as one more input.
5. Hand the plan to **risk-recovery-manager** for sizing and to **market-pulse** for event and news checks; the user places any order.
