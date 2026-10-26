import unittest
from datetime import datetime,timezone
from v7_session_policy import SessionGate,SessionRules

class SessionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.rules=SessionRules(lucid_strategies=("rev_engulfing","rev_bounce"),
                                morning_profit_lock_usd=None)
        self.g=SessionGate(self.rules)
    def test_dst_october_cash_open_1430_swiss(self):
        # 26 Oct 2026: CH CET while NY EDT, so 14:30 CH is 09:30 NY
        self.assertEqual(self.g.decision("rev_engulfing",
            datetime(2026,10,26,13,30,tzinfo=timezone.utc)).reason,"OPENING_PAUSE")
    def test_later_reopen(self):
        self.assertTrue(self.g.decision("rev_engulfing",
            datetime(2026,10,26,16,30,tzinfo=timezone.utc)).allow)
    def test_lab_unrestricted(self):
        self.assertTrue(self.g.decision("rev_pinbar",
            datetime(2026,10,26,13,30,tzinfo=timezone.utc),book="lab").allow)
    def test_shortlist(self):
        self.assertEqual(self.g.decision("rev_pinbar",
            datetime(2026,10,26,16,30,tzinfo=timezone.utc)).reason,"STRATEGY_NOT_SELECTED")
    def test_profit_lock_is_realized_and_does_not_autoreopen(self):
        g=SessionGate(SessionRules(lucid_strategies=("rev_engulfing",),
                                  morning_profit_lock_usd=500))
        g.start_session("2026-10-26")
        g.register_closed_trade(300)
        self.assertTrue(g.decision("rev_engulfing",datetime(2026,10,26,16,30,
                           tzinfo=timezone.utc)).allow)
        g.register_closed_trade(201)
        self.assertEqual(g.decision("rev_engulfing",datetime(2026,10,26,16,30,
                           tzinfo=timezone.utc)).reason,"PROFIT_LOCK")
        g.start_session("2026-10-27")
        self.assertTrue(g.decision("rev_engulfing",datetime(2026,10,27,16,30,
                           tzinfo=timezone.utc)).allow)
    def test_flatten_explicit_only(self):
        g=SessionGate(SessionRules(lucid_strategies=("rev_engulfing",),
                  pause_position_policy="flatten"))
        r=g.decision("rev_engulfing",datetime(2026,10,26,13,30,tzinfo=timezone.utc))
        self.assertTrue(r.request_flatten)
        self.assertFalse(SessionGate(self.rules).decision("rev_engulfing",
            datetime(2026,10,26,13,30,tzinfo=timezone.utc)).request_flatten)
if __name__=="__main__": unittest.main()
