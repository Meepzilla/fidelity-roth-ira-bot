from __future__ import annotations
import pandas as pd
import numpy as np

def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    vals = 100 - (100 / (1 + rs))
    return float(vals.iloc[-1]) if not vals.empty and pd.notna(vals.iloc[-1]) else 50.0

def macd(close: pd.Series) -> dict:
    fast, slow = ema(close, 12), ema(close, 26)
    line = fast - slow
    signal = ema(line, 9)
    return {"macd": float(line.iloc[-1]), "signal": float(signal.iloc[-1]), "histogram": float((line - signal).iloc[-1]), "bullish": bool(line.iloc[-1] > signal.iloc[-1])}

def bollinger(close: pd.Series, window: int = 20, num_std: float = 2.0) -> dict:
    mid = sma(close, window).iloc[-1]
    std = close.rolling(window).std().iloc[-1]
    return {"mid": float(mid), "upper": float(mid + num_std * std), "lower": float(mid - num_std * std)}

def analyze_technicals(df: pd.DataFrame) -> dict:
    close = df["Close"]
    price = float(close.iloc[-1])
    s50 = float(sma(close, 50).iloc[-1]) if len(close) >= 50 else price
    s200 = float(sma(close, 200).iloc[-1]) if len(close) >= 200 else s50
    hi52 = float(close.tail(252).max()); lo52 = float(close.tail(252).min())
    pos52 = (price - lo52) / (hi52 - lo52) if hi52 > lo52 else 0.5
    daily = close.pct_change().dropna()
    vol = float(daily.std() * np.sqrt(252)) if len(daily) > 5 else 0.0
    return {
        "price": price, "sma50": s50, "sma200": s200,
        "above_sma50": price > s50, "above_sma200": price > s200,
        "golden_cross": s50 > s200,
        "rsi14": rsi(close), "macd": macd(close), "bollinger": bollinger(close),
        "high_52w": hi52, "low_52w": lo52, "position_52w": float(pos52),
        "annualized_volatility": vol,
        "return_1m": float(close.iloc[-1] / close.iloc[-22] - 1) if len(close) >= 22 else 0.0,
        "return_6m": float(close.iloc[-1] / close.iloc[-126] - 1) if len(close) >= 126 else 0.0,
        "return_1y": float(close.iloc[-1] / close.iloc[-252] - 1) if len(close) >= 252 else 0.0,
        "max_drawdown": float((close / close.cummax() - 1).min()),
    }
