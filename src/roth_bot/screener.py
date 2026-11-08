from __future__ import annotations

def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))

def score_value(valuation: dict, info: dict) -> float:
    mos = valuation.get("margin_of_safety")
    score = 50.0
    if mos is not None:
        score = _clamp(50 + mos * 150)
    pe = info.get("forwardPE") or info.get("trailingPE")
    if pe:
        # Broad anchor: PE 15 -> +10, PE 35 -> -15. ETFs often lack PE, stays neutral.
        score = _clamp(score + (22 - pe) * 0.8, 0, 100) if False else _clamp(0.7 * score + 0.3 * _clamp(50 + (22 - pe) * 2))
    return round(score, 1)

def score_quality(fund: dict) -> float:
    score = 50.0
    roe = fund.get("roe")
    if roe is not None: score += _clamp(roe * 60, -25, 25)
    pm = fund.get("profit_margin")
    if pm is not None: score += _clamp(pm * 50, -20, 20)
    cr = fund.get("current_ratio")
    if cr is not None: score += 5 if cr >= 1.5 else (-8 if cr < 1 else 0)
    de = fund.get("debt_to_equity")
    if de is not None: score += -10 if de > 200 else (5 if de < 50 else 0)
    return round(_clamp(score), 1)

def score_momentum(tech: dict) -> float:
    score = 50.0
    score += 12 if tech.get("above_sma200") else -12
    score += 6 if tech.get("above_sma50") else -6
    score += 8 if tech.get("golden_cross") else -4
    r = tech.get("rsi14", 50)
    # Context guard (Trading-ZettleKasten Indicators.md): RSI can stay overbought in a strong
    # trend, and indicators confirm rather than predict. In a confirmed uptrend the overbought
    # penalty is capped instead of treated as a sell trigger.
    uptrend = bool(tech.get("above_sma200") and tech.get("golden_cross"))
    if 45 <= r <= 65:
        score += 6
    elif r > 75:
        score += -3 if uptrend else -10
    elif r < 30:
        score += -6
    score += _clamp(tech.get("return_6m", 0) * 60, -12, 12)
    return round(_clamp(score), 1)

def score_risk(tech: dict, info: dict) -> float:
    score = 60.0
    vol = tech.get("annualized_volatility", 0.18)
    score += _clamp((0.20 - vol) * 120, -30, 15)
    dd = abs(tech.get("max_drawdown", 0))
    score += _clamp((0.25 - dd) * 40, -20, 8)
    beta = info.get("beta")
    if beta is not None: score += _clamp((1.0 - abs(beta - 1.0)) * 8, -10, 8) - 4
    return round(_clamp(score), 1)

def score_income(info: dict) -> float:
    y = info.get("dividendYield") or 0
    # 0% -> 35, 1.5% -> ~57, 4%+ -> 90. Income matters less for growth Roth, hence capped weight in composite.
    return round(_clamp(35 + y * 1400 if y < 0.1 else 90), 1) if y else 40.0

def composite(valuation: dict, fund: dict, tech: dict, info: dict, weights: dict) -> dict:
    parts = {"value": score_value(valuation, info), "quality": score_quality(fund), "momentum": score_momentum(tech), "risk": score_risk(tech, info), "income": score_income(info)}
    total = sum(parts[k] * weights.get(k, 0) for k in parts)
    return {"parts": parts, "total": round(total, 1)}

def signal_for(total: float, cfg: dict, valuation: dict, tech: dict) -> tuple[str, list[str]]:
    buy_t = cfg.get("buy_threshold", 70); hold_t = cfg.get("hold_threshold", 45)
    reasons = []
    mos = valuation.get("margin_of_safety")
    if mos is not None:
        reasons.append(f"Margin of safety {mos*100:.1f}% vs blended intrinsic estimate")
    reasons.append(f"RSI {tech.get('rsi14', 0):.0f}, price {'above' if tech.get('above_sma200') else 'below'} 200-day average")
    if tech.get("rsi14", 50) > 78: reasons.append("Overbought RSI, downgrade BUY to HOLD"); return "HOLD", reasons
    if total >= buy_t: sig = "BUY"
    elif total >= hold_t: sig = "HOLD"
    elif total >= 32: sig = "TRIM"
    else: sig = "SELL"
    # Require margin of safety for a BUY on a single name with an intrinsic estimate
    if sig == "BUY" and mos is not None and mos < 0:
        sig = "HOLD"; reasons.append("Score says BUY but price is above intrinsic estimate, held to HOLD")
    return sig, reasons

def position_size(total_score: float, portfolio_value: float, cash: float, max_single: float = 0.20, current_value: float = 0.0, volatility: float | None = None, target_volatility: float = 0.20) -> float:
    """Score scales a base position. Volatility scales it down (Trading-ZettleKasten Position
    Sizing.md: higher volatility, smaller size). Full size at or below target volatility,
    shrinking past it with a floor so volatile names are reduced, not banned."""
    if total_score < 45 or portfolio_value <= 0:
        return 0.0
    base_pct = 0.05 + max(0, (total_score - 45)) / 55 * 0.10  # 5% to 15%
    vol_factor = 1.0
    if volatility and volatility > target_volatility:
        vol_factor = max(0.35, target_volatility / volatility)
    target_value = min(portfolio_value * base_pct * vol_factor, portfolio_value * max_single)
    add = max(0.0, target_value - current_value)
    return round(min(add, cash), 2)

def bear_case(valuation: dict, fund: dict, tech: dict, scored: dict) -> str:
    """One generated counter-thesis line. Built to answer the Biases.md prompt:
    what evidence would make me change my mind about this trade."""
    parts = scored.get("parts", {})
    weakest = min(parts, key=parts.get) if parts else "value"
    bits = [f"weakest score is {weakest} at {parts.get(weakest)}"]
    mos = valuation.get("margin_of_safety")
    if mos is not None and mos < 0:
        bits.append(f"price sits {abs(mos)*100:.0f}% above the blended intrinsic estimate")
    if tech.get("rsi14", 50) > 75:
        bits.append(f"RSI {tech['rsi14']:.0f} is overbought, though RSI can stay extreme in a strong trend")
    if tech.get("annualized_volatility", 0) > 0.30:
        bits.append(f"volatility {tech['annualized_volatility']*100:.0f}% is high, consider a limit order instead of a market order")
    if tech.get("max_drawdown", 0) < -0.35:
        bits.append(f"historical max drawdown {tech['max_drawdown']*100:.0f}% shows the downside this name can deliver")
    return "Bear case, what would change this signal: " + "; ".join(bits) + ". Review trigger: score falls below the hold threshold, price drops 20% from here, or the thesis facts change."

def stress_loss(suggested_size: float, tech: dict) -> float:
    """Per-decision risk budget, adapted from the vault per-trade risk cap. Stress move is the
    smaller of the historical max drawdown magnitude and a 40% cap."""
    move = min(abs(tech.get("max_drawdown", 0)) or 0.25, 0.40)
    return round(suggested_size * move, 2)
