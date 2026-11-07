"""TAURUS Regime-Lab: Welche Lehrbuch-Strategie verdient in welcher Marktlage Geld?

Reine Forschung, keine Orders, kein Zugriff auf die Live-Datenbank.

Ablauf
  1. Kerzen laden (Yahoo via yfinance, oder Cache-Datei).
  2. Marktlage je Kerze mit regime.py (dieselbe Logik wie live), berechnet auf
     dem Zeitrahmen der Strategie. Kein Lookahead.
  3. Jede Strategie erzeugt Signale auf abgeschlossenen Kerzen (LONG und SHORT).
  4. Ausfuehrung: Einstieg naechster Open, Stop vor Ziel bei Doppeltreffer,
     Gap durch den Stop = Ausstieg zum Open, Zeitstopp, eine Position je
     Strategie/Richtung/Markt. Ergebnis in R NACH Kosten.
  5. Auswertung je Strategie x Richtung x Marktlage, getrennt nach
     In-Sample (erste 60 % der Zeit) und Out-of-Sample (letzte 40 %).

Playbook-Kriterien (vor dem Test festgelegt, nicht nachtraeglich angepasst):
  * In-Sample:  n >= MIN_N_IS, Ø R > 0
  * Out-of-Sample: n >= MIN_N_OOS, Ø R > 0
  * gesamt t-Wert >= 1.5 und in mindestens der Haelfte der Maerkte positiv
Alle Parameter sind Lehrbuch-Standardwerte und wurden NICHT optimiert.

Beispiel:
  python regime_lab.py --download --tf 1h --cache lab_1h.json.gz --out lab_out/1h
"""
import argparse
import gzip
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone

import regime as rg

YAHOO = {'nq': 'NQ=F', 'es': 'ES=F', 'gc': 'GC=F', 'btc': 'BTC-USD', 'eth': 'ETH-USD', 'sol': 'SOL-USD'}
CRYPTO = ('btc', 'eth', 'sol')
# Futures: Kosten je Kontrakt-Rundreise in Preispunkten (Kommission / Punktwert + 2 Ticks Slippage)
FUT_COST = {'nq': 1.0 / 2.0 + 2 * 0.25, 'es': 1.0 / 5.0 + 2 * 0.25, 'gc': 1.6 / 10.0 + 2 * 0.10}
CRYPTO_COST_RATE = 2 * (0.001 + 0.0002)          # Binance-Gebuehr + Slippage, beide Seiten
PERIOD = {'1h': '730d', '15m': '60d', '5m': '60d'}
IS_SHARE = 0.6
MAX_COST_SHARE = 0.10
MIN_N_IS, MIN_N_OOS = 30, 15
REGIMES = ('TREND_HOCH', 'TREND_RUNTER', 'RANGE', 'CHOP', 'UEBERGANG')


# ------------------------------------------------------------------ Indikatoren

def ema(v, n):
    out, a, last = [None] * len(v), 2 / (n + 1), None
    for i, x in enumerate(v):
        last = x if last is None else a * x + (1 - a) * last
        out[i] = last if i >= n - 1 else None
    return out


def sma(v, n):
    out, s = [None] * len(v), 0.0
    for i, x in enumerate(v):
        s += x
        if i >= n:
            s -= v[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def stdev(v, n):
    out = [None] * len(v)
    for i in range(n - 1, len(v)):
        w = v[i - n + 1:i + 1]
        m = sum(w) / n
        out[i] = math.sqrt(sum((x - m) ** 2 for x in w) / n)
    return out


def rsi(c, n):
    out = [None] * len(c)
    if len(c) <= n:
        return out
    g = sum(max(c[i] - c[i - 1], 0) for i in range(1, n + 1)) / n
    l = sum(max(c[i - 1] - c[i], 0) for i in range(1, n + 1)) / n
    out[n] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    for i in range(n + 1, len(c)):
        d = c[i] - c[i - 1]
        g = (g * (n - 1) + max(d, 0)) / n
        l = (l * (n - 1) + max(-d, 0)) / n
        out[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    return out


def atr(h, l, c, n=14):
    out, last = [None] * len(c), None
    for i in range(1, len(c)):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        last = tr if last is None else (last * (n - 1) + tr) / n
        if i >= n:
            out[i] = last
    return out


def stoch_k(h, l, c, n=14, smooth=3):
    raw = [None] * len(c)
    for i in range(n - 1, len(c)):
        hh, ll = max(h[i - n + 1:i + 1]), min(l[i - n + 1:i + 1])
        raw[i] = 50.0 if hh == ll else 100 * (c[i] - ll) / (hh - ll)
    out = [None] * len(c)
    for i in range(n - 1 + smooth - 1, len(c)):
        out[i] = sum(raw[i - smooth + 1:i + 1]) / smooth
    return out


def supertrend_dir(h, l, c, a, mult=3.0):
    """+1 / -1 je Kerze (klassischer Supertrend 10/3 auf ATR14-Basis)."""
    n = len(c)
    d = [0] * n
    up = dn = None
    for i in range(n):
        if a[i] is None:
            continue
        mid = (h[i] + l[i]) / 2
        bu, bd = mid - mult * a[i], mid + mult * a[i]
        if up is None:
            up, dn, d[i] = bu, bd, 1
            continue
        up = max(bu, up) if c[i - 1] > up else bu
        dn = min(bd, dn) if c[i - 1] < dn else bd
        prev = d[i - 1] or 1
        d[i] = 1 if (prev == -1 and c[i] > dn) else -1 if (prev == 1 and c[i] < up) else prev
    return d


class Ind:
    def __init__(self, bars):
        self.o = [b['open'] for b in bars]
        self.h = [b['high'] for b in bars]
        self.l = [b['low'] for b in bars]
        self.c = c = [b['close'] for b in bars]
        self.t = [int(b['time']) for b in bars]
        self.atr = atr(self.h, self.l, c)
        self.e20, self.e50, self.e200 = ema(c, 20), ema(c, 50), ema(c, 200)
        self.s5, self.s20, self.s50, self.s200 = sma(c, 5), sma(c, 20), sma(c, 50), sma(c, 200)
        self.sd20, self.sd50 = stdev(c, 20), stdev(c, 50)
        self.rsi2 = rsi(c, 2)
        self.stk = stoch_k(self.h, self.l, c)
        e12, e26 = ema(c, 12), ema(c, 26)
        self.macd = [None if a is None or b is None else a - b for a, b in zip(e12, e26)]
        first = next((i for i, x in enumerate(self.macd) if x is not None), len(c))
        sig = ema([x for x in self.macd[first:]], 9)
        self.macd_sig = [None] * first + sig
        self.st = supertrend_dir(self.h, self.l, c, self.atr)
        # Vortages-Hoch/Tief (UTC-Kalendertag), nur abgeschlossene Tage
        self.pdh, self.pdl = [None] * len(c), [None] * len(c)
        day, cur, prev = None, None, None
        for i, t in enumerate(self.t):
            d = t // 86400
            if d != day:
                prev, cur, day = cur, [self.h[i], self.l[i]], d
            else:
                cur[0], cur[1] = max(cur[0], self.h[i]), min(cur[1], self.l[i])
            if prev:
                self.pdh[i], self.pdl[i] = prev


# ------------------------------------------------------------------ Strategien
# Jede Funktion: (ind, i, side) -> None oder dict(stop=..., tp=None|preis, exit=None|'sma5'|'mean',
#                 trail=None|ATR-Faktor, hold=max. Kerzen). side +1 = LONG, -1 = SHORT.

def _hh(x, i, n):
    return max(x[i - n:i])


def _ll(x, i, n):
    return min(x[i - n:i])


def s_donchian(d, i, s):
    c, a = d.c[i], d.atr[i]
    if s > 0 and c > _hh(d.h, i, 20) and d.c[i - 1] <= _hh(d.h, i - 1, 20):
        return dict(stop=c - 2 * a, trail=3.0, hold=60)
    if s < 0 and c < _ll(d.l, i, 20) and d.c[i - 1] >= _ll(d.l, i - 1, 20):
        return dict(stop=c + 2 * a, trail=3.0, hold=60)


def s_ema_pullback(d, i, s):
    c, a, e20, e50 = d.c[i], d.atr[i], d.e20[i], d.e50[i]
    if s > 0 and e20 > e50 and c > e50 and d.l[i] <= e20 < c and c > d.o[i]:
        stop = min(d.l[i - 2:i + 1]) - 0.2 * a
        return dict(stop=stop, tp=c + 2 * (c - stop), hold=40)
    if s < 0 and e20 < e50 and c < e50 and d.h[i] >= e20 > c and c < d.o[i]:
        stop = max(d.h[i - 2:i + 1]) + 0.2 * a
        return dict(stop=stop, tp=c - 2 * (stop - c), hold=40)


def s_macd_trend(d, i, s):
    m, g, m1, g1 = d.macd[i], d.macd_sig[i], d.macd[i - 1], d.macd_sig[i - 1]
    if None in (m, g, m1, g1, d.e200[i]):
        return None
    c, a = d.c[i], d.atr[i]
    if s > 0 and m1 <= g1 and m > g and c > d.e200[i]:
        return dict(stop=c - 2 * a, trail=3.0, hold=60)
    if s < 0 and m1 >= g1 and m < g and c < d.e200[i]:
        return dict(stop=c + 2 * a, trail=3.0, hold=60)


def s_supertrend(d, i, s):
    c, a = d.c[i], d.atr[i]
    if d.st[i] == s and d.st[i - 1] == -s:
        return dict(stop=c - s * 2.5 * a, trail=3.0, hold=80)


def s_inside_break(d, i, s):
    # Kerze i-1 ist Inside Bar der Mutterkerze i-2, Kerze i schliesst ausserhalb der Mutter
    mh, ml = d.h[i - 2], d.l[i - 2]
    if not (d.h[i - 1] <= mh and d.l[i - 1] >= ml):
        return None
    c = d.c[i]
    if s > 0 and c > mh and d.c[i] > (d.e50[i] or c):
        stop = ml
        return dict(stop=stop, tp=c + 2 * (c - stop), hold=40) if c > stop else None
    if s < 0 and c < ml and d.c[i] < (d.e50[i] or c):
        stop = mh
        return dict(stop=stop, tp=c - 2 * (stop - c), hold=40) if stop > c else None


def s_rsi2_trend(d, i, s):
    # Connors: Ruecksetzer im langfristigen Trend kaufen, Ausstieg ueber SMA5
    r, c, a = d.rsi2[i], d.c[i], d.atr[i]
    if r is None or d.s200[i] is None:
        return None
    if s > 0 and c > d.s200[i] and r < 10:
        return dict(stop=c - 3 * a, exit='sma5', hold=15)
    if s < 0 and c < d.s200[i] and r > 90:
        return dict(stop=c + 3 * a, exit='sma5', hold=15)


def s_keltner_break(d, i, s):
    c, a, e = d.c[i], d.atr[i], d.e20[i]
    if s > 0 and c > e + 2 * a and d.c[i - 1] <= d.e20[i - 1] + 2 * d.atr[i - 1]:
        return dict(stop=c - 2 * a, trail=3.0, hold=60)
    if s < 0 and c < e - 2 * a and d.c[i - 1] >= d.e20[i - 1] - 2 * d.atr[i - 1]:
        return dict(stop=c + 2 * a, trail=3.0, hold=60)


def s_nr7_break(d, i, s):
    j = i - 1
    rng = [d.h[k] - d.l[k] for k in range(j - 6, j + 1)]
    if rng[-1] != min(rng):
        return None
    c = d.c[i]
    if s > 0 and c > d.h[j]:
        stop = d.l[j]
        return dict(stop=stop, tp=c + 2 * (c - stop), hold=30) if c > stop else None
    if s < 0 and c < d.l[j]:
        stop = d.h[j]
        return dict(stop=stop, tp=c - 2 * (stop - c), hold=30) if stop > c else None


def s_bb_reentry(d, i, s):
    m, sd, m1, sd1 = d.s20[i], d.sd20[i], d.s20[i - 1], d.sd20[i - 1]
    if None in (m, sd, m1, sd1):
        return None
    c, a = d.c[i], d.atr[i]
    if s > 0 and d.c[i - 1] < m1 - 2 * sd1 and c > m - 2 * sd and c > d.o[i]:
        stop = min(d.l[i - 1], d.l[i]) - 0.25 * a
        return dict(stop=stop, tp=m, hold=30) if m - c >= 0.8 * (c - stop) else None
    if s < 0 and d.c[i - 1] > m1 + 2 * sd1 and c < m + 2 * sd and c < d.o[i]:
        stop = max(d.h[i - 1], d.h[i]) + 0.25 * a
        return dict(stop=stop, tp=m, hold=30) if c - m >= 0.8 * (stop - c) else None


def s_rsi2_fade(d, i, s):
    r, c, a = d.rsi2[i], d.c[i], d.atr[i]
    if r is None:
        return None
    if s > 0 and r < 5:
        return dict(stop=c - 1.5 * a, exit='sma5', hold=15)
    if s < 0 and r > 95:
        return dict(stop=c + 1.5 * a, exit='sma5', hold=15)


def s_stoch_fade(d, i, s):
    k, k1, c, a = d.stk[i], d.stk[i - 1], d.c[i], d.atr[i]
    if k is None or k1 is None:
        return None
    if s > 0 and k1 <= 20 < k:
        return dict(stop=c - 1.5 * a, tp=c + 1.5 * 1.5 * a, hold=30)
    if s < 0 and k1 >= 80 > k:
        return dict(stop=c + 1.5 * a, tp=c - 1.5 * 1.5 * a, hold=30)


def s_zscore_fade(d, i, s):
    m, sd, c, a = d.s50[i], d.sd50[i], d.c[i], d.atr[i]
    if m is None or not sd:
        return None
    z = (c - m) / sd
    if s > 0 and z < -2:
        return dict(stop=c - 1.5 * a, exit='mean', hold=40)
    if s < 0 and z > 2:
        return dict(stop=c + 1.5 * a, exit='mean', hold=40)


def s_pdhl_fade(d, i, s):
    pdh, pdl, c, a = d.pdh[i], d.pdl[i], d.c[i], d.atr[i]
    if pdh is None:
        return None
    mid = (pdh + pdl) / 2
    if s < 0 and d.h[i] > pdh and c < pdh and c < d.o[i]:
        stop = d.h[i] + 0.2 * a
        return dict(stop=stop, tp=max(mid, c - 2 * (stop - c)), hold=30) if c > mid else None
    if s > 0 and d.l[i] < pdl and c > pdl and c > d.o[i]:
        stop = d.l[i] - 0.2 * a
        return dict(stop=stop, tp=min(mid, c + 2 * (c - stop)), hold=30) if c < mid else None


def s_turtle_soup(d, i, s):
    # Falscher Ausbruch: neues 20er-Tief/-Hoch, Schluss wieder innerhalb
    c, a = d.c[i], d.atr[i]
    lo, hi = _ll(d.l, i, 20), _hh(d.h, i, 20)
    if s > 0 and d.l[i] < lo and c > lo:
        stop = d.l[i] - 0.1 * a
        return dict(stop=stop, tp=c + 2 * (c - stop), hold=30)
    if s < 0 and d.h[i] > hi and c < hi:
        stop = d.h[i] + 0.1 * a
        return dict(stop=stop, tp=c - 2 * (stop - c), hold=30)


STRATEGIES = {
    # Trendfolge
    'donchian20': ('Donchian-20-Ausbruch, Trailing 3 ATR', s_donchian),
    'ema_pullback': ('Rücksetzer an EMA20 im EMA20/50-Trend, 2R', s_ema_pullback),
    'macd_trend': ('MACD-Kreuz in Richtung EMA200, Trailing 3 ATR', s_macd_trend),
    'supertrend': ('Supertrend(10,3)-Wechsel, Trailing 3 ATR', s_supertrend),
    'inside_break': ('Inside-Bar-Ausbruch mit EMA50-Filter, 2R', s_inside_break),
    'rsi2_trend': ('Connors RSI(2) im SMA200-Trend, Ausstieg SMA5', s_rsi2_trend),
    'keltner_break': ('Keltner-Ausbruch (EMA20 ± 2 ATR), Trailing 3 ATR', s_keltner_break),
    'nr7_break': ('NR7-Ausbruch, 2R', s_nr7_break),
    # Mean Reversion / Seitwaerts
    'bb_reentry': ('Bollinger-Rückkehr, Ziel SMA20', s_bb_reentry),
    'rsi2_fade': ('RSI(2) extrem ohne Trendfilter, Ausstieg SMA5', s_rsi2_fade),
    'stoch_fade': ('Stochastik 14/3 kreuzt 20/80, 1.5R', s_stoch_fade),
    'zscore_fade': ('Z-Score 50 > 2σ, Ausstieg am Mittelwert', s_zscore_fade),
    'pdhl_fade': ('Fehlausbruch Vortageshoch/-tief, Ziel Tagesmitte', s_pdhl_fade),
    'turtle_soup': ('Falscher 20er-Ausbruch (Turtle Soup), 2R', s_turtle_soup),
}


# ------------------------------------------------------------------ Ausfuehrung

def cost_price(market, entry):
    return entry * CRYPTO_COST_RATE if market in CRYPTO else FUT_COST[market]


def simulate(market, bars, ind, regimes, key, fn, side, start=210):
    trades = []
    n = len(bars)
    diffs = sorted(ind.t[k + 1] - ind.t[k] for k in range(min(n - 1, 2000)))
    step = diffs[len(diffs) // 2]
    i = start
    while i < n - 2:
        a = ind.atr[i]
        if not a:
            i += 1
            continue
        sig = fn(ind, i, side)
        if not sig:
            i += 1
            continue
        e_i = i + 1
        entry = ind.o[e_i]
        stop = sig['stop']
        if abs(entry - ind.c[i]) > 0.5 * a:   # wie live GAP_INVALID: Einstieg zu weit vom Signal
            i += 1
            continue
        risk = (entry - stop) * side
        if risk < 0.25 * a:                   # Gap ueber den Stop hinaus / unsinnig enger Stop
            i += 1
            continue
        if market not in CRYPTO and cost_price(market, entry) > MAX_COST_SHARE * risk:   # wie live: COST_TOO_HIGH
            i += 1
            continue
        tp = sig.get('tp')
        if tp is not None and (tp - entry) * side <= 0:
            i += 1
            continue
        best = entry
        exit_p = reason = None
        j = e_i
        last = min(n - 1, e_i + sig['hold'])
        while j <= last:
            o, h, l, c = ind.o[j], ind.h[j], ind.l[j], ind.c[j]
            # Gap-Ausstieg zum Open nur nach echter Handelspause (Zeitluecke), sonst Datenfehler
            if j > e_i and ind.t[j] - ind.t[j - 1] > step and (o - stop) * side <= 0:
                exit_p, reason = o, 'GAP_STOP'; break
            if (l if side > 0 else h) * side <= stop * side:
                exit_p, reason = stop, 'STOP'; break
            if tp is not None and (h if side > 0 else l) * side >= tp * side:
                exit_p, reason = (max(o, tp) if side > 0 else min(o, tp)) if j > e_i else tp, 'ZIEL'; break
            # Schlusskurs-Regeln
            if sig.get('trail'):
                best = max(best, h) if side > 0 else min(best, l)
                new = best - side * sig['trail'] * a
                stop = max(stop, new) if side > 0 else min(stop, new)
            ex = sig.get('exit')
            if ex == 'sma5' and ind.s5[j] is not None and (c - ind.s5[j]) * side > 0:
                exit_p, reason = c, 'SMA5'; break
            if ex == 'mean' and ind.s50[j] is not None and (c - ind.s50[j]) * side >= 0:
                exit_p, reason = c, 'MITTE'; break
            if j == last:
                exit_p, reason = c, 'ZEIT'; break
            j += 1
        if exit_p is None:
            break
        gross = (exit_p - entry) * side
        r_net = (gross - cost_price(market, entry)) / risk
        trades.append(dict(market=market, strategy=key, side='LONG' if side > 0 else 'SHORT',
                           time=ind.t[i], regime=regimes[i], r=r_net, reason=reason,
                           bars=j - e_i + 1, cost_r=cost_price(market, entry) / risk))
        i = j + 1                              # eine Position je Strategie/Richtung/Markt
    return trades


def run(candles, tf):
    out = []
    for market, bars in candles.items():
        if len(bars) < 400:
            print(market, 'zu wenige Kerzen', len(bars)); continue
        ind = Ind(bars)
        regs = [rg.classify(f)['regime'] if f else 'UNBEKANNT' for f in rg.compute_series(bars)]
        t0, t1 = ind.t[210], ind.t[-1]
        cut = t0 + IS_SHARE * (t1 - t0)
        for key, (_, fn) in STRATEGIES.items():
            for side in (1, -1):
                for tr in simulate(market, bars, ind, regs, key, fn, side):
                    tr['sample'] = 'IS' if tr['time'] < cut else 'OOS'
                    out.append(tr)
        print(f'{market} {tf}: {len(bars)} Kerzen, Marktlagen ' +
              ', '.join(f'{r} {regs.count(r) / len(regs):.0%}' for r in REGIMES))
    return out


# ------------------------------------------------------------------ Auswertung

def stat(rs):
    n = len(rs)
    if not n:
        return dict(n=0, avg=None, win=None, t=None, sum=0.0)
    m = sum(rs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in rs) / (n - 1)) if n > 1 else 0
    return dict(n=n, avg=m, win=sum(1 for x in rs if x > 0) / n, t=(m / (sd / math.sqrt(n)) if sd else None), sum=sum(rs))


def evaluate(trades):
    cells = defaultdict(list)
    for t in trades:
        cells[(t['strategy'], t['side'], t['regime'])].append(t)
        cells[(t['strategy'], t['side'], 'ALLE')].append(t)
    rows = []
    for (k, side, reg), ts in cells.items():
        if reg == 'UNBEKANNT':
            continue
        allr = stat([t['r'] for t in ts])
        isr = stat([t['r'] for t in ts if t['sample'] == 'IS'])
        oos = stat([t['r'] for t in ts if t['sample'] == 'OOS'])
        mk = defaultdict(list)
        for t in ts:
            mk[t['market']].append(t['r'])
        mk_pos = sum(1 for v in mk.values() if len(v) >= 5 and sum(v) > 0)
        mk_n = sum(1 for v in mk.values() if len(v) >= 5)
        passed = (reg != 'ALLE' and isr['n'] >= MIN_N_IS and isr['avg'] > 0 and oos['n'] >= MIN_N_OOS
                  and oos['avg'] > 0 and (allr['t'] or 0) >= 1.5 and mk_n and mk_pos * 2 >= mk_n)
        rows.append(dict(strategy=k, side=side, regime=reg, all=allr, IS=isr, OOS=oos,
                         markets={m: stat(v) for m, v in mk.items()}, mk_pos=mk_pos, mk_n=mk_n, passed=bool(passed),
                         cost_r=sum(t['cost_r'] for t in ts) / len(ts)))
    return rows


def _f(x, d=2, sign=True):
    return '–' if x is None else (f'{x:+.{d}f}' if sign else f'{x:.{d}f}')


def report(rows, tf, meta):
    L = [f'# TAURUS Regime-Lab · {tf}', '',
         f"Daten: {meta['span']} · Märkte: {', '.join(meta['markets'])} · Trades: {meta['trades']} · "
         f'IS = erste {IS_SHARE:.0%} der Zeit, OOS = Rest. Ergebnis in R nach Kosten.', '',
         '## Playbook (bestanden: IS>0, OOS>0, t≥1.5, ≥ Hälfte der Märkte positiv)', '',
         '| Marktlage | Strategie | Seite | n | Ø R | Treffer | t | Ø R IS (n) | Ø R OOS (n) | Märkte + | je Markt Ø R (n) |',
         '|---|---|---|---|---|---|---|---|---|---|---|']
    ok = sorted([r for r in rows if r['passed']], key=lambda r: (REGIMES.index(r['regime']), -r['all']['avg']))
    for r in ok:
        L.append(f"| {r['regime']} | {r['strategy']} | {r['side']} | {r['all']['n']} | {_f(r['all']['avg'])} | "
                 f"{r['all']['win']:.0%} | {_f(r['all']['t'], 1, False)} | {_f(r['IS']['avg'])} ({r['IS']['n']}) | "
                 f"{_f(r['OOS']['avg'])} ({r['OOS']['n']}) | {r['mk_pos']}/{r['mk_n']} | "
                 + ', '.join(f"{m} {_f(v['avg'])} ({v['n']})" for m, v in sorted(r['markets'].items())) + ' |')
    if not ok:
        L.append('| – | keine Strategie besteht | | | | | | | | |')
    L += ['', '## Matrix Ø R (n) je Marktlage', '',
          '| Strategie | Seite | ALLE | ' + ' | '.join(REGIMES) + ' | Kosten R |',
          '|---|---|---|' + '---|' * len(REGIMES) + '---|']
    idx = {(r['strategy'], r['side'], r['regime']): r for r in rows}
    for k in STRATEGIES:
        for side in ('LONG', 'SHORT'):
            cells = []
            for reg in ('ALLE',) + REGIMES:
                r = idx.get((k, side, reg))
                cells.append('–' if not r else f"{'**' if r['passed'] else ''}{_f(r['all']['avg'])} ({r['all']['n']}){'**' if r['passed'] else ''}")
            a = idx.get((k, side, 'ALLE'))
            L.append(f'| {k} | {side} | ' + ' | '.join(cells) + f" | {_f(a['cost_r'] if a else None, 2, False)} |")
    L += ['', '## Strategien', ''] + [f'- **{k}**: {d}' for k, (d, _) in STRATEGIES.items()]
    return '\n'.join(L) + '\n'


# ------------------------------------------------------------------ Daten

def download(markets, tf):
    import yfinance as yf
    out = {}
    for m in markets:
        df = yf.Ticker(YAHOO[m]).history(period=PERIOD[tf], interval=tf, auto_adjust=False, prepost=True, timeout=60)
        step = {'1h': 3600, '15m': 900, '5m': 300}[tf]
        now = datetime.now(timezone.utc).timestamp()
        rows = []
        for idx, r in df.iterrows():
            t = int(idx.to_pydatetime().astimezone(timezone.utc).timestamp())
            o, h, l, c = (float(r[k]) for k in ('Open', 'High', 'Low', 'Close'))
            if t + step > now or not all(math.isfinite(x) for x in (o, h, l, c)) or not l <= min(o, c) <= max(o, c) <= h:
                continue
            if h == l and not (r['Volume'] or 0):         # eingefrorene Kerze
                continue
            rows.append(dict(time=t, open=o, high=h, low=l, close=c, volume=float(r['Volume'] or 0)))
        out[m] = rows
        print(m, tf, len(rows))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tf', default='1h', choices=tuple(PERIOD))
    ap.add_argument('--markets', default=','.join(YAHOO))
    ap.add_argument('--cache')
    ap.add_argument('--download', action='store_true')
    ap.add_argument('--out', default='lab_out')
    a = ap.parse_args()
    markets = a.markets.split(',')
    if a.cache and os.path.exists(a.cache) and not a.download:
        with gzip.open(a.cache, 'rt') as f:
            candles = json.load(f)
    else:
        candles = download(markets, a.tf)
        if a.cache:
            with gzip.open(a.cache, 'wt') as f:
                json.dump(candles, f)
    candles = {m: v for m, v in candles.items() if m in markets}
    trades = run(candles, a.tf)
    rows = evaluate(trades)
    ts = [b['time'] for v in candles.values() for b in v]
    fmt = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime('%d.%m.%Y')
    meta = dict(span=f'{fmt(min(ts))} – {fmt(max(ts))}', markets=sorted(candles), trades=len(trades))
    os.makedirs(a.out, exist_ok=True)
    md = report(rows, a.tf, meta)
    open(os.path.join(a.out, 'lab.md'), 'w').write(md)
    with gzip.open(os.path.join(a.out, 'lab.json.gz'), 'wt') as f:
        json.dump(dict(meta=meta, rows=rows), f)
    print(md)


if __name__ == '__main__':
    main()
