from __future__ import annotations
import pandas as pd

def get_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Return OHLCV history. Isolated so provider can be swapped."""
    import yfinance as yf
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if df.empty:
        raise ValueError(f"No history returned for {ticker}. Check ticker or network.")
    return df

def get_info(ticker: str) -> dict:
    import yfinance as yf
    t = yf.Ticker(ticker)
    try:
        return t.info or {}
    except Exception:
        return {}

def get_next_earnings(ticker: str):
    """Next earnings date as a date, or None. Index ETFs normally return None, which is the intended filter."""
    import datetime as _dt
    try:
        import yfinance as yf
        cal = yf.Ticker(ticker).calendar
        dates = []
        if isinstance(cal, dict):
            raw = cal.get("Earnings Date") or []
            dates = list(raw) if isinstance(raw, (list, tuple)) else [raw]
        elif cal is not None and hasattr(cal, "loc"):
            try:
                dates = list(cal.loc["Earnings Date"].values)
            except Exception:
                dates = []
        for d in dates:
            if d is None:
                continue
            if hasattr(d, "date"):
                return d.date()
            try:
                return _dt.date.fromisoformat(str(d)[:10])
            except ValueError:
                continue
    except Exception:
        return None
    return None

def get_price(ticker: str, info: dict | None = None) -> float | None:
    info = info if info is not None else get_info(ticker)
    for key in ("currentPrice", "regularMarketPrice", "previousClose"):
        if info.get(key):
            return float(info[key])
    return None

def synthetic_history(n: int = 300, start: float = 100.0, drift: float = 0.0004, vol: float = 0.015, seed: int = 42) -> pd.DataFrame:
    """Deterministic synthetic series for tests and offline demos."""
    import numpy as np
    rng = np.random.default_rng(seed)
    returns = rng.normal(drift, vol, size=n)
    prices = start * (1 + returns).cumprod()
    idx = pd.date_range("2024-01-02", periods=n, freq="B")
    return pd.DataFrame({"Open": prices, "High": prices * 1.005, "Low": prices * 0.995, "Close": prices, "Volume": 1_000_000}, index=idx)
