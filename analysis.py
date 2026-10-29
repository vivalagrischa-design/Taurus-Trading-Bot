"""TAURUS Analyse: Welche Strategie funktioniert in welcher Marktlage?

Ablauf bei jedem Aufruf:
 1. Geschlossene Trades aus der Datenbank laden (paper_engine.trades).
 2. Fuer jeden Trade die Marktlage zum Signalzeitpunkt bestimmen
    (aus den gespeicherten 5M-Kerzen, ohne Lookahead) und in
    trade_regime dauerhaft speichern. Bereits berechnete werden wiederverwendet.
 3. Auswerten: Matrix Strategie x Marktlage, Einstiegsqualitaet, Playbook.
Alle Zahlen sind Papertrading-Forschung, keine Handelsempfehlung.
"""
import json
import math
import time
from bisect import bisect_right
from collections import defaultdict

import regime as rg

DIMS = {
    'regime': 'Marktlage',
    'vol': 'Volatilität',
    'session': 'Session',
    'side_vs_trend': 'Richtung vs. Trend',
    'hour_zh': 'Stunde (CH-Zeit)',
    'weekday': 'Wochentag',
}
WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
FEATURE_KEYS = ['adx', 'atr_pct', 'rsi', 'dist_vwap_atr', 'bb_width_pct', 'er60', 'ema_gap_atr', 'last_body_atr']
CHECKPOINTS_MIN = (5, 10, 15, 20, 30, 45, 60, 90)
_SERIES_CACHE = {}


# --------------------------------------------------------------- Datenzugriff
def ensure_tables(db):
    db.execute('''CREATE TABLE IF NOT EXISTS trade_regime(
        trade_id TEXT PRIMARY KEY, feature_version TEXT, computed_at BIGINT, features TEXT)''')


def _strategy_timeframes():
    from paper_engine import ACTIVE_1M, ACTIVE_EXTREMES
    return set(ACTIVE_1M) | set(ACTIVE_EXTREMES)


def load_candles(db, market):
    from paper_engine import TEST_VERSION
    rows = db.execute("SELECT bar_time,open,high,low,close,volume FROM market_candles "
                      "WHERE system='lab' AND run_id=? AND market=? AND timeframe='5m' ORDER BY bar_time",
                      (TEST_VERSION, market)).fetchall()
    return [dict(r) for r in rows]


def series_for(db, market):
    """Kennzahlen-Reihe je Markt, gecacht bis eine neue Kerze dazukommt."""
    bars = load_candles(db, market)
    key = (len(bars), bars[-1]['bar_time'] if bars else 0)
    hit = _SERIES_CACHE.get(market)
    if hit and hit['key'] == key:
        return hit
    prepared = [{'time': b['bar_time'], 'open': b['open'], 'high': b['high'],
                 'low': b['low'], 'close': b['close'], 'volume': b['volume']} for b in bars]
    entry = {'key': key, 'times': [b['time'] for b in prepared],
             'series': rg.compute_series(prepared), 'count': len(prepared)}
    _SERIES_CACHE[market] = entry
    return entry


# ------------------------------------------------------------ Trade-Anreicherung
def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def enrich_trades(db, rows, news_days=frozenset()):
    """Haengt jedem Trade Marktlage + Kennzahlen + R-Werte an."""
    ensure_tables(db)
    tf_1m = _strategy_timeframes()
    stored = {}
    for r in db.execute('SELECT trade_id,feature_version,features FROM trade_regime').fetchall():
        if r['feature_version'] == rg.FEATURE_VERSION:
            try:
                stored[r['trade_id']] = json.loads(r['features'])
            except Exception:
                pass
    markets = {}
    out = []
    now = int(time.time())
    for t in rows:
        t = dict(t)
        sig_time = int(t['signal_time'])
        cutoff = sig_time + (60 if t['strategy'] in tf_1m else 300)
        feats = stored.get(t['id'])
        if feats is None:
            m = t['market']
            if m not in markets:
                markets[m] = series_for(db, m)
            f = rg.features_at(markets[m]['times'], markets[m]['series'], cutoff) if markets[m]['count'] else None
            if f and f['time'] + rg.STEP >= cutoff - 6 * 3600:   # Kerzenabdeckung plausibel
                feats = f
                db.execute('INSERT INTO trade_regime(trade_id,feature_version,computed_at,features) VALUES(?,?,?,?) '
                           'ON CONFLICT(trade_id) DO UPDATE SET feature_version=excluded.feature_version,'
                           'computed_at=excluded.computed_at,features=excluded.features',
                           (t['id'], rg.FEATURE_VERSION, now, json.dumps(feats, separators=(',', ':'))))
        cls = rg.classify(feats, news_day=time.strftime('%Y-%m-%d', time.gmtime(sig_time)) in news_days)
        risk = float(t.get('risk_plan') or 0) or 200.0
        pnl = t.get('pnl')
        mfe = (float(t['mfe_usd']) / risk) if t.get('mfe_usd') is not None else None
        mae = (float(t['mae_usd']) / risk) if t.get('mae_usd') is not None else None
        hold = (int(t['exit_time']) - int(t['entry_time'])) / 60 if t.get('exit_time') and t.get('entry_time') else None
        item = {
            'id': t['id'], 'market': t['market'], 'strategy': t['strategy'], 'side': t['side'],
            'status': t['status'], 'signal_time': sig_time, 'entry_time': t.get('entry_time'),
            'exit_time': t.get('exit_time'), 'entry': t.get('entry'), 'exit': t.get('exit'),
            'pnl': None if pnl is None else float(pnl),
            'r': None if pnl is None else float(pnl) / risk,
            'mfe_r': mfe, 'mae_r': mae, 'hold_min': hold, 'exit_reason': t.get('exit_reason'),
            'regime': cls['regime'], 'vol': cls['vol'], 'trend_dir': cls['trend_dir'],
            'news_day': cls['news_day'],
            'session': rg.session_of(sig_time), 'hour_zh': rg.hour_zh(sig_time),
            'weekday': WEEKDAYS[rg.weekday_zh(sig_time)],
            'side_vs_trend': rg.side_vs_trend(t['side'], cls['trend_dir']),
            'features': {k: (feats or {}).get(k) for k in FEATURE_KEYS},
        }
        item['verdict'] = entry_verdict(item)
        out.append(item)
    return out


def entry_verdict(t):
    """Trennt Einstiegs- von Ausstiegsproblemen (nur geschlossene Trades)."""
    if t['status'] != 'CLOSED' or t['pnl'] is None:
        return None
    if t['pnl'] > 0:
        return 'GEWINN'
    mfe = t['mfe_r']
    if mfe is None:
        return 'VERLUST_UNKLAR'
    if mfe >= 1.0:
        return 'RUECKGABE'            # war >= 1R im Plus, am Ende Verlust -> Ausstieg
    if mfe < 0.5:
        return 'FALSCHER_EINSTIEG'    # nie ernsthaft im Plus -> Einstieg
    return 'VERLUST_TEILWEISE'


# ------------------------------------------------------------------ Statistik
def stats(rows, min_n=10):
    n = len(rows)
    if n == 0:
        return {'n': 0, 'verdict': 'ZU_WENIG', 'confidence': 'ZU_WENIG'}
    rs = [x['r'] for x in rows]
    usd = [x['pnl'] for x in rows]
    wins = sum(1 for x in usd if x > 0)
    gw = sum(x for x in usd if x > 0)
    gl = -sum(x for x in usd if x < 0)
    avg = sum(rs) / n
    ci_low = ci_high = None
    if n > 1:
        sd = math.sqrt(sum((x - avg) ** 2 for x in rs) / (n - 1))
        se = sd / math.sqrt(n)
        ci_low, ci_high = avg - 1.96 * se, avg + 1.96 * se
    p = wins / n
    z = 1.96
    wilson = (p + z * z / (2 * n) - z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / (1 + z * z / n)
    holds = [x['hold_min'] for x in rows if x.get('hold_min') is not None]
    if n < min_n:
        verdict = 'ZU_WENIG'
    elif ci_low is not None and ci_low > 0:
        verdict = 'GRUEN'            # statistisch klar positiv
    elif ci_high is not None and ci_high < 0:
        verdict = 'ROT'              # statistisch klar negativ
    elif avg > 0:
        verdict = 'TENDENZ_PLUS'
    elif avg < 0:
        verdict = 'TENDENZ_MINUS'
    else:
        verdict = 'NEUTRAL'
    return {
        'n': n, 'wins': wins, 'losses': n - wins, 'win_rate': p, 'win_rate_low': wilson,
        'avg_r': avg, 'ci_low': ci_low, 'ci_high': ci_high, 'sum_usd': sum(usd),
        'profit_factor': (gw / gl) if gl > 0 else None, 'verdict': verdict,
        'confidence': 'ZU_WENIG' if n < min_n else 'VORLAEUFIG' if n < 30 else 'BELASTBAR',
        'median_hold_min': sorted(holds)[len(holds) // 2] if holds else None,
    }


def _closed(trades):
    return [t for t in trades if t['status'] == 'CLOSED' and t['pnl'] is not None]


def _dim_value(t, dim):
    v = t.get(dim)
    return 'UNBEKANNT' if v is None else v


def matrix(trades, dim='regime', min_n=10):
    closed = _closed(trades)
    cols = sorted({_dim_value(t, dim) for t in closed}, key=lambda x: (isinstance(x, str), x))
    strategies = sorted({t['strategy'] for t in closed})
    cells = {}
    totals = {}
    for s in strategies:
        rows = [t for t in closed if t['strategy'] == s]
        totals[s] = stats(rows, min_n)
        cells[s] = {}
        for c in cols:
            sub = [t for t in rows if _dim_value(t, dim) == c]
            if sub:
                cells[s][str(c)] = stats(sub, min_n)
    col_totals = {str(c): stats([t for t in closed if _dim_value(t, dim) == c], min_n) for c in cols}
    return {'dim': dim, 'dim_label': DIMS.get(dim, dim), 'columns': [str(c) for c in cols],
            'strategies': strategies, 'cells': cells, 'totals': totals,
            'column_totals': col_totals, 'all': stats(closed, min_n)}


def entry_analysis(trades, min_n=10):
    closed = _closed(trades)
    verdicts = defaultdict(int)
    per_strategy = defaultdict(lambda: defaultdict(int))
    for t in closed:
        verdicts[t['verdict']] += 1
        per_strategy[t['strategy']][t['verdict']] += 1
    hours = []
    for h in range(24):
        sub = [t for t in closed if t['hour_zh'] == h]
        if sub:
            hours.append({'hour': h, **stats(sub, min_n)})
    buckets = {}
    for key in FEATURE_KEYS:
        vals = [(t['features'].get(key), t) for t in closed if t['features'].get(key) is not None]
        if len(vals) < 8 or len({v for v, _ in vals}) < 4:
            continue
        sv = sorted(v for v, _ in vals)
        edges = [sv[int(len(sv) * q / 4)] for q in (1, 2, 3)]
        groups = defaultdict(list)
        for v, t in vals:
            groups[bisect_right(edges, v)].append(t)
        bounds = [sv[0]] + edges + [sv[-1]]
        buckets[key] = [{'label': f'{bounds[i]:.2f} … {bounds[i + 1]:.2f}', **stats(groups[i], min_n)}
                        for i in range(4) if groups.get(i)]
        win_med = _median([v for v, t in vals if t['pnl'] > 0])
        loss_med = _median([v for v, t in vals if t['pnl'] <= 0])
        buckets[key] = {'buckets': buckets[key], 'median_winners': win_med, 'median_losers': loss_med}
    combos = []
    keyed = defaultdict(list)
    for t in closed:
        keyed[(t['strategy'], t['regime'], t['side_vs_trend'])].append(t)
    for (s, r, sv), rows in keyed.items():
        st = stats(rows, min_n)
        if st['n'] >= min_n:
            combos.append({'strategy': s, 'regime': r, 'side_vs_trend': sv, **st})
    combos.sort(key=lambda x: x['avg_r'])
    return {'verdicts': dict(verdicts), 'per_strategy': {k: dict(v) for k, v in per_strategy.items()},
            'hours': hours, 'features': buckets,
            'worst': combos[:8], 'best': combos[::-1][:8]}


def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def exit_timing(db, trades):
    """Zeit-Ausstieg: Wie oft endet ein Trade im Minus, wenn er nach X Minuten
    noch nicht im Plus ist? Braucht trade_path (wird ab jetzt live geloggt)."""
    closed = {t['id']: t for t in _closed(trades)}
    if not closed:
        return {'checkpoints': [], 'trades_with_path': 0}
    paths = defaultdict(dict)
    try:
        for r in db.execute('SELECT trade_id,minutes_since_entry,r_close FROM trade_path').fetchall():
            if r['trade_id'] in closed:
                paths[r['trade_id']][int(r['minutes_since_entry'])] = float(r['r_close'])
    except Exception:
        return {'checkpoints': [], 'trades_with_path': 0}
    out = []
    for cp in CHECKPOINTS_MIN:
        behind, ahead = [], []
        for tid, p in paths.items():
            near = [m for m in p if abs(m - cp) <= 2]
            t = closed[tid]
            if not near or (t['hold_min'] is not None and t['hold_min'] < cp - 2):
                continue                      # Trade war da schon beendet
            r_cp = p[min(near, key=lambda m: abs(m - cp))]
            (behind if r_cp <= 0 else ahead).append(t)
        out.append({'minutes': cp, 'behind': stats(behind, 5) if behind else {'n': 0},
                    'ahead': stats(ahead, 5) if ahead else {'n': 0}})
    return {'checkpoints': out, 'trades_with_path': len(paths)}


def hold_times(trades):
    closed = _closed(trades)
    res = {}
    for s in sorted({t['strategy'] for t in closed}):
        w = [t['hold_min'] for t in closed if t['strategy'] == s and t['pnl'] > 0 and t['hold_min'] is not None]
        l = [t['hold_min'] for t in closed if t['strategy'] == s and t['pnl'] <= 0 and t['hold_min'] is not None]
        res[s] = {'median_winners_min': _median(w), 'median_losers_min': _median(l), 'n_w': len(w), 'n_l': len(l)}
    return res


def playbook(trades, min_n=10):
    """Pro Strategie: wo laufen lassen, wo abschalten. 'belegt' nur bei
    statistisch klarem Ergebnis, sonst als Tendenz markiert."""
    mx = matrix(trades, 'regime', min_n)
    out = []
    for s in mx['strategies']:
        entry = {'strategy': s, 'total': mx['totals'][s], 'run': [], 'stop': [],
                 'lean_run': [], 'lean_stop': [], 'unknown': []}
        for col, st in mx['cells'][s].items():
            tag = {'n': st['n'], 'avg_r': st.get('avg_r'), 'win_rate': st.get('win_rate'), 'regime': col}
            v = st['verdict']
            (entry['run'] if v == 'GRUEN' else entry['stop'] if v == 'ROT' else
             entry['lean_run'] if v == 'TENDENZ_PLUS' else entry['lean_stop'] if v == 'TENDENZ_MINUS' else
             entry['unknown']).append(tag)
        out.append(entry)
    return out


def current_hints(trades, current_regime, min_n=10):
    closed = _closed(trades)
    hints = []
    for s in sorted({t['strategy'] for t in closed}):
        sub = [t for t in closed if t['strategy'] == s and t['regime'] == current_regime]
        if sub:
            st = stats(sub, min_n)
            hints.append({'strategy': s, 'n': st['n'], 'avg_r': st.get('avg_r'),
                          'win_rate': st.get('win_rate'), 'verdict': st['verdict']})
    return hints


# ------------------------------------------------------------------ Oeffentlich
def load_news_days():
    """Optionale Datei news_days.txt: ein Datum (YYYY-MM-DD) pro Zeile."""
    import os
    path = os.path.join(os.path.dirname(__file__), 'news_days.txt')
    if not os.path.isfile(path):
        return frozenset()
    with open(path, encoding='utf-8') as fh:
        return frozenset(x.strip() for x in fh if x.strip() and not x.startswith('#'))


def _load_trade_rows(db, market=None):
    from paper_engine import TEST_VERSION
    exp = db.execute('SELECT started_at FROM paper_experiments WHERE version=?', (TEST_VERSION,)).fetchone()
    started = int(exp['started_at']) if exp else 0
    sql = "SELECT * FROM trades WHERE signal_time>=? AND status IN ('CLOSED','OPEN')"
    params = [started]
    if market:
        sql += ' AND market=?'
        params.append(market)
    return db.execute(sql + ' ORDER BY signal_time', params).fetchall(), started


def report(dim='regime', market=None, min_n=10):
    from paper_engine import conn, _LOCK
    if dim not in DIMS:
        raise ValueError('unbekannte Dimension')
    with _LOCK:
        with conn() as db:
            rows, started = _load_trade_rows(db, market)
            trades = enrich_trades(db, rows, load_news_days())
            timing = exit_timing(db, trades)
            from paper_engine import DATABASE_URL, DB
            persistence = 'PostgreSQL' if DATABASE_URL else DB
    return {
        'generated_at': int(time.time()), 'experiment_started_at': started, 'persistence': persistence,
        'min_n': min_n, 'dims': DIMS, 'market': market or 'all',
        'trades': sorted(trades, key=lambda t: -t['signal_time']),
        'matrix': matrix(trades, dim, min_n), 'entries': entry_analysis(trades, min_n),
        'playbook': playbook(trades, min_n), 'hold_times': hold_times(trades), 'exit_timing': timing,
        'data_notes': {'closed': len(_closed(trades)),
                       'with_regime': sum(1 for t in trades if t['regime'] != 'UNBEKANNT'),
                       'with_mfe': sum(1 for t in _closed(trades) if t['mfe_r'] is not None)},
    }


def market_overview(min_n=10):
    """Seite 1: aktuelle Marktlage je Markt + was bisher in dieser Lage funktioniert hat."""
    from paper_engine import conn, _LOCK, MARKETS
    out = []
    with _LOCK:
        with conn() as db:
            rows, _ = _load_trade_rows(db)
            trades = enrich_trades(db, rows, load_news_days())
            for m in MARKETS:
                ser = series_for(db, m)
                f = next((x for x in reversed(ser['series']) if x), None) if ser['count'] else None
                cls = rg.classify(f)
                item = {'market': m, **cls, 'time': f['time'] + rg.STEP if f else None,
                        'session': rg.session_of(f['time'] + rg.STEP) if f else None,
                        'price': f['close'] if f else None,
                        'adx': f['adx'] if f else None, 'atr_pct': f['atr_pct'] if f else None,
                        'rsi': f['rsi'] if f else None, 'dist_vwap_atr': f['dist_vwap_atr'] if f else None,
                        'bb_width_pct': f['bb_width_pct'] if f else None}
                item['hints'] = current_hints(trades, cls['regime'], min_n) if f else []
                out.append(item)
    return {'generated_at': int(time.time()), 'markets': out, 'min_n': min_n}


def chart_data(market, bars=576):
    """Seite 1: Kursverlauf mit Marktlage je Kerze (Standard: 576 x 5M = 2 Tage)."""
    from paper_engine import conn, _LOCK, MARKETS
    if market not in MARKETS:
        raise ValueError('Unbekannter Markt')
    with _LOCK:
        with conn() as db:
            ser = series_for(db, market)
    out = []
    for f in ser['series'][-bars:]:
        if not f:
            continue
        cls = rg.classify(f)
        a, d = f.get('atr'), f.get('dist_vwap_atr')
        vwap = round(f['close'] - d * a, 2) if (d is not None and a) else None
        out.append({'t': f['time'], 'c': f['close'], 'v': vwap, 'r': cls['regime'], 'adx': f['adx']})
    return {'market': market, 'bars': out}


if __name__ == '__main__':          # python analysis.py  -> schnelle Textausgabe
    rep = report()
    mx = rep['matrix']
    print('Persistenz:', rep['persistence'], '| geschlossene Trades:', rep['data_notes']['closed'])
    for s in mx['strategies']:
        print(f'\n{s}')
        for c, st in mx['cells'][s].items():
            print(f"  {c:14s} {st['wins']}/{st['n']}  Ø {st['avg_r']:+.2f}R  {st['verdict']}")
