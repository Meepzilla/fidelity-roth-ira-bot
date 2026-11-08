from __future__ import annotations
import argparse, pathlib, sys

from .config import load_config
from .data import get_history, get_info, get_price
from .technicals import analyze_technicals
from .valuation import estimate_intrinsic
from .research import fundamentals_snapshot
from .screener import composite, signal_for, position_size
from .forecast import monte_carlo, scenario_table
from .portfolio import load_fidelity_csv, drift_report, contribution_status, suggest_rebalance
from .report import ticker_section, full_report

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

def main(argv=None):
    p = argparse.ArgumentParser(prog="roth-bot", description="Fidelity Roth IRA research bot (no trade execution)")
    p.add_argument("--config", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("ticker"); a.add_argument("--price", type=float, default=None)
    sub.add_parser("screen")
    po = sub.add_parser("portfolio"); po.add_argument("--csv", required=True)
    f = sub.add_parser("forecast"); f.add_argument("--balance", type=float, default=0); f.add_argument("--annual-contribution", type=float, default=7500); f.add_argument("--years", type=int, default=27); f.add_argument("--expected-return", type=float, default=0.08); f.add_argument("--volatility", type=float, default=0.16)
    sub.add_parser("report")
    args = p.parse_args(argv)
    cfg = load_config(args.config)

    if args.cmd == "analyze":
        r = analyze_one(args.ticker.upper(), cfg, args.price)
        size = position_size(r["scored"]["total"], 50000, cfg["account"].get("cash_balance", 0) or 5000, cfg["risk"]["max_single_position"])
        print(ticker_section(r["ticker"], r["tech"], r["valuation"], r["fund"], r["scored"], r["signal"], r["reasons"], size))
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
        print(contribution_status(cfg["account"]["contribution_limit_2026"], cfg["account"].get("contributed_ytd", 0)))
    elif args.cmd == "forecast":
        mc = monte_carlo(args.balance, args.annual_contribution, args.years, args.expected_return, args.volatility, cfg["forecast"].get("simulations", 5000))
        print(mc)
        for row in scenario_table(args.balance, args.annual_contribution, args.years): print(row)
    elif args.cmd == "report":
        sections = []
        for t in cfg["watchlist"]:
            try:
                r = analyze_one(t, cfg)
                size = position_size(r["scored"]["total"], 50000, cfg["account"].get("cash_balance", 0) or 5000, cfg["risk"]["max_single_position"])
                sections.append(ticker_section(t, r["tech"], r["valuation"], r["fund"], r["scored"], r["signal"], r["reasons"], size))
            except Exception as e:
                sections.append(f"## {t} — ERROR\n{e}")
        fc = monte_carlo(0, cfg["account"]["contribution_limit_2026"], cfg["forecast"]["years"], cfg["forecast"]["expected_return"], cfg["forecast"]["volatility"], 2000)
        text = full_report(sections, forecast=fc)
        out = pathlib.Path("reports"); out.mkdir(exist_ok=True)
        fp = out / "latest_briefing.md"; fp.write_text(text)
        print(text); print(f"\nSaved to {fp}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
