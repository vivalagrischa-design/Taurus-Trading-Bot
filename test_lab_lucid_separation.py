"""Regression tests: LAB never inherits Lucid's shared 20-micro cap."""
import os
import tempfile
import unittest
from datetime import datetime, timezone

class LabVsLucidTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=os.environ.get('TAURUS_DB_PATH')
        os.environ['TAURUS_DB_PATH']=self.tmp.name+'/test.sqlite'
        import paper_engine
        self.engine=paper_engine
        self.old_db=paper_engine.DB
        paper_engine.DB=os.environ['TAURUS_DB_PATH']

    def tearDown(self):
        self.engine.DB=self.old_db
        if self.old is None:os.environ.pop('TAURUS_DB_PATH',None)
        else:os.environ['TAURUS_DB_PATH']=self.old
        self.tmp.cleanup()

    def test_lab_can_open_more_than_twenty_micros_without_lucid_gate(self):
        p=self.engine
        stamp=int(datetime(2026,10,26,15,0,tzinfo=timezone.utc).timestamp())
        with p.conn() as db:
            for n in range(2):
                db.execute("""INSERT INTO trades
                    (id,market,strategy,side,signal_time,signal_stop,signal_tp,status,timeframe)
                    VALUES(?,?,?,?,?,?,?,'PENDING','5m')""",
                    (f'lab-{n}','mgc','rev_engulfing','LONG',stamp-300,100.,105.))
            bars=[{'time':stamp-300+i*300,'open':100.,'high':100.3,
                   'low':99.9,'close':100.2,'volume':100} for i in range(20)]
            bars[-1]['time']=stamp
            p._open_pending(db,'mgc',bars[-1],bars,'5m')
            trades=db.execute("SELECT qty,risk_plan,status FROM trades WHERE id LIKE 'lab-%'").fetchall()
            self.assertEqual(len(trades),2)
            self.assertTrue(all(x['status']=='OPEN' for x in trades),trades)
            self.assertTrue(all(x['qty']>20 for x in trades),trades)
            self.assertTrue(all(x['risk_plan']<=p.RISK+1e-6 for x in trades),trades)

    def test_lucid_executor_still_enforces_shared_contract_cap(self):
        import lucid_executor
        p=self.engine
        stamp=int(datetime(2026,10,26,15,0,tzinfo=timezone.utc).timestamp())
        with p.conn() as db:
            lucid_executor.setup(db)
            for n in range(2):
                db.execute("""INSERT INTO lucid_orders
                    (id,market,strategy,side,signal_time,stop,tp,status,qty)
                    VALUES(?,?,?,?,?,?,?,'PENDING',0)""",
                    (f'lucid-{n}','mgc','rev_engulfing','LONG',stamp-300,100.,105.))
            bar={'time':stamp,'open':100.,'high':100.3,'low':99.9,'close':100.2}
            for n in range(2):
                row=db.execute("SELECT * FROM lucid_orders WHERE id=?",(f'lucid-{n}',)).fetchone()
                lucid_executor._open(db,row,bar)
            rows=db.execute("SELECT qty,status FROM lucid_orders WHERE id LIKE 'lucid-%'").fetchall()
            total=sum(int(r['qty']) for r in rows if r['status']=='OPEN')
            self.assertLessEqual(total,lucid_executor.MAX_QTY)
            self.assertGreater(total,0)

if __name__=='__main__':
    unittest.main()
