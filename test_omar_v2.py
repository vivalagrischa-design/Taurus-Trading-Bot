"""Omar V2 regression: breakout volume, confirmed retest and no lookahead."""
import unittest
from unittest.mock import patch
from omar_v2 import _hours,_pivots,signals,build,KEY

class OmarV2Tests(unittest.TestCase):
    def bars(self):
        bars=[]
        for i in range(160):
            bars.append(dict(time=i*300,open=100.,high=101.,low=99.,close=100.,volume=100.))
        bars[155].update(open=100.,high=104.,low=100.,close=103.,volume=200.)
        bars[156].update(open=101.2,high=103.,low=100.8,close=102.,volume=100.)
        return bars

    def test_requires_completed_retest_after_breakout(self):
        bars=self.bars()
        with patch('omar_v2._uptrend',return_value=True):
            self.assertEqual(signals(bars[:156],'nq'),[])
            sig=signals(bars[:157],'nq')
        self.assertEqual(len(sig),1)
        self.assertEqual(sig[0]['time'],bars[156]['time'])
        self.assertEqual(sig[0]['side'],'LONG')
        self.assertEqual(sig[0]['strategy'],KEY)
        self.assertEqual(sig[0]['timeframe'],'5m')
        self.assertAlmostEqual((sig[0]['tp']-sig[0]['entry'])/(sig[0]['entry']-sig[0]['stop']),2.,places=3)

    def test_volume_filter_rejects_weak_breakout(self):
        bars=self.bars();bars[155]['volume']=120
        with patch('omar_v2._uptrend',return_value=True):
            self.assertEqual(signals(bars,'nq'),[])

    def test_no_uptrend_rejects_breakout(self):
        self.assertEqual(signals(self.bars(),'nq'),[])

    def test_incomplete_hour_is_ignored(self):
        bars=self.bars()[:13]
        self.assertEqual(len(_hours(bars)),1)
        del bars[5]
        self.assertEqual(_hours(bars),[])

    def test_pivots_require_two_future_completed_hour_bars(self):
        hours=[dict(high=h,low=l) for h,l in [(10,1),(11,2),(14,0),(12,2),(11,3)]]
        hi,lo=_pivots(hours)
        self.assertEqual(hi,[14])
        self.assertEqual(lo,[0])

    def test_ui_strategy_id(self):
        self.assertEqual(build(self.bars(),'mes')['id'],KEY)

if __name__=='__main__':unittest.main()
