from __future__ import annotations
import datetime

def ticker_section(ticker: str, tech: dict, valuation: dict, fund: dict, scored: dict, signal: str, reasons: list[str], size: float, bear: str | None = None, earnings: str | None = None, stress: float | None = None) -> str:
    snap = valuation.get("snapshot", {})
    trend = "uptrend" if tech.get("above_sma200") else "downtrend"
    lines = [
        f"## {ticker} — {signal} (score {scored['total']}/100)",
        f"Price ${tech['price']:,.2f} | SMA50 ${tech['sma50']:,.2f} | SMA200 ${tech['sma200']:,.2f} | RSI {tech['rsi14']:.0f} ({trend} context) | Vol {tech['annualized_volatility']*100:.1f}%",
        f"52-week position {tech['position_52w']*100:.0f}% of range (${tech['low_52w']:,.2f} to ${tech['high_52w']:,.2f}) | 6m return {tech['return_6m']*100:.1f}%",
        f"Valuation: forward P/E {snap.get('forward_pe')} | P/B {snap.get('price_to_book')} | EV/EBITDA {snap.get('ev_to_ebitda')} | yield {snap.get('dividend_yield')} | blended intrinsic {valuation.get('blended_intrinsic')}",
        f"Scores: " + ", ".join(f"{k} {v}" for k, v in scored["parts"].items()),
        f"Suggested add (if you agree): ${size:,.2f}",
        "Reasons:",
    ] + [f"- {r}" for r in reasons] + [f"Fundamentals: ROE {fund.get('roe')} | margin {fund.get('profit_margin')} | D/E {fund.get('debt_to_equity')} | analyst mean target {fund.get('analyst_target_mean')}"]
    if bear:
        lines.append(bear)
    if earnings:
        lines.append(f"Event risk: {earnings}")
    if stress is not None and size > 0:
        lines.append(f"Stress loss estimate on the suggested add, if this name repeats a drawdown-scale move: ${stress:,.2f}")
    return "\n".join(lines)

def plan_lines(cfg: dict) -> list[str]:
    """Restate the active plan every run (Biases.md: a written plan is a bias control)."""
    r, s = cfg.get("risk", {}), cfg.get("scoring", {})
    return [
        "## Active plan (from config)",
        f"Buy at score {s.get('buy_threshold')}+, hold at {s.get('hold_threshold')}+. Max single position {r.get('max_single_position', 0.2)*100:.0f}%. Rebalance band {r.get('rebalance_band_points')} points. Review any position down {abs(r.get('stop_loss_review_pct', -0.2))*100:.0f}% from cost.",
        "The score ranks expected value under the model assumptions. It does not predict returns. Process over outcomes: a good decision with a bad outcome is still a good decision.",
    ]

def track_record_lines(buckets: dict, adherence: dict) -> list[str]:
    if not buckets and not adherence.get("logged"):
        return []
    lines = ["## Track record (from the decision journal)"]
    for sig, b in sorted(buckets.items()):
        hr = f" | hit rate {b['hit_rate']*100:.0f}%" if b.get("hit_rate") is not None else ""
        lines.append(f"{sig}: {b['count']} calls | avg forward return {b['avg_forward_return']*100:.1f}%{hr}")
    lines.append(f"Process adherence: action recorded on {adherence.get('action_recorded_pct')}% of calls, reason recorded on {adherence.get('reason_recorded_pct')}%.")
    return lines

def full_report(sections: list[str], portfolio_lines: list[str] | None = None, forecast: dict | None = None, plan: list[str] | None = None, track: list[str] | None = None) -> str:
    today = datetime.date.today().isoformat()
    head = [f"# Roth IRA Briefing — {today}", "", "Decision support only. No trades were placed. Review each ticket in Fidelity before acting.", ""]
    if plan:
        head += [*plan, ""]
    if portfolio_lines:
        head += ["## Portfolio", *portfolio_lines, ""]
    if forecast:
        head += ["## Projection (Monte Carlo)", f"Median ${forecast['median']:,.0f} | P25 ${forecast['p25']:,.0f} | P75 ${forecast['p75']:,.0f} | Total contributed ${forecast['total_contributed']:,.0f} over {forecast['years']} years", ""]
    if track:
        head += [*track, ""]
    return "\n".join(head + sections)
