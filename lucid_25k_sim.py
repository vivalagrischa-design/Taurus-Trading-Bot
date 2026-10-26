"""TAURUS V7 LucidFlex 25K shared-account paper risk gate.

Standalone research component. NOT wired into V6 paper_engine or real brokerage.
All timestamps are UTC-aware. No real orders.
"""
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
MICRO_POINT_VALUE = {"nq": 2.0, "mes": 5.0, "mgc": 10.0}

@dataclass
class AccountRules:
    starting_balance: float = 25_000.0
    profit_target: float = 1_250.0
    max_loss: float = 1_000.0
    eval_max_micros: int = 20
    funded_initial_max_micros: int = 10
    funded_scaled_max_micros: int = 20
    funded_scale_profit: float = 1_000.0
    eval_consistency: float = 0.40
    daily_loss_limit: float | None = None  # LucidFlex DLL ON amount MUST be verified at checkout
    risk_per_trade: float = 200.0  # TAURUS internal, not Lucid rule
    max_open_stop_risk: float = 600.0  # TAURUS internal, not Lucid rule
    max_daily_loss_internal: float = 400.0  # TAURUS internal, not Lucid rule
    # For new trades only; broker mandates liquidation by 16:45 NY.
    new_entry_cutoff: time = time(16, 40)

@dataclass
class Position:
    market: str
    side: str
    qty: int
    entry: float
    stop: float
    strategies: list[str] = field(default_factory=list)

    @property
    def planned_risk(self) -> float:
        v = MICRO_POINT_VALUE[self.market]
        return abs(self.entry - self.stop) * v * self.qty

@dataclass
class Admission:
    accepted: bool
    reason: str
    qty: int = 0

class Lucid25K:
    """One shared virtual account, independent research strategies upstream.

    All positions in same market must face same direction. No implicit netting,
    no orders sent. Caller must supply fee-adjusted realized pnl and mark equity.
    """
    def __init__(self, rules=None, phase="evaluation"):
        self.rules = rules or AccountRules()
        if phase not in ("evaluation", "funded"):
            raise ValueError("unknown phase")
        self.phase = phase
        self.balance = self.rules.starting_balance
        self.session_start_balance = self.balance
        self.peak_eod = self.balance
        self.mll_floor = self.balance - self.rules.max_loss
        self.positions: list[Position] = []
        self.session_profit_reference = 0.0
        self.funded_max_micros = self.rules.funded_initial_max_micros
        self.locked = False
        self.breached = False
        self.positive_days = []
        self.session_day = None

    def capacity(self):
        return self.rules.eval_max_micros if self.phase == "evaluation" else self.funded_max_micros

    def open_micros(self):
        return sum(p.qty for p in self.positions)

    def stop_risk(self):
        return sum(p.planned_risk for p in self.positions)

    def mark(self, quotes):
        """Mark-to-market account equity, quotes keyed by nq/mes/mgc."""
        floating = 0.0
        for p in self.positions:
            px = quotes[p.market]
            direction = 1 if p.side == "LONG" else -1
            floating += (px - p.entry) * direction * MICRO_POINT_VALUE[p.market] * p.qty
        return self.balance + floating

    def _limits(self, equity):
        if equity <= self.mll_floor:
            self.breached = True
            self.locked = True
            return "MAX_LOSS_BREACH"
        daily_loss = self.session_start_balance - equity
        if self.rules.daily_loss_limit is not None and daily_loss >= self.rules.daily_loss_limit:
            self.locked = True
            return "LUCID_DAILY_LOCK"
        if daily_loss >= self.rules.max_daily_loss_internal:
            self.locked = True
            return "TAURUS_DAILY_LOCK"
        return None

    def admit(self, market, side, desired_qty, entry, stop, signal_time, quotes=None):
        if market not in MICRO_POINT_VALUE or side not in ("LONG","SHORT"):
            return Admission(False,"INVALID_MARKET_OR_SIDE")
        if not isinstance(signal_time, datetime) or signal_time.tzinfo is None:
            return Admission(False,"UTC_AWARE_TIMESTAMP_REQUIRED")
        ny = signal_time.astimezone(NY)
        # CME Sunday reopen at 18:00 NY; weekday daily trading until 16:45.
        d = ny.weekday()  # Monday=0, Sunday=6
        valid = ((d in (0,1,2,3) and (ny.time() < time(16,45) or ny.time() >= time(18))) or
                 (d == 4 and ny.time() < time(16,45)) or
                 (d == 6 and ny.time() >= time(18)))
        if not valid or ny.time() >= self.rules.new_entry_cutoff and ny.time() < time(18):
            return Admission(False,"CLOSED_OR_PRE_FLATTEN")
        if self.breached or self.locked:
            return Admission(False,"ACCOUNT_LOCKED")
        if quotes:
            reason = self._limits(self.mark(quotes))
            if reason: return Admission(False,reason)
        if self.balance <= self.mll_floor:
            return Admission(False,"MAX_LOSS_BREACH")
        if any(p.market == market and p.side != side for p in self.positions):
            return Admission(False,"OPPOSITE_SIDE_SAME_MARKET")
        if desired_qty < 1: return Admission(False,"INVALID_QUANTITY")
        risk_one = abs(entry-stop)*MICRO_POINT_VALUE[market]
        if risk_one <= 0: return Admission(False,"INVALID_STOP")
        if (side=="LONG" and stop >= entry) or (side=="SHORT" and stop <= entry):
            return Admission(False,"INVALID_STOP_SIDE")
        remaining_contracts = self.capacity() - self.open_micros()
        remaining_risk = self.rules.max_open_stop_risk - self.stop_risk()
        # Account-wide drawdown buffer: do not spend risk at/below hard MLL.
        remaining_mll = self.balance - self.mll_floor - self.stop_risk()
        qty = min(int(desired_qty),remaining_contracts,
                  int(self.rules.risk_per_trade//risk_one),
                  int(max(0,remaining_risk)//risk_one),
                  int(max(0,remaining_mll)//risk_one))
        if qty < 1: return Admission(False,"SIZE_OR_RISK_LIMIT")
        return Admission(True,"OK" if qty==desired_qty else "DOWNSIZED",qty)

    def open(self, market, side, desired_qty, entry, stop, strategy, signal_time, quotes=None):
        admission=self.admit(market,side,desired_qty,entry,stop,signal_time,quotes)
        if admission.accepted:
            self.positions.append(Position(market,side,admission.qty,entry,stop,[strategy]))
        return admission

    def close(self, position_index, exit_price, fees=0.0):
        p=self.positions.pop(position_index)
        direction=1 if p.side=="LONG" else -1
        pnl=(exit_price-p.entry)*direction*MICRO_POINT_VALUE[p.market]*p.qty-fees
        self.balance+=pnl
        self._limits(self.balance)
        return pnl

    def end_session(self):
        pnl=self.balance-self.session_start_balance
        self.positive_days.append(pnl)
        self.peak_eod=max(self.peak_eod,self.balance)
        # 25K EOD trailing threshold locks to 25,100 once peak EOD >26,100.
        self.mll_floor=min(25_100.0,self.peak_eod-self.rules.max_loss)
        if self.balance <= self.mll_floor:
            self.breached=True
        if self.phase=="funded":
            gains=self.balance-self.rules.starting_balance
            self.funded_max_micros=(self.rules.funded_scaled_max_micros if gains>=self.rules.funded_scale_profit
                                    else self.rules.funded_initial_max_micros)
        self.session_start_balance=self.balance
        self.locked=self.breached
        return pnl

    def evaluation_passed(self):
        profit=self.balance-self.rules.starting_balance
        if self.phase!="evaluation" or self.breached or profit < self.rules.profit_target: return False
        # LucidFlex 40% consistency: largest positive session cannot exceed 40% of total profit.
        return max((max(0,x) for x in self.positive_days),default=0) <= self.rules.eval_consistency*profit
