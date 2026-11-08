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

def test_v02_journal_and_evaluation(tmp_path):
    from roth_bot.journal import log_signal, load_journal, record_action, evaluate, process_adherence
    p = tmp_path / "decisions.csv"
    log_signal(p, "VTI", "BUY", 72.0, 100.0, 2500.0, today="2026-11-01")
    log_signal(p, "XYZ", "SELL", 20.0, 50.0, 0.0, today="2026-11-01")
    rows = load_journal(p)
    assert len(rows) == 2
    assert record_action(p, "VTI", "bought", "drift was low")
    rows = load_journal(p)
    buckets = evaluate(rows, {"VTI": 110.0, "XYZ": 40.0})
    assert buckets["BUY"]["hit_rate"] == 1.0 and buckets["SELL"]["hit_rate"] == 1.0
    assert buckets["BUY"]["avg_forward_return"] == 0.1
    adh = process_adherence(rows)
    assert adh["logged"] == 2 and adh["action_recorded_pct"] == 50.0

def test_v02_vol_scaled_sizing_and_rsi_guard():
    from roth_bot.screener import score_momentum
    calm = position_size(85, 50000, 100000, volatility=0.10)
    wild = position_size(85, 50000, 100000, volatility=0.60)
    assert 0 < wild < calm
    up = {"above_sma200": True, "above_sma50": True, "golden_cross": True, "rsi14": 82, "return_6m": 0.10}
    down = {"above_sma200": False, "above_sma50": False, "golden_cross": False, "rsi14": 82, "return_6m": 0.10}
    assert score_momentum(up) > score_momentum(down) + 20

def test_v02_bear_case_concentration_recovery_earnings():
    from roth_bot.screener import bear_case, stress_loss
    from roth_bot.portfolio import sector_concentration, recovery_pct
    from roth_bot.research import earnings_flag
    import datetime as dt
    val = {"margin_of_safety": -0.10}
    tech = {"rsi14": 55, "annualized_volatility": 0.18, "max_drawdown": -0.20}
    scored = {"parts": {"value": 30, "quality": 60, "momentum": 55, "risk": 50, "income": 45}, "total": 48}
    text = bear_case(val, {}, tech, scored)
    assert "weakest score is value" in text and "above the blended intrinsic" in text
    assert stress_loss(1000, tech) == 200.0
    df = pd.DataFrame([{"symbol": "AAPL", "quantity": 1, "last_price": 1, "market_value": 500.0, "cost_basis": 1}, {"symbol": "MSFT", "quantity": 1, "last_price": 1, "market_value": 300.0, "cost_basis": 1}, {"symbol": "BNDX", "quantity": 1, "last_price": 1, "market_value": 200.0, "cost_basis": 1}])
    conc = sector_concentration(df, {"AAPL": "Technology", "MSFT": "Technology", "BNDX": "Bond"}, 40.0)
    assert conc[0]["sector"] == "Technology" and conc[0]["flag"] and conc[0]["pct"] == 80.0
    assert recovery_pct(-0.25) == 33.3
    assert earnings_flag(dt.date(2026, 11, 20), today=dt.date(2026, 11, 8)) is not None
    assert earnings_flag(dt.date(2027, 2, 1), today=dt.date(2026, 11, 8)) is None
    assert earnings_flag(None, today=dt.date(2026, 11, 8)) is None

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
