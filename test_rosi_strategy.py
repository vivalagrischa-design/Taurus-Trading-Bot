import unittest
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch
from rosi_strategy import build,_previous_levels,SESSIONS
from lucid_executor import SELECTED
NY=ZoneInfo('America/New_York')
UTC=timezone.utc

class RosiLabTests(unittest.TestCase):
    def bars(self):
        start=datetime(2026,10,26,22,tzinfo=UTC)
        end=datetime(2026,10,28,12,20,tzinfo=UTC)
        bars=[];now=start
        while now<=end:
            ny=now.astimezone(NY)
            if ny.hour!=17:
                prior=now<datetime(2026,10,27,21,tzinfo=UTC)
                bars.append(dict(time=int(now.timestamp()),open=100.,
                   high=110. if prior else 105.,low=90. if prior else 95.,
                   close=100.,volume=100))
            now+=timedelta(minutes=5)
        return bars

    def test_three_independent_local_sessions(self):
        bars=self.bars()
        for when in (datetime(2026,10,28,7,tzinfo=UTC),
                     datetime(2026,10,28,8,tzinfo=UTC),
                     datetime(2026,10,28,12,tzinfo=UTC)):
            ts=int(when.timestamp())
            ix=next(i for i,b in enumerate(bars) if b['time']==ts)
            bars[ix].update(open=109.,high=111.,low=104.,close=109.)
            bars[ix+1].update(open=109.,high=109.5,low=107.,close=108.)
        tiles={t['id']:t for t in build(bars,'nq')}
        self.assertEqual(set(tiles),set(SESSIONS))
        for key in SESSIONS:
            sigs=tiles[key]['signals']
            self.assertEqual(len(sigs),1,(key,sigs))
            sig=sigs[0]
            self.assertEqual(sig['side'],'SHORT')
            self.assertEqual(sig['stop'],111.25)
            self.assertEqual(sig['tp'],90.)
            self.assertEqual(sig['timeframe'],'5m')

    def test_no_signal_without_completed_previous_session(self):
        bars=self.bars()
        bars=[b for b in bars if b['time']!=int(datetime(2026,10,27,20,55,tzinfo=UTC).timestamp())]
        self.assertTrue(all(not t['signals'] for t in build(bars,'nq')))

    def test_no_lookahead_into_current_day_levels(self):
        bars=self.bars()
        ix=next(i for i,b in enumerate(bars) if b['time']==int(datetime(2026,10,28,7,tzinfo=UTC).timestamp()))
        base=_previous_levels(bars)[ix]
        bars[-1]['high']=9999
        self.assertEqual(_previous_levels(bars)[ix],base)

    def test_sweep_requires_confirmed_followup(self):
        bars=self.bars()
        ix=next(i for i,b in enumerate(bars) if b['time']==int(datetime(2026,10,28,7,tzinfo=UTC).timestamp()))
        bars[ix].update(open=109,high=111,low=104,close=109)
        self.assertTrue(all(not t['signals'] for t in build(bars[:ix+1],'nq')))
        bars[ix+1].update(open=109,high=109.5,low=107,close=108)
        self.assertEqual(len(build(bars[:ix+2],'nq')[0]['signals']),1)

    def test_lucid_winners_only(self):
        self.assertEqual(set(SELECTED),{'rev_engulfing','rev_bounce','trend_pullback','bb_only_short'})
        self.assertFalse(any(s.startswith('rosi') for s in SELECTED))

if __name__=='__main__':unittest.main()
