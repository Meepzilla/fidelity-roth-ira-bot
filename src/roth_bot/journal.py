from __future__ import annotations
import csv, datetime, pathlib

FIELDS = ["date", "ticker", "signal", "score", "price", "suggested_size", "action", "reason"]

def journal_path(base: str | pathlib.Path = "data/decisions.csv") -> pathlib.Path:
    return pathlib.Path(base)

def log_signal(path, ticker: str, signal: str, score: float, price: float, suggested_size: float, today: str | None = None) -> dict:
    """Append one recommendation row. The bot remembers every call it makes.
    Adapted from Trading-ZettleKasten journaling directives (Biases.md, Trader Psychology.md):
    a journal is the control for overconfidence and the evidence base for review."""
    p = journal_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    row = {"date": today or datetime.date.today().isoformat(), "ticker": ticker.upper(), "signal": signal, "score": score, "price": price, "suggested_size": suggested_size, "action": "", "reason": ""}
    exists = p.exists()
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)
    return row

def load_journal(path) -> list[dict]:
    p = journal_path(path)
    if not p.exists():
        return []
    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("score", "price", "suggested_size"):
            try: r[k] = float(r[k])
            except (TypeError, ValueError): r[k] = 0.0
    return rows

def record_action(path, ticker: str, action: str, reason: str = "") -> bool:
    """Attach the user's action to the most recent unacted row for a ticker."""
    rows = load_journal(path)
    for r in reversed(rows):
        if r["ticker"] == ticker.upper() and not r.get("action"):
            r["action"] = action; r["reason"] = reason
            p = journal_path(path)
            with open(p, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
                for row in rows: w.writerow({k: row.get(k, "") for k in FIELDS})
            return True
    return False

def evaluate(rows: list[dict], current_prices: dict[str, float]) -> dict:
    """Score past calls against current prices. Process check, not a promise.
    BUY hits when price rose, SELL/TRIM hit when price fell, HOLD is neutral and excluded from hit rate."""
    buckets: dict[str, dict] = {}
    for r in rows:
        cur = current_prices.get(r["ticker"])
        if cur is None or not r.get("price"):
            continue
        fwd = cur / r["price"] - 1
        b = buckets.setdefault(r["signal"], {"count": 0, "forward_returns": [], "hits": 0, "scored": 0})
        b["count"] += 1; b["forward_returns"].append(fwd)
        if r["signal"] == "BUY":
            b["scored"] += 1; b["hits"] += 1 if fwd > 0 else 0
        elif r["signal"] in ("SELL", "TRIM"):
            b["scored"] += 1; b["hits"] += 1 if fwd < 0 else 0
    for b in buckets.values():
        fr = b.pop("forward_returns")
        b["avg_forward_return"] = round(sum(fr) / len(fr), 4) if fr else 0.0
        b["hit_rate"] = round(b["hits"] / b["scored"], 3) if b["scored"] else None
    return buckets

def process_adherence(rows: list[dict]) -> dict:
    """Process over outcomes (Trader Psychology.md): was the loop closed with an action and a reason."""
    total = len(rows)
    acted = sum(1 for r in rows if r.get("action"))
    reasoned = sum(1 for r in rows if r.get("reason"))
    return {"logged": total, "action_recorded_pct": round(acted / total * 100, 1) if total else 0.0, "reason_recorded_pct": round(reasoned / total * 100, 1) if total else 0.0}
