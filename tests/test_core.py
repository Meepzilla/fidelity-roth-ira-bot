import pandas as pd
from roth_bot.data import synthetic_history
from roth_bot.technicals import analyze_technicals, rsi
from roth_bot.valuation import dcf, dividend_discount, graham_number, margin_of_safety
from roth_bot.forecast import monte_carlo, cagr
from roth_bot.portfolio import load_fidelity_csv, drift_report, contribution_status
from roth_bot.screener import composite, signal_for, position_size
import pathlib, textwrap

def test_technicals_ranges():
    df = synthetic_history()
    t = analyze_technicals(df)
    assert 0 <= t["rsi14"] <= 100
    assert t["price"] > 0 and t["high_52w"] >= t["low_52w"]
    assert -1 <= t["max_drawdown"] <= 0

def test_rsi_flat():
    s = pd.Series([100.0]*30)
    # Flat series yields neutral handling, no crash
    assert 0 <= rsi(s) <= 100

def test_dcf_and_valuation_helpers():
    v = dcf(free_cash_flow=1_000_000, growth_rate=0.05, shares_outstanding=100_000)
    assert v["per_share"] > 0 and v["enterprise_value"] > 1_000_000
    assert dividend_discount(2.0, 0.03, 0.09) > 0
    assert dividend_discount(0, 0.03, 0.09) is None
    assert graham_number(3.0, 20.0) > 0
    assert graham_number(-1, 20) is None
    assert abs(margin_of_safety(120, 100) - 0.1666) < 0.01

def test_monte_carlo_ordering():
    mc = monte_carlo(10000, 7500, 10, simulations=1000)
    assert mc["p10"] <= mc["median"] <= mc["p90"]
    assert mc["total_contributed"] == 10000 + 75000
    assert abs(cagr(100, 121, 2) - 0.10) < 1e-6

def test_fidelity_csv_and_drift(tmp_path):
    csv_path = tmp_path / "pos.csv"
    csv_path.write_text(textwrap.dedent("""\
        Symbol,Quantity,Last Price,Market Value,Cost Basis
        VTI,10,$300.00,"$3,000.00","$2,500.00"
        VXUS,20,$60.00,"$1,200.00","$1,000.00"
        """))
    df = load_fidelity_csv(str(csv_path))
    assert len(df) == 2 and df.iloc[0]["market_value"] == 3000
    drift = drift_report(df, {"VTI": 0.60, "VXUS": 0.25, "CASH": 0.05}, cash=0, band_points=5)
    assert any(r["symbol"] == "VTI" for r in drift)
    cs = contribution_status(7500, 7500)
    assert cs["maxed"] and cs["remaining"] == 0

def test_scoring_and_sizing():
    val = {"margin_of_safety": 0.20}
    fund = {"roe": 0.20, "profit_margin": 0.15, "current_ratio": 1.8, "debt_to_equity": 40}
    tech = {"above_sma200": True, "above_sma50": True, "golden_cross": True, "rsi14": 55, "return_6m": 0.08, "annualized_volatility": 0.15, "max_drawdown": -0.12}
    info = {"forwardPE": 18, "beta": 1.0, "dividendYield": 0.015}
    weights = {"value": 0.25, "quality": 0.25, "momentum": 0.20, "risk": 0.15, "income": 0.15}
    scored = composite(val, fund, tech, info, weights)
    assert 0 <= scored["total"] <= 100
    sig, _ = signal_for(scored["total"], {"buy_threshold": 70, "hold_threshold": 45}, val, tech)
    assert sig in ("BUY", "HOLD", "TRIM", "SELL")
    assert position_size(30, 50000, 5000) == 0.0
    assert position_size(85, 50000, 5000) > 0
