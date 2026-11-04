"""TAURUS Kerzen-Studie: Welche 5M-Kerze fuehrt in welcher Marktlage wohin?

Fuer jedes Kerzenmuster (auf abgeschlossener Kerze erkannt) und jede
Marktlage wird gemessen, was danach WIRKLICH passiert ist:

  * Einstieg zum Open der naechsten Kerze (wie live)
  * Klammer +-1 ATR: was wird zuerst erreicht, +1 ATR oder -1 ATR
    (innerhalb von 12 Kerzen = 1 Stunde)? -> p_up / p_down
  * Netto-Erwartung in R fuer die bessere Richtung bei Stop = Ziel = 1 ATR,
    nach Kommission und 2 Ticks Slippage (MNQ/MES/MGC)
  * Vergleich mit der Basisrate: alle Kerzen derselben Marktlage
    (sonst verwechselt man "Aufwaertstrend" mit "gutes Muster")
  * Stabilitaet: erste und zweite Haelfte des Zeitraums getrennt

Gleiche Kerzen-Bausteine wie im Lehrbuch, objektiv definiert. Kein Muster
wird empfohlen, nur gemessen. Viele Kombinationen -> einige wirken
zufaellig gut; deshalb Basisrate, Konfidenzintervall und Haelften-Check.

  python candle_study.py --source yahoo --out candle_out
  python candle_study.py --source archive --archive-dir archives
"""
import argparse
import glob
import math
import os
from collections import defaultdict
from datetime import datetime, timezone

import paper_engine as pe
import regime as rg

HORIZON = 12
MIN_N = 100


def patterns(bars, i, atr):
    """Liste der Muster auf Kerze i (nur Kerzen <= i)."""
    b, p, q = bars[i], bars[i - 1], bars[i - 2]
    o, h, l, c = b['open'], b['high'], b['low'], b['close']
    rng = h - l
    if rng <= 0 or atr <= 0:
        return []
    body = abs(c - o); up_w = h - max(o, c); lo_w = min(o, c) - l
    bull, bear = c > o, c < o
    out = []
    if p['close'] < p['open'] and bull and o <= p['close'] and c >= p['open'] and body > abs(p['close'] - p['open']):
        out.append('bull_engulfing')
    if p['close'] > p['open'] and bear and o >= p['close'] and c <= p['open'] and body > abs(p['close'] - p['open']):
        out.append('bear_engulfing')
    if lo_w >= 2 * body and up_w <= 0.25 * rng and rng >= 0.5 * atr:
        out.append('hammer')
    if up_w >= 2 * body and lo_w <= 0.25 * rng and rng >= 0.5 * atr:
        out.append('shooting_star')
    if body <= 0.1 * rng and rng >= 0.5 * atr:
        out.append('doji')
    if body >= 0.8 * rng and rng >= 1.0 * atr:
        out.append('bull_marubozu' if bull else 'bear_marubozu' if bear else None)
    if h < p['high'] and l > p['low']:
        out.append('inside_bar')
    if h > p['high'] and l < p['low']:
        out.append('outside_bar_up' if bull else 'outside_bar_down' if bear else None)
    if all(x['close'] > x['open'] for x in (q, p, b)) and q['close'] < p['close'] < c:
        out.append('three_up')
    if all(x['close'] < x['open'] for x in (q, p, b)) and q['close'] > p['close'] > c:
        out.append('three_down')
    if rng >= 2 * atr:
        out.append('big_range_up' if bull else 'big_range_down' if bear else None)
    if rng >= atr and (c - l) >= 0.9 * rng:
        out.append('close_at_high')
    if rng >= atr and (h - c) >= 0.9 * rng:
        out.append('close_at_low')
    return [x for x in out if x]


def first_touch(bars, i, atr, horizon=HORIZON):
    """Ab Open der Kerze i+1: wird +1 ATR oder -1 ATR zuerst erreicht? Beide in einer Kerze -> unklar."""
    if i + 1 >= len(bars):
        return None
    e = bars[i + 1]['open']
    up, dn = e + atr, e - atr
    for b in bars[i + 1:i + 1 + horizon]:
        if b['time'] - bars[i]['time'] > (horizon + 3) * 300:   # nicht ueber Pausen hinweg
            return None
        hu, hd = b['high'] >= up, b['low'] <= dn
        if hu and hd:
            return 'both'
        if hu:
            return 'up'
        if hd:
            return 'down'
    return 'none'


def study(markets_bars):
    rows = []
    for market, bars in markets_bars.items():
        if len(bars) < 300:
            continue
        series = rg.compute_series(bars)
        mult, comm = pe.FUTURES[market]
        tick = pe.FUTURES_TICK[market]
        ts = sorted(b['time'] for b in bars)
        mid = ts[len(ts) // 2]
        for i in range(60, len(bars) - 1):
            f = series[i]
            if not f or not f['atr']:
                continue
            atr = f['atr']
            res = first_touch(bars, i, atr)
            if res is None:
                continue
            reg = rg.classify(f)['regime']
            cost_r = (comm + 2 * tick * pe.FUTURES_SLIP_TICKS * mult) / (atr * mult)   # Kosten in R je Kontrakt
            half = 'A' if bars[i]['time'] < mid else 'B'
            for pat in ['ALLE_KERZEN'] + patterns(bars, i, atr):
                rows.append((market, reg, pat, res, cost_r, half))
    return rows


def _wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def summarize(rows):
    g = defaultdict(list)
    for m, reg, pat, res, cost, half in rows:
        g[(reg, pat)].append((res, cost, half))
        g[('ALLE', pat)].append((res, cost, half))
    base = {}
    out = []
    for (reg, pat), v in g.items():
        dec = [x for x in v if x[0] in ('up', 'down', 'both')]
        n = len(dec)
        if n == 0:
            continue
        ups = sum(1 for x in dec if x[0] == 'up')
        downs = sum(1 for x in dec if x[0] in ('down', 'both'))       # beides -> zaehlt gegen Long
        downs_s = sum(1 for x in dec if x[0] == 'down')
        ups_s = sum(1 for x in dec if x[0] in ('up', 'both'))          # beides -> zaehlt gegen Short
        p_up, p_dn = ups / n, downs_s / n
        cost = sum(x[1] for x in dec) / n
        ev_long = (ups - downs) / n - cost
        ev_short = (downs_s - ups_s) / n - cost
        halves = {}
        for hname in 'AB':
            hd = [x for x in dec if x[2] == hname]
            if hd:
                u = sum(1 for x in hd if x[0] == 'up'); d = sum(1 for x in hd if x[0] in ('down', 'both'))
                ds = sum(1 for x in hd if x[0] == 'down'); us = sum(1 for x in hd if x[0] in ('up', 'both'))
                c = sum(x[1] for x in hd) / len(hd)
                halves[hname] = ((u - d) / len(hd) - c, (ds - us) / len(hd) - c, len(hd))
        item = {'regime': reg, 'pattern': pat, 'n': n, 'p_up': p_up, 'p_down': p_dn,
                'p_up_ci': _wilson(ups, n), 'p_down_ci': _wilson(downs_s, n), 'cost_r': cost,
                'ev_long_r': ev_long, 'ev_short_r': ev_short, 'halves': halves,
                'undecided_share': 1 - n / len(v)}
        out.append(item)
        if pat == 'ALLE_KERZEN':
            base[reg] = item
    for it in out:
        b = base.get(it['regime'])
        it['p_up_vs_base'] = it['p_up'] - b['p_up'] if b else None
        it['p_down_vs_base'] = it['p_down'] - b['p_down'] if b else None
        best = 'LONG' if it['ev_long_r'] >= it['ev_short_r'] else 'SHORT'
        it['best_side'] = best
        it['best_ev_r'] = max(it['ev_long_r'], it['ev_short_r'])
        hs = it['halves']
        k = 0 if best == 'LONG' else 1
        it['stable'] = bool('A' in hs and 'B' in hs and hs['A'][k] > 0 and hs['B'][k] > 0)
        # signifikant besser als die Basisrate? (unteres KI ueber Basisrate)
        if b and it['pattern'] != 'ALLE_KERZEN':
            it['beats_base'] = (it['p_up_ci'][0] > b['p_up']) if best == 'LONG' else (it['p_down_ci'][0] > b['p_down'])
        else:
            it['beats_base'] = False
    return out


def markdown(items, meta):
    L = ['# TAURUS Kerzen-Studie (5M)', '',
         f"Daten: {meta['source']} · {meta['from']} bis {meta['to']} · Märkte: {', '.join(meta['markets'])} · "
         f"{meta['bars']} Kerzen", '',
         'Messung: Einstieg nächste Kerze (Open). Was kommt zuerst innerhalb 1 Stunde: +1 ATR oder −1 ATR? '
         'p_up/p_down = Anteil. Bei 50 % hat ein Muster keine Richtung. '
         'Netto-R = Erwartung bei Stop = Ziel = 1 ATR nach Kommission und Slippage. '
         'Basis = alle Kerzen derselben Marktlage. „Schlägt Basis“ = unteres 95%-KI über der Basisrate.', '',
         '## Basisraten je Marktlage (alle Kerzen)', '', '| Marktlage | n | p_up | p_down | Kosten R |', '|---|---|---|---|---|']
    for it in sorted([x for x in items if x['pattern'] == 'ALLE_KERZEN'], key=lambda x: x['regime']):
        L.append(f"| {it['regime']} | {it['n']} | {it['p_up']*100:.1f}% | {it['p_down']*100:.1f}% | {it['cost_r']:.3f} |")
    L += ['', f'## Höchste Trefferquoten (n ≥ {MIN_N})', '',
          '| Marktlage | Muster | n | Richtung | Trefferquote | KI | vs. Basis | Netto-R | Hälfte A / B | stabil | schlägt Basis |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    cand = [x for x in items if x['n'] >= MIN_N and x['pattern'] != 'ALLE_KERZEN']
    for it in sorted(cand, key=lambda x: -max(x['p_up'], x['p_down']))[:40]:
        side = it['best_side']
        p = it['p_up'] if side == 'LONG' else it['p_down']
        ci = it['p_up_ci'] if side == 'LONG' else it['p_down_ci']
        vb = it['p_up_vs_base'] if side == 'LONG' else it['p_down_vs_base']
        k = 0 if side == 'LONG' else 1
        ha = it['halves'].get('A', (0, 0, 0))[k]; hb = it['halves'].get('B', (0, 0, 0))[k]
        L.append(f"| {it['regime']} | {it['pattern']} | {it['n']} | {side} | {p*100:.1f}% | {ci[0]*100:.0f}–{ci[1]*100:.0f}% | "
                 f"{(vb or 0)*100:+.1f} Pkt | {it['best_ev_r']:+.3f} | {ha:+.2f} / {hb:+.2f} | {'ja' if it['stable'] else 'nein'} | "
                 f"{'ja' if it['beats_base'] else 'nein'} |")
    good = [x for x in cand if x['best_ev_r'] > 0 and x['stable'] and x['beats_base']]
    L += ['', '## Kandidaten mit positivem Netto-R, stabil in beiden Hälften und besser als die Basis', '']
    if good:
        for it in sorted(good, key=lambda x: -x['best_ev_r']):
            L.append(f"- {it['regime']} · {it['pattern']} → {it['best_side']}: Netto {it['best_ev_r']:+.3f} R, n={it['n']}")
    else:
        L.append('- Keine. Kein Kerzenmuster erfüllt alle drei Bedingungen.')
    mx = max((max(x['p_up'], x['p_down']) for x in cand), default=0)
    L += ['', f'Höchste gemessene Trefferquote eines Musters mit n ≥ {MIN_N}: {mx*100:.1f}%.']
    return '\n'.join(L) + '\n'


def main(argv=None):
    import json
    import backtest as bt
    from feed_quality import clean
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--source', choices=('archive', 'yahoo', 'cache'), default='archive')
    ap.add_argument('--archive-dir', default='archives')
    ap.add_argument('--cache', help='candles.json.gz von backtest.py --save-candles')
    ap.add_argument('--markets', default='nq,mes,mgc')
    ap.add_argument('--out', default='candle_out')
    a = ap.parse_args(argv)
    markets = [m for m in a.markets.split(',') if m in pe.FUTURES]
    if a.source == 'archive':
        paths = [p for p in glob.glob(os.path.join(a.archive_dir, '**', '*.json*'), recursive=True) if os.path.basename(p)[:4].isdigit()]
        candles = bt.load_archive(paths)[0]
    elif a.source == 'cache':
        candles = bt.load_candles(a.cache)
    else:
        candles = {(m, '5m'): bt.load_yahoo(m, '5m', 60) for m in markets}
    mb = {m: clean(candles.get((m, '5m'), [])) for m in markets}
    rows = study(mb)
    items = summarize(rows)
    allt = [b['time'] for v in mb.values() for b in v]
    meta = {'source': a.source, 'markets': markets, 'bars': len(allt),
            'from': datetime.fromtimestamp(min(allt), timezone.utc).strftime('%Y-%m-%d') if allt else None,
            'to': datetime.fromtimestamp(max(allt), timezone.utc).strftime('%Y-%m-%d') if allt else None}
    os.makedirs(a.out, exist_ok=True)
    md = markdown(items, meta)
    open(os.path.join(a.out, 'candles.md'), 'w').write(md)
    json.dump({'meta': meta, 'items': items}, open(os.path.join(a.out, 'candles.json'), 'w'))
    print(md[:3000])


if __name__ == '__main__':
    main()
