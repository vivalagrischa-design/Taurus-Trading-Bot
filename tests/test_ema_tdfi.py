"""EMA 50/100 + TDFI: Signal nur nach Kreuzung mit Bestaetigung, kein Lookahead."""
import math
import unittest

import ema_tdfi as et


def _bars(closes):
    return [dict(time=i * 300, open=c, high=c + 0.5, low=c - 0.5, close=c, volume=100.) for i, c in enumerate(closes)]


def _down_then_up(n_down=200, n_up=60):
    closes = [200 - 0.2 * i for i in range(n_down)]
    closes += [closes[-1] + 0.8 * (i + 1) for i in range(n_up)]
    return closes


class EmaTdfiTests(unittest.TestCase):
    def test_long_after_upward_cross(self):
        sigs = et.signals(_bars(_down_then_up()))
        self.assertEqual(len(sigs), 1)
        s = sigs[0]
        self.assertEqual(s['side'], 'LONG')
        self.assertEqual(s['strategy'], et.KEY)
        self.assertEqual(s['timeframe'], '5m')
        self.assertAlmostEqual((s['tp'] - s['entry']) / (s['entry'] - s['stop']), 2.0, places=2)

    def test_short_mirror(self):
        sigs = et.signals(_bars([400 - c for c in _down_then_up()]))
        self.assertEqual([s['side'] for s in sigs], ['SHORT'])

    def test_no_lookahead(self):
        bars = _bars(_down_then_up())
        full = et.signals(bars)
        t = full[0]['time']
        idx = next(i for i, b in enumerate(bars) if b['time'] == t)
        self.assertEqual(et.signals(bars[:idx]), [])
        self.assertEqual(et.signals(bars[:idx + 1])[0]['id'], full[0]['id'])

    def test_flat_market_no_signal(self):
        self.assertEqual(et.signals(_bars([100.0] * 300)), [])

    def test_chop_whipsaws_documented(self):
        # Bekannte Schwaeche (wie im Video, bewusst nicht weggefiltert):
        # TDFI ist relativ normiert und bestaetigt auch Mini-Kreuzungen im Seitwaertsmarkt.
        closes = [100 + 0.3 * math.sin(i / 3) for i in range(300)]
        self.assertGreater(len(et.signals(_bars(closes))), 5)

    def test_tdfi_bounded(self):
        vals = [v for v in et.tdfi(_down_then_up()) if v is not None]
        self.assertTrue(all(-1.0 <= v <= 1.0 for v in vals))

    def test_tile_and_lab_wiring(self):
        import paper_engine as pe
        from strategies import evaluate
        self.assertIn(et.KEY, pe.ACTIVE_5M)
        ids = [t['id'] for t in evaluate(_bars(_down_then_up()), [], 'nq')]
        self.assertIn(et.KEY, ids)

    def test_not_in_lucid(self):
        import lucid_executor as lx
        self.assertNotIn(et.KEY, lx.SELECTED)


if __name__ == '__main__':
    unittest.main()
