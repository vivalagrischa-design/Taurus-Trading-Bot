"""Extra V7 account behavior tests. Run: python -m unittest discover -s tests -v"""
import unittest
from datetime import datetime, timezone
from lucid_25k_sim import Lucid25K, AccountRules
from v7_parallel_research import ParallelResearch

NOW=datetime(2026,10,26,14,0,tzinfo=timezone.utc)

class V7IntegrationTests(unittest.TestCase):
    def test_two_hundred_risk_per_trade(self):
        a=Lucid25K()
        self.assertEqual(a.rules.risk_per_trade,200)
        result=a.open("nq","LONG",20,30000,29990,"omar",NOW)
        self.assertEqual(result.qty,10)
        self.assertLessEqual(a.positions[0].planned_risk,200)
    def test_shared_risk_across_strategies(self):
        a=Lucid25K()
        a.open("nq","LONG",10,30000,29990,"omar",NOW)
        r=a.open("mes","LONG",20,7000,6990,"ema",NOW)
        self.assertEqual(r.qty,8)
        self.assertLessEqual(a.stop_risk(),600)
    def test_lab_continues_after_lucid_failure(self):
        x=ParallelResearch()
        x.lucid.balance=23999
        x.signal("omar","nq","LONG",2,30000,29995,NOW)
        x.signal("ema","mes","LONG",2,7000,6999,NOW)
        self.assertEqual(x.report()["research_signals"],2)
        self.assertEqual(x.report()["lucid_accepted"],0)
    def test_trailing_eod_floor(self):
        a=Lucid25K()
        a.balance=26150
        a.end_session()
        self.assertEqual(a.mll_floor,25100)
    def test_weekend_rejected(self):
        a=Lucid25K()
        sat=datetime(2026,10,31,14,tzinfo=timezone.utc)
        self.assertFalse(a.admit("nq","LONG",1,30000,29990,sat).accepted)

if __name__=="__main__":
    unittest.main()
