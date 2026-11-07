"""V9: Strategien je 1h-Marktlage – Kausalitaet, Marktlagen-Filter, Ausstiege, Groesse."""
import os
import random
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paper_engine as pe
import v9_regime as v9

T0 = 1_780_000_000 // 3600 * 3600


def walk_1h(n=700, seed=3, start=20000.0):
    rnd = random.Random(seed)
    out, p, drift = [], start, 0.0
    for i in range(n):
        if i % 120 == 0:
            drift = rnd.choice((-1, 0, 1)) * 0.0012
        o = p
        c = o * (1 + drift + rnd.gauss(0, 0.004))
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.002)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, 0.002)))
        out.append(dict(time=T0 + i * 3600, open=o, high=h, low=l, close=c, volume=100))
        p = c
    return out


def fivem_for(hours):
    """5M-Kerzen, die exakt die Stunden abdecken (12 je Stunde)."""
    out = []
    for hb in hours:
        for k in range(12):
            x = hb['open'] + (hb['close'] - hb['open']) * (k + 1) / 12
            out.append(dict(time=hb['time'] + 300 * k, open=x, high=max(x, hb['high'] if k == 6 else x),
                            low=min(x, hb['low'] if k == 3 else x), close=x, volume=10))
    return out


class Signals(unittest.TestCase):
    def setUp(self):
        self.h = walk_1h()
        v9.set_hourly('nq', self.h)

    def tearDown(self):
        v9.set_hourly('nq', None)

    def test_produces_signals_in_allowed_regime_only(self):
        sigs, regs = v9.hourly_signals(self.h, 'nq')
        total = sum(len(v) for v in sigs.values())
        self.assertGreater(total, 0)
        for key, lst in sigs.items():
            for s in lst:
                self.assertEqual(s['regime_1h'], v9.STRATEGIES[key][3])
                self.assertEqual((s['time'] + 300) % 3600, 0)      # letzte 5M-Kerze der Stunde
                if s['side'] == 'LONG':
                    self.assertLess(s['stop'], s['entry']); self.assertGreater(s['tp'], s['entry'])
                else:
                    self.assertGreater(s['stop'], s['entry']); self.assertLess(s['tp'], s['entry'])

    def test_gate_off_shows_more(self):
        on = sum(len(v) for v in v9.hourly_signals(self.h, 'nq')[0].values())
        with patch.dict(os.environ, {'TAURUS_REGIME_GATE': 'off'}):
            off = sum(len(v) for v in v9.hourly_signals(self.h, 'nq')[0].values())
        self.assertGreater(off, on)

    def test_causal_prefix(self):
        full, _ = v9.hourly_signals(self.h, 'nq')
        for cut in (400, 550, 699):
            pre, _ = v9.hourly_signals(self.h[:cut + 1], 'nq')
            lim = self.h[cut]['time'] + 3600
            for k in v9.KEYS:
                self.assertEqual([s['id'] for s in full[k] if s['time'] < lim], [s['id'] for s in pre[k]])

    def test_build_uses_only_completed_hours(self):
        five = fivem_for(self.h[-60:])
        all_ids = {s['id'] for t in v9.build(five, 'nq') for s in t['signals']}
        # 5M-Verlauf endet mitten in der vorletzten Stunde: deren Signal darf noch nicht sichtbar sein
        cut = five[:-18]
        part_ids = {s['id'] for t in v9.build(cut, 'nq') for s in t['signals']}
        self.assertTrue(part_ids <= all_ids)
        last = cut[-1]['time']
        for t in v9.build(cut, 'nq'):
            for s in t['signals']:
                self.assertLessEqual(s['time'], last)

    def test_non_futures_neutral(self):
        tiles = v9.build(fivem_for(self.h[-30:]), 'btc')
        self.assertEqual(len(tiles), len(v9.KEYS))
        self.assertTrue(all(not t['signals'] for t in tiles))

    def test_hourly_from_5m_only_complete_hours(self):
        five = fivem_for(self.h[:3])[:-1]                # letzte Stunde ohne HH:55
        agg = v9.hourly_from_5m(five)
        self.assertEqual([b['time'] for b in agg], [self.h[0]['time'], self.h[1]['time']])
        self.assertAlmostEqual(agg[0]['close'], self.h[0]['close'])


class Wiring(unittest.TestCase):
    def test_active_in_lab_not_lucid(self):
        import lucid_executor as lx
        for k in v9.KEYS:
            self.assertIn(k, pe.ACTIVE_5M)
            self.assertNotIn(k, lx.SELECTED)
        self.assertEqual(set(pe.V9_EXITS), set(v9.KEYS))

    def test_evaluate_contains_v9_tiles(self):
        from strategies import evaluate
        h = walk_1h(400)
        v9.set_hourly('mes', h)
        try:
            ids = {t['id'] for t in evaluate(fivem_for(h[-40:]), [], 'mes')}
        finally:
            v9.set_hourly('mes', None)
        self.assertTrue(set(v9.KEYS) <= ids)


class Execution(unittest.TestCase):
    """Paper-Engine: V9-Ausstiege und Mindestgroesse."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.p = patch.object(pe, 'DB', self.tmp.name)
        self.p.start()
        self.db = pe.conn().__enter__()
        pe.init_tables(self.db)
        pe.init_extra(self.db)

    def tearDown(self):
        self.p.stop()
        os.unlink(self.tmp.name)

    def _trade(self, strategy, side, entry, stop, tp):
        tid = f'nq:{strategy}:1:{side}'
        self.db.execute("INSERT INTO trades(id,market,strategy,side,signal_time,status,signal_entry,signal_stop,signal_tp,timeframe) "
                        "VALUES(?,?,?,?,?,'PENDING',?,?,?,'5m')", (tid, 'nq', strategy, side, 1, entry, stop, tp))
        return tid

    def _row(self, tid):
        return self.db.execute('SELECT * FROM trades WHERE id=?', (tid,)).fetchone()

    def test_min_one_contract_with_wide_stop(self):
        tid = self._trade('v9_macd_long', 'LONG', 20000, 19800, 24000)   # 200 Pkt * 2 USD = 400 USD > 200
        pe._open_pending(self.db, 'nq', dict(time=300, open=20000, high=20010, low=19990, close=20005), [], '5m')
        r = self._row(tid)
        self.assertEqual(r['status'], 'OPEN')
        self.assertEqual(r['qty'], 1)
        # Bestehende Strategien bleiben bei max. 200 USD
        tid2 = self._trade('ema20', 'LONG', 20000, 19800, 20800)
        pe._open_pending(self.db, 'nq', dict(time=300, open=20000, high=20010, low=19990, close=20005), [], '5m')
        self.assertEqual(self._row(tid2)['exit_reason'], 'RISK_LIMIT')

    def test_trailing_from_best_high_not_1r_rule(self):
        tid = self._trade('v9_macd_long', 'LONG', 20000, 19900, 22000)
        pe._open_pending(self.db, 'nq', dict(time=300, open=20000, high=20000, low=20000, close=20000), [], '5m')
        entry = self._row(tid)['entry']
        r0 = entry - 19900
        pe._close_open(self.db, 'nq', dict(time=600, open=20000, high=20050, low=19995, close=20010), '5m')
        self.assertAlmostEqual(self._row(tid)['stop'], max(19900, 20050 - 1.5 * r0))
        pe._close_open(self.db, 'nq', dict(time=900, open=20200, high=20300, low=20190, close=20290), '5m')
        self.assertAlmostEqual(self._row(tid)['stop'], 20300 - 1.5 * r0)

    def test_fixed_target_has_no_trailing(self):
        tid = self._trade('v9_bb_dip', 'LONG', 20000, 19950, 20080)
        pe._open_pending(self.db, 'nq', dict(time=300, open=20000, high=20000, low=20000, close=20000), [], '5m')
        pe._close_open(self.db, 'nq', dict(time=600, open=20000, high=20070, low=19990, close=20065), '5m')
        r = self._row(tid)
        self.assertEqual(r['status'], 'OPEN')
        self.assertEqual(r['stop'], 19950)          # generisches 1R-Trailing waere hier aktiv geworden


if __name__ == '__main__':
    unittest.main()
