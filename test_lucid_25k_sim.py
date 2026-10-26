"""Contract and drawdown tests for the isolated V7 LucidFlex 25K gate."""
import unittest
from datetime import datetime, timezone
from lucid_25k_sim import Lucid25K, AccountRules

# 2026-10-26 14:00 UTC = 10:00 New York
NOW = datetime(2026,10,26,14,0,tzinfo=timezone.utc)

class TestLucid25K(unittest.TestCase):
    def test_eval_caps_total_across_strategies(self):
        a=Lucid25K(AccountRules(risk_per_trade=1000,max_open_stop_risk=2000))
        x=a.open("nq","LONG",16,30000,29995,"engulf",NOW)
        y=a.open("mes","LONG",12,7000,6999,"bounce",NOW)
        self.assertTrue(x.accepted)
        self.assertEqual(y.qty,4)
        self.assertEqual(a.open_micros(),20)
        self.assertFalse(a.open("mgc","LONG",1,4000,3999,"ema",NOW).accepted)
    def test_opposing_same_market_rejected(self):
        a=Lucid25K()
        self.assertTrue(a.open("nq","LONG",3,30000,29995,"engulf",NOW).accepted)
        self.assertEqual(a.open("nq","SHORT",3,30000,30005,"bounce",NOW).reason,
                         "OPPOSITE_SIDE_SAME_MARKET")
    def test_funded_starts_with_ten(self):
        a=Lucid25K(AccountRules(risk_per_trade=2000,max_open_stop_risk=2000),phase="funded")
        self.assertEqual(a.open("nq","LONG",20,30000,29995,"engulf",NOW).qty,10)
        a.balance=26000
        a.end_session()
        self.assertEqual(a.capacity(),20)
    def test_lucid_max_loss_lock(self):
        a=Lucid25K()
        a.balance=24000
        self.assertFalse(a.open("nq","LONG",1,30000,29999,"engulf",NOW).accepted)
    def test_closed_weekend(self):
        a=Lucid25K()
        saturday=datetime(2026,10,31,14,tzinfo=timezone.utc)
        self.assertEqual(a.admit("nq","LONG",1,30000,29999,saturday).reason,
                         "CLOSED_OR_PRE_FLATTEN")
    def test_internal_stop_risk(self):
        a=Lucid25K()
        x=a.open("nq","LONG",10,30000,29995,"engulf",NOW)
        self.assertTrue(x.accepted)
        self.assertEqual(x.qty,10)
        y=a.open("mes","LONG",10,7000,6990,"bounce",NOW)
        self.assertEqual(y.qty,4)
    def test_eval_consistency(self):
        a=Lucid25K()
        a.balance=26250
        a.positive_days=[700,550]
        self.assertFalse(a.evaluation_passed())
        a.positive_days=[400,425,425]
        self.assertTrue(a.evaluation_passed())
if __name__=="__main__":
    unittest.main()
