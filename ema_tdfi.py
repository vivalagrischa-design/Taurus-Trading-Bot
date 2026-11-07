"""TAURUS LAB: EMA-Cross 50/100 + TDFI-Bestaetigung (Instagram-Reel "Easy EMA Scalping").

Regeln (5M, nur abgeschlossene Kerzen, kein Lookahead):
  * Kreuzung: EMA50 kreuzt EMA100 (Schlusskurs-Basis).
  * Bestaetigung: Trend Direction Force Index (TDFI, Laenge 13) schiesst ueber
    +0.05 (LONG) bzw. unter -0.05 (SHORT) - das ist die gestrichelte "Range"
    im unteren Panel. Die Bestaetigung darf auf der Kreuzungskerze oder bis zu
    CONFIRM_BARS Kerzen danach kommen, solange die EMAs noch richtig liegen.
  * Pro Kreuzung hoechstens ein Signal.
  * Stop 1.5 ATR(14), Ziel 2R. Einstieg wie alle Strategien: naechster 5M-Open.

Die Parameter sind die aus dem Video bzw. TradingView-Standardwerte und
wurden NICHT optimiert. Kein Marktlagen-Filter: zuerst messen, in welcher
Marktlage die Strategie funktioniert.
"""
from strategies import tile, signal_with_params

KEY = 'ema_tdfi'
NAME = 'EMA 50/100 Cross + TDFI'
FAST, SLOW = 50, 100
TDFI_LEN = 13
TRIGGER = 0.05
CONFIRM_BARS = 6
ATR_LEN = 14
STOP_ATR = 1.5
TARGET_R = 2.0


def _ema(values, span):
    out, a, last = [], 2 / (span + 1), None
    for v in values:
        last = v if last is None else a * v + (1 - a) * last
        out.append(last)
    return out


def _atr(h, l, c, n=ATR_LEN):
    out, last = [None] * len(c), None
    for i in range(1, len(c)):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        last = tr if last is None else (last * (n - 1) + tr) / n
        if i >= n:
            out[i] = last
    return out


def tdfi(closes, length=TDFI_LEN):
    """Trend Direction Force Index, normiert auf [-1, 1] (Rueckblick 3x Laenge)."""
    mma = _ema([x * 1000 for x in closes], length)
    smma = _ema(mma, length)
    raw = [0.0] * len(closes)
    for i in range(1, len(closes)):
        impet = ((mma[i] - mma[i - 1]) + (smma[i] - smma[i - 1])) / 2
        raw[i] = abs(mma[i] - smma[i]) * impet ** 3
    look = 3 * length
    out = [None] * len(closes)
    for i in range(look, len(closes)):
        m = max(abs(x) for x in raw[i - look + 1:i + 1])
        out[i] = raw[i] / m if m else 0.0
    return out


def signals(bars):
    if len(bars) < SLOW + 10:
        return []
    o = [float(b['open']) for b in bars]
    h = [float(b['high']) for b in bars]
    l = [float(b['low']) for b in bars]
    c = [float(b['close']) for b in bars]
    fast, slow = _ema(c, FAST), _ema(c, SLOW)
    t = tdfi(c)
    atr = _atr(h, l, c)
    out, cross_i, cross_side, used = [], None, None, True
    for i in range(SLOW, len(bars)):
        if fast[i - 1] <= slow[i - 1] and fast[i] > slow[i]:
            cross_i, cross_side, used = i, 'LONG', False
        elif fast[i - 1] >= slow[i - 1] and fast[i] < slow[i]:
            cross_i, cross_side, used = i, 'SHORT', False
        if used or cross_i is None or i - cross_i > CONFIRM_BARS or t[i] is None or not atr[i]:
            continue
        if cross_side == 'LONG' and fast[i] > slow[i] and t[i] > TRIGGER:
            stop = c[i] - STOP_ATR * atr[i]
            tp = c[i] + TARGET_R * (c[i] - stop)
        elif cross_side == 'SHORT' and fast[i] < slow[i] and t[i] < -TRIGGER:
            stop = c[i] + STOP_ATR * atr[i]
            tp = c[i] - TARGET_R * (stop - c[i])
        else:
            continue
        used = True
        out.append(signal_with_params(
            KEY, cross_side, bars[i]['time'], c[i], stop, tp,
            f'EMA{FAST} kreuzt EMA{SLOW}, TDFI {t[i]:+.2f} jenseits ±{TRIGGER}; Stop {STOP_ATR} ATR; {TARGET_R:g}R',
            level=slow[i], breakout_time=bars[cross_i]['time'], timeframe='5m'))
    return out


def build(bars, market='nq'):
    sigs = signals(bars)
    if len(bars) < SLOW + 10:
        return tile(KEY, NAME, 'neutral', f'Mindestens {SLOW + 10} abgeschlossene 5M-Kerzen benötigt', [],
                    [('EMA-Kreuzung', 'neutral'), ('TDFI-Bestätigung', 'neutral')])
    c = [float(b['close']) for b in bars]
    fast, slow = _ema(c, FAST)[-1], _ema(c, SLOW)[-1]
    t = tdfi(c)[-1] or 0.0
    recent = bool(sigs and sigs[-1]['time'] == bars[-1]['time'])
    return tile(KEY, NAME, 'green' if recent else 'neutral',
                f'EMA{FAST} {fast:.2f} · EMA{SLOW} {slow:.2f} · TDFI {t:+.2f} · Stop {STOP_ATR} ATR · {TARGET_R:g}R (nur LAB)',
                sigs,
                [('EMA50 > EMA100', 'green' if fast > slow else 'red'),
                 ('TDFI jenseits ±0.05', 'green' if t > TRIGGER else 'red' if t < -TRIGGER else 'neutral'),
                 ('Signal letzte Kerze', 'green' if recent else 'neutral')])
