"""Shared conservative contract gate for the V7 Lucid paper account.

All strategies share a single micro-futures capacity. Pending trades reserve
one contract until filled or cancelled; OPEN trades reserve their actual qty.
This is a paper simulation only, not a broker-side risk check.
"""
import os

MAX_MICROS = int(os.getenv("TAURUS_LUCID_MAX_MICROS", "20"))
MICRO_MARKETS = frozenset(("nq", "mes", "mgc"))

def allowed_quantity(db, market, side, proposed):
    """Return permitted integer micro contracts; zero rejects a new fill.

    Pending reservations prevent simultaneous strategies from each assuming
    they own the same capacity. The current trade being filled is excluded
    from reservations by its market+side only at the caller's discretion;
    here we conservatively count all pending orders, including the caller.
    """
    if market not in MICRO_MARKETS or side not in ("LONG", "SHORT"):
        return 0
    if MAX_MICROS <= 0:
        return 0
    rows = db.execute(
        "SELECT market,side,status,qty FROM trades WHERE status IN ('OPEN','PENDING')"
    ).fetchall()
    used = 0
    for row in rows:
        if row["market"] not in MICRO_MARKETS:
            continue
        if row["status"] == "OPEN":
            used += max(0, int(row["qty"] or 0))
        else:
            used += 1
        if row["market"] == market and row["side"] != side:
            return 0
    return max(0, min(int(proposed), MAX_MICROS - used))
