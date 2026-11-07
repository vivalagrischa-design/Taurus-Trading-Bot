"""TAURUS V9: Strategien je 1h-Marktlage (nur Futures, nur LAB).

Grundlage: Regime-Lab (research/REGIME_LAB_FAZIT.md), 1h-Kerzen ueber 2 Jahre,
NQ/ES/GC, nach Kosten, In-Sample UND Out-of-Sample positiv, alle Maerkte positiv.

  Marktlage 1h   Strategie                                       Backtest
  TREND_RUNTER   v9_bb_dip        Bollinger-Rueckkehr LONG, Ziel SMA20    +0.21 R (n 285)
  TREND_RUNTER   v9_stoch_dip     Stochastik 14/3 kreuzt 20 LONG, 1.5R    +0.15 R (n 464)
  UEBERGANG      v9_macd_long     MACD-Kreuz ueber EMA200, Trailing 3 ATR  +0.28 R (n 205)
  RANGE          v9_st_short      Supertrend-Wechsel SHORT, Trailing 3 ATR +0.19 R (n 127)
  CHOP           v9_keltner_long  Keltner-Ausbruch LONG, Trailing 3 ATR    +0.50 R (n 70)
  CHOP           v9_macd_short    MACD-Kreuz unter EMA200, Trailing 3 ATR  +0.31 R (n 100)

Ablauf live:
  * Signal auf der abgeschlossenen 1h-Kerze, Marktlage aus regime.py auf 1h-Kerzen.
  * Das Signal wird auf die letzte 5M-Kerze dieser Stunde gelegt (Start HH:55), damit
    die Paper-Engine wie gewohnt zum naechsten 5M-Open einsteigt (= 1h-Open).
  * Ausstiege wie im Backtest (siehe EXITS): fester Zielkurs bzw. Trailing ab Einstieg
    mit 3 ATR(1h), Zeitstopp nach HOLD Stunden. Das allgemeine 1R-Trailing gilt NICHT.

Die Regeln selbst stammen 1:1 aus regime_lab.py (eine Quelle der Wahrheit).
"""
import os
import time

import regime as rg
import regime_lab as lab

FUTURES_MARKETS = ('nq', 'mes', 'mgc')
HOUR = 3600
MIN_1H_BARS = 260                       # EMA200 + Aufwaermphase der Marktlage

# key: (Name, Regel aus regime_lab, Seite, erlaubte 1h-Marktlage)
STRATEGIES = {
    'v9_bb_dip': ('V9 · Abwärts: Bollinger-Rückkehr Long', lab.s_bb_reentry, 1, 'TREND_RUNTER'),
    'v9_stoch_dip': ('V9 · Abwärts: Stochastik-Umkehr Long', lab.s_stoch_fade, 1, 'TREND_RUNTER'),
    'v9_macd_long': ('V9 · Übergang: MACD-Kreuz Long', lab.s_macd_trend, 1, 'UEBERGANG'),
    'v9_st_short': ('V9 · Seitwärts: Supertrend Short', lab.s_supertrend, -1, 'RANGE'),
    'v9_keltner_long': ('V9 · Chop: Keltner-Ausbruch Long', lab.s_keltner_break, 1, 'CHOP'),
    'v9_macd_short': ('V9 · Chop: MACD-Kreuz Short', lab.s_macd_trend, -1, 'CHOP'),
}
KEYS = tuple(STRATEGIES)
FAR_TARGET_R = 20.0                     # Trailing-Strategien: Ziel nur formal (Engine braucht einen TP)

# Ausstiegsregeln fuer paper_engine: trail = Trailing-Abstand als Vielfaches des Anfangsrisikos
# (Stop 2 ATR, Trailing 3 ATR -> 1.5; Supertrend Stop 2.5 ATR -> 1.2). None = kein Trailing.
EXITS = {
    'v9_bb_dip': None, 'v9_stoch_dip': None,
    'v9_macd_long': 1.5, 'v9_macd_short': 1.5, 'v9_keltner_long': 1.5, 'v9_st_short': 1.2,
}

_HOURLY = {}                            # market -> Liste 1h-Kerzen (Tests/Backtest)
_CACHE = {}                             # market -> (Schluessel, Ergebnis)


def set_hourly(market, bars):
    """1h-Kerzen vorgeben (Backtest/Tests). None entfernt die Vorgabe."""
    if bars is None:
        _HOURLY.pop(market, None)
    else:
        _HOURLY[market] = sorted(bars, key=lambda b: int(b['time']))
    _CACHE.pop(market, None)


def _hourly(market):
    if market in _HOURLY:
        return _HOURLY[market]
    if os.environ.get('TAURUS_V9_FEED', 'on').lower() in ('off', '0', 'false', 'no'):
        return []
    from yahoo_feed import fetch_market
    return fetch_market(market, '1h').get('candles') or []


def _gate_on():
    from regime_gate import enabled
    return enabled()


def hourly_signals(bars1h, market):
    """Alle V9-Signale auf 1h-Kerzen (nur abgeschlossene). Rueckgabe: (key -> Liste, Marktlagen)."""
    out = {k: [] for k in KEYS}
    if len(bars1h) < MIN_1H_BARS:
        return out, []
    ind = lab.Ind(bars1h)
    regs = [rg.classify(f)['regime'] if f else 'UNBEKANNT' for f in rg.compute_series(bars1h)]
    gate = _gate_on()
    from strategies import signal_with_params
    for key, (name, fn, side, regime) in STRATEGIES.items():
        busy_until = -1
        for i in range(210, len(bars1h)):
            if i <= busy_until or not ind.atr[i]:
                continue
            if gate and regs[i] != regime:
                continue
            sig = fn(ind, i, side)
            if not sig:
                continue
            c, stop = ind.c[i], sig['stop']
            risk = (c - stop) * side
            if risk <= 0:
                continue
            tp = sig.get('tp')
            if tp is None:
                tp = c + side * FAR_TARGET_R * risk
            if (tp - c) * side <= 0:
                continue
            t1h = int(bars1h[i]['time'])
            s = signal_with_params(
                key, 'LONG' if side > 0 else 'SHORT', t1h + HOUR - 300, c, stop, tp,
                f'{name} · 1h-Marktlage {regs[i]} · {lab.STRATEGIES[_lab_key(fn)][0]}',
                level=c, breakout_time=t1h, timeframe='5m')
            s['time_exit'] = t1h + HOUR + int(sig['hold']) * HOUR
            s['regime_1h'] = regs[i]
            out[key].append(s)
            busy_until = i                 # hoechstens ein Signal je Stunde und Strategie
    return out, regs


def _lab_key(fn):
    return next(k for k, (_, f) in lab.STRATEGIES.items() if f is fn)


def build(bars5m, market='nq'):
    from strategies import tile
    if market not in FUTURES_MARKETS:
        return [tile(k, STRATEGIES[k][0], 'neutral', 'V9 nur für Futures (NQ/MES/MGC)', [], []) for k in KEYS]
    if not bars5m:
        return [tile(k, STRATEGIES[k][0], 'neutral', 'Keine 5M-Kerzen', [], []) for k in KEYS]
    last5 = int(bars5m[-1]['time'])
    first5 = int(bars5m[0]['time'])
    # Kausal: nur 1h-Kerzen, die bis zum Ende der letzten 5M-Kerze abgeschlossen sind
    hourly = [b for b in _hourly(market) if int(b['time']) + HOUR <= last5 + 300]
    ck = (len(hourly), int(hourly[-1]['time']) if hourly else 0, _gate_on())
    cached = _CACHE.get(market)
    if cached and cached[0] == ck:
        sigs, regs = cached[1]
    else:
        sigs, regs = hourly_signals(hourly, market)
        _CACHE[market] = (ck, (sigs, regs))
    now_reg = regs[-1] if regs else 'UNBEKANNT'
    tiles = []
    for key, (name, _, _, regime) in STRATEGIES.items():
        visible = [s for s in sigs[key] if first5 <= s['time'] <= last5]
        recent = bool(visible and visible[-1]['time'] == last5)
        active = now_reg == regime
        detail = (f'1h-Marktlage jetzt: {now_reg} · handelt nur in {regime} · '
                  + (f'{len(hourly)} 1h-Kerzen' if len(hourly) >= MIN_1H_BARS else f'wartet auf {MIN_1H_BARS} 1h-Kerzen ({len(hourly)})'))
        tiles.append(tile(key, name, 'green' if recent else 'yellow' if active else 'neutral', detail, visible,
                          [('Passende 1h-Marktlage', 'green' if active else 'neutral'),
                           ('Signal letzte Stunde', 'green' if recent else 'neutral')]))
    return tiles


def regime_now(market):
    """Aktuelle 1h-Marktlage fuer die Anzeige."""
    hourly = _hourly(market)
    if len(hourly) < 80:
        return 'UNBEKANNT'
    f = rg.compute_series(hourly)[-1]
    return rg.classify(f)['regime']


def hourly_from_5m(bars5m):
    """1h-Kerzen aus 5M-Kerzen (Backtest/Fallback). Eine Stunde zaehlt nur, wenn ihre
    letzte 5M-Kerze (HH:55) vorhanden ist, also die Stunde abgeschlossen ist."""
    out, cur = [], None
    for b in sorted(bars5m, key=lambda x: int(x['time'])):
        h = int(b['time']) // HOUR * HOUR
        if cur is None or cur['time'] != h:
            if cur and cur['_done']:
                out.append({k: v for k, v in cur.items() if k != '_done'})
            cur = dict(time=h, open=float(b['open']), high=float(b['high']), low=float(b['low']),
                       close=float(b['close']), volume=float(b.get('volume') or 0), _done=False)
        else:
            cur['high'] = max(cur['high'], float(b['high']))
            cur['low'] = min(cur['low'], float(b['low']))
            cur['close'] = float(b['close'])
            cur['volume'] += float(b.get('volume') or 0)
        if int(b['time']) == h + HOUR - 300:
            cur['_done'] = True
    if cur and cur['_done']:
        out.append({k: v for k, v in cur.items() if k != '_done'})
    return out
