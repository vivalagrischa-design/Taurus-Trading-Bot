"""TAURUS V8: Strategien je Marktlage (5M, nur abgeschlossene Kerzen, kein Lookahead).

Grundidee (Literatur + eigener Backtest):
  * Trend (TREND_HOCH / TREND_RUNTER): mit dem Trend handeln, nie dagegen.
      trend_ema_pullback  Ruecksetzer an die EMA20, Wiederaufnahme-Kerze, Ziel 2R
      trend_breakout_1h   Ausbruch ueber das 1h-Hoch/-Tief in Trendrichtung, Ziel 2R
  * Seitwaerts (RANGE): Uebertreibungen an den Raendern zuruecknehmen,
    Ziel ist die Mitte (Mean Reversion).
      range_bb_reentry    Schluss zurueck innerhalb des Bollinger-Bands, Ziel SMA20
      range_rsi2          RSI(2) extrem, Ziel 1R
  * CHOP / UEBERGANG: keine neue Strategie. Dort verlieren laut Backtest fast alle;
    flach bleiben ist die Strategie.
  * Uhrzeit-Effekte (US-Aktienindex-Futures, unabhaengig von der Marktlage):
      orb5                5-Minuten-Opening-Range-Breakout (Zarattini/Aziz 2023):
                          Richtung der 9:30-Kerze, Stop am anderen Ende, Ziel 10R,
                          spaetestens 16:00 New York raus
      imom_last30         Intraday-Momentum (Gao/Han/Li/Zhou 2018): Rendite vom
                          Vortagesschluss bis 10:00 bestimmt die Richtung der
                          letzten halben Stunde (15:30-16:00)

Die Parameter stammen aus der Literatur bzw. sind runde Standardwerte und
wurden NICHT auf unsere 60 Tage optimiert.

Ergebnis 60-Tage-Backtest (26.8.-4.11.2026, nach Kosten):
  aktiv:   trend_breakout_1h (nur TREND_HOCH, +0.12 R, beide Haelften positiv),
           orb5 (+0.10 R, n=71, nur LAB), trend_engulf_fade (aus der Kerzen-Studie, nur LAB)
  inaktiv: range_bb_reentry (-0.19 R), range_rsi2 (-0.11 R), trend_ema_pullback (-0.04 R),
           imom_last30 (-0.12 R, Haelften widerspruechlich). Code bleibt fuer Nachtests.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import regime as rg
from strategies import tile, signal_with_params

NY = ZoneInfo('America/New_York')
INDEX_MARKETS = ('nq', 'mes')
COOLDOWN = 6                         # Kerzen zwischen zwei Signalen derselben Strategie
NAMES = {
    'trend_ema_pullback': 'Trend: EMA20-Rücksetzer',
    'trend_breakout_1h': 'Trend: 1h-Ausbruch',
    'range_bb_reentry': 'Range: Bollinger-Rückkehr',
    'range_rsi2': 'Range: RSI(2) Extrem',
    'orb5': 'ORB 5 Minuten (9:30)',
    'imom_last30': 'Intraday-Momentum letzte 30 Min.',
    'trend_engulf_fade': 'Abwärtstrend: Bullish Engulfing shorten',
}
KEYS = tuple(NAMES)


def _rsi(closes, period):
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    g = l = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        g += max(d, 0); l += max(-d, 0)
    g /= period; l /= period
    out[period] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        g = (g * (period - 1) + max(d, 0)) / period
        l = (l * (period - 1) + max(-d, 0)) / period
        out[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    return out


def _bb(closes, i, n=20, k=2.0):
    if i < n - 1:
        return None
    w = closes[i - n + 1:i + 1]
    m = sum(w) / n
    sd = (sum((x - m) ** 2 for x in w) / n) ** .5
    return m, m - k * sd, m + k * sd


def _ny(ts):
    return datetime.fromtimestamp(int(ts), timezone.utc).astimezone(NY)


def _sig(key, side, b, entry, stop, tp, reason, time_exit=None):
    s = signal_with_params(key, side, b['time'], entry, stop, tp, reason, timeframe='5m')
    if time_exit:
        s['time_exit'] = int(time_exit)
    return s


def build(bars, market='nq'):
    found = {k: [] for k in KEYS}
    if len(bars) < 80:
        return [tile(k, NAMES[k], 'neutral', 'Mindestens 80 abgeschlossene 5M-Kerzen benötigt', [], []) for k in KEYS]
    series = rg.compute_series(bars)
    regimes = [rg.classify(f)['regime'] if f else 'UNBEKANNT' for f in series]
    o = [float(b['open']) for b in bars]; h = [float(b['high']) for b in bars]
    l = [float(b['low']) for b in bars]; c = [float(b['close']) for b in bars]
    rsi2 = _rsi(c, 2)
    last = {k: -10 ** 9 for k in KEYS}

    def emit(key, i, sig):
        if i - last[key] >= COOLDOWN and sig['side'] in ('LONG', 'SHORT'):
            found[key].append(sig)
            last[key] = i

    for i in range(60, len(bars)):
        f = series[i]
        if not f:
            continue
        b, reg, atr = bars[i], regimes[i], f['atr']
        e20, e50 = f['ema20'], f['ema50']

        # ---- Trend: Ruecksetzer an EMA20 + Wiederaufnahme-Kerze
        if reg == 'TREND_HOCH' and l[i] <= e20 + 0.2 * atr and c[i] > e20 and c[i] > o[i] and c[i] > h[i - 1]:
            stop = min(min(l[i - 2:i + 1]) - 0.2 * atr, c[i] - 0.8 * atr)
            emit('trend_ema_pullback', i, _sig('trend_ema_pullback', 'LONG', b, c[i], stop, c[i] + 2 * (c[i] - stop),
                                               'Aufwärtstrend, Rücksetzer an EMA20, Wiederaufnahme; 2R'))
        if reg == 'TREND_RUNTER' and h[i] >= e20 - 0.2 * atr and c[i] < e20 and c[i] < o[i] and c[i] < l[i - 1]:
            stop = max(max(h[i - 2:i + 1]) + 0.2 * atr, c[i] + 0.8 * atr)
            emit('trend_ema_pullback', i, _sig('trend_ema_pullback', 'SHORT', b, c[i], stop, c[i] - 2 * (stop - c[i]),
                                               'Abwärtstrend, Rücksetzer an EMA20, Wiederaufnahme; 2R'))

        # ---- Trend: Ausbruch ueber 1h-Hoch/-Tief (12 Kerzen) in Trendrichtung
        hh, ll = max(h[i - 12:i]), min(l[i - 12:i])
        if reg == 'TREND_HOCH' and c[i] > hh and c[i - 1] <= hh and c[i] > e20:
            stop = c[i] - 1.5 * atr
            emit('trend_breakout_1h', i, _sig('trend_breakout_1h', 'LONG', b, c[i], stop, c[i] + 2 * (c[i] - stop),
                                              'Aufwärtstrend, Schluss über 1h-Hoch; Stop 1.5 ATR; 2R'))
        if reg == 'TREND_RUNTER' and c[i] < ll and c[i - 1] >= ll and c[i] < e20:
            stop = c[i] + 1.5 * atr
            emit('trend_breakout_1h', i, _sig('trend_breakout_1h', 'SHORT', b, c[i], stop, c[i] - 2 * (stop - c[i]),
                                              'Abwärtstrend, Schluss unter 1h-Tief; Stop 1.5 ATR; 2R'))

        # ---- Range: zurueck ins Bollinger-Band, Ziel Mitte
        if reg == 'RANGE':
            now, prev = _bb(c, i), _bb(c, i - 1)
            if now and prev:
                mid, lo, up = now
                if c[i - 1] < prev[1] and c[i] > lo and c[i] > o[i]:
                    stop = min(l[i - 1], l[i]) - 0.25 * atr
                    if mid - c[i] >= 0.8 * (c[i] - stop):
                        emit('range_bb_reentry', i, _sig('range_bb_reentry', 'LONG', b, c[i], stop, mid,
                                                         'Seitwärts, Schluss zurück über unterem BB; Ziel SMA20'))
                if c[i - 1] > prev[2] and c[i] < up and c[i] < o[i]:
                    stop = max(h[i - 1], h[i]) + 0.25 * atr
                    if c[i] - mid >= 0.8 * (stop - c[i]):
                        emit('range_bb_reentry', i, _sig('range_bb_reentry', 'SHORT', b, c[i], stop, mid,
                                                         'Seitwärts, Schluss zurück unter oberem BB; Ziel SMA20'))
            # ---- Range: RSI(2) extrem
            if rsi2[i] is not None:
                if rsi2[i] < 5:
                    stop = c[i] - 1.2 * atr
                    emit('range_rsi2', i, _sig('range_rsi2', 'LONG', b, c[i], stop, c[i] + (c[i] - stop),
                                               'Seitwärts, RSI(2) < 5; Stop 1.2 ATR; 1R'))
                elif rsi2[i] > 95:
                    stop = c[i] + 1.2 * atr
                    emit('range_rsi2', i, _sig('range_rsi2', 'SHORT', b, c[i], stop, c[i] - (stop - c[i]),
                                               'Seitwärts, RSI(2) > 95; Stop 1.2 ATR; 1R'))

        # ---- Kerzen-Studie: Bullish Engulfing IM Abwaertstrend -> Short (Gegenbewegung verkaufen).
        # Einziges Muster, das in der 60-Tage-Studie netto positiv, in beiden Haelften
        # positiv und besser als die Basisrate war (58 % zuerst -1 ATR). Stop = Ziel = 1 ATR.
        if reg == 'TREND_RUNTER':
            po, pc = o[i - 1], c[i - 1]
            if pc < po and c[i] > o[i] and o[i] <= pc and c[i] >= po and (c[i] - o[i]) > (po - pc):
                emit('trend_engulf_fade', i, _sig('trend_engulf_fade', 'SHORT', b, c[i], c[i] + atr, c[i] - atr,
                                                  'Abwärtstrend + Bullish Engulfing (Kerzen-Studie); Stop/Ziel 1 ATR'))

        # ---- Uhrzeit-Effekte, nur US-Indexfutures
        if market in INDEX_MARKETS:
            t = _ny(b['time'])
            close_ts = int(datetime(t.year, t.month, t.day, 16, 0, tzinfo=NY).timestamp())
            if t.hour == 9 and t.minute == 30 and c[i] != o[i]:
                side = 'LONG' if c[i] > o[i] else 'SHORT'
                stop = l[i] if side == 'LONG' else h[i]
                risk = abs(c[i] - stop)
                if risk > 0:
                    tp = c[i] + 10 * risk if side == 'LONG' else c[i] - 10 * risk
                    emit('orb5', i, _sig('orb5', side, b, c[i], stop, tp,
                                         'Richtung der ersten 5 Min. ab 9:30; Stop anderes Kerzenende; 10R oder 16:00',
                                         time_exit=close_ts))
            if t.hour == 15 and t.minute == 25:
                # Rendite Vortagesschluss (Schluss der 15:55-Kerze) bis 10:00 (Schluss der 9:55-Kerze)
                day = t.date()
                prev_close = ten = None
                for j in range(i - 1, max(0, i - 400), -1):
                    tj = _ny(bars[j]['time'])
                    if ten is None and tj.date() == day and tj.hour == 9 and tj.minute == 55:
                        ten = c[j]
                    if tj.date() < day and tj.hour == 15 and tj.minute == 55:
                        prev_close = c[j]
                        break
                if prev_close and ten and ten != prev_close:
                    side = 'LONG' if ten > prev_close else 'SHORT'
                    d = 1 if side == 'LONG' else -1
                    stop = c[i] - d * 2 * atr
                    emit('imom_last30', i, _sig('imom_last30', side, b, c[i], stop, c[i] + d * 4 * atr,
                                                'Vortagesschluss→10:00 gibt Richtung für 15:30–16:00 vor; Ausstieg 16:00',
                                                time_exit=close_ts))

    cur = bars[-1]['time']
    return [tile(k, NAMES[k], 'green' if found[k] and found[k][-1]['time'] == cur else 'neutral',
                 f"Marktlage jetzt: {regimes[-1]}", found[k],
                 [('Signal letzte Kerze', 'green' if found[k] and found[k][-1]['time'] == cur else 'neutral')])
            for k in KEYS]
