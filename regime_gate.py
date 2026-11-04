"""TAURUS V8 Marktlagen-Filter: eine Strategie darf nur in den Marktlagen
handeln, in denen sie laut Backtest (oder per Konstruktion) einen Vorteil hat.

Signale ausserhalb der erlaubten Marktlagen werden vor der Ausfuehrung
entfernt (LAB, Lucid und Backtest gleichermassen). Strategien ohne Eintrag
werden nicht gefiltert.

Mit der Umgebungsvariable TAURUS_REGIME_GATE=off wird der Filter
abgeschaltet (fuer Forschung: zeigt, wie eine Strategie in ALLEN
Marktlagen abschneidet).
"""
import os
from bisect import bisect_right

import regime as rg

# Bestehende Strategien: nur Marktlagen, die im 60-Tage-Backtest
# (25.8.-3.11.2026, n >= 40) einen positiven Durchschnitt hatten.
# Neue V8-Strategien: Marktlage per Konstruktion (siehe regime_strategies.py).
GATES = {
    'omar': {'TREND_RUNTER'},                 # 60 Tage: +0.12 R, beide Haelften positiv
    'ema20': {'TREND_RUNTER'},                # +0.08 R, beide Haelften positiv
    'trend_pullback_mtf': {'TREND_RUNTER'},   # inaktiv (+0.02 R = kein Vorteil)
    'bb_only_long': {'TREND_RUNTER'},         # nur LAB, 1M-Daten erst 29 Tage
    'trend_breakout_1h': {'TREND_HOCH'},      # TREND_HOCH +0.12 R stabil, TREND_RUNTER -0.08 R
    'trend_engulf_fade': {'TREND_RUNTER'},
    'trend_ema_pullback': {'TREND_HOCH', 'TREND_RUNTER'},   # inaktiv
    'range_bb_reentry': {'RANGE'},            # inaktiv
    'range_rsi2': {'RANGE'},                  # inaktiv
    # orb5: Uhrzeit-Effekt, bewusst ohne Marktlagen-Filter
}


def enabled():
    return os.environ.get('TAURUS_REGIME_GATE', 'on').lower() not in ('off', '0', 'false', 'no')


class RegimeLookup:
    """Marktlage zu einem Zeitpunkt aus abgeschlossenen 5M-Kerzen (kausal)."""

    def __init__(self, bars5m):
        self.times = [int(b['time']) for b in bars5m]
        self.series = rg.compute_series(bars5m) if bars5m else []

    def at(self, signal_time, timeframe='5m'):
        cutoff = int(signal_time) + (300 if timeframe == '5m' else 60)
        f = rg.features_at(self.times, self.series, cutoff) if self.times else None
        return rg.classify(f)['regime']


def apply(tiles, bars5m, lookup=None):
    """Entfernt Signale ausserhalb der erlaubten Marktlagen. Gibt neue Tiles zurueck."""
    if not enabled() or not tiles:
        return tiles
    lk = lookup or RegimeLookup(bars5m)
    out = []
    for st in tiles:
        allowed = GATES.get(st.get('id'))
        if not allowed:
            out.append(st)
            continue
        keep = [s for s in st.get('signals', [])
                if lk.at(s['time'], s.get('timeframe', '5m')) in allowed]
        out.append(dict(st, signals=keep, gate=sorted(allowed)))
    return out
