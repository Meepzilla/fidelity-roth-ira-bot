from __future__ import annotations
import pathlib
import yaml

DEFAULTS = {
    "account": {"broker": "Fidelity", "type": "Roth IRA", "contribution_limit_2026": 7500, "contributed_ytd": 0, "cash_balance": 0},
    "watchlist": ["VTI", "VXUS", "BND"],
    "target_allocation": {"VTI": 0.60, "VXUS": 0.25, "BND": 0.10, "CASH": 0.05},
    "risk": {"max_single_position": 0.20, "rebalance_band_points": 5.0, "max_portfolio_volatility": 0.20, "stop_loss_review_pct": -0.20, "target_volatility": 0.20, "sector_concentration_pct": 40.0, "earnings_window_days": 14},
    "scoring": {"buy_threshold": 70, "hold_threshold": 45, "weights": {"value": 0.25, "quality": 0.25, "momentum": 0.20, "risk": 0.15, "income": 0.15}},
    "valuation": {"dcf": {"discount_rate": 0.09, "terminal_growth": 0.03, "projection_years": 5}, "margin_of_safety_required": 0.15},
    "forecast": {"years": 27, "expected_return": 0.08, "volatility": 0.16, "simulations": 5000},
}

def load_config(path: str | pathlib.Path | None = None) -> dict:
    cfg = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()}
    # deep copy nested scoring/valuation
    import copy
    cfg = copy.deepcopy(DEFAULTS)
    if path is None:
        for candidate in [pathlib.Path("config.yaml"), pathlib.Path("config.example.yaml")]:
            if candidate.exists():
                path = candidate
                break
    if path and pathlib.Path(path).exists():
        loaded = yaml.safe_load(pathlib.Path(path).read_text()) or {}
        for k, v in loaded.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg
