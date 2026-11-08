from __future__ import annotations
import argparse, pathlib, sys

from .config import load_config
from .data import get_history, get_info, get_price, get_next_earnings
from .technicals import analyze_technicals
from .valuation import estimate_intrinsic
from .research import fundamentals_snapshot, earnings_flag
from .screener import composite, signal_for, position_size, bear_case, stress_loss
from .forecast import monte_carlo, scenario_table
from .portfolio import load_fidelity_csv, drift_report, contribution_status, suggest_rebalance, sector_concentration, recovery_pct
from .report import ticker_section, full_report, plan_lines, track_record_lines
from .journal import log_signal, load_journal, record_action, evaluate, process_adherence

JOURNAL = "data/decisions.csv"

def analyze_one(ticker: str, cfg: dict, price_override: float | None = None) -> dict:
    info = get_info(ticker)
    hist = get_history(ticker)
    tech = analyze_technicals(hist)
    if price_override:
        tech["price"] = price_override
    price = price_override or tech["price"]
    val = estimate_intrinsic(info, price, cfg["valuation"]["dcf"])
    fund = fundamentals_snapshot(info)
    scored = composite(val, fund, tech, info, cfg["scoring"]["weights"])
    signal, reasons = signal_for(scored["total"], cfg["scoring"], val, tech)
    return {"ticker": ticker, "tech": tech, "valuation": val, "fund": fund, "scored": scored, "signal": signal, "reasons": reasons, "info": info}

def sized(r: dict, cfg: dict) -> float:
    return position_size(r["scored"]["total"], 50000, cfg["account"].get("cash_balance", 0) or 5000, cfg["risk"]["max_single_position"], volatility=r["tech"].get("annualized_volatility"), target_volatility=cfg["risk"].get("target_volatility", 0.20))

def section_for(r: dict, cfg: dict, with_earnings: bool = True) -> str:
    size = sized(r, cfg)
    ef = None
    if with_earnings:
        try:
            ef = earnings_flag(get_next_earnings(r["ticker"]), window_days=cfg["risk"].get("earnings_window_days", 14))
        except Exception:
            ef = None
    return ticker_section(r["ticker"], r["tech"], r["valuation"], r["fund"], r["scored"], r["signal"], r["reasons"], size, bear=bear_case(r["valuation"], r["fund"], r["tech"], r["scored"]), earnings=ef, stress=stress_loss(size, r["tech"]))

def main(argv=None):
    p = argparse.ArgumentParser(prog="roth-bot", description="Fidelity Roth IRA research bot (no trade execution)")
    p.add_argument("--config", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("ticker"); a.add_argument("--price", type=float, default=None)
    sub.add_parser("screen")
    po = sub.add_parser("portfolio"); po.add_argument("--csv", required=True)
    f = sub.add_parser("forecast"); f.add_argument("--balance", type=float, default=0); f.add_argument("--annual-contribution", type=float, default=7500); f.add_argument("--years", type=int, default=27); f.add_argument("--expected-return", type=float, default=0.08); f.add_argument("--volatility", type=float, default=0.16)
    sub.add_parser("report")
    j = sub.add_parser("journal"); j.add_argument("--ticker", required=True); j.add_argument("--action", required=True, choices=["bought", "sold", "held", "ignored"]); j.add_argument("--reason", default="")
    args = p.parse_args(argv)
    cfg = load_config(args.config)

    if args.cmd == "analyze":
        r = analyze_one(args.ticker.upper(), cfg, args.price)
        print(section_for(r, cfg))
    elif args.cmd == "screen":
        for t in cfg["watchlist"]:
            try:
                r = analyze_one(t, cfg)
                print(f"{t:6} {r['signal']:4} score {r['scored']['total']:5}  price ${r['tech']['price']:,.2f}  RSI {r['tech']['rsi14']:.0f}  parts {r['scored']['parts']}")
            except Exception as e:
                print(f"{t:6} ERROR {e}", file=sys.stderr)
    elif args.cmd == "portfolio":
        df = load_fidelity_csv(args.csv)
        total = float(df["market_value"].sum()) if not df.empty else 0
        print(f"Positions: {len(df)}  Market value: ${total:,.2f}")
        print(df.to_string(index=False) if not df.empty else "(empty)")
        drift = drift_report(df, cfg["target_allocation"], cfg["account"].get("cash_balance", 0), cfg["risk"]["rebalance_band_points"])
        for row in drift: print(row)
        for ticket in suggest_rebalance(drift, total): print("TICKET:", ticket)
        sectors = {}
        for sym in (df["symbol"].tolist() if not df.empty else []):
            try:
                sectors[sym] = get_info(sym).get("sector") or "Unknown"
            except Exception:
                sectors[sym] = "Unknown"
        for row in sector_concentration(df, sectors, cfg["risk"].get("sector_concentration_pct", 40.0)):
            flag = " FLAG: correlated holdings multiply the same risk" if row["flag"] else ""
            print(f"SECTOR {row['sector']}: {row['pct']}% (${row['value']:,.0f}){flag}")
        print(contribution_status(cfg["account"]["contribution_limit_2026"], cfg["account"].get("contributed_ytd", 0)))
    elif args.cmd == "forecast":
        mc = monte_carlo(args.balance, args.annual_contribution, args.years, args.expected_return, args.volatility, cfg["forecast"].get("simulations", 5000))
        print(mc)
        for row in scenario_table(args.balance, args.annual_contribution, args.years): print(row)
    elif args.cmd == "journal":
        ok = record_action(JOURNAL, args.ticker, args.action, args.reason)
        print(f"Recorded {args.action} for {args.ticker.upper()}." if ok else f"No unacted journal row found for {args.ticker.upper()}. Run a report first to log signals.")
    elif args.cmd == "report":
        sections, prices = [], {}
        for t in cfg["watchlist"]:
            try:
                r = analyze_one(t, cfg)
                prices[t] = r["tech"]["price"]
                sections.append(section_for(r, cfg))
                log_signal(JOURNAL, t, r["signal"], r["scored"]["total"], r["tech"]["price"], sized(r, cfg))
            except Exception as e:
                sections.append(f"## {t} — ERROR\n{e}")
        rows = load_journal(JOURNAL)
        track = track_record_lines(evaluate(rows, prices), process_adherence(rows))
        fc = monte_carlo(0, cfg["account"]["contribution_limit_2026"], cfg["forecast"]["years"], cfg["forecast"]["expected_return"], cfg["forecast"]["volatility"], 2000)
        text = full_report(sections, forecast=fc, plan=plan_lines(cfg), track=track)
        out = pathlib.Path("reports"); out.mkdir(exist_ok=True)
        fp = out / "latest_briefing.md"; fp.write_text(text)
        print(text); print(f"\nSaved to {fp}. Signals logged to {JOURNAL}.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
