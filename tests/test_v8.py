"""V8: Marktlagen-Filter, neue Strategien, Zeit-Ausstieg, Kostenregel, Kerzen-Qualitaet."""
import os
import sqlite3
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backtest as bt
import feed_quality
import paper_engine as pe
import regime_gate
import regime_strategies
from engine import demo_candles


def bar(t, o, h, l, c, v=100):
    return {'time': t, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': v}


class Gate(unittest.TestCase):
    def test_removes_signals_outside_allowed_regime(self):
        bars = demo_candles(300)
        lk = regime_gate.RegimeLookup(bars)
        times = [b['time'] for b in bars[100:]]
        sigs = [{'time': t, 'side': 'SHORT'} for t in times]
        tiles = [{'id': 'omar', 'signals': sigs}, {'id': 'orb5', 'signals': sigs}]
        out = regime_gate.apply(tiles, bars, lk)
        self.assertTrue(all(lk.at(s['time']) == 'TREND_RUNTER' for s in out[0]['signals']))
        self.assertEqual(len(out[1]['signals']), len(sigs))          # orb5 ohne Filter

    def test_can_be_switched_off(self):
        with patch.dict(os.environ, {'TAURUS_REGIME_GATE': 'off'}):
            tiles = [{'id': 'omar', 'signals': [{'time': 1, 'side': 'LONG'}]}]
            self.assertIs(regime_gate.apply(tiles, []), tiles)

    def test_removed_strategies_not_active(self):
        for s in pe.ACTIVE_5M + pe.ACTIVE_1M + pe.ACTIVE_EXTREMES:
            self.assertFalse(s.startswith('rev_') or s.startswith('rosi_') or s == 'trend_pullback', s)


class NewStrategies(unittest.TestCase):
    def test_causal_signals_on_prefix_equal_full_history(self):
        bars = demo_candles(400)
        full = {(t['id'], s['time']) for t in regime_strategies.build(bars) for s in t['signals']}
        for cut in (200, 300, 399):
            pre = {(t['id'], s['time']) for t in regime_strategies.build(bars[:cut + 1]) for s in t['signals']}
            self.assertEqual({x for x in full if x[1] <= bars[cut]['time']}, pre)

    def test_signals_have_stop_on_loss_side_and_valid_target(self):
        for t in regime_strategies.build(demo_candles(400)):
            for s in t['signals']:
                if s['side'] == 'LONG':
                    self.assertLess(s['stop'], s['entry']); self.assertGreater(s['tp'], s['entry'])
                else:
                    self.assertGreater(s['stop'], s['entry']); self.assertLess(s['tp'], s['entry'])


class TimeExitAndCost(unittest.TestCase):
    def test_time_exit_parity_with_paper_engine(self):
        db = sqlite3.connect(':memory:'); db.row_factory = sqlite3.Row
        pe.init_tables(db)
        db.execute("INSERT INTO trades(id,market,strategy,side,status,entry,stop,tp,qty,signal_stop,initial_stop,cost_estimate,"
                   "mfe_usd,mae_usd,entry_time,trail_updates,time_exit) VALUES('t','nq','orb5','LONG','OPEN',100,90,200,2,90,90,0,0,0,0,0,600)")
        bars = [bar(0, 100, 101, 99, 100), bar(300, 100, 102, 99.5, 101), bar(600, 103, 104, 102, 103)]
        for i, b in enumerate(bars):
            pe._close_open(db, 'nq', b, '5m', bars[:i + 1])
        live = dict(db.execute("SELECT exit_reason,exit,pnl FROM trades").fetchone()); db.close()
        t = {'strategy': 'orb5', 'side': 'LONG', 'entry': 100, 'stop': 90, 'tp': 200, 'signal_stop': 90, 'qty': 2,
             'trail_updates': 0, 'mfe_r': 0.0, 'mae_r': 0.0, 'entry_time': 0, 'time_exit': 600}
        for b in bars:
            if bt._manage(t, b, 'nq'):
                break
        self.assertEqual(live['exit_reason'], 'TIME'); self.assertEqual(t['exit_reason'], 'TIME')
        self.assertAlmostEqual(t['pnl'], live['pnl'], places=4)
        self.assertEqual(t['exit'], 103 - 0.25)

    def test_cost_rule_cancels_tight_stops(self):
        self.assertGreater(pe.cost_share(100.25, 99.25, 'nq'), pe.MAX_COST_SHARE)
        self.assertLess(pe.cost_share(100.25, 80, 'nq'), pe.MAX_COST_SHARE)
        t = {'id': 'x', 'market': 'nq', 'strategy': 'omar', 'side': 'LONG', 'signal_time': 0,
             'signal_entry': 100, 'signal_stop': 99, 'signal_tp': 102, 'status': 'PENDING'}
        self.assertEqual(bt._open(t, bar(300, 100, 100, 100, 100), 'nq'), 'COST_TOO_HIGH')


class Quality(unittest.TestCase):
    def test_only_frozen_bars_removed_by_default(self):
        bars = [bar(0, 1, 2, 0.5, 1.5, 0), bar(60, 1.5, 1.5, 1.5, 1.5, 0), bar(120, 1.5, 2, 1, 1.8, 10)]
        self.assertEqual([b['time'] for b in feed_quality.clean(bars, 'frozen')], [0, 120])
        self.assertEqual([b['time'] for b in feed_quality.clean(bars, 'all')], [120])
        self.assertEqual(len(feed_quality.clean(bars, 'none')), 3)


class CandleStudy(unittest.TestCase):
    def test_runs_and_reports_baseline(self):
        import candle_study as cs
        items = cs.summarize(cs.study({'nq': demo_candles(400)}))
        self.assertTrue(any(x['pattern'] == 'ALLE_KERZEN' for x in items))
        for x in items:
            self.assertLessEqual(x['p_up'] + x['p_down'], 1.0 + 1e-9)


if __name__ == '__main__':
    unittest.main()
