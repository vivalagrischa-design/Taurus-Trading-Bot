"""Regression for daily read-only research archive and run isolation."""
import tempfile,unittest
from datetime import datetime,timezone
from unittest.mock import patch
import paper_engine
from daily_archive import daily_snapshot

class DailyArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old=paper_engine.DB
        paper_engine.DB=self.temp.name+'/research.db'
    def tearDown(self):
        paper_engine.DB=self.old
        self.temp.cleanup()
    def test_empty_day_has_schema_and_versions(self):
        data=daily_snapshot('2026-10-27')
        self.assertEqual(data['day_swiss'],'2026-10-27')
        self.assertEqual(data['schema_version'],1)
        self.assertEqual(data['lab']['risk_usd'],200)
        self.assertEqual(data['counts']['lab_trades'],0)
        self.assertEqual(data['counts']['lucid_orders'],0)
        self.assertTrue(data['day_end_utc']>data['day_start_utc'])
    def test_candle_and_signal_included_only_on_selected_day(self):
        ts=int(datetime(2026,10,27,12,tzinfo=timezone.utc).timestamp())
        with paper_engine.conn() as db:
            db.execute("""INSERT INTO market_candles(system,run_id,market,timeframe,bar_time,open,high,low,close,volume,source)
               VALUES('lab','run','nq','5m',?,1,2,0,1,10,'test')""",(ts,))
            db.execute("""INSERT INTO signal_log(id,market,strategy,side,signal_time,decision,reason)
               VALUES('one','nq','ema20','LONG',?,'PENDING','test')""",(ts,))
        selected=daily_snapshot('2026-10-27')
        prior=daily_snapshot('2026-10-26')
        self.assertEqual(selected['counts']['candles'],1)
        self.assertEqual(selected['counts']['lab_signals'],1)
        self.assertEqual(prior['counts']['candles'],0)
        self.assertEqual(prior['counts']['lab_signals'],0)
    def test_reject_future_day(self):
        with self.assertRaises(ValueError):
            daily_snapshot('2999-01-01')
if __name__=='__main__':unittest.main()
