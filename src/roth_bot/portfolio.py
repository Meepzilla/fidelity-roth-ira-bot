from __future__ import annotations
import csv, re
import pandas as pd

def _money(v) -> float:
    if v is None or str(v).strip() in ("", "--", "n/a"):
        return 0.0
    return float(re.sub(r"[^0-9.\-]", "", str(v)) or 0)

def load_fidelity_csv(path: str) -> pd.DataFrame:
    """Parse Fidelity Positions download. Tolerates header variations and $/% symbols.
    Expected columns (any casing): Symbol/Description, Quantity, Last Price, Market Value / Current Value, Cost Basis / Average Cost.
    Skips footer disclaimer rows Fidelity appends.
    """
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        norm = { (h or "").strip().lower(): h for h in reader.fieldnames }
        def pick(*names):
            for n in names:
                if n in norm:
                    return norm[n]
            return None
        c_sym = pick("symbol", "symbol/cusip", "security")
        c_qty = pick("quantity", "qty")
        c_price = pick("last price", "price")
        c_val = pick("market value", "current value", "value")
        c_cost = pick("cost basis", "average cost basis", "cost basis total")
        for r in reader:
            sym = (r.get(c_sym) or "").strip() if c_sym else ""
            if not sym or sym.lower().startswith("the data and information") or len(sym) > 12:
                continue
            rows.append({
                "symbol": sym.upper(),
                "quantity": _money(r.get(c_qty)) if c_qty else 0.0,
                "last_price": _money(r.get(c_price)) if c_price else 0.0,
                "market_value": _money(r.get(c_val)) if c_val else 0.0,
                "cost_basis": _money(r.get(c_cost)) if c_cost else 0.0,
            })
    df = pd.DataFrame(rows)
    if not df.empty and (df["market_value"] == 0).all() and (df["quantity"] != 0).any():
        df["market_value"] = df["quantity"] * df["last_price"]
    return df

def allocation(df: pd.DataFrame, cash: float = 0.0) -> dict[str, float]:
    total = float(df["market_value"].sum() + cash) if not df.empty else cash
    if total <= 0:
        return {}
    out = {row.symbol: float(row.market_value / total) for row in df.itertuples()}
    if cash:
        out["CASH"] = cash / total
    return out

def drift_report(df: pd.DataFrame, target: dict[str, float], cash: float = 0.0, band_points: float = 5.0) -> list[dict]:
    cur = allocation(df, cash)
    tickers = sorted(set(cur) | set(target))
    total_value = float(df["market_value"].sum() + cash) if not df.empty else cash
    rows = []
    for t in tickers:
        c, tg = cur.get(t, 0.0), target.get(t, 0.0)
        drift = (c - tg) * 100
        rows.append({"symbol": t, "current_pct": round(c * 100, 2), "target_pct": round(tg * 100, 2), "drift_points": round(drift, 2), "needs_rebalance": abs(drift) > band_points, "dollar_drift": round((c - tg) * total_value, 2)})
    return rows

def contribution_status(limit: float, contributed: float) -> dict:
    remaining = max(limit - contributed, 0)
    pct = contributed / limit if limit else 0
    return {"limit": limit, "contributed": contributed, "remaining": remaining, "pct_used": round(pct * 100, 1), "warning": pct >= 0.9, "maxed": remaining == 0}

def suggest_rebalance(drift: list[dict], total_value: float) -> list[str]:
    tickets = []
    for r in drift:
        if not r["needs_rebalance"] or r["symbol"] == "CASH":
            continue
        if r["target_pct"] == 0:
            tickets.append(f"REVIEW {r['symbol']}: {r['current_pct']}% of portfolio with no target allocation set — set a target in config.yaml or trim intentionally, not automatically")
        elif r["dollar_drift"] > 0:
            tickets.append(f"TRIM {r['symbol']} by about ${r['dollar_drift']:,.0f} to return to {r['target_pct']}% target")
        else:
            tickets.append(f"BUY {r['symbol']} by about ${abs(r['dollar_drift']):,.0f} to return to {r['target_pct']}% target")
    return tickets
