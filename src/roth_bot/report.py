from __future__ import annotations
import datetime

def ticker_section(ticker: str, tech: dict, valuation: dict, fund: dict, scored: dict, signal: str, reasons: list[str], size: float) -> str:
    snap = valuation.get("snapshot", {})
    lines = [
        f"## {ticker} — {signal} (score {scored['total']}/100)",
        f"Price ${tech['price']:,.2f} | SMA50 ${tech['sma50']:,.2f} | SMA200 ${tech['sma200']:,.2f} | RSI {tech['rsi14']:.0f} | Vol {tech['annualized_volatility']*100:.1f}%",
        f"52-week position {tech['position_52w']*100:.0f}% of range (${tech['low_52w']:,.2f} to ${tech['high_52w']:,.2f}) | 6m return {tech['return_6m']*100:.1f}%",
        f"Valuation: forward P/E {snap.get('forward_pe')} | P/B {snap.get('price_to_book')} | yield {snap.get('dividend_yield')} | blended intrinsic {valuation.get('blended_intrinsic')}",
        f"Scores: " + ", ".join(f"{k} {v}" for k, v in scored["parts"].items()),
        f"Suggested add (if you agree): ${size:,.2f}",
        "Reasons:",
    ] + [f"- {r}" for r in reasons] + [f"Fundamentals: ROE {fund.get('roe')} | margin {fund.get('profit_margin')} | D/E {fund.get('debt_to_equity')} | analyst mean target {fund.get('analyst_target_mean')}"]
    return "\n".join(lines)

def full_report(sections: list[str], portfolio_lines: list[str] | None = None, forecast: dict | None = None) -> str:
    today = datetime.date.today().isoformat()
    head = [f"# Roth IRA Briefing — {today}", "", "Decision support only. No trades were placed. Review each ticket in Fidelity before acting.", ""]
    if portfolio_lines:
        head += ["## Portfolio", *portfolio_lines, ""]
    if forecast:
        head += ["## Projection (Monte Carlo)", f"Median ${forecast['median']:,.0f} | P25 ${forecast['p25']:,.0f} | P75 ${forecast['p75']:,.0f} | Total contributed ${forecast['total_contributed']:,.0f} over {forecast['years']} years", ""]
    return "\n".join(head + sections)
