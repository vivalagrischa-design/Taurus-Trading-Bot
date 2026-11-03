"""TAURUS Backtest: Welche Strategie funktioniert in welcher Marktlage?

Spielt die ECHTEN Taurus-Strategien (strategies.evaluate, bb_rsi.build) auf
historischen Kerzen ab und fuehrt jedes Signal mit DENSELBEN Regeln aus wie
das Live-LAB in paper_engine.py:

  * Signal auf abgeschlossener Kerze -> Einstieg zum OPEN der naechsten Kerze
    plus 1 Tick Slippage (pe._slipped)
  * Groesse: 200 USD Risiko je Trade inkl. Kommission und Slippage (pe.RISK)
  * Storno wie live: GAP_INVALID, RISK_LIMIT, TP_NOT_PROFITABLE_NET
  * Stop vor Ziel, wenn beide in derselben Kerze liegen (konservativ)
  * Trailing-Stop ab +1R auf Schlusskurs, folgt mit 1R Abstand
    (nicht fuer rev_bounce und bb_rsi_scale, wie live)
  * Gap durch den Stop: Ausstieg zum Open, nicht zum Stop-Preis
  * Pro Markt und Strategie hoechstens eine aktive Position

Jeder Trade bekommt die Marktlage aus regime.py zum Signalzeitpunkt
(ohne Lookahead) und wird mit analysis.stats ausgewertet.

Datenquellen:
  --source archive  die taeglichen Archive (Branch taurus-daily-archives)
  --source yahoo    yfinance: 60 Tage 5M, bis 29 Tage 1M (verzoegerte Proxies)

Kein Zugriff auf die Live-Datenbank, keine Orders. Reine Forschung.

Beispiele:
  python backtest.py --source yahoo --out backtest_out
  python backtest.py --source archive --archive-dir archives/2026 --compare-live
"""
import argparse
import bisect
import glob
import gzip
import json
import math
import os
import random
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import paper_engine as pe
import regime as rg
from analysis import stats

NY = ZoneInfo('America/New_York')
STEP = {'5m': 300, '1m': 60, 'extremes': 60}
WARMUP = {'5m': 75, '1m': 60, 'extremes': 60}       # wie paper_engine._advance_generic
# Live sieht 5 Tage 5M (~1380 Kerzen) bzw. 7 Tage 1M. Wir werten in
# ueberlappenden Fenstern dieser Groesse aus; die Ueberlappung dient als Aufwaermphase.
WINDOW = {'5m': 1380, '1m': 2400, 'extremes': 2400}
OVERLAP = {'5m': 380, '1m': 600, 'extremes': 600}
NO_TRAIL = ('bb_rsi_scale', 'rev_bounce')
YAHOO = {'nq': 'NQ=F', 'mes': 'ES=F', 'mgc': 'GC=F'}


# ------------------------------------------------------------------ Kerzen

def _clean(rows):
    out = {}
    for b in rows:
        try:
            t = int(b['time']); o, h, l, c = (float(b[k]) for k in ('open', 'high', 'low', 'close'))
        except (KeyError, TypeError, ValueError):
            continue
        if not all(math.isfinite(x) for x in (o, h, l, c)) or not l <= min(o, c) <= max(o, c) <= h:
            continue
        out[t] = {'time': t, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': float(b.get('volume') or 0)}
    return [out[t] for t in sorted(out)]


def load_archive(paths):
    """Kerzen und LAB-Trades aus den taeglichen JSON-Archiven (.json oder .json.gz)."""
    candles, trades = defaultdict(list), {}
    for path in sorted(paths):
        opener = gzip.open if path.endswith('.gz') else open
        with opener(path, 'rt') as f:
            day = json.load(f)
        for c in day.get('market_candles') or []:
            if c.get('system') == 'lab':
                candles[(c['market'], c['timeframe'])].append(
                    {'time': c['bar_time'], 'open': c['open'], 'high': c['high'], 'low': c['low'],
                     'close': c['close'], 'volume': c.get('volume')})
        for t in (day.get('lab') or {}).get('trades') or []:
            trades[t['id']] = t                      # spaeteres Archiv = neuerer Stand
    return {k: _clean(v) for k, v in candles.items()}, list(trades.values())


def load_yahoo(market, interval, days):
    """Verzoegerte Yahoo-Proxies wie yahoo_feed.py, nur abgeschlossene Kerzen.
    5M: bis 60 Tage in einem Abruf. 1M: in 7-Tage-Stuecken (Yahoo-Limit)."""
    import yfinance as yf
    tk = yf.Ticker(YAHOO[market])
    frames = []
    if interval == '5m':
        frames.append(tk.history(period=f'{min(days, 60)}d', interval='5m', auto_adjust=False, prepost=True, timeout=30))
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=min(days, 29))
        while start < end:
            stop = min(start + timedelta(days=7), end)
            frames.append(tk.history(start=start, end=stop, interval='1m', auto_adjust=False, prepost=True, timeout=30))
            start = stop
            time.sleep(1)
    step = STEP[interval]
    now = time.time()
    rows = []
    for frame in frames:
        for idx, r in frame.iterrows():
            t = int(idx.to_pydatetime().astimezone(timezone.utc).timestamp())
            if t + step > now:
                continue
            vol = r['Volume']
            rows.append({'time': t, 'open': r['Open'], 'high': r['High'], 'low': r['Low'], 'close': r['Close'],
                         'volume': vol if vol == vol else 0})
    return _clean(rows)


# ------------------------------------------------------------------ Signale

def _engine_signals(engine, market, bars5m, bars1m):
    """Alle Signale einer Engine auf dem ganzen Verlauf, fensterweise wie live."""
    from strategies import evaluate
    from bb_rsi import build as bb_build
    active = {'5m': pe.ACTIVE_5M, '1m': pe.ACTIVE_1M, 'extremes': pe.ACTIVE_EXTREMES}[engine]
    base = bars5m if engine == '5m' else bars1m
    if not base:
        return []
    w, ov = WINDOW[engine], OVERLAP[engine]
    times5 = [b['time'] for b in bars5m]
    found = {}
    start = 0
    while True:
        end = min(len(base), start + w)
        chunk = base[start:end]
        valid_from = chunk[0]['time'] if start == 0 else base[start + ov]['time']
        if engine == '5m':
            tiles = evaluate(chunk, market=market)
        else:
            last = chunk[-1]['time'] + 60
            done5 = bars5m[:bisect.bisect_right(times5, last - 300)]   # nur abgeschlossene 5M-Kerzen
            tiles = evaluate(done5[-WINDOW['5m']:], bars1m=chunk, market=market) if engine == '1m' else bb_build(chunk)
        for st in tiles:
            if st['id'] not in active:
                continue
            for sig in st['signals']:
                if sig.get('side') in ('LONG', 'SHORT') and valid_from <= int(sig['time']) <= chunk[-1]['time']:
                    found[(st['id'], int(sig['time']), sig['side'])] = dict(sig, strategy=st['id'], engine=engine)
        if end >= len(base):
            break
        start = end - ov
    return sorted(found.values(), key=lambda s: (s['time'], s['strategy']))


def generate_signals(market, bars5m, bars1m):
    sigs = _engine_signals('5m', market, bars5m, bars1m)
    if bars1m:
        if market == 'nq':                                  # Opening-Strategien laufen live nur fuer NQ
            sigs += _engine_signals('1m', market, bars5m, bars1m)
        sigs += _engine_signals('extremes', market, bars5m, bars1m)
    return sigs


def causality_audit(market, bars5m, signals, samples=40, seed=7):
    """Prueft, ob die Fenster-Auswertung dieselben Signale liefert wie live
    (Strategien Kerze fuer Kerze nur mit Vergangenheit aufgerufen).
    Abweichungen deuten auf Lookahead oder Fenster-Effekte in einer Strategie."""
    from strategies import evaluate
    rng = random.Random(seed)
    if len(bars5m) < WINDOW['5m'] // 2:
        return {'samples': 0, 'note': 'zu wenig Kerzen'}
    have = defaultdict(set)
    for s in signals:
        if s['engine'] == '5m':
            have[int(s['time'])].add((s['strategy'], s['side']))
    lo = min(len(bars5m) - 1, max(WARMUP['5m'], 300))
    cuts = sorted(rng.sample(range(lo, len(bars5m)), min(samples, len(bars5m) - lo)))
    # Zusaetzlich gezielt Kerzen mit Signal pruefen (sonst meist leere Vergleiche).
    sig_idx = [i for i, b in enumerate(bars5m) if b['time'] in have and i >= lo]
    cuts = sorted(set(cuts) | set(rng.sample(sig_idx, min(samples, len(sig_idx)))))
    mism = defaultdict(lambda: {'only_backtest': 0, 'only_live': 0, 'match': 0})
    for k in cuts:
        t = bars5m[k]['time']
        tiles = evaluate(bars5m[max(0, k - WINDOW['5m'] + 1):k + 1], market=market)
        live = {(st['id'], s['side']) for st in tiles if st['id'] in pe.ACTIVE_5M
                for s in st['signals'] if int(s['time']) == t and s.get('side') in ('LONG', 'SHORT')}
        for key in live | have[t]:
            slot = mism[key[0]]
            if key in live and key in have[t]:
                slot['match'] += 1
            elif key in live:
                slot['only_live'] += 1
            else:
                slot['only_backtest'] += 1
    return {'samples': len(cuts), 'by_strategy': dict(mism)}


# ------------------------------------------------------------------ Ausfuehrung (Spiegel von paper_engine)

def _open(trade, bar, market):
    side = trade['side']
    entry = pe._slipped(float(bar['open']), side, True, market)
    stop, tp = trade['signal_stop'], trade['signal_tp']
    dist = entry - stop if side == 'LONG' else stop - entry
    if dist <= 0 or (side == 'LONG' and entry >= tp) or (side == 'SHORT' and entry <= tp):
        return 'GAP_INVALID'
    if trade['strategy'] == 'bb_rsi_scale' and market in pe.FUTURES:
        return 'CRYPTO_RESEARCH_ONLY'
    mult, comm = pe.FUTURES[market]
    rpu = abs(entry - stop) * mult + comm + pe.FUTURES_TICK[market] * pe.FUTURES_SLIP_TICKS * mult
    qty = math.floor(pe.RISK / max(rpu, 0.0001))
    if qty > 0 and pe._estimated_net_at_stop({'side': side, 'entry': entry, 'qty': qty}, tp, market) <= 0:
        return 'TP_NOT_PROFITABLE_NET'
    risk_plan = qty * rpu
    if qty <= 0 or risk_plan > pe.RISK + 1e-5:
        return 'RISK_LIMIT'
    trade.update(status='OPEN', entry_time=int(bar['time']), entry=entry, stop=stop, initial_stop=stop, tp=tp,
                 qty=qty, risk_plan=risk_plan, trail_updates=0, mfe_r=0.0, mae_r=0.0)
    return None


def _manage(trade, bar, market):
    """Eine Kerze fuer einen offenen Trade. True = geschlossen."""
    side, stop, tp, entry = trade['side'], trade['stop'], trade['tp'], trade['entry']
    d = 1 if side == 'LONG' else -1
    r0 = abs(entry - trade['signal_stop']) or 1e-12
    fav = (bar['high'] - entry) if d == 1 else (entry - bar['low'])
    adv = (entry - bar['low']) if d == 1 else (bar['high'] - entry)
    trade['mfe_r'] = max(trade['mfe_r'], fav / r0)
    trade['mae_r'] = min(trade['mae_r'], -adv / r0)
    stop_hit = bar['low'] <= stop if d == 1 else bar['high'] >= stop
    tp_hit = bar['high'] >= tp if d == 1 else bar['low'] <= tp
    if not (stop_hit or tp_hit):
        if trade['strategy'] not in NO_TRAIL and (bar['close'] - entry) * d >= r0:
            cand = bar['close'] - d * r0
            new = max(stop, cand) if d == 1 else min(stop, cand)
            if new != stop:
                trade['stop'] = new
                trade['trail_updates'] += 1
        return False
    if stop_hit:
        raw = min(stop, bar['open']) if d == 1 else max(stop, bar['open'])
        reason = 'SL' if trade['trail_updates'] == 0 else 'TRAIL'
    else:
        raw, reason = tp, 'TP'
    mult, comm = pe.FUTURES[market]
    exit_price = pe._slipped(raw, side, False, market)
    gross = (exit_price - entry) * trade['qty'] * d * mult
    fees = trade['qty'] * comm
    trade.update(status='CLOSED', exit_time=int(bar['time']), exit=exit_price, exit_reason=reason,
                 gross_pnl=gross, fees_paid=fees, pnl=gross - fees)
    return True


def execute(market, bars, signals, engine):
    """Kerze fuer Kerze wie paper_engine._advance_generic (eine Engine, ein Markt)."""
    by_time = defaultdict(list)
    for s in signals:
        if s['engine'] == engine:
            by_time[int(s['time'])].append(s)
    active, done = {}, []
    tf = '5m' if engine == '5m' else '1m'
    for i, bar in enumerate(bars):
        if i < WARMUP[engine]:
            continue
        for key, t in list(active.items()):
            if t['status'] == 'PENDING' and t['signal_time'] < bar['time']:
                why = _open(t, bar, market)
                if why:
                    t.update(status='CANCELLED', exit_reason=why)
                    done.append(active.pop(key))
        for key, t in list(active.items()):
            if t['status'] == 'OPEN' and t['entry_time'] <= bar['time'] and _manage(t, bar, market):
                done.append(active.pop(key))
        for s in by_time.get(int(bar['time']), ()):
            if s['strategy'] in active:          # live: POSITION_ALREADY_ACTIVE
                continue
            ctx = pe._trade_context(bars[max(0, i - (240 if tf == '1m' else 48)):i + 1], int(s['time']), tf)
            active[s['strategy']] = {
                'id': f"{market}:{s['strategy']}:{int(s['time'])}:{s['side']}", 'market': market,
                'strategy': s['strategy'], 'engine': engine, 'side': s['side'], 'signal_time': int(s['time']),
                'signal_entry': float(s['entry']), 'signal_stop': float(s['stop']), 'signal_tp': float(s['tp']),
                'status': 'PENDING', 'phase': ctx.get('phase'), 'ny_session': ctx.get('ny_session'),
                'reason': str(s.get('reason', ''))}
    return done + list(active.values())


# ------------------------------------------------------------------ Marktlage + Auswertung

def attach_regime(trades, bars5m, news_days=frozenset()):
    series = rg.compute_series(bars5m)
    times = [b['time'] for b in bars5m]
    for t in trades:
        cutoff = t['signal_time'] + (300 if t['engine'] == '5m' else 60)
        f = rg.features_at(times, series, cutoff)
        cls = rg.classify(f, news_day=time.strftime('%Y-%m-%d', time.gmtime(t['signal_time'])) in news_days)
        t.update(regime=cls['regime'], vol=cls['vol'], side_vs_trend=rg.side_vs_trend(t['side'], cls['trend_dir']),
                 session=rg.session_of(t['signal_time']), news_day=cls['news_day'])
        if t['status'] == 'CLOSED':
            t['r'] = t['pnl'] / t['risk_plan'] if t['risk_plan'] else 0.0
            t['hold_min'] = (t['exit_time'] - t['entry_time']) / 60
    return trades


def _round(x):
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v) for v in x]
    return x


def summarize(trades, min_n=20):
    closed = [t for t in trades if t['status'] == 'CLOSED']
    def grouped(*dims):
        g = defaultdict(list)
        for t in closed:
            g[tuple(t[d] for d in dims)].append(t)
        return g
    def stat(rows):
        s = stats(rows, min_n)
        s['avg_mfe_r_losers'] = (sum(t['mfe_r'] for t in rows if t['pnl'] <= 0) /
                                 max(1, sum(1 for t in rows if t['pnl'] <= 0)))
        s['fees_usd'] = sum(t['fees_paid'] for t in rows)
        return s
    out = {
        'closed': len(closed), 'sum_usd': sum(t['pnl'] for t in closed),
        'cancelled': dict(sorted(_count(t['exit_reason'] for t in trades if t['status'] == 'CANCELLED').items())),
        'by_strategy': {k[0]: stat(v) for k, v in grouped('strategy').items()},
        'by_strategy_regime': {f'{k[0]}|{k[1]}': stat(v) for k, v in grouped('strategy', 'regime').items()},
        'by_strategy_side_vs_trend': {f'{k[0]}|{k[1]}': stat(v) for k, v in grouped('strategy', 'side_vs_trend').items()},
        'by_strategy_session': {f'{k[0]}|{k[1]}': stat(v) for k, v in grouped('strategy', 'session').items()},
        'by_market': {k[0]: stat(v) for k, v in grouped('market').items()},
    }
    playbook = defaultdict(list)
    for key, s in out['by_strategy_regime'].items():
        strat, reg = key.split('|')
        if s['n'] >= min_n and s['verdict'] in ('GRUEN', 'TENDENZ_PLUS'):
            playbook[reg].append({'strategy': strat, 'n': s['n'], 'avg_r': s['avg_r'], 'verdict': s['verdict']})
    out['playbook'] = {r: sorted(v, key=lambda x: -x['avg_r']) for r, v in playbook.items()}
    return _round(out)


def _count(items):
    c = defaultdict(int)
    for x in items:
        c[x] += 1
    return c


def markdown(summary, meta, audit):
    def fmt(s):
        return (f"| {s['n']} | {s['win_rate'] * 100:.0f}% | {s['avg_r']:+.2f} | "
                f"{(s['ci_low'] or 0):+.2f} … {(s['ci_high'] or 0):+.2f} | {s['sum_usd']:,.0f} | {s['verdict']} |")
    lines = ['# TAURUS Backtest', '',
             f"Daten: {meta['source']} · {meta['from']} bis {meta['to']} · Märkte: {', '.join(meta['markets'])}",
             f"Geschlossene Trades: {summary['closed']} · Summe: {summary['sum_usd']:,.0f} USD (200 USD Risiko je Trade, je Strategie getrennt)",
             '', 'R = Ergebnis / geplantes Risiko. KI = 95%-Konfidenzintervall des Durchschnitts-R. '
             'GRUEN/ROT nur wenn das ganze KI über/unter 0 liegt. Unter 20 Trades: ZU_WENIG.', '',
             '## Strategien gesamt', '', '| Strategie | n | Treffer | Ø R | KI | USD | Urteil |', '|---|---|---|---|---|---|---|']
    for k, s in sorted(summary['by_strategy'].items(), key=lambda kv: kv[1]['avg_r']):
        lines.append(f'| {k} ' + fmt(s))
    lines += ['', '## Strategie × Marktlage (n ≥ 10)', '', '| Strategie | Marktlage | n | Treffer | Ø R | KI | USD | Urteil |',
              '|---|---|---|---|---|---|---|---|']
    for k, s in sorted(summary['by_strategy_regime'].items()):
        if s['n'] >= 10:
            a, b = k.split('|')
            lines.append(f'| {a} | {b} ' + fmt(s))
    lines += ['', '## Playbook: positive Strategien je Marktlage (n ≥ 20)', '']
    if summary['playbook']:
        for reg, items in sorted(summary['playbook'].items()):
            lines.append(f"- **{reg}**: " + ', '.join(f"{x['strategy']} ({x['avg_r']:+.2f} R, n={x['n']}, {x['verdict']})" for x in items))
    else:
        lines.append('- Keine Strategie erreicht in einer Marktlage n ≥ 20 mit positivem Ø R.')
    if audit:
        lines += ['', '## Kausalitäts-Check (Fenster-Auswertung vs. Kerze für Kerze)', '',
                  'Abweichungen = Strategie liefert je nach Fensterlänge andere Signale (Lookahead oder Fenster-Effekt).', '']
        for m, a in audit.items():
            bad = {k: v for k, v in (a.get('by_strategy') or {}).items() if v['only_backtest'] or v['only_live']}
            lines.append(f"- {m}: {a.get('samples', 0)} Stichproben, " + (
                'keine Abweichungen' if not bad else 'Abweichungen: ' + ', '.join(
                    f"{k} (nur Backtest {v['only_backtest']}, nur live {v['only_live']}, gleich {v['match']})" for k, v in bad.items())))
    return '\n'.join(lines) + '\n'


def compare_with_live(bt_trades, live_trades):
    """Gleiche Trade-ID im Backtest und im Live-LAB: stimmen Status, Exit und P/L?"""
    live = {t['id']: t for t in live_trades if t.get('status') == 'CLOSED'}
    both = [(t, live[t['id']]) for t in bt_trades if t['status'] == 'CLOSED' and t['id'] in live]
    same_exit = sum(1 for a, b in both if a['exit_reason'].replace('TRAIL', 'SL') == b['exit_reason'])
    pnl_close = sum(1 for a, b in both if abs(a['pnl'] - float(b['pnl'])) <= 1.0)
    return {'live_closed': len(live), 'backtest_closed': sum(1 for t in bt_trades if t['status'] == 'CLOSED'),
            'matched_ids': len(both), 'same_exit_reason': same_exit, 'pnl_within_1usd': pnl_close,
            'pnl_live_matched': round(sum(float(b['pnl']) for _, b in both), 2),
            'pnl_backtest_matched': round(sum(a['pnl'] for a, _ in both), 2)}


# ------------------------------------------------------------------ CLI

def run(markets, candles, news_days=frozenset(), audit_samples=40):
    trades, audit = [], {}
    for m in markets:
        b5, b1 = candles.get((m, '5m'), []), candles.get((m, '1m'), [])
        if len(b5) < WARMUP['5m'] + 10:
            print(f'{m}: zu wenig 5M-Kerzen ({len(b5)}), übersprungen')
            continue
        t0 = time.time()
        sigs = generate_signals(m, b5, b1)
        mt = execute(m, b5, sigs, '5m')
        if b1:
            if m == 'nq':
                mt += execute(m, b1, sigs, '1m')
            mt += execute(m, b1, sigs, 'extremes')
        attach_regime(mt, b5, news_days)
        trades += mt
        if audit_samples:
            audit[m] = causality_audit(m, b5, sigs, audit_samples)
        print(f'{m}: {len(b5)} 5M / {len(b1)} 1M Kerzen, {len(sigs)} Signale, '
              f"{sum(t['status'] == 'CLOSED' for t in mt)} geschlossene Trades ({time.time() - t0:.0f}s)")
    return trades, audit


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--source', choices=('archive', 'yahoo'), default='archive')
    ap.add_argument('--archive-dir', default='archives', help='Ordner mit YYYY-MM-DD.json(.gz), rekursiv')
    ap.add_argument('--markets', default='nq,mes,mgc')
    ap.add_argument('--days-5m', type=int, default=60)
    ap.add_argument('--days-1m', type=int, default=29)
    ap.add_argument('--min-n', type=int, default=20)
    ap.add_argument('--audit-samples', type=int, default=40)
    ap.add_argument('--compare-live', action='store_true', help='nur mit --source archive')
    ap.add_argument('--out', default='backtest_out')
    a = ap.parse_args(argv)
    markets = [m.strip() for m in a.markets.split(',') if m.strip() in pe.FUTURES]
    live_trades = []
    if a.source == 'archive':
        paths = [p for p in glob.glob(os.path.join(a.archive_dir, '**', '*.json*'), recursive=True)
                 if os.path.basename(p)[:4].isdigit()]
        candles, live_trades = load_archive(paths)
    else:
        candles = {}
        for m in markets:
            candles[(m, '5m')] = load_yahoo(m, '5m', a.days_5m)
            candles[(m, '1m')] = load_yahoo(m, '1m', a.days_1m) if a.days_1m > 0 else []
    try:
        from analysis import load_news_days
        news = load_news_days()
    except Exception:
        news = frozenset()
    trades, audit = run(markets, candles, news, a.audit_samples)
    all5 = [b['time'] for m in markets for b in candles.get((m, '5m'), [])]
    meta = {'source': a.source, 'markets': markets, 'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'from': datetime.fromtimestamp(min(all5), NY).strftime('%Y-%m-%d') if all5 else None,
            'to': datetime.fromtimestamp(max(all5), NY).strftime('%Y-%m-%d') if all5 else None,
            'strategy_source_hash': pe.STRATEGY_SOURCE_HASH, 'risk_usd': pe.RISK}
    summary = summarize(trades, a.min_n)
    os.makedirs(a.out, exist_ok=True)
    doc = {'meta': meta, 'summary': summary, 'audit': audit, 'trades': _round(trades)}
    if a.compare_live and live_trades:
        doc['live_comparison'] = compare_with_live(trades, live_trades)
        print('Vergleich mit Live-LAB:', doc['live_comparison'])
    with open(os.path.join(a.out, 'backtest.json'), 'w') as f:
        json.dump(doc, f, separators=(',', ':'))
    md = markdown(summary, meta, audit)
    with open(os.path.join(a.out, 'backtest.md'), 'w') as f:
        f.write(md)
    print(f"\nGeschlossen: {summary['closed']}, Summe {summary['sum_usd']:,.0f} USD -> {a.out}/backtest.md")
    return doc


if __name__ == '__main__':
    main()
