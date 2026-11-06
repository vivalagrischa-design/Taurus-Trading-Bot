"""PO3 10:00: Regeln, Kausalitaet und Ausfuehrung in der Paper-Engine."""
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import po3_10am as po3

NY = ZoneInfo('America/New_York')
D1, D2 = date(2026, 10, 6), date(2026, 10, 7)     # Di (Vortag), Mi (Handelstag)


def ts(day, hh, mm):
    return int(datetime(day.year, day.month, day.day, hh, mm, tzinfo=NY).timestamp())


def b(t, o, h, l, c):
    return {'time': t, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': 100}


def scenario(k=1.0, prev_bull=True):
    """Lehrbuch-Long: Vortag bullisch, Pre-Market-Sweep des Vortagestiefs,
    enge Accumulation, Sweep des Acc-Tiefs um 10:02, IFVG-Entry um 10:05."""
    bars = []
    o0, c0 = (100.0, 101.0) if prev_bull else (101.0, 100.0)
    for i in range(240, 960):                        # Vortag 04:00-16:00
        p = o0 + (c0 - o0) * max(0, i - 570) / 389 if i >= 570 else o0
        lo = 99.0 if i == 700 else p - 0.05
        bars.append(b(ts(D1, i // 60, i % 60), p * k, (p + 0.05) * k, lo * k, p * k))
    for i in range(240, 600):                        # Handelstag bis 10:00
        if i < 360: p = 101.0
        elif i < 420: p = 101.0 - 2.0 * (i - 360) / 60   # Dip bis 99.0 ...
        elif i < 570: p = 99.0 + 2.5 * (i - 420) / 150  # ... zurueck auf 101.5
        else: p = 101.5 + (0.1 if i % 2 else -0.1)
        lo = 98.9 if i == 420 else p - 0.05
        bars.append(b(ts(D2, i // 60, i % 60), p * k, (p + 0.05) * k, lo * k, p * k))
    tail = [  # 10:00 ...
        (101.50, 101.55, 101.45, 101.46), (101.46, 101.47, 101.32, 101.33),
        (101.33, 101.34, 101.10, 101.12),               # 10:02 Sweep unter 101.35
        (101.12, 101.08, 101.04, 101.06),               # 10:03 bearish FVG (Top 101.32)
        (101.06, 101.10, 101.02, 101.09),
        (101.09, 101.40, 101.08, 101.38),               # 10:05 Schluss > 101.32 -> IFVG
    ]
    for j, (o, h, l, c) in enumerate(tail):
        bars.append(b(ts(D2, 10, j), o * k, max(o, h, c) * k, l * k, c * k))
    for j in range(6, 400):                          # danach langsam aufwaerts
        p = 101.38 + 0.004 * j
        t = ts(D2, 10, 0) + 60 * j
        bars.append(b(t, p * k, (p + 0.03) * k, (p - 0.03) * k, (p + 0.01) * k))
    return bars


def daily_rows(rising=True, k=1.0):
    """Index-Tageskerzen bis zum Vortag; rising=True -> ATR am Ende hoch (Rang 1.0)."""
    rows = []
    day = D1 - timedelta(days=299)
    for i in range(300):
        rng = (0.5 + 1.5 * i / 299) if rising else (2.0 - 1.5 * i / 299)
        rows.append((day + timedelta(days=i), 100 * k, (100 + rng) * k, 100 * k, (100 + rng / 2) * k))
    return rows


class Rules(unittest.TestCase):
    def setUp(self):
        po3.set_daily('nq', daily_rows(True))

    def test_textbook_long_signal(self):
        tl = po3.build(scenario(), 'nq')
        self.assertEqual(len(tl['signals']), 1, tl['details'])
        s = tl['signals'][0]
        self.assertEqual((s['side'], s['trigger']), ('LONG', 'IFVG'))
        self.assertEqual(s['time'], ts(D2, 10, 5))
        self.assertAlmostEqual(s['entry'], 101.38)
        self.assertAlmostEqual(s['stop'], 101.02 - 0.5)
        self.assertAlmostEqual(s['tp'], 101.38 + 3 * (101.38 - 100.52), places=4)
        self.assertEqual(s['time_exit'], ts(D2, 15, 55))
        self.assertEqual(s['timeframe'], '1m')

    def test_causal_no_signal_before_trigger_bar(self):
        bars = scenario()
        cut = next(i for i, x in enumerate(bars) if x['time'] == ts(D2, 10, 4))
        self.assertEqual(po3.build(bars[:cut + 1], 'nq', last_only=True)['signals'], [])
        full = po3.build(bars, 'nq')['signals']
        pre = po3.build(bars[:cut + 2], 'nq', last_only=True)['signals']
        self.assertEqual(pre, full)

    def test_low_volatility_blocks(self):
        po3.set_daily('nq', daily_rows(False))
        self.assertEqual(po3.build(scenario(), 'nq')['signals'], [])

    def test_bias_conflict_blocks(self):
        # Vortag baerisch, 4H 06-10 bullisch -> kein Bias
        self.assertEqual(po3.build(scenario(prev_bull=False), 'nq')['signals'], [])

    def test_no_daily_data_no_signal(self):
        po3._DAILY.pop('nq', None)
        tl = po3.build(scenario(), 'nq')
        self.assertEqual(tl['signals'], [])
        self.assertIn('Tagesdaten', tl['details'])

    def test_gold_not_supported(self):
        self.assertEqual(po3.build(scenario(), 'mgc')['signals'], [])

    def test_mirrored_short(self):
        mir = [b(x['time'], 200 - x['open'], 200 - x['low'], 200 - x['high'], 200 - x['close']) for x in scenario()]
        s = po3.build(mir, 'nq')['signals']
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]['side'], 'SHORT')
        self.assertAlmostEqual(s[0]['entry'], 200 - 101.38)
        self.assertGreater(s[0]['stop'], s[0]['entry']); self.assertLess(s[0]['tp'], s[0]['entry'])


class Engine(unittest.TestCase):
    def test_paper_engine_opens_once_without_trailing(self):
        import paper_engine as pe
        k = 100.0                                      # NQ-aehnliches Preisniveau
        po3.set_daily('nq', daily_rows(True, k))
        bars = scenario(k)
        with tempfile.TemporaryDirectory() as d, patch.object(pe, 'DB', os.path.join(d, 'p.db')), \
                patch.object(pe, 'DATABASE_URL', ''):
            start = next(i for i, x in enumerate(bars) if x['time'] == ts(D2, 9, 0))
            pe.advance_po3('nq', bars[:start])         # Wasserzeichen setzen
            for i in range(start + 1, len(bars) + 1, 7):
                pe.advance_po3('nq', bars[:i])
            pe.advance_po3('nq', bars)
            with pe.conn() as db:
                rows = [dict(r) for r in db.execute("SELECT * FROM trades WHERE strategy='po3_10am'")]
        self.assertEqual(len(rows), 1)
        t = rows[0]
        self.assertEqual(t['side'], 'LONG')
        self.assertEqual(t['entry_time'], ts(D2, 10, 6))   # naechster Open
        self.assertIn(t['status'], ('OPEN', 'CLOSED'))
        self.assertEqual(t['trail_updates'] or 0, 0)        # kein Trailing
        self.assertEqual(t['time_exit'], ts(D2, 15, 55))

    def test_registered(self):
        import paper_engine as pe
        self.assertIn('po3_10am', pe.ALL_STRATS)
        self.assertIn('po3_10am', pe.NO_TRAIL)
        self.assertEqual(pe._engine_strategies('po3'), ('po3_10am',))


if __name__ == '__main__':
    unittest.main()
