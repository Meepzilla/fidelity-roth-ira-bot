from __future__ import annotations

def dcf(free_cash_flow: float, growth_rate: float = 0.05, discount_rate: float = 0.09, terminal_growth: float = 0.03, years: int = 5, shares_outstanding: float | None = None, net_debt: float = 0.0) -> dict:
    """Simple DCF. free_cash_flow is total FCF (same currency as output). Returns enterprise/equity value and per-share if shares given."""
    if discount_rate <= terminal_growth:
        raise ValueError("discount_rate must exceed terminal_growth")
    pv = 0.0; fcf = free_cash_flow
    for yr in range(1, years + 1):
        fcf = fcf * (1 + growth_rate) if yr > 1 or True else fcf
        # Year 1 uses grown FCF to be explicit; adjust: first iteration already grows once
        pv += fcf / ((1 + discount_rate) ** yr)
    terminal_fcf = fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** years)
    enterprise = pv + pv_terminal
    equity = enterprise - net_debt
    result = {"enterprise_value": enterprise, "equity_value": equity, "pv_forecast": pv, "pv_terminal": pv_terminal}
    if shares_outstanding:
        result["per_share"] = equity / shares_outstanding
    return result

def dividend_discount(dividend_per_share: float, growth: float, required_return: float) -> float | None:
    if required_return <= growth or dividend_per_share <= 0:
        return None
    return dividend_per_share * (1 + growth) / (required_return - growth)

def graham_number(eps: float, book_value_per_share: float) -> float | None:
    if eps <= 0 or book_value_per_share <= 0:
        return None
    return (22.5 * eps * book_value_per_share) ** 0.5

def margin_of_safety(intrinsic: float | None, price: float | None) -> float | None:
    if not intrinsic or not price or price == 0:
        return None
    return (intrinsic - price) / intrinsic

def multiples_snapshot(info: dict, price: float | None = None) -> dict:
    price = price or info.get("currentPrice") or info.get("regularMarketPrice")
    return {
        "price": price,
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "price_to_book": info.get("priceToBook"),
        "price_to_sales": info.get("priceToSalesTrailing12Months"),
        "peg": info.get("pegRatio"),
        "ev_to_ebitda": info.get("enterpriseToEbitda"),
        "dividend_yield": info.get("dividendYield"),
        "eps_trailing": info.get("trailingEps"),
        "book_value": info.get("bookValue"),
    }

def estimate_intrinsic(info: dict, price: float | None, cfg: dict) -> dict:
    """Combine available estimators. Any missing input yields None, never a fabricated value."""
    snap = multiples_snapshot(info, price)
    p = snap["price"]
    ddm = dividend_discount((info.get("dividendRate") or 0), 0.03, cfg.get("discount_rate", 0.09)) if info.get("dividendRate") else None
    graham = graham_number(info.get("trailingEps") or 0, info.get("bookValue") or 0)
    candidates = [v for v in [ddm, graham] if v]
    blended = sum(candidates) / len(candidates) if candidates else None
    return {"snapshot": snap, "ddm": ddm, "graham_number": graham, "blended_intrinsic": blended, "margin_of_safety": margin_of_safety(blended, p)}
