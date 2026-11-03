"""TAURUS Simulation: Monte-Carlo auf Basis von Backtest-Trades und Kerzen.

Drei Werkzeuge, alle reine Standardbibliothek, mit festem Seed reproduzierbar:

1. trades  Ziehen mit Zuruecklegen aus den Backtest-Trades einer Strategie
           (optional nur eine Marktlage): Verteilung der Summe nach N Trades,
           Wahrscheinlichkeit fuer ein Plus, typischer Drawdown.
           Zeigt, ob ein positives Ergebnis Zufall sein koennte.

2. lucid   Wie oft wuerde ein Lucid-25K-Konto mit diesen Trades das Ziel
           (+1250 USD) erreichen, bevor der Max Loss (1000 USD, nachgezogen)
           greift? Vereinfachung: Drawdown wird nach jedem Trade nachgezogen,
           nicht erst am Tagesende (strenger als Lucid). Risiko je Trade
           wird von 200 USD auf --risk skaliert.

3. path    "Time Machine" nach Marktlage: spielt den Rest eines Trades
           10'000-mal durch. Jede 5M-Kerze wird aus frueheren Kerzen
           derselben Tageszeit (+-2 Kerzen) gezogen, nur aus Phasen mit
           derselben Marktlage. Exits wie Taurus: Stop vor Ziel in derselben
           Kerze, Trailing ab +1R. Urteil nach Break-even-Quote 1/(1+R).

Simulation, keine Vorhersage. Die Zukunft kann Dinge tun, die in den Daten
nie vorkamen (News, Gaps, Halts).

Beispiele:
  python sim.py trades --report backtest_out/backtest.json --strategy omar --regime TREND_RUNTER
  python sim.py lucid  --report backtest_out/backtest.json --strategies omar,trend_pullback_mtf --risk 100
  python sim.py path   --source archive --archive-dir archives --market nq --side LONG \\
        --entry 29600 --stop 29580 --tp 29640 --time "2026-11-02 10:15"
"""
import argparse
import glob
import json
import os
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
SLOTS = 288                    # 5M-Kerzen pro 24h
COIN_FLIP, STRONG = 0.05, 0.15  # Urteilsschwellen in Prozentpunkten um die Break-even-Quote


def _pct(sorted_vals, q):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * q
    lo = int(k); hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def _closed(report, strategies=None, regime=None, market=None):
    rows = [t for t in report['trades'] if t.get('status') == 'CLOSED']
    if strategies:
        rows = [t for t in rows if t['strategy'] in strategies]
    if regime:
        rows = [t for t in rows if t.get('regime') == regime]
    if market:
        rows = [t for t in rows if t['market'] == market]
    return rows


# ------------------------------------------------------------------ 1. trades

def bootstrap_trades(rs, n_trades=100, runs=10000, seed=19):
    """rs: Liste von R-Werten. Gibt Verteilung der R-Summe nach n_trades zurueck."""
    if not rs:
        return {'n_source': 0, 'note': 'keine Trades'}
    rng = random.Random(seed)
    sums, dds = [], []
    for _ in range(runs):
        eq = peak = dd = 0.0
        for _ in range(n_trades):
            eq += rng.choice(rs)
            peak = max(peak, eq)
            dd = min(dd, eq - peak)
        sums.append(eq)
        dds.append(dd)
    sums.sort(); dds.sort()
    return {
        'n_source': len(rs), 'n_trades': n_trades, 'runs': runs, 'seed': seed,
        'avg_r_source': statistics.mean(rs),
        'p_positive': sum(1 for s in sums if s > 0) / runs,
        'sum_r_p5': _pct(sums, .05), 'sum_r_median': _pct(sums, .5), 'sum_r_p95': _pct(sums, .95),
        'max_dd_r_median': _pct(dds, .5), 'max_dd_r_p5': _pct(dds, .05),
        'reliability': 'ZU_WENIG' if len(rs) < 20 else 'VORLAEUFIG' if len(rs) < 30 else 'BELASTBAR',
    }


# ------------------------------------------------------------------ 2. lucid

def lucid_pass(pnls_usd, risk=200.0, target=1250.0, max_loss=1000.0, max_trades=400, runs=10000, seed=19):
    """pnls_usd: P/L je Trade bei 200 USD Risiko. Skaliert auf risk."""
    if not pnls_usd:
        return {'n_source': 0, 'note': 'keine Trades'}
    scale = risk / 200.0
    pool = [p * scale for p in pnls_usd]
    rng = random.Random(seed)
    passed = failed = 0
    to_pass, to_fail = [], []
    for _ in range(runs):
        eq = peak = 0.0
        for k in range(1, max_trades + 1):
            eq += rng.choice(pool)
            peak = max(peak, eq)
            if eq >= target:
                passed += 1; to_pass.append(k); break
            if eq <= min(peak - max_loss, 0.0):      # nachgezogen, bis die Grenze die Startbalance erreicht
                failed += 1; to_fail.append(k); break
    return {
        'n_source': len(pool), 'risk_per_trade': risk, 'runs': runs, 'seed': seed,
        'p_pass': passed / runs, 'p_fail': failed / runs, 'p_undecided': (runs - passed - failed) / runs,
        'median_trades_to_pass': statistics.median(to_pass) if to_pass else None,
        'median_trades_to_fail': statistics.median(to_fail) if to_fail else None,
        'note': 'Drawdown nach jedem Trade nachgezogen (strenger als Lucid EOD). Ohne Tageslimit und Konsistenzregel.',
    }


# ------------------------------------------------------------------ 3. path

def _slot(ts):
    et = datetime.fromtimestamp(int(ts), timezone.utc).astimezone(NY)
    return (et.hour * 60 + et.minute) // 5


def build_pool(bars5m, regimes=None):
    """Kerzen als Verhaeltnisse zum vorherigen Schluss, je Tageszeit-Slot.
    regimes: Liste gleicher Laenge mit der Marktlage der VORHERIGEN Kerze."""
    pool = defaultdict(list)
    for i in range(1, len(bars5m)):
        b, p = bars5m[i], bars5m[i - 1]
        pc = float(p['close'])
        if pc <= 0 or b['time'] - p['time'] > 3600:           # ueber Wochenende/Pause nicht verketten
            continue
        reg = regimes[i - 1] if regimes else None
        pool[(_slot(b['time']), reg)].append((b['open'] / pc, b['high'] / pc, b['low'] / pc, b['close'] / pc))
    return pool


def _candidates(pool, slot, regime, window, min_pool):
    out = []
    for d in range(-window, window + 1):
        out += pool.get(((slot + d) % SLOTS, regime), [])
    if len(out) >= min_pool or regime is None:
        return out, regime is not None
    alls = []
    for (s, _), v in pool.items():
        if min(abs(s - slot), SLOTS - abs(s - slot)) <= window:
            alls += v
    return alls, False


def path_sim(pool, side, entry, stop, tp, start_ts, bars_ahead=78, regime=None, trailing=True,
             replays=10000, seed=19, window=2, min_pool=30):
    long = side == 'LONG'
    d = 1 if long else -1
    r0 = abs(entry - stop)
    if r0 <= 0:
        raise ValueError('Stop muss auf der Verlustseite liegen')
    r_tp = abs(tp - entry) / r0
    start_slot = _slot(start_ts)
    cand, fallbacks = [], 0
    for k in range(1, bars_ahead + 1):
        c, regime_used = _candidates(pool, (start_slot + k) % SLOTS, regime, window, min_pool)
        if regime is not None and not regime_used:
            fallbacks += 1
        cand.append(c)
    if any(not c for c in cand):
        return {'note': 'zu wenig historische Kerzen fuer diese Tageszeit'}
    rng = random.Random(seed)
    outcomes, rs = defaultdict(int), []
    for _ in range(replays):
        p, st, res = entry, stop, None
        for c in cand:
            o, h, l, cl = rng.choice(c)
            hi, lo, close = p * h, p * l, p * cl
            stop_hit = lo <= st if long else hi >= st
            tp_hit = hi >= tp if long else lo <= tp
            if stop_hit:
                raw = min(st, p * o) if long else max(st, p * o)
                res = ('trail' if st != stop else 'stop', (raw - entry) * d / r0)
                break
            if tp_hit:
                res = ('target', r_tp)
                break
            if trailing and (close - entry) * d >= r0:
                cand_stop = close - d * r0
                st = max(st, cand_stop) if long else min(st, cand_stop)
            p = close
        if res is None:
            res = ('open', (p - entry) * d / r0)
        outcomes[res[0]] += 1
        rs.append(res[1])
    n = replays
    p_t, p_s = outcomes['target'] / n, outcomes['stop'] / n
    decided = p_t + p_s
    be = 1 / (1 + r_tp)
    share = p_t / decided if decided else None
    if share is None:
        verdict = 'Kein Ergebnis: weder Ziel noch Stop in der Zeit'
    else:
        gap = share - be
        side_word = 'zum Ziel' if gap > 0 else 'zum Stop'
        verdict = ('Nahe Break-even' if abs(gap) < COIN_FLIP else
                   ('Tendiert ' if abs(gap) < STRONG else 'Deutlich ') + side_word)
    rs.sort()
    return {
        'replays': n, 'seed': seed, 'bars_ahead': bars_ahead, 'regime': regime, 'trailing': trailing,
        'regime_fallback_bars': fallbacks, 'r_target': round(r_tp, 3),
        'p_target': p_t, 'p_stop': p_s, 'p_trail': outcomes['trail'] / n, 'p_open': outcomes['open'] / n,
        'avg_r': statistics.mean(rs), 'r_p5': _pct(rs, .05), 'r_median': _pct(rs, .5), 'r_p95': _pct(rs, .95),
        'break_even_share': be, 'target_share_of_decided': share, 'verdict': verdict,
    }


def regimes_for(bars5m):
    import regime as rg
    series = rg.compute_series(bars5m)
    return [rg.classify(f)['regime'] if f else 'UNBEKANNT' for f in series]


# ------------------------------------------------------------------ CLI

def _print(d):
    print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}, indent=2, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('trades'); t.add_argument('--report', required=True); t.add_argument('--strategy', required=True)
    t.add_argument('--regime'); t.add_argument('--market'); t.add_argument('--n', type=int, default=100)
    t.add_argument('--runs', type=int, default=10000); t.add_argument('--seed', type=int, default=19)
    lu = sub.add_parser('lucid'); lu.add_argument('--report', required=True); lu.add_argument('--strategies', required=True)
    lu.add_argument('--regime'); lu.add_argument('--risk', type=float, default=200.0)
    lu.add_argument('--runs', type=int, default=10000); lu.add_argument('--seed', type=int, default=19)
    p = sub.add_parser('path')
    p.add_argument('--source', choices=('archive', 'yahoo'), default='archive'); p.add_argument('--archive-dir', default='archives')
    p.add_argument('--market', default='nq'); p.add_argument('--side', choices=('LONG', 'SHORT'), required=True)
    p.add_argument('--entry', type=float, required=True); p.add_argument('--stop', type=float, required=True)
    p.add_argument('--tp', type=float, required=True); p.add_argument('--time', help='New York Zeit "YYYY-MM-DD HH:MM", Standard: letzte Kerze')
    p.add_argument('--regime', help='Marktlage erzwingen; Standard: die Marktlage zum Zeitpunkt')
    p.add_argument('--all-regimes', action='store_true', help='ohne Marktlagen-Filter')
    p.add_argument('--bars', type=int, default=78); p.add_argument('--no-trailing', action='store_true')
    p.add_argument('--replays', type=int, default=10000); p.add_argument('--seed', type=int, default=19)
    a = ap.parse_args(argv)
    if a.cmd in ('trades', 'lucid'):
        rep = json.load(open(a.report))
        if a.cmd == 'trades':
            rows = _closed(rep, [a.strategy], a.regime, a.market)
            _print(bootstrap_trades([r['r'] for r in rows], a.n, a.runs, a.seed))
        else:
            rows = _closed(rep, [s.strip() for s in a.strategies.split(',')], a.regime)
            _print(lucid_pass([r['pnl'] for r in rows], a.risk, runs=a.runs, seed=a.seed))
        return
    import backtest as bt
    if a.source == 'archive':
        paths = [x for x in glob.glob(os.path.join(a.archive_dir, '**', '*.json*'), recursive=True) if os.path.basename(x)[:4].isdigit()]
        bars = bt.load_archive(paths)[0].get((a.market, '5m'), [])
    else:
        bars = bt.load_yahoo(a.market, '5m', 60)
    if not bars:
        raise SystemExit('keine 5M-Kerzen gefunden')
    if a.time:
        ts = int(datetime.strptime(a.time, '%Y-%m-%d %H:%M').replace(tzinfo=NY).timestamp())
    else:
        ts = bars[-1]['time']
    regs = regimes_for(bars)
    idx = max([i for i, b in enumerate(bars) if b['time'] <= ts] or [0])
    history = [b for b in bars if b['time'] < ts]
    pool = build_pool(history, None if a.all_regimes else regs[:len(history)])
    regime = None if a.all_regimes else (a.regime or regs[idx])
    res = path_sim(pool, a.side, a.entry, a.stop, a.tp, ts, a.bars, regime, not a.no_trailing, a.replays, a.seed)
    res['history_bars'] = len(history)
    _print(res)


if __name__ == '__main__':
    main()
