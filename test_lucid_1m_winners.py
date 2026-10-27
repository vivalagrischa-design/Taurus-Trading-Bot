"""Ensure Lucid's selected 1M BB_ONLY_SHORT actually generates paper orders."""
import os,tempfile,unittest
from datetime import datetime,timezone
from unittest.mock import patch
import paper_engine,lucid_executor

class LucidOneMinuteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=paper_engine.DB
        paper_engine.DB=self.tmp.name+'/test.db'
    def tearDown(self):
        paper_engine.DB=self.old
        self.tmp.cleanup()
    def bars(self,n):
        start=int(datetime(2026,10,27,6,40,tzinfo=timezone.utc).timestamp())
        return [dict(time=start+i*60,open=100.,high=100.5,low=99.5,close=100.,volume=100) for i in range(n)]
    def test_selected_one_minute_winner_gets_order_and_fill(self):
        bars=self.bars(321)
        target=bars[-1]['time']+60
        def fake_build(seq):
            t=seq[-1]['time']
            signals=[dict(time=t,side='SHORT',stop=101.,tp=98.)] if t==target else []
            return [dict(id='bb_only_short',signals=signals)]
        with patch('bb_rsi.build',side_effect=fake_build):
            first=lucid_executor.advance('nq',bars,'1m')
            self.assertIn('first observation',first['reason'])
            lucid_executor.advance('nq',self.bars(322),'1m')
            with paper_engine.conn() as db:
                row=db.execute("SELECT status,timeframe FROM lucid_orders WHERE strategy='bb_only_short'").fetchone()
                self.assertEqual((row['status'],row['timeframe']),('PENDING','1m'))
            lucid_executor.advance('nq',self.bars(323),'1m')
            with paper_engine.conn() as db:
                row=db.execute("SELECT status,qty FROM lucid_orders WHERE strategy='bb_only_short'").fetchone()
                self.assertEqual(row['status'],'OPEN')
                self.assertGreater(row['qty'],0)
                self.assertLessEqual(row['qty'],20)
    def test_lucid_5m_does_not_touch_one_minute_orders(self):
        bars=self.bars(321)
        lucid_executor.advance('nq',bars,'1m')
        with paper_engine.conn() as db:
            lucid_executor.setup(db)
            db.execute("""INSERT INTO lucid_orders(id,market,strategy,side,signal_time,stop,tp,status,qty,timeframe)
              VALUES('bb1','nq','bb_only_short','SHORT',0,101,98,'PENDING',0,'1m')""")
        five=[dict(b,time=b['time']+300*i) for i,b in enumerate(bars[:76])]
        lucid_executor.advance('nq',five,'5m')
        with paper_engine.conn() as db:
            row=db.execute("SELECT status FROM lucid_orders WHERE id='bb1'").fetchone()
            self.assertEqual(row['status'],'PENDING')
if __name__=='__main__':unittest.main()
