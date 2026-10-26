"""TAURUS V7: independent unlimited strategy research plus a strict Lucid shadow account.

Run BOTH books on the same incoming signal feed, never on a real brokerage.
A blown Lucid 25K evaluation is permanently FAILED for that attempt. Research
continues independently and never presents post-failure trades as Lucid-eligible.
"""
from dataclasses import dataclass, field
from typing import Optional
from lucid_25k_sim import Lucid25K, AccountRules

@dataclass
class ResearchTrade:
    strategy: str
    market: str
    side: str
    requested_qty: int
    entry: float
    stop: float
    opened_at: object
    pnl: Optional[float] = None

@dataclass
class ReplayStatus:
    research_trades: list[ResearchTrade] = field(default_factory=list)
    rejected_lucid: list[dict] = field(default_factory=list)
    passed_lucid: list[dict] = field(default_factory=list)

class ParallelResearch:
    def __init__(self, lucid=None):
        self.lucid = lucid or Lucid25K(AccountRules(),phase="evaluation")
        self.status = ReplayStatus()

    def signal(self,strategy,market,side,qty,entry,stop,at,quotes=None):
        # LAB: archive every proposed entry; no daily stop, no $1000 max-loss.
        # The independent strategy backtester is responsible for its own fills.
        self.status.research_trades.append(
            ResearchTrade(strategy,market,side,qty,entry,stop,at)
        )
        # LUCID: immutable account rules; disqualified accounts never reopen.
        admit=self.lucid.open(market,side,qty,entry,stop,strategy,at,quotes)
        record=dict(strategy=strategy,market=market,side=side,
                    requested_qty=qty,admitted_qty=admit.qty,reason=admit.reason)
        (self.status.passed_lucid if admit.accepted else self.status.rejected_lucid).append(record)
        return admit

    @property
    def evaluation_breached(self):
        return self.lucid.breached

    def report(self):
        return dict(research_signals=len(self.status.research_trades),
                    lucid_accepted=len(self.status.passed_lucid),
                    lucid_rejected=len(self.status.rejected_lucid),
                    lucid_balance=self.lucid.balance,
                    lucid_breached=self.lucid.breached)
