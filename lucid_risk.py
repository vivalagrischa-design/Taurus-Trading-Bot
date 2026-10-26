"""Shared conservative contract gate for the V7 Lucid paper account.

All strategies share a single micro-futures capacity. Pending trades reserve
one contract until filled or cancelled; OPEN trades reserve their actual qty.
This is a paper simulation only, not a broker-side risk check.
"""
import os

MAX_MICROS = int(os.getenv("TAURUS_LUCID_MAX_MICROS", "20"))
MICRO_MARKETS = frozenset(("nq", "mes", "mgc"))

def allowed_quantity(db, market, side, proposed, exclude_trade_id=None):
    """Return permitted integer micro contracts; zero rejects a new fill.

    Pending reservations prevent simultaneous strategies from each assuming
    they own the same capacity. The trade currently being filled is excluded by its id; other pending
    trades each reserve one contract.
    """
    if market not in MICRO_MARKETS or side not in ("LONG", "SHORT"):
        return 0
    if MAX_MICROS <= 0:
        return 0
    rows = db.execute(
        "SELECT id,market,side,status,qty FROM trades WHERE status IN ('OPEN','PENDING')"
    ).fetchall()
    used = 0
    for row in rows:
        if row["id"] == exclude_trade_id:
            continue
        if row["market"] not in MICRO_MARKETS:
            continue
        if row["status"] == "OPEN":
            used += max(0, int(row["qty"] or 0))
        else:
            used += 1
        if row["market"] == market and row["side"] != side:
            return 0
    return max(0, min(int(proposed), MAX_MICROS - used))
