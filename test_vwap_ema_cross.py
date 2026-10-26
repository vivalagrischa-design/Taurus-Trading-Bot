import unittest
from datetime import datetime, timezone
from vwap_ema_cross import to_3m, detect, build, STRATEGY, _session

class TestVWAPEMA(unittest.TestCase):
    def setUp(self):
        self.start=int(datetime(2026,10,26,12,0,tzinfo=timezone.utc).timestamp())
    def make(self,closes):
        bars=[]
        for i,price in enumerate(closes):
            for m in range(3):
                t=self.start+i*180+m*60
                bars.append({'time':t,'open':price,'high':price+.5,
                             'low':price-.5,'close':price,'volume':100})
        return bars
    def test_aggregation_only_complete_consecutive(self):
        b=self.make([100,101,102]); self.assertEqual(len(to_3m(b)),3)
        del b[4]; self.assertEqual(len(to_3m(b)),2)
        b.append(b[0]);self.assertEqual(len(to_3m(b)),1)
    def test_no_signal_without_volume(self):
        b=self.make([100]*25+[102]*4)
        for bar in b:bar['volume']=0
        self.assertEqual(detect(to_3m(b),ema_period=3),[])
    def test_long_cross_on_closed_candle(self):
        b=self.make([100]*20+[99]*5+[110]*5)
        s=detect(to_3m(b),ema_period=5)
        self.assertTrue(any(x['side']=='LONG' for x in s),s)
        long=next(x for x in s if x['side']=='LONG')
        self.assertEqual(long['timeframe'],'3m')
        self.assertEqual(long['strategy'],STRATEGY)
        self.assertAlmostEqual((long['tp']-long['entry'])/(long['entry']-long['stop']),1.5)
    def test_no_last_partial_bar(self):
        b=self.make([100]*20+[99]*5+[110]*5)
        self.assertEqual(to_3m(b[:-2])[-1]['time'],self.start+28*180)
        self.assertEqual(detect(to_3m(b[:-2]),ema_period=5),detect(to_3m(b[:-3]),ema_period=5))
    def test_ny_session_reset_at_18h(self):
        old=int(datetime(2026,10,26,21,0,tzinfo=timezone.utc).timestamp())
        new=int(datetime(2026,10,26,22,0,tzinfo=timezone.utc).timestamp())
        self.assertNotEqual(_session(old),_session(new))
    def test_display(self):
        tile=build(self.make([100]*25),market='mes')
        self.assertEqual(tile['id'],STRATEGY)
        self.assertIn('3M',tile['name'])
if __name__=='__main__':unittest.main()
