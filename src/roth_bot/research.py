from __future__ import annotations

def fundamentals_snapshot(info: dict) -> dict:
    return {
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"), "industry": info.get("industry"),
        "market_cap": info.get("marketCap"), "beta": info.get("beta"),
        "profit_margin": info.get("profitMargins"), "operating_margin": info.get("operatingMargins"),
        "roe": info.get("returnOnEquity"), "roa": info.get("returnOnAssets"),
        "revenue_growth": info.get("revenueGrowth"), "earnings_growth": info.get("earningsGrowth"),
        "debt_to_equity": info.get("debtToEquity"), "current_ratio": info.get("currentRatio"),
        "free_cashflow": info.get("freeCashflow"), "operating_cashflow": info.get("totalCashFromOperatingActivities"),
        "dividend_yield": info.get("dividendYield"), "payout_ratio": info.get("payoutRatio"),
        "analyst_target_mean": info.get("targetMeanPrice"), "analyst_target_low": info.get("targetLowPrice"), "analyst_target_high": info.get("targetHighPrice"),
        "recommendation": info.get("recommendationKey"), "num_analysts": info.get("numberOfAnalystOpinions"),
    }

def earnings_flag(next_earnings, today=None, window_days: int = 14) -> str | None:
    """Event-risk line for single stocks reporting soon. Source rule: earnings gap risk is real and
    the score does not price it (Trading-ZettleKasten Risk Management.md, Earnings & Reports.md)."""
    import datetime as _dt
    if next_earnings is None:
        return None
    today = today or _dt.date.today()
    delta = (next_earnings - today).days
    if 0 <= delta <= window_days:
        return f"Earnings on {next_earnings.isoformat()} ({delta}d away). Score does not price gap risk. Guidance matters more than the headline numbers."
    return None

def quality_flags(f: dict) -> list[str]:
    flags = []
    if f.get("roe") is not None and f["roe"] < 0:
        flags.append("Negative ROE")
    if f.get("debt_to_equity") is not None and f["debt_to_equity"] > 200:
        flags.append("High debt/equity (>2.0x as reported x100)")
    if f.get("profit_margin") is not None and f["profit_margin"] < 0:
        flags.append("Negative profit margin")
    if f.get("current_ratio") is not None and f["current_ratio"] < 1:
        flags.append("Current ratio below 1.0")
    return flags
