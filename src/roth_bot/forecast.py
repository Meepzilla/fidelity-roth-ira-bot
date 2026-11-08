from __future__ import annotations
import numpy as np

def monte_carlo(balance: float, annual_contribution: float, years: int, expected_return: float = 0.08, volatility: float = 0.16, simulations: int = 5000, seed: int = 7) -> dict:
    """Geometric Brownian motion with annual contributions at start of each year."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(expected_return, volatility, size=(simulations, years))
    balances = np.full(simulations, float(balance))
    for yr in range(years):
        balances = balances + annual_contribution
        balances = balances * (1 + returns[:, yr])
        balances = np.maximum(balances, 0)
    return {
        "p10": float(np.percentile(balances, 10)),
        "p25": float(np.percentile(balances, 25)),
        "median": float(np.percentile(balances, 50)),
        "p75": float(np.percentile(balances, 75)),
        "p90": float(np.percentile(balances, 90)),
        "mean": float(balances.mean()),
        "total_contributed": float(balance + annual_contribution * years),
        "years": years, "simulations": simulations,
    }

def cagr(start: float, end: float, years: float) -> float:
    if start <= 0 or years <= 0:
        return 0.0
    return (end / start) ** (1 / years) - 1

def scenario_table(balance: float, annual_contribution: float, years: int) -> list[dict]:
    rows = []
    for name, ret in [("Bear 4%", 0.04), ("Base 7%", 0.07), ("Bull 10%", 0.10)]:
        bal = balance
        for _ in range(years):
            bal = (bal + annual_contribution) * (1 + ret)
        rows.append({"scenario": name, "return_assumption": ret, "ending_balance": round(bal, 2)})
    return rows
