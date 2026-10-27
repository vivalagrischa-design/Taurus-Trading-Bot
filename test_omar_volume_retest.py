import unittest
from datetime import datetime, timezone
from omar_volume_retest import hourly_complete, _trend_up, _breakout, _signal, build

class OmarVolumeRetestTests(unittest.TestCase):
    def make(self,n=150):
        t=int(datetime(2026,10,23,0,0,tzinfo=timezone.utc).timestamp())
        return [dict(time=t+i*300,open=100,high=101,low=99,close=100,volume=100) for i in range(n)]
    def test_only_complete_hours(self):
        bars=self.make(25)
        self.assertEqual(len(hourly_complete(bars)),2)
        del bars[3]
        self.assertEqual(len(hourly_complete(bars)),1)
    def test_no_hourly_trend_no_signal(self):
        bars=self.make(150)
        bars[-1]['volume']=1000
        self.assertFalse(_breakout(bars,149,hourly_complete(bars)))
        self.assertIsNone(_signal(bars,149,hourly_complete(bars),'nq'))
    def test_tile_is_separate_from_original_omar(self):
        t=build(self.make(150),'nq')
        self.assertEqual(t['id'],'omar_volume_retest')
        self.assertEqual(t['signals'],[])
    def test_zero_volume_not_breakout(self):
        bars=self.make(150)
        bars[-1]['volume']=0
        self.assertEqual(_breakout(bars,149,hourly_complete(bars)),[])
if __name__=='__main__':unittest.main()
