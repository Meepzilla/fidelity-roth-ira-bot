# Fidelity Roth IRA Research Bot

Decision-support bot for a Fidelity Roth IRA. It does research, valuation estimates, technical analysis, portfolio drift checks, and retirement projections, then produces a scored BUY / HOLD / TRIM / SELL report with reasons.

It does **not** place trades. Fidelity has no retail trading API for Roth IRAs. Every output is a trade ticket for you to review and execute manually in Fidelity. That human gate is intentional.

> Not financial advice. This is an educational research tool. Past performance, model estimates, and scores do not predict returns. Verify any ticker, price, and tax rule before acting. Consider a fee-only fiduciary for personalized advice.

## What it does

| Module | Output |
|---|---|
| `valuation.py` | DCF intrinsic value, Dividend Discount Model, Graham Number, multiples vs history, margin of safety |
| `technicals.py` | SMA 50/200, EMA, RSI(14), MACD, Bollinger Bands, 52-week range position |
| `forecast.py` | Monte Carlo projection (GBM), CAGR scenarios, Roth IRA contribution + growth projection |
| `portfolio.py` | Load Fidelity Positions CSV export, allocation drift, contribution tracker, rebalance tickets |
| `screener.py` | Composite score 0-100: Value 25, Quality 25, Momentum 20, Risk 15, Income 15 -> signal + position size suggestion |
| `research.py` | Company snapshot from yfinance: margins, ROE, debt, earnings dates, analyst targets |
| `report.py` | Markdown briefing you can read in 2 minutes |

## Quick start

```bash
git clone <this-repo>
cd fidelity-roth-ira-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp config.example.yaml config.yaml   # edit watchlist, targets, contributions
cp .env.example .env                 # optional API keys, none required for v1

# Analyze one ticker
python -m roth_bot.cli analyze VTI
python -m roth_bot.cli analyze AAPL --price 227.50

# Screen your whole watchlist
python -m roth_bot.cli screen

# Portfolio: export Positions from Fidelity (Accounts > Positions > Download)
python -m roth_bot.cli portfolio --csv data/fidelity_positions.csv

# Retirement projection
python -m roth_bot.cli forecast --balance 45000 --annual-contribution 7500 --years 27 --expected-return 0.08 --volatility 0.16

# Full briefing to reports/
python -m roth_bot.cli report
```

## Fidelity workflow

1. In Fidelity: Accounts & Trade > Portfolio > Positions > gear icon > Download Positions (CSV).
2. Save as `data/fidelity_positions.csv` (gitignored, never committed).
3. Run `portfolio` or `report`. The bot parses Symbol, Quantity, Last Price, Market Value, Cost Basis.
4. Review tickets. Execute manually in Fidelity if you agree. Log the fill in `data/trades.csv`.

## Roth IRA rules baked in

- 2026 contribution limit in config: $7,500 (under 50). Update yearly in `config.yaml`.
- No tax drag modeling inside the Roth (dividends/gains are not taxed on qualified withdrawal). The bot does not optimize for taxable placement.
- Contribution tracker warns at 90% and blocks scoring a buy that would exceed cash + pending contributions in your config.
- Wash sale and day-trading logic are not needed inside a Roth in the same way as taxable, but frequent trading still carries settlement and Fidelity restrictions. The bot flags holding period < 30 days on a TRIM/SELL.

## Config

See `config.example.yaml`. Key fields:

- `watchlist`: tickers to screen
- `target_allocation`: e.g. VTI 0.60, VXUS 0.25, BND 0.10, cash 0.05
- `risk`: max single position (default 0.20), max drawdown tolerance, rebalance band (default 5 points)
- `scoring`: weights and thresholds for BUY >= 70, HOLD 45-69, TRIM/SELL < 45 (with overrides)

## Data sources

v1 uses `yfinance` (free, no key, can be delayed / rate-limited). Interfaces are isolated in `data.py` so you can swap in Polygon, Tiingo, or FMP by implementing `get_history()` and `get_info()`.

## Tests

```bash
pytest -q
```

Tests use synthetic price series, no network required.

## Structure

```
src/roth_bot/
  cli.py        # entry point
  config.py     # YAML loader + defaults
  data.py       # market data adapter
  valuation.py  # DCF, DDM, multiples
  technicals.py # indicators
  forecast.py   # Monte Carlo + projections
  portfolio.py  # Fidelity CSV + drift + contributions
  screener.py   # composite scoring + signals
  research.py   # fundamentals snapshot
  report.py     # markdown briefing
examples/
  sample_positions.csv
  sample_watchlist_report.md
```

## v0.2: what came from Trading-ZettleKasten

This version applies an influence pass from the public vault [NaitikJoshiPro/Trading-ZettleKasten](https://github.com/NaitikJoshiPro/Trading-ZettleKasten), an Obsidian trading knowledge base. A full review with per-item verdicts sits in the project notes. The vault is written for leveraged intraday trading, so most of it was deliberately skipped. What transferred:

Adopted:
- Decision journal (`journal.py`, `data/decisions.csv`). Every report run logs date, ticker, signal, score, price, and suggested size. Record what you did with `python -m roth_bot.cli journal --ticker VTI --action bought --reason "drift was low"`. Actions are bought, sold, held, ignored.
- Track record section in the briefing. Past calls are scored against current prices by signal bucket, with hit rate and average forward return, plus process adherence reported separately from outcomes.
- Bear case line on every ticker, built from the weakest sub-score, valuation gap, and extremes. It answers the vault prompt: what would change this signal.
- Sector concentration check in the portfolio output. Correlated holdings multiply the same risk.
- Volatility-scaled position sizing. Higher volatility, smaller suggested add.
- Earnings flag within 14 days on single-stock tickets. The score does not price gap risk.
- RSI context guard. An overbought RSI inside a confirmed uptrend no longer takes the full momentum penalty, because RSI can stay extreme in strong trends.
- Plan restatement at the top of every briefing, and a stress loss estimate on each suggested add.
- EV/EBITDA added to the multiples snapshot.

Skipped on purpose: stop-loss and take-profit ladders, per-trade pip sizing, Kelly sizing, macro event risk halving, ICT and order-flow concepts, and sentiment as a score input. Each is day-trading machinery, unavailable inside a Roth IRA, or contradicted by long-horizon design.

## Roadmap

- [ ] SEC EDGAR earnings call / 10-K parser
- [ ] News sentiment (RSS + scoring)
- [ ] Backtester for the composite score
- [ ] Weekly scheduled briefing via GitHub Actions (artifact only, no trading)
- [ ] Optional read-only Plaid holdings sync

## License

MIT. See LICENSE.
