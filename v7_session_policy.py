"""V7 session policy: independent research, shadow-account admission control.

NY exchange-time rules avoid DST errors. All decision inputs must be known at
decision time. This module sends no orders and does not change V6.
"""
from dataclasses import dataclass
from datetime import datetime,time
from zoneinfo import ZoneInfo

NY=ZoneInfo("America/New_York")

@dataclass(frozen=True)
class SessionRules:
    # US stock cash open 09:30 NY, irrespective of Swiss/US DST mismatches.
    open_pause_start: time = time(9,20)
    open_pause_end: time = time(12,0)
    # 12:00 NY = 17:00 Swiss on 26 Oct 2026; 18:00 normally in winter.
    morning_profit_lock_usd: float | None = None
    # Select only 2-5 vetted strategy ids for Lucid; LAB logs all.
    lucid_strategies: tuple[str,...] = ()
    # On pause: 'hold' = no new entries, existing positions retain normal SL/TP;
    # 'flatten' = request closing ALL live positions at contemporaneous executable
    # prices (handled by broker/position executor, not this module).
    pause_position_policy: str = "hold"

    def __post_init__(self):
        if self.pause_position_policy not in ("hold","flatten"):
            raise ValueError("pause_position_policy must be hold or flatten")
        if len(self.lucid_strategies)>5:
            raise ValueError("Lucid shortlist maximum five strategies")

@dataclass(frozen=True)
class GateResult:
    allow: bool
    reason: str
    request_flatten: bool=False

class SessionGate:
    def __init__(self,rules=None):
        self.rules=rules or SessionRules()
        self.manual_pause=False
        self.realized_session_pnl=0.0
        self.locked_for_session=False
        self.session_key=None

    def start_session(self,session_key):
        if session_key!=self.session_key:
            self.session_key=session_key
            self.realized_session_pnl=0.0
            self.locked_for_session=False
            self.manual_pause=False

    def register_closed_trade(self,realized_net_pnl):
        # Must be fed from actual simulator fills, never floating profit.
        self.realized_session_pnl+=float(realized_net_pnl)
        limit=self.rules.morning_profit_lock_usd
        if limit is not None and self.realized_session_pnl>=limit:
            self.locked_for_session=True

    def decision(self,strategy:str,at:datetime,book="lucid")->GateResult:
        if not isinstance(at,datetime) or at.tzinfo is None:
            raise ValueError("timezone-aware datetime required")
        if book=="lab":
            return GateResult(True,"LAB_ALWAYS_RECORD")
        if book!="lucid":
            raise ValueError("unknown book")
        if strategy not in self.rules.lucid_strategies:
            return GateResult(False,"STRATEGY_NOT_SELECTED")
        ny=at.astimezone(NY).time()
        pause=(self.rules.open_pause_start<=ny<self.rules.open_pause_end)
        blocked=self.manual_pause or self.locked_for_session or pause
        if blocked:
            reason=("MANUAL_PAUSE" if self.manual_pause else
                    "PROFIT_LOCK" if self.locked_for_session else "OPENING_PAUSE")
            return GateResult(False,reason,
                request_flatten=self.rules.pause_position_policy=="flatten")
        return GateResult(True,"SESSION_ALLOWED")
