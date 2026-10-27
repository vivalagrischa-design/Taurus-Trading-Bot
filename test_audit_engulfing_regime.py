import unittest
from audit_engulfing_regime import regime, audit

class RegimeAuditTests(unittest.TestCase):
    def bars(self,trend=True):
        out=[]
        for i in range(45):
            price=100+i*.5 if trend else 100+(i%2)*.5
            out.append(dict(time=i*300,open=price-.1,high=price+.3,
                            low=price-.3,close=price,volume=100))
        return out
    def test_detects_trend_and_chop_from_prior_bars(self):
        a=regime(self.bars(True),35*300)
        b=regime(self.bars(False),35*300)
        self.assertEqual(a['state'],'TREND')
        self.assertEqual(b['state'],'CHOP')
    def test_future_bars_cannot_change_past_regime(self):
        a=self.bars(True)
        before=regime(a,30*300)
        a.extend(dict(time=100000+i*300,open=1,high=1,low=1,close=1,volume=100) for i in range(10))
        self.assertEqual(before,regime(a,30*300))
    def test_missing_candles_report_unknown_not_inferred(self):
        t=dict(strategy='rev_engulfing',status='CLOSED',pnl=-100,
               market='nq',side='SHORT',signal_time=1000,entry=200,
               initial_stop=201,exit_reason='SL')
        result=audit([t],{})
        self.assertFalse(result['market_regime_available'])
        self.assertIsNone(result['trades'][0]['regime'])
if __name__=='__main__':unittest.main()
