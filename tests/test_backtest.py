"""Backtest und Simulation (python -m unittest discover -s tests)."""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backtest as bt
import paper_engine as pe
import sim
from engine import demo_candles


def bar(t, o, h, l, c):
    return {'time': t, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': 100}


def pending(strategy='ema20', side='LONG', entry=100.0, stop=90.0, tp=120.0, t=0):
    return {'id': 'x', 'market': 'nq', 'strategy': strategy, 'engine': '5m', 'side': side, 'signal_time': t,
            'signal_entry': entry, 'signal_stop': stop, 'signal_tp': tp, 'status': 'PENDING'}


class ExecutionRules(unittest.TestCase):
    def opened(self, **kw):
        t = pending(**kw)
        self.assertIsNone(bt._open(t, bar(300, 100, 100, 100, 100), 'nq'))
        return t

    def test_entry_next_open_with_one_tick_and_risk_sizing(self):
        t = self.opened()
        self.assertEqual(t['entry'], 100.25)                     # 1 Tick Slippage
        rpu = (100.25 - 90) * 2 + 1 + 0.25 * 2
        self.assertEqual(t['qty'], int(200 // rpu))
        self.assertLessEqual(t['risk_plan'], 200)

    def test_gap_beyond_stop_cancels(self):
        t = pending()
        self.assertEqual(bt._open(t, bar(300, 89, 89, 89, 89), 'nq'), 'GAP_INVALID')

    def test_stop_wins_when_both_inside_one_bar(self):
        t = self.opened()
        self.assertTrue(bt._manage(t, bar(600, 100, 130, 80, 110), 'nq'))
        self.assertEqual(t['exit_reason'], 'SL')
        self.assertLess(t['pnl'], 0)

    def test_gap_through_stop_fills_at_open(self):
        t = self.opened()
        bt._manage(t, bar(600, 85, 86, 84, 85), 'nq')
        self.assertEqual(t['exit'], 85 - 0.25)

    def test_trailing_arms_at_one_r_and_acts_next_bar(self):
        t = self.opened()
        r0 = 100.25 - 90
        self.assertFalse(bt._manage(t, bar(600, 101, 111, 100.5, 110.5), 'nq'))   # +1R auf Schluss
        self.assertAlmostEqual(t['stop'], 110.5 - r0)
        self.assertTrue(bt._manage(t, bar(900, 110, 110, 99, 99), 'nq'))
        self.assertEqual(t['exit_reason'], 'TRAIL')
        self.assertAlmostEqual(t['exit'], 110.5 - r0 - 0.25)     # Trailing-Stop minus 1 Tick, nicht der alte Stop

    def test_no_trailing_for_rev_bounce(self):
        t = self.opened(strategy='rev_bounce')
        bt._manage(t, bar(600, 101, 111, 100.5, 110.5), 'nq')
        self.assertEqual(t['stop'], 90.0)

    def test_one_position_per_strategy(self):
        bars = [bar(i * 300, 100, 100.5, 99.5, 100) for i in range(100)]
        sigs = [dict(strategy='ema20', engine='5m', side='LONG', time=80 * 300, entry=100, stop=80, tp=140),
                dict(strategy='ema20', engine='5m', side='LONG', time=81 * 300, entry=100, stop=80, tp=140)]
        trades = bt.execute('nq', bars, sigs, '5m')
        self.assertEqual(len(trades), 1)


class ParityWithPaperEngine(unittest.TestCase):
    """Gleiche Kerzen -> gleiches Ergebnis wie paper_engine._close_open."""

    def live_result(self, bars, side, entry, stop, tp, strategy):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        pe.init_tables(db)
        qty = 3
        db.execute("INSERT INTO trades(id,market,strategy,side,status,entry,stop,tp,qty,signal_stop,initial_stop,"
                   "cost_estimate,mfe_usd,mae_usd,entry_time,trail_updates) VALUES('t','nq',?,?,'OPEN',?,?,?,?,?,?,0,0,0,?,0)",
                   (strategy, side, entry, stop, tp, qty, stop, stop, bars[0]['time']))
        for i, b in enumerate(bars):
            pe._close_open(db, 'nq', b, '5m', bars[:i + 1])
        row = dict(db.execute("SELECT exit_reason,exit,pnl FROM trades WHERE id='t'").fetchone())
        db.close()
        return row

    def check(self, bars, side, strategy='ema20'):
        entry, stop, tp = (100.0, 95.0, 110.0) if side == 'LONG' else (100.0, 105.0, 90.0)
        live = self.live_result(bars, side, entry, stop, tp, strategy)
        t = {'strategy': strategy, 'side': side, 'entry': entry, 'stop': stop, 'tp': tp, 'signal_stop': stop,
             'qty': 3, 'trail_updates': 0, 'mfe_r': 0.0, 'mae_r': 0.0, 'entry_time': bars[0]['time']}
        for b in bars:
            if bt._manage(t, b, 'nq'):
                break
        self.assertEqual(t['exit_reason'].replace('TRAIL', 'SL'), live['exit_reason'])
        self.assertAlmostEqual(t['pnl'], live['pnl'], places=4)

    def test_long_target(self):
        self.check([bar(0, 100, 101, 99, 100), bar(300, 100, 104, 99, 103), bar(600, 103, 111, 102, 110)], 'LONG')

    def test_short_trailing_stop(self):
        self.check([bar(0, 100, 101, 99, 100), bar(300, 99, 99.5, 94, 94.5), bar(600, 95, 101, 94, 100)], 'SHORT')

    def test_long_gap_stop(self):
        self.check([bar(0, 100, 101, 99, 100), bar(300, 93, 94, 92, 93)], 'LONG')


class Signals(unittest.TestCase):
    def test_window_pass_equals_single_evaluate_on_short_history(self):
        from strategies import evaluate
        bars = demo_candles(400)
        mine = {(s['strategy'], s['time'], s['side']) for s in bt.generate_signals('nq', bars, [])}
        ref = {(st['id'], int(s['time']), s['side']) for st in evaluate(bars, market='nq') if st['id'] in pe.ACTIVE_5M
               for s in st['signals'] if s.get('side') in ('LONG', 'SHORT')}
        self.assertEqual(mine, ref)

    def test_run_produces_regime_tagged_trades(self):
        bars = demo_candles(400)
        trades, _ = bt.run(['nq'], {('nq', '5m'): bars}, audit_samples=0)
        closed = [t for t in trades if t['status'] == 'CLOSED']
        self.assertTrue(closed)
        for t in closed:
            self.assertIn(t['regime'], ('TREND_HOCH', 'TREND_RUNTER', 'RANGE', 'CHOP', 'UEBERGANG', 'UNBEKANNT'))
            self.assertAlmostEqual(t['r'], t['pnl'] / t['risk_plan'])
        s = bt.summarize(trades)
        self.assertEqual(s['closed'], len(closed))
        self.assertIn('# TAURUS Backtest', bt.markdown(s, {'source': 't', 'from': 'a', 'to': 'b', 'markets': ['nq']}, {}))


class Simulation(unittest.TestCase):
    def test_bootstrap_is_reproducible_and_sane(self):
        a = sim.bootstrap_trades([1.0, -1.0, 2.0], 50, 2000, seed=3)
        b = sim.bootstrap_trades([1.0, -1.0, 2.0], 50, 2000, seed=3)
        self.assertEqual(a, b)
        self.assertGreater(a['p_positive'], 0.9)
        self.assertEqual(sim.bootstrap_trades([-1.0], 10, 100)['p_positive'], 0)

    def test_lucid_pass_and_fail(self):
        self.assertEqual(sim.lucid_pass([400.0], runs=100)['p_pass'], 1.0)
        self.assertEqual(sim.lucid_pass([-200.0], runs=100)['p_fail'], 1.0)
        # Trailing: +900 dann -1000 -> Grenze bei -100 erreicht, Konto verloren
        r = sim.lucid_pass([900.0, -1000.0], runs=2000, seed=1)
        self.assertGreater(r['p_fail'], 0)

    def test_path_hits_target_in_steady_uptrend(self):
        bars = [bar(1793000000 + i * 300, 100 + i, 101 + i, 99.9 + i, 101 + i) for i in range(400)]
        pool = sim.build_pool(bars)
        r = sim.path_sim(pool, 'LONG', 100, 95, 105, bars[-1]['time'], bars_ahead=20, replays=500)
        self.assertEqual(r['p_target'], 1.0)
        self.assertEqual(r['verdict'], 'Deutlich zum Ziel')

    def test_path_stop_before_target_in_same_bar(self):
        bars = [bar(1793000000 + i * 300, 100, 110, 90, 100) for i in range(400)]
        r = sim.path_sim(sim.build_pool(bars), 'LONG', 100, 95, 105, bars[-1]['time'], bars_ahead=5, replays=200)
        self.assertEqual(r['p_stop'], 1.0)


if __name__ == '__main__':
    unittest.main()
