"""Regime-Lab: Ausfuehrung naechster Open, Stop vor Ziel, Kosten, kein Lookahead."""
import unittest

import regime_lab as L


def _bars(rows):
    return [dict(time=i * 3600, open=o, high=h, low=l, close=c, volume=1) for i, (o, h, l, c) in enumerate(rows)]


class LabTests(unittest.TestCase):
    def _run(self, rows, fn):
        bars = _bars(rows)
        ind = L.Ind(bars)
        return L.simulate('btc', bars, ind, ['RANGE'] * len(bars), 'x', fn, 1, start=20)

    def test_target_and_cost(self):
        rows = [(100, 101, 99, 100)] * 25 + [(100, 103, 99.9, 102.5)] + [(102.5, 103, 102, 102.5)] * 5
        fn = lambda d, i, s: dict(stop=d.c[i] - 1, tp=d.c[i] + 2, hold=10) if i == 22 else None
        t = self._run(rows, fn)
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0]['reason'], 'ZIEL')
        # Einstieg Open 100 (Kerze 23), Ziel 102, Risiko 1, Kosten 0.24 % von 100
        self.assertAlmostEqual(t[0]['r'], 2 - 100 * L.CRYPTO_COST_RATE, places=6)

    def test_stop_before_target_same_bar(self):
        rows = [(100, 101, 99, 100)] * 23 + [(100, 103, 98, 100)] + [(100, 101, 99, 100)] * 5
        fn = lambda d, i, s: dict(stop=99.0, tp=102.0, hold=10) if i == 22 else None
        t = self._run(rows, fn)
        self.assertEqual(t[0]['reason'], 'STOP')
        self.assertLess(t[0]['r'], -1)

    def test_signal_only_uses_past(self):
        rows = [(100 + i * .1, 100.5 + i * .1, 99.5 + i * .1, 100 + i * .1) for i in range(300)]
        bars = _bars(rows)
        full = L.Ind(bars)
        part = L.Ind(bars[:250])
        for k in ('e20', 'atr', 'rsi2', 'macd', 's200'):
            self.assertEqual(getattr(full, k)[249], getattr(part, k)[249])


if __name__ == '__main__':
    unittest.main()
