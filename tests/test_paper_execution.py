"""Regression checks for the paper execution rules (python -m unittest discover -s tests)."""
import sqlite3
import unittest
from unittest.mock import patch
import paper_engine as pe


def memory_db():
    db=sqlite3.connect(":memory:")
    db.row_factory=sqlite3.Row
    db.execute("""CREATE TABLE trades(
      id TEXT,market TEXT,strategy TEXT,side TEXT,status TEXT,
      entry REAL,stop REAL,tp REAL,qty REAL,signal_stop REAL,
      cost_estimate REAL,mfe_usd REAL,mae_usd REAL,entry_time INTEGER,
      trail_updates INTEGER,scale_legs INTEGER,scale_pending INTEGER,
      last_leg_price REAL,initial_stop REAL,exit_time INTEGER,exit REAL,
      pnl REAL,exit_reason TEXT,stop_net_estimate REAL,break_even_stop REAL,
      risk_plan REAL,exit_context TEXT,exit_reference REAL,exit_slippage_usd REAL,
      gross_pnl REAL,fees_paid REAL)""")
    return db


def add(db,side="LONG",stop=98,tp=104,strategy="ema20"):
    db.execute("""INSERT INTO trades(id,market,strategy,side,status,entry,stop,tp,qty,
    signal_stop,cost_estimate,mfe_usd,mae_usd,entry_time,trail_updates,scale_legs,
    scale_pending,last_leg_price,initial_stop)
    VALUES ('t','btc',?,?,'OPEN',100,?,?,1,?,0,0,0,1000,0,1,0,100,?)""",
    (strategy,side,stop,tp,stop,stop))


class PaperExitTests(unittest.TestCase):
    def test_take_profit_long(self):
        db=memory_db();add(db)
        pe._close_open(db,"btc",dict(time=1300,open=100,high=105,low=99,close=104),"5m")
        r=dict(db.execute("SELECT * FROM trades").fetchone())
        self.assertEqual(r["status"],"CLOSED")
        self.assertEqual(r["exit_reason"],"TP")
        self.assertGreater(r["pnl"],0)
    def test_short_take_profit(self):
        db=memory_db();add(db,side="SHORT",stop=102,tp=96)
        pe._close_open(db,"btc",dict(time=1300,open=100,high=101,low=95,close=96),"5m")
        r=dict(db.execute("SELECT * FROM trades").fetchone())
        self.assertEqual(r["exit_reason"],"TP")
        self.assertGreater(r["pnl"],0)
    def test_simultaneous_stop_and_target_is_stop(self):
        db=memory_db();add(db)
        pe._close_open(db,"btc",dict(time=1300,open=100,high=105,low=97,close=103),"5m")
        self.assertEqual(db.execute("SELECT exit_reason FROM trades").fetchone()[0],"SL")
    def test_trailing_cannot_move_backward(self):
        db=memory_db();add(db,stop=98,tp=110)
        pe._close_open(db,"btc",dict(time=1300,open=100,high=103,low=99,close=103),"5m")
        first=db.execute("SELECT stop FROM trades").fetchone()[0]
        self.assertGreater(first,98)
        pe._close_open(db,"btc",dict(time=1600,open=103,high=103.5,low=first+0.1,close=102.5),"5m")
        self.assertAlmostEqual(db.execute("SELECT stop FROM trades").fetchone()[0],first)
    def test_net_break_even_is_beyond_entry(self):
        self.assertGreater(pe._net_break_even_stop(100,"LONG","btc"),100)
        self.assertLess(pe._net_break_even_stop(100,"SHORT","btc"),100)
    def test_scale_requires_adverse_fill(self):
        db=memory_db();add(db,side="SHORT",stop=105,tp=98,strategy="bb_rsi_scale")
        db.execute("UPDATE trades SET scale_pending=1 WHERE id='t'")
        pe._add_scaled_legs(db,"btc",dict(open=99,time=1300),"5m")
        r=db.execute("SELECT scale_legs,scale_pending FROM trades").fetchone()
        self.assertEqual((r[0],r[1]),(1,0))


if __name__=="__main__":
    unittest.main()
